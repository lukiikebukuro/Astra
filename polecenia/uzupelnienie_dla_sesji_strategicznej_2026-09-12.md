# UZUPEŁNIENIE PACZKI — dla sesji strategicznej (claude.ai)

**Data:** 2026-09-12 · **Od:** sesja wykonawcza (Claude Code, repo `astra`)
**Do:** sesja strategiczna, która dostała paczkę z 09–10.09
**Tryb:** wszystko poniżej read-only. Zero zmian w kodzie, zero zapisów do baz, zero deployu.

---

## 0. Po co ten dokument

Dostałeś: `briefing_2026-09-09.md`, listę 16 zadań, `ROADMAPA_OGOLNA_PROJEKTU.md`,
`roadmapa_pamieci_astry.md`, `audyt_pokrycia_roadmapy_2026-09-10.md` oraz
`dopisek_do_paczki_2026-09-10.md`.

Ten plik dokłada **siedem rzeczy, których w tamtej paczce nie ma**, i z których
**trzy zmieniają wnioski** z dokumentów, które już masz. Kolejność od najważniejszej.

Czego tu **nie** ma: powtórzenia roadmapy, listy zadań ani opisu architektury.
To jest delta, nie brief.

---

## 1. ⚠ DATA ZABIEGU — dwie różne daty, nie jedna. Korekta wobec całej paczki

**Ustalone od Łukasza 12.09, to jest wersja obowiązująca:**

> **14.09 = przyjęcie do szpitala. Zabieg = po paru dniach pobytu, na pewno.**
> (Najbliższe źródło z bazy mówi „17 albo 18 września" — patrz tabela niżej.)

Cała paczka, którą masz, mówi „operacja 14.09" — i **dopisek rekomenduje na tej podstawie
wpisanie jednej daty** do `lukasz_core.json` jako wersji taniej Z6. To by utrwaliło błąd.

**Dlaczego to się rozjechało — w bazie są TRZY sprzeczne wersje, w dwóch kolekcjach:**

| kiedy | u kogo | co zapisano | trwałość |
|---|---|---|---|
| 28.08 16:04 | Menma | `[FACT:health] … Mam juz date zabiegu. 14 wrzesnia` | permanent, imp 9 |
| 31.08 20:42 | Holo | `[MEDICATION:schedule] … zabieg … 14 wrzesnia` | long_term, imp 8 |
| **03.09 18:41** | Menma | `[MEDICATION:schedule] 14 jest przyjęcie. Zabieg bedzie jakos 17 wrzesnia albo 18` | long_term, imp 5 |

Trzeci wpis jest **najnowszy, najbardziej precyzyjny i zgodny z tym, co Łukasz mówi dziś** —
i **przegrywa w retrievalu**. `supersede` działa w obrębie jednej kolekcji i jednej pary
`(typ, podtyp)`, więc trzy wersje żyją równolegle, a wygrywa nie najnowsza, tylko najbliższa
zapytaniu. Pokój zapytany dziś odpowie datą **przyjęcia**, podając ją jako datę zabiegu.

**Konsekwencje dla strategii, nie tylko dla tego jednego wpisu:**
1. Wersja tania Z6 musi mieć **dwa osobne pola** (przyjęcie / zabieg), nie jedno.
2. To jest nowa, nieopisana wcześniej klasa usterki: **brak rozstrzygania sprzeczności
   między kolekcjami.** Wpisana do rejestru jako **Z10**. Dotyczy każdego faktu, który
   Łukasz aktualizuje w rozmowie — a on aktualizuje, bo tak działa życie.
3. Kanarek dla Z6 musi sprawdzać nie tylko „czy data jest w prompcie", ale **którа z trzech**.

---

## 2. ⚠ N3 ROZSTRZYGNIĘTE — hipoteza z dopisku jest FAŁSZYWA

Dopisek (§4, zadanie 2) mówi:

> „Prawdopodobnie cała odpowiedź: siostry mają `SIOSTRY_EXTRACTION_MODE=on` od 19.08,
> a mechanizm `persistence` zdjął tam blocker `DATE`→168h. […] To nie jest różnica
> w rerankerze ani w prompcie — to różnica w polityce trwałości.
> **Sprawdzić najpierw tę hipotezę.**"

Sprawdzone w kodzie. **Nie potwierdza się, i to w trzech punktach:**

**a) `persistence` nie jest mechanizmem sióstr.** `compute_persistence` to statyczna metoda
na `VectorStore` (`vector_store.py:65`) — **kod wspólny**, działa identycznie dla Astry.
Wprowadzona 19.08 dla całego systemu (`47958c5`), nie dla pokoju.

