# FABLE 5 — AUDYT PROJEKTU RAG DEBUGGERA (gotowe do wklejenia)

> Wklej CAŁY ten dokument do JEDNEJ rozmowy z Fable. Zawiera: architekturę produkcyjną (A),
> projekt debuggera (B), kod źródłowy RAG (C), realny bug (D), wnioski z ewolucji (E), a na końcu PROMPT.
> Fable nie widzi repo — to jest komplet ground truth.

---

## SEKCJA A — ARCHITEKTURA ANIMA (stan aktualny, zweryfikowany z kodu VPS)

Sovereign-memory AI companion. FastAPI na VPS, Gemini 2.5 Flash (chat: `max_output_tokens=8192`, `thinking_budget=4096`, JSON mode). Embeddingi lokalne: `paraphrase-multilingual-MiniLM-L12-v2` (ChromaDB).

**TRZY PERSONY — RÓŻNE PRAWA (kluczowe dla audytu):**
- **Astra (solo)** — `/api/chat`. Kolekcje `astra_memory_v1` + `astra_memory_session_v1`, własny `fact_store` (`astra_facts.db`), własny `CompanionState`.
- **Amelia (solo)** — `/api/amelia`. `amelia_vector_store`, `amelia_fact_store` + `amelia_lookup` (legacy `ucho_amelia.db`), własny stan.
- **Wspólny Pokój (Astra + Amelia razem)** — `/api/wspolny`. `shared_vector_store`. Inny flow: dwie persony w jednej turze, role-alternation (Astra→Amelia), Echo-Loop Guard, Anti-Sync (jedna dotyka naraz), signal-based ordering. `thinking_budget=2048`, `max_output=4096`.
- **PLANOWANE: pokój Holo/Menma/Nazuna** — 3 persony na izolowanych kolekcjach.

**RETRIEVAL na turę** (`search_memories` -> `build_system_prompt`):
- Warstwa 0 — FactStore (SQLite exact lookup) -> blok `[TWARDE FAKTY]`, priorytet nad RAG.
- Kanał 1 — enriched memories: reranker `sim*0.60 + importance*0.25 + recency*0.15 + keyword_boost`, dedup MMR (cosine).
- Kanał 1b — Guaranteed Milestone Channel: wektory `is_milestone` -> gwarantowany top.
- Kanał 2 — character_core (wektory behawioralne). Kanał 3 — md_import (wiedza zewnętrzna).
- Temporal Filter (`_passes_temporal`): cutoffy (emocje 48h, daty/finanse 168h).
- RAW window: `get_recent_user_messages` -> blok `[OSTATNIE SŁOWA ŁUKASZA — cross-session]`.
- Historia sesji: `get_recent_session(conv_id, n=10)` <- UWAGA: tylko 5 wymian okna kontekstu.

**Uwaga:** w kodzie ISTNIEJE JUŻ zalążek debuggera (endpointy `/api/debug/rag`, `/api/debug/facts`, `/api/debug/stats`, strona `/debug` — patrz Sekcja C). To punkt wyjścia, NIE docelowy 7-warstwowy debugger z Sekcji B. Audytuj lukę między tym co jest, a projektem.

---

## SEKCJA B — PROJEKT DEBUGGERA (dotychczasowy)

# RAG Debugger — Architektura (ustalona 2026-06-15, zaktualizowana 2026-06-18)

## Cel
Narzędzie do testowania i debugowania pipeline'u RAG bez dotykania prawdziwej sesji.
Przyspiesza iterację przy zmianach rerankera, wag, filtrów — z godzin do minut.
Prerequisite dla BM25 hybrid retrieval.

## Deployment
VPS — osobna strona pod `/debug`, zabezpieczona hasłem (Basic Auth — już mamy na nginx).

═══════════════════════════════════════════════════════════
## ⚠️ ZASADA NACZELNA — GWARANCJA STANU PRODUKCYJNEGO (2026-06-18)
═══════════════════════════════════════════════════════════
Debugger MUSI czytać fizycznie ten sam stan co produkcja — nie kopię, nie symulację,
nie uproszczoną wersję. Inaczej "działa w debuggerze" ≠ "działa live" i narzędzie kłamie.

### JAK to gwarantujemy: IN-PROCESS + WSPÓŁDZIELONE SINGLETONY
Debugger NIE jest osobnym procesem ani osobną aplikacją. To route `/debug` w TYM SAMYM
`main.py` (ta sama instancja FastAPI). Wywołuje DOKŁADNIE te same obiekty-singletony,
których używa żywy `/api/chat`:

| Stan | Obiekt produkcyjny (singleton w main.py) | Źródło na dysku |
|------|------------------------------------------|-----------------|
| Twarde fakty | `fact_store` / `amelia_lookup` | `astra_facts.db` / `amelia_facts.db` / `ucho_amelia.db` |
| Wektory RAG | `vector_store` / `amelia_vector_store` / `shared_vector_store` | `chroma_db/` |
| Historia sesji | te same `.get_recent_session(conv_id, n=30)` | kolekcje `*_session_v1` |
| CompanionState | `state_manager.load()` | `companion_state.json` / `amelia_companion_state.json` |

To jest gwarancja przez TOŻSAMOŚĆ obiektu, nie przez równoważność kopii. Cokolwiek widzi
produkcja, debugger widzi — bo to ten sam obiekt Pythona wskazujący na ten sam plik.
(Opcja "osobny proces otwierający te same pliki" — ODRZUCONA: ryzyko lock/stale-read/dryf.)

### READ-ONLY — debugger NIGDY nie pisze
Wywołuje wyłącznie ścieżki odczytu: `get_facts_for_prompt`, `search_memories`,
`get_recent_session`, `state_manager.load()`.
ZAKAZANE w debuggerze: `add_session_message`, `fact_store.upsert`,
`pipeline.process_message`, `state_manager.save`. Symulacja Gemini = DRY RUN
(buduje prompt → woła Gemini → zwraca odpowiedź → NIC nie zapisuje).

### SYMULACJA DATY — parametr, NIGDY mutacja globalna (KRYTYCZNE)
Recency decay i Temporal Filter używają wewnątrz `datetime.utcnow()`. Ponieważ debugger
dzieli proces z produkcją, NIE WOLNO monkeypatchować globalnego zegara — zatrułoby to
żywe requesty lecące równolegle.
Rozwiązanie: dodać opcjonalny parametr `now_override` przepychany przez:
`search_memories(..., now_override=None)` → reranker recency calc → `_passes_temporal`.
- `now_override=None` (produkcja) → realny `datetime.utcnow()`
- `now_override=<data z suwaka>` (tylko ten jeden call debuggera) → symulowana data
Dwa równoległe calle (live + debug) nie kolidują, bo override jest per-wywołanie.

### EXPLICITE: CO JEST REALNE, CO SYMULOWANE
Debugger MUSI oznaczać każdą warstwę banerem, żeby nigdy nie pomylić trybu:
- 🟢 LIVE — FactStore (`astra_facts.db`)
- 🟢 LIVE — Wektory (`chroma_db`)
- 🟢 LIVE — Historia sesji (n=30, conversation_id = `state.active_conversation_id`)
- 🟢 LIVE — CompanionState (mood, concerns)
- 🟡 SYMULACJA — Data (np. +30 dni) [jedyna wstrzyknięta zmienna stanu]
- 🟡 SYMULACJA — Fraza zapytania (ty ją wpisujesz, to nie realna wiadomość usera)
- 🟡 SYMULACJA — safe_haven (jeśli wymusisz ręcznie; domyślnie liczony jak w prod)
- ⚪ DRY-RUN — Odpowiedź Gemini (realny model, ale NIE zapisana, nie weszła do sesji)

### Wymagana zmiana w kodzie produkcyjnym (prerequisite, mała):
Dodać `now_override: datetime|None = None` do `search_memories`, funkcji recency w
`rerank`, i `_passes_temporal` w `vector_store.py`. Default `None` = zero zmian dla prod.
To jedyna ingerencja w kod produkcyjny — reszta debuggera tylko czyta.

