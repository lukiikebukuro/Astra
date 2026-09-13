# Polecenia dla agenta w Antigravity — sesja 09.09.2026

## Kontekst
Pracujesz na kopii/sandboxie repo Astry/ANIMA. Główny agent (Claude Code na VPS) prowadzi produkcję — TY nie deployujesz nic, nie zapisujesz do żadnej bazy produkcyjnej. To sesja diagnostyczna, read-only, mająca dać materiał do porównania z tym co już wie CC.

## Zadanie 1 — priorytet, zrób jako pierwsze
Sprawdź, czy istnieje już w repo zbiorczy plik/dokument z listą otwartych zadań (może nazywać się TODO, otwarte_zadania, roadmapa_ogolna, albo być rozproszony po evolution logach w `wazne/ewolucja/`). Znajdź go i streść jego zawartość. Jeśli nie istnieje, powiedz to wprost — nie zgaduj.

## Zadanie 2 — bug z datą operacji
W kodzie odpowiedzialnym za ekstrakcję i retrieval (prawdopodobnie `main.py`, `vector_store.py`, moduł ekstraktora) sprawdź:
- Jak dokładnie fakt typu `DATE:medical_visit` jest zapisywany — czy trafia do FactStore, czy tylko do wektorów
- Czy istnieje ograniczenie długości zapisu (jak wcześniej znalezione obcięcie na 80 znaku) które mogłoby ucinać datę
- Czy `night_insight` (nocna analiza) ma osobny kanał w retrievalu, czy jest czytany tylko przez poranną wiadomość

## Zadanie 3 — porównanie Astra vs Menma (siostry)
Znajdź w logach konkretny przypadek, gdzie Menma poprawnie przywołała datę operacji bez pytania, podczas gdy Astra w podobnej sytuacji musiała dopytać. Sprawdź czy różnica leży w: (a) innej strukturze ich baz wektorowych, (b) różnym progu podobieństwa/dystansu w rerankerze, (c) czymś w promptcie systemowym każdej z nich.

## Zadanie 4 — wiek wektorów w bazie Astry
Policz rozkład dat utworzenia wektorów w `astra_memory_v1`. Sprawdź czy wektory sprzed 19.08.2026 (przed wprowadzeniem świadomych blokad ekstraktora) mają:
- Wyższy odsetek nigdy niewybieranych przez retrieval (martwe wpisy)
- Niższą jakość przy losowej próbce (porównaj 20 losowych starych vs 20 losowych nowych)

## Zadanie 5 — mapa struktury folderów
Zrób prostą mapę drzewa katalogów całego repo (nie tylko `wazne/`), z jednym zdaniem opisu co jest w każdym folderze najwyższego poziomu. Cel: Łukasz gubi się w tym gdzie co leży.

## Format odpowiedzi
Zwięźle, po polsku, z konkretnymi ścieżkami plików i liniami kodu gdzie to możliwe. Nie proponuj zmian w kodzie — to zadanie czysto diagnostyczne. Jeśli czegoś nie możesz sprawdzić (brak dostępu, plik nie istnieje), powiedz to wprost zamiast zgadywać.
