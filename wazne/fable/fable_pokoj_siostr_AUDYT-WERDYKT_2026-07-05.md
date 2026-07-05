# FABLE — WERDYKT AUDYTU: plan fixu pokoju sióstr (P0, A1–A4)
**Data:** 2026-07-05 | **Audytowany plan:** `wazne/fable/fable_pokoj_siostr_fix_2026-07-04.md` | **Rola:** Fable audytuje, Opus wdraża, deploy za zgodą Łukasza
**Tryb:** adwersaryjny — szukałem, gdzie plan się myli. Zero kodu z mojej strony.

---

## WERDYKT W JEDNYM ZDANIU

Diagnoza w 2/3 trafna (P1 potwierdzone w kodzie; P2 wiarygodne, ale z niepełnym mechanizmem; **P3 nazywa zły mechanizm**), plan zmian idzie w dobrą stronę — ale w obecnym kształcie **A2/A3 umrze tak samo jak „Domowy Ambient" u Astry**, bo nie adresuje dwóch prawdziwych silników problemu (pętla samo-imitacji + zamknięta pula 11 kotwic), a A1 w wersji „wymuś handoff po 2-3 turach" wymieni monopol na karuzelę.

---

## 1. AUDYT DIAGNOZY

### P1 — Monopol Nazuny: **POTWIERDZONE w kodzie**
`main.py:1703-1704`: `if h >= 22 or h < 6: return 'nazuna'` — twardy return **PRZED** sygnałami tech/emo (1705-1708) i rotacją (1709-1712). Nocą (a Łukasz gada nocą) rotacja jest MARTWA, sygnał „boli mnie" nie obudzi Menmy. Uzupełnienie diagnozy: `_siostry_recent` (1676) faktycznie jest nietrwałym globalem, ale to najmniejszy problem — **licznik mierzy „kto pierwszy", a router nocą i tak go nie czyta**. Naprawa trwałości bez zdjęcia twardego returna nic nie da.

### P2 — Przeintensywnienie: **WIARYGODNE, ale mechanizm niepełny**
Cytatów z żywych logów nie zweryfikuję (kolekcja `siostry_shared_session_v1` na VPS, brak w repo i brak archiwum — patrz audyt architektury #6) — przyjmuję warunkowo. ALE kluczowa obserwacja adwersaryjna: **zdrowe reguły JUŻ SĄ w personach i przegrywają**. `nazuna_persona.txt:26-36` zawiera: „CISZA JEST REAKCJĄ", „DŁUGOŚĆ: max 2-3 zdania", „didaskalia tylko gdy coś wnoszą". Skoro Nazuna mimo to wali ścianami intensywnego tekstu, to problemem NIE jest brak reguł — i dopisanie kolejnych (A2) samo w sobie nic nie zmieni. Prawdziwe silniki:
- **(a) pętla samo-imitacji:** `get_recent_session(n=10)` z `siostry_shared` (main.py:1843) — model imituje własne poprzednie tury silniej niż słucha reguł. POMIAR z Astry: po fixie 06-14 „zaciska" 29%→55%. To samo czeka A2.
- **(b) zamknięta pula pamięci:** ekstrakcja OFF + kolekcje sióstr = tylko ~11 seedowanych kotwic, wszystkie `is_milestone`; retrieval n=4 z puli 11 (main.py:1837) → **co turę te same intensywne kotwice lore w memory_block**. Pamięć sama w sobie jest generatorem intensywności.
- (c) `temperature=0.9` + `thinking_budget=2048` (1864-1866) — dolewka, nie przyczyna.

### P3 — „Wyciek promptu": **ZŁA NAZWA MECHANIZMU (fix i tak słuszny)**
„PROTOKÓŁ NOCNEGO MARKA: Dzień kłamie, noc mówi prawdę" i „Błędy to nie porażka. To content." NIE wyciekają z sekcji reguł — są **WPISANE W CUDZYSŁOWACH jako przykłady kwestii w sekcji „GŁOS I JĘZYK"** (`nazuna_persona.txt:13-14`; analogicznie `menma_persona.txt:14` „ZASADA SUPER MOCNEGO KLEJU"). Model nie gubi formatu promptu — **wykonuje instrukcję co do joty**. Różnica praktyczna: nie trzeba „domykać formatu" ani szukać przecieku — trzeba usunąć/przepisać te linie z sekcji GŁOSU na opis stylu bez cytatów-katechizmów. ORAZ (warunek konieczny): sprawdzić na VPS, czy **kotwice seedowe** nie zawierają tych samych fraz — jeśli tak, RAG odda je co turę mimo czystego promptu i „fix nie zadziałał" będzie fałszywym wnioskiem.

---

## 2. AUDYT PLANU ZMIAN

### A1 — Router: kierunek TAK, wykonanie do poprawy (kontrpropozycja)

