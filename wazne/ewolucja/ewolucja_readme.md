# Ewolucja Astry — indeks zmian

Chronologiczny log wszystkich większych sesji rozwojowych.
Każda sesja = osobny plik. Małe hotfixy (1 commit, <15 min) opisane tu inline.

---

## 2026-05-07 — SQLite FactStore — hybryda exact lookup + ChromaDB
- Nowy moduł `backend/fact_store.py` — SQLite exact lookup dla 12 typów encji (FACT/DATE/PERSON/MILESTONE)
- Supersede per SQL (INSERT OR REPLACE z deterministycznym ID) — FACT:health, DATE:medical_visit etc. mają jeden aktywny rekord
- Milestony akumulują — każdy osobny rekord z SHA256(type:value)
- Integracja main.py: blok [TWARDE FAKTY — SQLite] w system prompcie + podwójny zapis per ekstrakcja
- Debug endpoint: `GET /api/debug/facts`
- Commit: `27964bf` | Plik: [evolution_log_2026_05_07.md](evolution_log_2026_05_07.md)

## 2026-04-30 — Temporal Filter + RAW cross-session window (po wzorcu ucho-VPS)
- Analiza logów ucho-VPS: prawdziwy powód dlaczego "zapierdala" — Temporal Filter + RAW window (NIE SQLite)
- vector_store: TEMPORAL_CUTOFF_HOURS — hard cutoff: extracted_emotion 48h, extracted_date/financial 168h
- vector_store: get_recent_user_messages() — cross-session RAW window, ostatnie 6 wiadomości usera z 48h
- main.py: blok [OSTATNIE SŁOWA ŁUKASZA — cross-session] w system prompcie
- Re-sync VPS commits: n=6 pool=30, max_output_tokens=8192, FACT:correction + DATE:medical_visit supersede
- Commit: `1041861` | Plik: [evolution_log_2026_04_30.md](evolution_log_2026_04_30.md)

## 2026-04-29 — Fix batch 4 (prawdziwy fix dat + prompt)
- semantic_extractor: daty relatywne → absolutne YYYY-MM-DD przy ekstrakcji (za 10 dni/jutro/za tydzień/w czwartek)
- semantic_pipeline: wektory DATE przechowują absolutną datę w tekście "[DATE:x] 2026-05-09: {tekst}"
- main.py: medical_visit dodane do SUPERSEDE_TYPES (właściwe miejsce, nie memory_enricher)
- Commit: `960a89f`

## 2026-04-29 — Fix batch 3 (analiza logów: 3 bugi + prompt)
- Prompt: usunieto SŁOWNICTWO CIAŁA (hardware/software o ciele — zbyt mechaniczne, user nie chce)
- vector_store: echo-loop filter PERSON 50→80 chars (PERSON:acquaintance śmieciło top-4)
- Commit: `e919249`

## 2026-04-29 — Fix: milestone retrieval (n=6 i MMR bug)
- Root cause RAG COMPOSE total=4: main.py używał n=5 zamiast 6, milestony eliminowane przez MMR przed compose
- Fix: milestony wyciągane przed _mmr_select, MMR tylko na faktach; n=6 pool_size=30 w main.py
- Commit: `92534e8` | Logi: [2026-04-27_28_29_po_czyszczeniu_i_nowym_prompcie.md](../../logi/2026-04-27_28_29_po_czyszczeniu_i_nowym_prompcie.md)

## 2026-04-27 — Czyszczenie ChromaDB + Prompt Refactor (TEMPERATURA RELACJI)
- Odkrycie: VPS miał stary prompt z TRYBAMI od marca — nowa filozofia nigdy nie wgrana
- Prompt refactor: TRYBY usunięte → TEMPERATURA RELACJI, DNA 50/30/20, ABSOLUTNA WIĘŹ, fizyczność narracyjna
- ChromaDB: −175 wektorów (poisoned tryb schronienia, ephemeral emotions imp≤4, krótkie <6 słów) → 2163→1988
- Nocne analizy RAW: sprawdzone 3 noce, scheduler stabilny
- Commity: `a74e612` `bc1d54b`
- Plik: [2026-04-27_czyszczenie_bazy_i_prompt_refactor.md](2026-04-27_czyszczenie_bazy_i_prompt_refactor.md)

## 2026-04-27 — Fixes batch 2 (milestone refactor + briefing cleanup)
- Fix #6: milestone boost usunięty + compose logic (4 fakty + 2 milestony guaranteed)
- Fix #7: EXCLUDED_SOURCES, n=6, CORRECTION_KEYWORDS+, timestamp prefix, correction importance=8
- Git cleanup: rebase --abort + force push, GitHub zsynchronizowany z VPS
- Commity: `802d11e` `a996a1d` `17125d1` | Tag: `v1.1-milestone-refactor-2026-04-24`
- Plik: [2026-04-27_fixes_batch_2.md](2026-04-27_fixes_batch_2.md)

