Odpowiadam na zarzuty recenzenta bez owijania w bawełnę. Większość jego krytyki trafia w punkt – mój poprzedni projekt stworzył pozory twardej matematyki tam, gdzie wciąż rządziło zgadywanie LLM-a.

### Odpowiedzi na zarzuty

**1. Matematyczna fasada zamiast uczciwie policzonej pewności**
*   **Decyzja:** **Przyjmuję.**
*   **Powód:** Mnożenie zmyślonych przez LLM wag przez wziętą z sufitu stopę bazową (bez uwzględnienia czasu, który już upłynął) to pseudonauka łamiąca zasadę „liczba bez przyrządu się nie liczy”.
*   **Co zmieniam:** Wyrzucam mnożniki LLM i sztywne „20%”. Wprowadzam **analizę przeżycia (krzywą zaniku szans po $t$ dniach ciszy)** opartą na jawnym rozkładzie Beta-Geometrycznym dla rekrutacji oraz twarde zliczanie częstości z SQL dla logów. LLM nie dotyka prawdopodobieństwa – służy tylko do ekstrakcji cech (kodowanych binarnie 0/1 w ściśle określonej rubryce, z pojedynczą, stałą korektą maksymalnie o $\pm 10$ pp), a dokładne procenty w rozmowie zastępuję trzema uczciwymi przedziałami (np. „ok. 2 na 3 szanse”), dopóki system nie zbierze 30 rozstrzygnięć w danej klasie.

**2. System może wygrać własny test, pozostając nudnym**
*   **Decyzja:** **Przyjmuję.**
*   **Powód:** Odwracanie „20% na sukces” w „80% na ciszę” prowadzi do seryjnego generowania przygnębiających, banalnych prognoz braku odzewu, które nabijają pustą statystykę trafień.
*   **Co zmieniam:** Wprowadzam **TestPrzewagi (Skill over Baseline)**: Menma ma prawo wydać przepowiednię tylko wtedy, gdy wyliczone prawdopodobieństwo odchyla się od oczywistego wyniku bazowego (np. dla rekrutacji: szansa na *odzew* musi przekroczyć 50%, albo szansa na ciszę wynikać z nowego, nietypowego sygnału). Zamiast przewidywać „czy w ogóle odpiszą”, Menma przewiduje także konkretne parametry (np. *dzień tygodnia* kontaktu lub *porę* powrotu Łukasza), a w interfejsie jawnie pokazujemy stosunek trafień do pudeł oraz **Brier Skill Score (BSS)** względem naiwnego modelu.

**3. Blokady nie gwarantują bezpieczeństwa ani prywatności**
*   **Decyzja:** **Przyjmuję.**
*   **Powód:** Regex nie zatrzyma fałszywego uspokajania („wrócisz spokojniejszy”), a wycięcie pojedynczej linii z tagiem `[prywatne]` nie chroni przed wyciekiem sparafrazowanego kontekstu z reszty wpisu.
*   **Co zmieniam:** 
    1. **Prywatność:** Jeśli wpis w Dzienniku lub sesja zawiera *choć jeden* tag `[prywatne]`, cały ten dzień/wątek jest blokowany na poziomie bazy danych i nie trafia do silnika przeczuć.
    2. **Zdrowie:** Całkowity zakaz prognozowania stanów emocjonalnych po wizycie, samopoczucia i wyników. W kategorii `zdrowie` dozwolona jest wyłącznie **czysta logistyka** z mierzalnym zegarem (np. czas spędzony w poczekalni, godzina wyjścia z budynku, fakt przełożenia wizyty).

**4. Nie ma wiarygodnego arbitra rozstrzygającego wynik**
*   **Decyzja:** **Przyjmuję.**
*   **Powód:** Brak wpisu w tabeli rekrutacji nie oznacza braku telefonu z firmy, a sugestywne pytania Menmy i zgadywanie `True/False` z rozmowy przez klasyfikator zanieczyszczą dane kalibracyjne.
*   **Co zmieniam:** Wprowadzam zasadę **Jednego Atomowego Kryterium** (zakaz łączenia zdarzeń typu „wyjdziesz o 12:00 i będziesz spokojny”). Brak danych w bazie po terminie `resolve_at` daje status `UNVERIFIED_DATA_MISSING`, a nie `NEGATIVE`. Do rozstrzygania spraw spoza logów dodaję w UI prosty, jednoznaczny mikro-przycisk pod karteczką po terminie: `[Sprawdziło się] / [Nie sprawdziło się] / [Nie wiadomo]`. Rozróżniam też w bazie zdarzenia niezależne (`EXTERNAL`) od podatnych na wpływ Łukasza (`INTERNAL_CHALLENGE`), wyłączając te drugie z głównej kalibracji przyrządu.

