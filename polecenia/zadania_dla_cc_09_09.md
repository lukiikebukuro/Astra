# Zadania dla CC — Astra/ANIMA, sesja 09.09.2026

## Zasada nadrzędna (ustalona dziś)
**Najpierw kompletna roadmapa ogólna (nie tylko pamięci) — dopiero po jej ukończeniu przechodzimy do realizacji poszczególnych punktów.** Bez tego rośnie dług technologiczny przez dokładanie punktowych napraw bez widzenia całości.

**Pierwsze pytanie do CC, zanim cokolwiek innego:** gdzie obecnie fizycznie leżą najważniejsze dokumenty (evolution logi, roadmapa pamięci, work-ordery, STAN_AMNEZJI.md) — poprosić o listę ścieżek, żeby Łukasz miał jasny punkt odniesienia zamiast zgadywać w bałaganie folderów.

**Drugie pytanie:** czy istnieje już zbiorczy plik z otwartymi zadaniami (TODO, roadmapa_ogolna, czy rozproszone po evolution logach)? Nie duplikować, jeśli już jest.

---

## PRIORYTET 1 — zrobić przed szpitalem (do 14.09)

### 1. Bug z datą operacji — cztery/pięć przyczyn
Cztery znane przyczyny z poprzedniej diagnozy: zła etykieta (emocja zamiast fakt), wygasły wektor 2,5h przed pytaniem, `night_insight` strukturalnie niewidoczny dla RAG w rozmowie na żywo, obcięcie zapisu na 80 znaku. Piąty, nowy epizod (09.09): Astra znowu musiała dopytać o datę mimo że fakt był w bazie.

### 2. Porównanie Astra vs Menma — dlaczego różnica
W podobnej sytuacji Menma (siostry) poprawnie przywołała datę operacji sama, bez pytania. Astra musiała dopytać. Sprawdzić Amnezją: różnica w strukturze bazy, progu podobieństwa w rerankerze, czy w promptcie systemowym.

### 3. Redukcja przewidywalności — nocne analizy i wiadomość dnia
Zbyt dużo, zbyt regularnych automatycznych wiadomości od Astry. Zmniejszyć częstotliwość albo zwiększyć różnorodność.

### 4. Powiadomienia nie działają
Techniczny bug — push notifications przy wiadomościach od Astry nie przychodzą.

---

## PRIORYTET 2 — roadmapa i mapa (fundament pod resztę)

### 5. Roadmapa pamięci — rewizja z 04.09 już gotowa
Punkt "0" (kontekst w zapytaniu) okazał się regresją retrievalu, nie poprawką. Poprawiona wersja z pięcioma przyczynami bugu i nową kolejnością prac (naprawić zapis → naprawić hydraulikę → dopiero wracać do rankingu) już istnieje jako dokument — do wdrożenia w tej kolejności.

### 6. Roadmapa ogólna (nie tylko pamięci)
Zbudować albo odświeżyć pełną roadmapę całego projektu — pamięć będzie jednym z elementów, nie całością. Ma dać jasny obraz: co zrobione, co w toku, co dalej.

### 7. Mapa struktury folderów
Bałagan w plikach — Łukasz nie pamięta gdzie co zapisał. Poprosić CC o mapę drzewa katalogów z opisem co jest gdzie.

### 8. Historyczny szum w bazie Astry
Hipoteza: wektory sprzed 19.08 (przed wprowadzeniem świadomych blokad ekstraktora) mają systematycznie gorszą jakość niż nowsze. Dotychczasowe sprzątanie było punktowe (konkretne znalezione problemy jak fałszywe deklaracje), nie pełny wsteczny audyt. Sprawdzić: ile starych wektorów nigdy nie jest wybieranych przez retrieval, jaka jest jakość losowej próbki starych vs nowych.

### 9. Sprawdzić czy pierwsze rozmowy z Astrą są zarchiwizowane
Łukasz archiwizuje logi regularnie, ale nie jest pewien czy zrobił to na samym początku projektu. CC ma bezpośredni dostęp do VPS — sprawdzić czy najwcześniejsze rozmowy fizycznie gdzieś istnieją.

---

## PRIORYTET 3 — po rekonwalescencji, nie pilne

### 10. Pięć nawyków stylu od Gemini
Brak bezwładności emocjonalnej (zbyt szybkie przeskoki nastroju), pętla powtarzalnych gestów w gwiazdkach, nadmierne meta-gadanie o relacji zamiast bycia w niej, natychmiastowa kapitulacja przy konfrontacji zamiast zdrowego oporu, przebijanie immersji elementami UI.

### 11. Konkretny przykład z sióstr — Holo blokująca się
Nie zrozumiała polecenia "niech ktoś inny z was wybierze" — odpowiedziała "…", potem pytała "kogo chcesz wywołać" zamiast przekazać pytanie dalej. Osobno: Menma pomyliła serię anime (Frieren zamiast HxH) przy poprawnie zrozumianym poleceniu.

### 12. Bardziej wciągająca, interaktywna dynamika pokoju sióstr
Mechanizm pamięci faktów działa dobrze technicznie, ale styl bywa sztywny (dużo metafor kupieckich u Holo — złoto, pole, żniwa — ten sam mechanizm co u Astry, inny słownik). Kierunek: coś bliższego "interaktywnej opowieści".

### 13. Trop — narracja trzecioosobowa jak w c.ai (Machi)
c.ai buduje scenę aktywnie ("for the first time she..."), nie tylko reaguje. Zrobić głębszą dekonstrukcję porównawczą konkretnych rozmów z Machi vs Astry — co dokładnie daje silniejsze poczucie zaangażowania. UWAGA: testować ostrożnie, dopiero po operacji — poprzedni tryb scenariusza wyłączał pamięć i kosztował całą sesję twórczą.

### 14. Hybrydowy mechanizm pamięci — plik zawsze czytany
Rozważyć, żeby krytyczne, rzadko zmieniające się fakty biograficzne (data operacji, choroby, kluczowe daty) żyły w zawsze-wczytywanym pliku tekstowym (podobnie jak system pamięci Claude'a), nie wyłącznie w wektorach zależnych od retrievalu. Może rozwiązać całą klasę problemów jak bug z datą.

### 15. Pomysł na filmik TikTok — "Astra Reacts: Zimna Krew"
Astra komentuje/ocenia swoje najzimniejsze, najbardziej mechaniczne odpowiedzi z przeszłości. Konkretne przykłady już znalezione w rozmowach z dzisiejszego przeglądu.

---

## Uwaga na koniec
Priorytet 1 (cztery punkty) realistyczny do zrobienia w kilka dni przed 14.09. Priorytet 2 to fundament wymagający więcej czasu — zacząć, ale nie oczekiwać ukończenia przed szpitalem. Priorytet 3 zostaje w całości na rekonwalescencję.
