# Architektura Multi-User dla ANIMA

> Dokument projektowy: skalowanie AI Companion z pamięcią długoterminową z 1 → N użytkowników.

---

## Diagnoza obecnego stanu

Przeanalizowałem cały codebase ANIMA/UCHO. Oto kluczowe single-user bottlenecki:

| Komponent | Obecny stan | Problem multi-user |
|-----------|-------------|-------------------|
| **ChromaDB** | 1 kolekcja `memory_v1`, filtr [companion](file:///c:/Users/lpisk/Projects/ucho-VPS/backend/database.py#658-671) | Brak `user_id` — wszyscy dzielą te same wektory |
| **SQLite** | 7 plików per companion ([ucho_amelia.db](file:///c:/Users/lpisk/Projects/ucho-VPS/backend/ucho_amelia.db), etc.) | Hardcoded ścieżki, brak user namespace |
| **VectorStore** | SHA256(`companion:text`) jako ID | Kolizje ID między userami (ten sam tekst = ten sam ID!) |
| **app.py** | Globalne `db_instances`, `vector_memory` singleton | Zero identyfikacji usera |
| **IsolationGuard** | Filtruje persony, nie userów | Persona ≠ User — brak bariery user-level |
| **Dedup cache** | `_dedup_ttl_cache` — globalny dict | User A blokuje zapis user B tego samego tekstu |
| **Hygiene cache** | `_hygiene_seen_cache` — per companion | Bez user namespace |

> [!CAUTION]
> **Krytyczny bug bezpieczeństwa**: SHA256(`companion:text`) jest deterministyczny — jeśli User A i User B napiszą ten sam tekst do tego samego companion, `upsert` nadpisze wektor User A danymi User B. Dane wyciekają.

---

## 1. Izolacja wektorów ChromaDB

### Rekomendacja: **Metadata filtering z `user_id`** (Faza 1) → **Osobne kolekcje** (Faza 2)

#### Faza 1 — Metadata filtering (MVP, teraz)

```python
# vector_store.py — zmiana

class VectorStore:
    def add_memory(self, text, metadata, user_id, ...):
        # KRYTYCZNE: user_id W HASH'U ID
        mem_id = hashlib.sha256(
            f"{user_id}:{companion}:{text}".encode('utf-8')
        ).hexdigest()[:32]
        
        metadata['user_id'] = user_id  # metadane ChromaDB
        
        self.collection.upsert(
            documents=[text],
            metadatas=[metadata],
            ids=[mem_id]
        )
    
    def search(self, query, user_id, companion_filter, ...):
        # PODWÓJNY FILTR: user_id + companion
        where_clause = {
            "$and": [
                {"user_id": user_id},
                {"companion": companion_filter}
            ]
        }
        results = self.collection.query(
            query_texts=[query],
            where=where_clause,
            ...
        )
        # + post-query validation na user_id
```

**Zalety**: minimalne zmiany w kodzie, działa od razu.
**Wady**: scan penalty rośnie liniowo z liczbą userów; przy 100+ userach ChromaDB zwalnia.

#### Faza 2 — Kolekcje per user (100+ userów)

```python
class MultiUserVectorStore:
    def __init__(self):
        self.client = chromadb.PersistentClient(path=self.persist_directory)
        self._collections = {}  # cache: user_id → Collection
    
    def _get_collection(self, user_id: str) -> Collection:
        """Lazy-loaded kolekcja per user."""
        key = f"user_{user_id}"
        if key not in self._collections:
            self._collections[key] = self.client.get_or_create_collection(
                name=key,
                embedding_function=self.ef
            )
        return self._collections[key]
    
    def search(self, query, user_id, companion_filter, ...):
        collection = self._get_collection(user_id)
        # Filtr tylko na companion — user_id jest już izolowany
        where_clause = {"companion": companion_filter}
        return collection.query(query_texts=[query], where=where_clause, ...)
```

**Zalety**: O(1) izolacja, zero scan penalty, prosty cleanup (drop collection = drop user).
**Wady**: wiele kolekcji w jednym ChromaDB instance (limit ~1000 kolekcji w embedded mode).

#### Faza 3 — Osobne bazy ChromaDB (1000+ userów)

```
/data/
  /users/
    /user_abc123/
      /chroma_db/    ← osobny PersistentClient
      /sqlite/       ← osobne SQLite pliki
    /user_def456/
      /chroma_db/
      /sqlite/
```

Każdy user = osobny `PersistentClient`. Pełna fizyczna izolacja.

### Moja rekomendacja

| Skala | Strategia | Kiedy |
|-------|-----------|-------|
| 1-50 userów | Metadata filtering (`user_id` w WHERE) | **MVP — teraz** |
| 50-500 | Kolekcje per user | Kiedy latency > 200ms |
| 500+ | Osobne ChromaDB instances | Kiedy potrzebujesz shardingu |

---

## 2. Zarządzanie sesjami

### Rekomendacja: **JWT (JSON Web Tokens)** z refresh tokenami

```
┌─────────────┐    POST /auth/login     ┌─────────────┐
│  Extension   │ ──────────────────────→ │   Flask API  │
│  (Chrome)    │ ←────────────────────── │              │
│              │    {access_token,       │  JWT Verify  │
│              │     refresh_token}      │              │
└──────┬───────┘                         └──────┬───────┘
       │                                        │
       │  GET /api/context-summary              │
       │  Authorization: Bearer <JWT>           │
       │ ──────────────────────────────────────→ │
       │                                        │
       │  JWT payload: {user_id, exp, iat}      │
       │  user_id → VectorStore + Database      │
```

#### Implementacja

```python
# auth.py — NOWY MODUŁ

import jwt
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify

SECRET_KEY = os.environ['JWT_SECRET']  # NIGDY w kodzie!

def create_tokens(user_id: str) -> dict:
    access = jwt.encode({
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(hours=1),
        'type': 'access'
    }, SECRET_KEY, algorithm='HS256')
    
    refresh = jwt.encode({
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(days=30),
        'type': 'refresh'
    }, SECRET_KEY, algorithm='HS256')
    
    return {'access_token': access, 'refresh_token': refresh}

def require_auth(f):
    """Dekorator — wymusza JWT na endpoincie."""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return jsonify({'error': 'Missing token'}), 401
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
            request.user_id = payload['user_id']
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401
        return f(*args, **kwargs)
    return decorated
```

```python
# app.py — użycie

@app.route('/api/context-summary')
@require_auth
def context_summary():
    user_id = request.user_id  # z JWT
    companion = request.args.get('companion', 'amelia')
    
    memories = vector_memory.search(
        query=...,
        user_id=user_id,        # ← NOWE
        companion_filter=companion
    )
```

#### Dlaczego JWT a nie session tokens?

| Cecha | JWT | Session Tokens |
|-------|-----|----------------|
| Stateless | ✅ Nie wymaga DB lookup | ❌ Wymaga Redis/DB |
| Skalowalność | ✅ Dowolna ilość serwerów | ❌ Shared session store |
| Extension-friendly | ✅ Przechowywany w `chrome.storage` | ⚠️ Cookie problematyczne w MV3 |
| Revocation | ⚠️ Wymaga blacklist | ✅ Natychmiastowe |

> [!TIP]
> Dla MVP wystarczy JWT bez refresh tokenów i bez blacklisty. Dodaj je w fazie 2.

---

## 3. Skalowanie ChromaDB przy 100+ userach

### Problem: ChromaDB embedded = single-process, in-memory index

ChromaDB w trybie `PersistentClient` ładuje **cały HNSW index do RAM**. Przy 5600 wektorach (teraz) to ~50MB. Przy 100 userów × 5000 wektorów = **500K wektorów ≈ 2-4GB RAM**.

### Strategia skalowania

```
Faza 1 (1-50 users):     Embedded ChromaDB, metadata filtering
                          RAM: ~500MB, Latency: <500ms
                          
Faza 2 (50-200 users):   ChromaDB Server Mode (osobny proces)
                          docker run chromadb/chroma
                          RAM: 2-4GB dedicated, Latency: <200ms
                          
Faza 3 (200+ users):     Qdrant lub Milvus (production-grade)
                          Sharding, replication, horizontal scaling
                          
Faza 4 (1000+ users):    Qdrant Cloud / Pinecone
                          Managed service, zero-ops
```

### ChromaDB Server Mode (Faza 2 — rekomendowane na start VPS)

```python
# Zmiana w vector_store.py — 1 linia

# BYŁO (embedded):
self.client = chromadb.PersistentClient(path=self.persist_directory)

# NOWE (server):
self.client = chromadb.HttpClient(
    host=os.environ.get('CHROMA_HOST', 'localhost'),
    port=int(os.environ.get('CHROMA_PORT', 8000))
)
```

```bash
# Docker na VPS:
docker run -d --name chromadb \
  -p 8000:8000 \
  -v /data/chroma:/chroma/chroma \
  -e ANONYMIZED_TELEMETRY=False \
  chromadb/chroma:latest
```

**Ten jeden krok** rozwiązuje:
- ✅ Pamięć nie wpływa na Flask process
- ✅ Może działać na osobnej maszynie
- ✅ Backup niezależny od app serwera

### Przejście na Qdrant (Faza 3)

Qdrant ma natywne **multi-tenancy** z `payload` filtering i **tenant isolation**:

```python
from qdrant_client import QdrantClient

client = QdrantClient("localhost", port=6333)

# Szukaj tylko w danych user X
client.search(
    collection_name="memories",
    query_vector=embedding,
    query_filter=Filter(
        must=[
            FieldCondition(key="user_id", match=MatchValue(value="user_123")),
            FieldCondition(key="companion", match=MatchValue(value="amelia"))
        ]
    )
)
```

> [!IMPORTANT]
> Nie rób migracji do Qdrant na MVP. ChromaDB Server Mode wystarczy do 200 userów. Migracja wektorów jest bolesna i czasochłonna.

---

## 4. Co zamienić w stacku

### SQLite → PostgreSQL

| Aspekt | SQLite (teraz) | PostgreSQL |
|--------|----------------|------------|
| Concurrent writes | ❌ 1 writer, file lock | ✅ MVCC, wielu pisarzy |
| Multi-user | ❌ Osobne pliki per companion per user → eksplozja plików | ✅ Schema per user lub RLS |
| Connections | ❌ Nie thread-safe domyślnie | ✅ Connection pooling |
| Backup | ❌ Kopiowanie plików | ✅ pg_dump, streaming replication |
| Skala | Działa do ~10 userów | Działa do milionów |

#### Kiedy migrować?

**Nie na MVP.** SQLite działa dobrze dla 1-10 userów jeśli:
- Dodasz `user_id` kolumnę do każdej tabeli
- Użyjesz jednej bazy per companion (nie per user×companion)
- Dodasz indeksy na [(user_id, companion)](file:///c:/Users/lpisk/Projects/ucho-VPS/backend/app.py#346-359) w każdej tabeli

```sql
-- Migracja SQLite (szybka, na start)
ALTER TABLE conversations ADD COLUMN user_id TEXT NOT NULL DEFAULT 'legacy';
CREATE INDEX idx_conv_user ON conversations(user_id);

-- Każdy query musi filtrować:
SELECT * FROM conversations 
WHERE companion = ? AND user_id = ?;
```

**Migruj na PostgreSQL** kiedy:
- Masz > 10 concurrent userów
- Potrzebujesz `LISTEN/NOTIFY` (real-time updates)
- Rozmiar baz > 500MB sumarycznie

### Flask → FastAPI

| Aspekt | Flask (teraz) | FastAPI |
|--------|---------------|---------|
| Async | ❌ WSGI (1 request = 1 thread) | ✅ ASGI (async native) |
| Validation | ❌ Ręczne parsowanie | ✅ Pydantic (auto-validation) |
| WebSocket | ❌ Flask-SocketIO (hack) | ✅ Natywne WebSocket |
| Performance | ~500 req/s | ~3000 req/s |
| Typing | ❌ Brak | ✅ Full type hints + auto-docs |

#### Kiedy migrować?

**Nie na MVP.** Flask + Gunicorn (4 workery) obsłuży 50+ concurrent userów. Migruj kiedy:
- Potrzebujesz WebSocket (live companion chat)
- ChromaDB/Gemini calls blokują i potrzebujesz true async
- Chcesz auto-generated API docs (Swagger)

> [!TIP]
> Dodaj `gunicorn --workers 4 --threads 2 app:app` do deployment. To natychmiastowy 8x throughput bez zmiany kodu.

---

## 5. Race Conditions i jak je eliminować

### RC #1: Concurrent ChromaDB writes (CRITICAL)

```
User A: add_memory("kocham pizzę", companion="amelia")
User B: add_memory("kocham pizzę", companion="amelia")  ← JEDNOCZEŚNIE

Problem: SHA256("amelia:kocham pizzę") = ten sam ID!
User B nadpisuje wektor User A.
```

**Fix**: `user_id` w hash ID (opisane wyżej).

### RC #2: SQLite concurrent writes (HIGH)

```
User A: save_conversation() → SQLite WRITE LOCK
User B: save_conversation() → sqlite3.OperationalError: database is locked
```

**Fix natychmiastowy** (SQLite WAL mode):
```python
class Database:
    def __init__(self, db_path):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.execute('PRAGMA journal_mode=WAL')  # ← DODAJ TO
        self.conn.execute('PRAGMA busy_timeout=5000')   # czekaj 5s zamiast crash
```

**Fix docelowy**: PostgreSQL z connection poolem.

### RC #3: Dedup cache race (MEDIUM)

```python
# Obecny stan — globalny dict, zero thread safety:
_dedup_ttl_cache: dict[str, float] = {}

# User A sprawdza: "czy istnieje?" → Nie
# User B sprawdza: "czy istnieje?" → Nie  ← oba przechodzą!
# User A zapisuje → OK
# User B zapisuje → DUPLIKAT
```

**Fix**:
```python
import threading

_dedup_lock = threading.Lock()

def is_vector_duplicate(text, companion_id, user_id):
    key = hashlib.md5(f"{user_id}:{companion_id}:{text}".encode()).hexdigest()
    with _dedup_lock:
        now = time.time()
        # cleanup + check + register w jednej atomic operacji
        _dedup_ttl_cache = {k: v for k, v in _dedup_ttl_cache.items() if now - v < 60}
        if key in _dedup_ttl_cache:
            return True
        _dedup_ttl_cache[key] = now
        return False
```

### RC #4: Embedding model loading (LOW)

```
User A: pierwszy request → ładuj model (~2s)
User B: pierwszy request → ładuj model PONOWNIE (~2s)
```

**Fix**: Model jest już singleton w `VectorStore.__init__`. Ale z Gunicorn workery — każdy worker ładuje osobno. To OK (każdy process ma swoją kopię).

### RC #5: Token Manager contention (LOW)

[token_manager.py](file:///c:/Users/lpisk/Projects/ucho-VPS/backend/token_manager.py) liczy tokeny synchronicznie. Przy 10+ concurrent requests, CPU spike.

**Fix**: Cache token count per text hash (LRU cache):
```python
from functools import lru_cache

@lru_cache(maxsize=1024)
def count_tokens(text: str) -> int:
    return len(text) // 4  # przybliżenie
```

---

## 6. Minimal Viable Architecture — Co teraz, co później

### 🟢 FAZA 1 — MVP (1-2 tygodnie)

**Cel**: Multi-user działa, dane izolowane, basic auth.

| Zadanie | Plik | Wysiłek |
|---------|------|---------|
| Dodaj `user_id` do `VectorStore.add_memory()` i [search()](file:///c:/Users/lpisk/Projects/ucho-VPS/backend/vector_store.py#393-532) | [vector_store.py](file:///c:/Users/lpisk/Projects/ucho-VPS/backend/vector_store.py) | 2h |
| Dodaj `user_id` do SHA256 hash ID | [vector_store.py](file:///c:/Users/lpisk/Projects/ucho-VPS/backend/vector_store.py) | 30min |
| JWT auth (`require_auth` decorator) | `auth.py` [NEW] | 3h |
| User registration endpoint (email + hasło) | `auth.py` | 2h |
| Dodaj `user_id` do SQLite schema + queries | [database.py](file:///c:/Users/lpisk/Projects/ucho-VPS/backend/database.py) | 4h |
| `user_id` w dedup cache i hygiene cache | [app.py](file:///c:/Users/lpisk/Projects/ucho-VPS/backend/app.py) | 1h |
| Przenieś JWT secret do env vars | `.env` | 15min |
| Update extension — store JWT, send w headerach | `background.js` | 2h |
| SQLite WAL mode + busy_timeout | [database.py](file:///c:/Users/lpisk/Projects/ucho-VPS/backend/database.py) | 15min |
| Login/register UI w extension popup | `popup.html` | 3h |

**Łącznie**: ~18h pracy

### 🟡 FAZA 2 — Stabilizacja (miesiąc 2)

| Zadanie | Dlaczego |
|---------|----------|
| ChromaDB Server Mode (Docker) | Odciążenie Flask process |
| Refresh tokeny + token rotation | Bezpieczeństwo sesji |
| Rate limiting per user | Ochrona przed abuse |
| User data export (GDPR) | Prawo do danych |
| Monitoring (Prometheus/Grafana) | Observability |
| Gunicorn z 4+ workers | Concurrent request handling |

### 🔴 FAZA 3 — Skalowanie (miesiąc 3+)

| Zadanie | Kiedy |
|---------|-------|
| SQLite → PostgreSQL | > 20 concurrent users |
| ChromaDB → Qdrant | > 500 users lub potrzeba shardingu |
| Flask → FastAPI | Potrzeba WebSocket / async |
| Redis session store | JWT blacklisting, rate limiting |
| Per-user kolekcje ChromaDB | Latency > 200ms na search |
| Horizontal scaling (Docker Swarm/K8s) | > 1000 users |

---

## Diagram — Docelowa architektura

```
┌─────────────────────────────────────────────────────────────────┐
│                     MULTI-USER ANIMA                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  [Chrome Extension]                                              │
│       │ Authorization: Bearer <JWT>                              │
│       │ X-User-Id: user_abc123                                   │
│       ▼                                                          │
│  ┌──────────────────────┐                                        │
│  │  Nginx (reverse      │                                        │
│  │  proxy + SSL)        │                                        │
│  └──────────┬───────────┘                                        │
│             ▼                                                    │
│  ┌──────────────────────┐     ┌──────────────────┐               │
│  │  Flask/FastAPI        │────→│  ChromaDB Server  │              │
│  │  + Gunicorn (4w)     │     │  (Docker, 8000)   │              │
│  │                      │     │                   │              │
│  │  @require_auth       │     │  Kolekcje:        │              │
│  │  user_id z JWT       │     │  user_abc_memories │              │
│  │                      │     │  user_def_memories │              │
│  └──────────┬───────────┘     └──────────────────┘               │
│             │                                                    │
│             ▼                                                    │
│  ┌──────────────────────┐     ┌──────────────────┐               │
│  │  PostgreSQL           │     │  Redis            │              │
│  │  (users, convos,     │     │  (rate limiting,  │              │
│  │   relationships)     │     │   JWT blacklist)  │              │
│  └──────────────────────┘     └──────────────────┘               │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Podsumowanie decyzji

| Pytanie | Odpowiedź MVP | Odpowiedź docelowa |
|---------|---------------|---------------------|
| Izolacja wektorów | Metadata filtering (`user_id` w WHERE) | Osobne kolekcje per user |
| Sesje | JWT (access token, 1h) | JWT + refresh + blacklist |
| Skalowanie ChromaDB | Embedded + metadata filter | ChromaDB Server → Qdrant |
| SQLite vs PostgreSQL | SQLite + WAL + `user_id` kolumna | PostgreSQL + RLS |
| Flask vs FastAPI | Flask + Gunicorn | FastAPI (kiedy potrzeba async) |
| Race conditions | Threading locks + WAL + user_id w hash | PostgreSQL MVCC + Redis locks |

> [!IMPORTANT]
> **Nie rób wszystkiego naraz.** MVP to: `user_id` wszędzie + JWT + WAL mode. Reszta skaluje się naturalnie kiedy masz realnych userów i realne metryki.
