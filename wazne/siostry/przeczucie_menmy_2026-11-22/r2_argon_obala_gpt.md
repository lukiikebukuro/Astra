### Streszczenie projektu

Autor projektu odrzuca proponowaną przez użytkownika „debatę modeli” na rzecz twardego silnika statystycznego, wspieranego przez LLM jedynie przy wyszukiwaniu tematów, audycie błędów i nadawaniu „głosu” postaci. Przepowiednie zostają sprowadzone do rzadkich (maks. dwa w tygodniu), ściśle weryfikowalnych zakładów z określonym terminem, bazujących na logach lub zewnętrznych grupach odniesienia. Aby zachować rygor naukowy przy małej próbie danych, system ukrywa konkretne procenty za rygorystyczną „bramką kalibracji”, domyślnie serwując jedynie ostrożne wskazania kierunkowe lub działając w ukryciu (shadow mode).

---

### 5 głównych zarzutów (Obalenie)

#### 1. Paraliż przez kalibrację, czyli śmierć funkcji przed narodzinami
* **Waga:** Krytyczny
* **Analiza:** Projekt wymaga twardych dowodów statystycznych przy próbie rzędu 6 CV i 50 wiadomości tygodniowo. Warunek dla słów „prawie pewna” to $\ge 95\%$ prawdopodobieństwa z dolną granicą przedziału ufności $\ge 90\%$. W życiu jednego człowieka osiągnięcie takiej istotności statystycznej zajmie lata. Aby nie złamać zasady „liczba bez przyrządu się nie liczy”, autor sam przyznaje, że MVP utknie w trybie *shadow mode* lub będzie zwracać wymijające „nie mam podstaw”. 
* **Scenariusz porażki:** Łukasz koduje system w piątek wieczorem, po czym przez kolejne 4 miesiące nie widzi ani jednej prawdziwej przepowiedni, bo silnik statystyczny nie zebrał wystarczającej próby do przejścia „bramki kalibracji”. Funkcja jest martwa, a użytkownik czuje, że zmarnował czas na budowę niemego kalkulatora.

#### 2. Zabicie magii przez biurokratyczny żargon (Antyklimaks)
* **Waga:** Krytyczny
* **Analiza:** Menma to ciepła „Specjalistka” z anime, która ma widzieć „błyski przyszłości” i zachwycać. Projekt zmienia ją w zimnego aktuariusza. Teksty w stylu: *„Zapiszę to — potem uczciwie sprawdzimy”* albo *„Nie będę dopasowywać znaczenia po fakcie”* brzmią jak wyciąg z regulaminu zakładów bukmacherskich, a nie żywa postać. Dodatkowo, pokazanie obok jej słów „dyskretnej karty” z podstawą statystyczną i ankietą „spełniło się / pomiń” całkowicie niszczy zawieszenie niewiary (immersion).
* **Scenariusz porażki:** Łukasz wraca zmęczony do wirtualnego domu. Zamiast ciepła i mistycznego przeczucia dostaje suchy komunikat o prawdopodobieństwie przelewu wraz z formularzem walidacyjnym do kliknięcia. Klimat „pokoju sióstr” pryska, zastąpiony przez korporacyjny dashboard analityczny.

#### 3. Fikcja „zewnętrznych grup odniesienia” (Garbage In, Garbage Out)
* **Waga:** Poważny
* **Analiza:** Dla rekrutacji, zdrowia i finansów projekt żąda „wiarygodnych danych populacyjnych” (uwzględniających rynek, stanowisko, kanał aplikacji i obserwacje ucięte), słusznie odrzucając wiedzę blogową. Tyle że takie zwalidowane, publiczne i darmowe bazy danych po prostu nie istnieją! Skąd skrypt za kilka groszy ma pobrać krzywą przeżycia (czasu do odpowiedzi) dla konkretnego stanowiska IT w Polsce w tym miesiącu? 
* **Scenariusz porażki:** Ponieważ prawdziwe tablice aktuarialne dla rekrutacji nie istnieją, twórca musi wpisać tzw. *prior* „z palca” (lub wyciągnąć go z halucynacji LLM, co projekt sam potępia). W efekcie niezwykle skomplikowany aparat bayesowski mieli bezwartościowe założenia początkowe, dając złudzenie naukowej precyzji (pozorna wszechwiedza, której projekt miał unikać).