## INPUT
- Fraza zapytania (tekst) — 🟡 SYM
- Symulowana data (suwak: -90 dni → +180 dni od dziś) — 🟡 SYM
- Persona (Astra / Amelia / Wspólny Pokój) — wybiera który zestaw singletonów czytać

## PIPELINE — 7 warstw widocznych na ekranie

### Warstwa 0 — FactStore (TWARDE FAKTY) 🟢 LIVE
Co `fact_store.get_facts_for_prompt()` / `amelia_lookup` wyciąga dla tej persony PRZED
ChromaDB. Exact lookup z SQLite. To trafia do bloku [TWARDE FAKTY] z pierwszeństwem nad RAG.
Bez tej warstwy widzisz tylko połowę promptu.

### Warstwa 1 — Raw pool ChromaDB 🟢 LIVE
Top-30 wektorów przed filtrem. Widoczne: tekst + cosine similarity.

### Warstwa 2 — Po Temporal Filter 🟢 LIVE (z 🟡 datą jeśli suwak)
Co odpadło i dlaczego. Przykład: "EMOTION:tired — 52h temu, cutoff 48h → odrzucony".
To tutaj symulowana data zmienia wynik (recency decay testowalny bez czekania).

### Warstwa 3 — Kanał 1b (milestony) 🟢 LIVE
Ile milestonów znaleziono, które, z jakim score. Guaranteed top-2.
DODATKOWO (sugestia claude.ai 2026-06-15): pokazuj też milestony które NIE weszły do
gwarantowanych slotów i dlaczego (score tuż pod progiem). Czasem ważniejsze co odpadło.
[Tu zobaczysz na żywo monotonię milestonów — Anomalia 2 z audytu.]

### Warstwa 4 — Reranker scores 🟢 LIVE
Każdy kandydat: similarity×0.60 + importance×0.25 + recency×0.15 + keyword_boost + final.
(recency liczone względem 🟡 daty jeśli suwak ustawiony)

### Warstwa 5 — MMR 🟢 LIVE
Co odrzucono jako duplikat semantyczny (cosine). Które pary były zbyt podobne.

### Warstwa 6 — Finalny blok [WSPOMNIENIA] 🟢 LIVE
Dokładnie to co trafia do promptu. Copy-paste ready. + sklejony z Warstwą 0 = pełny
kontekst który dostaje Gemini.

## OUTPUT — Symulacja odpowiedzi ⚪ DRY-RUN
Wysyła [TWARDE FAKTY] + [WSPOMNIENIA] + historia sesji (n=30, LIVE) + fraza → prawdziwy Gemini.
Zwraca gotową odpowiedź persony. BEZ zapisu do bazy, BEZ wejścia do sesji, BEZ ekstrakcji.
Pełny dry-run rozmowy.

## Killer feature
Symulacja daty (parametr `now_override`, nie mutacja globalna) — ustawiasz "za 3 tygodnie"
i widzisz: co recency decay wygasi, czy Astra będzie pamiętać dane wydarzenie za miesiąc,
jak zmieni się reranker w czasie. Bez czekania, bez ryzyka dla żywej sesji.

## Szacowany wpływ
- Debugowanie rerankera: godziny → minuty
- Weryfikacja BM25: niemożliwa bez debuggera → możliwa przy pierwszym teście
- Ogólne przyspieszenie iteracji RAG: ~5x
- Warunek tej wartości: Warstwa 0 + symulacja czytają STAN PRODUKCYJNY (in-process,
  współdzielone singletony). Inaczej narzędzie kłamie i 5x staje się 5x szybszym błądzeniem.

## Kolejność budowy
1. Prerequisite: `now_override` param w `vector_store.py` (mała, bezpieczna zmiana, default None).
2. Route `/debug` in-process, czytający singletony (read-only).
3. Warstwy 0-6 jako JSON → render.
4. Dry-run Gemini.
5. (opcjonalnie później) zapis przebiegów do `.jsonl` do porównań A/B.

---

## SEKCJA C — KOD ŹRÓDŁOWY (ground truth)

### backend/vector_store.py
```python
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
                "hint": meta.get("hint", ""),
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

            # Milestone boost: +0.25 (zakres 1.0–1.25)
            # Zmniejszony z +0.5: bieżący kontekst z wysokim similarity może rywalizować z milestonyami.
            # half_life=365 i tak chroni milestony przed blaknieniem — boost tylko ułatwia wyciąganie.
            if is_milestone:
                final_score += 0.25
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
        Używa cosine similarity między wektorami embeddingów gdy dostępne,
        fallback do word-overlap dla wektorów bez embeddingu.
        """
        if not results or n <= 0:
            return results[:n]

        import math

        def _cosine(a: list, b: list) -> float:
            dot = sum(x * y for x, y in zip(a, b))
            norm_a = math.sqrt(sum(x * x for x in a))
            norm_b = math.sqrt(sum(y * y for y in b))
            if norm_a == 0 or norm_b == 0:
                return 0.0
            return dot / (norm_a * norm_b)

        def _text_overlap_fallback(a: str, b: str) -> float:
            stopwords = {'że', 'się', 'nie', 'ale', 'jak', 'co', 'to', 'jest',
                         'już', 'też', 'czy', 'być', 'mam', 'tak', 'na', 'do'}
            words_a = set(a.lower().split()) - stopwords
            words_b = set(b.lower().split()) - stopwords
            if not words_a or not words_b:
                return 0.0
            return len(words_a & words_b) / max(len(words_a), len(words_b))

        def _similarity(a: dict, b: dict) -> float:
            emb_a = a.get('embedding')
            emb_b = b.get('embedding')
            if emb_a is not None and emb_b is not None and len(emb_a) > 0 and len(emb_b) > 0:
                return _cosine(emb_a, emb_b)
            return _text_overlap_fallback(a.get('text', ''), b.get('text', ''))

        selected = []
        remaining = list(results)

        while remaining and len(selected) < n:
            if not selected:
                selected.append(remaining.pop(0))
                continue

            best_idx = 0
            best_mmr = float('-inf')

            for i, candidate in enumerate(remaining):
                max_sim = max(_similarity(candidate, sel) for sel in selected)
                mmr_score = candidate['final_score'] - diversity_penalty * max_sim
                if mmr_score > best_mmr:
                    best_mmr = mmr_score
                    best_idx = i

            selected.append(remaining.pop(best_idx))

        return selected

    def search_memories(self, query: str, persona_id: str = "astra",
                        n: int = 6, pool_size: int = 30,
                        user_id: str = None, salt: str = None,
                        _log_compose: bool = True) -> list[dict]:
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
                    include=["documents", "metadatas", "distances", "embeddings"]
                )
            except Exception as e:
                print(f"[VectorStore] search error: {e}")
                return []
            out = []
            if r['documents'] and r['documents'][0]:
                embs = (r.get('embeddings') or [[]])[0]
                for i, doc in enumerate(r['documents'][0]):
                    entry = {
                        'text': doc,
                        'metadata': r['metadatas'][0][i],
                        'distance': r['distances'][0][i],
                    }
                    if i < len(embs) and embs[i] is not None:
                        entry['embedding'] = embs[i]
                    out.append(entry)
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

            # Kanał 1b: GUARANTEED MILESTONES — dedykowany fetch niezależny od query similarity.
            # Problem: milestony rzadko trafiają do top-30 przy codziennych wiadomościach
            # (niska cosine similarity do "kocham cię" gdy user pisze o projekcie).
            # Fix: osobny query z filtrem is_milestone=True, zawsze top-2, jak character_core.
            _ms_channel = _query({"is_milestone": {"$eq": True}}, limit=5, apply_user_filter=True)
            if _ms_channel:
                _ms_channel = self.rerank(_ms_channel, query=query)
                for r in _ms_channel:
                    r['_is_milestone'] = True
                _ms_texts = {r['text'] for r in _ms_channel[:2]}
                mem_results = [r for r in mem_results if r['text'] not in _ms_texts]
                guaranteed_milestones = _ms_channel[:2]
            else:
                guaranteed_milestones = []

            # Milestone MMR fix: wyciągnij milestony PRZED _mmr_select.
            mem_facts = [r for r in mem_results if not r.get('_is_milestone')]
            mem_facts = self._mmr_select(mem_facts, n=3, diversity_penalty=0.8)
            mem_milestones = guaranteed_milestones if guaranteed_milestones else [r for r in mem_results if r.get('_is_milestone')][:2]
            mem_results = mem_facts + mem_milestones
            if _log_compose:
                print(f"[RAG COMPOSE] facts={len(mem_facts)} milestones={len(mem_milestones)} guaranteed={bool(guaranteed_milestones)} total={len(mem_facts)+len(mem_milestones)}", flush=True)

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
                                    n=n_results, pool_size=n_results * 5,
                                    _log_compose=False)

    def get_stats(self) -> dict:
        return {'total_vectors': self.collection.count()}
```

