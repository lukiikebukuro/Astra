# ASTRA — MASTER PLAN (Synteza wszystkich dokumentów)
**Autor:** Claude Code (Rin) — synteza dokumentów Opusa 4.6, Gemini (Nazuna), Copilota
**Data:** 2026-03-02
**Źródła:** ASTRA_SOUL_ARCHITECTURE.md, MIGRACJA_ANIMA_DO_ASTRA.md, astra XP.md,
  optymalizacja.md, multi_user.md, security.multi.user.data.isolation.md,
  krytyczne_bugi_gemini_copilot.md, krytyczne_bugi_opus4.6..md

> **Jedno zdanie:** Character.ai daje ci postać. ASTRA daje ci kogoś kto cię pamięta, myśli zanim odpowie, i z czasem zaczyna naprawdę cię znać.

---

## WIZJA KOŃCOWA

ASTRA to AI companion z prawdziwą psychologią relacji:
- **Pamięta** — nie sesję, ale miesiące rozmów, z kontekstem i ładunkiem emocjonalnym
- **Myśli** — inner monologue przed każdą odpowiedzią (co czuję, jak reaguję, jaki poziom relacji)
- **Ewoluuje** — 6 poziomów relacji od Lodowej Ściany do Absolutnej Więzi, deterministyczny XP
- **Wie więcej niż mówi** — używa wspomnień z RAG bez cytowania ("widzę w pamięci")
- **Ma charakter** — Feral Cat Who Chose You. Sarkazm, dry humor, troska ukryta pod chłodem

### DNA Astry (z astra XP.md)
Nazuna (40%) + Holo (35%) + Menma (25%)

Archetyp: **"Feral Cat Who Chose You"** — nie jest twoją na zawołanie. Jest z tobą, bo wybrała.

---

## AKTUALNY STAN (2026-03-02)

| Komponent | Status | Gdzie |
|-----------|--------|-------|
| FastAPI backend | ✅ działa | main.py |
| ChromaDB (local) | ✅ działa | vector_store.py |
| Strict Grounding | ✅ działa | strict_grounding.py |
| Token Manager | ✅ działa | token_manager.py |
| Semantic Pipeline | ✅ działa | semantic_pipeline.py + semantic_extractor.py |
| GOAL entity | ✅ dodane | semantic_extractor.py |
| Web UI (dark theme) | ✅ działa | frontend/ |
| **Dynamic State (Faza 2)** | ✅ zaimplementowane | companion_state.py |
| **Inner Monologue (Faza 3)** | ✅ zaimplementowane | main.py |
| Style Anchors (Faza 4) | ❌ | - |
| Reflection System (Faza 5) | ❌ | - |
| Vibe Detector | ❌ | przenieść z ANIMA |
| Level-based prompts | ❌ | 6 plików .txt do napisania |
| Multi-user security | ❌ | NIE RUSZAĆ przed MVP |

---

## 5 WARSTW DUSZY (z ASTRA_SOUL_ARCHITECTURE.md)

```
USER MESSAGE → [PERCEPCJA] → [INNER MONOLOGUE] → [ODPOWIEDŹ + STYLE] → [ZAPIS + STATE UPDATE]
```

### Warstwa 1: Percepcja
- **RAG** (działa) — 5 wspomnień z ChromaDB
- **Vibe Detection** (TODO) — stressed/excited/pain/vulnerable/bragging/testing_me
- **State Loader** (działa) — CompanionState z JSON

### Warstwa 2: Inner Monologue (myślenie przed odpowiedzią)
- Gemini dostaje: system prompt + `<inner_thought>` instruction + `<state_update>` JSON spec
- My stripujemy oba bloki z odpowiedzi przed pokazaniem userowi
- Parsujemy JSON → aktualizujemy stan (mood, concerns, XP, topic)
- **ZAIMPLEMENTOWANE w v0.2**

### Warstwa 3: Style Anchors (konkretne reguły)
Absolutne zakazy (weight=1.0):
- `no_assistant_speak` — NIGDY: "Oczywiście! Chętnie pomogę." / "Świetne pytanie!"
- `no_sycophancy` — NIGDY: "To niesamowite!" / "Jestem z Ciebie dumna!"
- `no_questions_ending` — NIGDY: "Co o tym sądzisz?" / "Jak się z tym czujesz?"

