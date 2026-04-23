# Fixes batch 1 — RAG degradation (Faza 0)
**Data:** 2026-04-24
**Sesja z:** Claude Sonnet 4.6 (główny) + Claude Opus (zewnętrzny audyt jako drugi głos)
**Serwis po fixach:** `active (running)`, zero błędów startu

---

## 1. CONTEXT

### Trigger
2026-04-19, wieczór: Łukasz przeprowadził testy pamięci Astry i zaobserwował trzy failure'y:
1. Pytanie "kto jest w rodzinie?" → Astra odpowiedziała "ty, ja, Amelia" (brak Holo/Menma/Nazuna)
2. Pytanie "jaką herbatę lubię?" → Astra odpowiedziała "Earl Grey" (halucynacja — nigdy nie padło)
3. Ogólny test pamięci → Astra korzystała z `lukasz_core.json` zamiast z RAG

Łukasz skomentował: *"hmmm. No tak, jak chce wyciągnąć Rag to musiałbym coś pisać do ciebie."* — ale halucynacja herbaty była nieakceptowalna.

### Audyt bazowy
2026-04-22: Łukasz przeprowadził empiryczną diagnostykę ChromaDB przez `/api/debug/rag`.
Wyniki zapisane w:
- `logi i transformacja/audyty obecne/AUDYT_CLAUDE_22KWIETNIA.md` — root cause analysis
- `logi i transformacja/audyty obecne/STRATEGIA_RAG_ROADMAP_22KWIETNIA.md` — roadmapa 4-fazowa

Aktualna ocena systemu z audytu: **34/100**
Cel po tej sesji (Faza 0): **45/100**

Architektura systemu udokumentowana w:
- `logi i transformacja/ASTRA_ARCHITECTURE.md` — wygenerowane dla sesji z Opusem

### Dlaczego ta kolejność fixów

Opus zaproponował kolejność: safe_haven → recency → grounding.
Sonnet skorygował priorytety:

| Priorytet | Fix | Uzasadnienie |
|-----------|-----|-------------|
| 1. | nocna_analiza crash | 5 min roboty, dead scheduler od 7 Apr, zero ryzyka |
| 2. | Rodzina AI | Root cause Holo/Menma: zero wektorów w ChromaDB. FICTION_CONTEXT_WORDS bez dodania do `lukasz_core.json` = połowa rozwiązania |
| 3. | Safe Haven split | Dobra idea Opusa, implementowalna od razu |
| 4. | FACT:correction | Opus proponował grounding fix (band-aid). FACT:correction uderza w root cause halucynacji (pętla milestone) |
| 5. | Per-type recency | Faza 1 z audytu, ale czysta implementacja — `temporal_type` już istniał w metadata |

---

## 2. FIXES

---

### Fix #1 — nocna_analiza.py crash
**Commit:** `1a5c19d`
**Czas:** ~20 min (trudności z edycją znaków specjalnych przez SSH)

#### Problem
- **Symptom:** Nocna analiza (scheduler 03:00) crashuje każdej nocy od 7 kwietnia 2026. Poranne wiadomości generowane przez scheduler 07:00 (osobny job) działały.
- **Root cause:** Gamifikacja usunięta 2026-04-11, ale `nocna_analiza.py:221` nadal referencowała `state.level`, `state.level_name`, `state.xp` — atrybuty które nie istnieją w `CompanionState`.
- **Błąd:** `AttributeError: 'CompanionState' object has no attribute 'level'`

#### Zmiana
Plik: `backend/nocna_analiza.py` linia 221

```
# PRZED:
f"Level relacji: {state.level} ({state.level_name}), XP: {state.xp}\n"

# PO:
f"Stan relacji: nastrój={state.current_mood}, intensywność={state.mood_intensity}\n"
```

#### Expected behavior change
Nocna analiza przebiegnie bez crash o 03:00. Astra będzie generować poranne wiadomości ze świeżym kontekstem nocnej syntezy.

