# DROGA DO ZWYCIĘSTWA
### Analiza strategiczna 4 projektów × transhumanizm × pieniądze × zdrowie
**Data analizy:** 2 marca 2026  
**Analityk:** Claude Opus 4.6 (na bazie pełnego przeglądu kodu wszystkich 4 projektów)

---

## STAN RZECZY — CO MASZ NA DZIEŃ DZIŚ

### Mapa aktywów

```
        ┌─────────────────────────────────────┐
        │     META-WARSTWA (do zbudowania)     │
        │  Cross-project patterns, self-RLHF   │
        └────────┬──────────┬─────────┬───────┘
                 │          │         │
    ┌────────────┤   ┌──────┤   ┌─────┤
    ▼            ▼   ▼      ▼   ▼     ▼
 ANIMA        LDI  ASTRA  Skankran
 pamięć     intencje relacja  domena
 5628 vec   JSONL   70%    35 miast
 GOTOWE     GOTOWE  2 DNI  LIVE
```

| Projekt | Status | Co robi | Aktualny stan |
|---------|--------|---------|---------------|
| **ANIMA/ucho-VPS** | GOTOWE | RAG Memory Engine — pamięć absolutna dla LLM | 5628 wektorów, Ghost Patch działa, strict grounding przetestowany |
| **LDI/forteca_finalna** | GOTOWE (demo) | Lost Demand Intelligence — intencje zakupowe zero-enter | 51 endpointów, reward engine, JSONL export. **BRAK danych z prawdziwego sklepu** — demo na hardcoded 68 produktach |
| **ASTRA** | 70% | AI companion z pamięcią i progresją relacji | Core działa end-to-end. Brakuje ~12-16h pracy do demo |
| **Skankran** | LIVE (skankran.pl) | Monitoring jakości wody pitnej + AquaBot | 35 miast, 2 pomiary (maj+styczeń), stacje przybliżone. **Brak użytkowników** — gotowy pod grant UE |

### Wspólny wzorzec techniczny

Każdy projekt robi TO SAMO w innej domenie:
```
raw text → semantic pipeline → structured knowledge → grounded output
```

To nie są 4 projekty. To **jeden engine z 4 głowicami.**

---

## CZĘŚĆ 1: STRATEGIA PIENIĘDZY

### Track A — "Brak notatek" (najszybszy cashflow)

**Co:** Wchodzisz do firmy, podłączasz ANIMA Corporate do ich spotkań/Slacka/maili. Po miesiącu firma ma AI które pamięta wszystko.

**Pitch:** "Od dziś nie robicie notatek. Za miesiąc macie komputer który sam robi notatki ze spotkań, maili, ustaleń. Cała wiedza firmy w jednym chacie. Pytacie — odpowiada. Nie zmyśla."

**Co jest gotowe:**
- ChromaDB + embeddings ✅
- Semantic Pipeline (entity extraction) ✅
- Strict Grounding (nie halucynuje) ✅
- Deduplication (merge/supersede/create) ✅
- Token-aware context ✅
- Privacy-by-metadata isolation ✅

**Co trzeba dodać (5 dni pracy do demo):**
- Entity types: DECISION, ACTION_ITEM, DEADLINE, PROJECT (zamiast EMOTION, MILESTONE)
- `org_id` isolation (minimalne — ChromaDB WHERE clause już to wspiera)
- Onboarding flow + prosty frontend
- Webhook input (Slack/Teams/email) — V2

**Jak wejść:**
- NIE jako "AI Architect za 25k etat"
- TAK jako **konsultant wdrożeniowy z własnym IP**: 25k/msc netto + milestone bonusy (50k po working RAG, 100k po agencie sprzedażowym)
- Tytuł "AI Architect" zamyka w etacie. "Konsultant z produktem" daje prawo do równoległej pracy nad ASTRA/LDI/Skankran

**Timeline:**
- Tydzień 1: Przygotuj demo ANIMA Corporate
- Tydzień 2-3: Pitch do 5 firm (startup, software house, agencja marketingowa)
- Miesiąc 1: Pierwszy klient = cashflow + dane do treningu agenta