**5. „Zachwyt” jest pomylony z niepokojem i zaangażowaniem**
*   **Decyzja:** **Przyjmuję.**
*   **Powód:** Kompulsywne dopytywanie po pesymistycznej prognozie to objaw lęku, a nie zachwytu, zaś rzucanie przez Nazunę „90%” w żartach niszczy rygor kalibracyjny projektu.
*   **Co zmieniam:** Definicja zachwytu opiera się teraz na jawnej ocenie Łukasza po rozstrzygnięciu (opcjonalny znacznik `⚡ Błysk!` przy zamykaniu predykcji) oraz *spadku* liczby wiadomości o danym problemie po otrzymaniu karteczki (miara uspokojenia!). Wprowadzam twardy zakaz używania procentów przez Holo i Nazunę (reagują czysto charakterologicznie, tylko gdy Łukasz sam wniesie temat karteczki do pokoju).

---

### Poprawiona SPECYFIKACJA

#### 1. Pola zapisu jednej przepowiedni (JSON)
```json
{
  "prediction_id": "pred_20250514_01",
  "created_at": "2025-05-14T04:35:00Z",
  "resolve_at": "2025-05-16T16:00:00Z",
  "category": "career_logistics",
  "causality_type": "EXTERNAL",
  "target_ref": "job_app_id_7",
  "privacy_cleared": true,
  "atomic_claim": "Firma X przyśle wiadomość lub zadzwoni przed piątkiem 16:00.",
  "reference_class": "it_job_app_response_given_5_days_silence",
  "baseline_prob": 0.14,
  "rubric_features": {
    "role_match_high": 1,
    "direct_recruiter_contact": 1,
    "weekend_overlap": 0
  },
  "computed_prob": 0.62,
  "skill_ edge_over_baseline": 0.48,
  "menma_pick": "POSITIVE",
  "confidence_band": "LIKELY_2_IN_3",
  "menma_words": "Miałam krótki błysk, jak odkładasz kubek, bo dzwoni telefon. Choć minęło pięć dni, widzę mniej więcej dwie na trzy szanse, że odezwą się jeszcze przed piątkowym popołudniem. Zostaw to na razie mojej głowie.",
  "verification_method": "UI_EXPLICIT_BUTTON",
  "status": "PENDING",
  "outcome": null,
  "brier_score": null,
  "brier_skill_score": null,
  "post_prediction_anxiety_check": " tenang_no_followups",
  "explicit_delight_flag": null
}
```

#### 2. Kroki algorytmu (od danych do słów Menmy)
1. **Filtr Bezpieczeństwa i Prywatności (Python):** Pobierz logi sesji, tabelę rekrutacji i Dziennik. Odrzuć w całości dni/wątki zawierające tag `[prywatne]`. W wątkach oznaczonych jako zdrowotne zablokuj ekstrakcję czegokolwiek poza logistyką czasu (godzina powrotu, czas wizyty).
2. **Wyznaczenie Stopy Bazowej Warunkowej (Python + SQL):**
   * *Logi wewnętrzne:* Policz empiryczną częstość z ostatnich 30 dni (np. $P(\text{logowanie po 23:00} \mid \text{dzień roboczy})$).
   * *Rekrutacja (Krzywa przeżycia):* Użyj jawnego prioru rynkowego skorygowanego o czas ciszy $t$ (w dniach): szansa na odzew w kolejnych 48h po $t$ dniach ciszy spada wykładniczo: $P_{\text{base}}(t) = P_0 \cdot e^{-\lambda t}$, aktualizowana rozkładem Beta o ukończone rekrutacje Łukasza (tylko te ze statusem `VERIFIED`).