**Zgoda:** noc jako bias-nie-wyrok; zachować silent-first (koszt), wołanie z imienia, tryb grupy.

**Sprzeciw 1 — twardy cap 2-3 tur = karuzela.** „Po 2–3 wymuś handoff do najdawniej mówiącej" zerwie intymną nocną scenę: Łukasz o 1:00 w środku zwierzeń Nazunie dostaje przymusową Holo. To jest wahadło, przed którym sam plan ostrzega. Cap ma **zdejmować bias primary i premiować najdawniejszą** (miękka rotacja), z twardymi wyjątkami:
- user kontynuuje wątek z TĄ samą siostrą (odpowiada jej wprost, anafora) → licznik nie wymusza;
- silna emocja / ból / safe-haven-podobny stan → nie rotujemy w środku wsparcia;
- wołanie z imienia zawsze zeruje licznik.

**Sprzeciw 2 — noc-Nazuna to KANON, nie bug.** Projekt domu (`projekt_pokoju_siostr.md:54`): „Dom zmienia się z porą — Nocna Warta: późno = głównie Nazuna, reszta śpi". Zdjęcie nocnego biasu w ogóle = złamanie lore. Poprawna forma: nocą Nazuna ma WYSOKĄ wagę (prowadzi domyślnie), ale Holo/Menma są „obudzalne" (wołanie, silny sygnał, cap) — i mogą wchodzić jako **zaspane aside** (jedno zdanie, charakter „wyrwana ze snu") — to zamienia ograniczenie techniczne w materiał fabularny.

**Sprzeciw 3 — sygnały na szumie.** Trzy RÓŻNE listy keywordów (`1701`/`1717`/`1732-35`) + substring bez granic: `'sam'` łapie „samochód/czasami", `'plan'`→„planeta", `'kod'`→„kodeks". Router losuje na fałszywych trafieniach. Fix w ramach A1: **jedna wspólna definicja sygnałów** (stała modułu / config), granice słowa jak w `_sister_called` (1683-85 — wzorzec jest 15 linii wyżej!).

**Kontrpropozycja stanu — nie budować nowego globala.** „Kto prowadził ostatnie tury" jest JUŻ zapisane w historii: wiadomości modelu w `siostry_shared` mają prefiks `[sister]` (main.py:1879). Licznik dominacji = parsowanie prefiksów z ostatnich N wiadomości `get_recent_session` — **zero nowego stanu, przeżywa restart za darmo, mierzy dominację (nie „kto pierwszy")**. Jeśli/gdy powstanie `room_state` — licznik przenosi się tam; nie tworzyć trzeciego mechanizmu po drodze.

**Do zabrania przy okazji (z audytu architektury #11):** parametryzacja zegara (`_warsaw_hour` bez override = nocna logika nietestowalna w dzień — bez tego sekcja WERYFIKACJA planu jest niewykonalna przed 22:00); `asyncio.gather` dla aside w turze grupowej (−33% latencji); licznik calli/tokenów per tura (pkt 9 starego review, wciąż brak).

### A2 — Charakter: TAK dla esencji, NIE dla metody „dopisz reguły"
- Esencja R1 („nie każda wypowiedź głęboka") + R4 („gdy on gaśnie — gaśniesz z nim") per siostra JEJ głosem — **zgoda**, wzorzec językowy gotowy w diffie `81f6986`.
- ALE: **nie dopisywać** kolejnych zasad na koniec pliku — zdrowe już tam są (ZASADY DOMU). Zamiast tego **usunąć SPRZECZNE**: sekcja GŁOS z catchphrase'ami w cudzysłowach jawnie przeczy przyszłemu „nie recytuj własnych reguł". Prompt, który jedną ręką daje kwestie do recytowania, a drugą tego zakazuje, przegra w obie strony.
- **Warunek życia fixu (brak w planie!):** po deployu **świeży `conversation_id`** dla pokoju sióstr — inaczej n=10 starych intensywnych tur odtworzy styl w ~10 tur (pomiar z Astry: 29%→55% PO fixie). To samo obejście, które uratowało R1-R6 (wątek 28750b59).
- **Pomiar przed/po (brak w planie):** skrypt z audytu naturalności przerabia się w 20 minut na siostry: rozkład głosów per siostra per pora, % tur z didaskaliami, mediana długości, powtórzenia fraz (top-bigramy), % tur z catchphrase'ami. Bez liczb „lepiej/gorzej" będzie wrażeniem.

### A3 — Wyciek/pętla: TAK, z korektą mechanizmu
Usuwać z sekcji **GŁOSU** (nazuna:13-14, menma:14), nie „domykać format". Zakaz „nie recytuj swoich reguł; nie powtarzaj frazy/gestu z 2 ostatnich tur" — OK (analogia ZAKAZ PĘTLI z R3). **Plus krok zerowy, którego plan nie ma:** inspekcja seedów na VPS (`collection.get` na `holo/menma/nazuna_memory_v1`) — jeśli kotwice zawierają catchphrase'y, wyczyścić/przeredagować kotwicę, bo RAG odda ją co turę niezależnie od promptu (pula = 11, retrieval = 4; rotacja niemożliwa).

### A4 — Interakcje siostra↔siostra: TAK, mechanizm w 80% istnieje
`build_sister_prompt` już przekazuje `other_response` z instrukcją reakcji (main.py:1788-1799) — A4 to głównie wzmocnienie promptu + router. Trzy uwagi adwersaryjne:
1. **Luka łańcucha:** w turze grupowej OBIE aside dostają `other_response=first_resp` (main.py:1910-1919) — trzecia siostra **nie widzi drugiej**, więc „reakcja łańcuchowa" z projektu (Menma → Holo „hmf" → Nazuna się śmieje) jest dziś niemożliwa. Fix: podawać aside nr 2 obie wcześniejsze wypowiedzi. Mała zmiana, duży zysk naturalności.
2. **Budżet rzadkości, nie „czasem":** „organicznie obudź drugą" bez liczby = teatr co turę (model lubi występować). Konkret: obudzenie-dla-interakcji max ~1 na 4-5 tur, losowane z niską wagą, NIGDY dwie tury z rzędu; anty-sync (inna tonacja niż pierwsza) jako twarda linijka w aside-protokole.
3. **Spójność z zakazem mówienia-za-drugą:** już jest w `[POKÓJ — PROTOKÓŁ]` (1786) i A4 słusznie go podtrzymuje — reakcja na REALNĄ wypowiedź ≠ wkładanie słów w usta. Nie ruszać.