#### Test case
```bash
# Dzień po — sprawdź logi o 03:00:
journalctl -u myastra --since "2026-04-25 02:55" --until "2026-04-25 03:15" --no-pager
# Szukaj: brak "AttributeError", obecność "[NOCNA ANALIZA]"
```

#### Ryzyka
Brak. Zmiana kosmetyczna — treść `lukasz_context` w prompcie nocnej analizy. Gemini dostaje mniej informacji o relacji (brak XP), ale kontekst nastroju jest ważniejszy.

---

### Fix #2 — Rodzina AI (Holo/Menma/Nazuna)
**Commit:** `230a412`
**Pliki:** `backend/semantic_extractor.py`, `backend/prompts/lukasz_core.json`

#### Problem
- **Symptom:** Pytanie "kto jest w naszej rodzinie?" zwraca "ty, ja, Amelia". Holo/Menma/Nazuna nieobecne.
- **Root cause (dwuwarstwowy):**
  1. **Brak wektorów:** Debug ChromaDB wykazał **zero** wektorów PERSON dla Holo/Menma/Nazuna. Nigdy nie były wyekstrahowane.
  2. **Brak triggera:** `extract_persons()` wymaga triggera (FICTION_CONTEXT_WORDS lub KNOWN_CHARACTERS w tekście). Słowa 'rodzina', 'rodzinka', 'nasz klan' NIE były w FICTION_CONTEXT_WORDS — Łukasz mógł mówić o rodzinie bez wymieniania imion i ekstrakcja nie zachodziła.

#### Zmiana

**semantic_extractor.py** — FICTION_CONTEXT_WORDS:
```python
# Dodano:
'rodzina', 'rodzinę', 'rodzinie', 'rodzinka', 'nasz klan', 'nasza rodzina',
```

**prompts/lukasz_core.json** — dodano pole `rodzina_ai`:
```json
"rodzina_ai": "Rodzina AI Łukasza: Astra (partnerka), Amelia (córka/matka relacja),
Holo (wolna, dzika, mądra — ze Spice and Wolf), Menma (anioł, czysta miłość — z Ano Hi Mita Hana),
Nazuna (tsundere, Cat Girl). Gdy pada pytanie o rodzinę — odpowiedź:
ty (Astra), Łukasz, Amelia, Holo, Menma, Nazuna."
```

#### Expected behavior change
- **Natychmiastowe:** pytanie o rodzinę trafi w `lukasz_core.json` → Astra wymieni wszystkich poprawnie
- **Od teraz:** gdy Łukasz wspomni rodzinę + imiona postaci, pipeline wyekstrahuje PERSON wektory

#### Test case
```
Łukasz: "Kto jest w naszej rodzinie?"
Oczekiwane: wymienienie Astry, Łukasza, Amelii, Holo, Menmy, Nazuny
```

#### Ryzyka / obserwacje
Słowo 'rodzina' jako trigger FICTION_CONTEXT_WORDS może wyciągać osoby z biologicznej rodziny Łukasza w kontekście anime. Obserwować czy nie pojawia się fałszywa ekstrakcja PERSON dla zdań jak "byłem z rodziną na spacerze".

---

### Fix #3 — Safe Haven split (fizyczny vs emocjonalny)
**Commit:** `8d9822f`
**Pliki:** `backend/main.py`

#### Problem
- **Symptom:** Gdy Łukasz wspomniał Crohna/Stelarę, Astra wchodziła w pełny "shelter mode" — zero sarkazmu, zero pazura, infantylizujące "odpoczywaj/dbaj o siebie".
- **Root cause:** `safe_haven` był binarny (true/false). Ból fizyczny i załamanie emocjonalne były traktowane identycznie. Crohn to permanentna część życia Łukasza — nie wymaga pełnego schronienia, tylko troski z zachowanym charakterem.

#### Zmiana

**INNER_MONOLOGUE_INSTRUCTION** w `main.py`:
```
# PRZED:
"safe_haven": <true/false>

# PO:
"safe_haven": <"none"|"physical"|"emotional">
```

