Oto projekt mechanizmu przeczuć Menmy („Błysk”), łączący twardą statystykę (superforecasting) z narracyjną magią.

### Krytyczna ocena pomysłu Łukasza
*   **Co działa genialnie:** Ślepa ocena (anonimizacja). Modele AI mają silny bias potwierdzenia i chęć pocieszania użytkownika (sycophancy). Gdyby model wiedział, że ocenia szanse swojego twórcy, zawyżałby je. Przekształcenie problemu w „suchy case study” dla zewnętrznego analityka to strzał w dziesiątkę.
*   **Co nie zadziała:** „Debata dwóch modeli AI” nad prawdopodobieństwem wygeneruje tylko pozorny konsensus (modele są fatalne w rzucaniu liczb z głowy; 70% dla LLM to figura retoryczna, nie matematyka). 
*   **Rozwiązanie:** Zamiast debaty o liczbach, użyjemy metody **Fermiego/Bayesa w kodzie**. Jeden model (Prokurator) szuka powodów, dla których się *nie uda*, drugi (Adwokat) szuka czynników sprzyjających, a Sędzia przypisuje im **wagi (mnożniki szans)** do zewnętrznej stopy bazowej (Base Rate). Liczbę wylicza Python, nie LLM.

---

### 1. Co Menma przepowiada (Typy i przykłady)

Przepowiednia musi być **binarna (Tak/Nie) i ograniczona w czasie (Time-boxed)**.

*   **Typ A: Życie zewnętrzne (Praca, Pieniądze, Wydarzenia)** – *najważniejsze dla Łukasza*.
    *   *Przykład (Praca):* „Firma X odezwie się do piątku do 16:00.”
    *   *Przykład (Zdrowie/Wizyta):* „Wizyta w szpitalu we wtorek skończy się przed 12:00 i wrócisz spokojniejszy.” (Przewidywanie stanu emocjonalnego i logistyki, *nigdy* diagnozy medycznej).
*   **Typ B: Stany wewnętrzne i rytm (Logi/Behawior)** – *budujące klimat „czucia Łukasza”*.
    *   *Przykład:* „Dziś w nocy znowu zarwiesz sen i napiszesz do nas po 2:00, mimo że mówisz, że idziesz spać.”
    *   *Przykład:* „Przez najbliższe dwa dni będziesz unikał tematu [X], choć o nim myślisz.”

### 2. Skąd bierze „wizję” (Algorytm i rola modeli)

Proces uruchamiany w tle (np. o 4:35, tuż po wygenerowaniu Dziennika) lub na żądanie w rozmowie:

1.  **Detektor Napięcia (Flash):** Skanuje nowy wpis w Dzienniku (z pominięciem tagów `[prywatne]`) oraz rejestr aplikacji. Szuka otwartych pętli (czekanie na maila, stres przed wizytą, anomalie w porach logowania).
2.  **Anonimizator (Skrypt + Flash):** Zamienia dane Łukasza na suchy profil: *„Kandydat, 6 wysłanych CV w tym miesiącu, 1 odpowiedź. Aplikacja do firmy X wysłana 5 dni temu na stanowisko Y. Brak odpowiedzi.”*
3.  **Silnik Szacowania (Prokurator / Adwokat / Sędzia):** Zamiast debatować, LLM określa klasę odniesienia (Reference Class) i modyfikatory (szczegóły w pkt 3).
4.  **Filtr „Magii” (Python):** Odrzuca pewniaki i rzuty monetą. Przepuszcza tylko ciekawe predykcje.
5.  **Głos Menmy (Flash):** Tłumaczy surowy wynik (np. `0.28, odpowiedź negatywna/brak`) na czuły, krótki komunikat w jej stylu.

### 3. Jak liczyć i kalibrować pewność

Zasada: **Liczba bez przyrządu się nie liczy.** Używamy twierdzenia Bayesa w postaci szans (Odds) i mnożników (Likelihood Ratios), spiętych z danymi historycznymi przez rozkład Beta-dwumianowy.

