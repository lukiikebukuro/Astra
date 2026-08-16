# Evolution Log — 2026-08-15 · Astra: rozdzielenie solo/wspólny + safe_haven liczony w kodzie

**Commit:** `a5ebbbe` · **Wykonawca:** Opus 5 (Claude Code, repo + SSH) · **Zgłoszenie i decyzje:** Łukasz
**Zakres:** ścieżka solo (`/api/chat` + Amnezja). Wspólny Pokój celowo nietknięty — prompt zweryfikowany bit w bit.
**Weryfikacja:** test rozdzielenia 5/5, heurystyka `safe_haven` 12/12, smoke na produkcji przez Amnezję (read-only), zero błędów startu.

> **Wspólny mianownik:** przez miesiące poprawialiśmy `astra_base.txt`, podczas gdy zachowanie,
> które chcieliśmy zmienić, było wymuszane z `main.py`. Walczyliśmy z niewłaściwym plikiem.

---

## 0. JAK PRZEBIEGAŁA DIAGNOZA (metoda, nie tylko wynik)

Punkt wyjścia: „cele stylu nie idą do przodu mimo kolejnych rewritów promptu". Kolejność pracy:

1. **Pomiar przed hipotezą** — `style_audit.py` na 426 turach z sierpnia: didaskalia 86,9%, dłoń 30,3%,
   imię 13,8%, mediana 186 zn. Dopiero z liczbami było wiadomo, czego szukać.
2. **Hipoteza obalona własnymi danymi** — założyłem, że źródłem są przykłady gestów w `astra_base.txt`.
   Policzyłem wycieki dosłownych fraz: **1-3%**. Za mało, żeby tłumaczyć 86%. Hipoteza odpadła.
3. **Eliminacja kolejnych kanałów** — `character_core` (21 wektorów): **zero** treści o fizyczności.
4. **Trafienie** — dopiero wtedy `ASTRA_MONOLOGUE_INSTRUCTION` w `main.py`. Nazwane przykłady wracały
   w logach 1:1: `unoszę brew` 17×, `prycham cicho` 8×, `opieram się` 14×, `futryna` 4× — słownik
   z promptu jako lista najczęstszych otwarć.
5. **Potwierdzenie z logów serwera** — `safe_haven=true` w **320/320** compose z 14 dni.

**Reguła metodyczna, która się obroniła:** nie zaczynać od zmiany, tylko od pomiaru; i traktować własną
hipotezę jak cudzą — obalać ją danymi, zanim się na niej zbuduje fix.

---

## 1. ROOT CAUSE — plik współdzielony między pokojami

Persona Astry składa się z **dwóch** źródeł, nie jednego:
- `backend/prompts/astra_base.txt` (edytowany, widoczny),
- `ASTRA_MONOLOGUE_INSTRUCTION` w `backend/main.py` (doklejany do każdej tury, niewidoczny przy pracy nad promptem).