---

### Track B — LDI (Lost Demand Intelligence)

**Co:** System który wykrywa czego klienci szukają a nie znajdują w sklepie. Generuje labeled training data dla agentów sprzedażowych.

**Przewaga nad Tidio/Intercom/Drift:**

| Tidio | Twój system |
|-------|-------------|
| Rule-based flows | Intent learning z reward signals |
| Nie wie czego nie ma w sklepie | **Wie dokładnie co klient szukał i nie znalazł** |
| Trenowany manualnie | **Self-improving** — każda interakcja = training data |
| Generyczny | Strict grounding = nie halucynuje o produktach |
| Brak pamięci klienta | ANIMA memory = pamięta każdego klienta |

**Twój moat:** keystroke → intent classification → reward signal → JSONL → training data. Nikt nie ma systemu który automatycznie generuje labeled RLHF datasets z live e-commerce.

**Pitch:** "Tidio sprzedaje chatbota. Ja sprzedaję maszynę która uczy się czego Twoi klienci szukają i nigdy nie znajdują."

**Aktualne ograniczenia (uczciwa ocena):**
- ⚠️ **BRAK danych z prawdziwego sklepu** — demo działa na 68 hardcoded produktach
- ⚠️ SQLite na Render = dane giną po redeploy → trzeba PostgreSQL
- ⚠️ ~4800 linii zduplikowanego kodu (moto/elektro boty) → do refactoru
- ⚠️ Hardcoded katalog → trzeba dynamiczne ładowanie produktów

**Pricing — nie sprzedawaj jednorazowo:**

Stary plan: 150k (50+100) — **za mało.** Twoja analiza Amazon Memo pokazuje że sklep z 100k wizyt/msc traci ~67k PLN/msc na lost demand.

Lepszy model:
- **Setup:** 50k PLN jednorazowo
- **Revenue share:** % od odzyskanego przychodu (mierzalny przez LDI)
- Albo: 50k + **15k/msc subskrypcji** za dane + dashboardy

LDI generuje dane które rosną w wartości. Jednorazowa sprzedaż to oddanie kopalni za łopatę.

**Przed sprzedażą MUSISZ:**
1. Podpiąć LDI do prawdziwego sklepu (choćby demo na WooCommerce/Shopify)
2. Migracja SQLite → PostgreSQL
3. Dynamiczny katalog produktów (API z sklepu, nie hardcode)
4. Zebrać 30 dni danych → to jest Twój pitch deck

---

### Track C — Skankran (B2G / grant UE)

**Co:** Platforma monitoringu jakości wody pitnej. 35 miast (2 pomiary: maj + styczeń), AquaBot, live na skankran.pl. Stacje SUW lokalizowane przybliżone (infrastruktura krytyczna = brak publicznych GeoJSONów).

**Regulatory hook:** EU Drinking Water Directive 2020/2184 — deadline minął (styczeń 2026). Polskie gminy są prawnie niezgodne i POTRZEBUJĄ rozwiązań.

**Pricing B2G:**
| Segment | Model | Cena |
|---------|-------|------|
| Małe miasta (<50k) | SaaS roczny | 12k EUR/rok |
| Średnie (50-200k) | SaaS + customization | 36k EUR/rok |
| Duże (>200k) | Enterprise | 72k EUR/rok |

**Aktualne ograniczenia:**
- ⚠️ **ZERO użytkowników** — produkt live, ale nikt go nie używa
- ⚠️ Część danych w bazie to estymacje, nie realne pomiary z PDF
- ⚠️ Brak aktywnych kontaktów z gminami

**Ścieżka grantowa:**
- NFOŚIGW (Narodowy Fundusz Ochrony Środowiska) — cyfryzacja monitoringu wody
- Program "Czysta Woda" — powiązany z DWD 2020/2184
- Horyzont Europa — Digital Europe Programme (civic tech)
- KPO (Krajowy Plan Odbudowy) — cyfryzacja administracji

