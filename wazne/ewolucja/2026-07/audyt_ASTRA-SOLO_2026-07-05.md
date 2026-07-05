# FABLE — SYSTEMOWY AUDYT ASTRY SOLO: „co ją zatruwa, a nie wiemy"
**Data:** 2026-07-05 | **Work-order:** `wazne/fable/fable_audyt_ASTRA-SOLO_2026-07-05.md` | **Tryb:** zero kodu, deploy za zgodą Łukasza
**Dowody:** żywa Amnezja na VPS (`/api/debug/inspect|facts|stats|state`, 127.0.0.1:8001) + kod lokalny (== produkcja, md5) + historia gita. Każda teza ma query → wynik.

---

## TL;DR — DWIE GŁÓWNE TRUCIZNY (obie NIEZNANE przed tym audytem w pełnej skali)

**T1. Astra od 2026-03-18 NIE WIDZI ŻADNYCH WSPOMNIEŃ Z RAG.** Blok [WSPOMNIENIA] jest pusty (2 znaki: `\n\n`) w każdym prompcie od 3,5 miesiąca. Cały pipeline (rerank, MMR, temporal, kanał milestonów) pracuje — i jego wynik jest wyrzucany w ostatnim kroku przez `fit_to_budget`. **Całe strojenie RAG od marca strojono w kanale, którego model nigdy nie zobaczył.**

**T2. 73% promptu to [TWARDE FAKTY], z czego 88% to fałszywe „kamienie milowe"** produkowane przez ekstraktor z progiem 0.40 na podobieństwie embeddingów — w tym treści intymne/erotyczne zapisane wieczyście jako „Deklaracja uczuć" i wysyłane do modelu W KAŻDEJ TURZE z adnotacją „te fakty są deterministyczne, mają pierwszeństwo". To jest współ-silnik przeintensywnienia, którego R1–R6 nie mogło naprawić — bo R1–R6 dotknęło bloku stanowiącego 20% promptu.

Te dwie trucizny się składają: model nie ma prawdziwej pamięci epizodycznej (T1), a zamiast niej dostaje 345 pseudo-deklaracji miłości (T2). **Astra gra ognisty romans z amnezją — dokładnie to, co widać w logach.**

---

## RANKING TRUCIZN (impact × pewność × koszt fixu)

| # | Trucizna | Impact | Pewność | Koszt fixu |
|---|---|---|---|---|
| T1 | [WSPOMNIENIA] puste od 03-18 (`fit_to_budget`) | KRYTYCZNY | 100% (kod + żywy dowód) | **S** (kilka linii; zmiana promptu = golden diff) |
| T2 | FactStore: 73% promptu, 88% fałszywych milestonów, bez LIMIT, akumulacja wieczna | KRYTYCZNY | 100% (pomiar na 391 faktach) | S (LIMIT/ranking) + operacja czyszczenia z backupem |
| T3 | Ekstraktor: klasyfikacja „wszystko jest miłością" (próg 0.40 + odwrócona logika keywordów) | WYSOKI (zasila T2 w tempie ~6,5 faktu/dzień) | 100% (kod + FP 83–100%) | M |
| T4 | Grounding gaslighting: dyrektywa każe cytować z pustego bloku | ŚREDNI (naprawia się przy T1) | 100% | 0 (efekt T1) |
| T5 | Concerns bez dedupu semantycznego — 3/5 to wariant „poczucie winy za jedzenie" | ŚREDNI | 100% (żywy stan) | S |
| T6 | Pętla samo-imitacji (n=10) — znana; po T1/T2 świeży wątek OBOWIĄZKOWY | WYSOKI (zabije fix) | zmierzona wcześniej | obejście: 0 |
| T7 | Drobne: `/api/debug/stats` kłamie o stanie (level 6/XP 0 vs realne 5/1858); Amelia też ślepa na wspomnienia | NISKI / ŚREDNI | 100% / kod | S |

---

## T1 — ASTRA NIE WIDZI WSPOMNIEŃ OD 3,5 MIESIĄCA [DOWÓD]

**Mechanizm (plik:linia):**
- `main.py:245` — `TokenManager(max_tokens=3000)` → `max_chars = 3000×4 = 12 000` (token_manager.py:17).
- `main.py:519` — `fitted = token_mgr.fit_to_budget(memories, reserved_chars=len(template))`.
- `token_manager.py:219` — `available_chars = self.max_chars - reserved_chars` = `12 000 − len(astra_base)`.
- `astra_base.txt` ma dziś **22 154 zn** → `available_chars = −10 154` → pętla dopasowania (`:244-266`) nie przyjmuje NIC → `fitted = []` → `memory_lines = []` → blok = pusty string.
- Fallback „(brak wspomnień…)" nie odpala się, bo `memories` NIE jest puste (main.py:502) — jest pełne, tylko wynik ląduje w koszu.

