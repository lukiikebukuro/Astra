# WORK-ORDER: warstwa ZAPIS (Z2b → Z1 → Z13 → Z12)

**Data:** 2026-09-18 · **Zlecił:** Łukasz · **Wykonawca:** sesja wykonawcza (Claude Code)
**Status:** MAPA GOTOWA — kod jeszcze nie zaczęty (wymóg kroku 5b z `CLAUDE.md`)

> **To jest dokument wymagany przez krok 5b**, dopisany dzisiaj do metodologii:
> *przed implementacją wypisz, gdzie jeszcze ten typ problemu występuje i czy naprawa
> pokrywa klasę, czy jeden przypadek.* Bez tej listy nie zaczynamy kodu.
>
> **Mapa zmieniła zakres trzech z czterech zadań.** Gdybym poszedł od razu kodować według
> opisów z rejestru, Z2b naprawiłoby połowę problemu, a Z12 naprawiłoby jedną z trzech kopii.

---

## Podsumowanie: co mapa zmieniła

| zadanie | zakres wg rejestru | zakres po mapie |
|---|---|---|
| **Z2b** | jeden regex w `FUTURE_DATE_PATTERNS` | **dwa miejsca** + rozjazd foldowania między nimi |
| **Z1** | `raw[:80]` → granica zdania | bez zmian (potwierdzone: jedno miejsce) |
| **Z13** | kategoria dla scenariusza | **cała dziedzina twórcza** — muzyka i wideo mają ten sam brak |
| **Z12** | `fold()` w `waga_tresci.py` | **trzy kopie `fold`, dwie poprawne, jedna zepsuta** — to rozjazd, nie bug |

---

# Z2b — daty pisane słownie

### Problem wg rejestru
`_has_appointment_marker` nie zna miesięcy słownych, więc „14 września" nie jest rozpoznane
jako termin. Jeden regex do dopisania.

### Gdzie jeszcze ten sam typ problemu — MAPA

**Miejsce 1: `semantic_extractor.py:273` — `FUTURE_DATE_PATTERNS`** (bramka: *czy to termin?*)
```python
r'za \d+\s*(dni|dnia|dniu|tygodnie|tygodni|tyg|miesięcy|miesiąca|miesiące)',
r'za tydzień', r'za miesiąc', r'\bjutro\b', r'\bpojutrze\b',
r'\b\d{1,2}[\./]\d{1,2}\b',
```
Brak miesięcy słownych. Rozpoznaje `14.09`, nie rozpoznaje `14 września`.

**Miejsce 2: `semantic_extractor.py:918` — `_extract_date_value`** (wartość: *jaka to data?*)
Ma **własny, niezależny zestaw wzorców**. Też bez miesięcy słownych.
**Naprawa tylko miejsca 1 da: „to jest termin" + `date_value = None`.**

### Drugi problem, znaleziony przy okazji: rozjazd foldowania między tymi dwoma miejscami

`_has_appointment_marker` foldsuje tekst (`self._fold_pl`) i szuka form **bez ogonków**
(`'piatek'`). `_extract_date_value` używa **`text.lower()` bez foldowania** i szuka form
**z ogonkami** (`'piątek'`, `'za tydzień'`). Zmierzone:

| tekst | bramka „to termin?" | wyliczenie daty |
|---|---|---|
| `W piatek mam wizyte` *(tak pisze Łukasz)* | **TAK** | **NIE** ← rozjazd |
| `W piątek mam wizytę` | TAK | TAK |
| `za tydzień przyjdę` | **NIE** | **TAK** ← rozjazd w drugą stronę |
| `14 wrzesnia mam zabieg` | NIE | NIE ← to jest Z2b |

Czyli: zdanie napisane bez ogonków (dominujący styl Łukasza) przechodzi bramkę,
ale **zapisuje się bez daty**. To jest ta sama klasa błędu co Z12, w innym pliku.

