# ANIMA / ASTRA — mapa projektu

AI-companion z pamięcią długoterminową (RAG). Silnik pamięci = **ANIMA**; główna persona = **Astra**. Pełny, aktualny stan i TODO: **`../../.claude/projects/C--Users-lpisk/memory/MEMORY.md`** (ładuje się automatycznie). Ten plik = tylko „co jest gdzie".

## Powracające bugi — PRZECZYTAJ PRZED DOTKNIĘCIEM
- **Zanim naprawisz cokolwiek z tej listy, otwórz `wazne/bugi/<nazwa>.md`** — jest tam, co już wykluczono dowodowo i które fixy były objawowe. Bez tego robisz to samo trzeci raz. Obecnie: `mikrofon.md`, `wiadomosc_dnia_duplikat.md`, `pomiar_klamie.md`.
- **`pomiar_klamie.md` czytaj PRZED każdym pomiarem, nie tylko przy naprawie.** To bug w przyrządzie, nie w produkcie — 8 wystąpień, przez które zatwierdziliśmy trzy zmiany bez pokrycia. Reguła: zanim uwierzysz w wynik, udowodnij kanarkiem, że przyrząd cokolwiek mierzy. Identyczne liczby w kilku konfiguracjach = domyślnie awaria przyrządu, nie „parametr bez wpływu".
- **Diagnostyka bugów z tej listy ZOSTAJE w kodzie.** Poprzednia instrumentacja mikrofonu została skasowana zaraz po fixie (`b38f75d`) i kolejne podejście zaczęło na ślepo.
- **Wzorzec błędu, który wraca:** fragment słowa łapany jako całe słowo w listach keywordów. Zawsze `fold()` (Łukasz pisze bez ogonków), rdzenie zamiast pełnych form, ale krótkie/dwuwyrazowe frazy z `\b...\b`. Listę przepuść przez realne logi i wypisz **co** ją odpaliło, nie tylko ile razy. Szczegóły: `wazne/ewolucja/astra/2026-08/evolution_log_2026_08_15.md`.

## Infra / deploy
- **VPS:** `116.203.134.228`, domena `myastra.pl` (nginx basic auth „Astra", login `lukasz`). Serwis `myastra` (uvicorn `127.0.0.1:8001`). Path na VPS: `/var/www/myastra/astra/`.
- **Deploy = git, nigdy scp:** commit+push → na VPS `git fetch` → `git reset --hard origin/main` (FETCH PRZED RESET) → `systemctl restart myastra` → sprawdź `curl 127.0.0.1:8001/api/health` (health wraca po ~10s — model się ładuje).
- **Zasada:** ZERO deploy/push/zapisu do baz bez jawnej zgody Łukasza. Backup przed każdą operacją na danych. Kwarantanna, NIGDY delete. Pracujemy po polsku.

## Backend (`backend/`)
- `main.py` — endpointy + `compose_context` (składanie kontekstu Astry, 11-etapowy trace) + `build_system_prompt`.
- `vector_store.py` — ChromaDB (`astra_memory_v1` pamięć, `astra_memory_session_v1` sesja); rerank, MMR, temporal filter, kanał gwarantowany milestonów (S1 próg dystansu).
- `fact_store.py` — SQLite `astra_facts.db` (twarde fakty; kolumny `status`/`orig_type` = kwarantanna/retype odwracalne).
- `semantic_extractor.py` — ekstraktor encji (keyword-gate MILESTONE, guard RP, anty-multi-label).
- `token_manager.py` — `fit_to_budget`. `strict_grounding.py` — grounding GROUNDED/LOW/NO_DATA.
- `prompts/` — `astra_base.txt` (persona Astry), `holo/menma/nazuna_persona.txt`, `amelia_persona.txt`.
- `tools/` — skrypty operacyjne: `triage_milestony.py` (sędzia LLM triage, reużywalny), `seed_siostry.py`, `cleanup_*`. `backups/` — backupy baz.

## Pokoje (endpointy)
- **Astra solo** `/api/chat` (pełny compose + debug). **Amelia** `/api/amelia`. **Wspólny** `/api/wspolny` (Astra+Amelia — NIE ruszać).
- **Siostry** Holo/Menma/Nazuna `/api/siostry` (multiagent; `_generate_sister`, `build_sister_prompt`, router `_pick_primary`; kolekcje `holo/menma/nazuna_memory_v1` + `siostry_shared_v1`). Osobny, prostszy pipeline — NIE przez `compose_context`.
- **Amnezja** (RAG debugger) `/amnezja` + `/api/debug/inspect` (read-only trace 11 etapów + grounding + `now_override`). Widzi TYLKO Astrę.

## Dokumenty (`wazne/`)
- `fable/` — **WYŁĄCZNIE to, co powiedział Fable** (strateg): `audyty/`, `spece/`, `plany/`, `prompty/`, jego work-ordery, **case study** (`case_study_rag_memory_detox_2026-07-21.*`, live: myastra.pl/casestudy). **Własnych planów/work-orderów tu NIE zapisujemy** — idą do folderu aktora, którego dotyczą (`siostry/`, `amelia/`, `pokoj/`, `debugger/`), tak jak w `ewolucja/` (patrz `ewolucja/STRUKTURA.md`). Wyjątek: `fable/golden/` (harness + baseline'y testów) zostaje wspólne dla wszystkich pomiarów.
- `ewolucja/2026-07/` — logi zmian per data (najnowsze: `evolution_log_2026_07_15.md` detoks, `_2026_07_21.md` O1+pomiar+dere-turn).
- `logi/astra/` — dumpy rozmów (JSON z CoT+hint). `siostry/` — kanon dynamiki pokoju sióstr.

## Stan bieżący (skrót — szczegóły w MEMORY.md)
- Detoks Astry (Odtrucie #1+#2) WYKONANY: ekstraktor 6.5→0.5 śmieci/dzień, milestony 455→144, monokultura 2.0→0.65.
- **Przebieg #2** (triage achievement/gift/habit) — dry-run zamrożony (`backups/przebieg2_verdicts_*.json`), apply CZEKA na zgodę. Strażnik: R7 (kotwica altanki dociera do promptu).
- Otwarte: O1 (cap/kontekstowy filtr retype-FACT), migracja compose sióstr (odblokowuje Amnezję tam), symulator tłoku, re-run dere-turn.