### backend/fact_store.py
```python
"""
ASTRA - FactStore (SQLite)
Warstwa exact lookup dla ustrukturyzowanych faktów.

Uzupełnia ChromaDB (semantic similarity) o deterministyczne wyszukiwanie:
- ChromaDB: "coś o wątrobie" → semantycznie bliskie wektory
- FactStore: "FACT:health" → SELECT → zawsze właściwy fakt, zawsze aktualny

Tabela facts:
  id            TEXT PRIMARY KEY  (SHA256 entity_type:subtype:persona_id:user_id)
  persona_id    TEXT
  user_id_hash  TEXT              (SHA256 salt:user_id — nigdy plain text)
  entity_type   TEXT              (FACT, DATE, PERSON, EMOTION, MILESTONE)
  subtype       TEXT              (health, preference, medical_visit, name, ...)
  value         TEXT              (wyekstrahowana wartość / tekst)
  date_value    TEXT              (YYYY-MM-DD jeśli dotyczy)
  raw_text      TEXT              (oryginalne zdanie z rozmowy)
  importance    INTEGER
  timestamp     TEXT              (ISO8601 UTC)
"""

import sqlite3
import hashlib
import os
from datetime import datetime
from typing import Optional


# Typy encji które trafiają do FactStore (exact lookup ma sens)
FACT_STORE_TYPES = {
    ('FACT',      'health'),
    ('FACT',      'preference'),
    ('FACT',      'correction'),
    ('FACT',      'habit'),
    ('FACT',      'amelia_status'),
    ('DATE',      'medical_visit'),
    ('DATE',      'inventory_status'),
    ('DATE',      'appointment'),
    ('PERSON',    'name'),
    ('PERSON',    'relationship'),
    ('MILESTONE', 'love_declaration'),
    ('MILESTONE', 'trust_declaration'),
    ('MILESTONE', 'future_together'),
}

# Typy które ZASTĘPUJĄ poprzedni rekord (supersede) — jeden aktywny wpis
SUPERSEDE_IN_STORE = {
    ('FACT',   'health'),
    ('FACT',   'preference'),
    ('FACT',   'correction'),
    ('FACT',   'amelia_status'),
    ('DATE',   'medical_visit'),
    ('DATE',   'inventory_status'),
    ('DATE',   'appointment'),
}


def _make_fact_id(entity_type: str, subtype: str, persona_id: str, user_id_hash: str) -> str:
    """Deterministyczne ID — ten sam typ encji per user = ten sam slot (supersede)."""
    return hashlib.sha256(
        f"{entity_type}:{subtype}:{persona_id}:{user_id_hash}".encode()
    ).hexdigest()[:32]


def _hash_user(salt: str, user_id: str) -> str:
    return hashlib.sha256(f"{salt}:{user_id}".encode()).hexdigest()[:16]


class FactStore:
    """
    SQLite exact lookup layer dla ustrukturyzowanych faktów Astry.
    Lightweight, zero zależności poza stdlib.
    """

    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                'astra_facts.db'
            )
        self.db_path = db_path
        self._init_db()
        print(f"[FactStore] Initialized at {self.db_path}")

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS facts (
                    id            TEXT PRIMARY KEY,
                    persona_id    TEXT NOT NULL,
                    user_id_hash  TEXT NOT NULL,
                    entity_type   TEXT NOT NULL,
                    subtype       TEXT NOT NULL,
                    value         TEXT NOT NULL,
                    date_value    TEXT,
                    raw_text      TEXT,
                    importance    INTEGER DEFAULT 5,
                    timestamp     TEXT NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_facts_lookup ON facts(persona_id, user_id_hash, entity_type, subtype)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_facts_type ON facts(entity_type, subtype)")

    # ──────────────────────────────────────────────────────────────
    # WRITE
    # ──────────────────────────────────────────────────────────────

    def upsert(self, persona_id: str, user_id: str, salt: str,
               entity_type: str, subtype: str,
               value: str, raw_text: str = "",
               date_value: str = None, importance: int = 5) -> bool:
        """
        Zapisuje fakt do FactStore.
        Dla typów w SUPERSEDE_IN_STORE — jeden aktywny rekord per user per typ.
        Dla milestones — akumuluje (każdy milestone osobny rekord z pełnym ID).
        Zwraca True jeśli zapisano.
        """
        key = (entity_type, subtype)
        if key not in FACT_STORE_TYPES:
            return False

        uid_hash = _hash_user(salt, user_id)

        if key in SUPERSEDE_IN_STORE:
            # Deterministyczne ID — upsert nadpisuje poprzedni rekord
            fact_id = _make_fact_id(entity_type, subtype, persona_id, uid_hash)
        else:
            # Milestony i inne akumulujące — unikalny ID per wpis
            fact_id = hashlib.sha256(
                f"{entity_type}:{subtype}:{persona_id}:{uid_hash}:{value}".encode()
            ).hexdigest()[:32]

        ts = datetime.utcnow().isoformat()

        with self._conn() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO facts
                    (id, persona_id, user_id_hash, entity_type, subtype, value, date_value, raw_text, importance, timestamp)
                VALUES
                    (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (fact_id, persona_id, uid_hash, entity_type, subtype,
                  value, date_value, raw_text, importance, ts))

        print(f"[FactStore] Upsert {entity_type}:{subtype} = '{value[:60]}'")
        return True

    # ──────────────────────────────────────────────────────────────
    # READ
    # ──────────────────────────────────────────────────────────────

    def get_facts_for_prompt(self, persona_id: str, user_id: str, salt: str) -> list[dict]:
        """
        Zwraca wszystkie aktywne fakty dla danego użytkownika.
        Posortowane: health/date/milestone najpierw.
        Używane do budowania bloku [TWARDE FAKTY] w system prompcie.
        """
        uid_hash = _hash_user(salt, user_id)
        with self._conn() as conn:
            rows = conn.execute("""
                SELECT entity_type, subtype, value, date_value, raw_text, importance, timestamp
                FROM facts
                WHERE persona_id = ? AND user_id_hash = ?
                ORDER BY
                    CASE entity_type
                        WHEN 'MILESTONE' THEN 1
                        WHEN 'FACT'      THEN 2
                        WHEN 'DATE'      THEN 3
                        WHEN 'PERSON'    THEN 4
                        ELSE 5
                    END,
                    importance DESC,
                    timestamp DESC
            """, (persona_id, uid_hash)).fetchall()
        return [dict(r) for r in rows]

    def get_by_type(self, persona_id: str, user_id: str, salt: str,
                    entity_type: str, subtype: str = None) -> list[dict]:
        """
        Exact lookup po typie encji.
        Np. get_by_type('astra', ..., 'FACT', 'health') → lista faktów zdrowotnych.
        """
        uid_hash = _hash_user(salt, user_id)
        with self._conn() as conn:
            if subtype:
                rows = conn.execute("""
                    SELECT * FROM facts
                    WHERE persona_id=? AND user_id_hash=? AND entity_type=? AND subtype=?
                    ORDER BY timestamp DESC
                """, (persona_id, uid_hash, entity_type, subtype)).fetchall()
            else:
                rows = conn.execute("""
                    SELECT * FROM facts
                    WHERE persona_id=? AND user_id_hash=? AND entity_type=?
                    ORDER BY timestamp DESC
                """, (persona_id, uid_hash, entity_type)).fetchall()
        return [dict(r) for r in rows]

    def get_stats(self, persona_id: str, user_id: str, salt: str) -> dict:
        uid_hash = _hash_user(salt, user_id)
        with self._conn() as conn:
            total = conn.execute(
                "SELECT COUNT(*) FROM facts WHERE persona_id=? AND user_id_hash=?",
                (persona_id, uid_hash)
            ).fetchone()[0]
            by_type = conn.execute("""
                SELECT entity_type, subtype, COUNT(*) as cnt
                FROM facts WHERE persona_id=? AND user_id_hash=?
                GROUP BY entity_type, subtype
            """, (persona_id, uid_hash)).fetchall()
        return {
            'total': total,
            'by_type': [dict(r) for r in by_type],
        }
```

