"""
ASTRA - Vector Store (ChromaDB)
Oparty na ANIMA vector_store.py z następującymi zmianami:
- persona_id zamiast companion (gotowe na rodzinę person)
- user_id haszowany SHA256(salt:user_id:text) — security od dnia 0
- Score > 1.0 cap (Battle Royale fix)
- Reranker weights: similarity=0.65, importance=0.2, recency=0.15 (Battle Royale fix)
"""

import chromadb
from chromadb.utils import embedding_functions
import os
import hashlib
from datetime import datetime, timedelta


PERSONA_ID_DEFAULT = "astra"  # fallback dla compatibility shim


def _make_vector_id(user_id: str, text: str, salt: str) -> str:
    """SHA256(salt:user_id:text) — wyciek danych niemożliwy."""
    return hashlib.sha256(f"{salt}:{user_id}:{text}".encode('utf-8')).hexdigest()[:32]


class VectorStore:
    # Default weights — similarity-dominant (Battle Royale fix 2026-03-01)
    DEFAULT_WEIGHTS = {
        'importance': 0.2,
        'recency': 0.15,
        'similarity': 0.65,
    }
    RECENCY_HALF_LIFE_DAYS = 30

    def __init__(self, collection_name="astra_memory_v1"):
        self.persist_directory = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 'chroma_db'
        )
        self.client = chromadb.PersistentClient(path=self.persist_directory)
        self.ef = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=self.ef
        )
        print(f"[ASTRA VectorStore] Initialized at {self.persist_directory}")
        print(f"[ASTRA VectorStore] Vectors in collection: {self.collection.count()}")

    # ──────────────────────────────────────────────────────────
    # ADD
    # ──────────────────────────────────────────────────────────

    def add_memory(self, text: str, user_id: str, salt: str, persona_id: str = "astra",
                   source: str = "chat", importance: int = 5, is_milestone: bool = False,
                   timestamp: str = None) -> str | None:
        """
        Dodaje wspomnienie do bazy wektorowej.
        ID = SHA256(salt:user_id:text) — deterministyczne, bezpieczne, bez duplikatów.
        """
        if not text or len(text.strip()) < 10:
            return None

        # Echo loop prevention — strip [MEMORY]...[/MEMORY] zanim zapiszemy
        import re
        text_clean = re.sub(r'\[MEMORY\].*?\[/MEMORY\]', '', text, flags=re.DOTALL).strip()
        if len(text_clean) < 10:
            return None

        # Milestones dostaną importance=10
        if is_milestone:
            importance = 10

        mem_id = _make_vector_id(user_id, text_clean, salt)

        metadata = {
            "persona_id": persona_id,
            "user_id": hashlib.sha256(f"{salt}:{user_id}".encode()).hexdigest()[:16],
            "source": source,
            "importance": importance,
            "is_milestone": is_milestone,
            "timestamp": timestamp or datetime.utcnow().isoformat(),
        }

        # upsert = ten sam tekst → ten sam slot, zero duplikatów
        self.collection.upsert(
            documents=[text_clean],
            metadatas=[metadata],
            ids=[mem_id]
        )
        return mem_id

    # ──────────────────────────────────────────────────────────
    # SESSION HISTORY (ChromaDB-persisted, survives restart)
    # ──────────────────────────────────────────────────────────

    # Licznik sekwencji — gwarantuje kolejność user→model w historii
    _seq: int = 0

    def add_session_message(self, conversation_id: str, role: str, content: str,
                            user_id: str, salt: str, persona_id: str = "astra") -> str | None:
        """Zapisuje wiadomość z historii sesji (role=user|model)."""
        import re
        content_clean = re.sub(r'\[MEMORY\].*?\[/MEMORY\]', '', content, flags=re.DOTALL).strip()
        if not content_clean:
            return None

        # ID = hash(conv_id + role + content) — deterministyczne
        msg_id = hashlib.sha256(
            f"{salt}:{conversation_id}:{role}:{content_clean}".encode()
        ).hexdigest()[:32]

        # seq gwarantuje że user zawsze jest przed model w tej samej sekundzie
        VectorStore._seq += 1
        seq_suffix = f".{VectorStore._seq:06d}"

        metadata = {
            "persona_id": persona_id,
            "user_id": hashlib.sha256(f"{salt}:{user_id}".encode()).hexdigest()[:16],
            "source": "session_message",
            "role": role,
            "conversation_id": conversation_id,
            "importance": 3,   # session messages mają niski priorytet w RAG
            "is_milestone": False,
            "timestamp": datetime.utcnow().isoformat() + seq_suffix,
        }

        self.collection.upsert(
            documents=[content_clean],
            metadatas=[metadata],
            ids=[msg_id]
        )
        return msg_id

    def get_recent_session(self, conversation_id: str, n: int = 10) -> list[dict]:
        """
        Pobiera ostatnie N wiadomości z danej sesji (sorted by timestamp).
        Zwraca listę {role, content} dla Gemini history.
        """
        try:
            results = self.collection.get(
                where={
                    "$and": [
                        {"source": "session_message"},
                        {"conversation_id": conversation_id},
                    ]
                },
                include=["documents", "metadatas"]
            )
        except Exception as e:
            print(f"[VectorStore] get_recent_session error: {e}")
            return []

        if not results['documents']:
            return []

        messages = []
        for i, doc in enumerate(results['documents']):
            meta = results['metadatas'][i]
            messages.append({
                "role": meta.get("role", "user"),
                "content": doc,
                "timestamp": meta.get("timestamp", ""),
            })

        # Sortuj po timestamp, ostatnie n
        messages.sort(key=lambda x: x["timestamp"])
        messages = messages[-n:]

        return [{"role": m["role"], "content": m["content"]} for m in messages]

    # ──────────────────────────────────────────────────────────
    # SEARCH
    # ──────────────────────────────────────────────────────────

    @staticmethod
    def _keyword_boost(query: str, document: str, boost: float = 0.10) -> float:
        """Hybrid search lite — zlicza wspólne słowa kluczowe."""
        import re as _re
        _stopwords = {
            'jest', 'czym', 'było', 'były', 'jaki', 'jakie', 'jaka', 'kto',
            'co', 'jak', 'czy', 'ale', 'nie', 'tak', 'tego', 'tej', 'tych',
            'który', 'która', 'które', 'przez', 'oraz', 'lub', 'dla',
        }
        query_words = set(_re.findall(r'\b\w{4,}\b', query.lower())) - _stopwords
        if not query_words:
            return 0.0
        doc_lower = document.lower()
        matches = sum(1 for w in query_words if w in doc_lower)
        return boost * (matches / len(query_words))

    def rerank(self, results: list, weights: dict = None, query: str = '') -> list:
        """
        Rerank wyników wg similarity + importance + recency + keyword_boost.
        Milestones dostają +1.0 (guaranteed top).
        Score > 1.0 cap przed milestone boost (Battle Royale fix).
        """
        if not results:
            return results

        if weights is None:
            weights = self.DEFAULT_WEIGHTS

        now = datetime.utcnow()

        for result in results:
            meta = result.get('metadata', {})
            is_milestone = meta.get('is_milestone', False)

            # 1. Importance (0–1)
            importance_score = min(meta.get('importance', 5) / 10.0, 1.0)

            # 2. Recency — exponential decay, half-life 30 dni
            timestamp_str = meta.get('timestamp', '')
            if timestamp_str:
                try:
                    ts = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                    age_days = max(0, (now - ts.replace(tzinfo=None)).days)
                    recency_score = 0.5 ** (age_days / self.RECENCY_HALF_LIFE_DAYS)
                except (ValueError, TypeError):
                    recency_score = 0.5
            else:
                recency_score = 0.5

            # 3. Similarity (0–1), CAP przed milestone boost
            distance = result.get('distance', 1.0)
            similarity_score = max(0, min(1, 1 - (distance / 2)))  # cap [0,1]

            # 4. Keyword boost
            kw_boost = self._keyword_boost(query, result.get('text', '')) if query else 0.0

            # Weighted sum
            final_score = (
                weights['importance'] * importance_score +
                weights['recency'] * recency_score +
                weights['similarity'] * similarity_score +
                kw_boost
            )

            # Temporal boost: wiadomości z ostatnich 24h
            if timestamp_str:
                try:
                    ts_check = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                    age_hours = (now - ts_check.replace(tzinfo=None)).total_seconds() / 3600
                    if age_hours < 24:
                        final_score += 0.15
                except (ValueError, TypeError):
                    pass

            # CAP do 1.0 PRZED milestone boost
            final_score = min(final_score, 1.0)

            # Milestone boost: +1.0 (zakres 1.0–2.0)
            if is_milestone:
                final_score += 1.0
                result['_is_milestone'] = True

            result['final_score'] = round(final_score, 4)
            result['_score_detail'] = {
                'similarity': round(similarity_score, 3),
                'importance': round(importance_score, 3),
                'recency': round(recency_score, 3),
                'keyword': round(kw_boost, 3),
            }

        results.sort(key=lambda x: x['final_score'], reverse=True)
        return results

    def search_memories(self, query: str, persona_id: str = "astra",
                        n: int = 5, pool_size: int = 20) -> list[dict]:
        """
        Dual-channel RAG:
        - Kanał 1: wspomnienia z rozmów (top-3)
        - Kanał 2: wiedza zewnętrzna md_import (top-2, jeśli similarity > 0.35)
        Zapobiega dominacji świeżych wspomnień nad dokumentami wiedzy.
        """
        def _query(extra_filter: dict, limit: int) -> list[dict]:
            try:
                r = self.collection.query(
                    query_texts=[query],
                    n_results=limit,
                    where={"$and": [{"persona_id": persona_id}, extra_filter]},
                    include=["documents", "metadatas", "distances"]
                )
            except Exception as e:
                print(f"[VectorStore] search error: {e}")
                return []
            out = []
            if r['documents'] and r['documents'][0]:
                for i, doc in enumerate(r['documents'][0]):
                    out.append({
                        'text': doc,
                        'metadata': r['metadatas'][0][i],
                        'distance': r['distances'][0][i],
                    })
            return out

        # Kanał 1: wspomnienia (bez session_message i md_import)
        # Uwaga: ChromaDB nie obsługuje $nin, filtrujemy po pobraniu
        raw_mem = _query({"source": {"$ne": "session_message"}}, limit=pool_size)
        mem_results = [r for r in raw_mem if r.get('metadata', {}).get('source') != 'md_import']
        if mem_results:
            mem_results = self.rerank(mem_results, query=query)
            mem_results = mem_results[:3]

        # Kanał 2: wiedza zewnętrzna (md_import)
        know_results = _query({"source": {"$eq": "md_import"}}, limit=10)
        if know_results:
            know_results = self.rerank(know_results, query=query)
            # Tylko jeśli similarity jest sensowna (distance < 1.3 ≈ similarity > 0.35)
            know_results = [r for r in know_results if r.get('distance', 2) < 1.3]
            know_results = know_results[:2]

        # Scal, usuń duplikaty po tekście, ogranicz do n
        seen = set()
        combined = []
        for r in (know_results + mem_results):
            key = r['text'][:80]
            if key not in seen:
                seen.add(key)
                combined.append(r)

        combined.sort(key=lambda x: x.get('final_score', 0), reverse=True)
        return combined[:n]

    def search(self, query: str, companion_filter: str = None,
               n_results: int = 5, **kwargs) -> list:
        """
        Compatibility shim dla MemoryConsolidator z ANIMA.
        Mapuje companion_filter -> persona_id.
        """
        persona_id = companion_filter or PERSONA_ID_DEFAULT
        return self.search_memories(query=query, persona_id=persona_id,
                                    n=n_results, pool_size=n_results * 4)

    def get_stats(self) -> dict:
        return {'total_vectors': self.collection.count()}