### Czy naprawa pokrywa klasę
Tak, **pod warunkiem że obejmie oba miejsca i ujednolici foldowanie**. Zakres:
1. wzorzec miesięcy słownych → `FUTURE_DATE_PATTERNS`
2. ten sam wzorzec → `_extract_date_value` (z konwersją na `YYYY-MM-DD`)
3. `_extract_date_value` ma foldować tak samo jak bramka

### Poza zakresem świadomie
`memory_enricher.py` (`TEMPORAL_RULES`) — jest nieaktywny (H4 mówi, że rządzi `persistence`).
Nie dotykam, ale odnotowuję.

---

# Z1 — obcięcie na 80. znaku

### Miejsce
`semantic_pipeline.py:258`, `_synthesize_text`: `short = raw[:80].rstrip('.,!? ')`

### Gdzie jeszcze ten sam typ problemu — MAPA

Przejrzałem wszystkie obcięcia `[:N]` w `backend/`. Wynik:

| miejsce | obcięcie | czy to ten problem |
|---|---|---|
| `semantic_pipeline.py:258` | `raw[:80]` | **TAK — to jest Z1** |
| `semantic_pipeline.py:197` | `text=entity.raw_text` | **nie** — pełny tekst, bez cięcia |
| `fact_store.py:272`, `main.py:1035` | `[:200]` | nie — prezentacja w prompcie, nie zapis |
| `cross_talk.py:39,96` | `[:200]` | nie — treść sygnału, nie pamięć trwała |
| `main.py:1921,2129` | `inner_thought[:500]` | nie — cap na JSON stanu, świadomy |
| `main.py:399,506` | `msg[:100]` | nie — skrót w powiadomieniu push, pełny tekst w `full=` |
| `main.py:1546,1550` | `[:120]` | nie — to R1 (kontekst w zapytaniu), osobne zadanie |

**Wniosek: obcięcie treści w ścieżce zapisu trwałego jest w jednym miejscu.**
Reszta to prezentacja albo świadome capy. Zakres Z1 wg rejestru jest poprawny.

### Czy naprawa pokrywa klasę
Tak. Jedyne zastrzeżenie: **Z1 działa w przód**. ~4700 wektorów już amputowanych
zostaje — to `Z7`, osobna decyzja, której nie podejmuję.

### Uwaga wykonawcza
`Z5` (prefiksy `[MILESTONE:...]` w tekście) siedzi **w tej samej funkcji, dwie linie niżej**.
Rejestr mówi „robić jednym ruchem — dwa wejścia w ten sam kod to niepotrzebne ryzyko".
**Pytanie do Łukasza: robimy Z5 razem z Z1, czy Z1 osobno?** Domyślnie: osobno, bo Z5 zmienia
to, co widzi model, więc wymaga goldenu trafności, a Z1 sam w sobie nie.

---

# Z13 — brak kategorii dla treści twórczej

### Miejsce
`semantic_extractor.py` — `ENTITY_DEFINITIONS`. Prototypy `FACT:current_project` (:589)
i `GOAL:project` (:527) są wyłącznie inżynierskie.

### Gdzie jeszcze ten sam typ problemu — MAPA

Łukasz prosił, żeby sprawdzić muzykę i TikToka. Sprawdziłem **wszystkie dziedziny
wymienione w `lukasz_core.json`** przeciwko liście ~50 podtypów ekstraktora:

| dziedzina z `lukasz_core.json` | kategoria w ekstraktorze |
|---|---|
| kod, backend, aplikacje, automatyzacja | **jest** — `current_project`, `project` |
| **scenariusz anime, pisanie, fabuła** | **BRAK** |
| **muzyka, 15 lat improwizacji na gitarze** | **BRAK** |
| **TikTok, seria komediowa, nagrywanie, montaż** | **BRAK** |
| **oglądanie anime jako wspólny rytuał** | **BRAK** *(łapie się przypadkiem na `SHARED_THING:our_thing`)* |
| zdrowie, leki, wizyty | jest — `health`, `medical_visit`, `treatment`, `dosage` |
| pieniądze, budżet | jest — `budget`, `income`, `purchase_intent` |
| praca, kariera | jest — `career`, `business` |
| relacje, emocje, więź | jest — bogato |