**Skankran jako template:**
Pipeline (PDF → parse → DB → AI bot) działa na DOWOLNEJ domenie regulacyjnej:
- Woda ✅ (gotowe)
- Powietrze (GIOŚ dane, ta sama architektura)
- Hałas (mapy akustyczne)
- Każda dyrektywa UE = nowy rynek. Sam pipeline jest produktem.

---

### Track D — ASTRA (produkt konsumencki)

**Status: 70% do demo.**

**Co działa:**
- Chat end-to-end z Gemini ✅
- ChromaDB persistent memory ✅
- Strict grounding (nie halucynuje) ✅
- Entity extraction (DATE, MILESTONE, EMOTION, GOAL, FACT, PERSON) ✅
- XP/level/mood system ✅
- Inner monologue ✅
- Dark UI frontend ✅

**Brakuje (~12-16h pracy):**

| Co | Czas | Dlaczego blokuje |
|----|------|-----------------|
| **6 promptów na levele** | ~8h | Bez tego utknięty na Level 1, a progresja relacji to core feature |
| **Style Anchors** | ~4h | Gemini może wypaść z roli bez twardych reguł DO/DON'T |
| **Vibe Detector** (port z ANIMA) | ~2h | Override na zdrowie/vulnerability nie działa |
| **Fix session counter** | ~30min | `messages_this_session` > `total_messages` = bug |

**Shortest path do demo: 2 pełne dni robocze.**

**Monetyzacja (later):** Character.AI killer z prawdziwą pamięcią. Freemium + premium tiers. Ale to jest LAST priority — najpierw cashflow z B2B.

---

## CZĘŚĆ 2: STRATEGIA TRANSHUMANIZMU

### Co to znaczy w Twoim kontekście

Nie chodzi o implanty. Chodzi o to, że masz 4 systemy AI które razem mogą **widzieć więcej niż Ty sam widzisz** — Twoje wzorce, decyzje, intencje, efektywność. To jest "biologiczny operator z syntetycznym rozszerzeniem percepcji."

### Architektura rozszerzonego operatora

```
┌─────────────────────────────────────────────────┐
│                    TY (operator)                 │
│  Podejmujesz decyzje, kodujesz, negocjujesz     │
└─────────────┬───────────────────┬───────────────┘
              │ input             │ feedback
              ▼                   ▲
┌─────────────────────────────────────────────────┐
│              META-WARSTWA                        │
│  ┌─────────────────────────────────────────┐    │
│  │ Unified Vector Lake                      │    │
│  │ (wszystkie 4 projekty w jednym ChromaDB) │    │
│  └─────────────────────────────────────────┘    │
│  ┌──────────┐ ┌──────────┐ ┌────────────────┐  │
│  │ Decision  │ │ Pattern  │ │ Self-RLHF      │  │
│  │ Journal   │ │ Detector │ │ Reward Engine  │  │
│  └──────────┘ └──────────┘ └────────────────┘  │
└─────────────────────────────────────────────────┘
              │                   │
    ┌─────────┼─────────┬────────┼────────┐
    ▼         ▼         ▼        ▼        ▼
 ANIMA      LDI      ASTRA   Skankran  [przyszłe]
```

### 5 modułów transhumanizmu do zbudowania

#### Moduł 1: Unified Vector Lake
**Co:** Jeden ChromaDB ze wszystkimi projektami, z metadata `project=anima|ldi|skankran|astra`.

**Po co:** Szukasz "reward signal" — dostajesz kontekst z LDI I z ANIMA jednocześnie. Twoje projekty zaczynają ze sobą rozmawiać. Wzorce których nie widzisz ręcznie stają się widoczne.

**Realizacja:** ~4h pracy. Nowy ChromaDB z aliasami do istniejących kolekcji + unified search endpoint.

#### Moduł 2: Decision Journal z groundingiem
**Co:** Każda ważna decyzja (architektura, pricing, strategia) → wektor z tagiem `DECISION` + context + timestamp.