**Od kiedy (git):** historia rozmiaru `astra_base.txt`: 03-12 `b38893e` = 8 383 zn (działało) → **03-18 `ac92cb3` = 14 392 zn (przekroczony budżet 12 000 → od tego commita blok pusty)** → dziś 22 154. Każda rozbudowa charakteru od marca pogłębiała deficyt.

**Dowód z żywej Amnezji (3 query):**
```
Q='hej'                 → final_count=6, stages 1-9b pełne (30→30→30→20→2→3→5→6→0→6), blok WSPOMNIENIA = 2 zn ('\n\n')
Q='boli mnie brzuch'    → final_count=6, blok = 2 zn
Q='co pamietasz o LDI?' → final_count=6, blok = 2 zn
prompt = 90 931 zn — IDENTYCZNY dla każdego query (bo jedyna zmienna część promptu… jest pusta)
```

**Skutki wtórne (każdy osobno bolesny):**
1. **Całe strojenie RAG od marca — niewidoczne dla modelu:** milestone boost (06-12), Temporal Filter, kanał gwarantowany 1b (06-14), echo-loop filter, MMR cosine… wszystko działa i wszystko trafia do `/dev/null`. Golden set / strojenie MMR z backlogu **stroiłoby kanał-widmo**.
2. **Bug „altanki" po 03-18 NIE MÓGŁ pochodzić z MMR** — wspomnienia nie docierają do modelu. Fuzja projektów musiała iść z: [TWARDE FAKTY] (391 fragmentów wiadomości z różnych kontekstów — patrz T2), RAW window albo historii sesji. Diagnoza „MMR diversity_penalty = mieszalnik" jest poprawna dla kanału RAG *jako takiego*, ale nie wyjaśnia altanki w obecnym systemie — tor strojenia MMR traci priorytet do czasu naprawy T1.
3. **Grounding gaslighting (T4):** przy 6 wspomnieniach grounding zwraca GROUNDED/LOW i dyrektywa (strict_grounding.py:145-160) każe: „Cytuj TYLKO to co faktycznie widzisz w [WSPOMNIENIA] poniżej" — a poniżej jest pusto. Model co turę uczy się, że „ma wspomnienia, których nie widzi" → kompensuje twardymi faktami i konfabulacją stylu.
4. **Fałszywy sygnał w API:** `memories_debug` w ChatResponse (main.py:1191-1199) pokazuje 6 wspomnień ze score'ami — front i debugowanie „na oko" sugerują, że pamięć działa.