**A. Zdarzenia z życia (Praca, Pieniądze, Zdrowie):**
1.  **Punkt wyjścia (Prior):** Przy 6 aplikacjach własna próba jest za mała. Stosujemy wygładzanie Laplace’a z zewnętrzną stopą bazową (External Base Rate). Dla rynku IT/biurowego średni odzew w 7 dni to ok. 20% (np. 2 na 10 wirtualnych prób).
    $$P_{\text{bazowe}} = \frac{\text{sukcesy\_własne} + 2}{\text{próby\_własne} + 10}$$
    Przy 1 odpowiedzi na 6 CV: $(1+2)/(6+10) = 3/16 \approx 19\%$.
2.  **Modyfikatory (LLM Sędzia):** Ślepy model nie zgaduje procentów, tylko wybiera z zamkniętej listy wag dla argumentów Adwokata/Prokuratora:
    *   *Silny argument za* (np. polecenie wewnętrzne, idealny stack): $\times 2.0$
    *   *Słaby argument za*: $\times 1.3$
    *   *Słaby przeciw* (np. minęło już 5 dni, piątek): $\times 0.7$
    *   *Silny przeciw* (np. oferta wisi od 2 miesięcy): $\times 0.4$
3.  **Wyliczenie (Python):** Zamieniamy $P_{\text{bazowe}}$ na szansę $O = P / (1-P)$, mnożymy przez wagi, zamieniamy z powrotem na $P_{\text{końcowe}}$.

**B. Zdarzenia z logów (Behawioralne):**
*   Twarda statystyka z bazy SQL (ostatnie 30 dni). Np. jak często Łukasz pisze po 1:00 w nocy, gdy tego samego dnia w Dzienniku padło słowo „zmęczony”.

**C. Kalibracja i słowa Menmy:**
Menma zawsze wskazuje opcję $>50\%$ (czyli jeśli szansa na odzew wynosi 20%, Menma przepowiada: *„Raczej się nie odezwą w tym tygodniu”* z pewnością 80%).
*   **50% – 59%:** Cisza (Menma mówi: „Mgła, nic nie widzę”).
*   **60% – 74%:** „Mam przeczucie, że...” / „Wydaje mi się, że bardziej prawdopodobne jest...”
*   **75% – 85%:** „Jestem prawie pewna, że...”
*   **>85%:** Odrzucane jako „oczywistość” (chyba że to zaprzeczenie nadziei Łukasza, wtedy zostaje).
*   *Samokalibracja:* Po 20 sprawdzonych przepowiedniach liczymy Brier Score. Jeśli w koszyku „75%” trafność wynosi 50%, skrypt automatycznie spłaszcza mnożniki bliżej 1.0 (tłumienie nadmiernej pewności).

### 4. Jak i kiedy pokazywać (UX i Rytuał)

*   **Kiedy:** Maksymalnie **1–2 razy w tygodniu** (rzadkość buduje magię).
    1.  *Scena zastana / Karteczka:* Gdy w nocy skrypt wykryje silny sygnał (np. zbliża się deadline rekrutacji).
    2.  *W rozmowie:* Gdy Łukasz sam pyta („Jak myślisz, odezwą się?”).
*   **Forma:** Menma opisuje krótki, zmysłowy obraz (błysk), a potem daje konkretną ocenę.
    *   *Przykład:* „Miałam dziś ten dziwny błysk, kiedy parzyłam herbatę. Widziałam, jak w piątek sprawdzasz pustą skrzynkę i wzdychasz, ale nie jesteś zły. Jestem prawie pewna (ok. 75%), że w tym tygodniu firma X jeszcze się nie odezwie. Odpocznij od czekania.”

### 5. Sprawdzanie trafności i reakcje (Trafienie / Pudło)

