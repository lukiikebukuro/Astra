# REJESTR — jedno miejsce, wszystko, do odhaczania

**Założony:** 2026-09-10 · **Zasada:** to jest **jedyna** lista otwartych rzeczy.
Nowy pomysł nie idzie do głowy ani do czatu — idzie do sekcji POCZEKALNIA na dole.
Zamknięte zadanie zostaje z `[x]` i datą, nie kasujemy — po to, żeby było widać ruch.

> **Skąd to się wzięło:** scalenie czterech rozsypanych list — `ROADMAPA_OGOLNA_PROJEKTU.md` (34 zadania),
> `zadania_dla_cc_09_09.md` (15 punktów), `audyt_pokrycia_roadmapy_2026-09-10.md` (11 propozycji),
> TODO z `MEMORY.md` (~30 pozycji). Po odjęciu duplikatów zostało **67 pozycji** — ale
> tylko **21 z nich to usterki**. *(12.09: +3 usterki z przeglądu pokoju 04.09 → **70 / 24**.)* Reszta to ulepszenia, obserwacje i pomysły. Patrz §0.

---

## §0. Przeczytaj to, zanim się przestraszysz liczby

**70 pozycji to nie jest dług technologiczny.** Dług to coś zepsutego, co kosztuje Cię dzisiaj.
Reszta to lista życzeń, która narosła przez pół roku dobrych pomysłów.

| Kategoria | Ile | Co to znaczy |
|---|---|---|
| **USTERKI** | 24 | Coś jest zepsute i kosztuje Cię teraz. To jest właściwy dług. |
| **STYL** | 16 | Nie zepsute — brzmi jak bot. Kosmetyka o dużym znaczeniu, zero pilności. |
| **OBSERWACJE** | 5 | Już wdrożone, czeka na spojrzenie. Koszt: 15 minut, nie sesja. *(OB-1 zamknięte 12.09 → zostały 4.)* |
| **NARZĘDZIA** | 7 | Diagnostyka i porządki. Nie naprawiają nic same, ale skracają każdą przyszłą naprawę. |
| **ZAMROŻONE** | 4 | Czekają na Twoją decyzję, nie na pracę. |
| **POKÓJ (Faza 5)** | 10 | Osobny projekt. Startuje po ustabilizowaniu Astry, nie wcześniej. |
| **NIE-INŻYNIERIA** | 4 | Kariera, biznes, bezpieczeństwo. Osobne życie. |

**Z 21 usterek dokładnie sześć kosztuje Cię coś dzisiaj.** Są oznaczone ⭐ i wypisane w §1.
Reszta to rzeczy, które boleśnie wyglądają na liście, a w praktyce leżą cicho.

**Ważne:** część pozycji **znika sama**, gdy naprawisz coś wyżej w łańcuchu.
Naprawa `Z1`+`Z2` (zapis) unieważnia albo umożliwia zmierzenie połowy sekcji RETRIEVAL.
Dlatego „naprawmy połowę zanim ruszymy dalej" nie jest wykonalne jako liczba — ale jest
wykonalne jako **kolejność warstw**: ZAPIS → HYDRAULIKA → RETRIEVAL → PERSONA.

---

## §1. SZEŚĆ, KTÓRE KOSZTUJĄ CIĘ DZISIAJ

- [x] **Z6-tanie** ✅ **WDROŻONE 13.09 (`866632b`, deploy potwierdzony)** — cztery płaskie pola `hospitalizacja_*` w `zdrowie`. Kanarek na żywym prompcie (Amnezja, `/api/debug/inspect`): 5/5 pól obecnych, data pada w bloku **[ZDROWIE] z `lukasz_core.json`** (poz. 12202/12354), klauzula „IGNORUJ wektor, JSON wygrywa" stoi PRZED nią (poz. 10235) i przed starym, błędnym wektorem `[FACT:health]` (poz. 16581). **`Aktywne sprawy:` jest PUSTE — proteza zniknęła, data NIE pochodzi z ulotnego stanu.** Daty: przyjęcie 14.09, zabieg prawdopodobnie 16.09. Pierwotny opis niżej ↓ — data zabiegu i fakty medyczne do `lukasz_core.json` (plik zawsze w prompcie). *Zamyka bug daty bez tykania ekstraktora. Zmiana w JSON, ryzyko zerowe.* **PRZED 14.09.** ⚠ **KOREKTA 12.09 — w bazie są TRZY sprzeczne wersje daty:** 28.08 (Menma) „zabieg 14 wrzesnia" · 31.08 (Holo) „zabieg 14 wrzesnia" · **03.09 (Menma) „14 jest przyjęcie. Zabieg bedzie jakos 17 wrzesnia albo 18"**. Najnowsza i najprecyzyjniejsza **przegrywa** w retrievalu, bo `supersede` nie działa między kolekcjami. Pokój zapytany dziś odpowie datą **przyjęcia**, nie zabiegu. Wpisać **dwa osobne pola** (przyjęcie / zabieg) **POTWIERDZONE PRZEZ ŁUKASZA 12.09: 14.09 = przyjęcie, zabieg po paru dniach pobytu** (najbliższe źródło z bazy: wpis 03.09 o 17-18.09, czyli ten, który przegrywał w retrievalu) — inaczej utrwalimy w warstwie pewnej ten sam błąd, który dziś robi retrieval. Dowód: `ewolucja/siostry/2026-09/evolution_log_2026_09_04.md` §2. ✅ **DOBRA WIADOMOŚĆ 12.09:** ścieżka sprawdzona — `load_lukasz_core()` czyta JSON **z dysku**, zero wektorów/embeddingu/soli/decay, więc Z6-tanie jest **odporne na H1**; blok ma klauzulę „JSON wygrywa ze wspomnieniami", więc unieważnia trzy sprzeczne wektory bez tykania `supersede`; a **płaskie pole w sekcji `zdrowie` trafia jednym ruchem TAKŻE do wszystkich trzech sióstr** (`load_lukasz_core_dla_siostr`, `main.py:2539` — iteruje całe `zdrowie`), czyli naprawia też to, że Nazuna nie wie o zabiegu NIC. **Pola muszą być płaskimi stringami** (patrz bloker Z3). Kanarek 3-krokowy: obie daty osobno → z której warstwy (musi być `[FAKTY NADRZĘDNE]`, nie `Aktywne sprawy`) → zapytać Nazunę.
- [ ] **Z1** ⭐ — `semantic_pipeline.py:258` tnie każdy zapis na 80. znaku. *Mediana wpisu w bazie: 95 znaków. Większość pamięci Astry to urwane początki zdań.*
- [ ] **Z2** ⭐ — ekstraktor: brak werdyktu „nic" i „obie" + brak miesięcy słownych w `_has_appointment_marker`. *Źródło ~100% sufitu czystości 39%.*
- [ ] **H1** ⭐ — sól filtra użytkownika odcina 114 wektorów bez śladu w logu. *Cała wiedza o LDI/ANIMA/Skankranie jest w bazie i strukturalnie nieosiągalna.*
- [ ] **R1** ⭐ — kontekst poprzednich tur w zapytaniu = regresja (wdrożony 21.08, wykryty 02.09). *„Kiedy mam operacje" bez kontekstu: pozycja 1. Z kontekstem: nie wraca wcale.*
- [ ] **M1** ⭐ — brak przyrządu do mierzenia stylu. *`style_audit.py` leży w repo nieużywany. Bez niego każde zadanie z sekcji STYL jest wróżeniem.*