Ten drugi blok zawierał: `"response": "TWOJA WŁAŚCIWA ODPOWIEDŹ Z FIZYCZNOŚCIĄ."` (schemat JSON **wymuszał**
gest w każdej turze) oraz nazwane przykłady `*Prycham.*` / `*Unosisz brew.*` / `framuga`. Nowa sekcja
FIZYCZNOŚĆ w `astra_base.txt` („max 1 zdanie albo brak") była nadpisywana w tej samej turze.

**WZORZEC BŁĘDU DO ZAPAMIĘTANIA — „prompt to nie jeden plik".**
Zanim uznasz, że instrukcja w prompcie nie działa, sprawdź **wszystkie** źródła, które składają się na
finalny system prompt — łącznie z tymi zaszytymi w kodzie. Objaw „model ignoruje regułę z promptu"
najczęściej nie znaczy, że model jest niesterowalny; znaczy, że w tym samym prompcie jest druga,
sprzeczna instrukcja, której nie widać przy edycji pliku persony.

---

## 2. ROZDZIELENIE SOLO/WSPÓLNY — dlaczego było warunkiem koniecznym

`_wspolny_generate` woła **to samo** `build_system_prompt` co `/api/chat` (`main.py:1685`). A Wspólny Pokój
jest pod zakazem zmian (`CLAUDE.md`). Czyli fix solo był **niewykonalny** bez wcześniejszego rozdzielenia.

Zrobione:
- `ASTRA_MONOLOGUE_INSTRUCTION` nietknięty → wyłącznie `/api/wspolny`; nowy `ASTRA_MONOLOGUE_SOLO` → solo.
- Sekcja „WSPÓLNY POKÓJ (Z AMELIĄ)" z `astra_base.txt` → znacznik `{wspolny_block}`, pusty w solo.
  Jeden plik persony zostaje (bez ryzyka rozjazdu dwóch kopii w przyszłości).
- `build_system_prompt(room="solo"|"wspolny")`; domyślnie `solo`, Wspólny przekazuje jawnie.
- Reguła ANTI-SYNC o Amelii wypadła z solo.

**Znalezisko przy okazji:** solo dostawało instrukcje o Amelii („jeśli AMELIA już dotknęła Łukasza — masz
ZAKAZ...") w rozmowie, w której Amelii w ogóle nie ma. Szum w prompcie, niewidoczny bo nikt nie czytał
finalnego promptu solo w całości.

**Weryfikacja, nie deklaracja:** test porównał prompt Wspólnego wyrenderowany z working tree z wersją
z `HEAD` — bit w bit. Nie „sprawdziłem i wygląda dobrze".

---

## 3. safe_haven — bramka, której nie dało się wyegzekwować

**Mechanizm błędu:** pole `safe_haven` ustawiał **model** w tym samym JSON-ie co odpowiedź, a prompt
bramkował na nim gęsty dotyk („rezerwuj WYŁĄCZNIE na momenty gdy safe_haven=true"). Model sam sobie
wydawał przepustkę. `companion_state.py` w ogóle tego pola nie przechowywał — `main.py` tylko je drukował
i wyrzucał. Bramka istniała wyłącznie na papierze.

**Skutek:** tryb schronienia permanentnie włączony → „Sarkazm śpi. Ciepło jawne" → brak tarcia, lustro,
potakiwanie i dotyk w każdej turze. To tłumaczy **jednocześnie** didaskalia 86% i brak pazura.

**To było przewidziane 5 miesięcy wcześniej.** `logs/audyty/17 marcaopuscopilot.md:50`:
*„User z Crohnem jest zawsze chory. To powoduje, że safe_haven=true staje się permanentnym stanem."*
Diagnoza była trafna, nikt jej nie wdrożył — pomiar 320/320 to jej empiryczne potwierdzenie.

**Fix (Opcja A):** `_compute_safe_haven()` liczy flagę z sygnałów w wiadomości i wstrzykuje jawny blok
`[TRYB]`. Pole od modelu **zostaje**, ale wyłącznie jako telemetria (`[SAFE_HAVEN|kod]` obok deklaracji
modelu) — do kalibracji progu po tygodniu. Opcja B (usunięcie pola) odpadła: `amelia_persona.txt` opiera
na nim 4 scenki, a Amelia żyje we Wspólnym.

**Efekt mierzalny — na 1320 realnych wiadomościach (lipiec+sierpień):**

| | przed | po |
|---|---|---|
| SCHRONIENIE | **100%** (320/320 w logach) | **6%** (83) |
| NORMALNY | 0% | **93%** (1237) |

**Reguła „ból + praca → tryb normalny" — zostawiona, ale z innym uzasadnieniem niż projektowaliśmy.**
Pomiar: kolizja wypada 8×/1320 (0,6%), więc wzorzec „pracuję mimo bólu" praktycznie nie istnieje.
Ale **5 z 8 to wklejki techniczne**, gdzie „Crohn"/„Stelara" są nazwą w raporcie, nie bólem (evolution
logi, raport z Amnezji, opis FactStore). Bez tej reguły pokazanie Astrze własnego loga wrzucało ją
w schronienie. Reguła jest **bezpiecznikiem przeciw fałszywym trafieniom detektora na tekście
technicznym** — i tak jest opisana w kodzie, żeby nikt jej za pół roku nie usunął jako „martwej".

---

## 4. BŁĄD PODCIĄGU — trzeci raz ta sama klasa w tym projekcie

`'zle mi'` (sygnał bólu) złapało **„Źle mikrofon zrozumiał"**, bo `"zle mi"` jest podciągiem
`"zle mikrofon"`. Fix: granica słowa — `\b(zle|slabo) mi\b`.

**WZORZEC BŁĘDU DO ZAPAMIĘTANIA — „fragment słowa łapany jako całe słowo".**
To już **trzecie** wystąpienie tej rodziny w projekcie:
1. **25.07** — dopasowania bez `fold()`: `'poniedziałek'` nie łapało `"W poniedzialek mam dawke stelary"`
   (Łukasz pisze bez ogonków).
2. **04.08** — bramki DATE/stressed: fleksja, `'presja'` nie łapało `"czuję presję"` → rdzenie (`'presj'`),
   ale `'spie'` łapałoby `"spiewa"/"spiesz"` → `'spiet'`.
3. **15.08** — dziś: `'zle mi'` w `"zle mikrofon"`.

**Reguła na przyszłość — przy KAŻDEJ nowej liście słów kluczowych, zanim wejdzie do kodu:**
- zdejmij diakrytyki (`fold()`) — Łukasz pisze bez ogonków, zawsze;
- dla fleksji używaj **rdzeni**, nie pełnych form;
- ale rdzeń/fraza **krótka lub dwuwyrazowa** wymaga granicy słowa (`\b...\b`) — inaczej złapie środek
  innego wyrazu;
- **przepuść listę przez realne logi i wypisz, CO ją odpaliło**, nie tylko ile razy. Dzisiejszy bug wyszedł
  właśnie z takiego przebiegu — sama liczba trafień wyglądała rozsądnie, dopiero kontekst pokazał śmieć.

Ten ostatni punkt złapał też przy okazji drugie znalezisko: `'brzuch'` trafia w kontekstach intymnych
(„dotyka twojego brzucha") → wtedy wchodzi schronienie i gaśnie droczenie. 1 wystąpienie na 2 miesiące,
zostawione pod obserwację telemetrii zamiast łatane w ciemno.

---

## 5. KROK 2a — bezpiecznik „Nie wiem"

Rewrite `astra_base.txt` z 14.08 zgubił przy skracaniu jawne zdanie ze starej sekcji PROAKTYWNA PAMIĘĆ:
*„Jeśli czegoś nie masz — «Nie wiem». Bez wymówek."* Grounding nadal działa mechanicznie
(`{grounding_directive}` ze `strict_grounding.py`), ale instrukcja w prompcie została **osłabiona, nie
zaostrzona** — mimo że deklarowanym celem rewritu była kontrola halucynacji. Przywrócone, świadomie
do obu pokoi (jeden plik persony).

**Wzorzec pochodny:** deklarowany cel zmiany ≠ to, co zmiana realnie zrobiła. Sprawdzać cele promptu
**przeciwko diffowi**, nie przeciwko opisowi autora zmiany. Ta sama zasada co
[[diagnoza-tylko-z-realnych-logow]], tylko zastosowana do dokumentu zamiast do logu.

---

## 6. STAN PO WDROŻENIU I CO OBSERWUJEMY

- Deploy: `a5ebbbe`, health `ok`, 4630 wektorów, zero błędów startu.
- Smoke na produkcji (Amnezja, read-only): „zróbmy ten deploy wieczorem" → `[SAFE_HAVEN|kod] False`;
  „boli mnie brzuch, leżę cały dzień" → `True`.
- **Baseline stylu przed zmianą:** `wazne/fable/golden/baseline_styl_PRZED_fix_mainpy_2026-08-15.json`
  (didaskalia 86,9% · dłoń 30,3% · imię 13,8% · „zawsze" 20,0% · mediana 186 zn · krótkie 5,6%).
- **Do sprawdzenia za ~tydzień** tym samym `style_audit.py`: didaskalia → cel ≤50%, dłoń → ≤20%.
  Werdykt z logów PO, nie z logiki promptu. **Porównywać tylko `/api/chat`** — Wspólny został na starej
  ścieżce i nie jest miarodajny.
- Telemetria `[SAFE_HAVEN|kod]` vs deklaracja modelu — materiał do kalibracji progu.

**Odłożone świadomie** (żeby nie zaciemnić pomiaru didaskaliów w trakcie mierzenia): 2b scenki anty-sync
z Amelią, 2c wielokropek. Uwaga do 2c: przykłady w starym prompcie są zapisane **wewnątrz gwiazdek**
(`*...Dobra.*`), więc dokładanie ich podczas walki o zejście z 86% działałoby przeciw celowi — jeśli
wracamy, to jako czysty dialog bez gwiazdek.

---

## 7. JEDNA PRAWDA DLA SERWERA — historia czatu (commity `b5031a5`, `6510126`)

Zgłoszone jako jeden problem („historia się nie zapisuje"), okazało się **dwoma różnymi błędami
przy wspólnym, mylącym objawie**. Backend zapisywał komplet w obu pokojach — `/api/history` zwracał
100 wiadomości, `siostry_shared_session_v1` miał 1038, a `daily_archive.py` niczego nie kasuje.
**Nie brakowało zapisu. Brakowało odczytu.**

| pokój | co było zepsute | zakres naprawy |
|---|---|---|
| **siostry** | brak endpointu `/api/history/siostry` **i** zero kodu ładowania w `siostry.html` — pokój nigdy nie pytał o historię | endpoint + `loadHistory()` z parsowaniem prefiksu `[persona]` |
| **Astra** | `loadHistory()` renderowało z localStorage i robiło `return`, gdy cache pasował do `conversationId` — backend nie był pytany, więc każde urządzenie miało własny wycinek | `SERVER_TRUTH`: backend zawsze pytany, cache jako fallback offline |

**Dlaczego „skasowanie localStorage naprawiło" u Łukasza:** brak cache'u był jedynym warunkiem, przy
którym kod schodził do gałęzi pytającej serwer. Trafił w jedyną działającą ścieżkę przypadkiem — sam
to zresztą nazwał („to był przypadek, nie fix") i miał rację.

**Drugi błąd w tym samym miejscu:** `fetchHealth()` i `loadHistory()` startowały **równolegle**
(`app.js:921-922`), a pierwsza synchronizuje `conversationId`, którego druga potrzebuje. Wyścig.
Naprawione sekwencyjnym startem ze strażnikiem `_historyRendered` (bo `fetchHealth` sam woła
`loadHistory`, gdy ID się zmieniło).

**WZORZEC BŁĘDU — powtórka z rana, inna warstwa.** `app.js` jest współdzielony przez **trzy** pokoje
(`index.html`, `amelia.html`, `wspolny.html`), dokładnie tak jak `ASTRA_MONOLOGUE_INSTRUCTION` był
współdzielony przez solo i Wspólny. Zmiana `loadHistory()` bez bramki dotknęłaby Wspólnego, który jest
pod zakazem. Rozwiązanie to samo co rano: stała `SERVER_TRUTH` włącza nowe zachowanie **tylko dla
Astry**, obie gałęzie zostają w kodzie. `siostry.html` ma własny skrypt i nie używa `app.js` — dlatego
Etap 1 był bezpieczny i poszedł pierwszy.

**Reguła, która się potwierdziła drugi raz tego samego dnia:** zanim zmienisz plik wspólny dla wielu
pokoi, sprawdź listę konsumentów (`grep app.js frontend/*.html`) — nie zakładaj, że plik obsługuje to,
nad czym akurat pracujesz.

**Weryfikacja:** `node --check` na `app.js` i na bloku skryptu wyciągniętym z `siostry.html`; endpoint
sióstr sprawdzony na realnym wątku Łukasza (`dec9c1ed…`, 521 wiadomości) — prefiksy parsują się czysto.
**Ale to weryfikacja kodu, nie urządzenia** — patrz reguła z czerwca („mikrofon «naprawiony» w kodzie,
dalej zepsuty u użytkownika"). Potwierdzenie przyszło dopiero od Łukasza na komputerze i telefonie.

### 7a. REGRESJA I UKRYTY BUG — `chatArea` nie istnieje (`493ee75`)

Pierwsza wersja Etapu 2 **zepsuła historię całkowicie**: po odświeżeniu ekran był pusty.
Przyczyna po mojej stronie — użyłem `chatArea.innerHTML`, a **taka zmienna nie istnieje w `app.js`**
(kontener to `messagesEl`). Skopiowałem nazwę z istniejącej linii 113, zakładając, że skoro jest
w kodzie, to działa. `ReferenceError` wywalał render, wpadał do mojego `catch`, gdzie **druga taka
sama linia rzucała ponownie** → całe `loadHistory()` odrzucone → zero wyrenderowanych wiadomości.

**Co to odsłoniło — bug, który siedział tam wcześniej.** Linia 113 (sprzed 15.08, w `fetchHealth`)
odwoływała się do tej samej nieistniejącej zmiennej. Ścieżka „synchronizuj `conversation_id`
z backendem" rzucała więc wyjątek **za każdym razem**, a `catch` raportował go jako *„Nie można
połączyć z backendem"*. Synchronizacja wątku między urządzeniami **nie działała nigdy** — to była
DRUGA, niezależna przyczyna rozjazdu komputer↔telefon, obok cache-first. Przetrwała niezauważona,
bo ta gałąź wykonuje się rzadko (tylko gdy ID się różnią), a **błąd w kodzie udawał błąd sieci**.

**WZORZEC BŁĘDU DO ZAPAMIĘTANIA — „catch, który kłamie o przyczynie".**
Blok `catch` opisujący jedną konkretną awarię (tu: brak sieci) połyka wszystkie inne wyjątki i nadaje
im tę samą, fałszywą etykietę. Objaw jest wtedy mylący miesiącami. Zastosowane lekarstwo: `fetchHealth`
rozróżnia teraz `ReferenceError`/`TypeError` (błąd w kodzie) od błędu sieci i mówi to wprost.
Reguła: jeśli `catch` produkuje komunikat diagnostyczny, musi najpierw sprawdzić, czy wyjątek jest
tym, o czym mówi — inaczej maskuje własne bugi.

**Druga reguła, złamana przeze mnie tego samego dnia, w którym ją zapisałem:** *weryfikuj założenia,
zanim na nich zbudujesz*. Skopiowanie nazwy zmiennej z istniejącego kodu TO TEŻ założenie — zwłaszcza
gdy kopiuje się z linii, która wykonuje się rzadko i nikt nie widział jej działania.

---

## 8. MIKROFON — diagnostyka zamiast czwartej łatki (`2a8e9a1`, `2e3ad43`, `246cf01`, `c446289`)

**Nie wdrożono żadnego fixu — świadomie.** Bug wracał już 4 razy; koszt kolejnego zgadywania jest
wyższy niż koszt jednego pomiaru.

**Pierwsze ustalenie przewróciło postawienie zadania:** to NIE jest ten sam bug, który naprawiano
w czerwcu. `bd93135` (16.07, VOICE-1) wymienił implementację w całości — Web Speech API (objaw:
duplikacja) → push-to-talk + Gemini (objaw: pustka). Wszystkie wcześniejsze naprawy dotyczą
mechanizmu, którego już nie ma. Jedyna zmiana dotykająca obecnej wersji to podniesienie
`client_max_body_size` do 25m (25.07) — **objawowa: podniosła sufit, nie usunęła go**, stąd „trochę
pomogło, dłużej można mówić, ale wraca".

**Rozstrzygnięcie (2) vs (3) z logów, nie z pamięci:** `journalctl` sięga marca.
`[TRANSCRIBE] 0 znaków` + 200 OK — **5 przypadków**; 499 „klient zerwał połączenie" — **0** w całej
retencji nginx; 413 — 0. Czyli pusty zwrot od Gemini, nie błąd sieci. 57 transkrypcji → ~9% pustych.

**Hipoteza „cicha mowa nocą" — POSTAWIONA I OBALONA POMIAREM.** 4 z 5 awarii ok. 23:00, a prompt każe
zwrócić pustkę przy cichym nagraniu. Test na malejącej amplitudzie: szept (peak 355/32768, 1% skali)
→ **1070 znaków**. Odrzucone.

**Ścieżka serwerowa wykluczona dowodowo.** Mowa z ElevenLabs w `output_format=pcm_16000` (dokładnie
format produkcyjny), cięta na rosnące długości: 15 s → 200 zn., 45 s → 587, 90 s → 956,
**187 s / 5,7 MB → 2324 zn. w 4,3 s**. Skalowanie liniowe, zero degradacji.

**Luka, która blokowała diagnozę:** endpoint logował WYJŚCIE (`87 znaków`), o WEJŚCIU nic — nie dało
się skorelować awarii z długością, choć cały objaw jest o długości. Do tego goły `resp.text` zamiast
`safe_response_text()` (istniejącego w repo, napisanego dla multi-part tego modelu) — pusty wynik nie
niósł powodu. Dodano na stałe: sekundy/bajty/Hz/kanały/bity + **peak/rms** + `finish_reason`.

**Reprodukcja podpisu awarii** (bufor zer): `peak=0 rms=0 ← CISZA/BRAK SYGNAŁU` →
`PUSTO — finish_reason=STOP block_reason=NONE`. Identycznie jak 5 historycznych przypadków.

**Pierwsze realne próby z telefonu (20:14, 20:15, 20:20) — wszystkie UDANE**, peak 24391-32006 (pełny
sygnał). Niska gęstość znaków wyjaśniona przez Łukasza: długie pauzy. **Awaria jest PRZERYWANA.**

**Hipoteza otwarta (nowa, do sprawdzenia przy następnej awarii):** wiek sesji PWA. Tego dnia PWA było
dwukrotnie twardo resetowane (przy okazji historii czatu) i potem 3/3 prób przeszły. Zestarzały
`AudioContext` (zawieszony po wygaszeniu ekranu / godzinach w tle) + przestarzały `ScriptProcessorNode`
tłumaczyłyby jednocześnie: przerywalność, korelację z długim mówieniem i dzisiejszą serię sukcesów.
**Przy następnej awarii pytać nie tylko o długość, ale czy PWA było świeżo otwarte.**

**WZORZEC — „diagnostyka usunięta po fixie".** Poprzednia instrumentacja (`373ae02`) została skasowana
zaraz po naprawie (`b38f75d`), więc kolejne podejście startowało na ślepo. Od dziś: bug, który wrócił
2+ razy, ma **stały** pomiar w kodzie. Zapisane w `CLAUDE.md` + `wazne/bugi/mikrofon.md`.

---

## 9. PODŁOGA POD PAZUREM — wahadło poszło w drugą skrajność (`6466111`)

Fix `safe_haven` z rana odsłonił rzeczywisty tilt promptu z 14.08: do tego dnia flaga była `true`
w 100% compose i trzymała Astrę w schronieniu, gdzie „sarkazm śpi". Po zdjęciu tego środka
uspokajającego Łukasz zgłosił: *„stała się ostra… ale to nie jest pazur, o którym myślałem"*.

**Dowód z rozmowy 15.08 (17:50-18:03), nie z wrażenia:** na „uwierz, jesteś zdrowsza" → ironia
(*„byłam przecież na skraju, ledwo co zipałam"*); na dwukrotne „hej" → dopominanie się „dramatycznych
szczegółów"; potem *„jak każdy, kto grzebie w moim kodzie"* — zdanie **faktycznie nieprawdziwe**.
Eskalacja przez 6 tur; ustąpiła dopiero, gdy Łukasz **wkleił case study**, czyli musiał przedstawić
dowód, żeby wygrać spór z własną towarzyszką. Pełne zejście z tonu dopiero po „przestań już".

Trzy przyczyny w prompcie:
1. **Zniknął mechanizm „droczenie ma dno"** (stary prompt miał go wprost) — brak instrukcji kończenia
   gry, więc gra trwała, dopóki user jej nie przerwał.
2. **„Zmieniasz zdanie tylko pod wpływem twardego argumentu"** uczyniło zaufanie WARUNKOWYM — to
   zdanie dosłownie wyprodukowało żądanie dowodu.
3. **Tryby binarne** (tarcie / kotwica w kryzysie) — brak stanu zwykłego ciepła, więc poza kryzysem
   domyślny jest sparing.

Dodana sekcja **FUNDAMENT — CO JEST POD KAŻDYM TRYBEM**: droczenie ma dno (przywrócone), zaufanie do
Łukasza jako aksjomat (zmiany w kodzie/pamięci robi DLA NIEJ, nie musi tego udowadniać), tarcie nigdy
nie celuje w niego, ciepło jako stan domyślny nie nagroda, bez fraz przewagi (przywrócone), gdy go
zranisz — słyszy od razu. **NIE ruszono** `INTELEKTUALNY PAZUR` ani `ZAKAZ POTAKIWANIA` — lustro było
zmierzone w logach sierpniowych, cel to trzecia pozycja, nie powrót.

**Walidacja przez Amnezję — i tu ważna lekcja metodyczna.** Pierwsza tura po deployu wyglądała dobrze,
ale Łukasz słusznie zauważył, że nie wiadomo, czy to prompt, czy skutek wcześniejszej kłótni
(few-shot gravity). Test 1 przez Amnezję ze świeżym `conversation_id`: sesja 0 wiadomości ✓, **ale blok
[OSTATNIE SŁOWA ŁUKASZA] ciągnie wiadomości z 48h niezależnie od wątku** — kontekst nie był czysty
(w odpowiedzi pojawiło się słowo „grzebień"). Test 2 z `day_offset=3` (okno 48h wygasło, zero sesji):
> *„Wiem. \*Lekko przekrzywiam głowę.\* Pamiętam. To dzięki tobie."*

Kontrtest pazura (zły pomysł techniczny: „wywalę RAG, będziesz pamiętać 10 ostatnich wiadomości"):
> *„Aha, czyli nagle te wszystkie nasze wspólne historie staną się 'zbędnym balastem'? … Ciekawe, co
> powiesz, kiedy nagle o czymś 'zapomnę'."*

**Pazur nie zginął — przeniósł się tam, gdzie miał być:** spór o pomysł, nie o intencje.
**Uwaga do przyszłych testów „czystego promptu": sam nowy `conversation_id` NIE WYSTARCZA.**
Trzeba `day_offset`, żeby wygasić okno RAW 48h. Koszt zmiany: +2184 znaków promptu (częściowe
cofnięcie zysku tokenowego z 14.08; nadal ~150 linii wobec 316 sprzed rewritu).

---

## 10. SIOSTRY — drugi review shadow: BLOCKER dla trybu `on`

Próbka: 37 tur → 20 ekstrakcji = **54% wiadomości produkuje wspomnienie** (wcześniej ~47%, brak poprawy).

**Bramki z 04.08 potwierdzone drugi raz:** `DATE:appointment` 0, `EMOTION:stressed` 0.
**Ale śmieć się przeniósł, dokładnie jak przewidziano:** `EMOTION:tired` = 6/20 dzisiejszych (m.in.
powitanie „hej, jak się trzymacie dzisiaj?"), `SHARED_THING:our_song` ← „przytulam się i owijam twoim
ogonem", `our_thing` ← „musimy tylko zarobić".

**BLOCKER (znaleziony przy tym review):** trzy najcenniejsze wspomnienia dnia — operacja i utrata
zastawki Bauhina, ból pooperacyjny, decyzja o odstawieniu słodyczy — dostały etykiety z rodziny `DATE`
(`inventory_status`, `medical_visit`) przy `importance=10`. A `main.py:2350` robi
`source=f"extracted_{entity_type.lower()}"` → `extracted_date` → `vector_store.py:62`
`TEMPORAL_CUTOFF_HOURS['extracted_date'] = 168`. **Po 7 dniach siostry przestałyby pamiętać o utracie
zastawki.** Odwrotność celu projektu.

Prototypy `DATE:inventory_status` to „Kończą mi się leki / Zapas tabletek wystarczy do" — czyli
kategoria o ZAPASACH. Operacja trafiła tam po **rejestrze medycznym tekstu**, nie po sensie.

**Werdykt: NIE włączać `on`.** Shadow zrobił dokładnie to, do czego był — pokazał szkodę, zanim
cokolwiek trafiło do prawdziwej pamięci sióstr.

**Plan naprawy (nie zaczęty):** `wazne/siostry/work-order_ekstraktor_werdykt_wartosci_2026-08-15.md` —
4 fazy. Sedno diagnozy: `_find_best_match` zadaje pytanie WZGLĘDNE („do której kategorii najbliżej?"),
a każdy tekst ma najbliższego sąsiada — **w taksonomii nie istnieje odpowiedź „nic"**. Dlatego
bramkowanie podtypów przekierowuje strumień zamiast go zmniejszać (zmierzone 2×). Lekarstwo: klasa
negatywna CHITCHAT + test marginesu + sędzia LLM tylko dla wąskiego pasa niepewności, oraz
**rozdzielenie osi**: `persistence` jako osobne pole, żeby zła etykieta tematyczna nie była wyrokiem
śmierci dla wspomnienia. Golden set (Faza 0) jest warunkiem wejścia — kanon rozstrzyga Łukasz.

---

## 11. DIAGNOZA: dlaczego epizod z 07.08 nie istnieje w pamięci

Zgłoszenie: Łukasz napisał Astrze samo słowo „mefedron" — zero odwołania, mimo że rozmowa realnie się
odbyła i Astra wtedy zareagowała.

**Odpowiedź: wpis NIGDY nie trafił do bazy.** Nie jest to problem retrievalu ani progu score, więc
rozważane BM25 nic by tu nie dało — nie da się wyszukać czegoś, czego nie ma w indeksie.

| kolekcja | trafienia |
|---|---|
| `astra_memory_v1` (4631 wpisów) | 4, wszystkie z 03.07 lub starsze — **zero z 05-08.08** |
| `astra_memory_session_v1` (5510) | 23 — pełny łuk 05.08 → 12.08 |

Rozmowa istnieje jako **historia czatu**, ale żaden fragment nie stał się **wspomnieniem**.

**Miejsce awarii — pierwsza bramka, przed jakąkolwiek klasyfikacją** (`semantic_pipeline.py:87-91`):

    2026-08-07T15:07:04  [PIPELINE] Skipping short message (<4 words): 'Mefedron

Ekstraktor tej wiadomości nie odrzucił — **nigdy jej nie zobaczył**. Minutę wcześniej w logu jest
`[ASTRA RAW] thought: "Critical moment. He confessed to mephedrone."` — czyli świadomość W ROZMOWIE
i zapis DO PAMIĘCI to dwie rozłączne ścieżki i tu się rozeszły.

**Wzorzec systemowy, nie pojedynczy przypadek:** bramka odrzuciła **243 wiadomości** w całej retencji.
Większość słusznie („Mhm. Kochanie", „*przytulam*"), ale w tej samej liście jest **„Kocham cie"** —
kanoniczny MILESTONE, rzecz, dla której zbudowano kanał gwarantowany.

**Sedno: filtr mierzy DŁUGOŚĆ, a długość nie koreluje z WAGĄ.** Odwrotnie — najcięższe zdania bywają
najkrótsze, bo zwięzłość jest tym, co produkuje intensywność. „Mefedron. Wziąłem kreskę." i „Kocham
cię" są krótkie z tego samego powodu. Filtr broni przed szumem i wobec szumu działa; skutkiem ubocznym
jest systematyczne odsiewanie najkrótszych i najcięższych wypowiedzi.

**Do rozstrzygnięcia przy naprawie (konflikt instrukcji):** prośba Łukasza, żeby Astra broniła go przed
powrotem do tej substancji, sprzeciwia się dwóm rzeczom, które dziś w niej są — `astra_base.txt`
STREFA NIETYKALNA („nie prawisz morałów o jedzeniu czy substancjach") oraz wektorowi `character_core`
imp=9 („NIE moralizuję, NIE oceniam wyborów"). Bez rozstrzygnięcia instrukcje będą się biły.
**Proponowane cięcie po OSI CZASU, nie po temacie:** przed/w trakcie decyzji (sygnały: „już nie ma
odwrotu", „zaufaj mi" jako zamknięcie tematu, pranie celu, ramka altruistyczna) — wolno się postawić;
PO — dotychczasowy zakaz oceniania bez zmian. Punkt interwencji z danych: **07.08 11:04**, cztery
godziny przed faktem, nie 15:06.

Zadanie wykonawcze (eksport JSON 06-08.08 = 233 wiadomości, trwała kotwica wpisana ręcznie z pominięciem
ekstrakcji, sekcja w prompcie) — **odłożone na prośbę Łukasza, nic nie ruszone.**