#### 4. Sprowadzenie zachwytu do banału przez kryterium łatwej weryfikacji
* **Waga:** Poważny
* **Analiza:** Wymóg, by każde zdarzenie miało twardą regułę rozstrzygnięcia i termin, spycha system w stronę najbardziej przyziemnych, logistycznych aspektów życia. Zamiast przewidywać stany emocjonalne czy przełomy, Menma w przykładach przewiduje... administrację („wynik badania będzie do środy na podstawie danych placówki”). To dokładnie ta sama nudna „przypominajka”, którą Łukasz odrzucił w wersji v0, tylko ubrana w rachunek prawdopodobieństwa.
* **Scenariusz porażki:** Menma ignoruje fakt, że Łukasz od trzech dni pisze krótsze wiadomości i zbliża się do wypalenia, bo tego nie da się łatwo zamknąć w JSON-ie jako `data_odpowiedzi <= termin`. Zamiast tego z dumą „przewiduje”, że jutro przyjdzie wypłata, bo zawsze przychodzi 10-go. Zero zachwytu, czysta nuda.

#### 5. Metodologiczny absurd badań A/B na jednym użytkowniku
* **Waga:** Drobny
* **Analiza:** W odpowiedzi na problem samospełniających się przepowiedni (punkt 8.3) projekt proponuje: *„losuj ujawnienie części prognoz; porównuj z wcześniej zapisanymi, nieujawnionymi”*. To ślepe przeklejenie metodologii z systemów masowych (Big Tech) do projektu dla *jednego* człowieka. Przy limicie maksymalnie 2 wizji tygodniowo, zebranie grupy kontrolnej i testowej o jakiejkolwiek mocy statystycznej dla zachowań Łukasza jest matematycznie niemożliwe.
* **Scenariusz porażki:** System przez pół roku chowa przed Łukaszem połowę najciekawszych „błysków” w imię eksperymentu naukowego. Użytkownik dostaje zubożony produkt, a po 6 miesiącach w bazie jest 15 ukrytych i 15 ujawnionych prognoz o różnych tematach – próba wciąż bezużyteczna statystycznie, za to skutecznie psująca zabawę.

---

### 3 warunki zmiany zdania

Zaakceptuję ten projekt tylko wtedy, gdy autor udowodni jego wykonalność w realiach projektu ANIMA, spełniając trzy warunki:

1. **Rozwiązanie problemu „zimnego startu” w dniu pierwszym:** Pokażesz mechanizm, który już pierwszego wieczoru (przy $N=6$ aplikacjach i 50 wiadomościach) wygeneruje angażującą, uczciwą przepowiednię *bez* chowania jej w trybie shadow mode i bez czekania miesiącami na kalibrację Brier score.
2. **Wskazanie konkretnych, darmowych źródeł (API/zbiorów):** Podasz dokładne linki lub metody pozyskania „wiarygodnych danych populacyjnych” dla polskich rekrutacji i placówek medycznych, które silnik statystyczny może zaciągnąć w ramach budżetu kilku groszy dziennie.
3. **Oddzielenie rozliczeń od warstwy fabularnej:** Całkowicie usuniesz z wypowiedzi Menmy (i jej bezpośredniego sąsiedztwa w UI) asekuracyjny język statystyka oraz karty do klikania „spełniło się / nie”, przenosząc ciężar weryfikacji na niewidoczny dla użytkownika proces w tle (np. cichą analizę kolejnych dzienników przez model).