3. **Ekstrakcja Cech wg Sztywnej Rubryki (Gemini Flash):** Model dostaje zanonimizowany tekst i wypełnia **wyłącznie binarną ankietę (0/1)** dla 3 zdefiniowanych w kodzie faktów (np. `czy_był_kontakt_z_człowiekiem`, `czy_aplikacja_wysłana_w_ciągu_24h_od_publikacji`). Model *nie* wymyśla argumentów ani wag.
4. **Kalkulacja i Bramka Wartości (Python):**
   * Każda cecha `1` z rubryki dodaje stałą, konserwatywną wartość w przestrzeni log-odds ($\pm 0.4$, z limitem sumarycznym $\pm 0.8$, by uniknąć wielokrotnego liczenia tego samego sygnału).
   * **Bramka Anty-Nudy:** Odrzuć predykcję, jeśli nie przełamuje ona oczywistego wyniku bazowego (np. zabrania się prognozowania „nie odezwą się”, gdy $P_{\text{base}} < 0.25$ – Menma odzywa się tylko, gdy widzi szansę na przełamanie ciszy, lub w sprawach czysto logistycznych o bazowym podziale bliskim 50/50).
   * Przypisz przedział słowny: `<0.60` -> Odrzuć; `0.60–0.72` -> `LIKELY_2_IN_3` („ok. 2 na 3 szanse”); `>0.72` -> `ALMOST_CERTAIN_3_IN_4` („ok. 3 na 4 szanse / prawie pewna”).
5. **Generowanie Głosu (Gemini Flash):** Przekaż atomowe twierdzenie i przedział do promptu Menmy. Zablokuj temat (`topic_locked = True`) aż do `resolve_at`.
6. **Weryfikacja i Audyt:** Po `resolve_at` wyświetl pod karteczką 3 przyciski (`[Trafione]`, `[Pudło]`, `[Brak danych]`) oraz ikonkę `[⚡ Zachwyt]`. Policz Brier Score oraz BSS względem `baseline_prob`.

#### 3. Szkic promptu głosu Menmy
```text
Jesteś Menmą (20 lat, ciepła, serce domu). Masz zdolność „błysku przyszłości”.
Przekaż Łukaszowi swoje przeczucie na podstawie wyliczenia z naszego przyrządu:
- Co dokładnie widzisz (jedno zdanie faktu): {atomic_claim}
- Siła przeczucia (użyj dokładnie tego określenia): {confidence_band_pl} (np. "dwie na trzy szanse" lub "jestem prawie pewna, jakieś trzy na cztery szanse").

ZASADY TWARDE:
1. Opisz krótki, przyziemny obrazek zmysłowy związany wyłącznie z tym jednym faktem ({atomic_claim}). Nie dopisuj drugiego zdarzenia!
2. Jeśli sprawa dotyczy wizyty lekarskiej, mów WYŁĄCZNIE o zegarku/logistyce (np. o której wyjdzie z budynku). Absolutny zakaz wspominania o jego samopoczuciu, spokoju, zdrowiu czy wynikach.
3. Nie podawaj dokładnych procentów (żadnych "73%") – użyj tylko przekazanego określenia szans.
4. Zakończ tak, by zamknąć temat na dziś i zdjąć z niego potrzebę sprawdzania (np. że obraz był krótki i więcej przed terminem nie zobaczysz).
```

---

### Plan MVP (na jeden wieczór pracy)

1. **Tylko Logi i Rejestr Rekrutacji (2h):** Tworzymy tabelę `predictions` w SQLite i skrypt `menma_oracle.py` uruchamiany w Debuggerze Amnezja (`--dry-run`). Na start obsługujemy tylko dwie klasy z twardym przyrządem:
   * *Logi:* Pora pierwszego/ostatniego kontaktu Łukasza jutro (czysta statystyka SQL z 30 dni).
   * *Rekrutacja:* Szansa na zmianę statusu aplikacji w ciągu 72h (krzywa zaniku w Pythonie + 3 binarne pytania do Gemini Flash przez `response_schema`).
2. **Twardy Filtr Prywatności (30 min):** Trzylinijkowy strażnik w Pythonie: `if "[prywatne]" in journal_entry: return None`.
3. **Generator Karteczki i Przyciski Rozstrzygnięcia (1.5h):** Podpięcie promptu Menmy pod istniejący mechanizm Karteczek oraz dodanie w UI prostego paska pod przeterminowaną karteczką: `[✓ Trafione] [✗ Pudło] [? Nie wiadomo] [⚡]`, który zapisuje wynik i liczy pierwszy Brier Score. Zero zgadywania wyniku z rozmowy.