**b) Lista siostrzana tylko BLOKUJE, nic nie odblokowuje.** `SIOSTRY_TYPY_BLOKOWANE`
(`main.py:2824`) zawiera trzy pozycje: `DATE:inventory_status`, `FACT:correction`,
`SHARED_THING:inside_joke`. `DATE:medical_visit` nie jest zablokowane u nikogo.

**c) Blocker, któremu przypisano winę, i tak nie był aktywny u Astry.** Wpis Astry
z 31.08 `[DATE:medical_visit] „Nie pamietasz kiedy mam zabieg? Operacje"` był
**permanent, importance 8** — nie 168 h. Bo `ma_sygnal_wagi()` łapie rdzeń `operacj`
(`waga_tresci.py:29`) i nadpisuje regułę `DATE → short_term`.

### Co się stało NAPRAWDĘ — i to jest gorsza wiadomość niż hipoteza

Różnica nie jest w polityce trwałości. Jest w **loterii etykiet na ścieżce zapisu**:

| | zdanie, które niosło datę | etykieta | trwałość | efekt |
|---|---|---|---|---|
| **siostry** | „Mam juz date zabiegu. 14 wrzesnia" | `FACT:health` | **permanent** (reguła jawna) | przetrwało |
| **siostry** | „…zabieg … 14 wrzesnia" | `MEDICATION:schedule` | long_term | przetrwało |
| **Astra** | „Wyznaczyli mi date zabiegu. 14 wrzesnia" (28.08) | **żadna — zero wektorów** | — | **ekstraktor zgubił zdanie** |
| **Astra** | „Tak. 14 wrzesnia. Super! Pamietasz." (29.08) | `EMOTION:excited` | **ephemeral 48 h** | wygasło 2 h 35 min przed pytaniem |
| **Astra** | „Nie pamietasz kiedy mam zabieg? Operacje" (31.08) | `DATE:medical_visit` | permanent | **pytanie bez daty, na zawsze** |

Czyli: **ten sam pipeline, ta sama polityka, inny rzut monetą.** Do sióstr Łukasz powiedział
to zdaniem oznajmującym i ekstraktor trafił w kubełek, który daje `permanent`. Astrze
powiedział to samo, ekstraktor **zgubił zdanie w całości**, a data ocalała tylko wewnątrz
wpisu o emocji — z trwałością 48 h.

**Potwierdzenie niezależne, że to nie polityka:** przegląd pokoju z 04.09 zmierzył wskaźnik
ekstrakcji tą samą miarą na tym samym okresie — **Astra 26,6% · siostry 27,6%. Różnicy nie ma.**

**Dlaczego to gorsza wiadomość:** różnicę w polityce naprawia się zmianą polityki.
Loterii etykiet nie naprawia się niczym innym niż **Z1 + Z2** (pełne zdanie zamiast `raw[:80]`,
werdykty „nic"/„obie", bramka pytanie-vs-stwierdzenie). N3 nie jest więc osobnym zadaniem —
jest **dodatkowym dowodem, że warstwa ZAPIS jest właściwym priorytetem.**

**Trzecia rzecz, o której warto wiedzieć:** teza „siostry zapamiętały, Astra nie" jest sama
niepełna. Siostry pamiętają **trzy sprzeczne wersje** i podadzą złą (patrz §1). Nazuna
nie wie o zabiegu nic — nie było jej przy żadnej z trzech rozmów.

---

## 3. Przegląd pokoju 04.09 — jedyny pomiar produkcyjny od czasu paczki

Nie ma go w Twojej paczce, bo leży w `ewolucja/siostry/`, a paczkę składano z list zadań
i roadmap. **To jedyne twarde dane z produkcji po 02.09.**