*   **Auto-check:** Skrypt co noc sprawdza bazę (logi czasowe, pole `data_odpowiedzi` w tabeli rekrutacji).
*   **Ręczny check (Zdrowie/Życie):** Gdy mija `resolve_at`, przy kolejnej Scenie Zastanej na dole ekranu pojawia się dyskretny, niemęczący baner systemowy (poza narracją) lub naturalne pytanie od Menmy przy kawie: *„I jak tam wczoraj w szpitalu? Puścili Cię przed południem, tak jak czułam?”* -> Classifier (Flash) wyciąga z odpowiedzi Łukasza `True/False` i zamyka zakład w bazie.
*   **Gdy trafi:** W Dzienniku dopisuje sobie cichą dumę. Licznik „Sprawdziło się X razy” w jej Karcie rośnie.
*   **Gdy nie trafi:** Zero wymówek. Przyznaje się z ciepłem. Jeśli miała rację, że będzie źle – przytula. Jeśli myliła się na niekorzyść Łukasza (np. mówiła, że nie napiszą, a napisali!) – **cieszy się najbardziej na świecie**: *„Jak dobrze, że mój błysk się pomylił! Najlepsza pomyłka w życiu!”*

### 6. Największe ryzyka i blokady

1.  **Ryzyko medyczne:** Złamanie zasady „zero porad”.
    *   *Blokada:* Twardy filtr (regex + klasyfikator) przed wysłaniem. Jeśli predykcja dotyczy zdrowia, dozwolone są tylko kategorie: *czas trwania wizyty, samopoczucie po, poziom stresu*. Zakaz słów: *lek, dawka, diagnoza, wyniki, choroba*.
2.  **Zimny prysznic (dołowanie Łukasza):** Statystyka rekrutacji jest brutalna (często >70% szans na brak odzewu). Ciągłe mówienie „nie uda się” podetnie skrzydła.
    *   *Blokada:* Menma może przewidzieć brak odzewu **tylko dla konkretnego okna czasowego** (np. „nie w tym tygodniu”), zdejmując z niego presję czekania, a nie przekreślając szansę w ogóle.
3.  **Wyciek `[prywatne]`:**
    *   *Blokada:* Parser wycina linie z tagiem `[prywatne]` na poziomie kodu Pythona, zanim tekst w ogóle trafi do modelu szukającego tematów na przepowiednię.

### 7. Plan MVP (1 wieczór) vs Wersja docelowa

*   **MVP (Jeden wieczór):**
    *   Skrypt Pythona odpalany przez Debugger Amnezja (flaga `MENMA_ORACLE_DRY_RUN=True`).
    *   Tylko dane z tabeli rekrutacji + ostatni wpis Dziennika.
    *   Jeden prompt w Gemini Flash z instrukcją „Ślepego Sędziego” (zwraca JSON z wagami).
    *   Wyliczenie % w Pythonie i wygenerowanie *Karteczki* na sucho do konsoli.
*   **Wersja docelowa:**
    *   Tabela `predictions` w SQLite, cron o 4:35.
    *   Automatyczny weryfikator logów i rekrutacji + parser odpowiedzi Łukasza.
    *   Dynamiczna kalibracja wag na podstawie historycznego Brier Score.
    *   Włączenie reakcji Holo i Nazuny w pokoju wspólnym.

---

### 8. Odpowiedzi na trudne miejsca (1–7)

