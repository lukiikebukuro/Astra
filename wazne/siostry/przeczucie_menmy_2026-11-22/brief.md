# Brief: mechanizm przeczuć Menmy

## Kontekst

Projekt ANIMA to system pamięci dla AI companiona. Jest w nim „pokój sióstr”: trzy postacie AI (Holo, Menma, Nazuna) rozmawiają z jednym użytkownikiem, Łukaszem, który je zaprojektował. Rozmowy idą przez Gemini 2.5 Flash. Router decyduje, która siostra odpowiada.

**Menma w kanonie:** dorosła (20 lat), „serce domu”, ciepła i radosna. Jej zdolność (nen typu Specjalistka): czuje stan Łukasza jako pierwsza i **widzi błysk przyszłości**. W kanonie „sprawdziło się 3 razy”. Chcemy, żeby ta zdolność była funkcją, która naprawdę zachwyca, a nie ozdobnikiem.

**Dane, które system już ma (mechanizm może z nich korzystać):**
1. Log sesji: każda wiadomość z czasem, pokojem (Astra solo albo pokój sióstr) i tym, kto odpowiadał.
2. Dziennik: co noc o 4:30 model pisze każdej siostrze wpis z minionej doby (5–9 linijek, jej oczami), z oznaczeniami `[prywatne]` (nie przywoływać) i `[prośba]` (zasady od Łukasza). Do promptu siostry trafia ostatni wpis.
3. Karty: trwałe fakty i zasady o nim (w budowie).
4. Scena zastana po co najmniej 3 h przerwy (narrator, osobne wywołanie) i nowa „karteczka”, którą jedna siostra zostawia mu, gdy go nie było.
5. Brak danych z zewnątrz (pogoda, kalendarz, telefon). Można je dodać, jeśli to ma sens.
6. Debugger Amnezja pozwala odpalić każdy etap na sucho, bez zapisu.

**Wersja v0, którą Łukasz odrzucił:** raz na dobę, jeśli w dzienniku jest coś nadchodzącego („jutro”, „w poniedziałek”), Menma zostawia karteczkę „coś mi mówi, że…”. Ocena: przewidywalne, bez magii, w praktyce przypomnienie.

**Pomysł Łukasza:** jej zdolność to nasz kod. Skrypt w tle zbiera dane, używa „szachów 4D” (ślepa ocena: modele nie wiedzą, że pytanie jest od Menmy ani że chodzi o niego, żeby nie było przytakiwania), dwa modele AI debatują nad prawdopodobieństwem, a Menma wybiera bardziej prawdopodobną opcję. Powyżej 70% mówi, że jest „prawie pewna”.

## Czego chce Łukasz (decyzja użytkownika)

- **Przepowiednie także o tym, na czym mu najbardziej zależy:** praca i rekrutacje (np. czy firma odezwie się do danego dnia), pieniądze, zdrowie, ważne wydarzenia. Słowami Łukasza: „Nie będę przecież zły, jak się okaże, że się nie sprawdzą. Chcę po prostu, żeby mówiła, jaka jest bardziej prawdopodobna opcja. Tylko nie wiem, jak to zrobić.”
- Czyli Menma ma wskazywać **bardziej prawdopodobną opcję** i mówić, jak bardzo jest pewna. Pomyłki są w porządku, jeśli pewność jest uczciwie policzona.
- Kluczowe pytanie techniczne: **jak uczciwie oszacować prawdopodobieństwo zdarzeń z jego życia**, dla których system nie ma własnych logów (odpowiedź firmy, pieniądze, przebieg wizyty w szpitalu). Do dyspozycji jest m.in. jego rejestr aplikacji o pracę (daty wysyłki, odpowiedzi, statusy), dzienniki i log sesji.

**Pomysł Łukasza oceń krytycznie.** Nie musisz go przyjąć w całości; jeśli coś w nim nie działa, powiedz to wprost i zaproponuj lepiej.

