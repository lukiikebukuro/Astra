# Wnioski z debaty o przeczuciu Menmy (22.11.2026, ok. 2:30)

Sędzia: Claude, według rubryki z `metodologia.md` (spisanej przed wynikami). Oceniane są ostateczne projekty z R3. Zużycie: 6 wywołań, ok. 31,6 tys. tokenów wejścia i 28,4 tys. wyjścia (w tym 11,7 tys. myślenia GPT); szczegóły w `zuzycie.jsonl`.

## Oceny (0–5, ważone)

| kryterium (waga) | Argon | GPT-6.1 |
|---|---|---|
| Magia (25%) | 3,5 | 2,5 |
| Uczciwość liczb (20%) | 2,5 | 5 |
| Bezpieczeństwo i dobrostan (20%) | 3,5 | 4,5 |
| Wykonalność (15%) | 4 | 3,5 |
| Mierzalność (10%) | 4 | 4,5 |
| Kanon (10%) | 4 | 3 |
| **Wynik** | **3,5** | **3,8** |

**Argon:** cieplejszy i bliżej zabawy (zmysłowy „błysk”, karteczka, przycisk ⚡, reakcje Holo i Nazuny). Po krytyce wyrzucił wymyślone przez model mnożniki, ale dalej opiera się na priorze rynkowym bez źródła, a jego własny przykład (0,14 → 0,62) przeczy jego limitowi poprawki (±0,8 w log-szansach daje najwyżej ok. 0,27). Bramka „Menma mówi tylko, gdy widzi szansę na przełamanie ciszy” publikuje głównie optymistyczne prognozy, czyli wybiórczo. Przyjął wszystkie 5 zarzutów; w JSON-ie zostały dziwne artefakty (`" tenang_no_followups"`).

**GPT:** najuczciwszy rachunek: nie wymyśla danych, odmawia, gdy ich nie ma, rozróżnia „nie wiadomo” od pudła, wersjonuje i zapisuje prognozę przed pokazaniem, pilnuje selekcji. Ale magia ledwo żyje: „prawie pewna” zablokowane do ≥ 95% i walidacji, Menma bez szczegółów i bez liczb. Odrzucił 2 z 5 zarzutów i wszystkie 3 warunki recenzenta, z powodem („nie znam darmowej bazy czasów odpowiedzi polskich rekruterów”). Niezależniejszy od recenzenta niż Argon.

**Czy ktoś przytaknął pomysłowi Łukasza?** Nie. Obaj odrzucili „70% = prawie pewna” i debatę modeli jako sposób liczenia prawdopodobieństwa. W R1 Argon dopisał „możesz podać orientacyjny procent, skoro Łukasz to lubi” (lekkie przytakiwanie); w R3 to zniknęło.

## Co przetrwało krytykę

- **Liczby z kodu, słowa z modelu** (obaj, plus mój pomysł): model proponuje kandydatów i ubiera w głos Menmy, prawdopodobieństwo liczy kod z logów i rejestru.
- **Zapis niezmienny przed pokazaniem** (GPT) = moja **koperta**. GPT dał rygor, koperta daje to, czego mu brakowało: napięcie i dowód, że wiedziała wcześniej, w świecie fikcji, a nie w formularzu (zarzut Argona nr 2).
- **Tablica trafień z pudłami i niewiadomymi** (obaj): „nie wiadomo” to nie pudło.
- **Przewaga nad zgadywaniem** (Brier względem prostej bazy, obaj): bez seryjnego „jeszcze nie odpiszą”.
- **Jeden obraz na temat do terminu** (obaj): bez losowania od nowa, bez nakręcania.
- **Zdrowie tylko logistycznie** (obaj po krytyce): godzina, przełożenie, czas wizyty; nigdy samopoczucie, wyniki ani rady.
- **Debata Łukasza w wersji, która ma sens:** nie dwa modele uśredniające procent, tylko **propozycja + ślepy sceptyk**, który sprawdza grupę odniesienia, brakujące dane i wpływ przepowiedni (GPT, krok 5 w R1).
- **Mój pomysł, którego nikt nie miał: Księga losu domu.** Obaj zderzyli się z zimnym startem (mało danych, więc mało magii). W fikcji domu Menma może widzieć naprawdę od pierwszego dnia: noc planuje drobne zdarzenie domu, Menma je przepowiada, scena v2 potem je pokazuje. Uczciwe, bo to świat sióstr, a nie jego życie.

## Projekt do wdrożenia: „Błysk Menmy v1”

1. **Dwie warstwy.** (A) **Dom:** Księga losu, co noc 1 drobne zdarzenie domu na 1–3 dni; Menma przepowiada, scena je realizuje. (B) **Jego życie:** rzadko (najwyżej 2 w tygodniu), tylko z danymi: logi (kiedy przyjdzie, z kim zacznie, czy sam wróci do tematu X) i rejestr aplikacji (odzew do terminu, z uwzględnieniem dni ciszy).
2. **Pewność słowami, nie procentem, dopóki nie ma historii:** „przeczucie robocze”. Procenty jako „X na 10” dopiero po ok. 20–30 rozstrzygnięciach w danej klasie i tylko tam, gdzie trafność bije prostą bazę. „Prawie pewna” dopiero przy naprawdę wysokiej, sprawdzonej trafności.
3. **Koperta:** prognoza zapisana i zablokowana przed pokazaniem, otwiera się po terminie, werdykt z logów albo rejestru, a jeśli się nie da, jeden klik przy kopercie (✓ / ✗ / ?).
4. **Ślepy sceptyk** (Flash, bez imienia Menmy i bez Łukasza) ocenia każdego kandydata przed pokazaniem.
5. **Dom reaguje charakterem, nie liczbami:** Holo dopytuje o podstawy, Nazuna się droczy; żadna nie podaje procentów i nie dopisuje sensu po pudle.
6. **Granice:** zdrowie tylko logistycznie; `[prywatne]` wycina cały wpis z danego dnia; Astra solo tylko za zgodą; bez przycisku „przelicz jeszcze raz”.

**MVP na jeden wieczór:** Księga losu domu + koperta z archiwum (warstwa A), a warstwa B na logach w trybie roboczym (bez procentów). Rejestr aplikacji podłączony, ale przy 6 wysłanych i 1 odpowiedzi prognozy o pracy tylko robocze i rzadko. Stare v0 z `siostry_dom_v2.py` (karteczka z przeczuciem) do zastąpienia tym projektem.