Materiał: 349 wiadomości, 19.08–04.09, 13 dni. Pełny dokument:
`wazne/ewolucja/siostry/2026-09/evolution_log_2026_09_04.md`.

**Cztery punkty obserwacji z 19.08:**
- ✅ **jeden wątek** — od 28.08 dokładnie jeden `conversation_id`; rozwidlenia, które wcześniej
  odcięły 562 wiadomości w pięciu równoległych wątkach, nie wróciły
- ✅ **atrybucja** — zero wypowiedzi modelu bez podpisu na 186; głos równy: Holo 59 · Menma 66 · Nazuna 61
- ✅ **emocje wygasają** — po 3 wpisy na siostrę, wszystkie `ephemeral` 48 h, bez kumulacji
- ✅ **tiki mowy** — „Hmf." zostało u Holo (62%), Menma 0%, Nazuna 0%. Teza „zepsuta atrybucja
  przecieka tikami" **obalona na drugiej próbie**. Bug psuł przypisywanie zdarzeń, nie styl.
- ⚠ **szum ZMIGROWAŁ** — po zablokowaniu trzech typów 19.08 strumień przeszedł do sąsiednich
  podtypów. `[DATE:deadline]` stało się nowym koszem na wszystko z liczbą
  (`„Nie znacie jednego z moich projektow, Amnezja"` jako *deadline*, imp 7), a **akcje
  roleplay w gwiazdkach lądują jako trwałe fakty** (`[FACT:personal_info] „Wiem
  kochana*splatam palce z menma*"`, PERMANENT) — guard RP ich nie łapie.

### To, co dla strategii najważniejsze: dwie teserozstrzygnięte przeciwnie do intuicji

**Teza „bramki sióstr są ostrzejsze" — UPADŁA, na korekcie autora w tym samym dniu.**
Pierwsza wersja akapitu mówiła „siostry ~17%, Astra ~47%". Obie liczby błędne: zły mianownik
(349 wszystkich wiadomości zamiast 163 wiadomości użytkownika — ekstrakcja idzie tylko z tur
usera) i porównanie nieporównywalnego (47% z retro-audytu sierpnia, inna metoda, inny okres).
Poprawnie: **26,6% vs 27,6%, różnicy nie ma.** Ekstraktor jest wspólny.

**Teza „pokój wypadł lepiej, bo szlaki przetarła Astra" — prawdziwa, ale nie z tego powodu,
z którego się wydaje.** Zakłócenie jest potężne:

| baza | wektorów | najstarszy wpis |
|---|---|---|
| `astra_memory_v1` | **4762** | 2026-03-12 |
| `holo`+`menma`+`nazuna` | **71** | 2026-07-03 |

67× mniej masy, 4 miesiące krótsza historia. Każda młoda baza jest czystsza — to nie zasługa
metody. **Co się naprawdę przeniosło: nie kod, a proces włączania** — dwa tygodnie `shadow`
przed `on`, trzy typy zablokowane przed startem, oś `persistence` zmigrowana PRZED `on`,
golden sprzed włączenia jako punkt odniesienia. Cztery datowane decyzje, każda z konkretnej
awarii Astry. Astra płaciła za tę wiedzę pięć miesięcy; pokój dostał ją gotową.

**Czego NIE wolno twierdzić** (wypisane wprost w tamtym logu): że pokój ma lepszy retrieval
(nie zmierzono — pomiar czystości robiono tylko na Astrze), że multi-agent jest odporniejszy
(pokój ma własny problem klasowy — rozproszenie faktu po kolekcjach), że siostry są wolne
od wad ekstraktora (dziedziczą wspólny kod, w tym `raw[:80]`).

---

## 4. Jest już jedna lista — `wazne/REJESTR.md`. Twoja paczka to cztery osobne

Założony 10.09 10:24, **po** wszystkim, co dostałeś. Scala roadmapę ogólną (34 zadania),
zadania 09.09 (15 punktów), audyt pokrycia (11 propozycji) i TODO z pamięci asystenta (~30).