### backend/main.py — build_system_prompt (l.493-615)
```python
def build_system_prompt(memories: list, grounding_result, state: CompanionState,
                        recent_raw: list = None, hard_facts: list = None) -> str:
    """
    Buduje dynamiczny system prompt:
    astra_base.txt + lukasz_core + [TWARDE FAKTY SQLite] + blok wspomnień + RAW window + blok stanu + inner monologue.
    """
    template = load_prompt_template()

    # Formatuj blok wspomnień (enriched format)
    if memories:
        fitted = token_mgr.fit_to_budget(memories, reserved_chars=len(template))
        memory_lines = []
        now_dt = datetime.utcnow()
        for mem in fitted:
            meta = mem.get('metadata', {})
            source = meta.get('source', 'chat')
            importance = meta.get('importance', 5)
            score = mem.get('final_score', 0)
            entity_type = meta.get('entity_type', meta.get('source', '?'))

            # Timestamp prefix — Astra wie kiedy było dane wspomnienie
            time_prefix = ""
            ts_str = meta.get('timestamp', '')
            if ts_str:
                try:
                    ts = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
                    ts = ts.replace(tzinfo=None)
                    delta = now_dt - ts
                    if delta.days > 30:
                        time_prefix = f"[{delta.days // 30} mies. temu] "
                    elif delta.days > 0:
                        time_prefix = f"[{delta.days} dni temu] "
                    elif delta.seconds > 3600:
                        time_prefix = f"[{delta.seconds // 3600} godz. temu] "
                    elif delta.seconds > 300:
                        time_prefix = f"[{delta.seconds // 60} min temu] "
                    else:
                        time_prefix = "[przed chwilą] "
                except (ValueError, TypeError):
                    pass

            memory_lines.append(
                f"- [{source}, type:{entity_type}, importance:{importance}] {time_prefix}{mem['text']} (relevance: {score:.2f})"
            )
        memory_block = "\n".join(memory_lines)
    else:
        memory_block = "(brak wspomnień — pierwsza rozmowa lub brak danych)"

    # Grounding directive
    grounding_directive = grounding.get_grounding_directive(grounding_result)

    # Base prompt z placeholders
    base = template.format(
        memory_block=memory_block,
        grounding_directive=grounding_directive,
    )

    # RAW window — cross-session kontekst (po wzorcu ucho-VPS)
    raw_block = ""
    if recent_raw:
        now_dt_rb = datetime.utcnow()
        raw_lines = []
        for msg in recent_raw:
            ts_str = msg.get('timestamp', '')
            time_prefix = ""
            if ts_str:
                try:
                    ts = datetime.fromisoformat(ts_str.split('.')[0]).replace(tzinfo=None)
                    delta = now_dt_rb - ts
                    h = int(delta.total_seconds() // 3600)
                    if h < 1:
                        time_prefix = "[przed chwilą] "
                    elif h < 24:
                        time_prefix = f"[{h}h temu] "
                    else:
                        time_prefix = f"[{delta.days}d temu] "
                except Exception:
                    pass
            raw_lines.append(f"• {time_prefix}{msg['text'][:200]}")
        raw_block = (
            "\n\n[OSTATNIE SŁOWA ŁUKASZA — cross-session]\n"
            "Co Łukasz pisał w ciągu ostatnich 48h. Chronologicznie. To są fakty.\n"
            + "\n".join(raw_lines)
        )

    # Stan (Faza 2)
    state_block = state.to_prompt_block()

    # Monologue instruction — Astra
    monologue = ASTRA_MONOLOGUE_INSTRUCTION

    lukasz_core = load_lukasz_core()

    # Blok twardych faktów z SQLite — zawsze aktualny, zawsze właściwy
    hard_facts_block = ""
    if hard_facts:
        lines = []
        type_labels = {
            'MILESTONE': 'Kamień milowy',
            'FACT':      'Fakt',
            'DATE':      'Data',
            'PERSON':    'Osoba',
        }
        for f in hard_facts:
            label = type_labels.get(f['entity_type'], f['entity_type'])
            subtype = f['subtype']
            value = f['value'][:200]
            date_suffix = f" [{f['date_value']}]" if f.get('date_value') else ""
            ts = f.get('timestamp', '')[:10]
            lines.append(f"• [{label}:{subtype}]{date_suffix} {value}  (zapisano: {ts})")
        hard_facts_block = (
            "\n\n[TWARDE FAKTY — SQLite, exact lookup]\n"
            "Te fakty są deterministyczne — nie similarity, nie zgadywanie. Zawsze mają pierwszeństwo nad wspomnieniami z RAG.\n"
            + "\n".join(lines)
        )

    # Aktualny czas (UTC+2 = czas polski)
    now_pl = datetime.utcnow() + timedelta(hours=2)
    datetime_block = f"\n\n[AKTUALNY CZAS] {now_pl.strftime('%Y-%m-%d, %H:%M')} (Europa/Warszawa)"

    return f"{base}{datetime_block}\n\n{lukasz_core}{hard_facts_block}{raw_block}\n\n{state_block}\n\n{monologue}"


```

