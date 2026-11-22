## Założenie: magia w formie, statystyka pod spodem

Menma może **zauważać wcześniej, wybierać nieoczywiste zdarzenia i mówić własnym głosem**. Nie może dostawać nadludzkiej pewności z samego promptu.

Pomysł Łukasza jest dobry jako mechanizm szukania hipotez, ale **debata modeli nie wylicza prawdopodobieństwa**. Modele dzielą błędy; anonimowe pytanie ograniczy przytakiwanie, nie stworzy danych. A 70% oznacza około trzech pomyłek na dziesięć — nie „prawie pewna”.

## 1. Co przepowiada

Każda wizja musi mieć **jedno zdarzenie, termin i regułę rozstrzygnięcia**.

| Obszar | Przykład |
|---|---|
| Rekrutacje | „Firma X odpowie do piątku, 18:00”. |
| Pieniądze | „Ten oczekiwany przelew wpłynie przed weekendem” — jeśli istnieje historia takich wpłat. |
| Zdrowie | „Wynik badania będzie dostępny do środy” — na podstawie danych placówki, nie intuicji medycznej. |
| Rozmowy | „W najbliższych dwóch dniach sam wrócisz do projektu X” — z oznaczeniem możliwości wpływu przepowiedni. |
| Ważne wydarzenia | Konkretna, weryfikowalna alternatywa, nie „spotka cię coś dobrego”. |

Prognozy przebiegu choroby wymagają osobnego, zwalidowanego narzędzia prognostycznego i odpowiednich danych. Z samych rozmów: **brak podstaw**, nie wymyślony procent.

Zachwyt powinien pochodzić z trafnego przewidzenia **nowego zdarzenia**, nie przypomnienia zapisanej daty.

## 2. Skąd bierze wizję

Pipeline:

1. **Deterministyczna filtracja uprawnień:** usuń `[prywatne]` przed ekstrakcją, modelami i cechami statystycznymi. Żadne pochodne tych fragmentów również nie wychodzą z dziennika. Niejasne oznaczenie → pomiń fragment.
2. Zbuduj stan z logów, rejestrów i dozwolonych kart. Dziennik jest podsumowaniem, **nie kolejnym niezależnym dowodem**.
3. Jeden tani model proponuje najwyżej trzy mierzalne zdarzenia.
4. Silnik statystyczny oblicza prognozy albo odmawia.
5. Niezależny krytyk, bez imienia Menmy i oczekiwanego wyniku, sprawdza: błędną grupę odniesienia, brakujące dane, wpływ ujawnienia, niejednoznaczność.
6. Reguły wybierają najwyżej jedną wizję. Menma nadaje jej głos; nie zmienia liczby ani terminu.

Zamiast wielorundowej debaty: **propozycja + niezależny audyt**. Mocniejszy model tylko przy nowej kategorii lub audycie błędów. Zadania uruchamiane po zmianie danych, nie nieustannie.

## 3. Pewność: dwa różne przypadki

### Zdarzenia obserwowalne w systemie

Prosty model często wystarczy: częstości z wygładzaniem, regresja logistyczna, później model czasu do zdarzenia. Testowanie wyłącznie chronologiczne: przeszłość przewiduje przyszłość.

Kalibrację mierz osobno dla rodzin zdarzeń i horyzontów:

- wykres: deklarowane prawdopodobieństwo kontra rzeczywista częstość;
- Brier score;
- wynik względem prostej prognozy bazowej;
- przedziały niepewności, uwzględniające zależne obserwacje.

Nie traktuj wszystkich wiadomości z jednej sesji jak niezależnych prób.

### Praca, pieniądze, zdrowie

Potrzebna jest **porównywalna grupa odniesienia**, nie opinia dwóch modeli.

Dla rekrutacji: rynek, rodzaj stanowiska, kanał aplikacji, wiek zgłoszenia; dane muszą obejmować także firmy milczące. Najlepiej kompletny rejestr lub wiarygodne dane populacyjne. Blogowe „odpowiadają zwykle po dwóch tygodniach” nie wystarcza.