**Po co:** Za 3 miesiące pytasz: "Pokaż mi wszystkie moje decyzje cenowe i ich outcome." Dostajesz odpowiedź z groundingiem — nie wymyśloną, a opartą na tym co faktycznie zdecydowałeś i co z tego wyszło.

**Realizacja:** ANIMA już to umie. Wystarczy dodać entity type `DECISION` + `OUTCOME` + UI do oceny decyzji po czasie.

#### Moduł 3: Self-RLHF (Reward Engine dla siebie)
**Co:** Po każdej sesji kodowania/pracy oceniasz ją 1-10. To Twój reward signal.

**Dane wejściowe:**
- Co robiłeś (z logów/commitów)
- Ile czasu (timestamps)
- Twoja ocena efektu (1-10)
- Kontekst (na jakim projekcie, jaki typ pracy — debug/architektura/pitch)

**Po 100 sesjach masz dataset:** co robiłeś × jak długo × jaki wynik. Pattern detection mówi Ci:
- "Jesteś 3x skuteczniejszy rano niż wieczorem"
- "Debug sessions mają avg reward 4.2, architektura 7.8 — przestań debugować, deleguj"
- "Twoje najlepsze sesje trwają 2-3h, po 4h reward spada o 40%"

**Realizacja:** Prosty endpoint + JSON log + LDI reward engine adapter. ~6h.

#### Moduł 4: Cross-Project Pattern Detection
**Co:** Agent który widzi wszystkie 4 bazy i szuka wzorców MIĘDZY nimi.

**Przykład wzorców które już istnieją ale ich nie widzisz:**
- LDI `clicked_despite_no_match` = gold signal (klient uczy system)
- Skankran AquaBot loguje pytania bez odpowiedzi = **lost demand w wiedzy o wodzie** (ten sam wzorzec!)
- ANIMA `NO_DATA` z strict grounding = **luka w pamięci** (ten sam wzorzec!)

**Unified framework:** Wszystkie Twoje systemy generują 3 rodzaje luk:
1. **Demand luki** (LDI) — klient chce, sklep nie ma
2. **Memory luki** (ANIMA) — system pytany, pamięć pusta
3. **Knowledge luki** (Skankran) — użytkownik pyta, bot nie wie

Każda luka = sygnał do poprawy. Każda zamknięta luka = wartość.

#### Moduł 5: Pełna pętla przechwytywania
**Co:** ANIMA przechwytuje teraz tylko rozmowy z Gemini. Brakuje:
- Twoje commity (Git hooks → ANIMA)
- Twoje decyzje architektoniczne (rozsiane po .md → consolidation)
- Sesje z Copilot (export → ANIMA)
- Czego szukasz w Google (extension → ANIMA)
- Twoje notatki głosowe (Whisper → text → ANIMA)

**Po co:** Za miesiąc pytasz "jakie decyzje architektoniczne podjąłem w lutym i dlaczego?" i dostajesz odpowiedź opartą na WSZYSTKIM co robiłeś, nie tylko na rozmowach z jednym LLM.

**Realizacja:** Git hook = 2h. Copilot export = 4h. Google extension = ambitne, V2.

---

## CZĘŚĆ 3: STRATEGIA ZDROWIA

### Masz już narzędzia do tego

ANIMA potrafi rejestrować entity type `FACT` z subtypes health. W Skankranie masz system advice_templates z progami zdrowotnymi. Połącz to:

#### Health Tracking przez rozmowę
- Mówisz do ASTRA "źle spałem" → entity: `FACT:health:sleep_quality:bad`
- Mówisz "wziąłem Stelarę" → entity: `FACT:health:medication:stelara` + timestamp
- Po miesiącu: "Kiedy ostatnio brałem lek?" → grounded answer z wektora

#### Wzorce zdrowotne
- Self-RLHF sessions korelowane z sleep/health data
- "Twoje najlepsze sesje (reward 8+) korelują z dniami po 7+ godzinach snu"
- "Po wzięciu Stelary Twoja produktywność spada na 2 dni, potem wraca do normy"