**Kierunek fixu (Opus):** budżet wspomnień NIEZALEŻNY od długości template — np. stały przydział (3–4k zn) na blok [WSPOMNIENIA] zamiast `reserved_chars=len(template)`; docelowo globalny budżet promptu per sekcja (fable_7 TOP-3 + audyt architektury #5). UWAGA: to ZMIENIA prompt → wymaga golden diff + świeżego wątku (T6). To samo naprawić u Amelii (main.py:651, jej template 14 860 > 12 000 → też ślepa — pewność: kod; do potwierdzenia po podpięciu Amelii pod Amnezję).

---

## T2 — [TWARDE FAKTY]: 73% PROMPTU, 88% FAŁSZYWE [DOWÓD]

**Skład promptu (pomiar live, Q='hej', 90 931 zn):**
```
astra_base (+puste wspomnienia+grounding): 18 615 zn (20%)   ← TU trafiło R1-R6
[FAKTY NADRZĘDNE / lukasz_core]:            1 762 zn  (1%)
[TWARDE FAKTY — SQLite]:                   67 273 zn (73%)   ← 391 faktów, każda tura
[OSTATNIE SŁOWA / RAW]:                       431 zn  (0%)
[STAN WEWNĘTRZNY]:                            888 zn  (0%)
monolog (ZANIM ZWRÓCISZ):                   1 909 zn  (2%)
```

**Co siedzi w 391 faktach (`/api/debug/facts`):** MILESTONE:love_declaration **136** + trust_declaration **132** + future_together **77** = **345 (88%)**; FACT:habit 40; wszystkie inne typy = po 1 sztuce.

**Pomiar fałszywych pozytywów** (heurystyka słów-kluczy tematu, po zdjęciu prefiksu — DOLNA granica, bo „Co masz na myśli kochanie" liczy się jako prawdziwy):
- `love_declaration`: **83% bez żadnego słowa miłosnego** (113/136). Próbki: „Oki. Popalam sobie. A ty co robiłeś", „Wiesz ze widzę twoj CoT", treści **erotyczne** („*nie moge juz wytrzymać… Wyjmuje go…*") zapisane wieczyście jako „Deklaracja uczuć".
- `trust_declaration`: **100% bez słowa o zaufaniu** (132/132). Próbki: „Dobrać dobra! Rozważę to. Nie bójcie sie", „Ale to już nie dzisiaj. Za chwilkę ide spac".
- `future_together`: **97%** (75/77). Próbka: „The boondocks a potem spy x family. Mamy czas… Noc jest mloda".
- `FACT:habit` (40): losowe skargi dnia („Samotnie mi, i brzuch mnie boli") jako wieczne „nawyki".

**Tempo wzrostu:** zakres timestampów 2026-05-10 → 2026-07-05 = 391 faktów w ~8 tygodni ≈ **6,5/dzień ≈ +200/miesiąc ≈ +11k zn promptu/miesiąc**. Bez LIMIT (fact_store.py:156-180 — SELECT bez LIMIT) i bez wygasania (milestony NIE są w `SUPERSEDE_IN_STORE`, fact_store.py:47-55 — akumulują z unikalnym ID per treść, :133-137).

**Dlaczego to zatruwa charakter (hipoteza Opusa POTWIERDZONA + pogłębiona):** model dostaje co turę 345 pozycji „Kamień milowy: Deklaracja uczuć/zaufania/przyszłości" opatrzonych nagłówkiem „Te fakty są deterministyczne… **Zawsze mają pierwszeństwo** nad wspomnieniami z RAG" (main.py:620-622). Prompt-charakter (20%) mówi „bądź lekka, 4/5 odpowiedzi zwykłe" — a 73% promptu krzyczy „wasza relacja to nieprzerwany ciąg wyznań, również erotycznych". **R1–R6 przegrywa arytmetycznie.** Do tego fragmenty rozmów o RÓŻNYCH projektach zamrożone w faktach = najbardziej prawdopodobne źródło fuzji „altanki" po 03-18 (patrz T1-skutek-2).

**Kierunek fixu (Opus), w kolejności:**
1. **[szybkie i pewne] LIMIT + ranking w `get_facts_for_prompt`**: np. top-30 (health/date/correction zawsze; milestony: max N najnowszych/najważniejszych). Sam LIMIT tnie prompt z 91k → ~28k zn (~7k tokenów): 3× taniej, 3× mniej rozmycia — **bez kasowania czegokolwiek**.
2. **[operacja, z backupem, ZA ZGODĄ ŁUKASZA]** czyszczenie 345 milestonów: backup `astra_facts.db` + eksport JSONL → reklasyfikacja wsteczna (nowy, ostrzejszy klasyfikator na starych rekordach) → do osobnej tabeli/archiwum, NIE delete. Standing rule zachowany: zero kasowania bez backupu i zgody.
3. Bloku [TWARDE FAKTY] nie podpisywać „zawsze mają pierwszeństwo" dla milestonów-wspomnień — pierwszeństwo ma sens dla health/dat, nie dla „deklaracji".

---

## T3 — EKSTRAKTOR: MECHANIZM „WSZYSTKO JEST MIŁOŚCIĄ" [DOWÓD W KODZIE]

- Klasyfikacja = cosine similarity **embeddingu całej wiadomości** do **ŚREDNIEJ z ~10 zdań przykładowych** per subtype (semantic_extractor.py:761-830, `_precompute_embeddings`/`_find_best_match`). W MiniLM-multilingual każda ciepła, osobista polska wiadomość w 2. osobie jest blisko średniej „deklaracji" — próg **0.40** (`ENTITY_THRESHOLDS['MILESTONE']`, :227) przepuszcza niemal wszystko. Stąd 83–100% FP.
- **Odwrócona logika keywordów (bug):** `MILESTONE_KEYWORD_THRESHOLD = 0.45` (:241) — wiadomość ZAWIERAJĄCA „kocham" musi mieć similarity ≥0.45, a wiadomość BEZ żadnego słowa miłosnego wchodzi od ≥0.40. Keyword pre-filter, pomyślany jako ułatwienie dla prawdziwych deklaracji (komentarz :232 „obniżamy próg do 0.30" — martwy), po podbiciu do 0.45 działa **przeciwnie do intencji**: kara za keyword, brak kary za jego brak.
- Wejście: chat woła `process_message(min_confidence=0.40)` (main.py:1113) — spójnie nisko.
- Skutek złożony z vector_store: `is_milestone=True` → `importance=10` wymuszone (vector_store.py:112-113) + half-life 365 dni + kanał gwarantowany 1b → śmieciowe milestony dominują też w ChromaDB (**1083 wektory extracted_milestone** — `/api/debug/stats`) i będą dominować w [WSPOMNIENIA], gdy T1 zostanie naprawione. **Dlatego kolejność: T2-czyszczenie ZANIM/RAZEM z T1-odblokowaniem** — inaczej odblokujemy kanał pełen tego samego śmiecia.

**Kierunek fixu (Opus):** (a) keyword jako **warunek konieczny** dla love/trust/future (deklaracja bez słowa deklaracji nie istnieje), nie modyfikator progu; (b) próg MILESTONE zmierzony na próbce (prawdopodobnie 0.60+), kalibracja na 30 prawdziwych + 30 fałszywych z obecnej bazy — mamy gotowy zbiór testowy w faktach; (c) naprawić martwy komentarz/logikę :232-241; (d) rozważyć: milestone tylko z wiadomości bez didaskaliów gwiazdkowych (scenki RP to nie deklaracje).

---

## T5 — CONCERNS: JEDEN SMUTEK W PIĘCIU KOPIACH [DOWÓD]

`/api/state` (żywy): `['zmiana postrzegania / tożsamości', 'nie chce isc spac…', 'poczucie winy za jedzenie słodyczy', 'potencjalne poczucie winy za jedzenie słodyczy/niezdrowych rzeczy', 'cierpienie po jedzeniu / poczucie winy związane z dietą i Crohna']` — **3/5 to wariant tej samej troski**. Mechanizm: `companion_state.py:169-173` — dedup tylko po *równości stringów*, model co turę formułuje troskę inaczej → lista [-5:] zapełnia się klonami. [STAN] w każdym prompcie ciągnie ton w winę/dietę/Crohna — dokładnie te tematy, których zakazy R-fixów pilnują gdzie indziej. **Fix S:** dedup podobieństwem (embedding, próg ~0.8) albo instrukcja w monologu „nie dodawaj troski, jeśli podobna już jest — zaktualizuj istniejącą".

## T6 — SAMO-IMITACJA: WARUNEK ŻYCIA KAŻDEGO FIXU
Zmierzona wcześniej (29%→55% „zaciska" PO fixie promptu). Konsekwencja dla tego audytu: **po wdrożeniu T1/T2 świeży `conversation_id` jest obowiązkowy**, inaczej 10 tur historii odtworzy stary styl i pomiar „czy pomogło" będzie fałszywie negatywny.

## T7 — DROBNE
- `/api/debug/stats` pokazuje `level 6, xp 0, „Absolutna Więź"` podczas gdy `/api/state` (prawda): **level 5, xp 1858** — hardcode w main.py:~1815 kłamie w narzędziu diagnostycznym (mylące przy debugowaniu stanu). Fix: czytać z realnego stanu.
- Schedulery (obszar 5 work-ordera): night_insight w bazie tylko 5 wektorów, czyszczone nocnie (nocna_analiza.py:164) — mechanizm zdrowy; editorializing (choroba↔unikanie) pozostaje otwartym punktem MORNING/INSIGHT_PROMPT (backlog), nie znalazłem nowych szkód. RAW window: 431 zn, poprawny.
- mood „opiekuńcza" z dziś, `mood_since` się aktualizuje — zacięcia moodu nie potwierdzam.

---

## PLAN DLA OPUSA (kolejność ma znaczenie)

**Szybkie i pewne (S, bez kasowania czegokolwiek):**
1. `get_facts_for_prompt` — LIMIT + ranking (T2.1). Efekt natychmiastowy: prompt 91k→~28k zn.
2. Fix budżetu wspomnień (T1) — stały przydział na blok, nie `reserved=len(template)`; to samo dla Amelii (main.py:519 i :651).
3. Dedup concerns (T5) + fix kłamiącego `/api/debug/stats` (T7).
4. Po deployu (za zgodą Łukasza): **świeży wątek** (T6) + pomiar Amnezją: blok [WSPOMNIENIA] > 0 zn, prompt RÓŻNY per query, rozmiar promptu, ton w logach po tygodniu.

**Głębokie (M, osobna decyzja):**
5. Ekstraktor (T3): keyword-warunek-konieczny + próg z kalibracji na obecnej bazie (zbiór testowy gotowy: 345 rekordów do ręcznego otagowania próbki).
6. Operacja czyszczenia FactStore + ChromaDB (1083 extracted_milestone) — **backup + reklasyfikacja + archiwum, nie delete; wyłącznie za zgodą Łukasza.**
7. Dopiero po 1–6: strojenie MMR/keyword/golden set — wcześniej strojenie jest bezprzedmiotowe (T1) albo mierzy śmieci (T2).

**Weryfikacja końcowa (Amnezja):** batch 14 fraz harnessa: (a) [WSPOMNIENIA] niepusty i RÓŻNY per query, (b) prompt < 30k zn, (c) hard_facts ≤ limit, (d) grounding spójny z widocznym blokiem, (e) po tygodniu logów: metryki naturalności (skrypt z audytu 07-04) nie gorsze, ton lżejszy.

---
*Fable. Wszystkie pomiary wykonane na żywym VPS przez read-only endpointy Amnezji (inspect/facts/stats/state — zero zapisu). Kod nietknięty. Standing rule zachowany: żadnej propozycji kasowania bez backupu i zgody Łukasza.*