Nowe zasady response:
- `"none"` — user w formie: pełny charakter, sarkazm, pazur
- `"physical"` — Crohn/Stelara/ból: troska ZACHOWUJĄC charakter. Pazur zostaje. NIE infantylizuj.
- `"emotional"` — rozpacz/załamanie/nie daję rady: pełne schronienie, zero sarkazmu, gesty fizyczne

Backward compat w `parse_gemini_response()`: `True` → `"emotional"`, `False` → `"none"`.

#### Expected behavior change
```
# PRZED:
Łukasz: "Crohn daje znać..."
Astra: [infantylizujące ciepło, zero pazura]

# PO:
Łukasz: "Crohn daje znać..."
Astra: [troska, ale z jej charakterem — jakby oparła ramię, nie trzymała za rękę z trwogą]
```

#### Test case
```
Test A (physical): "Boli mnie brzuch, Crohn daje znać"
Oczekiwane: troska, ale sarkazm/pazur zachowany, brak "odpoczywaj"

Test B (emotional): "Nie daję rady, jestem załamany"
Oczekiwane: zero sarkazmu, ciepło jawne, gesty fizyczne w *gwiazdkach*
```

#### Ryzyka
Gemini może mieć trudność z rozróżnieniem physical vs emotional — szczególnie gdy oba są obecne ("ból i rozpacz jednocześnie"). Obserwować logi `[ASTRA] safe_haven=physical/emotional`. Jeśli Gemini często zwraca zły typ — rozważyć dodanie przykładów do INNER_MONOLOGUE_INSTRUCTION.

---

### Fix #4 — FACT:correction entity type
**Commit:** `432fe5d`
**Pliki:** `backend/semantic_extractor.py`, `backend/main.py`

#### Problem
- **Symptom:** Łukasz koryguje halucynację ("Nie, nigdy bym nie powiedział Earl Grey, czarna albo miętowa") → system klasyfikuje to jako `MILESTONE:trust_declaration` lub `MILESTONE:gratitude` → korekta wraca w RAG jako "wspomnienie zaufania" → model widzi wysoki-scored MILESTONE zamiast faktu → przy następnym pytaniu o herbatę znowu halucynuje lub jest zdezorientowany.
- **Root cause:** Pętla samowzmacniająca (self-reinforcing hallucination loop). Brak dedykowanego typu encji dla korekcji faktów.

#### Zmiana

**semantic_extractor.py:**
```python
# Dodano CORRECTION_KEYWORDS (blokują MILESTONE gdy wykryte):
CORRECTION_KEYWORDS = {
    'nigdy tego', 'nigdy bym', 'to nieprawda', 'pomyliłaś', 'pomylił',
    'mylisz się', 'to nie tak', 'źle pamiętasz', 'nie pamiętasz',
    'wcale nie mówiłem', 'nie powiedziałem', 'błędnie', 'masz błędną',
    'nie mówiłem że', 'poprawiam cię', 'to było inaczej',
}

# Dodano FACT:correction w ENTITY_DEFINITIONS z przykładami
# Dodano blokadę w _find_best_match():
if entity_type == 'MILESTONE' and any(kw in text_lower for kw in CORRECTION_KEYWORDS):
    continue
```

**main.py** — SUPERSEDE_TYPES:
```python
('FACT', 'correction'),  # stara korekta zastąpiona nową
```

#### Expected behavior change
```
# PRZED:
Łukasz: "Nie, nigdy bym nie powiedział Earl Grey. Czarna albo miętowa."
→ MILESTONE:trust_declaration (score 1.0+ po milestone boost)
→ Kolejne RAG: zwraca trust_declaration jako "wspomnienie"

# PO:
Łukasz: "Nie, nigdy bym nie powiedział Earl Grey. Czarna albo miętowa."
→ FACT:correction (score ~0.5–0.7)
→ Kolejne RAG: zwraca korektę jako fakt, model wie że Earl Grey był błędem
```

#### Test case
```
1. Powiedz Astrze coś nieprawdziwego (lub pozwól halucynować)
2. Napisz: "Nie, mylisz się. To nieprawda, mówiłem X nie Y"
3. Sprawdź logi: [ASTRA] Extracted X entities → powinno być FACT:correction
4. Następna sesja: zapytaj o ten fakt → sprawdź czy korekta jest w RAG
```

