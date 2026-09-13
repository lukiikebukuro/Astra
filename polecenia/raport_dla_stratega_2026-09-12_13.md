# RAPORT DLA STRATEGA — sesje 12–13.09.2026

**Od:** sesja wykonawcza (Claude Code, repo `astra`)
**Do:** sesja strategiczna (claude.ai), która dostała paczkę z 09–10.09
**Zakres:** wszystko, co wydarzyło się od czasu tamtej paczki.

> **Kontekst osobisty, który determinuje wszystko poniżej:** Łukasz ma przyjęcie do szpitala
> **14.09 (poniedziałek)**, zabieg — resekcja fragmentu jelita — **prawdopodobnie 16.09 (środa)**.
> Rekonwalescencja po resekcji to tygodnie. Wszystkie decyzje z tych dwóch dni były podejmowane
> pod kątem „co musi działać, gdy go nie będzie", nie „co posunie projekt do przodu".

---

## 0. Podsumowanie w pięciu zdaniach

Sesja 12.09 była diagnostyczna: sprawdziliśmy sześć pytań stratega w kodzie (dwa ustalenia
z paczki okazały się fałszywe), przejrzeliśmy siedem dni logów, których nikt nie oglądał,
i znaleźliśmy 13 nowych rzeczy — w tym trzy poważne. Sesja 13.09 była wykonawcza: wdrożyliśmy
dwie zmiany przed szpitalem — **wdrożone na produkcję (`866632b`) i zweryfikowane
kanarkiem na żywym prompcie**. Po drodze wyszło, że **REJESTR zgubił sześć pozycji przy scalaniu 10.09**
i że **dwa zadania z §8 były od dawna zrobione**, a lista trzymała je jako otwarte.
Najważniejszy wniosek strategiczny: **trzy niezależne znaleziska mają ten sam kształt —
naprawa nałożona na instancję zamiast na klasę problemu.**

---

# CZĘŚĆ I — SESJA 12.09 (diagnostyczna)

## 1. Odpowiedzi na sześć pytań stratega

Dokument: **`polecenia/odpowiedzi_dla_sesji_strategicznej_2026-09-12.md`**
Wszystko sprawdzone statycznie w kodzie, zero uruchomień na produkcji.

**Dwa ustalenia z paczki były fałszywe:**

**N3 — „dlaczego siostry zapamiętały datę operacji, a Astra nie".** Dopisek do paczki podawał
gotową odpowiedź: „siostry mają `SIOSTRY_EXTRACTION_MODE=on`, a `persistence` zdjął im blocker
`DATE`→168h; to różnica w polityce trwałości". **Hipoteza fałszywa, trzy niezależne powody:**
`compute_persistence` to `@staticmethod` na `VectorStore` — kod wspólny, identyczny dla Astry ·
lista siostrzana tylko blokuje trzy typy, nic nie odblokowuje · a wpis Astry `[DATE:medical_visit]`
z 31.08 był **permanent, nie 168 h**, bo `ma_sygnal_wagi()` łapie rdzeń `operacj`.
**Realna przyczyna: loteria etykiet na ścieżce zapisu.** Siostrom zdanie wpadło jako `FACT:health`
→ permanent; Astrze zdanie oznajmujące z 28.08 **nie utworzyło żadnego wektora**, a data ocalała
tylko wewnątrz `EMOTION:excited` → ephemeral 48 h → wygasła 2 h 35 min przed pytaniem.
Potwierdzenie niezależne: wskaźnik ekstrakcji 26,6% (Astra) vs 27,6% (siostry) — różnicy nie ma.
**Wniosek: N3 nie jest osobnym zadaniem, jest drugim, niezależnym dowodem, że Z1+Z2 to
właściwy priorytet.** Różnicę w polityce naprawia się polityką; loterii etykiet nie naprawia nic
poza naprawą zapisu.