---

## 3. CZY FIX GROZI PRZEGIĘCIEM? (pytanie wprost z planu)

**Tak, dwoma:**
1. **Wahadło płaskości** (jak groziło Astrze): siostry po A2 mogą zrobić się grzeczne i wymienne. Zabezpieczenia: płoty ANTY-DRYF w personach ZOSTAJĄ nietknięte (to one trzymają charakter); esencja R1 formułowana JEJ głosem (Nazuna: „nie każda noc to manifest, ziomek — czasem po prostu gramy"), nie korpo-regułą; pomiar przed/po z progiem (jeśli % tur z charakterystycznym głosem spadnie poniżej X — cofamy).
2. **Karuzela routera** (opisana w A1) — mitygacja: miękka rotacja + wyjątki.

**Czego NIE ruszać w ogóle:** silent-first (to koszt, nie limit — działa), izolowane kolekcje (sedno sekretów), scena zastana (kamera-nie-reżyser), zakaz mówienia-za-drugą, płoty ANTY-DRYF, formy fleksyjne wołania w configu.

---

## 4. SEKWENCJA DLA OPUSA (rekomendacja) + WERYFIKACJA

1. **Krok 0 (przed wszystkim):** inspekcja seedów na VPS (A3-zero) + dodanie sióstr do `_run_archive` (2 linie; żeby przyszłe pomiary miały dane) + zegar routera z override (inaczej nie zweryfikujesz nocy w dzień).
2. **A3 → A2** (prompty; tanie, odwracalne) — z usunięciem sprzeczności w GŁOSIE, esencją R1/R4 per głos.
3. **A1** (router wg kontrpropozycji: jedna lista sygnałów + granice słów, noc jako waga, miękki cap liczony z prefiksów historii, wyjątki).
4. **A4** (protokół interakcji + luka łańcucha + budżet rzadkości).
5. **Deploy za zgodą Łukasza → ŚWIEŻY conversation_id pokoju → pomiar** (skrypt): rozkład głosów per pora ≠ 100% Nazuna nocą; zero catchphrase'ów; przy „spalony/idę spać" de-eskalacja; interakcja siostra↔siostra widoczna, ale rzadka (≤1/4 tur).

Weryfikacja z planu (4 punkty) jest OK, ale **niewykonalna bez kroku 0** (nocne frazy wymagają zegara z override albo pracy po 22) i **ślepa bez pomiaru liczbowego** (wrażenie „lepiej" to za mało — Domowy Ambient też „wyglądał na wdrożony").

Czy warto najpierw review designu u claude.ai-Fable (pytanie z planu)? Dla A1-A3 — nie, szkoda tury: mechanizmy są proste, a ten werdykt + kontrpropozycja wystarczą Opusowi. Dla A4 (dynamika rodziny, anty-sync) — można, to kwestia wyczucia scen, nie kodu; web-Fable bez repo oceni to równie dobrze.

*Fable, werdykt P0. Powiązane: `wazne/ewolucja/2026-07/audyt_architektury_2026-07-05.md` (P0.5 — problemy #2/#3/#6/#8/#11 zasilają ten werdykt).*