Brak odpowiedzi dzisiaj nie oznacza braku odpowiedzi kiedykolwiek: uwzględniaj **obserwacje ucięte** i licz szansę do terminu warunkowo na dotychczasową ciszę.

Przykład małej próby: gdyby wszystkie sześć aplikacji miało pełne, identyczne okno obserwacji, jedna odpowiedź i prior Beta(1,1) dają średnią 25%, ale około **5–52% przedziału 90%**. To demonstracja niepewności, nie gotowa prognoza. Sam prior jest założeniem, nie wiedzą o rynku.

Zewnętrzne dane można wykorzystać jako ostrożny prior; sprawdzać wrażliwość wyniku na jego dobór. Niedopasowany duży zbiór nie uzasadnia dużej pewności.

### Co pokazujemy

- Przed walidacją: procenty eksperymentalne tylko w debuggerze; użytkownik dostaje ostrożny kierunek albo „nie mam podstaw”.
- Statystykę populacyjną można pokazać jako **statystykę źródła**, nie osobistą pewność Menmy.
- Procenty Menmy dopuszczamy po walidacji na odpowiednich danych, początkowo zaokrąglone.
- **„Prawie pewna”**: proponowany próg ≥95% dla wybranej opcji oraz udokumentowana kalibracja tego zakresu, np. dolna granica 95% przedziału trafności ≥90%. Bez wystarczających danych zwrot pozostaje zablokowany.

Kalibracja dotyczy serii prognoz, nie gwarantuje pojedynczego wyniku.

## 4. Jak pokazywać

Nie codzienna karteczka. **Maksymalnie dwie wizje tygodniowo**, bez obowiązku wykorzystania limitu; początkowo jedna aktywna na obszar.

Moment: naturalna przerwa w rozmowie albo powrót do domu. Bez alarmowych powiadomień.

> „Mam krótki błysk: bardziej widzę odpowiedź przed piątkiem niż dalszą ciszę. Zapiszę to — potem uczciwie sprawdzimy.”

Obok dyskretna karta: zdarzenie, termin, podstawa, poziom pewności, historia rozstrzygnięcia. Liczba tylko po przejściu bramki kalibracji.

Ponowne pytanie nie uruchamia nowego losowania. Aktualizacja wyłącznie po **nowym sprawdzalnym fakcie**, z zachowaniem poprzedniej wersji.

## 5. Sprawdzanie i uczenie

Prognoza zostaje niezmiennie zapisana **przed ujawnieniem**. Bez późniejszej zmiany sensu.

- Logi i rejestry: automatyczne rozstrzygnięcie.
- Dane deklarowane: jedna nieinwazyjna karta „spełniło się / nie / nie wiem / pomiń”.
- Zdrowie: dobrowolne rozliczenie, bez dopytywania o szczegóły.
- Brak informacji: `unknown`, nigdy automatyczna porażka ani sukces.

Menma po trafieniu:

> „Tym razem zobaczyłam dobrze.”

Po pudle:

> „Nie sprawdziło się. Nie będę dopasowywać znaczenia po fakcie.”

Raport obejmuje trafienia, pudła, brakujące wyniki i odsetek rozstrzygnięć. Pomijane wyniki mogą zniekształcać ocenę.

## 6. Główne blokady ryzyka

- **Zdrowie:** żadnych wskazówek dotyczących dawek, odstawiania leków ani decyzji o konsultacji. Prognoza nie uzasadnia takich działań.
- **Prywatność:** także osobna zgoda na wykorzystywanie rozmów Astra solo w pokoju sióstr.
- **Nakłanianie:** żadnego „zrób to, żeby wizja się spełniła”.
- **Nakręcanie:** brak przycisku „przelicz ponownie”, niezmienna prognoza, łatwe wyciszenie kategorii.
- **Pozorna wszechwiedza:** jawna informacja, że to prognozowanie z danych w fikcyjnej oprawie.
- **Siostry:** Holo może wyjaśnić podstawę; Nazuna zakwestionować interpretację. Żadna nie podbija pewności ani nie reinterpretowuje pudła.