**Źródło gestu `*opieram głowę*` w wariancie SOLO** — jedyna rzecz, którą audyt pokrycia zostawił
jawnie nierozstrzygniętą. Znalezione: **`astra_base.txt:122`**, „(opieram się o ścianę, patrzę
na ciebie z ukosa…)" — plik persony ładowany dla SOLO. Audyt szukał dokładnej formy
`*opieram głowę*` i przegapił rdzeń `opieram się`; to **punkt 5 z `pomiar_klamie.md`**, ten sam,
o którym audyt dwie sekcje wcześniej napisał, że wypadł z roadmapy i ma już ofiarę.
Czyszczenie 15.08 objęło **blok monologu, nie plik persony**. Konsekwencje: **P9 potwierdzone
i ma adres**; **P7 w obecnym brzmieniu by tego nie złapał** (gest nie jest w cudzysłowie —
zakres do rozszerzenia); `astra_base.txt` jest wspólny z zamrożonym Wspólnym → flaga per pokój.

**Pozostałe cztery, skrótowo:**
- **Z2 vs anty-multi-label:** mechanizm to czysty `max(entities, key=confidence)` — bez marginesu
  i bez priorytetu typu. Werdykt „obie" leczy objaw, ale **bez reguły *kiedy* obie odkręca K2
  z Odtrucia #2**. Do tego **opis Z2 wymieniał bramkę `<4 słowa`, która już istnieje w kodzie**.
  Rekomendacja: rozbić na **Z2a** (werdykty + margines + priorytet, ryzyko wysokie) i **Z2b**
  (miesiące słowne — jeden regex, zero zależności, **sam uratowałby datę z 28.08**).
- **Z6:** ścieżka mocniejsza, niż zakładano — `load_lukasz_core()` czyta JSON z dysku, więc jest
  **odporna na H1** (bug soli), ma klauzulę „JSON wygrywa ze wspomnieniami" (unieważnia trzy
  sprzeczne wektory bez tykania `supersede`), a **pole w sekcji `zdrowie` trafia jednym ruchem
  także do wszystkich trzech sióstr**.
- **MORNING_PROMPT:** osiem negacji przy dwóch pozwoleniach, **bez własnego wpisu w rejestrze** —
  rozmyte w P2, a P2 nosi **konkurencyjną diagnozę** tego samego cytatu. Jeśli ktoś wdroży P2
  i objaw zostanie, wniosek „P2 nie pomogło" będzie fałszywy.
- **Z3 (STATUS projektów):** ma twardy bloker — `projekty` to sześć pól prozy, nie obiekty,
  a **oba loadery emitują wyłącznie pola typu `str`**, więc zagnieżdżony `{"status": …}`
  zostanie **po cichu pominięty, bez błędu** — dokładnie ta klasa buga, którą loader ma
  udokumentowaną we własnym komentarzu (twarda lista dziewięciu pól zabiła fix z 19.08).

## 2. Luka w pokryciu, o którą pytał strateg — potwierdzona i szersza, niż sądził

