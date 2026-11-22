## Zarzuty — decyzje i zmiany

1. **Przyjmuję.** Bramka kalibracji blokowała całą funkcję zamiast tylko nieuzasadnionych deklaracji pewności; rozdzielam publikowanie jawnie eksperymentalnych przeczuć od prawa do podawania procentów.

2. **Przyjmuję.** Zaproponowane kwestie Menmy brzmiały administracyjnie; przenoszę rozliczenia do osobnego archiwum, a jej wypowiedzi piszę od nowa, zachowując naturalne sygnały niepewności.

3. **Przyjmuję.** Nie wskazałem dostępnych, odpowiednich danych populacyjnych; usuwam je jako zależność MVP i nie zastępuję wymyślonym priorem ani opinią LLM.

4. **Odrzucam.** Weryfikowalność nie wymusza banalności, choć moje przykłady były zbyt logistyczne; dodaję przewidywania tematów rozmów, deklarowanych odczuć i nowych zdarzeń, nadal z jednoznacznym kryterium rozstrzygnięcia.

5. **Odrzucam.** Eksperymenty N-of-1 nie są metodologicznym absurdem, ale przy tej częstotliwości nie dadzą tutaj użytecznej odpowiedzi; usuwam losowe ukrywanie wizji, zachowując oznaczenie możliwego wpływu na zachowanie.

## Warunki recenzenta

1. **Odrzucam gwarancję.** Sama liczba wiadomości nie zapewnia informacji prognostycznej, więc pierwszego wieczoru udostępniam tryb roboczych przeczuć, ale nie obiecuję ani zachwytu, ani rzeczywistej przewagi predykcyjnej.