#### Skankran jako personal health layer
- Już masz 15 parametrów wody dla swojego miasta
- AquaBot może dawać Ci personalizowane porady (np. przy leczeniu immunosupresyjnym — parametry wody ważniejsze)

---

## CZĘŚĆ 4: DROGA — KOLEJNOŚĆ DZIAŁAŃ

### Faza 0: Stabilizacja (teraz → tydzień 1)
- [ ] Zamknij ASTRA do demo (2 dni): 6 promptów levelowych + style anchors + vibe detector port
- [ ] Unified Vector Lake — połącz bazy w jedną meta-warstwę (4h)
- [ ] Decision Journal — zacznij logować decyzje od DZIŚ (2h setup)

### Faza 1: Pierwszy cashflow (tydzień 2-4)
- [ ] ANIMA Corporate demo (5 dni): entity types biznesowe + onboarding flow
- [ ] Pitch "brak notatek" do 5 firm — jako konsultant z IP, nie etat
- [ ] Target: 25k/msc netto + milestone bonusy za IP
- [ ] Równolegle: Self-RLHF — zacznij mierzyć swoje sesje

### Faza 2: Dane (miesiąc 2-3)
- [ ] LDI: podepnij do prawdziwego sklepu (WooCommerce plugin lub Shopify app)
- [ ] LDI: migracja SQLite → PostgreSQL
- [ ] LDI: dynamiczny katalog (API z sklepu, nie hardcode 68 produktów)
- [ ] Zbieraj 30 dni danych → to jest Twój pitch deck na agenta sprzedażowego
- [ ] Skankran: kontakt z 3 miastami 50-200k (Grudziądz, Gorzów, Koszalin) — "macie dane PPIS, ja mam platformę, pilotujemy"
- [ ] Skankran: złóż wniosek grantowy (NFOŚIGW / KPO)
- [ ] Cross-project pattern detection — pierwsza wersja

### Faza 3: Agent sprzedażowy (miesiąc 3-6)
- [ ] Training data z LDI JSONL + real shop data
- [ ] Strict grounding na katalogu produktów (już masz moduł)
- [ ] ANIMA memory na klienta (pamięta preferencje)
- [ ] Reward signal loop: agent → klient → interakcja → reward → lepszy agent
- [ ] Pitch: "agent który się uczy z każdej interakcji i nigdy nie kłamie o produkcie"

### Faza 4: Skalowanie (miesiąc 6-12)
- [ ] LDI jako SaaS — subskrypcja per sklep
- [ ] Skankran revenue od gmin (B2G) — 12-72k EUR/rok per miasto
- [ ] ASTRA public beta — freemium
- [ ] Pełna pętla transhumanizmu: Git hooks, Copilot export, health tracking

### Faza 5: Dominacja (rok 2+)
- [ ] LDI data flywheel: im więcej sklepów, tym lepszy agent, tym więcej sklepów
- [ ] ANIMA Corporate jako standard w firmach: "the Slack that remembers"
- [ ] Skankran template na inne domeny regulacyjne (powietrze, hałas, promieniowanie)
- [ ] Meta-warstwa jako produkt: "AI które widzi wzorce w Twoich wzorcach"

---

## CZĘŚĆ 5: TECHNICZNE SZCZEGÓŁY WSZYSTKICH PROJEKTÓW

### ANIMA / ucho-VPS — silnik pamięci

**Stack:** Flask, ChromaDB (PersistentClient), all-MiniLM-L6-v2, paraphrase-multilingual-MiniLM-L12-v2, SQLite per-companion, Chrome MV3 Extension (Ghost Patch)

**Architektura retrieval:**
```
Query → ChromaDB similarity search (pool_size=50)
  → Privacy Shield (WHERE clause per companion)
  → Post-query validation (defense-in-depth)
  → Secret knowledge filter
  → Reranker (similarity×0.65 + importance×0.2 + recency×0.15 + keyword_boost)
  → Milestone injection to top 3
  → Strict Grounding (distance: <0.25=GROUNDED, >0.7=NO_DATA)
  → Token-aware trimming (6000 raw chars budget)
  → Injection into LLM prompt
```

