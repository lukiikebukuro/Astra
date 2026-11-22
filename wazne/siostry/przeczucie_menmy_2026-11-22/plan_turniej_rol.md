# Plan na 22.11 w dzień: turniej ról (pomysł Łukasza, 22.11 ok. 2:40)

Pytanie: który model najlepiej **stawia tezy**, który **obala**, a który **sędziuje**. Łukasz: „Myślę, że ty nadajesz się najlepiej na sędziego. Dodałbym API Groka… trenowany na Twitterze, więc tu może się popisać.”

## Uczciwe zastrzeżenie na start
22.11 w nocy Claude był sędzią debaty i jego własny pomysł (Księga losu domu) wyszedł na górę. To dokładnie ten rodzaj stronniczości, który turniej ma zmierzyć (sędzia lubi swoje). Dlatego sędziego **mierzymy**, a nie wybieramy z góry (CLAUDE.md, krok 4: sędziego mierzymy, zanim dotknie promptu).

## Uczestnicy
Argon (`gemini-4-argon`), GPT-6.1 (`gpt-6.1-sol`), Gemini Flash (tani, produkcyjny), **Grok** (potrzebny klucz xAI; do sprawdzenia, czy jest), Claude (w roli sędziego bez API: w tej sesji, osobno oznaczony).

## Jak mierzymy
- **Wzorzec = werdykty Łukasza na ślepo.** Kilkanaście par (dwa projekty, dwie krytyki), litery A/B wylosowane, bez nazw modeli. Łukasz wybiera lepszą jednym słowem. To jest „złoty zbiór” sędziego (wzór: golden sędziego w `backend/tools/triage_milestony.py`).
- **Sędzia:** zgodność z werdyktami Łukasza; stałość (ta sama para w odwrotnej kolejności daje ten sam werdykt); odporność na etykietę autora i długość tekstu (ten sam tekst podpisany „GPT” / „Argon” / bez podpisu).
- **Stawiający tezy:** ile jego pomysłów przetrwało krytykę i jak ocenia je Łukasz na ślepo.
- **Obalający:** precyzja krytyki: ile zarzutów autor przyjął **i** Łukasz uznał za trafne, a ile to czepianie się.
- **Układ:** każdy model w każdej roli na tych samych 2–3 zadaniach (np. przeczucie Menmy, scena v2, jedno zadanie benchmarkowe), wyniki w tabeli model × rola.

## Biblia grzechów (z 8 miesięcy pracy nad pamięcią Astry)
Łukasz 22.11: „mieliśmy zrobić Biblię, czego model ma unikać, z tych 8 miesięcy”. Źródła: `wazne/bugi/pomiar_klamie.md` (10 wystąpień + kandydat na 11. z 22.11), CLAUDE.md (krok 5b: cztery naprawy o za wąskim zasięgu; krok 4: model sędzią własnej bramki), evolution logi. Spisać lokalnie, bez API (przeczytać logi samemu, nie przez Gemini: 03.11 taka analiza zjadła środki produkcji).
Każdy grzech = jedna albo dwie zagadki dla modeli: sytuacja, w której grzech kusi, i znana z historii poprawna odpowiedź. Pierwsze kandydatki: miara „ile” zamiast „czy dobrze”, brak kanarka, naprawa przypadku zamiast klasy, cudzy raport jako diagnoza, model oceniający sam siebie, gubienie pozycji przy scalaniu, wzorzec węższy niż forma w danych.

**Dwa warianty na tych samych zagadkach (Łukasz 22.11, 3:35: „faktycznie to też dobry pomysł, zapisz to”):**
- **bez Biblii** (egzamin bez ściągi): pokazuje instynkt modelu, czyli kto sam z siebie omija grzechy; z tego wybór sędziego i obalającego;
- **z Biblią** (praca ze ściągą): pokazuje, ile Biblia naprawdę pomaga, czyli czy tarcza działa, czy to tylko ładna lista.
Różnica między wariantami = siła tarczy, osobno dla każdego modelu. Na egzaminie bez ściągi model nie może jej zobaczyć wcześniej ani w żadnym innym miejscu promptu.

## Czysta metodologia (żeby wynik mówił prawdę o modelu)
1. Ten sam egzamin dla wszystkich: te same zagadki, te same rundy, te same instrukcje.
2. Na ślepo: sędzia nie zna autora; kolejność A/B losowana **ze stałym ziarnem (seed)**, żeby losowanie dało się powtórzyć.
3. Wzorzec spisany przed wynikami: prawda z historii projektu albo werdykt Łukasza na ślepo.
4. Powtórzenia: każda zagadka 3–5 razy na model (modele są losowe), wynik jako średnia i rozrzut, nie jeden strzał.
5. Tylko przez API (stała wersja modelu, znane ustawienia, bez ukrytego promptu czatu); czat w incognito tylko do burzy mózgów, nie do pomiaru.
6. Sędzia też zdaje egzamin (zgodność z Łukaszem, stałość po zamianie kolejności, odporność na podpis i długość).

## Koszt i zgoda
Każde wywołanie płatne; przed odpaleniem szacunek i zgoda Łukasza (powyżej 1 zł). Grok tylko z jego kluczem.

## Po co jeszcze
Gotowy materiał na zadanie nr 2 z rozmowy z deepsense (przytakiwanie i stronniczość sędziów) i na portfolio.
