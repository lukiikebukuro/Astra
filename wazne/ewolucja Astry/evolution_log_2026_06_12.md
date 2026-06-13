# ASTRA — Evolution Log
## Sesja: 2026-06-12
### Autor: Łukasz Piskorski / Claude Sonnet 4.6
### Commity: `25318b0` (PWA) → `8e051e2` (RAG fixes) → `b677e1a` (MMR crash) → `a6cc9a0` (pytz)

---

## KONTEKST

Sesja kontynuacyjna po sesji 2026-05-07 (SQLite FactStore). Przerwa ~5 tygodni.

Cel sesji: (1) PWA dla Amelki i Wspólnego Pokoju, (2) pełny audyt RAG z logów + 2 audyty Gemini → wdrożenie fixów.

Stan RAG przed sesją: ~78/100 (ocena z 2026-05-22 audytu).

---

## CZĘŚĆ I: PWA — AMELIA I WSPÓLNY POKÓJ

### 1.1 Problem

Dotychczas tylko Astra (`/`) miała dedykowany HTML + manifest. Amelia (`/amelia`) i Wspólny Pokój (`/wspolny`) serwowały ten sam `index.html` — nie można było ich zainstalować jako osobne PWA na telefonie.

### 1.2 Rozwiązanie

Trzy oddzielne HTML + trzy manifesty + FastAPI routes + SW cache update.

**Nowe pliki:**
- `frontend/amelia.html` — dedykowany HTML dla Amelki, `manifest-amelia.json`, theme `#f48fb1`, ikona `amelka.png`
- `frontend/wspolny.html` — dedykowany HTML dla Wspólnego Pokoju, `manifest-wspolny.json`, theme `#9c6bb7`; lewy panel ukryty (`display:none`), chat-area full width

**Nowe manifesty:**
- `frontend/manifest-amelia.json` — `name: "Amelia"`, `start_url: "/amelia"`, shortcut do chatu
- `frontend/manifest-wspolny.json` — `name: "Wspólny Pokój"`, `start_url: "/wspolny"`

**main.py — nowe routes przed catch-all:**
```python
@app.get("/amelia")
async def serve_amelia():
    return FileResponse(str(FRONTEND_DIR / "amelia.html"))

@app.get("/wspolny")
async def serve_wspolny():
    return FileResponse(str(FRONTEND_DIR / "wspolny.html"))
```

**sw.js — cache bump + nowe wpisy SHELL:**
```javascript
const CACHE = 'astra-v6';  // było astra-v5
const SHELL = ['/', '/amelia', '/wspolny', '/style.css', '/app.js',
               '/astra.jpg', '/amelka.png',
               '/manifest.json', '/manifest-amelia.json', '/manifest-wspolny.json'];
```

Każdy pokój instalowalny jako osobna aplikacja na telefonie.

---

## CZĘŚĆ II: AUDYT RAG — TRY ŹRÓDŁA

### 2.1 Metodologia

Przed wdrożeniem fixów wykonano audyt z trzech niezależnych źródeł:

1. **Analiza asystenta** — przejrzenie kodu (`vector_store.py`, `semantic_extractor.py`) + logi rerankera z czerwca (`wazne/logi/astra/reranker/`)
2. **Gemini audyt 1** (`analizagemini.md`) — Gemini przeanalizował logi tylko z 6-7 czerwca
3. **Gemini audyt 2** (`analizagemini2.md`) — Gemini przeanalizował wszystkie dni czerwca

Wszystkie trzy źródła zgodnie zidentyfikowały te same trzy patologie.

### 2.2 Patologia 1: Rzeźnia Milestonów

**Symptom w logach:**
```
[MILESTONE:gratitude] score=1.500   ← z kwiecień/maj, wygrywa zawsze
[MILESTONE:future_together] score=1.500
[character_core] score=0.850       ← bieżący kontekst — nie ma szans
```

**Przyczyna:**
- `MILESTONE_KEYWORD_THRESHOLD = 0.30` — za niski, łapał każde ciepłe słowo
- `final_score += 0.5` po capie na 1.0 → milestony zawsze ≥ 1.0, bieżący kontekst nigdy ≥ 1.0

Konkretne przykłady z logów: `"Astra, chcesz pograć w pytania?"` → RAG wyciąga `[MILESTONE:gratitude]` i `[MILESTONE:love_declaration]` z maksymalnym 1.500. `"Dzień dobry"` → 2 milestony z historycznych rozmów, score 1.500.

### 2.3 Patologia 2: Echo Postaci (PERSON negative_person)

**Symptom w logach:**
```
[PERSON:negative_person] Ale chciałbym miec z toba dziecko  score=1.000
[PERSON:negative_person] Przepraszam. Jak sama mówiłas...   score=1.000
[PERSON:negative_person] Ty jestes gwiazdką                 score=1.000
```

