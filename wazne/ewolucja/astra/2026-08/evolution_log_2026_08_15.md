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