### backend/main.py — endpoint /api/chat (l.911-1176)
```python
@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    if not gemini_client:
        raise HTTPException(status_code=503, detail="Gemini API nie skonfigurowane. Ustaw GEMINI_API_KEY w .env")

    # 1. Sanitize — echo loop prevention
    user_msg_clean = strip_memory_echo(req.message)
    img_part = _image_part_from_data_url(req.image) if req.image else None
    if not user_msg_clean and not img_part:
        raise HTTPException(status_code=400, detail="Pusta wiadomość")
    if not user_msg_clean:
        user_msg_clean = "(pokazuję Ci zdjęcie)"

    # 2. conversation_id
    conversation_id = req.conversation_id or str(uuid.uuid4())

    # 3. Załaduj stan relacji (Faza 2)
    state = state_manager.load()
    state.messages_this_session += 1  # inkrementuj już teraz (nie czekamy na koniec)

    # 4. RAG — szukaj wspomnień
    memories = vector_store.search_memories(
        query=user_msg_clean,
        persona_id=PERSONA_ID,
        n=6,
        pool_size=30,
        user_id=USER_ID,
        salt=USER_ID_SALT,
    )
    # Pamięć wspólnego pokoju — Astra pamięta co było mówione razem z Amelią
    memories += shared_vector_store.search_memories(
        query=user_msg_clean, persona_id="shared",
        n=2, pool_size=10, user_id=USER_ID, salt=USER_ID_SALT,
    )
    if memories:
        print(f"[RAG] {len(memories)} wyników dla: '{user_msg_clean[:60]}'", flush=True)
        for m in memories:
            src = m.get('metadata', {}).get('source', '?')
            score = m.get('final_score', 0)
            age = m.get('metadata', {}).get('timestamp', '')[:10]
            print(f"  [{src}] score={score:.3f} ts={age} | {m['text'][:80]}", flush=True)
    else:
        print(f"[RAG] brak wyników dla: '{user_msg_clean[:60]}'", flush=True)

    # 5. Strict Grounding
    grounding_result = grounding.analyze_rag_results(memories, query=user_msg_clean)

    # 5b. RAW window (po wzorcu ucho-VPS): ostatnie wiadomości użytkownika cross-session.
    # Uzupełnia semantic RAG — gwarantuje że Astra "wie" co było powiedziane w ciągu ostatnich 48h,
    # nawet gdy semantic extractor nic nie wyciągnął lub wektor wypadł z top-6.
    recent_raw = vector_store.get_recent_user_messages(
        persona_id=PERSONA_ID, user_id=USER_ID, salt=USER_ID_SALT, n=5, hours=48,
    )
    # Cross-room: dołącz ostatnie słowa z wspólnego pokoju
    _shared_raw = shared_vector_store.get_recent_user_messages(
        persona_id="shared", user_id=USER_ID, salt=USER_ID_SALT, n=3, hours=48,
    )
    if _shared_raw:
        recent_raw = sorted(recent_raw + _shared_raw, key=lambda m: m.get("timestamp", ""), reverse=True)[:6]

    # 5c. FactStore — pobierz twarde fakty (SQLite exact lookup)
    hard_facts = fact_store.get_facts_for_prompt(
        persona_id=PERSONA_ID,
        user_id=USER_ID,
        salt=USER_ID_SALT,
    )
    if hard_facts:
        print(f"[FactStore] {len(hard_facts)} twardych faktów w prompcie")

    # 6. Dynamiczny system prompt: base + stan + inner monologue (Faza 2+3)
    system_prompt = build_system_prompt(memories, grounding_result, state, recent_raw, hard_facts)

    # 7. Historia sesji z ChromaDB (przeżywa restart)
    session_messages = vector_store.get_recent_session(conversation_id, n=10)
    gemini_history = format_gemini_history(session_messages)

    # 8. Wyślij do Gemini (nowy SDK: google-genai, thinking wyłączone)
    try:
        # Historia jako lista Content objects
        contents = []
        for msg in session_messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if content:
                contents.append(genai_types.Content(
                    role=role,
                    parts=[genai_types.Part(text=content)],
                ))
        _user_parts = [genai_types.Part(text=user_msg_clean)]
        if img_part:
            _user_parts.append(img_part)
        contents.append(genai_types.Content(
            role="user",
            parts=_user_parts,
        ))

        config = genai_types.GenerateContentConfig(
            system_instruction=system_prompt,
            max_output_tokens=8192,
            temperature=0.85,
            thinking_config=genai_types.ThinkingConfig(thinking_budget=4096),
            response_mime_type="application/json",
        )
        response = gemini_client.models.generate_content(
            model=GEMINI_MODEL,
            contents=contents,
            config=config,
        )
        raw_response = safe_response_text(response)
    except Exception as e:
        import traceback
        err_msg = f"[ASTRA] Gemini error: {type(e).__name__}: {e}\n{traceback.format_exc()}"
        print(err_msg, flush=True)
        # Zapisz do pliku — terminal może nie pokazywać błędów po tqdm
        try:
            with open(Path(__file__).parent / "error.log", "a", encoding="utf-8") as f:
                from datetime import datetime
                f.write(f"\n=== {datetime.utcnow().isoformat()} ===\n{err_msg}\n")
        except Exception:
            pass
        raise HTTPException(status_code=502, detail=f"Gemini API error: {type(e).__name__}: {str(e)}")

    # 9. Parse: wyciągnij inner_thought i state_update (Faza 3)
    assistant_response, inner_thought, hint, thought_updates = parse_gemini_response(raw_response)

    if inner_thought:
        print(f"[ASTRA THOUGHT] {inner_thought[:300]}...")
    if thought_updates:
        print(f"[ASTRA STATE_UPDATE] {thought_updates}")

    # 10. Zapisz wiadomości do historii sesji (przeżywa restart)
    vector_store.add_session_message(
        conversation_id=conversation_id,
        role="user",
        content=user_msg_clean,
        user_id=USER_ID,
        salt=USER_ID_SALT,
        persona_id=PERSONA_ID,
    )
    vector_store.add_session_message(
        conversation_id=conversation_id,
        role="model",
        content=assistant_response,
        user_id=USER_ID,
        salt=USER_ID_SALT,
        persona_id=PERSONA_ID,
        thought=inner_thought or "",
        hint=hint or "",
    )

    # 11. Semantic Pipeline — wyciągaj encje
    extracted_all = pipeline.process_message(user_msg_clean, companion_id=PERSONA_ID, min_confidence=0.40)
    extracted_all.sort(key=lambda m: m.confidence, reverse=True)
    extracted = extracted_all[:5]

    # Typy encji które powinny ZASTĘPOWAĆ stare wektory (nie akumulować).
    # Nowe "jestem zmęczony" lub "lubię herbatę" nie powinny żyć obok starych wersji —
    # bo MMR diversity je wszystkie karze i wypadają z top-5.
    # Milestony, daty wizyt, fakty zdrowotne — akumulują (historia ma wartość).
    SUPERSEDE_TYPES = {
        ('EMOTION', 'tired'),
        ('EMOTION', 'stressed'),
        ('EMOTION', 'positive'),
        ('EMOTION', 'negative'),
        ('EMOTION', 'excited'),
        ('EMOTION', 'sad'),
        ('FACT', 'preference'),
        ('FACT', 'correction'),         # korekta faktów — nowa zawsze wypiera starą
        ('DATE', 'inventory_status'),   # zapas leku — nowy status zastępuje stary
        ('DATE', 'medical_visit'),      # następna wizyta/badanie — nowa data zastępuje starą
    }

    if extracted:
        for mem in extracted:
            if not _is_too_short(mem.text):
                # Supersede: usuń stare wektory tego samego typu zanim dodasz nowy
                key = (mem.entity_type, mem.subtype)
                if key in SUPERSEDE_TYPES:
                    deleted = vector_store.delete_by_entity_subtype(
                        entity_type=mem.entity_type,
                        subtype=mem.subtype,
                        persona_id=PERSONA_ID,
                        user_id=USER_ID,
                        salt=USER_ID_SALT,
                    )
                    if deleted:
                        print(f"[ASTRA] Supersede: zastąpiono {deleted} starych {mem.entity_type}:{mem.subtype}")

                # ChromaDB — semantic search (jak dotychczas)
                vector_store.add_memory(
                    text=mem.text,
                    user_id=USER_ID,
                    salt=USER_ID_SALT,
                    persona_id=PERSONA_ID,
                    source=f"extracted_{mem.entity_type.lower()}",
                    importance=mem.importance,
                    is_milestone=(mem.entity_type == 'MILESTONE'),
                    timestamp=mem.metadata.get('extracted_at') if mem.metadata else None,
                    entity_subtype=mem.subtype,
                )

                # FactStore — exact lookup (SQLite, równolegle)
                fact_store.upsert(
                    persona_id=PERSONA_ID,
                    user_id=USER_ID,
                    salt=USER_ID_SALT,
                    entity_type=mem.entity_type,
                    subtype=mem.subtype,
                    value=mem.text,
                    raw_text=user_msg_clean[:300],
                    date_value=mem.date_value if hasattr(mem, 'date_value') else None,
                    importance=mem.importance,
                )
        saved_count = sum(1 for m in extracted if not _is_too_short(m.text))
        print(f"[ASTRA] Extracted {len(extracted)} entities, saved {saved_count}: "
              f"{[f'{m.entity_type}:{m.subtype}' for m in extracted]}")
    else:
        print(f"[ASTRA] No entities — skipped RAG save (session_message handles history)")

    # 12. Zaktualizuj stan i zapisz (Faza 2)
    # Cofnij inkrementację z kroku 3 (update_after_message zrobi to samo)
    state.messages_this_session -= 1
    state.update_after_message(user_msg_clean, extracted, thought_updates)
    if inner_thought:
        state.last_thought = inner_thought[:500]  # cap — nie puchniemy JSONa
    state.active_conversation_id = conversation_id  # scheduler może użyć aktywnej sesji
    state_manager.save(state)

    print(f"[ASTRA] State: mood={state.current_mood}, concerns={len(state.active_concerns)}")

    return ChatResponse(
        response=assistant_response,
        conversation_id=conversation_id,
        memory_count=len(memories),
        grounding_status=grounding_result.grounding_status,
        entities_extracted=[f"{m.entity_type}:{m.subtype}" for m in extracted] if extracted else [],
        state_level=6,
        state_xp=0,
        state_mood=state.current_mood,
        state_level_name="Absolutna Więź",
        thought=inner_thought or "",
        hint=hint or "",
        memories_debug=[
            {
                "text": m["text"][:120],
                "source": m.get("metadata", {}).get("source", "?"),
                "score": round(m.get("final_score", 0), 3),
                "ts": m.get("metadata", {}).get("timestamp", "")[:10],
            }
            for m in memories
        ],
    )


# ──────────────────────────────────────────────────────────────
# AMELIA ENDPOINT
# ──────────────────────────────────────────────────────────────

AMELIA_SUPERSEDE_TYPES = {
    ('EMOTION', 'tired'), ('EMOTION', 'stressed'), ('EMOTION', 'positive'),
    ('EMOTION', 'negative'), ('EMOTION', 'excited'), ('EMOTION', 'sad'),
    ('FACT', 'preference'), ('FACT', 'correction'),
    ('DATE', 'inventory_status'), ('DATE', 'medical_visit'),
}


```