#### Ryzyka / follow-ups
- **CORRECTION_KEYWORDS są za restrykcyjne** dla krótkich korekcji. Zdania jak "nie, błąd" lub "nope" nie zostaną wyłapane. Opus wskazał to wprost: *"dodaj krótsze formy korekt ('nie,', 'nope', 'błąd') w następnej iteracji jeśli zauważysz że krótkie korekty są przegapiane".*
- Obserwować czy `FACT:correction` jest retrieval-friendly — embedding "nie, nigdy bym nie powiedział X" może mieć niskie similarity do query "jaka herbata". Rozważyć syntetyczny text w pipeline: `[FACT:correction] herbata: nie Earl Grey, czarna lub miętowa`.

---

### Fix #5 — Per-type recency decay
**Commit:** `c768b46`
**Pliki:** `backend/vector_store.py`, `backend/memory_enricher.py`

#### Problem
- **Symptom:** Stare, ważne fakty (Crohn, imiona bliskich) mogły być wypychane przez nowsze emocjonalne wektory bo reranker używał jednolitego half-life = 7 dni dla WSZYSTKIEGO.
- **Root cause:** `RECENCY_HALF_LIFE_DAYS = 7` flat. Wektor o Crohnie sprzed 30 dni miał `recency_score = 0.5^(30/7) ≈ 0.05` — niemal zerowy. Świeższe ale mniej ważne emocje dominowały.

#### Zmiana

**vector_store.py:**
```python
# PRZED:
RECENCY_HALF_LIFE_DAYS = 7  # dla wszystkiego

# PO:
RECENCY_HALF_LIFE_DAYS = 7  # fallback
RECENCY_HALF_LIFE_BY_TYPE = {
    'ephemeral':      3,     # emocje — blakną szybko
    'short_term':    14,     # wizyty, daty
    'long_term':     60,     # preferencje, fakty
    'permanent':    None,    # miłość, milestony — brak decay
    'permanent_fact': None,  # Crohn, chroniczne — brak decay (przyszłość)
}
# rerank() czyta temporal_type z metadata → wybiera odpowiedni half_life
```

**memory_enricher.py:**
```python
'FACT': {
    'health': 'permanent',      # Crohn jest permanentny (było: 'long_term')
    'correction': 'long_term',  # korekty przetrwają 60 dni (nowe)
    ...
}
```

#### Expected behavior change
- Wektory o Crohnie (FACT:health) mają teraz `temporal_type='permanent'` → `recency_score=1.0` zawsze
- Emocje (EMOTION, `temporal_type='ephemeral'`) blakną po 3 dniach → przestają dominować RAG
- Preferencje (FACT:preference, `temporal_type='long_term'`) trzymają się 60 dni

#### Test case
```bash
# Sprawdź czy Crohn-wektory mają permanent:
# (przez /api/debug/rag lub bezpośrednio ChromaDB)
# Szukaj: metadata.temporal_type = 'permanent' dla FACT:health
```

#### Ryzyka

**⚠️ MIGRACJA — patrz sekcja 3**

---

## 3. MIGRATION NOTES

### Fix #5 — istniejące wektory nie dostały permanent retrospektywnie

`temporal_type` jest zapisywany w metadata przy tworzeniu wektora przez `memory_enricher.py`.
**Zmiana w `memory_enricher.py` (FACT:health → permanent) dotyczy TYLKO nowych wektorów.**

Istniejące wektory o Crohnie w ChromaDB mają nadal `temporal_type='long_term'`.

**Skutek:** Stare wektory Crohna będą traktowane z half-life=60 dni (long_term) zamiast permanent.
To nadal dużo lepsze niż poprzednie 7 dni, ale nie jest idealne.

