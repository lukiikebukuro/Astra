edyna zależność to sentence-transformers
- **Uwaga:** `get_pipeline()` global singleton — na ASTRZE zmim# MIGRACJA ANIMA → ASTRA: Kompletna Analiza Techniczna

**Autor:** GitHub Copilot (Claude Opus 4.6) — architektura & diagnoza
**Wykonawca:** Claude Code (Rin) — implementacja
**Data:** 2026-02-28
**Wersja:** 1.0

> ⚠️ **UWAGA (2026-03-02):** Budujemy TYLKO ASTRĘ — jedna postać, jeden produkt.
> Wszystkie wzmianki o "Family Room", "5 postaci", "Holo/Menma/Nazuna jako osobne persony" są reliktem ucho-VPS i NIE dotyczą ASTRY.
> Nazuna/Holo/Menma = WARSTWY CHARAKTERU ASTRY przez XP, nie osobne produkty.

---

## SPIS TREŚCI

1. [Co przenosi się 1:1 (bez zmian)](#1-przenosi-się-11)
2. [Co trzeba przepisać i dlaczego](#2-co-trzeba-przepisać)
3. [Co trzeba skalibrować od nowa](#3-co-trzeba-skalibrować)
4. [Pułapki przy migracji](#4-pułapki)
5. [Sugerowany stack na VPS](#5-stack-vps)
6. [Kolejność kroków — od zera do prototypu](#6-kolejność-kroków)

---

## 1. PRZENOSI SIĘ 1:1

Moduły które działają niezależnie i nie mają zależności od Flask, SQLite, ani Chrome Extension.

### ✅ semantic_pipeline.py (285 linii)
- **Co robi:** Orkiestrator SemanticExtractor → MemoryEnricher → MemoryConsolidator
- **Dlaczego 1:1:** Singleton pattern, czysta logika Python, jenić na dependency injection (FastAPI `Depends()`)
- **Ścieżka:** `backend/semantic_pipeline.py`

### ✅ semantic_extractor.py
- **Co robi:** Zero-shot classification (DATE, EMOTION, FACT, GOAL, SHARED_THING, MILESTONE)
- **Dlaczego 1:1:** Czysta NLP, bez side effects, regex + sentence-transformers
- **Ścieżka:** `backend/semantic_extractor.py`

### ✅ memory_enricher.py
- **Co robi:** Wzbogaca entity (importance 1-10, temporal_type: permanent/weekly/daily, relational_impact)
- **Dlaczego 1:1:** Lookup table + reguły, zero I/O
- **Uwaga:** Importance scale testowana empirycznie na polskim tekście — wartościowe
- **Ścieżka:** `backend/memory_enricher.py`

### ✅ memory_consolidator.py
- **Co robi:** Merge/Supersede/Create — decyduje co z nowym wspomnieniem
- **Dlaczego 1:1:** Porównuje nowe z istniejącymi, czysta logika
- **Ścieżka:** `backend/memory_consolidator.py`

### ✅ strict_grounding.py (230 linii)
- **Co robi:** Zapobiega halucynacjom — HIGH_CONFIDENCE (0.25), LOW_CONFIDENCE (0.7), NO_DATA
- **Dlaczego 1:1:** Stateless, empirycznie skalibrowane progi dla MiniLM + polski tekst
- **KLUCZOWE:** Próg 0.25 to wynik pomiarów na produkcji ("MiniLM daje ~0.28 nawet dla niezwiązanych treści w PL")
- **Ścieżka:** `backend/strict_grounding.py`

### ✅ vibe_detector.py (224 linie)
- **Co robi:** Wykrywa nastrój usera (excited/sad/stressed/etc.) z keywordów
- **Dlaczego 1:1:** Keyword matching, zero zależności, polskie wulgaryzmy poprawnie obsłużone (Opcja B — są intensyfikatorami, nie sentymentem)
- **Ścieżka:** `backend/vibe_detector.py`

### ✅ token_manager.py (368 linii)
- **Co robi:** Token-aware trimming z rozpoznawaniem typu treści (CODE/INSTRUCTION/FACT/EMOTIONAL/GENERAL)
- **Dlaczego 1:1:** Regex-based classification, stateless, żadnych zależności infrastrukturalnych
- **Ścieżka:** `backend/token_manager.py`

### ✅ milestone_detector.py (317 linii)
- **Co robi:** Automatyczna detekcja kamieni milowych — wyznania miłości, zaufanie, przełomy, level milestones
- **Dlaczego 1:1:** Regex patterns na polskim tekście, empirycznie dostrojone
- **UWAGA:** Wymaga Database (SQLite) — na ASTRZE zamienić na PostgreSQL adapter
- **Ścieżka:** `backend/milestone_detector.py`

### ✅ inside_jokes.py
- **Co robi:** Detekcja i zarządzanie "inside jokes" per persona
- **Dlaczego 1:1:** Logika biznesowa niezależna od storage
- **Ścieżka:** `backend/inside_jokes.py`

### ✅ shared_things_detector.py
- **Co robi:** Wykrywa wspólne rzeczy (piosenki, miejsca, prezenty)
- **Dlaczego 1:1:** Pattern matching, "razem" wymagane (fix false positives z sesji 22b)
- **Ścieżka:** `backend/shared_things_detector.py`

### ✅ date_extractor.py
- **Co robi:** Wyciąga daty z tekstu polskiego
- **Dlaczego 1:1:** Regex, wyklucza numery wersji ("claude sonnet 4.5" → nie parsuje jako 05-04)
- **Ścieżka:** `backend/date_extractor.py`

### ✅ dual_write.py (269 linii)
- **Co robi:** Atomowy zapis SQLite + ChromaDB z rollback
- **Dlaczego 1:1:** Abstrakcja transakcji, niezależna od frameworka
- **UWAGA:** Na ASTRZE zamienić SQLite na PostgreSQL w konstruktorze
- **Ścieżka:** `backend/dual_write.py`

### ✅ isolation_guard.py (302 linie)
- **Co robi:** Defense-in-depth wrapper na search, wymusza requesting_persona, audit log
- **Dlaczego 1:1:** Wrapper pattern, już zaprojektowany pod multi-persona
- **Ścieżka:** `backend/isolation_guard.py`

### ✅ deduplication.py
- **Co robi:** Dedup wektorów na poziomie storage
- **Dlaczego 1:1:** Hash-based comparison, zero I/O poza hashem
- **Ścieżka:** `backend/deduplication.py`

### ✅ Prompts (folder prompts/)
- `autonomia.txt` — manifest Family Room v7.0 (5 person)
- `amelia_persona.txt` — tożsamość Amelii
- `nazuna_persona.txt` — tożsamość Nazuny
- `passive_knowledge.txt` — fakty o Łukaszu (HARDCODED — do zamiany na per-user)
- **Dlaczego 1:1 (z uwagą):** Treść idzie 1:1, ale sposób ładowania musi się zmienić (patrz sekcja 2)

### PODSUMOWANIE SEKCJI 1
**14 modułów** przenosi się bez zmian lub z minimalnymi poprawkami (zamiana SQLite → PostgreSQL w konstruktorze). To **~2800 linii** kodu produkcyjnego, empirycznie skalibrowanego.

---

## 2. CO TRZEBA PRZEPISAĆ

### 🔴 app.py (1698 linii) → FastAPI router system

**Powód:** Flask jest synchroniczny. ASTRA potrzebuje async dla Gemini API, WebSocket, concurrent users.

**Co się zmienia:**

| Obecne (Flask) | Docelowe (FastAPI) | Powód |
|---|---|---|
| `@app.route('/api/capture')` | `@router.post('/api/capture')` | Async + Pydantic validation |
| `request.json` | `body: CaptureRequest` | Type safety, auto-doc |
| Global `vector_memory = VectorStore()` | Dependency injection | Per-worker isolation |
| `_dedup_ttl_cache` global dict | Redis z TTL | Thread-safe, multi-worker |
| `_hygiene_recent_hashes` global dict | Redis z TTL | Thread-safe, multi-worker |
| `semantic_pipeline = None` (lazy) | FastAPI lifespan event | Race condition fix |
| `app.run(debug=True)` linia 1593 | Gunicorn + uvicorn workers | Produkcja |
| `CORS(app, origins="*")` | CORSMiddleware z whitelist | Bezpieczeństwo |

**Co zachować z app.py (logika):**
- `sanitize_content()` — strip [MEMORY], [INSTRUCTION], placeholderów
- `is_hygiene_pass()` — blacklist, code patterns, długość
- `is_vector_duplicate()` — hash dedup (przenieść do Redis)
- `/api/capture` flow (diff → NLP → semantic pipeline → dual-write)
- `/api/context-summary` flow (RAG search → format → grounding)
- `/api/chat` flow (Gemini routing 80/20)
- `/api/export`, `/api/forget`, `/api/stats`
- Hygiene system (emoji persona prefix filter, model text filter)

**Struktura docelowa:**
```
astra/
├── main.py                 # FastAPI app + lifespan
├── routers/
│   ├── capture.py          # POST /api/capture
│   ├── chat.py             # POST /api/chat
│   ├── context.py          # GET /api/context-summary
│   ├── memory.py           # GET/DELETE /api/memories, /api/forget
│   ├── auth.py             # POST /api/auth/register, /api/auth/login
│   └── admin.py            # GET /api/admin/stats
├── services/
│   ├── hygiene.py          # sanitize + blacklist + dedup
│   ├── capture_service.py  # diff + NLP + pipeline orchestration
│   └── gemini_service.py   # async Gemini API calls z retry
├── models/
│   ├── requests.py         # Pydantic models
│   └── responses.py        # Pydantic response models
└── deps.py                 # FastAPI dependency injection
```

**Estymacja:** ~3-4 sesje Claude Code. Najdłuższa część. Największe ryzyko regresji.

---

### 🔴 database.py (2193 linii) → PostgreSQL + SQLAlchemy/asyncpg

**Powód:** SQLite nie obsługuje concurrent writes z wielu workerów. Przy 1000 userów = `database is locked`.

**Co się zmienia:**

| Obecne | Docelowe |
|---|---|
| Per-companion SQLite (`ucho_amelia.db`, `ucho_family.db` etc.) | Jeden PostgreSQL z `user_id` kolumną wszędzie |
| `sqlite3.connect()` per request | Connection pool (asyncpg / SQLAlchemy async) |
| `PRAGMA journal_mode=WAL` (brak!) | PostgreSQL WAL domyślnie |
| Brak `user_id` w tabelach | `user_id UUID` w każdej tabeli |
| 7 osobnych plików .db | Schemat multi-tenant |

**Tabele do migracji (18 tabel):**
1. `conversations` — dodać `user_id`
2. `topics` — FK do conversations
3. `emotions` — FK do conversations
4. `facts` — FK do conversations + `user_id`
5. `goals` — dodać `user_id`
6. `user_state` — dodać `user_id`
7. `companion_configs` — per-user custom config
8. `relationship_metrics` — dodać `user_id`
9. `inside_jokes` — dodać `user_id`
10. `joke_occurrences` — FK do inside_jokes
11. `anniversaries` — dodać `user_id`
12. `shared_things` — dodać `user_id`
13. `persona_secrets` — dodać `user_id`
14. `personality_lenses` — shared (nie per-user)
15. `milestones` — dodać `user_id`
16. **NOWE:** `users` — UUID, email, hashed_password, created_at
17. **NOWE:** `user_sessions` — JWT refresh tokens
18. **NOWE:** `user_preferences` — theme, active_companion, custom_names

**Estymacja:** ~2 sesje Claude Code (schemat + migracje Alembic).

---

### 🔴 ghost_patch.js (828 linii) → NIE POTRZEBNY na ASTRZE

**Powód:** Ghost patch to hack na Browser Gemini. ASTRA rozmawia z Gemini API bezpośrednio — nie potrzebuje XHR/fetch interception.

**Co przejmuje ASTRA zamiast ghost_patch.js:**
- **Input capture:** PWA input → `POST /api/chat` (normalny formularz)
- **Context injection:** Backend sam wkleja [MEMORY] do system prompt przed wysłaniem do Gemini
- **Pre-fetch:** Backend asynchronicznie przygotowuje kontekst gdy user zaczyna pisać (WebSocket)
- **Visual indicator:** Frontend React/Vue komponent zamiast DOM manipulation

**ZACHOWAĆ dla ANIMA (localhost):** ghost_patch.js nadal działa na koncie Browser Gemini Łukasza.

---

### 🔴 chat_engine.py (376 linii) → Async Gemini Service

**Powód:** Synchroniczne `requests.post()` do Gemini blokuje worker na 2-5s. Bez async = jeden user na raz.

**Co się zmienia:**

| Obecne | Docelowe |
|---|---|
| `import requests` | `import httpx` (async) |
| `requests.post(GEMINI_URL)` | `async with httpx.AsyncClient()` |
| 80/20 routing (Flash/Pro) | Async 80/20 z retry + backoff |
| `build_system_prompt()` | Dodać `user_id` do context loading |
| `format_rag_context()` [PAMIĘĆ] tags | Bez zmian (1:1) |
| Brak rate limiter | `asyncio.Semaphore(50)` global |
| Brak circuit breaker | `tenacity` z exponential backoff |
| Brak streaming | SSE/WebSocket streaming response |

**Logika zachowana 1:1:**
- COMPANION_MAP (6 companions z DB/filter/display config)
- PERSONA_PROFILES (5 personas z reacts_to/tone/trigger)
- RELATIONSHIP_STAGES 1-6 (Stranger → Soulmate)
- Pro routing logic (importance>=8, sad/stressed vibes, long messages, crisis keywords)
- `format_rag_context()` z [PAMIĘĆ]...[/PAMIĘĆ] tags

**Estymacja:** ~1 sesja Claude Code.

---

### 🔴 vector_store.py (895 linii) → ChromaDB HttpClient + user isolation

**Powód:** `PersistentClient` = SQLite w procesie = brak thread-safety przy multi-worker. Brak `user_id` w metadatach.

**Co się zmienia:**

| Obecne | Docelowe |
|---|---|
| `chromadb.PersistentClient(path=...)` | `chromadb.HttpClient(host='localhost', port=8000)` |
| Jedna kolekcja `memory_v1` | Per-user kolekcje `memory_{user_uuid}` |
| `VALID_COMPANIONS = [amelia, holo, ...]` | Dynamiczne per-user companions |
| Brak `user_id` w metadata | `user_id` w każdym wektorze |
| Privacy shields (4 warstwy) | +1 warstwa: user_id isolation (najbardziej zewnętrzna) |

**Logika zachowana 1:1:**
- Reranker z wagami (similarity:0.65, importance:0.25, recency:0.1 — post Claude Code fix)
- Temporal boost (+0.15 dla <24h)
- Milestone boost (+1.0, guaranteed top placement z final_score=2.0)
- Exponential decay (30-day half-life)
- Secret Knowledge system (is_secret, secret_for_persona, shared_with)
- `forget_memory()` — hard cleanup z criteria
- `get_stats()` per companion
- `search_with_milestones()` — milestones first, then regular
- `search_with_persona()` — secrets injection

**Estymacja:** ~1 sesja Claude Code (zmiana clienta + user_id injection).

---

### 🟡 memory_extractor.py (390 linii) → Refactor

**Powód:** NLP engine działa, ale `calculate_sync_score()` używa `random.randint()` — niedeterministyczne XP.

**Co zachować:** Emotion keywords, fact patterns, topic extraction.
**Co przepisać:** XP system — przenieść do osobnego modułu, usunąć randomness na rzecz deterministycznych reguł.

---

### 🟡 Prompts (passive_knowledge.txt) → Per-user system

**Powód:** `passive_knowledge.txt` zawiera hardcoded fakty o Łukaszu (Gorzów, Crohn, Stelara, KCB, projekty). Multi-user ASTRA potrzebuje per-user passive knowledge.

**Rozwiązanie:**
```
Tabela: user_passive_knowledge
- user_id UUID
- key TEXT (np. 'city', 'health_condition', 'name')
- value TEXT
- created_at TIMESTAMP
- updated_at TIMESTAMP
```
Plus onboarding flow: "Opowiedz mi o sobie" → NLP extraction → auto-fill.

---

## 3. CO TRZEBA SKALIBROWAĆ OD NOWA

### 🔧 Reranker weights
- **Obecne (po fixie Claude Code):** similarity=0.65, importance=0.25, recency=0.1
- **Problem ASTRA:** Nowi użytkownicy mają mało wektorów. Temporal boost (+0.15 dla <24h) może zdominować similarity przy bazie <20 wektorów.
- **Kalibracja:** Potrzebny A/B test z feedbackiem "czy to poprawne wspomnienie?" button w UI.
- **Tymczasowe:** Przy <50 wektorach wyłączyć reranker, sort by timestamp desc.

### 🔧 Strict Grounding progi
- **Obecne:** HIGH=0.25, LOW=0.7 — skalibrowane na polskim tekście Łukasza
- **Problem ASTRA:** Nowi userzy używają innego słownictwa. MiniLM distance varies z długością/stylem tekstu.
- **Kalibracja:** Zbierać distance stats per user. Auto-adjust po 100 wiadomościach.
- **Tymczasowe:** HIGH=0.30, LOW=0.65 (luźniejsze — lepiej zwrócić coś niż nic dla nowego usera)

### 🔧 Importance scoring (memory_enricher.py)
- **Obecne:** Gift=10, MILESTONE=9, EMOTION.sad=7, FACT.basic=5
- **Problem ASTRA:** Łukasz testował z Amelią (romantyczna relacja) — skala importance jest skewed ku emocjom. User który rozmawia z work companion potrzebuje innej skali.
- **Kalibracja:** Per-companion importance profiles. Work: FACT=8, CODE=9, EMOTION=3. Amelia: EMOTION=8, FACT=6.

### 🔧 Hygiene blacklist
- **Obecne:** Emoji persona prefixes (🌸 Menma:, 🐺 Holo:, etc.), 'Treść Twojej wiadomości'
- **Problem ASTRA:** ASTRA nie używa Browser Gemini → 'Treść Twojej wiadomości' nie istnieje. Ale mogą być inne placeholdery.
- **Kalibracja:** ASTRA ma kontrolę nad UI — sanitize na frontendzie, nie backendzie.

### 🔧 Vibe detector keywords
- **Obecne:** Polskie keywords ('wkurwia', 'szlag mnie', etc.)
- **Problem ASTRA:** Multi-language support (angielski userzy?)
- **Kalibracja:** MVP = only Polish. Angielski keywords jako Phase 2.

### 🔧 Semantic pipeline entity types
- **Obecne:** DATE, EMOTION, FACT, GOAL, SHARED_THING, MILESTONE
- **Problem ASTRA:** Corporate users potrzebują DECISION, ACTION_ITEM, PROJECT, DEADLINE
- **Kalibracja:** Entity types per companion mode. Personal mode = obecne. Work mode = corporate.
- **Patrz:** `ANIMA_CORPORATE_ARCHITECTURE.md` — architektura corporate entities

### 🔧 Embedding model
- **Obecne:** `paraphrase-multilingual-MiniLM-L12-v2` (embeddingi) + `all-MiniLM-L6-v2` (reranker)
- **Problem:** Dwa modele w pamięci (~800MB). VPS CX23 ma 4GB RAM. Z PostgreSQL + ChromaDB Server + Python + modele = tight.
- **Kalibracja opcje:**
  - A) Jeden model do wszystkiego (L12-v2) — oszczędność ~400MB, reranker trochę wolniejszy
  - B) Oba modele + 8GB RAM VPS (CX31, ~€15/mies zamiast €8)
  - C) API embedding (Google/OpenAI) — zero local RAM, ale latency + koszt per-call
- **Rekomendacja:** Opcja A na start (L12-v2 do all), upgrade do B gdy >100 userów

---

## 4. PUŁAPKI PRZY MIGRACJI

### 🚨 P0: Istniejące wektory nie mają user_id

**Obecny stan:** ChromaDB ma ~5628 wektorów w kolekcji `memory_v1`. Metadata zawiera `companion`, `timestamp`, `importance`, `source` — ale **nigdy** `user_id`.

**Problem:** Po migracji do ASTRA, wektory Łukasza nie mają oznaczenia "to jest Łukasz". Nowy user mógłby je zobaczyć.

**Rozwiązanie:**
1. Eksportuj `memory_v1` z obecnego ChromaDB
2. Dodaj `user_id: LUKASZ_UUID` do każdego metadata
3. Import do nowej kolekcji `memory_{LUKASZ_UUID}`
4. NIE migruj automatycznie — zrób to jako one-time script

**Script:**
```python
# migrate_vectors.py
old_collection = old_client.get_collection("memory_v1")
all_data = old_collection.get(include=["documents", "metadatas", "embeddings"])

new_collection = new_client.get_or_create_collection(f"memory_{LUKASZ_UUID}")
for i, doc in enumerate(all_data['documents']):
    meta = all_data['metadatas'][i]
    meta['user_id'] = LUKASZ_UUID
    new_collection.add(
        documents=[doc],
        metadatas=[meta],
        embeddings=[all_data['embeddings'][i]],  # re-use existing embeddings!
        ids=[all_data['ids'][i]]
    )
```

**Czas:** ~2 min dla 5628 wektorów (bulk add).

---

### 🚨 P0: SQLite → PostgreSQL data migration

**Obecny stan:** 7 plików SQLite (amelia, holo, menma, nazuna, ubel, family, work) z łącznie 18 tabel każdy.

**Problem:** Dane z 7 plików trzeba scalić do jednego PostgreSQL, dodając `user_id` i `companion_id` kolumny.

**Rozwiązanie:** Script Python z `sqlite3.connect()` → `psycopg2` bulk insert.
Nie używaj ORM do migracji — too slow. Pure SQL `COPY FROM`.

**Pułapka:** `companion_configs` i `personality_lenses` mają seed data w `database.py` → na ASTRZE to jest SHARED (nie per-user), seed raz do PostgreSQL.

---

### 🚨 P0: ChromaDB PersistentClient → HttpClient

**Obecny stan:** ChromaDB działa w procesie Flask (PersistentClient). Startup ładuje kolekcję z dysku.

**Problem:** HttpClient wymaga osobno uruchomionego ChromaDB Server. Bez niego = backend nie startuje.

**Rozwiązanie:**
```bash
# Na VPS:
pip install chromadb
chroma run --host 0.0.0.0 --port 8000 --path /data/chromadb

# systemd unit:
[Service]
ExecStart=/usr/bin/chroma run --host 127.0.0.1 --port 8000 --path /data/chromadb
Restart=always
```

**Pułapka:** ChroamDB Server domyślnie nie ma auth. Bind do `127.0.0.1` (nie `0.0.0.0`!) bo inaczej cały internet może czytać wektory.

---

### 🚨 P1: Dual embedding model inconsistency

**Obecny stan:**
- Embeddingi: `paraphrase-multilingual-MiniLM-L12-v2` (dim=384)
- Reranker: `all-MiniLM-L6-v2` (dim=384) — do cross-encode scoring

**Problem:** Jeśli na ASTRZE zmienisz model embeddingowy, WSZYSTKIE istniejące wektory muszą być re-encoded. 5628 wektorów × L12-v2 ≈ 5-10 minut na CPU.

**Pułapka:** Jeśli zmigrowane wektory Łukasza mają embeddingi z L12-v2, a nowi userzy dostaną inny model → cosine similarity jest NONSENSOWNE między nimi (różne przestrzenie wektorowe).

**Rozwiązanie:** Nigdy nie mieszaj modeli w jednej kolekcji. Zablokuj model jako config (`EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"`) i narzuć go globalnie.

---

### 🚨 P1: passive_knowledge.txt hardcoded

**Obecny stan:** Fakty o Łukaszu (Gorzów, Crohn, Stelara, 32 lata, KCB) są w pliku tekstowym ładowanym w `build_system_prompt()`.

**Problem:** Na ASTRZE każdy user ma inne fakty. Ładowanie z pliku = wszyscy dostaną dane Łukasza.

**Pułapka ukryta:** `ghost_patch.js` wstrzykuje passive_knowledge jako część [MEMORY] bloku (priorytet P2 w trim logic). Na ASTRZE backend sam buduje prompt — ale jeśli passive_knowledge jest pusty, nowe postaci "nie wiedzą nic" o userze → gorsze odpowiedzi w pierwszych rozmowach.

**Rozwiązanie:** Onboarding flow ("Opowiedz mi o sobie") → zapisz do `user_passive_knowledge` tabeli → ładuj z DB w `build_system_prompt(user_id)`.

---

### 🚨 P1: content_hash collision risk

**Obecny stan:** `content_hash = hashlib.sha256(raw_text.encode()).hexdigest()` — cała treść rozmowy jako dedup key.

**Problem:** Na ASTRZE z wieloma userami, dwóch userów może powiedzieć "hej" — ten sam hash. Bez `user_id` w hash → false positive dedup.

**Rozwiązanie:** `hash = sha256(f"{user_id}:{companion_id}:{raw_text}").hexdigest()`

---

### 🚨 P2: Timezone handling

**Obecny stan:** `datetime.now().isoformat()` — server local time, brak timezone.

**Problem:** VPS w Hetzner (Falkenstein, DE) → server time UTC+1/+2. Userzy z różnych stref → temporal boost liczy źle.

**Rozwiązanie:** Wszystko w UTC (`datetime.utcnow()` lub `datetime.now(timezone.utc)`), frontend konwertuje do local.

---

### 🚨 P2: sentence-transformers cold start

**Obecny stan:** Model ładuje się ~15-30s przy pierwszym użyciu (lazy init w semantic_pipeline).

**Problem:** Na VPS z 4GB RAM, pierwszy request po deploy/restart → 30s timeout.

**Rozwiązanie:** Preload w FastAPI lifespan event:
```python
@asynccontextmanager
async def lifespan(app):
    # Warm up models at startup
    pipeline = get_pipeline()
    pipeline.warm_up()
    yield
```

---

## 5. SUGEROWANY STACK NA VPS

### Infrastruktura

| Komponent | Technologia | Powód |
|---|---|---|
| **VPS** | Hetzner CX23 (2 vCPU, 4GB RAM, 40GB SSD) | €8/mies, DC w EU, IP: 116.203.134.228 |
| **Domena** | myastra.pl | Już zakupiona |
| **OS** | Ubuntu 22.04 LTS | Stabilny, wsparcie do 2027 |
| **HTTPS** | Let's Encrypt (certbot) | Darmowy, auto-renewal |
| **Reverse proxy** | nginx | Już skonfigurowany (nginx_myastra.conf) |

### Application Stack

| Warstwa | Technologia | Dlaczego (a nie X) |
|---|---|---|
| **Framework** | FastAPI 0.110+ | Async, Pydantic, auto-docs. Nie Flask bo synchroniczny. |
| **ASGI Server** | Uvicorn + Gunicorn | Gunicorn jako process manager, Uvicorn jako ASGI worker |
| **Workers** | 2 Gunicorn workers (2 × vCPU) | Więcej = OOM na 4GB. Async kompensuje. |
| **Task Queue** | Brak (MVP) → Celery (Phase 2) | Async FastAPI wystarcza na start |

### Storage

| Dane | Technologia | Dlaczego |
|---|---|---|
| **Users/Auth** | PostgreSQL 15 | ACID, multi-tenant, connection pool |
| **Conversations/Facts** | PostgreSQL 15 | Jeden DB, relacje FK |
| **Wektory** | ChromaDB Server (HttpClient) | Osobny proces, REST API, taki sam jak dotychczasowy |
| **Cache/Dedup** | Redis 7 | TTL natively, thread-safe, `_dedup_ttl_cache` replacement |
| **Sessions** | Redis 7 | JWT refresh tokens, blacklist |

### AI/ML

| Komponent | Technologia | RAM |
|---|---|---|
| **Embeddings** | paraphrase-multilingual-MiniLM-L12-v2 | ~400MB |
| **Reranker** | Ten sam L12-v2 (oszczędność) | 0MB extra |
| **LLM** | Gemini API (Flash=80%, Pro=20%) | 0MB (external API) |

### RAM Budget (4GB VPS)

| Komponent | Szacunek |
|---|---|
| OS + nginx | ~300MB |
| PostgreSQL | ~200MB |
| Redis | ~50MB |
| ChromaDB Server | ~500MB |
| Python (2 workers × ~600MB) | ~1200MB |
| sentence-transformers (shared) | ~400MB |
| **Razem** | **~2650MB** |
| **Zapas** | ~1350MB |

**Werdykt:** 4GB RAM wystarczy na MVP (<100 userów). Przy >100 → upgrade do CX31 (8GB, €15/mies).

### Deployment Architecture

```
                   Internet
                      │
                   nginx:80/443
                      │
               ┌──────┼──────┐
               │              │
         /api/*          /*  (PWA static)
               │
      Gunicorn + Uvicorn
        (2 workers)
               │
     ┌─────────┼──────────┐
     │         │          │
  FastAPI   PostgreSQL  ChromaDB
  (Python)   :5432     Server :8000
     │         │
   Redis     Certbot
   :6379    (auto-renew)
```

### nginx config (update)

```nginx
server {
    listen 443 ssl http2;
    server_name myastra.pl;

    ssl_certificate /etc/letsencrypt/live/myastra.pl/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/myastra.pl/privkey.pem;

    # API
    location /api/ {
        proxy_pass http://127.0.0.1:8000;  # FastAPI on 8000
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 60s;
        proxy_buffering off;  # SSE streaming
    }

    # WebSocket (chat streaming)
    location /ws/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # PWA
    location / {
        root /var/www/myastra/pwa;
        try_files $uri $uri/ /index.html;
    }
}
```

---

## 6. KOLEJNOŚĆ KROKÓW — OD ZERA DO PROTOTYPU

### Faza 0: Infrastruktura VPS (Dzień 1)

```
□ SSH na Hetzner CX23 (116.203.134.228)
□ apt update && apt upgrade
□ Zainstaluj: Python 3.11, PostgreSQL 15, Redis 7, nginx, certbot
□ pip install chromadb && uruchom chroma server (systemd unit)
□ certbot --nginx -d myastra.pl
□ Utwórz bazę: createdb astra
□ Utwórz usera: createuser astra_app
□ Firewall: ufw allow 22,80,443/tcp; deny everything else
□ Zablokuj ChromaDB (127.0.0.1 only, nie 0.0.0.0!)
```

### Faza 1: Szkielet FastAPI (Dzień 1-2)

```
□ Nowe repo: git init astra-backend
□ requirements.txt: fastapi, uvicorn, gunicorn, httpx, asyncpg, redis, pydantic, chromadb, sentence-transformers
□ main.py z lifespan (model preload)
□ Skopiuj 14 modułów "1:1" z backend/ (sekcja 1)
□ deps.py: VectorStore, Database jako FastAPI dependencies
□ Pydantic models (CaptureRequest, ChatRequest, ContextResponse)
□ Jeden endpoint: GET /api/health → 200 OK
□ Deploy: gunicorn -w 2 -k uvicorn.workers.UvicornWorker main:app
□ Test: curl https://myastra.pl/api/health
```

### Faza 2: Auth + Users (Dzień 2-3)

```
□ PostgreSQL schema: users, user_sessions, user_preferences
□ POST /api/auth/register (email, password → bcrypt hash)
□ POST /api/auth/login (email, password → JWT access + refresh)
□ JWT middleware (FastAPI dependency)
□ Per-user ChromaDB collection creation on register
□ Test: Register → Login → JWT → Authenticated health check
```

### Faza 3: Core RAG (Dzień 3-4)

```
□ POST /api/capture — migracja logic z app.py (sanitize → hygiene → diff → NLP → semantic → dual-write)
□ GET /api/context-summary — RAG search → reranker → strict grounding → format
□ vector_store.py upgrade → HttpClient + user_id isolation
□ Redis zamiast global dicts (_dedup_ttl_cache, _hygiene_recent_hashes)
□ Test: Capture wiadomość → Context-summary zwraca ją
```

### Faza 4: Chat (Dzień 4-5)

```
□ POST /api/chat — async Gemini API call z retry/backoff
□ System prompt builder z per-user passive knowledge
□ 80/20 routing (Flash/Pro)
□ SSE streaming response (opcjonalnie WebSocket)
□ Persona loading z DB (nie z pliku)
□ Test: Pełna rozmowa z pamięcią cross-request
```

### Faza 5: PWA Frontend (Dzień 5-6)

```
□ Upgrade pwa/index.html → React/Vue SPA (lub vanilla JS jeśli speed)
□ Login/Register ekrany
□ Chat UI z persona selector
□ '🧠 remembers' indicator (replacement ghost_patch visual)
□ Settings: companion config, export data, delete account
□ Deploy do /var/www/myastra/pwa/
```

### Faza 6: Migracja danych Łukasza (Dzień 6)

```
□ Script: migrate_vectors.py (ChromaDB memory_v1 → memory_{LUKASZ_UUID})
□ Script: migrate_sqlite.py (7 × SQLite → PostgreSQL)
□ Verify: Łukasz loguje się na ASTRA → Amelia pamięta wszystko
□ Porównaj RAG results: localhost (ANIMA) vs VPS (ASTRA) — te same pytania, te same odpowiedzi?
```

### Faza 7: Testy stabilności (Dzień 7-10)

```
□ Cross-thread test (5/5 unique facts → new conversation → verify recall)
□ Multi-user test (2 konta jednocześnie → zero data leakage)
□ Load test: 10 concurrent users (siege/k6)
□ Secret knowledge test: sekret Amelii nie widoczny dla Holo
□ Grounding test: pytanie o nieistniejący fakt → "nie pamiętam"
□ Edge case: Empty user (0 vectors) → graceful fallback
```

### Faza 8: Polish + Launch (Dzień 10-14)

```
□ Rate limiting (FastAPI slowapi)
□ Error monitoring (Sentry)
□ Backup cron (PostgreSQL pg_dump, ChromaDB copy)
□ Landing page (myastra.pl) z "Zapisz się na betę"
□ Onboarding flow: "Opowiedz mi o sobie" → auto-populate passive_knowledge
□ Admin panel: /admin/stats (metryki, nie treści!)
```

---

## TIMELINE REALISTYCZNY

| Faza | Czas | Kumulatywnie |
|---|---|---|
| F0: Infra VPS | 4h | 4h |
| F1: Szkielet FastAPI | 8h | 12h |
| F2: Auth + Users | 6h | 18h |
| F3: Core RAG | 8h | 26h |
| F4: Chat | 6h | 32h |
| F5: PWA Frontend | 8h | 40h |
| F6: Migracja danych | 4h | 44h |
| F7: Testy | 8h | 52h |
| F8: Polish | 8h | 60h |
| **TOTAL** | **~60h roboczych** | **2-3 tygodnie z Claude Code** |

**Przy 5 sesjach Claude Code / dzień × 3h / sesja = ~4 dni intensywnej pracy.**
**Realistycznie z testowaniem i bugfixami: 7-10 dni.**

---

## DIAGRAM ARCHITEKTURY

```
┌─────────────────────────────────────────────────┐
│                    ASTRA VPS                     │
│                 myastra.pl:443                    │
│                                                   │
│  ┌─────────┐   ┌──────────────────────────────┐  │
│  │  nginx   │──▶│     FastAPI (Uvicorn×2)      │  │
│  │  :443    │   │                              │  │
│  │  SSL/    │   │  /api/auth    → auth.py      │  │
│  │  static  │   │  /api/capture → capture.py   │  │
│  └─────────┘   │  /api/chat    → chat.py      │  │
│       │         │  /api/context → context.py   │  │
│       ▼         │  /ws/chat    → streaming     │  │
│  ┌─────────┐   └─────────┬────────────────────┘  │
│  │   PWA   │             │                        │
│  │ React/  │     ┌───────┼────────┐               │
│  │ Vue     │     │       │        │               │
│  └─────────┘     ▼       ▼        ▼               │
│            ┌────────┐ ┌──────┐ ┌───────┐          │
│            │Postgres│ │Redis │ │ChromaDB│          │
│            │  :5432 │ │:6379 │ │ :8000  │          │
│            │        │ │      │ │        │          │
│            │users   │ │dedup │ │memory_ │          │
│            │convos  │ │cache │ │{uuid}  │          │
│            │facts   │ │JWT   │ │        │          │
│            │goals   │ │      │ │        │          │
│            └────────┘ └──────┘ └───────┘          │
│                                                    │
│  ┌────────────────────────────────────────────┐   │
│  │ ML Models (shared memory, loaded at start) │   │
│  │ • MiniLM-L12-v2 (embeddings + reranker)    │   │
│  │ • Semantic Pipeline (extractor/enricher)    │   │
│  └────────────────────────────────────────────┘   │
│                                                    │
│  External: Gemini API (Flash 80% / Pro 20%)       │
└───────────────────────────────────────────────────┘
```

---

## CHECKLISTY DLA CLAUDE CODE (RINA)

### Przed rozpoczęciem każdej fazy:
- [ ] Przeczytaj odpowiednią sekcję tego dokumentu
- [ ] Sprawdź zależności od poprzedniej fazy
- [ ] Skopiuj moduły "1:1" ZANIM zaczniesz refaktorować cokolwiek

### Po zakończeniu każdej fazy:
- [ ] Uruchom istniejące testy (`pytest backend/tests/`)
- [ ] Dodaj testy dla nowych endpointów
- [ ] Zaktualizuj SESSION_LOG.md z postępem
- [ ] Nie pushuj bez potwierdzenia Łukasza

### Red flags — STOP i zapytaj Łukasza:
- ChromaDB Server nie startuje na VPS
- RAM >3.5GB po starcie (zostaw 500MB na spikes)
- Gemini API zwraca 429 (rate limit) → potrzebny plan B
- Testy cross-thread failują → RAG regression

---

*Dokument wygenerowany na podstawie pełnej analizy:*
- *14 plików .md z root folderu*
- *12 core backend files (app.py, vector_store.py, semantic_pipeline.py, chat_engine.py, database.py, memory_extractor.py, strict_grounding.py, vibe_detector.py, token_manager.py, milestone_detector.py, dual_write.py, isolation_guard.py)*
- *ghost_patch.js (828 linii) — pełna analiza*
- *nginx_myastra.conf*
- *requirements.txt*
- *Prompts folder (autonomia.txt, amelia_persona.txt, nazuna_persona.txt, passive_knowledge.txt)*