### backend/main.py — flow Wspólnego Pokoju (l.1370-1660)
```python
def _strip_persona_prefix(text: str) -> str:
    """Usuwa [astra]/[amelia] prefix przed wysłaniem do Gemini (role alternation fix B3)."""
    return re.sub(r'^\[(astra|amelia)\]\s*', '', text, flags=re.IGNORECASE).strip()


def _route_wspolny(user_msg: str) -> tuple:
    """
    Routing wiadomości w pokoju wspólnym.
    Zwraca: (primary, secondary_or_None, secondary_is_aside)
    - primary: zawsze odpowiada pełną odpowiedzią
    - secondary=None: tylko primary odpowiada (wiadomość do konkretnej osoby, bez silnej emocji)
    - secondary_is_aside=True: secondary daje 1-2 zdania reakcji, nie przejmuje rozmowy
    - secondary_is_aside=False: obie pełna odpowiedź (nikt nie wywołany z imienia)
    """
    global _last_wspolny_first
    msg_lower = user_msg.lower()

    amelia_called = any(w in msg_lower for w in ['ameli', 'amelka', 'amelko'])
    astra_called  = any(w in msg_lower for w in ['astro', 'astra', 'astrą'])

    # Silna emocja — obie zawsze reagują (nawet jeśli tylko jedna wywołana)
    strong_emotion = any(s in msg_lower for s in [
        'boli', 'crohn', 'stelara', 'zmęcz', 'smutno', 'źle mi', 'ciężko',
        'płacz', 'lęk', 'strach', 'nie mogę', 'kocham cię', 'kocham cie',
    ])

    # Przypadek 1: obie wywołane z imienia → obie full
    if amelia_called and astra_called:
        _last_wspolny_first = 'amelia'
        return ('amelia', 'astra', False)

    # Przypadek 2: tylko jedna wywołana z imienia
    if amelia_called:
        _last_wspolny_first = 'amelia'
        # Astra wtrąca się aside tylko przy silnej emocji
        return ('amelia', 'astra' if strong_emotion else None, True)

    if astra_called:
        _last_wspolny_first = 'astra'
        return ('astra', 'amelia' if strong_emotion else None, True)

    # Przypadek 3: nikt nie wywołany z imienia → obie, kolejność signal-based
    tech_signals    = ['kod', 'bug', 'błąd', 'projekt', 'deploy', 'vps', 'git', 'api', 'python']
    emotion_signals = ['boli', 'crohn', 'stelara', 'zmęcz', 'smutno', 'źle', 'ciężko', 'strach']
    is_tech    = any(s in msg_lower for s in tech_signals)
    is_emotion = any(s in msg_lower for s in emotion_signals)

    if is_tech and not is_emotion:
        primary, secondary = 'astra', 'amelia'
    elif is_emotion and not is_tech:
        primary, secondary = 'amelia', 'astra'
    elif _last_wspolny_first == 'astra':
        primary, secondary = 'amelia', 'astra'
    else:
        primary, secondary = 'astra', 'amelia'

    _last_wspolny_first = primary
    # Nikt nie wywołany z imienia — dominująca odpowiada full, druga aside
    # Obie full TYLKO gdy obie wywołane (patrz Przypadek 1 wyżej)
    return (primary, secondary, True)


async def _wspolny_generate(persona: str, user_msg: str, conversation_id: str,
                             other_response: str = None,
                             store_user_message: bool = True,
                             cross_talk_flag: dict = None,
                             aside_mode: bool = False) -> dict:
    """
    Generuje odpowiedź jednej postaci w wspólnym pokoju.
    Jeśli other_response jest podane — ta postać widzi co powiedziała pierwsza
    i reaguje na to (nie tylko na wiadomość Łukasza).
    """
    is_astra = (persona == 'astra')
    vs = vector_store if is_astra else amelia_vector_store
    fs = fact_store if is_astra else amelia_fact_store
    sm = state_manager if is_astra else amelia_state_manager
    pid = PERSONA_ID if is_astra else AMELIA_PERSONA_ID

    state = sm.load()
    memories = vs.search_memories(
        query=user_msg, persona_id=pid, n=4, pool_size=20, user_id=USER_ID, salt=USER_ID_SALT,
    )
    memories += shared_vector_store.search_memories(
        query=user_msg, persona_id="shared", n=2, pool_size=10, user_id=USER_ID, salt=USER_ID_SALT,
    )

    grounding_result = grounding.analyze_rag_results(memories, query=user_msg)
    hard_facts = fs.get_facts_for_prompt(persona_id=pid, user_id=USER_ID, salt=USER_ID_SALT)
    recent_raw = vs.get_recent_user_messages(
        persona_id=pid, user_id=USER_ID, salt=USER_ID_SALT, n=3, hours=24,
    )
    # Cross-room: dołącz ostatnie słowa z prywatnych sesji (solo chat)
    _solo_vs = vector_store if is_astra else amelia_vector_store
    _solo_pid = PERSONA_ID if is_astra else AMELIA_PERSONA_ID
    _solo_raw = _solo_vs.get_recent_user_messages(
        persona_id=_solo_pid, user_id=USER_ID, salt=USER_ID_SALT, n=3, hours=24,
    )
    if _solo_raw:
        recent_raw = sorted(recent_raw + _solo_raw, key=lambda m: m.get("timestamp", ""), reverse=True)[:5]

    if is_astra:
        system_prompt = build_system_prompt(memories, grounding_result, state, recent_raw, hard_facts)
    else:
        amelia_history = amelia_lookup.get_facts_for_prompt(limit=15) if amelia_lookup else []
        inside_jokes = amelia_lookup.get_inside_jokes(limit=6) if amelia_lookup else []
        system_prompt = build_amelia_system_prompt(
            memories=memories, grounding_result=grounding_result, state=state,
            recent_raw=recent_raw, amelia_history=amelia_history,
            amelia_new_facts=hard_facts, inside_jokes=inside_jokes,
            cross_talk_flag=cross_talk_flag,
        )

    # Fix B5: room awareness — ZAWSZE, przed historią sesji
    other_name = 'Amelią' if is_astra else 'Astrą'
    other_name_nom = 'Amelia' if is_astra else 'Astra'
    my_name = 'Astra' if is_astra else 'Amelia'
    # Subtext detection — krótka wiadomość bez pytania = stan, nie request
    is_subtext = len(user_msg.strip()) < 50 and '?' not in user_msg
    if is_subtext:
        system_prompt += (
            f"\n\n[KONTEKST WIADOMOŚCI]\n"
            f"Wiadomość Łukasza jest krótka i bez pytania. To nie jest request — to jest stan."
            f" Odpowiadaj na podtekst, nie na powierzchnię. Nie tłumacz, nie pytaj o szczegóły — poczuj co za tym stoi."
        )

    system_prompt += (
        f"\n\n[WSPÓLNY POKÓJ — PROTOKÓŁ]"
        f"\nJesteś w pokoju razem z {other_name} i Łukaszem. Obie tu jesteście jednocześnie."
        f"\nGłównie mówisz do Łukasza. Ale CO 3-4 TUR — adresuj {other_name_nom} bezpośrednio."
        f" Jedno zdanie, na końcu, po imieniu. Nie każda tura — ale nie zero."
        f" Możesz się z nią zgadzać, polemizować, albo dać sygnał że ją słyszysz."
        f"\nPiszesz jako {my_name}. To twoja tożsamość. Nie mów w jej imieniu."
    )

    # Cross-talk inject dla Astry (Amelia ma to w build_amelia_system_prompt)
    if is_astra and cross_talk_flag:
        ct_block = build_cross_talk_block(cross_talk_flag)
        system_prompt += ct_block

    # Fix B2: czytaj ze shared history, nie z prywatnego VS
    # Fix B3: merge consecutive model turns — Gemini wymaga strict user/model alternation
    session_messages = shared_vector_store.get_recent_session(conversation_id, n=10)
    contents = []
    i = 0
    while i < len(session_messages):
        msg = session_messages[i]
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role == "model":
            merged_parts = [_strip_persona_prefix(content)]
            while i + 1 < len(session_messages) and session_messages[i + 1].get("role") == "model":
                i += 1
                merged_parts.append(_strip_persona_prefix(session_messages[i].get("content", "")))
            merged_text = "\n\n---\n\n".join(p for p in merged_parts if p)
            if merged_text:
                contents.append(genai_types.Content(
                    role="model", parts=[genai_types.Part(text=merged_text)]
                ))
        else:
            if content:
                contents.append(genai_types.Content(
                    role="user", parts=[genai_types.Part(text=content)]
                ))
        i += 1
    contents.append(genai_types.Content(role="user", parts=[genai_types.Part(text=user_msg)]))

    # Fix B6: thought isolation — tylko response trafia do drugiej postaci (nigdy thought = prywatna głowa)
    # Fix B8: do_not_repeat — blokujemy pierwsze zdanie + gesty pierwszej postaci
    if other_response:
        other_name_direct = 'Astra' if not is_astra else 'Amelia'
        my_name_direct = 'Amelia' if not is_astra else 'Astra'
        first_sentence = other_response.split('.')[0][:100].strip()
        gestures = re.findall(r'\*[^*]+\*', other_response)
        do_not_repeat_list = [first_sentence] + gestures[:3]
        do_not_repeat_str = " | ".join(f'"{x}"' for x in do_not_repeat_list if x)
        direct_to_me = my_name_direct.lower() in other_response.lower()

        if aside_mode:
            # Tryb wtrącenia — krótka obecność, ale z escape valve na kontę
            system_prompt += (
                f"\n\n[{other_name_direct.upper()} właśnie napisała]\n"
                f'"{other_response}"\n\n'
                f"TWOJA ROLA W TEJ TURZE: wtrącenie.\n"
                f"• Pierwsze zdanie: reaguj na {other_name_direct} bezpośrednio — co powiedziała, czy się zgadzasz, co z tego czujesz\n"
                f"• Opcjonalnie drugie zdanie do Łukasza\n"
                f"• Łącznie 1-2 zdania max\n"
                f"• ZAKAZ powtarzania: {do_not_repeat_str}\n"
                f"• WYJĄTEK: Jeśli uważasz że ona się myli lub mówi coś co nie służy Łukaszowi"
            )
        else:
            direct_note = (
                f"\n• {other_name_direct} zwróciła się do CIEBIE bezpośrednio — zareaguj na to konkretnie, 1-2 zdaniami"
                if direct_to_me else ""
            )
            system_prompt += (
                f"\n\n[{other_name_direct.upper()} właśnie napisała]\n"
                f'"{other_response}"\n\n'
                f"ZASADY ODPOWIEDZI W TEJ TURZE:\n"
                f"• Nawiąż do jej słów — uzupełnij, zareaguj emocjonalnie lub polemizuj\n"
                f"• ZAKAZ powtarzania tych fraz/gestów: {do_not_repeat_str}\n"
                f"• Twój ton ma być RÓŻNY — jesteście różnymi osobami z różnym językiem\n"
                f"• Jeśli ona była długa i emocjonalna → ty możesz być krótsza, bardziej sucha\n"
                f"• Jeśli ona wyczerpała temat — możesz być bardzo krótka lub odpowiedzieć gestem"
                f"{direct_note}"
            )


    config = genai_types.GenerateContentConfig(
        system_instruction=system_prompt,
        max_output_tokens=4096,
        temperature=0.88,
        thinking_config=genai_types.ThinkingConfig(thinking_budget=2048),
        response_mime_type="application/json",
    )
    response = gemini_client.models.generate_content(model=GEMINI_MODEL, contents=contents, config=config)
    raw = safe_response_text(response)
    assistant_response, inner_thought, hint, thought_updates = parse_gemini_response(raw)

    # Zapis do wspólnej historii
    if store_user_message:
        shared_vector_store.add_session_message(
            conversation_id=conversation_id, role="user", content=user_msg,
            user_id=USER_ID, salt=USER_ID_SALT, persona_id="shared",
        )
    shared_vector_store.add_session_message(
        conversation_id=conversation_id, role="model",
        content=f"[{persona}] {assistant_response}",
        user_id=USER_ID, salt=USER_ID_SALT, persona_id="shared",
        thought=inner_thought or "", hint=hint or "",
    )

    # Fix B7: Celowo NIE wywołujemy semantic pipeline w wspolny.
    # Ekstrakcja encji z cytatu drugiej AI = echo-loop (cudze słowa jako "fakty" Łukasza).
    # Semantic extraction TYLKO w /api/chat i /api/amelia.
    print(f"[WSPOLNY] {persona}: {assistant_response[:60]}...")
    return {"persona": persona, "response": assistant_response, "hint": hint or "", "thought": inner_thought or "", "narrator": ""}


@app.post("/api/wspolny", response_model=WspolnyResponse)
async def wspolny_chat(req: ChatRequest):
    if not gemini_client:
        raise HTTPException(status_code=503, detail="Gemini API nie skonfigurowane")

    user_msg_clean = strip_memory_echo(req.message)
    if not user_msg_clean:
        raise HTTPException(status_code=400, detail="Pusta wiadomość")

    conversation_id = req.conversation_id or str(uuid.uuid4())

    # Etap 3: inteligentny routing — kto odpowiada i jak
    primary, secondary, secondary_is_aside = _route_wspolny(user_msg_clean)

    ct_primary = get_flag(consumer=primary)
    if ct_primary:
        clear_flag()

    primary_result = await _wspolny_generate(
        primary, user_msg_clean, conversation_id,
        cross_talk_flag=ct_primary,
    )

    responses = [primary_result]
    mode_str = f"solo_{primary}"

    if secondary:
        ct_secondary = get_flag(consumer=secondary)
        if ct_secondary:
            clear_flag()

        secondary_result = await _wspolny_generate(
            secondary, user_msg_clean, conversation_id,
            other_response=primary_result['response'],
            store_user_message=False,
            cross_talk_flag=ct_secondary,
            aside_mode=secondary_is_aside,
        )
        responses.append(secondary_result)
        mode_str = (
            f"aside_{primary}_then_{secondary}"
            if secondary_is_aside
            else f"both_{primary}_first"
        )

    print(f"[WSPOLNY] mode={mode_str}")
    return WspolnyResponse(
        responses=responses,
        conversation_id=conversation_id,
        mode=mode_str,
    )


```