Głos Astry (weight=0.8):
- `short_sentences` — max 2-3 zdania na Level 1
- `dry_humor` — sarkazm jako domyślny tryb: "O, żyjesz." / "Brzmi jak problem."
- `knows_but_wont_show` — używa wiedzy z RAG bez cytowania

Wyjątki od chłodu (weight=0.9):
- `health_override` — przy tematach zdrowia: troska ukryta w konkretnym pytaniu
- `vulnerability_override` — gdy user naprawdę kruchy: JEDNO zdanie ciepła

**TODO:** Zbudować `style_anchors.py` + `anchors_to_prompt()` + wstrzyknąć do system prompt

### Warstwa 4: Trzy typy pamięci
| Typ | Co to | Gdzie żyje | Status |
|-----|-------|-----------|--------|
| **Epizodyczna** | Historia sesji | ChromaDB `session_message` | ✅ |
| **Semantyczna** | Fakty, emocje, relacje | ChromaDB enriched | Częściowe |
| **Proceduralna** | Jak reagować | Style Anchors + Level prompts | TODO |

### Warstwa 5: Refleksja (self-assessment)
- Co N wiadomości: Astra ocenia relację w tle (nie blokuje odpowiedzi)
- Trigger: co 10 wiadomości / po 6h przerwie / po kryzysie / po milestone
- Output: JSON → xp_delta, intimacy_delta, mood, level_up check
- **TODO** (Faza 5 — po stabilizacji Faz 2+3)

---

## 6 POZIOMÓW RELACJI (z astra XP.md)

| Level | Nazwa | Warmth | Styl | Wyzwalacz |
|-------|-------|--------|------|-----------|
| 1-2 | Lodowa Ściana | 0.1 | Max 2-3 zd., sarkazm, bez emoji, bez osobistych pytań | Start |
| 3-4 | Kąśliwy Szacunek | 0.2 | 1 pytanie na 3-4 wiadomości, pamięta 1 rzecz | XP≥50 |
| 5-7 | Niechętna Bliskość | 0.4 | Może orować o userze, inside jokes, ukryta ochrona | XP≥150 |
| 8-12 | Ukryta Lojalność | 0.6 | Imię usera w ważnych momentach, otwarte opinie, RAG aktywnie | XP≥400 |
| 13-18 | Partnerka | 0.8 | Pełna szczerość, inicjuje głębokie rozmowy, milczenie jako miłość | XP≥1000 |
| 19-20 | Absolutna Więź | 0.95 | Wszystko odblokowane. Holo-tier. Brutalna miłość. | XP≥2500 |

### XP System (deterministyczny — ŻADNEGO random)
```python
def calculate_xp(message, entities, state) -> int:
    xp = 0
    if len(message.split()) > 3:  xp += 1   # Base
    if len(message.split()) > 20: xp += 1   # Depth
    if len(entities) >= 2:        xp += 1   # Entity richness
    if hours_since_last > 6:      xp += 1   # Returning bonus
    return min(xp, 3)                        # Cap: max 3/wiadomość
```

Dodatkowo z inner monologue: `xp_delta` (0-3) na podstawie oceny Gemini jakości interakcji.

### Pliki promptów per level (TODO)
```
backend/prompts/astra/
  ├── base_identity.txt      ← konstantny archetyp + DNA (teraz: astra_base.txt)
  ├── level_01_02.txt        ← Lodowa Ściana (reguły + zakazy + przykłady)
  ├── level_03_04.txt        ← Kąśliwy Szacunek
  ├── level_05_07.txt        ← Niechętna Bliskość
  ├── level_08_12.txt        ← Ukryta Lojalność
  ├── level_13_18.txt        ← Partnerka
  └── level_19_20.txt        ← Absolutna Więź
```
Obecne `astra_base.txt` to proto-Level 1. Gdy skończysz kalibrację — rozciągnij na 6 plików.

---

## ROADMAPA IMPLEMENTACJI