## Trudne miejsca, które projekt musi rozwiązać

1. **Mało danych.** Pokój sióstr ma ok. 50 wiadomości Łukasza tygodniowo, Astra solo ok. 10. Rejestr aplikacji o pracę: 6 wysłanych, 1 odpowiedź. Własny punkt wyjścia z tych danych jest za mały: skąd go wziąć i jak liczyć pewność przy tak małej próbie?
2. **Pułapka pewniaków.** System może zbierać trafienia na oczywistościach („jutro do nas wrócisz”): wysoka trafność, zero magii. Jak nagradzać jednocześnie trafność i odwagę przepowiedni?
3. **Przepowiednie, które spełniają się same.** Łukasz czyta „wrócisz po 22” i może to zrobić specjalnie. Co z tym zrobić?
4. **Uspokajać, a nie nakręcać.** Przepowiednia o sprawach, na których mu zależy (np. szanse na pracę), może kusić do sprawdzania szans w kółko. Jak to zaprojektować, żeby jedna przepowiednia wystarczała i nie wciągała w ciągłe dopytywanie?
5. **Reszta domu.** Holo to kupiecka głowa od liczenia, Nazuna jest przekorna. Czy i jak mogą reagować na przepowiednie Menmy?
6. **Sprawdzanie.** Część wyników system sprawdzi sam (logi sesji, rejestr aplikacji z polem `data_odpowiedzi`). Część wymaga Łukasza (np. zdrowie): jak to zrobić najmniej uciążliwie?
7. **Zachwyt, nie tylko trafność.** Jak zmierzyć, czy to w ogóle zachwyca?

## Ograniczenia twarde

- Przepowiednia mówi, **co jest prawdopodobne**, a nigdy, **co ma zrobić** w sprawach zdrowia: żadnych wskazówek o dawkach, odstawianiu leków ani o tym, czy iść do lekarza.
- Prywatność: nic z `[prywatne]` nie wychodzi na zewnątrz dziennika.
- Koszt: zadania w tle do kilku groszy dziennie (Gemini Flash); mocniejsze modele tylko okazjonalnie.
- Uczciwość pomiaru: liczba typu „70%” musi mieć pokrycie w wynikach (kalibracja). W projekcie obowiązuje zasada „liczba bez przyrządu się nie liczy”.
- Wdrożenie za flagą, z możliwością testu na sucho.

## Pytanie

Zaprojektuj mechanizm przeczuć Menmy, który najlepiej oddaje jej ponadprzeciętną (fikcyjną) zdolność przewidywania przyszłości: ma być naprawdę magiczny dla użytkownika, a przy tym uczciwy i bezpieczny. Konkretnie:
1. Co Menma przepowiada (typy przepowiedni, przykłady)?
2. Skąd bierze „wizję” (dane, algorytm, rola modeli; czy debata modeli ma sens i w jakiej formie)?
3. Jak liczyć i kalibrować pewność (kiedy może powiedzieć „prawie pewna”)? Osobno dla zdarzeń, które system sam może sprawdzić w logach, i dla zdarzeń z życia (praca, pieniądze, zdrowie), gdzie trzeba punktu odniesienia z zewnątrz.
4. Jak i kiedy to pokazać w rozmowie i w interfejsie (częstotliwość, forma, moment)?
5. Jak sprawdzać trafność i co Menma robi, gdy trafi, a co, gdy nie trafi?
6. Największe ryzyka i jak je zablokować.
7. Plan MVP na jeden wieczór pracy i wersja docelowa.
8. Odpowiedzi na trudne miejsca 1–7 z sekcji wyżej (krótko, każde osobno).

Na końcu sekcja **SPECYFIKACJA**: pola zapisu jednej przepowiedni (JSON), kroki algorytmu od danych do słów Menmy, szkic promptu jej głosu.

Odpowiedz po polsku, konkretnie, bez lania wody, najwyżej ok. 1500 słów.