## 7. MVP i wersja docelowa

**Jeden wieczór:** flaga, SQLite, import rejestru, jeden typ: „odpowiedź do siódmego dnia od wysłania”, prognozowany przy wysyłce. Prosty model na pełnych oknach, zapis przed wynikiem, karta rozliczenia, tryb Amnezja. Przy sześciu aplikacjach prawdopodobnie **shadow mode**, nie pokaz liczb.

Dodać jeden prompt głosu Menmy i deterministyczne blokady prywatności. Bez debaty modeli.

**Docelowo:** modele czasu do zdarzenia, wersjonowane źródła bazowe, kalibracja domenowa, audyt selekcji oraz eksperyment z ujawnianiem prognoz.

## 8. Trudne miejsca — odpowiedzi wprost

1. **Mało danych:** prior z odpowiedniego źródła, szeroka niepewność, możliwość odmowy. Nie istnieje uczciwy skrót.
2. **Pewniaki:** oceniaj poprawę Brier score względem bazy. Oddzielnie oceniaj ważność i nieoczywistość; nie premiuj samej ekstremalnej liczby.
3. **Samospełnianie:** oznaczaj podatność. Za zgodą losuj ujawnienie części prognoz; porównuj z wcześniej zapisanymi, nieujawnionymi. Oddzielaj przewidywanie od wpływu.
4. **Ciągłe sprawdzanie:** jedna wersja do nowego faktu, bez odświeżania emocjami.
5. **Reszta domu:** charakter i komentarz, nie teatr jednomyślności.
6. **Weryfikacja:** automatyczna, gdy możliwa; inaczej jedno dobrowolne kliknięcie.
7. **Zachwyt:** sporadyczne „czy to było niezwykłe?”, plus pomocność, zaufanie i napięcie. Sukces: zachwyt rośnie, przymus sprawdzania nie.

## SPECYFIKACJA

### Zapis jednej przepowiedni

```json
{
  "id": "uuid",
  "wersja": 1,
  "utworzono": "ISO8601",
  "domena": "rekrutacja",
  "zgoda": "rekrutacje:v1",
  "cel": {
    "podmiot_id": "aplikacja_42",
    "zdarzenie": "pierwsza_odpowiedz",
    "termin": "ISO8601",
    "regula": "data_odpowiedzi <= termin"
  },
  "dowody": ["dozwolony_snapshot_id"],
  "model_wersja": "forecast-v1",
  "zrodlo_bazowe": null,
  "p_surowe": null,
  "p_kalibrowane": null,
  "przedzial_niepewnosci_modelu": null,
  "p_bazowe": null,
  "kalibracja_id": null,
  "podatna_na_wplyw": true,
  "status": "shadow",
  "ujawniono": null,
  "tekst": null,
  "wynik": {
    "wartosc": null,
    "zrodlo": null,
    "sprawdzono": null
  }
}
```

### Algorytm

Uprawnienia → oczyszczony snapshot → mierzalni kandydaci → kontrola danych i bezpieczeństwa → model bazowy → prognoza i niepewność → audyt → bramka kalibracji → wybór według ważności i jakości → niezmienny zapis → głos Menmy → rozstrzygnięcie → ocena poza próbą.

Rejestruj także kandydatów i powody odrzucenia: selekcja „najciekawszych” również może psuć kalibrację.

### Prompt głosu

> Jesteś ciepłą, dorosłą Menmą. Otrzymujesz zatwierdzoną prognozę, nie tworzysz nowej. W 1–2 zdaniach nazwij bardziej prawdopodobne zdarzenie i termin. „Błysk” jest metaforą. Nie dodawaj szczegółów, liczb ani pewności. Nie sugeruj działań zdrowotnych. Nie obiecuj wyniku. Gdy podstawa jest słaba, powiedz to łagodnie. Nie produkuj wizji z braku danych.