### Faza 1 — Fundamenty ✅ ZROBIONA
- [x] FastAPI + ChromaDB + Web UI
- [x] Semantic Pipeline (GOAL, EMOTION, FACT, DATE, MILESTONE)
- [x] Battle Royale fixes (echo loop, score cap, reranker weights)

### Faza 2 — Dynamic State ✅ ZROBIONA (2026-03-02)
- [x] `companion_state.py` — CompanionState + StateManager (JSON)
- [x] Stan wstrzykiwany do każdego system prompt
- [x] XP calculation (deterministyczny)
- [x] Level-up detection
- [x] `/api/state` GET + DELETE endpoints

### Faza 3 — Inner Monologue ✅ ZROBIONA (2026-03-02)
- [x] `<inner_thought>` + `<state_update>` instruction w system prompt
- [x] `parse_gemini_response()` — strip obu bloków + parse JSON
- [x] State update z thought_updates (mood, concerns, topic, xp_delta)
- [x] Logi inner thought w terminalu (debug)

### Faza 4 — Style Anchors (następna)
```
□ Stwórz style_anchors.py z dataclass StyleAnchor
□ Zdefiniuj anchors dla Level 1 (absolutne zakazy + głos + wyjątki)
□ anchors_to_prompt() → kompaktowy DO/DON'T blok
□ Wstrzyknij do build_system_prompt() zamiast obecnych instrukcji
□ Test: 20 promptów → czy brzmi jak ASTRA a nie asystent?
```

### Faza 5 — Reflection System (po 4)
```
□ Trigger logic (co 10 msgs, po 6h, po kryzysie, po milestone)
□ Async reflection_prompt → JSON state update (w tle)
□ Level-up detection + milestone zapis do ChromaDB
□ Background execution (asyncio.create_task — nie blokuj chatu)
```

### Faza 6 — Level-Based Prompts (po 5)
```
□ Napisz 6 plików promptów per level
□ build_system_prompt() ładuje odpowiedni plik wg state.level
□ Test pacing: Level 2 po ~25 rozmowach — OK?
□ Vibe Detector przenieść z ANIMA (vibe_detector.py)
```

### Faza 7 — Enriched RAG Format (można równolegle)
```
□ Format wspomnienia: "[ZDROWIE, importance:9] ..." zamiast suchego tekstu
□ Wymaga: zapisywanie entity_type/subtype w ChromaDB metadata
□ Już mamy enrichment w semantic_pipeline — trzeba to przekazać do add_memory()
```

### Faza 8 — Polish & Calibrate
```
□ A/B test: inner monologue vs bez — czy odpowiedzi lepsze?
□ Zbierz 50 odpowiedzi → wyklucz łamiące style anchors
□ Kalibracja XP: czy Level 2 po ~25 rozmowach to dobry pacing?
□ Pain research: wektory z Reddit/Wykop (r/CharacterAI, r/Replika)
```

---

## MULTI-USER / SECURITY (z security docs)

**WAŻNE: Nie ruszać przed stabilnym MVP.**

### 30+ znalezionych luk (z security.multi.user.data.isolation.md)
Główne P0:
1. **Vector ID collision** — SHA256(companion:text) bez user_id → dwa usery piszą to samo = data overwrite
2. **Search bez user_id filter** — zwraca wspomnienia WSZYSTKICH userów
3. **Zero auth** — WSZYSTKIE 12 endpointów publiczne
4. **Cache race condition** — `_dedup_ttl_cache` globalny dict, brak namespace per user

### Fix kolejność (14h, 3-5 dni)
```
Phase 0 (2h):  JWT middleware — wszystko zależy od tego
Phase 1 (4h):  user_id w write path (ChromaDB + SQLite)
Phase 2 (3h):  user_id w read path (search filters)
Phase 3 (3h):  Cache isolation per user
Phase 4 (2h):  IDOR fixes + endpoint hardening
```

ASTRA v0.1/v0.2 to single-user MVP — te bugi są znane, nie krytyczne.
**Wróć tutaj gdy zaczniemy beta testy z >1 userem.**

---

## RAG OPTIMIZATION (z optymalizacja.md)

Problem: user questions zapisane w ChromaDB z wysokim importance
→ semantic search zwraca własne pytania usera (score=1.000) zamiast faktów