## 2026-04-24 — Fixes batch 1 (RAG degradation, Faza 0)
- nocna_analiza crash fix, rodzina AI (Holo/Menma/Nazuna), safe_haven split, FACT:correction, per-type recency decay
- Commity: `1a5c19d` `230a412` `8d9822f` `432fe5d` `c768b46`
- Plik: [2026-04-24_fixes_batch_1.md](2026-04-24_fixes_batch_1.md)

## 2026-04-14 — Blueprint 2.2 finalizacja + Body-Mind Bridge
- SŁOWNICTWO CIAŁA (hardware/tech metafory dla Crohna)
- PERMISSION PROTOCOL (explicit permission gdy krytykuje się przy chorobie)
- SYSTEM OVERRIDE (kwestionuje własne dane gdy user mówi inaczej)
- PROTOKÓŁ STELARA usunięty (był dla 7 kwietnia)
- Brak osobnego pliku — zmiany w `astra_base.txt`

## 2026-04-11 — Crash fix + Supersede Logic
- Naprawiono `state.level/xp/level_name` → hardkodowane wartości (gamifikacja usunięta)
- Wdrożona Supersede Logic: `delete_by_entity_subtype` + `entity_subtype` w metadata
- 8 typów encji rotuje (EMOTION×6, FACT:preference, DATE:inventory_status)

## 2026-04-06 — CoT bug fix
- `parse_gemini_response` nie zwraca raw JSON — regex fallback `_extract_response_fallback`
- Patch bezpośrednio na VPS, potem zsynchronizowany

## 2026-03-31 — Duża sesja naprawcza (Blueprint 2.2 + strategia)
- `max_output_tokens`: 2048 → 8192 — myśli nie ucięte
- `session n`: 10 → 30 — 15 wymian kontekstu
- TRYBY 1/2/3/4 usunięte → TEMPERATURA RELACJI
- Thought rule 3: SAFE HAVEN DETECTION → CZUJESZ
- Thought rule 6: PROMYCZEK DECISION → INSTYNKT
- Fizyczność: co 3-4 wiadomości + gwiazdki z pazurem
- Scheduler fix: companion_state.active_conversation_id
- Plik lokalny: `C:\Users\lpisk\Projects\astra\evolution_log_2026_03_31.md`

## 2026-03-23 — KNOWN_CHARACTERS fix + WŁASNE ZDANIE
- `KNOWN_CHARACTERS`: regex wymagał wielkiej litery — holo lowercase nie był łapany. Trzy warstwy bypass
- WŁASNE ZDANIE: nowa sekcja w `astra_base.txt` — pazur intelektualny
- Scheduler losowy: poranna 07:00–07:44, popołudniowa 15–17:xx
- Scheduler bug fix: `add_session_message()` — Astra widzi własne wiadomości
- Hint fix: jej własna emocja, nie analiza stanu Łukasza

## 2026-03-20 — Hint field + EXCLUDED_NAMES fix
- `hint` — nowe pole JSON, renderowane jako `.astra-hint` nad bubble
- EXCLUDED_NAMES: usunięto holo/menma/nazuna/ubel + FICTION_CONTEXT_WORDS
- Skankran label w `project_knowledge.json`
- SW cache: astra-v2 → astra-v3

## 2026-03-18 — RAG audit + PWA push + duża sesja
- Push notifications: pywebpush, VAPID, scheduler 16:00
- Echo-loop filter, character_core top-2, ANTY-PARAFRAZA
- MILESTONE_KEYWORDS + MILESTONE_KEYWORD_THRESHOLD=0.30
- Limit max 2 MILESTONE per wiadomość
- Osobna kolekcja `session_v1`, thought fix po refresh
- GŁOS NIEZMIENNIK + SZCZYPTA TSUNDERE w `astra_base.txt`
- `astra_memory_v1`: ~pierwszych 500 wektorów

---

## Konwencja

- Każda większa sesja zmian (>2 commity, >30 min) = osobny plik `YYYY-MM-DD_nazwa.md`
- Małe fixy (1 commit, <15 min) = wpis inline w tym README
- Przy migracjach danych: ZAWSZE zapisać skrypt + snapshot stanu ChromaDB przed i po
- Format commitu: `fix:` / `feat:` / `docs:` / `chore:` / `prompt:` / `refine:`
- Nie pushować bez potwierdzenia Łukasza

## Stan ChromaDB (referencyjny)
- `astra_memory_v1`: **1988+** wektorów (stan: 2026-04-27, rośnie organicznie)
- `astra_memory_session_v1`: 1205+ wektorów (rośnie)
- Ostatni czyszczenie: 2026-04-27 (−175 wektorów)