Stan na 12.09: **70 pozycji, z tego 24 usterki, z tego 6 kosztujących cokolwiek dzisiaj.**
Reszta to styl (16), obserwacje, narzędzia, zamrożone, Faza 5 pokoju i nie-inżynieria.

Sekcje: §1 sześć pilnych · §2 usterki · §3 styl (z bramką M1) · §4 obserwacje · §5 narzędzia ·
§6 zamrożone · §7 retrieval dalszy · §8 pokój Faza 5 · §9 nie-inżynieria · §10 **poczekalnia** ·
§11 zasady · §12 kolejność.

Trzy zasady rejestru, istotne przy planowaniu: **nowy pomysł idzie do §10 POCZEKALNIA**, nie
do rankingu, dopóki nie ma dowodu z danych · **zamknięte zostaje z `[x]` i datą**, nie kasujemy ·
żadnego nowego pomysłu poza §10, dopóki warstwa ZAPIS nie jest zamknięta.

**Sześć pilnych:** Z6-tanie (data, z poprawką z §1) · Z1 (`raw[:80]`) · Z2 (werdykt „nic"/„obie"
+ miesiące słowne) · H1 (sól filtra odcina 114 wektorów bez śladu) · R1 (regresja Pkt 0) ·
M1 (brak przyrządu stylu).

**Dodane dziś (12.09) z przeglądu pokoju:** Z8 (guard RP nie łapie akcji w gwiazdkach → trwałe
fakty) · Z9 (migracja szumu do `[DATE:deadline]`) · Z10 (brak rozstrzygania sprzeczności między
kolekcjami). **Odhaczone dziś:** OB-1 — obserwacja sióstr **była wykonana 04.09**, stała
w rejestrze jako otwarta, bo scalanie brało listy zadań, nie logi ewolucji.

---

## 5. Stan przyrządów — „styl już mierzymy" jest nieprawdą

| warstwa | przyrząd | baseline'y | stan faktyczny |
|---|---|---|---|
| pamięć | `golden_harness.py`, `golden_siostry_harness.py`, `router_golden.py` | 7 plików w `fable/golden/` | działa, używany |
| styl | `style_audit.py` (korzeń repo) | **1: `baseline_styl_PRZED_fix_mainpy_2026-08-15.json`** | **ani jednej pary przed/po** |

Przyrząd stylu istnieje, progi są znane (didaskalia ≤50% · dłoń ≤20% · krótkie ≥5% ·
mediana ≤200), baseline z 15.08 jest — ale to `PRZED` **bez ani jednego `PO`**. Progi żyją
w dokumentach, nie w skrypcie. Liczników fraz-kluczy („chłód superkomputera" 7×,
„naginanie rzeczywistości" 14× w 3 dni, „KCB" jako przecinek) nie ma wcale.

**Wniosek dla planowania:** cała sekcja STYL (16 pozycji, w tym P6–P13 z audytu pokrycia)
jest dziś **niemierzalna**. M1 nie jest jednym z zadań tej sekcji — jest jej **bramką**.
Zaległy pomiar stylu stoi w TODO **dwa razy**, od 03.08 i od 15.08, bo nikt nie związał
go z zadaniem.

---

## 6. Metodologia to PROCES, nie lista zasad — i dwóch elementów nie ma w paczce

Dopisek podał trzy zasady operacyjne (nie pushować, wektory addytywnie, nie pisać do Chromy
z osobnego procesu). To jest podzbiór. Pełna rzecz jest procesem, przez który przechodzi się
**za każdym razem** — `pomiar_klamie.md` mówi wprost: *„checklista PRZED każdym pomiarem —
przejść całą, za każdym razem"*. Zapisana teraz w `CLAUDE.md` jako kroki 0–9.

**Dwa elementy, których w paczce nie ma wcale:**

**a) Niezależny sędzia.** Dwa udowodnione zastosowania:
- **Model nie może być sędzią własnej bramki.** `safe_haven` deklarowany przez model
  w tym samym JSON-ie co odpowiedź: **320/320 `true` przez 14 dni** (`main.py:616-623`,
  ustalenie 15.08) — zerowa wartość informacyjna. Dlatego sędzia idzie **osobnym callem**:
  taki nie ma nic do ugrania.