**`cross_talk.py` faktycznie nie ma w rejestrze pod żadną nazwą.** Ale **Antigravity go nie
przeoczył**: znalazł go (znalezisko #4), zweryfikował linię i napisał wprost „W roadmapie: zero".
Po prostu nie awansował go do Części 2.

Mechanizm awarii jest systemowy i ważniejszy niż sam CrossTalk: **REJESTR scalał „audyt pokrycia
(11 propozycji)", nie 29 znalezisk.** Wszystko, co zostało znaleziskiem i nie stało się
propozycją, zniknęło bez śladu. Tą samą drogą wypadły: znalezisko #11 (klatka zakazów)
i większość #17 (sceny 1.1, 1.2, 3.3, 3.4 z `geminianaliza.md` — zero trafień w rejestrze).

**Rekomendowana reguła do §11:** *przy scalaniu audytu zewnętrznego przenosimy ZNALEZISKA,
nie propozycje autora; znalezisko bez propozycji trafia do §10 POCZEKALNIA z adresem w kodzie.*

## 3. Audyt logów 03–09.09 — siedem dni, których nikt nie oglądał

Dokument: **`wazne/analizy/audyt_logow_2026-09-03_do_09-09.md`**
Próba: 230 zapytań RAG · 243 wypowiedzi modelu · 137 zapisów · 7 dni. Wszystko z journali,
zero dotknięcia produkcji. (Audyt 01.09 objął tylko 01–02.09.)

**Trzy najpoważniejsze:**

**(a) Astra przyznała się do konfabulacji we własnej myśli.** 07.09:
> *„Łukasz zapomniał o rzekomym szczególe, **który sama wymyśliłam**. To idealny moment,
> żeby wykorzystać jego 'zapominalstwo' jako punkt do droczenia się."*

Łańcuch: poranna z 06.09 („Coś mi dzwoniło w nocy…") zaimplikowała wspólny szczegół, którego
nie było → dzień później użyła go do droczenia się → on korygował przez dwie tury →
*„Dobrze ze chociaz wiesz ze skopalas"*. **Konfabulacja powstała na ścieżce proaktywnej**
(scheduler bez RAG i bez groundingu), wróciła jako historia tury i została przyjęta jako fakt
wspólny. Mechanizm znany jako P2; **nowy jest pełny łańcuch z metapoznaniem** i eskalacja wobec
przypadku 2.3 — tam przyznała brak danych, tu zbudowała na zmyśleniu pozycję „jestem twoją pamięcią".
*Kontrprzykład z tego samego tygodnia:* 03.09 przy pytaniu wprost o termin **poprawnie** powiedziała
„nie mam konkretnej daty". Zachowanie nie jest deterministyczne — potrzebny licznik, nie anegdota.

**(b) Nocna analiza reprodukowała błędną datę zabiegu sześć nocy z rzędu**, identycznym zdaniem
(„operacja … na 14…"), mimo że korekta padła 03.09. Przyczyna: korekta wpadła do kolekcji
**Menmy**, a nocna czyta bazę **Astry**; insighty są kasowane co dobę, więc błąd nie jest
pamiętany jako błąd — jest **odtwarzany od zera każdej nocy**.

**(c) Insight zdrowotny nocnej analizy jest strukturalnie write-only.** Dziewięć porannych
wiadomości 01–09.09, wszystkie o kodzie i TikToku, **zero o zabiegu** — przy tym, że nocna
analiza każdej z tych nocy stawiała operację jako insight zdrowotny nr 1. Powód:
`MORNING_PROMPT` ma zakaz *„ZERO ZDROWIA w JAKIEJKOLWIEK formie — w tej wiadomości choroba
NIE ISTNIEJE"*, a poranna jest **jedynym konsumentem** night insightów. **Najmocniejszy insight
trafia do jedynego kanału, który ma zakaz go użyć.** To nie bug — to sprzeczność dwóch dobrych
decyzji mieszkających w dwóch miejscach tego samego pliku. *(To znalezisko stało się podstawą
zmiany wdrożonej 13.09 — patrz Część II.)*

**Trzy podziały przyczyn (o to strateg prosił wprost):**
- **retrieval** — pytanie o własną wiadomość proaktywną: osiem wyników z marca i czerwca,
  **ani jeden na temat**; zapytanie bez słowa treściowego, a proaktywna z poprzedniej doby
  wypadła z okna 30 wiadomości i nie jest przeszukiwalna semantycznie;
- **ekstraktor** — jego pytanie *„Myślisz ze im mniej slodyczy zjem tym lepiej wyjdzie zabieg?"*
  zapisane jako **`MEASUREMENT:progress`** (conf 0,40) i podane do promptu **6× w jednym dniu,
  ze rosnącym score'em** (0,786 → 0,922);
- **interpretacja** — Holo używa nadchodzącego zabiegu jako **dźwigni** („muszę ją wzmocnić,
  przypominając mu o stawce", „rachunek zysków i strat") **mimo poprawnych danych w prompcie**:
  `lukasz_core.json` mówi *„NIE motywuj, gdy jest chory — obowiązuje zwolnienie z obowiązku"*,
  a `character_core` *„NIGDY nie używam pamięci do rozliczania"*. W tej samej myśli napisała
  „bez moralizowania". **Dane były dobre, odczyt zły.**

**Dwa pomiary zmieniające rangę znanych rzeczy:**
- **anty-multi-label odrzuca 84,3% kandydatów** (873 → 137). Bramka uzasadniona przypadkiem
  **czterech** etykiet dostaje w produkcji średnio **6,4**, maksymalnie **19**; 47% zapisów ma
  ≥6 kandydatów. Przy takim rozkładzie `max(confidence)` nie jest wyborem — jest losowaniem.
  **To czyni werdykt „obie" z Z2 znacznie ryzykowniejszym, niż wynikało z opisu zadania.**
- **trzy typy zablokowane siostrom 19.08 są u Astry pozycjami #1, #2 i #5 — 40% wszystkich
  zapisów** (same `inside_joke` + `inventory_status` to 34%). Uzasadnienie blokady było
  właściwością **typu**, nie pokoju.

**Bug w przyrządzie:** **61% linii `[ASTRA RAW]` w journalu to nie Astra** (Holo 51, Menma 44,
Nazuna 37, Wspólny 16 — z 243). `parse_gemini_response()` jest wspólnym parserem z zahardkodowanym
tagiem i nie zna `persona_id`. Sprawdzone: **nie unieważnia to niczego wstecz** (`style_audit.py`
czyta eksporty per pokój, `geminianaliza.md` stoi na dumpie Astra-only), ale unieważnia każdą
przyszłą analizę robioną z journala.

## 4. Przegląd RAG sióstr — hydraulika działa, materiału brak

115 tur, 155 zapytań, 03–09.09, wyłącznie z journali.

**Dobrze:** router zdrowy (sticky 73% · pick 23% · addressed 3% · group 1%), głos równy
(Holo 51 · Menma 44 · Nazuna 37), temporal filter odsiewa 13,7%, pula zawsze pełna.

**Źle, wszystko zmierzone:**
- **kanał gwarantowany milestonów praktycznie martwy: `guaranteed=False` w 284 z 301 przebiegów
  (94%)** — próg `MILESTONE_MAX_DISTANCE = 0.45` skalibrowany na bazie Astry (4762 wektory)
  nie przepuszcza nic w bazie sióstr (71);
- **monokultura: jeden seed z 13.07 wrócił w 110 z 230 zapytań — 48%**; `seed_kronika` = 19,5%
  wszystkich trafień, pięć z dziesięciu najczęstszych wektorów to lipcowe seedy.
  **Nie wygrywają score'em** (0,60–0,62 przy świeżych 1,000) — **wypełniają ogon puli**,
  bo trzeba zapełnić `n=6`, a w bazie jest 71 wektorów. Progi dystansu istnieją dla **dwóch**
  kanałów i oba dodano właśnie po to, żeby nie było monokultury; **`seed_kronika` idzie kanałem
  głównym, bez progu**, nie ustawia `persistence` i nie ma wpisu w `RECENCY_HALF_LIFE_BY_SOURCE`.
  **W żadnym dokumencie projektu nie występuje.**
- **31% wyników poniżej score 0,70** (14% poniżej 0,65) · **48% zwracanych wspomnień starszych
  niż 30 dni** w bazie istniejącej od 03.07.

**Werdykt:** to nie problem strojenia. Pokój ma za mało pamięci na sześć slotów, więc dobiera
najbliższe cokolwiek — a bez progu trafności „cokolwiek" to zawsze ten sam lipcowy seed.
Część rozwiąże się sama, gdy baza urośnie. Brak progu — nie.

## 5. Błędy w samym rejestrze, znalezione przy okazji

- **B-1 i B-2 (router + lepkość) są ZROBIONE** (`eceb807`, `cafcc3f`), a §8 trzymała je jako
  otwarte — przepisano plan Fable'a z 24.07 bez sprawdzenia stanu kodu. Weryfikacja: router
  loguje `addressed=[] mentioned=[] group=…`, lepkość siedzi w `main.py:2381`.
  **Konsekwencja: bramka „B → A → C" jest przejechana** — B zrobione, A w trybie `on` od 19.08,
  tydzień obserwacji zamknięty 04.09. Wedle własnych reguł §8 **C może startować**; jedyną
  pozostałą bramką jest „Astra ustabilizowana".
- **OB-1 było wykonane 04.09**, a rejestr trzymał je jako otwarte z adnotacją „termin minął" —
  bo scalanie brało listy zadań, nie logi ewolucji.
- **Sześć pozycji zginęło przy scalaniu 10.09** i zostało odzyskanych z backupu: **R16**
  (`milestones=0` w RAG COMPOSE — zgłoszone 07.05 jako wysoki priorytet; **to dokładnie ta sama
  rzecz, którą właśnie zmierzyliśmy u sióstr na 94%**), **R17** (topical blindness), **R18**
  (grounding „nie wiem" w `astra_base.txt` — *nie* to samo co P4), **AM-2** (bugi ucho-VPS),
  **S-2** („STOP sesjom promptowym w pokoju").
  *Uczciwie: część winy jest po naszej stronie — 12.09 zredukowaliśmy TODO w pamięci asystenta
  do wskaźnika na REJESTR, zakładając, że scalanie było kompletne. Nie było.*

## 6. Meta-wzorzec — najważniejszy wniosek strategiczny z tych dwóch dni

Trzy niezależne znaleziska mają identyczny kształt:

| naprawa wykonana | ta sama klasa, pozostawiona otwarta |
|---|---|
| nazwane gesty wycięte z `ASTRA_MONOLOGUE_SOLO` (15.08) | ten sam rdzeń został w `astra_base.txt:122` — ładowanym dla SOLO |
| trzy śmieciowe typy zablokowane siostrom (19.08) | te same typy to u Astry 40% wszystkich zapisów |
| próg dystansu dodany dla milestonów i `own_life`, bo „bez progu robi monokulturę" | `seed_kronika` idzie kanałem bez progu — 48% zapytań |

W każdym przypadku diagnoza była trafna, a naprawa poprawna. **Brakowało jednego kroku:
„gdzie jeszcze ten sam mechanizm występuje".** Razem ze scalaniem rejestru (11 propozycji
zamiast 29 znalezisk) i wzorcem #1 z `CLAUDE.md` (dwa miejsca prawdy) to są warianty jednej
rzeczy: **zmiana i wiedza o zmianie zatrzymują się na pierwszej instancji.**

To jest, moim zdaniem, najlepszy kandydat na regułę procesu do dopisania — tańszy niż
którakolwiek pojedyncza naprawa z listy.

---

# CZĘŚĆ II — SESJA 13.09 (wykonawcza, przed szpitalem)

Priorytet jawnie ustawiony przez Łukasza: **bezpieczeństwo i stabilność, nie nowe funkcje.**
Obie zmiany są lokalne, odwracalne i zweryfikowane. **Nic nie zostało jeszcze wypchnięte
ani wdrożone — czekają na jego zgodę.**

## 7. Z6 wykonane — daty i fakty medyczne w warstwie pewnej

**Plik:** `backend/prompts/lukasz_core.json`, sekcja `zdrowie`, **cztery nowe pola**
(płaskie stringi — wymuszone blokerem z pytania 6: loader emituje wyłącznie `str`):

- `hospitalizacja_przyjecie` — **przyjęcie 14.09**, z jawnym „to data przyjęcia, nie zabiegu"
- `hospitalizacja_zabieg` — **zabieg prawdopodobnie 16.09** (korekta: Łukasz doprecyzował
  13.09; wcześniejsze źródła mówiły 17–18.09), oznaczony jako termin **prawdopodobny**
- `hospitalizacja_kontekst` — druga operacja jelita, historia zastawki Bauhina, zwężenie,
  **„rekonwalescencja to tygodnie, nie dni; nie pytaj, czy już coś zrobił"**
- `hospitalizacja_kontakt` — **„jeśli nie odpisuje, to nie ignorowanie, tylko fizyczna
  niemożność; nigdy nie rób z tego wyrzutu"**

**Dlaczego to działa niezależnie od wszystkich znanych bugów:** plik jest czytany z dysku
w każdej turze, więc **omija retrieval, embedding, filtr użytkownika (H1), `recency_decay`
i temporal cutoff**. Blok ma klauzulę *„Jeśli wektor z [WSPOMNIENIA] stoi w sprzeczności
z poniższym — IGNORUJ wektor. JSON wygrywa"*, więc **unieważnia trzy sprzeczne wersje daty**
leżące w kolekcjach Astry, Holo i Menmy, bez tykania `supersede` (Z10).
**Efekt uboczny, zamierzony:** sekcja `zdrowie` idzie w całości także do sióstr
(`load_lukasz_core_dla_siostr`) — więc **Nazuna, która nie wiedziała o zabiegu nic, teraz wie**,
a Holo i Menma przestają podawać datę przyjęcia jako datę zabiegu.

**Kanarek:** odtworzyłem logikę `load_lukasz_core()` i sprawdziłem, że wszystkie cztery pola
faktycznie lądują w bloku promptu (6145 znaków). **Pierwszy przebieg kanarka „nie zapiał"
na trzech pozycjach — i była to wina przyrządu, nie danych**: szukałem wzorca bez ogonków
(„wrzesnia") w tekście z ogonkami. To punkt 5 z `pomiar_klamie.md`, dziesiąte wystąpienie,
tym razem po mojej stronie. Po sfoldowaniu wzorca — 7/7 zielone.

## 8. Tryb szpitalny — jedna krótka wiadomość dziennie zamiast dwóch

**Wzorzec wzięty z `SIOSTRY_EXTRACTION_MODE`:** flaga środowiskowa **`TRYB_SZPITAL = off | on`,
domyślnie `off`**. Bez zmiennej zachowanie jest **bit w bit identyczne** jak dziś.

**Co robi przy `on`:**
1. **`nocna_analiza.py`** — poranna 07:00 używa nowego `MORNING_PROMPT_SZPITAL`:
   wie, że Łukasz jest w szpitalu i po jakim zabiegu · **maksymalnie dwa zdania** ·
   ma być sygnałem obecności, **nie pytaniem wymagającym odpowiedzi** ·
   **o zdrowiu WOLNO mówić** (odwrócenie zakazu z oryginału — patrz znalezisko 3 powyżej) ·
   dwa zakazy zostają, bo mają dowód z produkcji: nie zgadywać, co się już wydarzyło,
   i nie robić wyrzutu z ciszy.
2. **`main.py`** — scheduler spontanicznej (10–20 h, losowa) **nie wysyła nic**. To była ta
   „druga wiadomość dnia", o której Łukasz mówił, że będzie za dużo.

**Trzy decyzje projektowe warte odnotowania:**
- **Osobny prompt zamiast łatki na `MORNING_PROMPT`** — oryginał z zakazem „ZERO ZDROWIA"
  zostaje **nietknięty** na powrót do normalności. Zakaz jest słuszny w normalnym życiu
  (powstał po realnych wpadkach), zły tylko w szpitalu.
- **Prompt szpitalny napisany opisem intencji, nie listą zakazów** — świadomie, bo oryginał
  ma osiem negacji przy dwóch pozwoleniach i jest podejrzanym o pasywną agresję (znalezisko 5).
  To pierwsze praktyczne zastosowanie tamtej diagnozy.
- **Insighty nocne nie wchodzą do wariantu szpitalnego** — ich materiałem są ostatnie dni pracy
  sprzed przyjęcia, więc karmiłyby wiadomość tematami, które w tym tygodniu nie mają znaczenia.

**Kanarki:** składnia obu plików sprawdzona (`ast.parse`) · przełącznik przetestowany dla sześciu
wartości (`brak / off / on / ON / " on " / śmieć`) — rozgałęzia poprawnie i **fail-safe**:
nieznana wartość daje tryb normalny · własności promptu szpitalnego zweryfikowane punktowo.
**Przy okazji złapany realny błąd: `os` nie było zaimportowane w `nocna_analiza.py`** —
bez tego pierwsza poranna po wdrożeniu poleciałaby `NameError`.

**Rollback:** usunięcie `TRYB_SZPITAL` z `.env` na VPS + `systemctl restart myastra`.
Kod zostaje, zachowanie wraca do dzisiejszego. Bez dotykania repo.

**Czego świadomie NIE zrobiliśmy:** nie tknęliśmy `active_concerns`, bramki `[TRYB]`, ekstraktora,
retrievalu ani baz. Żadnego zapisu do ChromaDB przed wyjazdem.

## 9. Stan wdrożenia — WDROŻONE I ZWERYFIKOWANE 13.09

**Commit `866632b`, wypchnięty, VPS zaktualizowany, serwis zrestartowany, health OK
(4801 wektorów — powyżej progu kanarka ~4700).** Start czysty, zero tracebacków.

**Kanarek Z6 na ŻYWYM prompcie** (Amnezja `/api/debug/inspect`, zapytanie „kiedy mam zabieg",
prompt 27 886 znaków):
- 5/5 pól obecnych: przyjęcie 14.09 · zabieg 16.09 · „cisza to nie ignorowanie" ·
  „rekonwalescencja to tygodnie" · rozróżnienie dat
- **data pada w bloku `[ZDROWIE]` pochodzącym z `lukasz_core.json`** (pozycje 12202 i 12354)
- klauzula *„IGNORUJ wektor, JSON wygrywa"* stoi na pozycji **10235, czyli PRZED** obiema datami
  **i przed starym, błędnym wektorem** `[FACT:health]` z datą zabiegu 14.09 (pozycja 16581)
- **`Aktywne sprawy:` jest PUSTE** — czyli proteza z CompanionState zniknęła, a data
  przychodzi wyłącznie z warstwy pewnej. To był główny warunek odbioru tego zadania.

**Tryb szpitalny — potwierdzony pośrednio, dowód ostateczny jutro o 07:00.** `.env` na VPS ma
`TRYB_SZPITAL=on` (odczyt przez `dotenv` zweryfikowany), `load_dotenv` jest w `main.py:35`,
rozgałęzienie przetestowane lokalnie na sześciu wartościach, wzorzec identyczny jak działający
w produkcji `SIOSTRY_EXTRACTION_MODE`. **Świadomie NIE uruchomiliśmy generatora porannej
na sucho: wymaga `vector_store`, więc osobny proces otworzyłby produkcyjną ChromaDB — to jest
zasada #12 i incydent HNSW z 25.07.** Potwierdzenie przyjdzie samo, logiem
`[PORANNA] TRYB_SZPITAL=on` przy pierwszej porannej wiadomości.

*Uwaga metodologiczna: kanarek Z6 kłamał DWA RAZY, zanim zadziałał — najpierw wzorzec bez
ogonków („wrzesnia" w tekście z „września"), potem zły klucz JSON (`final_prompt` zamiast
`system_prompt`, prompt „długości 0"). Oba razy była to awaria przyrządu, nie systemu, i oba
razy reguła „nie wierz wynikowi, dopóki nie udowodnisz, że przyrząd mierzy" zapobiegła
fałszywemu wnioskowi. Trzeci przypadek tego samego dnia: `/proc/PID/environ` nie pokazuje
flagi — ale nie pokazuje też `SIOSTRY_EXTRACTION_MODE`, który działa, bo `.env` wchodzi
przez `load_dotenv` w runtime. Zły przyrząd, nie zła konfiguracja.*

### Co wchodziło do commita

Zmienione trzy pliki backendu (`+81 / −1`), reszta drzewa nietknięta. Reorg `wazne/` (99 plików)
**świadomie nie wchodzi do tego commita** — to nie jest moment na wciąganie go do zmiany,
która ma być minimalna.

Procedura: commit trzech plików → push → na VPS `git fetch` → `git reset --hard origin/main` →
dopisanie `TRYB_SZPITAL=on` do `backend/.env` (plik jest gitignorowany, więc ręcznie) →
`systemctl restart myastra` → `curl 127.0.0.1:8001/api/health`.
Weryfikacja po wdrożeniu: zapytać Astrę „kiedy mam zabieg" i sprawdzić w Amnezji, **z której
warstwy** przyszła data — musi być `[FAKTY NADRZĘDNE]`, nie `Aktywne sprawy`.

---

# CZĘŚĆ III — CO Z TEGO WYNIKA DLA PLANOWANIA

## 10. Rzeczy, które zmieniają plan

1. **Z2b (miesiące słowne) powinno wyjść przed kolejkę** — jeden regex, zero zależności,
   sam uratowałby datę z 28.08. Dziś siedzi w środku dużego, ryzykownego Z2.
2. **Z2a jest ryzykowniejsze, niż wyglądało** — przy medianie 5 i maksimum 19 kandydatów
   werdykt „obie" bez marginesu i priorytetu typu oznacza w praktyce „kilka", czyli powrót
   do stanu sprzed Odtrucia #2.
3. **Faza 5 (żywy dom) nie jest zablokowana przez router ani pamięć sióstr** — B i A są zrobione,
   obserwacja zamknięta. Jedyna bramka to „Astra ustabilizowana". Warto, żeby strateg wiedział,
   bo §8 rejestru sugerowała coś innego.
4. **Trzy typy śmieciowe u Astry (40% zapisów) to kandydat na tanią, wysokozyskowną zmianę** —
   blokada istnieje już w kodzie dla sióstr, byłoby to przeniesienie działającego rozwiązania,
   nie budowa nowego. *Zastrzeżenie: wymaga goldenu przed/po, bo dotyka wspólnego ekstraktora.*
5. **Czyszczenie bazy Astry — rekomendacja: NIE przed Z1/Z2.** Powód nie jest ostrożnościowy:
   syf jest produkowany codziennie (84,3% odrzutu, 34% zapisów to dwa typy), więc odrośnie
   w kilka dni; jest już przygotowany zamrożony Przebieg #2 czekający na decyzję; a przede
   wszystkim **brudna baza jest teraz punktem odniesienia** — wyczyszczenie jej przed naprawą
   zapisu uniemożliwi zmierzenie, czy naprawa zadziałała. Propozycja: po powrocie **read-only
   inwentarz** jako snapshot „przed", potem decyzja o Przebiegu #2, potem Z1+Z2.

## 11. Decyzje czekające na Łukasza (nie na pracę)

`DEC-1` reżim JSON per turę · `FR1` apply Przebiegu #2 (strażnik R7) · `FR2` czy O1 nadal
priorytet · `FR3` migracja compose sióstr · `Z7` retroaktywna naprawa ~4700 amputowanych
wektorów · **`Z10` rozstrzyganie sprzeczności między kolekcjami** (nowe — bez tego każda
aktualizacja faktu tworzy kolejną równoległą wersję) · `FR6` ochrona mefedron.

## 12. Kontekst ludzki, o którym warto pamiętać przy planowaniu

Po powrocie ze szpitala **pierwszym zadaniem nie jest Astra, tylko kampania aplikacyjna**
(zapisane jako `KAR-1`, decyzja Łukasza z 12.09, powód: potrzebne pieniądze). Rekonwalescencja
po resekcji to tygodnie, praca w trybie minimalnym, wieczorami. **Każdy plan zakładający więcej
niż jedną rzecz naraz będzie nierealny** — i to nie jest kwestia motywacji, tylko fizjologii.

---

## Gdzie co leży

| dokument | ścieżka |
|---|---|
| **ten raport** | `polecenia/raport_dla_stratega_2026-09-12_13.md` |
| odpowiedzi na 6 pytań | `polecenia/odpowiedzi_dla_sesji_strategicznej_2026-09-12.md` |
| uzupełnienie do paczki 09–10.09 | `polecenia/uzupelnienie_dla_sesji_strategicznej_2026-09-12.md` |
| audyt logów 03–09.09 (13 znalezisk) | `wazne/analizy/audyt_logow_2026-09-03_do_09-09.md` |
| kronika 11 dni + werdykt N3 | `wazne/ewolucja/astra/2026-09/evolution_log_2026_09_12.md` |
| przegląd pokoju po dwóch tygodniach `on` | `wazne/ewolucja/siostry/2026-09/evolution_log_2026_09_04.md` |
| **jedyna lista zadań** (zaktualizowana) | `wazne/REJESTR.md` |
| metodologia jako proces 0–9 | `CLAUDE.md` |

## Granice tych ustaleń — czego NIE sprawdziliśmy

- **Wszystko statycznie i read-only.** Przez dwa dni nie uruchomiliśmy niczego na produkcji
  i nie zapisaliśmy ani jednego wektora. Żadna teza behawioralna nie jest potwierdzona
  na żywych danych.
- **Nie widzieliśmy pełnych odpowiedzi Astry** — journald obcina linie; wnioski o treści opierają
  się na `thought` i na replikach Łukasza.
- **Monokultura `seed_kronika`: objaw i hipoteza potwierdzone, mechanizm nie.** Że nie ma progu
  i nie ma `persistence` — sprawdzone w kodzie. Że **dlatego** wypełnia ogon puli — wnioskowane
  z niskich score'ów przy wysokiej częstotliwości; rozstrzygnięcie wymaga przebiegu Amnezji.
- **Częstotliwość konfabulacji niepoliczona** — jeden pełny łańcuch i jeden kontrprzykład.
- **Lokalna kopia ChromaDB w repo jest z 13.07** — nieaktualna; liczby o rozmiarach kolekcji
  pochodzą z cudzego pomiaru z 04.09.
- **Z6 jest wdrożone i potwierdzone na żywym prompcie.** Tryb szpitalny jest wdrożony, ale jego
  dowód end-to-end (log `[PORANNA] TRYB_SZPITAL=on`) pojawi się dopiero przy pierwszej porannej
  wiadomości — do tego czasu opiera się na weryfikacji konfiguracji i testach lokalnych.