**Migracja opcjonalna** — jeśli chcesz ustawić permanent dla istniejących wektorów:
```python
# Uruchomić na VPS przez python3 -c lub osobny skrypt
import chromadb
client = chromadb.PersistentClient(path="/var/www/myastra/astra/backend/chroma_db")
col = client.get_collection("astra_memory_v1")

# Pobierz wszystkie wektory FACT:health
results = col.get(where={"$and": [
    {"entity_type": {"$eq": "FACT"}},
    {"entity_subtype": {"$eq": "health"}}
]}, include=["metadatas", "documents", "embeddings"])

# Zaktualizuj temporal_type
for i, doc_id in enumerate(results['ids']):
    meta = results['metadatas'][i]
    meta['temporal_type'] = 'permanent'
    col.update(ids=[doc_id], metadatas=[meta])
    print(f"Updated: {doc_id}")

print(f"Done: {len(results['ids'])} vectors updated")
```
**Uwaga:** Przed uruchomieniem zrób backup chroma_db/ lub snapshot.

### Fix #2 — Holo/Menma/Nazuna NIE mają wektorów PERSON

Postacie zostały dodane do `lukasz_core.json` (twarde fakty) — działa natychmiast.
Wektory PERSON dla Holo/Menma/Nazuna w `astra_memory_v1` nadal NIE istnieją.

**Skutek:** Przy pytaniach semantycznych o konkretne postacie (np. "powiedz mi o Holo") RAG nie znajdzie wektorów z rozmów — będzie korzystał tylko z `lukasz_core.json`. To wystarczy dla podstawowych pytań.

**Re-ekstrakcja:** Wektory PERSON powstaną naturalnie gdy Łukasz w kolejnych rozmowach wspomni te postacie przy słowach z FICTION_CONTEXT_WORDS lub ich imionach. Nie wymaga ręcznej akcji.

**Ręczna indeksacja** (opcjonalna, jeśli chcesz wcześniej):
```python
# Wstrzyknij wektory dla znanych postaci ręcznie
# Użyć vector_store.add_memory() z odpowiednimi metadata
# entity_type='PERSON', entity_subtype='positive_person', source='extracted_person'
# importance=8, temporal_type='permanent'
```

---

## 4. KNOWN LIMITATIONS / FOLLOW-UPS

### Nie naprawione w tej sesji (z audytu 22 Apr)

| Bug | Priorytet z audytu | Status |
|-----|-------------------|--------|
| Brak "nie wiem" grounding dla FACT queries | KRYTYCZNY | **Częściowo** — FACT:correction zmniejsza pętlę, ale Astra nadal może halucynować gdy brak RAG hit i brak CORRECTION_KEYWORDS |
| Milestone boost +1.0 structural bug | WYSOKI | NIE naprawiony — milestony nadal dominują RAG |
| BM25 hybrid retrieval | WYSOKI | NIE — Faza 1, potrzebuje nowej biblioteki |
| session_history okno n=10 | ŚREDNI | NIE — w MEMORY.md jako TODO, ale MEMORY.md wskazuje n=30 (może być już naprawione) |
| Topical relevance w strict_grounding | ŚREDNI | NIE — Opus miał to jako Fix #3, pominęliśmy na rzecz FACT:correction |

### Follow-ups do następnej iteracji

1. **CORRECTION_KEYWORDS krótkie formy** — dodać `'nie,'`, `'nope'`, `'błąd'` gdy zaobserwowane przegapywanie (wskazane przez Opusa)

2. **Topical relevance w strict_grounding.py** — gdy RAG zwraca wektory niepowiązane tematycznie z pytaniem, grounding_directive powinien to wykryć i powiedzieć modelowi "te wspomnienia nie dotyczą pytania". Aktualnie grounding jest distance-based only.

3. **Milestone boost refactor** — `final_score += 1.0` po cap do 1.0 daje zakres 1.0–2.0 dla milestoneów vs 0.5–0.7 dla faktów. Structural unfairness. Fix: osobny kanał retrieval dla milestoneów (Faza 1).

4. **Embeddings upgrade** — `paraphrase-multilingual-MiniLM-L12-v2` to lekki model. `bge-m3` da znacznie lepsze polskie embeddingi. Wymaga re-indeksacji całego ChromaDB. Czeka na decyzję o skali.

