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
        'importance': 0.25,
        'recency': 0.15,
        'similarity': 0.60,
    }
    RECENCY_HALF_LIFE_DAYS = 7  # fallback dla nieznanych source'ów

    # Per-type recency decay — różne źródła mają różne czasy życia
    # ephemeral: emocje, stany chwilowe — 3 dni
    # medium: preferencje, fakty ogólne — 60 dni
    # permanent: milestony, zdrowie, korekty — nie blakną (365 dni ~= infinity)
    RECENCY_HALF_LIFE_BY_SOURCE = {
        'extracted_emotion':    3,    # "jestem zmęczony" z 2 tygodni temu = szum
        'extracted_date':       7,    # terminy i daty — krótkie życie
        'extracted_fact':       60,   # preferencje, nawyki — długie życie
        'extracted_person':     90,   # ocena osób — bardzo długie życie
        'extracted_milestone':  365,  # deklaracje zaufania/miłości — permanentne
        'extracted_medication': 90,   # schematy leczenia — długie życie
        'extracted_goal':       30,   # cele — średnie życie
        'extracted_measurement': 30,  # pomiary ciała — średnie życie
        'extracted_financial':  14,   # budżety — krótkie życie
        'enriched':             30,   # wzbogacone przez pipeline
        'night_insight':        14,   # insighty nocne — średnie życie
        'character_core':       365,  # wektory charakteru — permanentne
        'md_import':            365,  # wiedza zewnętrzna — permanentna
    }

    # Temporal Filter (po wzorcu ucho-VPS) — HARD CUTOFF w godzinach.
    # Recency decay obniża score, ale wektor NADAL może wrócić.
    # Hard cutoff = po tym czasie wektor FIZYCZNIE odpada z wyników.
    # Tylko dla typów "śmieciowych" po czasie — permanentne fakty, milestony: bez limitu.
    TEMPORAL_CUTOFF_HOURS = {
        'extracted_emotion':   48,   # emocje → 2 dni max (potem irrelevant)
        'extracted_financial': 168,  # budżety → 7 dni
        'extracted_date':      168,  # stare daty → 7 dni (nowe już absolutne YYYY-MM-DD)
    }

    SESSION_COLLECTION_SUFFIX = "_session_v1"

    def __init__(self, collection_name="astra_memory_v1"):
        self.persist_directory = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 'chroma_db'
        )
        self.client = chromadb.PersistentClient(path=self.persist_directory)
        self.ef = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="paraphrase-multilingual-MiniLM-L12-v2"
        )
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=self.ef
        )
        # Osobna kolekcja dla historii sesji — nie miesza się z pamięcią semantyczną
        session_col_name = collection_name.replace("_v1", "") + self.SESSION_COLLECTION_SUFFIX
        self.session_collection = self.client.get_or_create_collection(
            name=session_col_name,
            embedding_function=self.ef
        )
        print(f"[ASTRA VectorStore] Initialized at {self.persist_directory}")
        print(f"[ASTRA VectorStore] Memory vectors: {self.collection.count()}")
        print(f"[ASTRA VectorStore] Session vectors: {self.session_collection.count()}")

    # ──────────────────────────────────────────────────────────
    # ADD
    # ──────────────────────────────────────────────────────────

    def add_memory(self, text: str, user_id: str, salt: str, persona_id: str = "astra",
                   source: str = "chat", importance: int = 5, is_milestone: bool = False,
                   timestamp: str = None, entity_subtype: str = "") -> str | None:
        """
        Dodaje wspomnienie do bazy wektorowej.
        ID = SHA256(salt:user_id:text) — deterministyczne, bezpieczne, bez duplikatów.
        entity_subtype: opcjonalny subtype encji (np. 'preference', 'tired') — używany przez supersede logic.
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
        if entity_subtype:
            metadata["entity_subtype"] = entity_subtype

        # upsert = ten sam tekst → ten sam slot, zero duplikatów
        self.collection.upsert(
            documents=[text_clean],
            metadatas=[metadata],
            ids=[mem_id]
        )
        return mem_id

    def delete_by_entity_subtype(self, entity_type: str, subtype: str,
                                  persona_id: str, user_id: str, salt: str) -> int:
        """
        Supersede logic: usuwa stare wektory tego samego entity_type:subtype przed dodaniem nowego.
        Działa tylko na wektorach które mają entity_subtype w metadanych (format po 2026-04-11).
        Zwraca liczbę usuniętych wektorów.
        """
        hashed_uid = hashlib.sha256(f"{salt}:{user_id}".encode()).hexdigest()[:16]
        source = f"extracted_{entity_type.lower()}"
        try:
            results = self.collection.get(
                where={
                    "$and": [
                        {"persona_id": {"$eq": persona_id}},
                        {"user_id": {"$eq": hashed_uid}},
                        {"source": {"$eq": source}},
                        {"entity_subtype": {"$eq": subtype}},
                    ]
                },
                include=["metadatas"]
            )
            ids = results.get('ids', [])
            if ids:
                self.collection.delete(ids=ids)
                print(f"[VectorStore] Supersede: usunięto {len(ids)} stary/ch {entity_type}:{subtype}")
            return len(ids)
        except Exception as e:
            print(f"[VectorStore] delete_by_entity_subtype error: {e}")
            return 0

    # ──────────────────────────────────────────────────────────
    # SESSION HISTORY (ChromaDB-persisted, survives restart)
    # ──────────────────────────────────────────────────────────

    # Licznik sekwencji — gwarantuje kolejność user→model w historii
    _seq: int = 0

    def add_session_message(self, conversation_id: str, role: str, content: str,
                            user_id: str, salt: str, persona_id: str = "astra",
                            thought: str = "", hint: str = "") -> str | None:
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
            "importance": 3,
            "is_milestone": False,
            "timestamp": datetime.utcnow().isoformat() + seq_suffix,
            "thought": thought[:500] if thought else "",
            "hint": hint[:200] if hint else "",
        }

        self.session_collection.upsert(
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
            results = self.session_collection.get(
                where={"conversation_id": conversation_id},
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
                "thought": meta.get("thought", ""),
            })

        # Sortuj po timestamp, ostatnie n
        messages.sort(key=lambda x: x["timestamp"])
        messages = messages[-n:]

        return [{"role": m["role"], "content": m["content"], "thought": m["thought"], "hint": m.get("hint", "")} for m in messages]

    # ──────────────────────────────────────────────────────────
    # SEARCH
    # ──────────────────────────────────────────────────────────

    @staticmethod
    def _keyword_boost(query: str, document: str, boost: float = 0.15) -> float:
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

            # 2. Recency — exponential decay z per-source half-life
            timestamp_str = meta.get('timestamp', '')
            source = meta.get('source', '')
            half_life = self.RECENCY_HALF_LIFE_BY_SOURCE.get(source, self.RECENCY_HALF_LIFE_DAYS)
            # Milestony i permanentne fakty zdrowotne nigdy nie blakną
            if meta.get('is_milestone', False):
                half_life = 365
            if timestamp_str:
                try:
                    ts = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                    age_days = max(0, (now - ts.replace(tzinfo=None)).days)
                    recency_score = 0.5 ** (age_days / half_life)
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

            # Milestone boost: +0.5 (zakres 1.0–1.5)
            # +1.0 było nadmiarowe odkąd half_life=365 chroni milestony przed blaknieniem
            if is_milestone:
                final_score += 0.5
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

    @staticmethod
    def _mmr_select(results: list, n: int, diversity_penalty: float = 0.8) -> list:
        """
        Maximum Marginal Relevance — wybiera n wyników balansując
        similarity (score) z diversity (unikanie klonów treściowych).
        Zapobiega dominacji jednego wektora we wszystkich slotach.
        """
        if not results or n <= 0:
            return results[:n]

        def _text_overlap(a: str, b: str) -> float:
            """Prosty overlap słów kluczowych (bez stopwords)."""
            stopwords = {'że', 'się', 'nie', 'ale', 'jak', 'co', 'to', 'jest',
                         'już', 'też', 'czy', 'być', 'mam', 'tak', 'na', 'do'}
            words_a = set(a.lower().split()) - stopwords
            words_b = set(b.lower().split()) - stopwords
            if not words_a or not words_b:
                return 0.0
            return len(words_a & words_b) / max(len(words_a), len(words_b))

        selected = []
        remaining = list(results)

        while remaining and len(selected) < n:
            if not selected:
                # Pierwszy: zawsze najlepszy score
                selected.append(remaining.pop(0))
                continue

            # Dla każdego kandydata: score - penalty za podobieństwo do już wybranych
            best_idx = 0
            best_mmr = float('-inf')
            selected_texts = [s['text'] for s in selected]

            for i, candidate in enumerate(remaining):
                cand_text = candidate.get('text', '')
                max_overlap = max(
                    _text_overlap(cand_text, sel_text)
                    for sel_text in selected_texts
                )
                mmr_score = candidate['final_score'] - diversity_penalty * max_overlap
                if mmr_score > best_mmr:
                    best_mmr = mmr_score
                    best_idx = i

            selected.append(remaining.pop(best_idx))

        return selected

    def search_memories(self, query: str, persona_id: str = "astra",
                        n: int = 6, pool_size: int = 30,
                        user_id: str = None, salt: str = None) -> list[dict]:
        """
        3-kanałowy RAG:
        - Kanał 1: ENRICHED + EXTRACTED — wspomnienia wzbogacone semantycznie (top-3)
        - Kanał 2: CHARACTER_CORE — wektory behawioralne (top-2, tylko jeśli relevant)
        - Kanał 3: MD_IMPORT — wiedza zewnętrzna (top-1, jeśli similarity > 0.35)
        Session_messages są w osobnej kolekcji (session_collection) — nie trafiają tu.

        user_id + salt: gdy podane, Kanał 1 filtruje po user_id (SaaS isolation).
        Kanał 2 (character_core) i Kanał 3 (md_import) są wspólne dla wszystkich userów.
        """
        # Hashed user_id dla filtrowania (SaaS isolation)
        hashed_uid = None
        if user_id and salt:
            hashed_uid = hashlib.sha256(f"{salt}:{user_id}".encode()).hexdigest()[:16]

        def _query(extra_filter: dict, limit: int, apply_user_filter: bool = False) -> list[dict]:
            try:
                base_filters = [{"persona_id": persona_id}, extra_filter]
                if apply_user_filter and hashed_uid:
                    base_filters.append({"user_id": hashed_uid})
                where = {"$and": base_filters} if len(base_filters) > 1 else base_filters[0]
                r = self.collection.query(
                    query_texts=[query],
                    n_results=limit,
                    where=where,
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

        # Kanał 1: enriched + extracted (session_messages w osobnej kolekcji — tu ich nie ma)
        # Wykluczamy md_import (Kanał 3), character_core (Kanał 2) i user_message_raw
        # user_message_raw = surowe kopie wiadomości usera — mają najwyższe cosine similarity
        # do aktualnej wiadomości (ten sam styl pisania) i wypychają wartościowe wspomnienia.
        # apply_user_filter=True — user B NIE widzi danych user A
        EXCLUDED_SOURCES = {'character_core', 'md_import', 'user_message_raw'}
        raw_mem = _query({"source": {"$ne": "md_import"}}, limit=pool_size,
                         apply_user_filter=True)
        mem_results = [
            r for r in raw_mem
            if r.get('metadata', {}).get('source') not in EXCLUDED_SOURCES
            # Filtruj extracted_person które są krótkimi cytatami (<50 znaków)
            # — tworzą echo-loop wracając w każdej turze jako top-scored
            and not (
                r.get('metadata', {}).get('source') == 'extracted_person'
                and len(r.get('text', '')) < 80  # echo-loop filter: PERSON krótsze niż 80 znaków = śmieć
            )
        ]
        if mem_results:
            mem_results = self.rerank(mem_results, query=query)

            # Temporal Filter (po wzorcu ucho-VPS): hard cutoff dla ephemeral typów.
            # Recency decay nie wystarczy — stare emocje/daty mogą wciąż dominować przez similarity.
            now_tf = datetime.utcnow()
            def _passes_temporal(r):
                src = r.get('metadata', {}).get('source', '')
                cutoff_h = self.TEMPORAL_CUTOFF_HOURS.get(src)
                if cutoff_h is None:
                    return True  # brak limitu dla long-term typów
                ts_str = r.get('metadata', {}).get('timestamp', '')
                if not ts_str:
                    return True
                try:
                    ts = datetime.fromisoformat(ts_str.split('.')[0]).replace(tzinfo=None)
                    return (now_tf - ts).total_seconds() / 3600 <= cutoff_h
                except Exception:
                    return True
            before_tf = len(mem_results)
            mem_results = [r for r in mem_results if _passes_temporal(r)]
            filtered_tf = before_tf - len(mem_results)
            if filtered_tf:
                print(f"[VectorStore] Temporal Filter: {before_tf} -> {len(mem_results)} ({filtered_tf} odfiltrowanych)")

            # Milestone MMR fix: wyciągnij milestony PRZED _mmr_select.
            # Bez tego MMR (n=3) eliminuje milestony — przegrywają z faktami bez boosta.
            mem_milestones = [r for r in mem_results if r.get('_is_milestone')]
            mem_facts = [r for r in mem_results if not r.get('_is_milestone')]
            mem_facts = self._mmr_select(mem_facts, n=3, diversity_penalty=0.8)
            mem_milestones = mem_milestones[:2]
            mem_results = mem_facts + mem_milestones
            print(f"[RAG COMPOSE] facts={len(mem_facts)} milestones={len(mem_milestones)} total={len(mem_facts)+len(mem_milestones)}")

        # Kanał 2: character_core (wektory behawioralne — top-2 zamiast top-1)
        # Dwa wektory pozwalają na współistnienie np. "JESTEM" + "daj perspektywę"
        char_results = _query({"source": {"$eq": "character_core"}}, limit=5)
        if char_results:
            char_results = self.rerank(char_results, query=query)
            char_results = [r for r in char_results if r.get('distance', 2) < 1.0]
            char_results = char_results[:2]

        # Kanał 3: wiedza zewnętrzna (md_import)
        know_results = _query({"source": {"$eq": "md_import"}}, limit=10)
        if know_results:
            know_results = self.rerank(know_results, query=query)
            know_results = [r for r in know_results if r.get('distance', 2) < 1.3]
            know_results = know_results[:1]

        # Scal, usuń duplikaty, ogranicz do n
        seen = set()
        combined = []
        for r in (char_results + mem_results + know_results):
            key = r['text'][:80]
            if key not in seen:
                seen.add(key)
                combined.append(r)

        combined.sort(key=lambda x: x.get('final_score', 0), reverse=True)
        return combined[:n]

    def get_recent_user_messages(self, persona_id: str, user_id: str, salt: str,
                                 n: int = 6, hours: int = 48) -> list[dict]:
        """
        RAW window (po wzorcu ucho-VPS): ostatnie N wiadomości użytkownika z ostatnich N godzin,
        z DOWOLNEJ sesji. Daje cross-session continuity — Astra wie co było mówione wczoraj,
        nawet jeśli semantic extractor nic nie wyciągnął lub baza nie zawierała patternów.
        Nie używa semantic search — czysto chronologiczne.
        """
        hashed_uid = hashlib.sha256(f"{salt}:{user_id}".encode()).hexdigest()[:16]
        cutoff_dt = datetime.utcnow() - timedelta(hours=hours)
        try:
            results = self.session_collection.get(
                where={
                    "$and": [
                        {"persona_id": {"$eq": persona_id}},
                        {"user_id": {"$eq": hashed_uid}},
                        {"role": {"$eq": "user"}},
                    ]
                },
                include=["documents", "metadatas"]
            )
        except Exception as e:
            print(f"[VectorStore] get_recent_user_messages error: {e}")
            return []

        if not results['documents']:
            return []

        messages = []
        for i, doc in enumerate(results['documents']):
            meta = results['metadatas'][i]
            ts_str = meta.get('timestamp', '')
            if not ts_str:
                continue
            try:
                ts = datetime.fromisoformat(ts_str.split('.')[0]).replace(tzinfo=None)
                if ts >= cutoff_dt:
                    messages.append({'text': doc, 'timestamp': ts_str, '_ts': ts})
            except (ValueError, TypeError):
                pass

        # Chronologicznie, ostatnie N
        messages.sort(key=lambda x: x['_ts'])
        messages = messages[-n:]
        return [{'text': m['text'], 'timestamp': m['timestamp']} for m in messages]

    def search(self, query: str, companion_filter: str = None,
               n_results: int = 5, **kwargs) -> list:
        """
        Compatibility shim dla MemoryConsolidator z ANIMA.
        Mapuje companion_filter -> persona_id.
        """
        persona_id = companion_filter or PERSONA_ID_DEFAULT
        return self.search_memories(query=query, persona_id=persona_id,
                                    n=n_results, pool_size=n_results * 5)

    def get_stats(self) -> dict:
        return {'total_vectors': self.collection.count()}