**Skala:** 5628 wektorów (amelia: ~5120, family: ~508). Latencja: ~480ms. Accuracy: 89% na semantic extraction.

**Dual-pipe Ghost Patch:**
- PIPE 1 (Capture): Extension → XHR/fetch intercept → POST /api/capture → Semantic Pipeline → ChromaDB + SQLite
- PIPE 2 (Injection): Enter keydown → GET /api/context-summary → Rerank → Strict Grounding → [MEMORY] block → prepend to user message

**Strict Grounding — 3 poziomy:**
- `GROUNDED` (distance < 0.25): "Cytuj TYLKO to co widzisz"
- `LOW_CONFIDENCE` (0.25–0.7): "Fragmentaryczne wspomnienia — NIE ZGADUJ"
- `NO_DATA` (distance > 0.7): "BEZWZGLĘDNY ZAKAZ wymyślania"

**Merge/Supersede/Create:** "Jestem zmęczony" ×100 = 1 wektor z mention_count=100. Data leku superseduje starą datę automatycznie.

**Ocena portfolio (Opus 4.6):** "Junior+ z seniorskim myśleniem produktowym. Kod do poprawienia, instynkt nie do nauczenia." Architektura 7/10, code quality 5/10, product instinct 9/10.

---

### LDI / forteca_finalna — silnik intencji

**Stack:** Flask + Flask-SocketIO (eventlet), SQLite (10 tabel), fuzzywuzzy NLP, WebSocket real-time

**Architektura intent pipeline (7 stages, ~60ms, zero API calls):**
```
User keystroke → Dual Debounce (200ms UI / 800ms backend)
  → Preprocess → Nonsense filter → Domain context check
  → Typo correction (200+ entries + fuzzy Levenshtein)
  → Structural query detection
  → Fuzzy matching (68 hardcoded products)
  → 5-level classification: HIGH → MEDIUM → LOW → NO_MATCH → nonsensical
```

**Kluczowa innowacja:** `NO_MATCH` + `structural_missing` = "klient szukał czegoś prawdziwego czego nie mamy." To jest Lost Demand — sygnał niewidoczny w Google Analytics.

**Reward Engine — 2 kalkulatory:**

1. Legacy (chatbot RLHF): raw -100 to +200, purchase +100, cart_add +50, "Vogal Shift" detection +30
2. Current (LDI P3): normalized [-1.0, +1.0]:
   - `clicked_despite_no_match` = **+15 (GOLD SIGNAL)** — klient uczył system czegoś nowego
   - `cart_add` = +35, `purchase` = +50
   - `bounce` = **-100 (instant -1.0)**

**JSONL training data format:**
```json
{
  "query": "klocki bmw e90",
  "intent_label": "product_match",
  "confidence": "HIGH",
  "reward_signal": {"score": 0.45, "clicked_alternative": true, "purchased": false},
  "matched_product_id": "KH001",
  "timestamp": "2025-12-01T15:30:00"
}
```

**In-memory knowledge base:** 300+ car brands, 500+ car models, 150+ motorcycle brands, 200+ part categories, multilingual (PL/EN/DE/IT), mechanic slang dictionary.

**Ocena techniczna:** 6/10 overall. Innowacja 7/10, architecture 7/10, code quality 5/10, production readiness 4/10. "Strong proof-of-concept with real intellectual substance, held back by engineering shortcuts."

**Metryki z Amazon Memo (benchmarking):**
| Metryka | Amazon (current) | LDI | Delta |
|---------|-----------------|-----|-------|
| Zero-result rate | 15% | 9% (po 3msc) | -40% |
| Zero-result conversion | 0.5% | 8% | +1500% |
| Lost demand visibility | 0% | 100% | ∞ |
| Training data yield | 2-3% | 20% | +566% |

**Koszt per query:** ~$0.001 (CPU fuzzy matching) vs $0.002/query GPT-4 = **$1.2M/msc w skali Amazona.**

---

### ASTRA — interfejs relacyjny z pamięcią

