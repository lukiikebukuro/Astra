# Polecenie dla CC — Astra: rozdzielenie solo/wspólny + fix main.py

Zielone światło na cały plan tak jak zaproponowałeś. Konkretnie:

## Krok 0 — rozdzielenie (rozszerzone o astra_base.txt)
Potwierdzone: rozdzielenie obejmuje oba miejsca, nie tylko main.py.

- **main.py:** rozbić `ASTRA_MONOLOGUE_INSTRUCTION` na `ASTRA_MONOLOGUE_SOLO` (nowy, edytowalny) + zostawić obecny dla Wspólnego. `build_system_prompt` dostaje parametr trybu z domyślną wartością taką, żeby ścieżka Wspólnego wychodziła bit w bit identyczna — weryfikacja testem porównującym prompt przed/po, nie na słowo.
- **astra_base.txt:** zostajemy przy jednym pliku (nie dzielimy na dwa) — zgadzamy się z Twoją propozycją. Sekcja "WSPÓLNY POKÓJ (Z AMELIĄ)" wchodzi w znacznik (np. `{wspolny_block}`), który w trybie solo renderuje się jako pusty. Jeden plik = charakter Astry edytujemy w jednym miejscu, bez ryzyka rozjazdu między solo/wspólny w przyszłości.
- Amelia i jej plik (`amelia_persona.txt`) — nie ruszamy, zero zmian.
- Reguła ANTI-SYNC o Amelii — wypada z wariantu solo (main.py) i z promptu solo (astra_base.txt) w ramach tego samego rozdzielenia, tym samym mechanizmem.

## Krok 1 — main.py, wariant solo
- 1a: wyrzucić nazwane gesty (*Prycham.*, *Unosisz brew.*, framuga) → zasada bez słownika.
- 1b: `"response": "TWOJA ODPOWIEDŹ."` zamiast `"...Z FIZYCZNOŚCIĄ."`
- 1c: **Opcja A potwierdzona.** safe_haven liczony w kodzie z sygnałów (ból/Crohn/kryzys w wiadomości + stan, plus reguła z marcowego audytu: jeśli Łukasz sam wraca do pracy/projektów → false), wstrzykiwany jawnie do promptu. Pole od modelu zostaje jako log telemetryczny (nie jako bramka) — dokładnie po to, żeby po tygodniu mieć dane "kod vs model" do kalibracji, tak jak przy shadow mode u sióstr.

## Krok 2 — astra_base.txt
- **2a ("Nie wiem") — rób razem z Krokiem 1**, tak jak proponujesz. Zero ryzyka dla pomiaru, inny mechanizm awarii (konfabulacja, nie styl).
- **2b (scenki anty-sync) i 2c (wielokropek) — odłożone za pomiar**, potwierdzone. Powód: nie chcemy zaciemniać odczytu didaskaliów (cel: 86% → ≤50%) nowym tekstem z gwiazdkowanymi przykładami w trakcie mierzenia efektu Kroku 1. Wrócimy do obu po weryfikacji.

## Krok 3 — weryfikacja
Tak jak proponujesz: baseline (sierpień: didaskalia 86%, dłoń 30%, imię 13%, mediana 186, krótkie 5.6%) zapisany do pliku przed zmianą. Po deployu: golden harness jako regresja na RAG, potem ~tydzień normalnych rozmów, ten sam `style_audit.py`. Werdykt z logów po, nie z logiki promptu — zgoda.

## Start
Zaczynaj od Kroku 0 i Kroku 1. Pokaż diff do przejrzenia przed jakimkolwiek pushem/deployem — nic nie leci bez naszego słowa.
