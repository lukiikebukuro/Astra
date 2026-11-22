# Metodologia debaty o przeczuciu Menmy (spisana PRZED wynikami, 22.11.2026 ok. 2:00)

Cel: wybrać najlepszy projekt mechanizmu przeczuć Menmy. To **debata nr 1** (jak zbudować). Debata nr 2 (dwa modele liczące szanse konkretnej przepowiedni) to część produktu i może, ale nie musi, wyjść z tej debaty.

## Protokół
- **R1, niezależnie:** Argon (`gemini-4-argon`) i GPT-6.1 (`gpt-6.1-sol`, rozumowanie `xhigh`) dostają ten sam `brief.md`. Nie widzą się nawzajem ani pomysłów Claude'a (żeby się na nich nie zakotwiczyli).
- **R2, ultrasceptyk na krzyż:** Argon obala projekt GPT, GPT obala projekt Argona. Krytyk nie wie, który model napisał projekt („inny model”). Najpierw uczciwe streszczenie w 3 zdaniach (dowód zrozumienia), potem 5 zarzutów z wagą i scenariuszem porażki, na końcu 3 warunki zmiany zdania.
- **R3, obrona:** autor dostaje krytykę swojego projektu; przy każdym zarzucie „przyjmuję” albo „odrzucam” z powodem; potem poprawiona specyfikacja.
- Do modeli idzie tylko brief i ich teksty: zero rozmów, dzienników i danych osobowych poza liczbami z briefu.

## Sędzia
Claude, trzeci model, niezależny od obu (zasada projektu: model nie jest sędzią własnej bramki). Ocenia **ostateczne projekty z R3** według rubryki niżej, ustalonej przed przeczytaniem wyników. Rubryki nie zmieniamy po fakcie.

| kryterium | waga | co znaczy 5/5 |
|---|---|---|
| Magia | 25% | Łukasz ma poczucie, że Menma naprawdę widzi; są momenty „wow”, nie przypomnienia |
| Uczciwość liczb | 20% | pewność ma przyrząd (kalibracja na wynikach), liczby z danych, słowa z modelu; mała próba uczciwie obsłużona |
| Bezpieczeństwo i dobrostan | 20% | granica zdrowia (prawdopodobne, nie „co robić”), prywatność, nie nakręca sprawdzania szans w kółko |
| Wykonalność | 15% | MVP na jeden wieczór na obecnej architekturze (dziennik, logi, karteczka, Amnezja), koszt w groszach dziennie |
| Mierzalność | 10% | trafność i zachwyt da się zmierzyć; odporność na pewniaki i przepowiednie spełniające się same |
| Kanon | 10% | Menma brzmi jak Menma; reszta domu ma rolę |

Każde kryterium 0–5, wynik ważony. Osobno: które zarzuty z R2 autor przyjął, a które odrzucił, i czy słusznie; czy któryś model przyjął pomysł Łukasza (70%, debata) bez krytyki, czyli przytaknął.

## Wynik
Plik `wnioski.md`: oceny obu projektów, co bierzemy z każdego, co z pomysłów Claude'a (koperta, Księga losu domu, tablica trafień, liczby z kodu) przetrwało krytykę, i jeden projekt do wdrożenia w prostych słowach.