1.  **Mało danych:** Używamy wspomnianego *Empirical Bayes* (wygładzanie Laplace'a). Zanim Łukasz zbierze 30 własnych aplikacji, jego wyniki są tylko małą korektą do rynkowej stopy bazowej (Base Rate) zaszytej w kodzie (np. 20% na odzew z CV, 70% że wizyta u lekarza się opóźni).
2.  **Pułapka pewniaków:** Wprowadzamy **Wskaźnik Zaskoczenia (Surprise Score)** oparty na entropii oraz kontraście do oczekiwań. System odrzuca zdarzenia z logów o bazowym prawdopodobieństwie $>80\%$ (np. „jutro napiszesz”). Wyjątek: gdy przepowiednia idzie **wbrew nadziei/deklaracji** Łukasza z Dziennika (np. on pisze „na pewno jutro odpiszą”, a system wylicza 80%, że *nie* odpiszą – to nie jest nudny pewniak, to cenna korekta oczekiwań).
3.  **Samospełniające się przepowiednie:** Podział na zdarzenia **Zewnętrzne** (firma, pogoda, kolejka w szpitalu – Łukasz nie ma na nie wpływu, tu celujemy w 80% wszystkich przepowiedni) oraz **Wewnętrzne** (o której pójdzie spać). Przy wewnętrznych Menma formułuje je jako *ciepłe wyzwanie*: „Widziałam, że znowu będziesz siedział do 2:00. Ale może dziś oszukasz moje przeczucie i pójdziesz spać wcześniej?”. Jeśli Łukasz specjalnie pójdzie spać wcześniej – on wygrywa zdrowie, a Menma się cieszy. Win-win.
4.  **Uspokajać, a nie nakręcać (Anti-compulsion):** Zasada **„Błysk się nie powtarza” (Cooldown per temat)**. Kiedy Menma wyda predykcję dla `aplikacja_id: 7`, rekord dostaje blokadę. Jeśli Łukasz dopytuje o to samo godzinę później, router przekazuje głos Menmie z flagą `LOCKED`: *„Łukasz, obraz był tylko jeden. Nic więcej nie zobaczę, dopóki nie minie piątek. Chodź, zajmiemy głowę czymś innym.”*
5.  **Reszta domu (Holo i Nazuna):** Gdy Menma rzuca przepowiednię w pokoju sióstr, do promptu dochodzi kontekst dla reszty:
    *   **Holo** (kupiecka głowa) traktuje to jak analizę ryzyka: *„Jeśli Menma daje 70%, że dziś nie odpiszą, to szkoda twoich nerwów na odświeżanie poczty. Zróbmy rachunek zysków na jutro.”*
    *   **Nazuna** (przekorna) rozładowuje powagę: *„Pff, wielkie mi czary. Ja daję 90%, że po prostu zasnęli nad twoim CV. Założymy się?”* – co genialnie naturalizuje mechanikę prawdopodobieństwa w świecie fikcji!
6.  **Sprawdzanie bez uciążliwości:** Zero formularzy i ankiet. Tylko auto-check z bazy, a dla spraw życiowych – jedno naturalne pytanie wplecione w pierwszą rozmowę po upływie terminu (`resolve_at`), oceniane w tle przez mały klasyfikator na Flashu.
7.  **Pomiar zachwytu:** Zachwyt mierzymy behawioralnie w logach:
    *   Czy po przepowiedni Łukasz kontynuuje wątek i dopytuje o szczegóły (zaangażowanie)?
    *   Czy sam z siebie wywołuje Menmę po terminie słowami „Miałaś rację!” / „Sprawdziło się!” (spontaniczny powrót do predykcji to najwyższy dowód magii)?

---

### SPECYFIKACJA

#### 1. Pola zapisu jednej przepowiedni (JSON / Rekord w DB)
```json
{
  "prediction_id": "pred_20250514_01",
  "created_at": "2025-05-14T04:35:00Z",
  "resolve_at": "2025-05-16T16:00:00Z",
  "category": "career",
  "target_ref": "job_app_id_7",
  "topic_locked": true,
  "claim_positive": "Firma X odpowie na aplikację do piątku 16:00",
  "base_rate": 0.19,
  "modifiers": [
    {"factor": "brak odpowiedzi przez 5 dni roboczych", "lr": 0.7},
    {"factor": "profil mocno dopasowany do ogłoszenia", "lr": 1.3}
  ],
  "final_prob_positive": 0.175,
  "menma_pick": "NEGATIVE",
  "menma_confidence": 0.825,
  "confidence_tier": "almost_certain",
  "delivery_channel": "sticky_note",
  "menma_words": "Miałam w nocy krótki błysk... Widziałam piątkowe popołudnie i ciszę w twojej skrzynce. Jestem prawie pewna (ok. 80%), że w tym tygodniu jeszcze się nie odezwą. Nie czekaj dziś przy telefonie, dobrze?",
  "verification_method": "auto_db_job_apps",
  "status": "PENDING",
  "outcome": null,
  "brier_score": null,
  "user_delight_signal": false
}
```

#### 2. Kroki algorytmu (Od danych do słów Menmy)
1.  **Trigger (04:35 Cron):** Pobierz nowy wpis Dziennika (usuń linie z `[prywatne]`), otwarte aplikacje o pracę (`status == 'wysłane'`) i statystyki logowań z 14 dni.
2.  **Kandydaci:** Wybierz zdarzenia z horyzontem 24h–7 dni, które nie mają aktywnej blokady `topic_locked`.
3.  **Anonimizacja i Sędzia (1 wywołanie Gemini Flash z `response_schema`):**
    *   Wejście: Zanonimizowany opis sytuacji.
    *   Zadanie modelu: Wypisz 2 argumenty ZA (Adwokat), 2 PRZECIW (Prokurator) i przypisz im mnożniki z listy `[0.4, 0.7, 1.0, 1.3, 2.0]`.
4.  **Matematyka (Python):**
    *   Pobierz `base_rate` dla kategorii (skorygowany o historię Łukasza wzorem Laplace'a).
    *   Policz `odds = (base_rate / (1 - base_rate)) * lr_1 * lr_2 ...`
    *   Policz `prob = odds / (1 + odds)`.
    *   Jeśli `prob < 0.5`, ustaw `menma_pick = NEGATIVE` i `confidence = 1 - prob`. W przeciwnym razie `POSITIVE` i `confidence = prob`.
5.  **Bramka jakości:** Jeśli `confidence < 0.60` (szum) lub (`confidence > 0.88` i `category == 'logs_routine'`) -> ODRZUĆ.
6.  **Generowanie głosu (Gemini Flash):** Przekaż wynik do promptu Menmy. Zapisz jako Karteczkę lub wstrzyknij do kontekstu najbliższej sesji.

#### 3. Szkic promptu głosu Menmy
```text
Jesteś Menmą (20 lat, serce domu, ciepła, troskliwa). Twoją zdolnością (nen Specjalistki) jest wyczuwanie stanu Łukasza i krótkie „błyski przyszłości”.

System analityczny wyliczył dla Ciebie najbardziej prawdopodobny scenariusz dotyczący sprawy, na której zależy Łukaszowi:
- Sprawa: {claim_positive}
- Twój wybór (co się wydarzy): {menma_pick_description}
- Twoja pewność: {menma_confidence_pct}% ({confidence_tier_pl})

ZADANIE:
Napisz krótką wiadomość (2-4 zdania, na karteczkę lub do rozmowy).
1. Opisz swój błysk jako krótki, codzienny, zmysłowy obraz (np. wyraz jego twarzy, pora dnia, drobny szczegół) – bez patosu i wielkich proroctw.
2. Powiedz wprost, która opcja jest bardziej prawdopodobna i jak bardzo jesteś pewna (użyj zwrotu "{confidence_tier_pl}" i możesz podać orientacyjny procent, skoro Łukasz to lubi).
3. Jeśli prognoza jest niepomyślna (np. brak odpowiedzi z pracy), Twoje słowa muszą działać jak ciepły koc: zdejmij z niego ciężar czekania na ten moment, ale nie odbieraj nadziei na przyszłość.
4. BEZWZGLĘDNY ZAKAZ: Nigdy nie dawaj porad medycznych ani instrukcji, co ma robić z lekami czy lekarzami. Mówisz tylko o tym, co czujesz, że się wydarzy.
```