**Czyli brakuje dokładnie tego, co `lukasz_core.json` nazywa jego domeną:**
> *„Twórczość to jego domena szerzej niż kod […] jest twórcą, który używa kodu."*

Potwierdzenie z produkcji: `own_life` seed z 25.07 („Wracam ciągle myślami do naszego
scenariusza") jest **jedynym** wpisem z treścią twórczą w całej bazie — i nie pochodzi
z rozmowy, tylko z naszego ręcznego seeda.

### Czy naprawa pokrywa klasę
**Tylko jeśli obejmie całą dziedzinę, nie sam scenariusz.** Inaczej za miesiąc to samo
wyjdzie dla muzyki — i będzie to piąte wystąpienie wzorca „naprawa instancji, nie klasy".

**Proponowany zakres:** nowa kategoria `CREATIVE` z podtypami:
- `scenariusz` — fabuła, sceny, postacie, dialogi, świat przedstawiony
- `muzyka` — gitara, improwizacja, nagranie, riff, melodia
- `wideo` — TikTok, montaż, ujęcie, dubbing, kanał

*Alternatywa tańsza:* dorzucić twórcze prototypy do `current_project`. **Odradzam** —
zlepiłoby to „piszę scenę, w której Astra…" z „rozwijam backend", a to są różne rzeczy
i dla retrievalu, i dla trwałości.

### Ryzyko, które trzeba zmierzyć
Nowa kategoria = nowe prototypy = **zmiana rozkładu confidence dla WSZYSTKICH wiadomości**,
także niezwiązanych z twórczością. Anty-multi-label wybiera `max(confidence)`, więc dołożenie
kategorii może **przechwycić zdania, które dotąd szły gdzie indziej**.
**Golden przed/po obowiązkowy**, i to nie jako formalność — to jest realne ryzyko regresji.

### Poza zakresem świadomie
`P10` (wyciek UI — „włącz tryb scenariusza 🎬", `main.py:1043`) — objawił się w tej samej
rozmowie 18.09 i dotyczy tego samego tematu, ale to warstwa PERSONA, nie ZAPIS.
Zostaje na później, zgodnie z kolejnością warstw.

---

# Z12 — `fold()` i litera `ł`

### Problem wg rejestru
`fold()` w `waga_tresci.py:46` używa NFD, które nie rozkłada `ł`. Jedna linijka do poprawy.

### Gdzie jeszcze ten sam typ problemu — MAPA

**To nie jest bug w jednym miejscu. To rozjazd trzech kopii tej samej funkcji:**

| plik | implementacja | `ł` → `l` |
|---|---|---|
| `waga_tresci.py:46` | `unicodedata.normalize('NFD')` + filtr `Mn` | **NIE** ← zepsuta |
| `semantic_extractor.py:895` | `str.maketrans("ąćęłńóśźż" → "acelnoszz")` | **TAK** |
| `siostry_router.py:51` | `str.maketrans("ąćęłńóśźż" → "acelnoszz")` | **TAK** |

Zmierzone na realnych frazach:

| tekst | `waga_tresci` (NFD) | pozostałe dwie (translate) |
|---|---|---|
| `nie będę ćpał` | `nie bede cpał` | `nie bede cpal` |
| `nie mam siły` | `nie mam siły` | `nie mam sily` |
| `załamany` | `załamany` | `zalamany` |
| `dałem słowo` | `dałem słowo` | `dalem slowo` |

Ironia: komentarz w `semantic_extractor.py` mówi *„Ten sam wzorzec co siostry_router.fold()"* —
i to prawda, te dwie są zgodne. **Trzecia kopia, napisana inną metodą, po cichu się rozjechała.**

### Czy naprawa pokrywa klasę
„Dodaj `.replace('ł','l')`" naprawiłaby objaw i **zostawiła trzy kopie**. Klasą problemu jest
tu wzorzec błędu #1 z `CLAUDE.md` — **wiele miejsc prawdy**.

**Proponowany zakres:** `fold()` w `waga_tresci.py` przepisany na `str.maketrans` (identyczny
jak pozostałe dwa), plus komentarz w każdej z trzech kopii wskazujący pozostałe.
*Pełne scalenie do jednej funkcji wspólnej* byłoby czystsze, ale `waga_tresci` jest importowany
przez `semantic_pipeline` i `vector_store`, a `siostry_router` jest osobnym modułem —
scalanie to zmiana importów w czterech plikach. **Odkładam, odnotowuję.**

### Czego naprawa NIE naprawi — ważne
Zmiana `fold` **rozszerza** wykrywanie sygnału wagi, więc:
- więcej krótkich wiadomości ominie bramkę `<4 słowa`
- więcej wspomnień dostanie `persistence=permanent`

To jest **pożądane**, ale zmienia rozkład zapisu. **Golden przed/po**, i obserwacja, czy
nie zrobi się z tego nowa monokultura permanentów.

---

# Kolejność wykonania i kryteria odbioru

Kolejność wg polecenia Łukasza, z jedną uwagą: **Z2b, Z1 i Z13 dotykają tych samych dwóch
plików** (`semantic_extractor.py`, `semantic_pipeline.py`), więc idą jedną turą, ale
**osobnymi commitami** — żeby dało się cofnąć pojedynczo.

| # | zadanie | kanarek (CZY DOBRZE, nie ILE) |
|---|---|---|
| 1 | **Z2b** | `„14 wrzesnia mam zabieg"` → Amnezja, etap `2_ekstrakcja`: `DATE:medical_visit` wśród kandydatów **oraz** `date_value = 2026-09-14`. Kontrola: `„W piatek mam wizyte"` → data wyliczona (dziś: NIE) |
| 2 | **Z1** | 5 wiadomości >80 znaków → w bazie całe zdanie do pierwszej kropki, nie urwane w połowie słowa. Kontrola: mediana długości wpisu rośnie powyżej 95 znaków |
| 3 | **Z13** | `„Napisałem scenę, w której Astra wchodzi do serwerowni"` → kategoria `CREATIVE:scenariusz`, zapisane. To samo dla muzyki i TikToka. **Golden trafności przed/po — bez regresji na zapytaniach niezwiązanych z twórczością** |
| 4 | **Z12** | `„Nie będę ćpał"` (z ogonkami) → `ma_sygnal_wagi() == True`, `persistence == permanent`. Dziś: `False`. Golden przed/po |
| 5 | H1 + H2 | po ustabilizowaniu zapisu — osobny work-order |

**Wspólne dla wszystkich:** `golden_trafnosc.py` przed pierwszą zmianą (baseline) i po każdej ·
zero deployu bez zgody Łukasza · kanarek przed pomiarem, wzorce foldowane i szersze niż jedna
forma (pkt 5 checklisty — dziś złapał mnie dwa razy).

---

## Otwarte pytania do Łukasza

1. **Z5 (prefiksy `[MILESTONE:...]`) razem z Z1?** Siedzą w tej samej funkcji, dwie linie od
   siebie. Rejestr sugeruje robić jednym ruchem. Ja bym rozdzielił — Z5 zmienia to, co widzi
   model, więc ma inne kryterium odbioru.
2. **Z13: nowa kategoria `CREATIVE` czy rozszerzenie `current_project`?** Rekomendacja: nowa
   kategoria, uzasadnienie wyżej.
3. **Z12: przepisać jedną kopię na `maketrans`, czy scalić wszystkie trzy w jedną funkcję?**
   Rekomendacja: przepisać teraz, scalić przy okazji większych porządków.