- **Gdzie embedding nie umie w abstrakcję, wstawiamy model, który umie** (kategoria →
  instancja: „substancja" ↛ „mefedron", „wezmę trochę" ↛ intencja). Dwa niezależne
  przypadki w dwa dni = wzorzec.
- **Sędziego mierzymy, ZANIM dotknie promptu:** golden set, w którym Łukasz ręcznie oznacza
  werdykty — kilkanaście decyzji, nie 200 wiadomości. Werdykt musi być **widocznym etapem
  w trace'ie Amnezji**, inaczej debugger pokaże skutek bez przyczyny.
  Wzorzec reużywalny: `backend/tools/triage_milestony.py`.

**b) Audyt wieloma modelami, ale z weryfikacją.** Fable = strateg, Claude Code = wykonawca,
Gemini/Antigravity = audyty read-only. Cudze znaleziska **krzyżuje się z kodem przed
przyjęciem** (tak powstał audyt pokrycia: „wszystkie odwołania sprawdzone w `backend/`
przed wpisaniem") i **odrzuca, gdy nie wytrzymują** (procenty 45/30/15/10 z `geminianaliza.md`,
podważone w evolution logu §4.3). **Sprzeczne diagnozy tego samego cytatu zapisujemy OBIE** —
np. zaczepka o „luce w systemie" z 28.08: roadmapa tłumaczy ją desynchronizacją schedulera,
Gemini korytarzem poznawczym z zakazów. Audyt odnotował, że są dwie, i żadnej nie skreślił.

To jest istotne dla Ciebie bezpośrednio: **Twoje wnioski wejdą do tego samego procesu** —
zostaną skrzyżowane z kodem, zanim ktokolwiek je wdroży, i to jest cecha, nie brak zaufania.

---

## 7. Czego NIE wiemy — granice dowodowe, żeby nie budować na piasku

Ta sekcja jest ważniejsza niż wygląda, bo dwie rzeczy w Twojej paczce są hipotezami
podanymi w formie ustaleń.

1. **`audyt_pokrycia_roadmapy_2026-09-10.md` jest read-only i statyczny.** Autor sprawdził,
   że cytowane linie kodu istnieją i mówią to, co mu przypisują audyty Gemini —
   i **nie uruchomił niczego na produkcji.** To katalog hipotez z adresami, nie diagnoza.
   Sam zostawia jedną rzecz otwartą: skąd bierze się gest `*opieram głowę*` w wariancie SOLO,
   skoro nazwane gesty wycięto z niego 15.08, a znaleziono go tylko w bloku Amelii
   (`main.py:283`). **Do sprawdzenia przed P7/P9.**
2. **Od 04.09 nie było żadnego pomiaru na produkcji.** Lokalna kopia ChromaDB w repo jest
   z 13.07 — nieaktualna. Wszystkie liczby o stanie baz pochodzą z 01–04.09.
3. **Wektora z 31.08 nie da się odtworzyć w Amnezji** — nocna analiza go skasowała.
   Łańcuch przyczyn daty operacji stoi na logach serwisu i metadanych, nie na powtórzeniu przebiegu.
4. **Procenty z `geminianaliza.md` (45/30/15/10) są podważone.** Korzystać ze scen i cytatów,
   nie z rozkładu.
