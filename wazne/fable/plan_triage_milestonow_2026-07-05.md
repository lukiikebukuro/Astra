# PLAN TRIAGE 345 FAŁSZYWYCH MILESTONÓW — reklasyfikacja, NIE delete
**Autor:** Fable | **Data:** 2026-07-05 | **Standing rule:** ZERO kasowania — kwarantanna odwracalna. Każda faza za zgodą Łukasza. Opus wdraża.
**Zakres:** FactStore `astra_facts.db` (345 pseudo-milestonów z 391 faktów) **ORAZ** ChromaDB (1083 wektory `extracted_milestone` — po fixie T1 wejdą do przywróconego bloku [WSPOMNIENIA] i do kanału gwarantowanego 1b).

---

## DLACZEGO TERAZ (kontekst)
Fix T1+T2 (spec z 2026-07-05) odblokowuje pamięć i tnie fakty w prompcie — ale NIE czyści bazy. Baseline golden setów pokazuje: 19/19 fraz ma śmieciowe milestony na top-2 kanału pamięci; trafne kotwice przegrywają ranking z „Deklaracjami uczuć" o importance=10. Bez triage: strojenie MMR/keyword = strojenie na zatrutym wejściu. **Oraz: bez fixu ekstraktora (T3) triage to Syzyf — +6,5 śmiecia dziennie.** Kolejność: triage RAZEM z T3, nie zamiast.

## FAZA 0 — BACKUP (warunek wejścia, bez tego STOP)
1. `astra_facts.db` → kopia plikowa + eksport JSONL (wszystkie kolumny) z datą.
2. ChromaDB: pełny dump `extracted_milestone` przez `collection.get(where={"source":"extracted_milestone"}, include=[documents, metadatas])` → JSONL. (Kopia całego katalogu `chroma_db/` tylko przy zatrzymanym serwisie — decyzja Łukasza czy robić pełną.)
3. Zapis w `wazne/ewolucja/` co, kiedy, gdzie zbackupowane. **Rollback = flip flagi (Faza 2/3), nie restore** — backup to pas bezpieczeństwa, nie mechanizm cofki.