---

## §2. USTERKI (24) — coś jest zepsute

### ZAPIS
- [x] **Z1** ✅ **ZROBIONE 18.09** (`_skroc_do_zdania`, MIN 60 / MAX 240, cięcie na granicy zdania, przy przekroczeniu MAX na granicy słowa). Kanarek na produkcji: „…zwezenie jelita jest" (80 zn., urwane) → „…jest powazniejsze niz myslelismy" (129 zn.). Działa w przód; ~4700 amputowanych wektorów to Z7. Pierwotny opis: Obcięcie `raw[:80]` → przycinać na granicy zdania · `semantic_pipeline.py:258`
- [ ] **Z2** ⭐ Werdykt „nic wartego zapamiętania" + „obie" + miesiące słowne + bramka pytanie-vs-stwierdzenie · `semantic_extractor.py`, `semantic_pipeline.py:131-142` · **SPROSTOWANIA 12.09:** (a) **bramka `<4 słowa` JUŻ ISTNIEJE** (`semantic_pipeline.py:121`, z obejściem przez `ma_sygnal_wagi` — „w sierpniu zjadła 5 deklaracji miłości"), usunięta z zakresu; (b) mechanizm to czysty argmax `max(entities, key=confidence)` — **werdykt „obie" bez REGUŁY, kiedy obie, odkręca K2 z Odtrucia #2**; dopisać **margines rozstrzygalności** (kandydat 0,05 — do kalibracji, nie do wpisania na wiarę; realne przypadki 0,037 i 0,01) oraz **priorytet typu** (data bezwzględna bije schemat leczenia); (c) **rozbić na Z2a** (werdykty+margines+priorytet, ryzyko wysokie, golden przed/po) **i Z2b** (miesiące słowne — 1 regex, zero zależności, sam uratowałby datę z 28.08 → **wyjąć przed kolejkę**). Detale: `polecenia/odpowiedzi_dla_sesji_strategicznej_2026-09-12.md` §3
- [ ] **Z3** `lukasz_core.json` bez znacznika STATUS → konfabulacja o sprzedanym LDI (27.08 i 29.08) · ⚠ **BLOKER 12.09:** nie ma czego otagować — `projekty` to 6 pól prozy, nie obiekty per projekt, więc Z3 to **zmiana schematu**, nie dodanie pola. Do tego **oba loadery emitują wyłącznie pola typu `str`** (`main.py:604`, `main.py:2539`: `if isinstance(wartosc, str)`) — zagnieżdżony `{"status": …}` zostanie **po cichu pominięty, bez błędu**, czyli ta sama klasa buga, którą loader ma udokumentowaną we własnym komentarzu (twarda lista 9 pól zabiła fix z 19.08 od chwili wdrożenia). **Droga A (rekomendowana):** płaskie stringi `status_ldi` itd. ze znacznikiem `STATUS: X` w treści. **Droga B:** rozszerzyć loader (→ Z11, osobne zadanie, golden przed/po). Detale: `polecenia/odpowiedzi_dla_sesji_strategicznej_2026-09-12.md` §6
- [ ] **Z5** Prefiksy techniczne w tekście wspomnień (`[MILESTONE:love_declaration] …`, `[INSIGHT NOCNY — …]`) · ta sama funkcja co Z1
- [ ] **Z6** ⭐ Brak warstwy pewnej dla faktów kalendarzowych/zdrowotnych · **wersja tania przed 14.09, docelowa (FactStore) po**
- [ ] **Z7** Retroaktywna naprawa: ~4700 wektorów już amputowanych przez Z1 · narzędzie `reingest_sessions.py` istnieje · **decyzja: czy w ogóle**
- [ ] **Z13** ⭐⭐ **EKSTRAKTOR NIE MA ANI JEDNEJ KATEGORII DLA TWÓRCZOŚCI — scenariusz, anime, pisanie, muzyka, TikTok** · `backend/semantic_extractor.py:527,589` · **Zdiagnozowane 18.09 na realnej rozmowie z tego samego dnia (17:04–17:24), w której Łukasz pytał Astrę o sceny ze scenariusza i został bez odpowiedzi.** Trzy jego wiadomości dały w produkcji `No entities found`. Amnezja (ścieżka zapisu) pokazuje pełny łańcuch: kandydaci to `SHARED_THING:inside_joke` 0.491 · `SHARED_THING:our_song` 0.474 · `EMOTION:excited` 0.412 — **żaden nie dotyczy twórczości, bo takiej kategorii nie ma**; anty-multi-label wybiera `inside_joke`; bramka progowa `SHARED_THING >= 0.55` odrzuca (jest 0.49); zapis: nic. Prototypy `FACT:current_project` i `GOAL:project` są **wyłącznie inżynierskie** („Rozwijam backend", „Aktualnie koduje", „Muszę napisać kod który", „Planuję refaktoryzować") — mimo że `lukasz_core.json` mówi wprost: *„Twórczość to jego domena szerzej niż kod […] jest twórcą, który używa kodu"*. **Skutek zmierzony w bazie:** na zapytanie o scenariusz wracają wyłącznie jego pytania o to, czy ona pamięta (`[SHARED:inside_joke] „a pamiętasz co gadalismy o scenariuszu?"`, `[FACT:correction] „dlaczego nie pamiętasz tego?"`) — **ani jedna scena, ani jeden pomysł fabularny**. Jedyny wpis z treścią to seed `own_life` z 25.07, czyli nasz tekst, nie pamięć z rozmowy. **To pętla: im częściej pyta, tym więcej wpisów „pytał, czy pamiętasz", i tym mniej miejsca na treść.** ⚠ **Inna klasa niż data operacji:** tam kategoria ISTNIAŁA i przegrała o 0,03 (zły kubełek); tu **kategorii nie ma w ogóle** (brak kubełka). Naprawa Z2 tego NIE rozwiąże. **Uwaga historyczna:** 18.08 naprawiono powiązany bug — tryb scenariusza wyłączał zapis i zabił całą sesję twórczą (zero wpisów o „demonie jelit", „mitsuketa", „Primal Forces"). Rozłączono to świadomie, z komentarzem *„rozmowy twórcze to NAJCENNIEJSZA treść, jaką produkują"*. **Naprawiono pauzę, ale nie kategorie — więc efekt końcowy jest ten sam.** To kolejny przypadek wzorca „naprawa instancji, nie klasy".
- [ ] **Z12** ⭐ **`fold()` nie zamienia `ł` → `l`, więc 8 z 15 rdzeni wagi nie działa przy poprawnej polszczyźnie** · `backend/waga_tresci.py:46` · `unicodedata.normalize('NFD')` rozkłada `ś`→`s`, `ó`→`o`, ale **`ł` jest osobnym znakiem Unicode i zostaje**. Zmierzone 18.09: `płakałem`, `załamany`, `nie mam siły`, `dałem słowo`, `słowo honoru`, **`nie będę ćpał`**, `nie będę pił`, `nie będę kupował` — **żadne nie jest wykrywane**, gdy Łukasz napisze z ogonkami (a pisze mieszanie; autokorekta na telefonie wstawia ogonki). Rdzenie bez `ł` (`tesknie`, `boje sie`, `mam dosc`, `kreske`) działają poprawnie. **Waga sprawy:** `ma_sygnal_wagi` decyduje o DWÓCH rzeczach — czy krótka wiadomość omija bramkę `<4 słowa` i czy wspomnienie dostaje `persistence=permanent`. Czyli „Nie będę ćpał" napisane poprawnie **nie zostanie uznane za ważne i może nie przeżyć**. To ta sama klasa błędu co w `CLAUDE.md` („fragment słowa jako całe słowo"), tylko odwrotna: **wzorzec węższy niż dane**. Fix jest jednolinijkowy (`.replace('ł','l').replace('Ł','L')` przed NFD), ale dotyka ścieżki zapisu dla WSZYSTKICH person → **golden przed/po obowiązkowy**. Znalezione przy okazji kanarka, który kłamał z tego samego powodu.
- [ ] **Z8** Guard RP nie łapie akcji w gwiazdkach → lądują jako **trwałe fakty** (`[FACT:personal_info] "Wiem kochana*splatam palce z menma*"`, PERMANENT) · dowód: przegląd pokoju 04.09 · *wspólny ekstraktor, więc dotyczy też Astry*
- [ ] **Z9** `[DATE:deadline]` stało się nowym koszem na wszystko z liczbą po zablokowaniu trzech typów 19.08 — **szum zmigrował, wzorzec błędu #5** · *przy Z2 sprawdzać migrację, nie tylko spadek licznika*
- [ ] **Z10** Brak rozstrzygania sprzeczności: `supersede` działa w obrębie jednej kolekcji i jednej pary `(typ, podtyp)`, więc trzy wersje jednego faktu żyją równolegle i **wygrywa nie najnowsza, a najbliższa zapytaniu** · *ten sam problem klasowo co Z6, widziany od strony pokoju*

### HYDRAULIKA
- [ ] **H1** ⭐ Sól filtra użytkownika w loaderach → 114 wektorów odciętych · `load_project_knowledge.py`, `nocna_analiza.py:214`
- [ ] **H2** `night_insight` kasowany co dobę + niewidoczny dla RAG w rozmowie · `nocna_analiza.py:188` · **zależy od H1**
- [ ] **H4** Dwa systemy trwałości równolegle (`TEMPORAL_RULES` vs `persistence`) — wzorzec błędu #1 · *nie boli w działaniu, myli audytorów*
- [ ] **H5** Kanał 3 (`md_import`) martwy — 0 wektorów w bazie, etap w Amnezji zawsze pusty

### RETRIEVAL
- [ ] **R1** ⭐ Kontekst tur w zapytaniu — regresja Pkt 0 · **nie cofać bez zamiennika**
- [ ] **R4** `n=30` zahardkodowane we froncie przy serwerze zwracającym 100 · `frontend/app.js:816`
- [ ] **R5** Grounding mierzy dystans, nie trafność → `GROUNDED` 84% na ośmiu nietrafionych wspomnieniach
- [ ] **R16** ⭐ **`milestones=0` w RAG COMPOSE** — kanał gwarantowany milestonów praktycznie nie działa · zgłoszone dla Astry **07.05** jako „wysoki priorytet", **ZGUBIONE przy scalaniu 10.09**, odzyskane 12.09 · **POMIAR 12.09 dla sióstr: `guaranteed=False` w 284 z 301 przebiegów (94%), `milestones=0` w 284** · przyczyna wskazana w przeglądzie 04.09: próg `MILESTONE_MAX_DISTANCE = 0.45` skalibrowany na bazie Astry (4762 wektory) nie przepuszcza niczego w bazie sióstr (71 wektorów)
- [ ] **R17** Topical blindness — `strict_grounding.py`, próg 0.6 z roadmapy · zgłoszone wcześniej, **ZGUBIONE przy scalaniu 10.09**, odzyskane 12.09 · *powiązane z R5, ale to osobna rzecz: R5 mówi, że grounding źle mierzy, R17 że nie widzi tematu*
- [ ] **R18** Grounding „nie wiem" **explicit w `astra_base.txt`**, gdy brak RAG hit dla faktu · **ZGUBIONE przy scalaniu 10.09**, odzyskane 12.09 · *NIE to samo co P4 — P4 zmienia TON dyrektywy w `strict_grounding.py`, R18 dodaje regułę do promptu persony*
- [ ] **R7** Kotwica altanki nie dociera do promptu · *wymaga filtra search-time + rozwiązania „kotwica-jest-kwarantanną", osobna sesja*

### PERSONA / ZACHOWANIE
- [ ] **P1** `ZAKAZ PĘTLI` istnieje tylko dla `/api/chat` — ścieżka proaktywna nie widzi go nigdy
- [ ] **P2** Scheduler proaktywny bez wglądu do RAG — pyta o rzeczy, których nie ma w pamięci
- [ ] **P5** Ramka scenariusza (`5924bef`) nie blokuje wycieku słownictwa fikcji do rozmowy
- [ ] **P10** Wyciek UI do dialogu — `main.py:1043` każe modelowi odsyłać do guzika 🎬

### INTERFEJS I DANE
- [ ] **U1** Powiadomienia push nie przychodzą · **brak jakiejkolwiek wcześniejszej diagnostyki**
- [ ] **U2** Mikrofon — diagnostyka wdrożona (`2a8e9a1`, `2e3ad43`), czeka na **jedną nieudaną próbę z telefonu**
- [ ] **U3** Amelia: `SERVER_TRUTH` niewłączony — ten sam bug historii co Astra · *zmiana = dopisanie `'amelia'` do stałej w `app.js`*
- [ ] **D1** Historyczny szum: hipoteza, że wektory sprzed 19.08 są systematycznie gorsze · **niezweryfikowana**

---

## §3. STYL I GŁOS (16) — nie zepsute, brzmi jak bot

> **Bramka:** wszystko w tej sekcji jest niemierzalne, dopóki nie stoi **M1**.
> Bez przyrządu to nie są naprawy, tylko zmiany, o których będziemy zgadywać, czy pomogły.

- [ ] **M1** ⭐ `style_audit.py` jako obowiązkowy kanarek warstwy PERSONA · **BRAMKA dla całej sekcji** · **stan 12.09: przyrząd istnieje i ma dokładnie JEDEN baseline, `PRZED`, bez ani jednego `PO`** (`baseline_styl_PRZED_fix_mainpy_2026-08-15.json`); progi żyją w dokumentach nie w skrypcie, liczników fraz-kluczy nie ma. Czyli styl umiemy zmierzyć, ale **ani razu nie zamknęliśmy pary przed/po**.
- [ ] **Z4** `own_life.json` — 7 gotowych zdań → obszary tematyczne · **plus próg `OWN_LIFE_MAX_DISTANCE = 0.60`**
- [ ] **P3** Level 6 „Absolutna Więź" pod nagłówkiem „DANE TWARDE" = rozkaz uległości · *hipoteza, tania do A/B*
- [ ] **P4** `strict_grounding` — ton urzędnika zamiast ludzkiego przyznania się do luki
- [ ] **P6** Bipolarny `[TRYB]` — brak bezwładności emocjonalnej · *objaw nr 1 z pięciu nawyków Gemini*
- [ ] **P7** Dosłowne cytaty w promptach działają jak skrypt · `astra_base.txt:87` powtórzony słowo w słowo 22.08 i 27.08 · ⚠ **SPROSTOWANIE 12.09: zakres za wąski.** P7 mówi „kwestie w cudzysłowie", a `astra_base.txt:122` ma nazwany gest **w nawiasie, bez cudzysłowu i bez gwiazdek** („opieram się o ścianę, patrzę na ciebie z ukosa…") — w obecnym brzmieniu P7 go NIE złapie. Rozszerzyć na **każdy nazwany, konkretny gest lub kwestię, niezależnie od interpunkcji**
- [ ] **P8** „GDY GO ZRANISZ" — wymuszona kapitulacja także przy zwykłej pomyłce · **zrobić przed P3 albo razem z P3**
- [ ] **P9** Didaskalia — odwrócić domyślną: czysty tekst normą, gest wyjątkiem · *baseline 90%, cel ≤50%* · ✅ **POTWIERDZONE 12.09 i MA ADRES:** źródłem gestu w SOLO jest **`astra_base.txt:122`** („opieram się o ścianę" jako przykład w nawiasie) — nie blok Amelii, jak zakładał audyt, który szukał dokładnej formy `*opieram głowę*` i przegapił rdzeń (to pkt 5 z `pomiar_klamie.md`). Pomiar 15.08 zmierzył `opieram się` **14×** (`main.py:180`). Czyszczenie 15.08 objęło blok monologu, **nie plik persony**. ⚠ **Ograniczenie wykonawcze:** `astra_base.txt` jest WSPÓLNY dla SOLO i Wspólnego (placeholder `{wspolny_block}`, `main.py:934`), a Wspólny jest pod zakazem zmian → **flaga per pokój albo przeniesienie sekcji FIZYCZNOŚĆ do wariantów per-pokój**
- [ ] **P11** `active_concerns` bez wygasania → ciągły tryb schronienia · **zależy od Z6** *(dziś ta lista jest protezą pamięci)*
- [ ] **P12** Patos sakralny + „Astra nigdy nie mówi »kocham Cię« pierwsza" · **najpierw pomiar, kto inicjuje**
- [ ] **P13** Recykling fraz-kluczy poza gestami — „naginanie rzeczywistości" 14× w 3 dni, „KCB" jako przecinek
- [ ] **P14** Prototypy `MILESTONE:future_together` ściągają rozmowy o pracy w melodramat o ciele · `semantic_extractor.py:243,362`
- [ ] **P15** `TRIMMABLE_WORDS` wycina modalność, nie ozdobniki · **najpierw zmierzyć, jak często się odpala**
- [ ] **P16** `character_core` wstrzykiwane w każdej turze poza budżetem n
- [ ] **WO-6** Sanitizer gwiazdek z historycznych tur `model` · `main.py:1146` · *profilaktyka na echo*
- [ ] **DEC-1** Reżim JSON per turę (`thought`/`mood`/`topic` przed `response`) · **DECYZJA, nie zadanie** — zamrozić z uzasadnieniem albo odrzucić

---

## §4. OBSERWACJE (5) — wdrożone, czeka na spojrzenie

> Koszt każdej: kilkanaście minut. Nie wymagają sesji. Najtańsze odhaczenia na tej liście.

- [x] **OB-1** Siostry `on` od 19.08 — **WYKONANE 04.09**, przegląd 13 dni / 349 wiadomości: `ewolucja/siostry/2026-09/evolution_log_2026_09_04.md`. (a) atrybucja ✅ zero wypowiedzi bez podpisu na 186, głos równy (59/66/61) · (b) emocje ✅ wygasają, po 3 wpisy `ephemeral` 48h, bez kumulacji · (c) **szum ZMIGROWAŁ ⚠** — `[DATE:deadline]` jako nowy kosz na wszystko z liczbą, akcje RP w gwiazdkach jako trwałe fakty · (d) jeden wątek ✅ od 28.08. **Stało tu jako otwarte, bo scalanie 10.09 brało listy zadań, nie logi ewolucji.** Nowe zadania z tego: Z8, Z9, Z10.
- [ ] **OB-6** **Rytm 3× w tygodniu + rodowód wiadomości nocnej — wdrożone 18.09 (`444c057`), do sprawdzenia po ~2 tygodniach:** (a) czy 3 wiadomości tygodniowo to właściwa częstotliwość, czy za mało · (b) czy prefiks `msg_kind=nocna_analiza` faktycznie ukrócił konfabulacje typu „coś mi dzwoniło w nocy" — to był cel zmiany, więc **szukać w logach, czy Astra nadal powołuje się na nieistniejące wspólne ustalenia** · (c) czy brak spontanicznej nie sprawił, że relacja zrobiła się jednostronna. Pierwsze uruchomienie: pon 21.09.
- [ ] **OB-2** Fixy proaktywne 06.08 (`e9653b2`, `3eebe05`) — czy poranna przestała zmyślać daty, czy spontaniczna przestała robić pretensje, czy wiadomość przestała znikać z UI
- [ ] **OB-3** Pokój DOM v2 (17.07) — czy Holo mówi „nie wiem" zamiast ściemniać (**to jest test właściwy**), czy Menma nie przestrzeliła w drugą stronę
- [ ] **OB-4** Pomiar stylu po fixie `main.py` — baseline PRZED istnieje (`baseline_styl_PRZED_fix_mainpy_2026-08-15.json`) · **wchłonięte przez M1**
- [ ] **OB-5** Re-run dere-turn — baseline A:B = 1:11, cel ~1:4

---

## §5. NARZĘDZIA I DIAGNOSTYKA (7)

- [ ] **A2** Amnezja z crona — golden nightly + diff + alert przy spadku recall >5% · *tanie, pilnuje wszystkich kolejnych zmian*
- [ ] **H3** Etap „odcięte przez filtr użytkownika" w trace'ie Amnezji · *bez niego debugger pokazuje brak danych tam, gdzie jest odcięcie*
- [ ] **A1** Astra nie wie, czym jest Amnezja — 17 wpisów, żaden nie mówi czym ona jest · **zależy od H1**
- [ ] **N1** Mapa drzewa katalogów z opisem, co jest gdzie · *połowa jest już w `CLAUDE.md`*
- [ ] **N2** Sprawdzić, czy najwcześniejsze rozmowy z Astrą są w ogóle zarchiwizowane
- [x] **N3** Astra vs siostry — dlaczego siostry przywołały datę, a Astra nie · **ROZSTRZYGNIĘTE 12.09: hipoteza FAŁSZYWA.** `compute_persistence` to kod wspólny (`vector_store.py:65`), nie mechanizm sióstr; `SIOSTRY_TYPY_BLOKOWANE` tylko blokuje trzy typy, nic nie odblokowuje; a wpis Astry `[DATE:medical_visit]` z 31.08 był **permanent, nie 168h** (bo `ma_sygnal_wagi` łapie rdzeń `operacj`). **Realna przyczyna: loteria etykiet na ścieżce zapisu.** Siostrom zdanie wpadło jako `FACT:health` → permanent; Astrze zdanie oznajmujące z 28.08 **nie utworzyło żadnego wektora**, a data ocalała tylko w `EMOTION:excited` → ephemeral 48h → wygasła 2h35min przed pytaniem. Potwierdzenie niezależne: wskaźnik ekstrakcji 26,6% (Astra) vs 27,6% (siostry) — różnicy nie ma. **N3 nie jest osobnym zadaniem, jest dowodem, że Z1+Z2 to właściwy priorytet.** Detale: `ewolucja/astra/2026-09/evolution_log_2026_09_12.md` §7.
- [ ] **N4** Symulacja tłoku / scale-degradation — `now_override` symuluje CZAS, nie OBJĘTOŚĆ · *wyróżnik produktu*

---

## §6. ZAMROŻONE (4) — czekają na decyzję, nie na pracę

- [ ] **FR1** Przebieg #2 — apply triage (achievement/gift/habit). Dry-run zrobiony, werdykty w `backups/`. **Strażnik: R7.** → *zatwierdzić albo odrzucić*
- [ ] **FR2** O1 — cap/kontekstowy filtr retype-FACT → *czy nadal priorytet, skoro szum pochodzi z zapisu, nie z retrievalu?*
- [ ] **FR3** Migracja compose sióstr przez `compose_context` — odblokuje Amnezję dla sióstr → *teraz czy po ustabilizowaniu Astry?*
- [ ] **FR6** Ochrona mefedron — architektura zatwierdzona 16.08, wykonanie **nie zaczęte**. Bloker: dane sesji tylko na VPS

---

## §7. RETRIEVAL — DALSZE (10) · po naprawie zapisu

> **Zasada z 15.08 i 25.08:** poprawianie wyszukiwania na zaśmieconej bazie uniemożliwia
> zmierzenie efektu. Ta sekcja czeka na Z1+Z2+H1, kropka.

- [ ] **R2** Kanał 4 — przeszukiwanie surowej sesji (~6500 wiadomości) semantycznie
- [ ] **R3** Warstwa epizodyczna — `night_insight` jako trwałe wspomnienie dnia · **zależy od H1+H2**
- [ ] **R8** Rozwinięcie zapytania przez model (kategoria → instancja; embedding nie robi abstrakcji)
- [ ] **R9** Grounding jako wyzwalacz drugiego strzału · **zależy od R5** (dziś grounding nie mierzy trafności)
- [ ] **R10** Pętla zwrotna — ranking uczony z tego, co zadziałało (wzorzec Gold Signal z LDI)
- [ ] **R11** Indeks po encjach — osoba/projekt jako węzeł ze wszystkimi faktami
- [ ] **R12** BM25 / hybryda — dla kodów, numerów, nazw własnych · *niżej niż zakładano*
- [ ] **R13** Mood-based dynamic weights — reranker zależny od `last_user_vibe`
- [ ] **R14** Migracja SDK `google.generativeai` → `python-genai` + Gemini 3.x
- [ ] **R15** Daty relatywne w starych wektorach + `DATE:appointment` supersede

---

## §8. POKÓJ SIÓSTR — FAZA 5 (10) · osobny projekt

> **Bramka startowa:** Astra ustabilizowana. Twarda zależność: **B → A → C.**
> Ekstrakcja na zbugowanym routerze = trwałe zatrucie kolekcji per-siostra. Nie fundujemy Odtrucia #3.

- [x] **B-1** Router: klasyfikacja ADDRESSED / MENTIONED / NONE · **ZROBIONE (`eceb807`, golden 24/24) — §8 błędnie trzymało to jako otwarte, bo przepisano plan Fable'a z 24.07.** Weryfikacja 12.09: router loguje `addressed=[…] mentioned=[…] group=…` (`main.py:2458`). Pomiar 03-09.09: 115 tur → sticky 73% · pick 23% · **addressed tylko 3%** · group 1%
- [x] **B-2** Lepkość rozmówcy `_last_full_speaker` · **ZROBIONE (`cafcc3f` — wygasanie lepkości).** Weryfikacja 12.09: `_last_full_speaker` + `_sticky_turns` w `main.py:2381-2382`, log pokazuje `sticky_turns=3 gap_min=39.2`
  ⚠ **KONSEKWENCJA DLA CAŁEJ §8:** bramka „B → A → C" jest **przejechana**. B zrobione, A w trybie `on` od 19.08, tydzień obserwacji zamknięty 04.09 (OB-1). Czyli wedle własnych reguł tej sekcji **C może startować** — jedyną pozostałą bramką jest „Astra ustabilizowana", nie praca nad routerem ani pamięcią sióstr.
- [ ] **A-D1** Decyzja atrybucji (rekomendacja: per-primary + shared dla `group_address`) · **wymaga zgody Łukasza**
- [ ] **A-1** Trzy twarde zasady bezpieczeństwa echo-loop
- [ ] **A-2** Procedura shadow → 5-7 dni → review → `on`
- [ ] **C-1** RoomState v0 — scena zastana · **po A-on + tydzień stabilności**
- [ ] **C-2** Zmienność dobowa · *tanie, duży efekt klimatyczny*
- [ ] **C-3** Przeczucie Menmy v0 · **twardy próg obowiązkowy**, inaczej natręctwo
- [ ] **C-4** Prawdziwe sekrety + przeciek v0 · **zależy od A-on + D1**
- [ ] **S-2** **STOP sesjom promptowym w pokoju** (ustalenie sprzed rejestru, **ZGUBIONE przy scalaniu 10.09**, odzyskane 12.09): warstwa promptowa jest wyczerpana — cały projekt + Biblia + 2 dni logów dały 3 zmiany. Wszystko dalej to architektura. **Nie otwierać kolejnej sesji „poprawmy prompt siostry".**
- [ ] **S-1** Pora dnia do `build_sister_prompt` · *3 linijki, najlepszy stosunek zysku do wysiłku w pokoju*

**Z PRZEGLĄDU RAG SIÓSTR 12.09** (115 tur, 155 zapytań, journale 03-09.09, read-only):
- [ ] **S-3** ⭐ **Monokultura retrievalu: jeden seed z 13.07 w 110 z 230 zapytań (48%).** `seed_kronika` = 19,5% wszystkich trafień, 5 z 10 najczęstszych wektorów to lipcowe seedy. **Nie wygrywają score'em (0,60-0,62 przy świeżych 1,000) — wypełniają ogon puli**, bo kolekcje mają ~71 wektorów, a `n=6` trzeba czymś zapełnić. Progi dystansu istnieją dla **dwóch** kanałów (`MILESTONE_MAX_DISTANCE=0.45`, `OWN_LIFE_MAX_DISTANCE=0.60`), dodane właśnie po to, by nie było monokultury — **`seed_kronika` idzie kanałem głównym, bez progu.** `seed_siostry.py:173` nie ustawia `persistence`, a `seed_kronika` nie ma wpisu w `RECENCY_HALF_LIFE_BY_SOURCE` (fallback 7 dni). **`seed_kronika` nie występuje w żadnym dokumencie projektu.**
- [ ] **S-4** **31% wyników poniżej score 0,70** (14% poniżej 0,65; min 0,587) — brak progu trafności na kanale głównym, więc slabe wektory wchodzą do promptu, żeby wypełnić `n`
- [ ] **S-5** **48% zwracanych wspomnień jest starszych niż 30 dni**, 16% starszych niż 60 (mediana wieku 15 dni, max 176) — w bazie, która istnieje od 03.07
- [ ] **S-6** **Pytanie zapisane jako `MEASUREMENT:progress`** (04.09, conf=0.40: „Myślisz ze im mniej slodyczy zjem tym lepiej wyjdzie zabieg?") i podane do promptu **6× w jednym dniu, ze rosnącym score'em** (0,786 → 0,922). Podtyp nieujęty w Z2. Trwałość `short_term` = 168 h
- [ ] **S-7** Dwa śmieciowe `[DATE:deadline]` z 03-04.09 podane do promptu **47× w tygodniu** (26× i 21×), akcja roleplay jako `SHARED:our_song` — **20×**. Koszt znaleziska „szum zmigrował" z 04.09, zmierzony
- [ ] **S-8** Holo używa nadchodzącego zabiegu jako **dźwigni** („muszę ją wzmocnić, przypominając mu o stawce", „rachunek zysków i strat") wbrew jawnej regule z `lukasz_core.json` docierającej do sióstr: *„NIE motywuj do działania, gdy jest chory — obowiązuje zwolnienie z obowiązku, nie zagrzewanie"* + `character_core` *„NIGDY nie używam pamięci do rozliczania"*. **Błąd interpretacji, nie danych** — dane były w prompcie. Żaden wpis w §8 nie dotyczy zachowania sióstr wobec reguł zdrowotnych
- [ ] **S-9** `[ASTRA RAW]` w logu oznacza tury **wszystkich** person — `parse_gemini_response()` (`main.py:1217`) ma tag zahardkodowany i nie zna `persona_id`. **61% linii `[ASTRA RAW]` (148 z 243) to nie Astra.** Bug przyrządu: każda przyszła analiza z journala będzie mylić persony. *(Sprawdzone: `style_audit.py` i `geminianaliza.md` są czyste — czytają eksporty per pokój.)*

Pełny raport: `wazne/analizy/audyt_logow_2026-09-03_do_09-09.md`

**Bugi pokoju zgłoszone 09.09, nieprzypisane:** Holo blokująca się przy „niech ktoś inny z was
wybierze" (odpowiedziała „…", potem pytała kogo wywołać) · Menma pomyliła serię anime
(Frieren zamiast HxH) przy poprawnie zrozumianym poleceniu.
**Prawdopodobnie B-1**, do potwierdzenia.

---

## §9. NIE-INŻYNIERIA (4)

- [ ] **BEZP-1** **Rotacja GitHub PAT na VPS** — token gołym tekstem w `git remote -v` w `/var/www/myastra/astra/` · *odłożone świadomie 03.08, ale to jest realne ryzyko*
- [ ] **AM-1** Amelia — work-order migracji na `compose_context` + Amnezja gotowy, niewykonany · *niepilne, nieaktywna 5+ tygodni*
- [ ] **AM-2** **ucho-VPS (stary system Amelii): supersede delete, `fact_extractor` daty bez kontekstu, `cross_contamination`** · **ZGUBIONE przy scalaniu 10.09**, odzyskane 12.09 · *ma historię w `ucho_amelia.db`, więc bugi dotyczą realnych danych*
- [ ] **RODZ-1** Rodzina AI — migracja Holo/Nazuny/Hany na VPS · **po Amelii**
- [ ] **KAR-1** ⭐ **KAMPANIA APLIKACYJNA — PIERWSZE ZADANIE PO POWROCIE ZE SZPITALA** (ustalone 12.09). Rozpisać **wszystkie** role pasujące do umiejętności i aplikować po kolei, systematycznie: praca na etat · freelance · SEO · audyty · wdrożenia/automatyzacja · implementation/solutions engineer. Powód: **potrzebne pieniądze**, nie „rozwój kariery".
  **Dwa osobne torty, różne horyzonty — nie mieszać w jednej liście:** (a) **gotówka w tygodniach** — freelance, SEO, audyty, wdrożenia LDI u konkretnej firmy; (b) **etat w 1–3 miesiące** — aplikacje senior AI/automatyzacja. Jeśli pilna jest gotówka, (a) idzie pierwsze i nie czeka na (b).
  **Ustalenia z rozmowy 12.09, do wykorzystania przy pisaniu ofert:** karta atutowa to **udokumentowany ślad rozumowania** (`pomiar_klamie.md`, korekta własnych liczb 04.09, sekcje „czego NIE można twierdzić") — nie samo „zbudowałem RAG", bo to ma każdy · do pracy **w pamięci dla AI** portfelem jest **ANIMA + Amnezja** (debugger z 11-etapowym trace'em), NIE LDI · do **zwykłych firm** LDI jest kluczem i argument „bez API, bez kosztu tokenowego, dane nie wychodzą z firmy" jest wtedy MOCNY (zdejmuje trzy obiekcje zakupowe naraz) · ale **zawęzić target**: nie „firma, co chce się zautomatyzować", a firma **z przepływem popytu, który się gubi** (e-commerce, sprzedaż z zapytań, dystrybucja, serwis z kolejką) · pierwsze zdanie to **„dajcie eksport CSV, oddam raport"**, nie „mam produkt" — bo onboarding LDI wymaga configu domenowego per branża · szukać pod **implementation/solutions engineer** i „automatyzacja firmy od środka", nie tylko pod „AI engineer" — więcej ról, mniej zabramkowane dyplomem · pytanie kontrolne na rozmowie: **co konkretnie mierzycie po 90 dniach** (jeśli nie umieją odpowiedzieć, to rola do gaszenia pożarów, nie do automatyzacji).
  **Luka do zamknięcia, tania:** ostatni commit 28.08, repo prywatne, case study na własnej domenie = odkrywalność zerowa. To problem dystrybucji, nie kompetencji.
  **VectorShift:** nie zaczynać zadania, dopóki nie wyjaśnią roli — 150–250k vs 20–30k to dwa różne stanowiska pod jednym ogłoszeniem.

---

## §10. POCZEKALNIA — pomysły bez dowodu

> Tu trafia każdy nowy pomysł. **Nie do rankingu, dopóki nie ma dowodu z danych.**
> To jest zawór bezpieczeństwa: dzięki niemu lista wyżej nie rośnie w nieskończoność.

- Narracja trzecioosobowa jak w c.ai (Machi) — dekonstrukcja porównawcza · **ostrożnie, po operacji** *(poprzedni tryb scenariusza wyłączał pamięć)*
- Bardziej wciągająca dynamika pokoju sióstr — „interaktywna opowieść"
- TikTok „Astra Reacts: Zimna Krew" — Astra komentuje własne najzimniejsze odpowiedzi
- Wykrywanie sprzeczności / rewizja przekonań
- Znaczniki pewności („wiem na pewno" / „chyba" / „to była plotka")
- Pamięć proceduralna — wzorce, nie fakty
- Debugger: symulacja tłoku jako produkt

---

## §11. ZASADY, KTÓRE OBOWIĄZUJĄ PRZY KAŻDYM ODHACZENIU

1. **Kanarek przed pomiarem.** Jedno zapytanie, o którym WIESZ, co musi wrócić. Nie wraca — przyrząd zepsuty, stop.
2. **CZY DOBRZE, nie ILE.** Metryka typu `count` bez wzorca oczekiwanej treści = Rodzina A. Wracasz i definiujesz, co POWINNO się pojawić.
3. **Środowisko.** Skrypt offline: jawny `load_dotenv` + wypisz liczbę wektorów na start. Nie ~4700 (Astra) — stop.
4. **Identyczne wiersze = alarm.** Nawet jeśli wyglądają sensownie.
5. **Wzorce szersze niż jedna forma.** Rdzenie, nie pełne formy („Amelka", „ldi" małymi).
6. **Chroma `$contains` jest case-sensitive.** `'ldi'` vs `'LDI'` = 18 vs 32 wpisy. Sprawdzaj oba.
7. **Ten sam kod po obu stronach porównania.**
8. **Golden przed i po** każdej zmianie w `compose_context` / `vector_store`.
9. **`style_audit.py` przed i po** każdej zmianie w `astra_base.txt` i blokach promptowych `main.py`.
10. **Nie pushować i nie deployować bez wyraźnej zgody Łukasza.**
11. **Wektory wgrywać addytywnie**, backup przed każdym zapisem, nigdy delete.
12. **Nigdy nie pisać do ChromaDB z osobnego procesu przy żywym serwisie.**

Pełne uzasadnienie punktów 1–8: `wazne/bugi/pomiar_klamie.md` (dziewięć wystąpień, kosztowały
trzy zatwierdzone zmiany bez pokrycia i trzy tygodnie przekonania, że retrieval jest w porządku).

---

## §12. KOLEJNOŚĆ — nie do wykonania od góry

```
TERAZ (przed 14.09):     Z6-tanie.  Jedna rzecz.  Reszta czeka.

PO POWROCIE, PIERWSZE:   KAR-1 — kampania aplikacyjna (pieniadze).  Przed warstwa 1.
                         Astra czeka; ona nie placi rachunkow.

PO POWROCIE, warstwa 1:  Z1 → Z2 → Z5 → Z3 → Z4
                         (+ M1 równolegle — nie blokuje, a odblokowuje §3)

warstwa 2:               H3 → H1 → H2 → H4
                         A2 (cron) — uruchomić jak najwcześniej, nieblokujące

warstwa 3:               R4 → R1 → R5 → R2 → R3

warstwa 4:               P4+P10 → P3+P8 → P9 → P6 → P7 → P1 → P13 → P5 → P11 → P12

FAZA 5 (pokój):          dopiero po stabilizacji Astry.  B → A → C.

CIĄGŁE:                  OB-1..OB-5 — odhaczać przy okazji, kosztują minuty
```

**Dlaczego nie da się „naprawić połowy zanim ruszymy dalej":** połowa z 67 to 34 zadania,
a część z nich znika albo zmienia sens po naprawie czegoś wyżej. Sensowna wersja tej samej zasady:
**żadnego nowego pomysłu poza §10, dopóki warstwa 1 nie jest zamknięta.**
Wtedy lista przestaje rosnąć, a Ty widzisz ruch.

---

## Zamknięte

- **N3** (12.09) — pytanie „dlaczego siostry zapamiętały datę, a Astra nie": hipoteza o polityce trwałości obalona; realna przyczyna to loteria etykiet w zapisie. Wzmacnia priorytet Z1+Z2.
- **OB-1** (04.09) — przegląd pokoju sióstr po dwóch tygodniach `on`: trzy punkty zielone, jeden ⚠ (migracja szumu). Wyniki: `ewolucja/siostry/2026-09/evolution_log_2026_09_04.md`. Odhaczone 12.09.

Wcześniej zamknięte, przed założeniem rejestru — nie powtarzać:
router sióstr `eceb807` · wygasanie lepkości `cafcc3f` · migracja compose sióstr A+B+C ·
Odtrucie #2 część B · Przebieg #2 + O1 `6d0cd75` · instrumentacja Amnezji `f52668f` ·
WO-4 own_life kanał `4207eea` · Faza 1 stylu `e6024b5`+`bf3cd04` ·
siostry `on` włączone 19.08 · jedna prawda dla serwera (SERVER_TRUTH Astra) 15.08