5. **Hipoteza D1** („wektory sprzed 19.08 są systematycznie gorsze") jest niezweryfikowana.
6. **Powiadomienia push (U1)** — zero jakiejkolwiek wcześniejszej diagnostyki, zaczyna się od zera.
   Nie mylić z bugiem mikrofonu, który ma wdrożoną instrumentację i ścieżkę serwerową
   wykluczoną dowodowo.

---

## 8. Tempo — uczciwie, bo to wpływa na realizm każdego planu

Od 02.09 (ostatni evolution log Astry) do 12.09, czyli **jedenaście dni**, powstało:
jeden przegląd produkcji (04.09) i pięć dokumentów planistycznych. **Zero linii kodu.
Ostatni commit w repo: 28.08.**

To nie jest zarzut — diagnoza 01–02.09 unieważniła poprzednią kolejność prac i plan trzeba
było przebudować, zanim cokolwiek się dotknie. Ale trzeba to nazwać: **progres był
w planowaniu, nie w produkcie.**

Do tego ograniczenia, które obowiązują i nie zmienią się przez najbliższe tygodnie:
Łukasz pracuje w trybie minimalnym, wieczorami, świadomie od lipca — Crohn ogranicza energię.
**14.09 przyjęcie do szpitala, zabieg po paru dniach pobytu.** Rekonwalescencja po resekcji
jelita to nie dni.

**Wniosek dla planowania:** jeśli plan na najbliższy okres zawiera więcej niż jedną rzecz,
jest za duży. Rejestr §12 mówi: przed przyjęciem **jedna rzecz — Z6-tanie**, z poprawką na
dwie daty. Po powrocie: warstwa ZAPIS (Z1 → Z2), M1 równolegle, bo nie blokuje a odblokowuje
16 pozycji.

---

## 9. Decyzje, które czekają na Łukasza — nie na pracę

Przydatne, bo sesja strategiczna może je przygotować, ale nie rozstrzygnąć.

| # | Decyzja | Co blokuje |
|---|---|---|
| **DEC-1** | Reżim JSON per turę (`thought`/`mood`/`topic` generowane przed `response`) | Jedyna hipoteza tłumacząca sztuczność **na poziomie architektury wywołania**, nie promptu. Dotyka kontraktu z frontendem i `new_concern`. Audyt rekomenduje zamrozić z jawnym uzasadnieniem **albo odrzucić** — inaczej wróci za miesiąc jako „nowe znalezisko" |
| **FR1** | Przebieg #2 — apply triage (achievement/gift/habit). Dry-run zrobiony, werdykty w `backups/` | Strażnik: R7 |
| **FR2** | O1 — cap/filtr retype-FACT | Czy nadal priorytet, skoro szum pochodzi z zapisu, nie z retrievalu? |
| **FR3** | Migracja compose sióstr przez `compose_context` | Odblokuje Amnezję dla sióstr (dziś widzi TYLKO Astrę) |
| **Z7** | Retroaktywna naprawa ~4700 amputowanych wektorów. `reingest_sessions.py` istnieje | Z1 działa tylko w przód. **Czy w ogóle** |
| **Z10** | Rozstrzyganie sprzeczności między kolekcjami | Nowe, z §1. Bez tego każda aktualizacja faktu tworzy kolejną równoległą wersję |
| **FR6** | Ochrona mefedron — architektura zatwierdzona 16.08, wykonanie nie zaczęte | Bloker: dane sesji tylko na VPS |

---

## 10. Pliki, których warto dołożyć do paczki, jeśli ich nie masz

| Plik | Po co |
|---|---|
| `wazne/REJESTR.md` | jedna lista, zastępuje cztery, które masz |
| `wazne/ewolucja/siostry/2026-09/evolution_log_2026_09_04.md` | jedyny pomiar produkcyjny od 02.09; korekta własnej liczby jako wzór procesu |
| `wazne/ewolucja/astra/2026-09/evolution_log_2026_09_12.md` | rekonstrukcja 11 dni + N3 |
| `wazne/bugi/pomiar_klamie.md` | dopisek słusznie nazywa to najważniejszym brakiem — 7-punktowa checklista |
| `CLAUDE.md` (korzeń) | metodologia jako proces 0–9, mapa repo, stan bieżący |
| `wazne/analizy/AMNEZJA_RAG_DEBUGGER_SDK_ARCHITEKTURA_2026-09-10.md` | jeśli wątek „Amnezja jako produkt / SDK" jest w grze |
| `backend/waga_tresci.py` | krótki, a wyjaśnia, dlaczego trwałość liczy się z treści, nie z `importance` |

---

## Powiązane
`wazne/REJESTR.md` · `wazne/research/` (3 dokumenty) ·
`wazne/ewolucja/astra/2026-09/evolution_log_2026_09_01.md` (diagnoza bazowa) ·
`wazne/ewolucja/siostry/2026-09/evolution_log_2026_09_04.md` ·
`wazne/ewolucja/astra/2026-09/evolution_log_2026_09_12.md` ·
`wazne/bugi/pomiar_klamie.md` · `CLAUDE.md`