**Stack:** FastAPI, ChromaDB, Gemini 2.5 Flash, sentence-transformers, vanilla JS frontend

**Działające komponenty (70%):**
- FastAPI backend (500 linii) ✅
- ChromaDB dual-channel RAG (memories + knowledge docs) ✅
- Strict Grounding (3-tier, anti-hallucination) ✅
- Token Manager (semantic-aware trimming: CODE=atomic, FACT=keep core, EMOTIONAL=strip intensifiers) ✅
- Semantic Pipeline (7 entity types: DATE, MILESTONE, SHARED_THING, EMOTION, GOAL, FACT, PERSON) ✅
- Memory Enricher (importance 1-10, relational impact, temporal type, supersede logic) ✅
- Companion State (XP deterministic, 6 levels, mood tracking, active concerns FIFO) ✅
- Inner Monologue (`<thinking>` + `<state>` blocks parsed, stripped before display) ✅
- Frontend dark UI (level/XP/mood display, entity pills, typing indicator, markdown) ✅
- Level 1 persona prompt "Lodowa Ściana" ✅

**Brakuje:**
| Element | Czas | Impact |
|---------|------|--------|
| 6 level prompts | ~8h | CRITICAL — relationship arc nie działa |
| Style Anchors | ~4h | HIGH — Gemini łamie character bez twardych reguł |
| Vibe Detector (port z ANIMA) | ~2h | MEDIUM — health/vulnerability override nie odpala |
| SQLite integration | ~4h | MEDIUM — MemoryConsolidator ma `database=None`, merge/supersede DB ops = no-op |
| Session counter fix | ~30min | LOW — `messages_this_session` > `total_messages` |

**Partially broken:**
- `MemoryConsolidator` — initialized with `database=None`. Vector dedup works, DB archival is a no-op.
- `SemanticPipeline.save_processed()` — returns `[]` because `self.database=None`. Memory saving happens directly in main.py via `vector_store.add_memory()`, bypassing pipeline.

---

### Skankran2 — domain knowledge engine

**Stack:** Flask, PostgreSQL (Render production) + SQLite (local dev), Gemini 2.5 Flash, Flask-SQLAlchemy, Socket.IO + Eventlet, Leaflet.js maps, Chart.js

**Dane (stan na marzec 2026):**
- **35 miast polskich** (poprzednie liczby zawyżone)
- Stacje SUW — lokalizacje **przybliżone** (infrastruktura krytyczna, brak publicznych GeoJSONów). Skankran oblicza najbliższą stację Haversine'em — dla małych miast wystarczające, dla Warszawy niedokładne
- **2 pomiary na miasto:** maj (baseline) + styczeń (trend) — wystarczy do analizy kierunku
- 15 parametrów: pH, twardość, azotany, żelazo, fluorki, chlor, chlorki, siarczany, potas, magnez, mętność, barwa, mangan, ołów, rtęć
- ⚠️ Część danych to estymacje z importu, nie surowe PDF PPIS — do uzupełnienia w ramach umowy z gminą

**AquaBot pipeline:**
```
User wybiera miasto + stacja (lub podaje adres → Nominatim geocoding → Haversine nearest SUW)
  → 15 parametrów załadowane do kontekstu
  → Gemini generuje greeting z traffic light (🟢🟠🔴)
  → Każde pytanie: full context (station data + city map + national averages + chat history)
  → Post-processing: <param:twardosc:294> → colored HTML dots
  → Prompt injection protection + GDPR IP hashing
```

**Advice system:** 646-liniowy advice_templates.json — 4D matrix:
- Health context (drinking/allergies/children/autoimmune)
- Parameter (15 params)
- Severity (orange/red)
- Progi SUROWSZE niż oficjalne polskie/UE normy → pozycjonowanie jako "adwokat wrażliwych populacji"

**Analytics "Satelita":**
- Visitor tracking (GDPR-compliant)
- User profile auto-detection: Rodzic/Biohacker/Pacjent/Ogólny
- Sensory complaint classification: Zapach/Smak/Wygląd
- B2B lead scoring (organizations visiting)
- Lost Demand tracking (pytania bez odpowiedzi)
- CSV export, health check per city