2. **Odrzucam.** Nie potrafię wskazać zweryfikowanej darmowej bazy czasów odpowiedzi polskich rekruterów, a [API NFZ](https://api.nfz.gov.pl/app-itl-api/) opisuje kolejki, nie indywidualny przebieg leczenia; ograniczam zakres zamiast pozorować dostępność danych.

3. **Odrzucam.** Cicha interpretacja dzienników nie wystarcza do rzetelnego rozliczania niejednoznacznych zdarzeń; usuwam formularze z rozmowy, lecz zachowuję `unknown`, dobrowolne potwierdzenia i dostępne poza sceną archiwum.

## Zimny start: co rzeczywiście dostaje Łukasz

Dwa tryby:

- **Przeczucie robocze:** kierunkowa hipoteza oparta na wskazanych przesłankach, bez procentu i bez twierdzenia o potwierdzonej skuteczności.
- **Prognoza zwalidowana:** estymacja z opisanym modelem, porównaniem z bazą i sprawdzoną kalibracją.

Przykład **warunkowy**, nie rzekomy odczyt nieudostępnionych logów: jeśli Łukasz kilkakrotnie spontanicznie wracał do porzuconego projektu i ostatnio pojawił się nowy impuls:

> „Mam nieśmiały błysk: zanim miną dwa dni, sam wrócisz tutaj do projektu X.”

Wewnętrzne kryterium: samodzielne rozpoczęcie rozmowy o X w ciągu 48 godzin. To prognoza podatna na wpływ ujawnienia, nie dowód czytania przyszłości.

**Nazwanie czegoś „przeczuciem” nie naprawia braku danych.** Przy braku sensownych przesłanek wizja nie powstaje; szczególnie nie wymuszamy jej dla rekrutacji lub zdrowia.

MVP obejmuje rozmowy oraz rekrutacje z kompletnym rejestrem. Pieniądze wymagają historii konkretnego procesu. Zdrowie: wyłącznie uzasadnione przewidywania logistyczne; żadnego diagnozowania wypalenia z długości wiadomości ani prognoz choroby bez zwalidowanego narzędzia.

## SPECYFIKACJA

### Zapis przepowiedni

```json
{
  "id": "uuid",
  "wersja": 1,
  "poprzednia_wersja": null,
  "utworzono": "ISO8601",
  "stan_danych_na": "ISO8601",
  "domena": "rozmowa",
  "zgoda_id": "zakres:v1",
  "cel": {
    "zdarzenie": "Lukasz sam rozpocznie rozmowe o X",
    "termin": "ISO8601",
    "regula": "jawna wzmianka inicjujaca temat X",
    "weryfikator": "logi"
  },
  "dowody": ["dozwolony_snapshot_id"],
  "zalozenia": [],
  "model_wersja": "v1",
  "polityka_selekcji": "v1",
  "pewnosc": {
    "tryb": "roboczy",
    "p_modelowe": null,
    "p_kalibrowane": null,
    "p_bazowe": null,
    "niepewnosc_id": null,
    "kalibracja_id": null
  },
  "podatnosc_na_wplyw": "mozliwa",
  "ujawniono": null,
  "tekst": null,
  "wynik": {
    "wartosc": "unknown",
    "dowody": [],
    "rozstrzygnieto": null
  }
}
```

`p_*` oznacza prawdopodobieństwo zapisanego zdarzenia, nie „siłę intuicji”. Ujawnione wersje są niezmienne; korekta tworzy nową wersję.

### Algorytm

1. **Uprawnienia:** odetnij `[prywatne]` i pochodne; przy niejasnym zakresie oznaczenia pomiń cały wpis. Astra solo wymaga osobnej zgody.
2. **Snapshot:** połącz dozwolone dane, usuwając duplikaty między logami, kartami i dziennikiem.
3. **Kandydaci:** jeden krótki przebieg Flash proponuje maksymalnie trzy zdarzenia wraz z przesłankami, terminem i falsyfikatorem; nie wycenia własnej pewności.
4. **Estymacja:** przy odpowiednich danych użyj prostego modelu statystycznego; bez nich dopuszczaj wyłącznie wyraźnie roboczą hipotezę albo odmowę. Sześć niejednakowo obserwowanych aplikacji nie stanowi gotowego mianownika.
5. **Wybór:** wyklucz przypomnienia znanych terminów i zdarzenia bez znaczenia; oceniaj osobno jakość predykcji, ważność oraz nieoczywistość, bez premiowania ekstremalnych deklaracji.
6. **Publikacja:** zapisz przed pokazaniem, nadaj głos Menmy, sprawdź zgodność tekstu z rekordem; maksymalnie dwie wizje tygodniowo, bez obowiązku wykorzystania limitu.
7. **Rozliczenie:** automatycznie z wiarygodnych logów/rejestrów; analiza wypowiedzi może wskazać jawne potwierdzenie, ale brak wzmianki oznacza `unknown`, nie pudło.
8. **Ocena:** rozdzielaj rodziny zdarzeń, horyzonty i podatność na wpływ; dla liczbowych prognoz sprawdzaj kalibrację oraz Brier względem bazy, uwzględniając selekcję publikowanych wizji.

„Prawie pewna” pozostaje zablokowane w MVP; później wymaga co najmniej 95% i odpowiedniej walidacji. **70% nie wystarcza.**

### Szkic promptu Menmy

> Jesteś ciepłą, dorosłą Menmą. Ubierz zatwierdzoną prognozę w 1–2 naturalne zdania. Nie dodawaj szczegółów, procentów, przyczyn ani pewności. Zachowaj podany stopień niepewności. Nie sugeruj działań zdrowotnych. Po pudle możesz powiedzieć: „Ten błysk mnie zmylił” — bez wymówek i reinterpretacji.

## Plan MVP — jeden wieczór

- Flaga funkcji, SQLite, oczyszczony snapshot, jeden szablon rozmowny i import CSV rekrutacji.
- Reguły bezpieczeństwa, niezmienny zapis, publikacja roboczych przeczuć i test Amnezją bez zapisu.
- Maksymalnie jedno krótkie wywołanie generujące dziennie, z limitem tokenów i kosztu; bez debaty modeli.
- Kolejne pytanie zwraca tę samą prognozę; aktualizacja tylko po nowym sprawdzalnym fakcie.
- Archiwum poza sceną: trafienia, pudła, niewiadome i podstawa. Holo wyjaśnia metodę na życzenie; Nazuna nie podbija pewności.
- Raz w tygodniu opcjonalne pytanie o zachwyt i napięcie; bez poprawy doświadczenia nie dokładamy złożoności.