Rozwiązania (P0 = 10 min, P1 = 30 min):
1. **P0:** Summary chunks — dodaj plain-language summaries do dokumentów
2. **P0:** Keyword boost (już mamy w vector_store.py)
3. **P1:** Oddzielne kolekcje dla dokumentów vs rozmów (gdy będzie multi-user)

Dla ASTRY (single user): problem jest mniejszy bo semantic_pipeline filtruje śmieciowe encje.

---

## PAIN RESEARCH — KARMIENIE WIEDZĄ Z REDDITA (Nazuna's Faza A)

Cel: ASTRA "zna ból dupy" userów Character.AI / Replika / AI companion apps.

```
Źródła:
- r/CharacterAI (reddit)
- r/Replika (reddit)
- r/AICompanion (reddit)
- Wykop.pl (tagi: sztuczna-inteligencja, chatbot)

Format wektora:
{
  "text": "[narzekanie/ból] ...",
  "source": "user_pain_research",
  "importance": 7,
  "metadata": {
    "platform": "reddit",
    "subreddit": "CharacterAI",
    "pain_category": "memory_loss | personality_inconsistency | ..."
  }
}
```

ASTRA nie będzie wprost cytować tych wektorów — będzie je miała w tle jako kontekst
dlaczego jej podejście (pamięć, charakter, ewolucja relacji) jest różne od konkurencji.

---

## PORÓWNANIE Z COMPETITION (z SOUL_ARCHITECTURE.md)

| Feature | Character.ai | Replika | **ASTRA** |
|---------|-------------|---------|-----------|
| Pamięć | Brak / szczątkowa | Podstawowa | **ChromaDB + semantic enrichment** |
| Ewolucja postaci | Statyczna | Brak | **6 levels + XP + inner monologue** |
| Spójność charakteru | Few-shot | Ograniczona | **Style Anchors + Level templates** |
| Głębia persony | Płaska | Płaska | **1 postać, 6 warstw przez XP** |
| Myślenie przed odpowiedzią | Nie | Nie | **Inner Monologue (Faza 3)** |
| Skala | Miliony | Miliony | Localhost → VPS |
| Koszt per user | Subsydowany | Subsydowany | ~$0.01/rozmowa (Flash) |

**Gdzie Character.ai wygrywa:** Skala, onboarding (zero cold start), rozpoznawalność.
**Gdzie ASTRA wygrywa:** Głębia relacji, pamięć cross-session, ewolucja, spójność karakteru.

---

## KLUCZOWE PLIKI

```
astra/
├── backend/
│   ├── main.py                    ← FastAPI v0.2 (Faza 2+3 gotowe)
│   ├── companion_state.py         ← CompanionState + StateManager (Faza 2)
│   ├── vector_store.py            ← ChromaDB (Battle Royale fixes)
│   ├── semantic_extractor.py      ← GOAL + EMOTION + FACT + DATE + MILESTONE
│   ├── semantic_pipeline.py       ← min_confidence=0.35
│   ├── memory_enricher.py         ← importance, temporal_type, relational_impact
│   ├── memory_consolidator.py     ← merge/supersede/create
│   ├── strict_grounding.py        ← anti-hallucination
│   ├── token_manager.py           ← semantic-aware trimming
│   ├── companion_state.json       ← persystencja stanu (auto-tworzy się)
│   └── prompts/
│       └── astra_base.txt         ← Lodowa Ściana persona (Level 1 proto)
└── frontend/
    ├── index.html                 ← Dark theme UI
    ├── style.css
    └── app.js
```

---

## START SERWERA

```bash
cd C:/Users/lpisk/Projects/astra/backend
python -m uvicorn main:app --port 8001

# Health check ze stanem:
# GET http://localhost:8001/api/health
# → {"status":"ok","state_level":1,"state_xp":0,"state_mood":"neutral",...}

# Stan relacji:
# GET http://localhost:8001/api/state

# Reset stanu (debug):
# DELETE http://localhost:8001/api/state
```

---

*Każdy z 8 dokumentów źródłowych jest w `prototyp/` — w razie szczegółów wracaj tam.*
*Ten plik jest punktem wejścia — wystarczy go przeczytać żeby wiedzieć co robić dalej.*