**Business model (EU DWD 2020/2184):**
- Deadline minął: styczeń 2026
- Gminy prawnie niezgodne → MUSZĄ wdrożyć transparentność danych o wodzie
- 21-day deployment vs 12-18 miesięcy u Asseco/Soflab
- 12k EUR/rok vs 250k EUR jednorazowo u konkurencji
- AquaBot zastępuje ~80% call center volume (153k EUR/rok oszczędności dla miasta 100k mieszkańców)
- **Aktualnie: 0 użytkowników, 0 klientów gminnych** — gotowy pod grant

**Ograniczenia które są w pitchu zaletą:**
- *35 miast, 2 pomiary* → "Mamy baseline i trend. Potrzebujemy Waszych danych żeby go uaktualnić"
- *Stacje na oko* → "Wy macie precyzyjne lokalizacje SUW jako operator. Po podpisaniu integrujemy — mapa staje się dokładna"
- *Progi kolorowe do negocjacji* → "Możecie sami skonfigurować kiedy coś jest pomarańczowe — my dostarczamy silnik i interfejs"
- **Target klient: miasta 50-200k** (Grudziądz, Zielona Góra, Gorzów, Koszalin) — nie Warszawa. Radny zna prezesa MPWiK, meeting w tydzień
- **Zabezpieczenie prawne:** AquaBot ma disclaimer, "dane orientacyjne", "nie zastępuje lekarza". Gminy publikują oficjalne wyniki PPIS — Skankran to wizualizacja, nie źródło danych

---

## CZĘŚĆ 6: FILOZOFIA — DLACZEGO TO DZIAŁA

### Jeden engine, cztery głowice

| Projekt | Co karmi | Co wypluwa | Wzorzec pamięci |
|---------|----------|-----------|----------------|
| **ANIMA** | Rozmowy, maile, spotkania | Pamięć absolutna, kontekst | **Pamięć rozszerzona** |
| **LDI** | Keystroke'i klientów | Intencje zakupowe, reward signals | **Percepcja intencji** |
| **ASTRA** | Relacja z użytkownikiem | Grounded odpowiedź + emocje | **Interfejs relacyjny** |
| **Skankran** | PDFy wodociągów, pytania | Kontekstowe porady zdrowotne | **Domain knowledge engine** |

### Agent sprzedażowy = LDI × ANIMA × Strict Grounding

To nie jest chatbot. To:
- **LDI** daje mu percepcję intencji (wie czego klient szuka zanim skończy pisać)
- **ANIMA** daje mu pamięć (pamięta preferencje klienta, historię, kontekst)
- **Strict Grounding** daje mu uczciwość (nie halucynuje o produkcie którego nie ma)
- **Reward Engine** daje mu self-improvement (uczy się z każdej interakcji)

### Transhumanizm = te same moduły zwrócone ku sobie

Te same narzędzia które budujesz dla klientów, firm i gmin — mogą analizować CIEBIE:
- ANIMA → Twoja pamięć rozszerzona (decyzje, wzorce, kontekst)
- LDI Reward Engine → Self-RLHF (mierzysz swoją produktywność)
- Strict Grounding → nie okłamujesz się co do postępów
- Cross-project patterns → widzisz wzorce których sam nie zauważasz
- Health tracking → korelacje zdrowie × produktywność × decyzje

**To nie jest AI które Cię zastępuje. To AI które widzi Twoje wzorce lepiej niż Ty sam.**

---

## PODSUMOWANIE JEDNYM ZDANIEM

Masz działający RAG memory engine, działający intent classifier z reward signals, działający domain knowledge bot na 35 miast z 2 pomiarami, i 70%-gotowego AI companion — teraz potrzebujesz jednego klienta płacącego za "brak notatek", 30 dni danych z prawdziwego sklepu, i 2 dni na zamknięcie ASTRA demo. Reszta to skalowanie tego co już istnieje.