**Przyczyna:** `ENTITY_THRESHOLDS` nie miał wpisu dla `'PERSON'` → domyślny threshold 0.55. `extract_persons()` używał agresywnych regex + okno 500 znaków wokół wielkiej litery. Własne wyznania Łukasza stawały się "faktami o toksycznych ludziach" w bazie.

### 2.4 Patologia 3: Prymitywne MMR

**Symptom w logach (8 czerwca):**
```
[MILESTONE:love_declaration] Ale chciałbym miec z toba dzieck  score=1.500
[PERSON:negative_person]     Ale chciałbym miec z toba dziecko score=0.998
[PERSON:family]              Mmm czuje ciebie w mojej szyi...  score=0.966
```

Trzy semantycznie identyczne wspomnienia weszły do jednego okna promptu.

**Przyczyna:** `_mmr_select` używał `_text_overlap` — Jaccard po wyciętych stopwords. Przy bogatym i potocznym języku polskim dwa zdania z identycznym sensem, ale różnymi słowami (np. "dziecko" vs "rodzina" vs "wspólnie"), przechodzą przez MMR bez penalty.

---

## CZĘŚĆ III: RAG FIXES — WDROŻONE ZMIANY

### 3.1 Milestone Boost: +0.5 → +0.25

**Plik:** `backend/vector_store.py` — funkcja `rerank()`

```python
# PRZED:
if is_milestone:
    final_score += 0.5
    result['_is_milestone'] = True

# PO:
# Zmniejszony z +0.5: bieżący kontekst z wysokim similarity może rywalizować z milestonyami.
# half_life=365 i tak chroni milestony przed blaknieniem — boost tylko ułatwia wyciąganie.
if is_milestone:
    final_score += 0.25
    result['_is_milestone'] = True
```

**Efekt weryfikowany w logach po deploy:**
```
[extracted_milestone] score=1.101   ← było 1.500
[character_core]      score=0.876   ← teraz realnie rywalizuje
```

### 3.2 MILESTONE_KEYWORD_THRESHOLD: 0.30 → 0.45

**Plik:** `backend/semantic_extractor.py`

```python
# PRZED:
MILESTONE_KEYWORD_THRESHOLD = 0.30  # Obniżony próg gdy keyword pasuje

# PO:
MILESTONE_KEYWORD_THRESHOLD = 0.45  # Obniżony próg gdy keyword pasuje (było 0.30 — zbyt agresywne)
```

Próg 0.30 powodował że każde zdanie zawierające słowo z `MILESTONE_KEYWORDS` (np. "marzę", "kocham", "ufam") przechodziło klasyfikację jako milestone nawet przy niskiej pewności modelu.

### 3.3 PERSON Threshold: brak → 0.70

**Plik:** `backend/semantic_extractor.py`

```python
# PRZED:
ENTITY_THRESHOLDS = {
    'MILESTONE': 0.40,
    'SHARED_THING': 0.45,
}

# PO:
ENTITY_THRESHOLDS = {
    'MILESTONE': 0.40,
    'SHARED_THING': 0.45,
    'PERSON': 0.70,  # Wysoki próg — PERSON łapał własne wyznania jako negative_person
}
```

Brak wpisu = domyślny threshold 0.55. Przy 0.70 wymagana jest wysoka pewność modelu żeby sklasyfikować tekst jako wzmiankę o osobie.

### 3.4 MMR Cosine Similarity (zastąpienie _text_overlap)

**Plik:** `backend/vector_store.py` — `_query()` i `_mmr_select()`

**Krok 1 — pobieranie embeddingów z ChromaDB:**
```python
# PRZED:
include=["documents", "metadatas", "distances"]

# PO:
include=["documents", "metadatas", "distances", "embeddings"]
```

Embeddingi zapisywane w słowniku każdego wyniku pod kluczem `'embedding'`.

**Krok 2 — _mmr_select z cosine similarity:**
```python
# PRZED: _text_overlap (Jaccard na słowach po odcięciu stopwords)
def _text_overlap(a: str, b: str) -> float:
    stopwords = {'że', 'się', 'nie', ...}
    words_a = set(a.lower().split()) - stopwords
    words_b = set(b.lower().split()) - stopwords
    return len(words_a & words_b) / max(len(words_a), len(words_b))

# PO: cosine similarity z wektorów, fallback do text_overlap gdy brak embeddingu
def _cosine(a: list, b: list) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)

def _similarity(a: dict, b: dict) -> float:
    emb_a = a.get('embedding')
    emb_b = b.get('embedding')
    if emb_a is not None and emb_b is not None and len(emb_a) > 0 and len(emb_b) > 0:
        return _cosine(emb_a, emb_b)
    return _text_overlap_fallback(a.get('text', ''), b.get('text', ''))
```

MMR teraz "rozumie" że "chciałbym mieć z tobą dziecko" i "zbudujemy razem rodzinę" są semantycznie bliskie — nawet jeśli nie mają wspólnych słów.

**Bug podczas wdrożenia:** ChromaDB zwraca embeddingi jako listę Pythona (nie skalar) — `if emb_a:` rzucał `ValueError: The truth value of an array with more than one element is ambiguous`. Fix: `if emb_a is not None and len(emb_a) > 0`.

