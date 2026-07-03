# FABLE (terminal, repo, read-only) — Audyt pokoju sióstr MVP (Holo/Menma/Nazuna)

> RAMA: Nie wierz raportowi wykonawcy (Opusa) — sprawdź na kodzie. Nie chwal, szukaj gdzie się mylą.
> Próbuj OBALIĆ każde twierdzenie, nie potwierdzić. Read-only, NIE edytuj, NIE commituj.
> Kod sióstr: `backend/main.py` (sekcja "POKÓJ SIÓSTR"), `backend/prompts/{holo,menma,nazuna}_persona.txt`,
> `backend/siostry.html`. Gałąź: `main` (wdrożona). Router-3-naraz jest na `main` ale NIE wdrożony (VPS=becb138).

## 1. MOJE TWIERDZENIA JAKO HIPOTEZY (obal albo potwierdź, plik:linia)
- **Router silent-first** (`_route_siostry`, ~main.py:1724): twierdzę, że persona „silent" NIE dostaje calla Gemini — endpoint `siostry_chat` generuje TYLKO dla person zwróconych z routera. Sprawdź: czy decyzja zapada PRZED callem (nie: woła i odrzuca)? Czy da się doprowadzić do 3 calli przy zwykłej turze?
- **Fleksja imion** (`SISTERS[...]["forms"]`, `_sister_called` z `\b`): pokaż listę form. Które odmiany NIE pokryte? Czy krótkie „holo" daje false-positive w środku słów (np. „holograficzny", „alkohol")? `\b` to ratuje czy nie?
- **Rotacja anti-sync** (`_remember_first`, `_siostry_recent`, `_pick_primary`): to faktyczna rotacja, czy dwie persony mogą się zblokować w pętli (jedna systematycznie ostatnia / nigdy nie prowadzi)?
- **Izolacja kolekcji** (`_sister_vs`, `_generate_sister`): czy zapytanie siostry FIZYCZNIE nie sięga kolekcji Astry/Amelii/innej siostry? Gdzie filtr, da się obejść? (uwaga: cross-room świadomie OFF na MVP — potwierdź, że naprawdę OFF).
- **Extraction OFF** (`_generate_sister`): potwierdź na ścieżce kodu, że ŻADEN zapis do pamięci semantycznej się nie dzieje (tylko `add_session_message` do `siostry_shared_vs`). Echo-loop guard realny?
- **Narrator / scena zastana** (`_scene_as_found`): czy narrator MOŻE wygenerować myśli/emocje/słowa sióstr (przekroczyć „kamera nie reżyser")? Gdzie granica w kodzie — tylko w prompcie, czy jest twardsza?
- **Provenance `origin_endpoint="holo_room"`**: UWAGA — runtime `_generate_sister` NIE pisze enriched memory (extraction OFF), tylko session messages. Więc provenance holo_room jest TYLKO na seedzie, nie na runtime. Potwierdź/obal: gdzie realnie trafia metka, i czy to problem.

## 2. POLOWANIE NA BUGI (edge cases)
Pusta scena; wszystkie trzy wywołane naraz z imienia; wiadomość po 23:00 (reguła Nazuny — sprawdź strefę czasową w `_warsaw_hour`); bardzo długa wiadomość; brak historii sesji (pierwsza tura + scena); równoległy request (globalny `_siostry_recent` bez locka); koszt/latencja przy 3 callach sekwencyjnych.

## 3. ORYGINALNE ZARZUTY DO SPRAWDZENIA
Aliasing w scenie/trace; serializacja JSON odpowiedzi `/api/siostry` (numpy/float?); escapowanie w `siostry.html` (XSS/łamanie renderu przez `<` w treści rozmowy — czy `esc()` pokrywa wszystko?); bind uvicorna (127.0.0.1 vs 0.0.0.0); auth na `/siostry` ORAZ `/amnezja` (nginx server-level — potwierdź, że oba pod zamkiem, i czy `/api/siostry` też).

## 4. SEKCJA OTWARTA (wolna ręka)
Czego NIE przewidzieliśmy? Gdzie system jest kruchy w sposób spoza tej listy? Cross-persona przeciek, echo-loop przy trzech głosach, dryf charakteru per siostra, failure mode przy skali — cokolwiek widzisz świeżym okiem.

## OUTPUT
Bugi wg ryzyka (plik:linia + jak udowodnić: test/diff/trace). Twierdzenia które NIE bronią się pod inspekcją. Go/No-Go dla dalszego użytku. Raport zapisz do `wazne/research/analiza/fable_9_WYNIK_audyt-siostr.md`.
