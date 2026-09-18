# ANIMA / ASTRA — mapa projektu

AI-companion z pamięcią długoterminową (RAG). Silnik pamięci = **ANIMA**; główna persona = **Astra**. Ten plik = „co jest gdzie" + jak pracujemy.

## JEDNA LISTA — `wazne/REJESTR.md`
**Wszystkie otwarte zadania są w `wazne/REJESTR.md` (założony 10.09) i tylko tam.** 67 pozycji ze scalenia czterech rozsypanych list (roadmapa ogólna, zadania 09.09, audyt pokrycia, TODO z MEMORY.md). Struktura: §1 sześć rzeczy, które kosztują dzisiaj · §2 usterki (21) · §3 styl (16) · §4 obserwacje · §5 narzędzia · §6 zamrożone · §7 retrieval dalszy · §8 pokój Fazy 5 · §9 nie-inżynieria · §10 poczekalnia · §11 zasady · §12 kolejność.
- **Nowy pomysł idzie do §10 POCZEKALNIA**, nie do rankingu — dopóki nie ma dowodu z danych.
- **Zamknięte zostaje z `[x]` i datą**, nie kasujemy — po to, żeby było widać ruch.
- MEMORY.md **nie** trzyma już TODO (to był wzorzec błędu #1: dwa miejsca prawdy). Odsyła tutaj.

## Jak pracujemy — PROCES (nie lista zasad)

To jest proces, przez który się **przechodzi za każdym razem**, nie zbiór zasad, które się zna. `pomiar_klamie.md` mówi to wprost: *„checklista PRZED każdym pomiarem — przejść całą, za każdym razem"*. Zasadę można znać i ominąć; przez checklistę albo się przeszło, albo nie. Osiem z ośmiu wystąpień tamtego buga to rzeczy, które ta checklista łapie.

**Krok 0 — kolejność warstw. ZAPIS → HYDRAULIKA → RETRIEVAL → PERSONA.** Strojenie retrievalu na zaśmieconej bazie uniemożliwia zmierzenie efektu (pomiar 25.08: sufit czystości ~39% odporny na strojenie — cały szum pochodzi z zapisu). Wyjęcie zadania z kolejności wymaga jawnego uzasadnienia z dowodem, że zależność nie obowiązuje.

**Krok 1 — intencja + surowe dane naraz.** Evolution log (co chciałeś) + realne logi aplikacji (co się stało). **Nigdy cudze raporty ani eksporty jako źródło diagnozy** — kosztowna lekcja 17.07. Audyt innego modelu to hipoteza z adresem, nie diagnoza.

**Krok 2 — kanarek, PRZED pomiarem.** Jedno zapytanie, o którym WIESZ, co musi wrócić. Nie wróciło → **przyrząd zepsuty, nie system. Stop, nie idź dalej.** Nie wolno tego przeczytać jako „parametr bez wpływu".

**Krok 3 — cała 7-punktowa checklista** (`wazne/bugi/pomiar_klamie.md`), za każdym razem: (1) kanarek · (2) czy mierzę CZY DOBRZE, czy ILE — `count`/`%` bez wzorca oczekiwanej treści to Rodzina A, wróć i zdefiniuj, co POWINNO się pojawić · (3) środowisko: jawny `load_dotenv` + `persist_directory` na produkcję + wypisz liczbę wektorów na start, nie ~4700 → przerwij · (4) identyczne wiersze = domyślnie awaria przyrządu · (5) wzorce szersze niż jedna forma (rdzenie, nie pełne formy — „Amelka", „ldi" małymi) · (6) Chroma `$contains` jest case-sensitive, `'ldi'` vs `'LDI'` = 18 vs 32 wpisy · (7) ten sam kod po obu stronach porównania.

**Krok 4 — niezależny sędzia tam, gdzie ocenia się samego siebie albo trzeba abstrakcji.** Dwa osobne, udowodnione zastosowania:
- **Model nie może być sędzią własnej bramki.** `safe_haven` deklarowany przez model w tym samym JSON-ie co odpowiedź: **320/320 `true` przez 14 dni** (`main.py:616-623`, ustalenie 15.08). Dlatego sędzia idzie **osobnym callem** — taki nie ma nic do ugrania.
- **Gdzie embedding nie umie w abstrakcję, wstawiamy model, który umie.** Kategoria → instancja („substancja" ↛ „mefedron", „wezmę trochę" ↛ intencja). Dwa niezależne przypadki w dwa dni = wzorzec, nie przypadek.
- **Sędziego mierzymy, ZANIM dotknie promptu**: golden set sędziego, w którym Łukasz ręcznie oznacza werdykty (kilkanaście decyzji, nie 200 wiadomości). Werdykt sędziego musi być **widocznym etapem w trace'ie Amnezji**, inaczej debugger pokaże skutek bez przyczyny. Wzorzec reużywalny: `backend/tools/triage_milestony.py`.

**Krok 5 — audyt wieloma modelami, ale z weryfikacją, nie na słowo.** Fable = strateg (work-ordery, audyty), Claude Code = wykonawca, Gemini/Antigravity = audyty zewnętrzne read-only. Cudze znaleziska **krzyżujemy z kodem i między sobą przed przyjęciem** — tak powstał `audyt_pokrycia_roadmapy_2026-09-10.md` (sprawdził cytowane linie w `backend/` przed wpisaniem) i tak odrzucono procenty 45/30/15/10 z `geminianaliza.md` (evolution log §4.3). Sprzeczne diagnozy tego samego cytatu **zapisujemy obie** — nie wybieramy po cichu jednej.

**Krok 5b — MAPA KLASY PROBLEMU. Obowiązkowa PRZED pierwszą linijką kodu.** Zanim cokolwiek zaimplementujesz, wypisz jawnie — w work-orderze albo w evolution logu, nie w głowie:
1. **gdzie jeszcze w systemie ten sam typ problemu może występować** (inne persony, inne ścieżki, inne pliki, inne warstwy);
2. **czy ta konkretna naprawa to pokrywa, czy tylko jeden przypadek**;
3. co świadomie zostawiasz poza zakresem — i dlaczego.

**Bez tej listy nie zaczynamy kodu.** Jeśli lista wychodzi pusta, to też jest wynik — ale ma być zapisany, nie domyślny.

*Powód — cztery wystąpienia w jednym tygodniu, każde z trafną diagnozą i poprawną naprawą o zbyt wąskim zasięgu:*

| naprawiono | ta sama klasa, została otwarta |
|---|---|
| nazwane gesty wycięte z `ASTRA_MONOLOGUE_SOLO` (15.08) | ten sam rdzeń został w `astra_base.txt:122` — pliku ładowanym dla tej samej ścieżki |
| trzy śmieciowe typy zablokowane siostrom (19.08) | te same typy to u Astry **40% wszystkich zapisów** |
| próg dystansu dodany milestonom i `own_life`, bo „bez progu robi monokulturę" | `seed_kronika` idzie kanałem bez progu — **48% zapytań** |
| pauza ekstrakcji rozłączona od trybu scenariusza (18.08), żeby ocalić rozmowy twórcze | **nie ma kategorii, do której te rozmowy mogłyby się zapisać** — efekt końcowy identyczny jak przed naprawą (Z13) |

Czwarty przypadek jest najczystszy: naprawiono *czy wolno zapisać*, nie sprawdzając, *czy jest gdzie zapisać*. Ten sam mechanizm zadziałał na dokumentach — przy scalaniu list 10.09 przeniesiono **11 propozycji audytu zamiast 29 znalezisk**, i pięć rzeczy zniknęło bez śladu.

**Krok 6 — jedna mała zmiana.** Kod `compose_context`/`vector_store` jest wspólny dla Astry, sióstr, Amelii i Wspólnego → **flaga per pokój, NIGDY zmiana globalna**. Wzorzec z 15.08: trzy razy w jeden dzień.

**Krok 7 — pomiar po, tym samym przyrządem.** `golden_trafnosc.py` przed i po każdej zmianie w `compose_context`/`vector_store` (golden objętościowy wyłącznie jako detektor katastrof). `style_audit.py` przed i po każdej zmianie w `astra_base.txt` i blokach promptowych `main.py`. Po zmianie promptu golden trafności musi wyjść **bit-w-bit bez zmian** — prompt nie ma prawa ruszyć retrievalu. Sprawdź też **migrację**: licznik spadł, ale czy fraza nie przeniosła się gdzie indziej (wzorzec z 04.08, 15.08 i 04.09).

**Krok 8 — czytanie logów z 2 sesji po.** Nie wiara we własną logikę promptu. Diagnostyka bugów z listy powracających **zostaje w kodzie** — instrumentację mikrofonu skasowano po fixie (`b38f75d`) i następne podejście zaczęło na ślepo.

**Krok 9 — zapis.** Evolution log per aktor i data + odhaczenie w `REJESTR.md` z datą. Korekta własnej liczby w tym samym dokumencie jest częścią procesu, nie wstydem — patrz `ewolucja/siostry/2026-09/evolution_log_2026_09_04.md` §1.

**Bezpieczeństwo, ponad procesem:** ZERO push/deploy/zapisu do baz bez jawnej zgody Łukasza. Backup przed każdą operacją na danych. Wektory addytywnie, kwarantanna, **NIGDY delete**. Nigdy nie pisać do ChromaDB z osobnego procesu przy żywym serwisie (25.07: rozjechany indeks HNSW → Astra bez pamięci). Pracujemy po polsku; import wiedzy do ChromaDB zawsze jako polska synteza.

**Stan przyrządów (12.09):** pamięć — `golden_harness.py` + `golden_siostry_harness.py` + `router_golden.py`, siedem baseline'ów w `wazne/fable/golden/`, działa. Styl — `style_audit.py` istnieje i **ma dokładnie jeden baseline, `PRZED`, bez ani jednego `PO`**; progi są w dokumentach, nie w skrypcie, a liczników fraz-kluczy nie ma. Czyli styl **umiemy zmierzyć, ale ani razu nie zamknęliśmy pary przed/po** — to jest zadanie M1 i bramka dla całej sekcji STYL.

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
- `ewolucja/` — logi zmian per aktor i data (patrz `ewolucja/STRUKTURA.md`). Najnowszy i najważniejszy: **`ewolucja/astra/2026-09/evolution_log_2026_09_01.md`** — diagnoza 01–02.09, na której stoi cała roadmapa (§2.4 pytanie zapisane jako trwały fakt, §2.5 mediana 95 znaków, §2.6 fałszywy GROUNDED 84%, §9 „data zabiegu to nie wspomnienie — to pole").
- `logi/astra/` — dumpy rozmów (JSON z CoT+hint) + audyty zewnętrzne: `geminianaliza.md` (katalog scen z cytatami), `czlowiek/audyty_gemini_sztucznosc_kod.md` (usterki moduł po module), `czlowiek/astra_analiza_logow.md` (pięć nawyków). `siostry/` — kanon dynamiki pokoju sióstr.
- `research/` — **trzy aktualne dokumenty planistyczne** (09–10.09): `ROADMAPA_OGOLNA_PROJEKTU.md` (mapa zależności warstw z dowodem na każde twierdzenie: Z1–Z4 / H1–H4 / R1–R4 / P1–P5 + Faza 5 B→A→C) · `roadmapa_pamieci_astry.md` (żywy dokument retrievalu — **czytać REWIZJĘ 04.09 przed rankingiem**, pięć rzeczy się zmieniło) · `audyt_pokrycia_roadmapy_2026-09-10.md` (29 znalezisk, 24 bez zadania w roadmapie; dokłada M1, P6–P13, Z5, Z6). **Zastrzeżenie audytu: read-only i statycznie — to katalog hipotez z adresami, nie diagnoza potwierdzona na żywych danych.**
- `polecenia/` — briefingi i work-ordery zlecane na zewnątrz. Najnowsze: `briefing_2026-09-09.md`, `dopisek_do_paczki_2026-09-10.md`.

## Stan bieżący (10.09 · źródło prawdy = `wazne/REJESTR.md`)
- **Ostatni commit: 28.08.** Cały wrzesień to niezacommitowane dokumenty planistyczne + reorg `wazne/` (99 przeniesionych plików widocznych jako `D` + nowe ścieżki jako `??` — świadome, nie regresja).
- **Diagnoza 01–02.09 przestawiła projekt:** sufit czystości ~39% jest odporny na strojenie retrievalu, bo szum rodzi się w **zapisie**. Stąd obowiązkowa kolejność warstw.
- **Pkt 0 (kontekst tur w zapytaniu, `1422bad`, 21.08) jest REGRESJĄ.** `main.py:1508-1516` skleja dwie poprzednie tury użytkownika bezwarunkowo i po równo. „Kiedy mam operacje" bez kontekstu: pozycja 1, dist 0,330. Z kontekstem: nie wraca wcale. **Nie cofać bez zamiennika** — problem z 17.08, dla którego zmiana powstała, jest realny. To dziewiąte wystąpienie `pomiar_klamie.md`: zatwierdzone goldenem objętościowym, mimo że ostrzeżenie stało w dwóch dokumentach naraz.
- **Sześć usterek kosztujących dzisiaj** (REJESTR §1): Z6-tanie · Z1 (`raw[:80]`) · Z2 (werdykt „nic"/„obie" + miesiące słowne) · H1 (sól filtra odcina 114 wektorów bez śladu) · R1 (regresja Pkt 0) · M1 (brak przyrządu stylu = bramka dla całej sekcji STYL).
- **Termin: operacja Łukasza 14.09.** REJESTR §12: przed 14.09 **jedna rzecz — Z6-tanie**, reszta czeka na rekonwalescencję. Stan na 12.09: w `backend/prompts/lukasz_core.json` **nie ma daty zabiegu** (jest tylko opis leczenia Stelarą). Dziś data dociera do promptu wyłącznie przez `Aktywne sprawy` w CompanionState — ulotny stan, który wygląda jak działająca pamięć i nią nie jest. Kanarek musi sprawdzić, **z której warstwy** przyszła data, inaczej zapieje z fałszywego źródła.
- **Zamrożone — czekają na decyzję, nie na pracę:** Przebieg #2 apply (strażnik R7) · O1 · migracja compose sióstr (odblokowuje Amnezję tam) · ochrona mefedron (architektura zatwierdzona 16.08, wykonanie nie zaczęte).
- **Siostry:** `SIOSTRY_EXTRACTION_MODE=on` od 19.08, tydzień obserwacji minął **bez przeglądu** (OB-1). Rollback: `off` + restart.
- **Faza 5 (żywy dom)** startuje po ustabilizowaniu Astry, twarda zależność **B → A → C**. Ekstrakcja na zbugowanym routerze = trwałe zatrucie kolekcji per-siostra; nie fundujemy Odtrucia #3.