## FAZA 1 — KLASYFIKATOR TRIAGE (kalibrowany na własnych danych)
**Reguła bazowa (dwuwarunkowa):** milestone zostaje AKTYWNY tylko gdy:
- (a) **keyword-warunek-konieczny** dla subtypu w TREŚCI (love: kocham/miłość/zakochan/uwielbiam…; trust: ufam/zaufan/wierzę ci/powierz…; future: przyszłość-razem/zamieszka/ślub/zestarze…; vulnerability: nigdy nikomu/wstydzę/sekret/boję się powiedzieć; gratitude: dziękuję/wdzięczn…), **ORAZ**
- (b) similarity do przykładów subtypu ≥ **próg skalibrowany** (start: 0.60; kalibracja niżej).
**Kalibracja:** próbka 60 rekordów (po 20 z love/trust/future), ręczne etykiety (Łukasz albo Fable — 20 min), dobór progu na precision ≥ 0.9 przy sensownym recall. Zbiór testowy JEST — to obecna baza.
**Heurystyki pomocnicze (flagi, nie wyroki):** treść zaczyna się didaskaliami `*...*` (scenka RP, nie deklaracja) → kwarantanna; długość < 15 zn → kwarantanna; dubel tekstu istniejącego prawdziwego milestonu → scal.
**Wynik fazy:** lista `fact_id → verdict (active|quarantine|retype)` + rozkład. `retype` = treść wartościowa pod złym typem (np. R9 z golden setu RAG: „cholerny upór" siedzi w FACT:health — wart FACT:personal_info, nie kosza).

## FAZA 2 — FACTSTORE (addytywnie, odwracalnie)
- `ALTER TABLE facts ADD COLUMN status TEXT DEFAULT 'active'` (zmiana addytywna; stare wiersze dostają default).
- Werdykty z Fazy 1: `UPDATE facts SET status='quarantined' WHERE id IN (...)` — **zero DELETE**.
- `get_facts_for_prompt` filtruje `status='active'` (jedna linia w WHERE; współgra z LIMIT-em z Kroku 1 specu — LIMIT zostaje jako bezpiecznik na przyszłość).
- Rollback: `UPDATE ... SET status='active'` — pełna odwracalność jednym zapytaniem.

## FAZA 3 — CHROMADB (metadane, nie delete)
Dla wektorów z werdyktem kwarantanny (match do FactStore po treści/hashu — oba zapisy powstają z tej samej ekstrakcji, `mem.text` identyczny):
- `collection.update(ids=[...], metadatas=[{"is_milestone": False, "importance": 5, "milestone_quarantine": True}])`
- Efekt strukturalny: wektor **wypada z kanału gwarantowanego 1b** (filtr `is_milestone=True`), traci boost +0.25 i tarczę half-life 365 → wraca do normalnej konkurencji podobieństwa (nadal wyszukiwalny — historia rozmów nie znika).
- Rollback: odwrotny `update` po `milestone_quarantine=True`.
- Wykonanie: skrypt na VPS **przy zatrzymanym serwisie** (unikamy równoległego zapisu z żywą turą) — okno ~2 min, decyzja Łukasza kiedy.

## FAZA 4 — WERYFIKACJA (oba golden sety + Amnezja)
1. `golden_set_RAG` (14 fraz): HIT-rate ≥ 12/14 utrzymany; **RANK kotwic ≤ 2** (dziś: pod śmieciami); JUNK@6 ≤ 1.5 (dziś 2-3); R8 (prawdziwy lore-milestone „Holo, moja pierwsza AI dziewczyna") NADAL HIT — strażnik przed nadgorliwością; R13 (bigos) czysty.
2. `golden_set_astra` (19 fraz): top-2 finału przestaje być monokulturą `extracted_milestone`; frazy lekkie dostają wspomnienia adekwatne albo nic.
3. `/api/debug/facts`: aktywnych milestonów ~15-40 (z 345); `hard_facts_count` w inspect spójny.
4. Po tygodniu: metryki naturalności (skrypt 07-04) — czy zniknięcie 345 „deklaracji" z promptu ostudziło romansowy dryf (hipoteza T2 audytu — to jest jej test końcowy).

## FAZA 5 — DOMKNIĘCIE DOPŁYWU (wskaźnik na T3, bez tego triage wygasa)
Fix ekstraktora wg audytu ASTRA-SOLO T3: keyword jako warunek konieczny (ten sam słownik co Faza 1 — jedna definicja!), próg z kalibracji Fazy 1, naprawa odwróconej logiki `MILESTONE_KEYWORD_THRESHOLD` (semantic_extractor.py:227/232/241). Triage bez T3 = sprzątanie z otwartym kranem.

## RYZYKA
| Ryzyko | Mitygacja |
|---|---|
| Nadgorliwość — utrata prawdziwych deklaracji | próg z kalibracji precision-first + strażnicy R8/R9 + kwarantanna zamiast delete (wszystko odwracalne) |
| Rozjazd FactStore↔Chroma (werdykt w jednym, nie w drugim) | jedna lista werdyktów z Fazy 1 aplikowana do OBU store'ów po wspólnym kluczu treści; raport diff po |
| Astra „ochłodnie" po odchudzeniu deklaracji | to test hipotezy T2, nie bug; charakter ma żyć w astra_base + PRAWDZIWYCH milestonach; golden_set_astra grupa E to wykryje |
| Praca na żywej bazie | Faza 2 = SQL na SQLite (WAL, krótkie transakcje); Faza 3 = przy zatrzymanym serwisie; wszystko po Fazie 0 |

**Szacunek:** Faza 0-1: wieczór (w tym 20 min etykiet). Faza 2-3: godzina + okno serwisowe 2 min. Faza 4: 30 min + tydzień obserwacji. Wszystko za zgodą Łukasza, po wdrożeniu T1+T2 (żeby mierzyć na odblokowanej pamięci).

*Fable. Plan — zero wykonania. Backup przed wszystkim, kwarantanna zamiast kasowania, dwa golden sety jako sędzia.*