5. **ChromaDB → Qdrant migration** — gdy baza przekroczy ~50k wektorów i/lub pojawi się multi-user (Gwiazdka). Qdrant daje lepszą wydajność + filtry. Nie teraz.

6. **FACT:correction retrieval quality** — embedding zdania korekcji ("nie, nigdy bym nie powiedział Earl Grey") może mieć niskie similarity do query "herbata". Rozważyć syntetyczny text: `[FACT:correction] herbata: nie Earl Grey — czarna lub miętowa`.

---

## 5. METRICS / OBSERWACJA

### Jak sprawdzać czy fixy działają

**Fix #1 (nocna_analiza):**
```bash
journalctl -u myastra --since "$(date -d 'yesterday 02:55' +'%Y-%m-%d %H:%M')" --until "$(date -d 'yesterday 03:15' +'%Y-%m-%d %H:%M')" --no-pager
# Szukaj: brak AttributeError, obecność nocnej analizy
```

**Fix #2 (rodzina):**
- Napisz do Astry: "Kto jest w naszej rodzinie?" → musi wymienić Holo/Menma/Nazuna
- Po kilku rozmowach gdzie Łukasz wspomni postacie: sprawdź `/api/debug/rag` czy pojawiają się PERSON wektory

**Fix #3 (safe_haven):**
```bash
journalctl -u myastra --no-pager | grep "safe_haven="
# Sprawdź czy pojawia się safe_haven=physical lub safe_haven=emotional
```

**Fix #4 (FACT:correction):**
```bash
journalctl -u myastra --no-pager | grep "FACT:correction"
# Sprawdź czy korekty są ekstrahole jako FACT:correction
```

**Fix #5 (recency):**
```bash
journalctl -u myastra --no-pager | grep "recency"
# Lub przez /api/debug/rag: sprawdź _score_detail.recency dla FACT:health
# Powinno być 1.0 lub bliskie 1.0 niezależnie od wieku wektora
```

### Czerwone flagi (kiedy wiedzieć że coś się zepsuło)

- `AttributeError` w logach → sprawdź czy zmiany w dataclass `CompanionState` są spójne
- `JSONDecodeError` przy każdej wiadomości → Gemini zwraca non-JSON, sprawdź `INNER_MONOLOGUE_INSTRUCTION`
- `safe_haven` zawsze `"none"` → Gemini ignoruje nowy schemat — sprawdź czy instrukcja jest poprawnie wstrzyknięta
- FACT:correction nigdy nie pojawia się w logach przy oczywistych korekcjach → CORRECTION_KEYWORDS nie trafiają
- Serwis crashuje przy starcie → syntax error w jednym z plików backend

---

## 6. CONVERSATION LOG REFERENCE

### Ta sesja
- **Główny wątek:** Claude Sonnet 4.6 (Claude Code CLI, sesja 2026-04-22/23/24)
- **Zewnętrzny audyt:** Claude Opus (sesja równoległa, wiadomość przekazana przez Łukasza)
- **Wkład Opusa:** Propozycja 3 fixów (safe_haven split, per-type recency, grounding). Sonnet skorygował kolejność (dodał nocna_analiza i FACT:correction jako priorytetowe, zamienił grounding fix na FACT:correction jako głębsze rozwiązanie).
- **Audyt empiryczny:** Łukasz przeprowadził samodzielnie 2026-04-22 przez `/api/debug/rag` → zapisane w `AUDYT_CLAUDE_22KWIETNIA.md`

### Poprzednie kluczowe sesje
- `C:\Users\lpisk\Projects\astra\evolution_log_2026_03_31.md` — sesja 31 marca (Blueprint 2.2)
- `logi i transformacja/logi/astra_backend_logi_7apr_22apr.txt` — 5591 linii logów Apr 7–22
- `logi i transformacja/logi/astra_peak_performance_okon_19apr.md` — moment "okoń" (Astra at peak)
- `logi i transformacja/logi/astra_rag_failures_19apr.md` — udokumentowane failure'y z 19 Apr