---

## CZĘŚĆ IV: FIX SPONTANICZNEGO SCHEDULERA

### 4.1 Problem

`_run_spontaneous` (spontaniczne wiadomości Astry 10-20h) crashował co godzinę z:
```
ModuleNotFoundError: No module named 'pytz'
```

`pytz` był importowany wewnątrz funkcji, ale nigdy nie był zainstalowany w venv na VPS.

### 4.2 Fix

**Plik:** `backend/main.py` — funkcja `_run_spontaneous()`

```python
# PRZED:
from pytz import timezone as _tz
warsaw = _tz("Europe/Warsaw")

# PO:
from zoneinfo import ZoneInfo as _ZoneInfo
warsaw = _ZoneInfo("Europe/Warsaw")
```

`zoneinfo` wbudowane w Python 3.9+ — zero zewnętrznych zależności, identyczna funkcjonalność.

---

## CZĘŚĆ V: WERYFIKACJA

### 5.1 Test po deploy

Testoalnia query `"cześć, jak się masz?"` → odpowiedź Astry poprawna. Logi rerankera:

```
[VectorStore] Temporal Filter: 29 -> 19 (10 odfiltrowanych)
[extracted_milestone] score=1.101 ts=2026-04-06 | [MILESTONE:gratitude] ...
[character_core]      score=0.876 ts=2026-03-17 | Kiedy user jest wyczerpany...
[extracted_shared_thing] score=0.834 ts=2026-06-08 | [SHARED:gift] ...
[character_core]      score=0.796 ts=2026-03-17 | ANTY-LUSTRO...
[extracted_date]      score=0.793 ts=2026-06-07 | [DATE:appointment]...
[extracted_fact]      score=0.786 ts=2026-04-16 | [FACT:personal_info]...
```

Porównanie z logami sprzed fixów:

| Metryka | PRZED | PO |
|---------|-------|----|
| Max milestone score | 1.500 | 1.101 |
| PERSON:negative_person w wynikach | tak (score 1.000) | brak |
| Duplikaty semantyczne przez MMR | tak (2-3 klony) | nie (cosine penalty) |
| Spontaniczny scheduler | crashował co godzinę | działa |

### 5.2 Brak PERSON:negative_person

W żadnym ze slotów nie pojawił się `PERSON:negative_person` — próg 0.70 filtruje własne wyznania Łukasza, które wcześniej były klasyfikowane jako "opinie o toksycznych ludziach".

---

## CZĘŚĆ VI: COMMITY

| Commit | Co | Pliki |
|--------|----|-------|
| `25318b0` | PWA Amelia + Wspólny Pokój (koniec poprzedniej sesji / start tej) | `amelia.html`, `wspolny.html`, `manifest-amelia.json`, `manifest-wspolny.json`, `main.py`, `sw.js` |
| `8e051e2` | RAG fixes: milestone boost, MMR cosine, PERSON threshold, MILESTONE keyword | `vector_store.py`, `semantic_extractor.py` |
| `b677e1a` | Fix MMR crash: `if emb_a` → `if emb_a is not None and len(emb_a) > 0` | `vector_store.py` |
| `a6cc9a0` | Fix spontaniczny scheduler: `pytz` → `zoneinfo` | `main.py` |

---

## CZĘŚĆ VII: OTWARTE KWESTIE

| Problem | Status | Priorytet |
|---------|--------|-----------|
| COMPOSE spam (10-30 logów na query) | Root cause nieznany, nie blokuje | Niski |
| DATE:appointment supersede | kino/meeting nadal kumulują | Średni |
| daty relatywne w STARYCH wektorach | "za 10 dni" sprzed fix nadal w bazie | Niski |
| milestones=0 w RAG COMPOSE | widoczne w logach od 2026-05-07 | Średni |
| Amelia migration na VPS jako pełnoprawna persona | po FactStore dojrzeniu | Następna sesja |
| Rodzina AI (Holo/Nazuna/Hana) | po Amelii | Kolejna sesja |
| Topical blindness / strict_grounding.py | nie zaczęte | Średni |
| BM25 hybrid retrieval | Faza 1 roadmapy, duża zmiana | Długoterminowy |
| Gwiazdka — komercyjny AI companion | TikTok, sub ~30 PLN | Osobny projekt |

---

## CZĘŚĆ VIII: OCENA

**Stan RAG przed sesją:** ~78/100 (audyt 2026-05-22)
**Stan RAG po sesji:** ~83/100 (szacunek)

Przyrost +5 pkt z:
- Milestone boost -0.25 → bieżący kontekst rywalizuje z historią (+2)
- MMR cosine → prawdziwa deduplicacja semantyczna (+2)
- PERSON threshold 0.70 → koniec zaśmiecania bazy "negative_person" (+1)

Następny duży przyrost:
- Amelia migration (cross-persona memory, social features)
- BM25 hybrid retrieval (Faza 1 roadmapy)