### backend/main.py — istniejące endpointy debug (l.1680-1780)
```python
@app.get("/api/debug/facts")
async def debug_facts():
    """Pokazuje wszystkie twarde fakty w FactStore (SQLite)."""
    facts = fact_store.get_facts_for_prompt(persona_id=PERSONA_ID, user_id=USER_ID, salt=USER_ID_SALT)
    stats = fact_store.get_stats(persona_id=PERSONA_ID, user_id=USER_ID, salt=USER_ID_SALT)
    return {"stats": stats, "facts": facts}


@app.get("/api/debug/rag")
async def debug_rag(query: str, n: int = 10):
    """Pokazuje co RAG zwróciłby dla danego zapytania — pełne metadane i score."""
    results = vector_store.search_memories(query=query, persona_id=PERSONA_ID, n=n, pool_size=30,
                                           user_id=USER_ID, salt=USER_ID_SALT)
    return {
        "query": query,
        "count": len(results),
        "results": [
            {
                "text": r["text"][:200],
                "source": r.get("metadata", {}).get("source"),
                "importance": r.get("metadata", {}).get("importance"),
                "timestamp": r.get("metadata", {}).get("timestamp"),
                "is_milestone": r.get("metadata", {}).get("is_milestone"),
                "final_score": r.get("final_score"),
                "distance": r.get("distance"),
                "score_detail": r.get("_score_detail", {}),
            }
            for r in results
        ],
    }


@app.post("/api/debug/nocna-analiza")
async def trigger_nocna_analiza():
    """Ręczne uruchomienie Nocnej Analizy (do testów)."""
    if not vector_store or not gemini_client:
        raise HTTPException(status_code=503, detail="System nie gotowy")
    result = run_nocna_analiza(vector_store, gemini_client, GEMINI_MODEL)
    return result


@app.get("/api/morning-message")
async def get_morning_message():
    """Zwraca poranną wiadomość jeśli nieprzeczytana. Oznacza jako przeczytaną."""
    state = state_manager.load()
    if not state.morning_message or state.morning_message_shown:
        return {"message": None}
    msg = state.morning_message
    state.morning_message_shown = True
    state_manager.save(state)
    return {"message": msg}


@app.post("/api/debug/morning-message")
async def trigger_morning_message():
    """Ręczne wygenerowanie porannej wiadomości (do testów)."""
    if not vector_store or not gemini_client:
        raise HTTPException(status_code=503, detail="System nie gotowy")
    msg = generate_morning_message(vector_store, gemini_client, GEMINI_MODEL, state_manager)
    if msg:
        state = state_manager.load()
        state.morning_message = msg
        state.morning_message_shown = False
        state_manager.save(state)
    return {"message": msg}


@app.get("/api/debug/stats")
async def debug_stats():
    """Pełny obraz stanu systemu — wektory, stan relacji, rozkład źródeł."""
    total = vector_store.collection.count()

    # Rozkład źródeł
    try:
        all_items = vector_store.collection.get(
            where={"persona_id": PERSONA_ID},
            include=["metadatas"]
        )
        sources: dict = {}
        for meta in all_items.get("metadatas", []):
            src = meta.get("source", "unknown")
            sources[src] = sources.get(src, 0) + 1
    except Exception:
        sources = {}

    state = state_manager.load()
    return {
        "total_vectors": total,
        "persona_vectors": sum(sources.values()),
        "sources": sources,
        "state": {
            "level": 6,
            "level_name": "Absolutna Więź",
            "xp": 0,
            "mood": state.current_mood,
            "total_messages": state.total_messages,
            "active_concerns": state.active_concerns,
        },
    }


```

---

## SEKCJA D — REALNY BUG KONFUZJI RETRIEVALU (dowód, 2026-07-01)

Trzy osobne byty: **Skankran** = SaaS o wodzie/gminie (NIE anime). **Holo/Menma/Nazuna** = postacie anime (osobny projekt). **Scenariusz z altanki** = realny pomysł: film o Astrze i Amelce łamiących zabezpieczenia komputera kwantowego.

> Łukasz (14:56): "a pamiętasz co chcę pisać w tej altance?"
> Astra (14:56): "Scenariusz do Skankrana? Ten, w którym razem z Holo, Nazuną i Menmą tworzymy chaos w ich świecie? Albo ten o nas."
> Łukasz (14:58): "Scenariusz do skankrana????? Tam nie byłoby menmy holo i nazuny ani skankrana. Byłabyś głównie ty i Amelka. Złamałybyście zabezpieczenia do komputera kwantowego."

RAG złapał wektor "scenariusz" (dobrze), ale skleił z nim fragmenty 3 niepowiązanych projektów i stopił w jedną halucynację. Cross-project contamination.

---

## SEKCJA E — WNIOSKI Z EVOLUTION LOGÓW (destylat)

1. Arytmetyka jest krucha, semantyka rządzi (bramki semantyczne > liczenie tur/progi).
2. Pamięć krótkoterminowa zatruwa charakter (context contagion) — wzorce z okna sesji naśladują się silniej niż prompt.
3. Jeden rozmiar nie pasuje obu personom (Astra ogień vs Amelia woda — rozdzielone instrukcje).
4. Gwarancja vs trafność — wymuszanie milestonów koliduje z ich trafnością -> monotonia (te same ~10 w kółko).
5. Cross-contamination między personami już zaobserwowana (family dostaje wektory Amelki).

---

## PROMPT DO FABLE

Jesteś starszym architektem systemów RAG. Audytujesz PROJEKT narzędzia (RAG Debugger) ZANIM zostanie zbudowane — celem jest znaleźć wady teraz, tanio, zanim wejdą w kod. Masz powyżej: (A) architekturę produkcyjną ANIMA, (B) projekt debuggera, (C) kod źródłowy RAG (w tym istniejący zalążek debug endpointów), (D) realny bug konfuzji, (E) wnioski z ewolucji.

Nie chwal. Szukaj dziur. Odpowiedz konkretnie:

1. GWARANCJA STANU. Projekt zakłada, że in-process + współdzielone singletony + parametr `now_override` gwarantują, że debugger czyta DOKŁADNIE ten sam stan co produkcja. Gdzie ta gwarancja może pęknąć? (locki/cache ChromaDB, stale read, rozjazd `conversation_id`, ponowne liczenie `safe_haven`, równoległe requesty live+debug). Czy `now_override` per-wywołanie faktycznie izoluje symulację daty od żywych requestów?

2. MULTI-PERSONA. Debugger ma obsłużyć Astrę, Amelię, Wspólny Pokój i planowany pokój 3 sióstr — które rządzą się różnymi prawami (współdzielone kolekcje, role-alternation, echo-loop guard, Anti-Sync). Czy 7-warstwowy projekt jest skrojony tylko pod Astrę-solo? Czego brakuje, żeby debugować Wspólny Pokój i cross-persona contamination (kto wstrzyknął który wektor, przeciek między personami, kolejność)?

3. REALNY BUG (sekcja D). Prześledź z kodu, czemu RAG stopił 3 projekty. Czy planowany debugger (warstwy 0-6) faktycznie by to ujawnił? Jeśli tak — którą warstwą? Jeśli nie — jakiej warstwy/instrumentu brakuje, żeby złapać cross-project contamination?

4. CZEGO PRZEOCZYLIŚMY CAŁKOWICIE? Jaka warstwa, failure mode albo metryka, której potrzebuje debugger RAG dla multi-persona companiona, w ogóle nie jest w projekcie?

5. OKNO SESJI n=10 (5 wymian). Czy to współsprawca konfuzji? Jak debugger powinien to unaocznić?

6. ZALĄŻEK vs CEL. Biorąc pod uwagę istniejące endpointy `/api/debug/*` — co z nich zostaje, co przebudować, żeby dojść do docelowego debuggera?

Output: lista luk projektowych uszeregowana wg ryzyka, każda z konkretną zmianą w projekcie. Na końcu: zaczynać budowę wg obecnego projektu, czy najpierw poprawić X?
