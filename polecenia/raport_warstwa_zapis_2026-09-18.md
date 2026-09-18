# RAPORT: warstwa ZAPIS — Z2b i Z1 wdrożone, blocker przed Z13

**Data:** 2026-09-18 (wieczór) · **Autor:** sesja wykonawcza (Claude Code)
**Stan:** 2 z 4 zadań zrobione i potwierdzone na produkcji. Z13 wstrzymane — brak przyrządu.

---

## 0. Skrót

| # | zadanie | stan |
|---|---|---|
| **0** | krok 5b w metodologii — mapa klasy problemu przed kodem | ✅ dopisany i **od razu zmienił zakres 3 z 4 zadań** |
| **1** | **Z2b** — daty pisane słownie | ✅ wdrożone, kanarek zielony |
| **2** | **Z1** — koniec ucinania na 80. znaku | ✅ wdrożone, kanarek zielony |
| **3** | **Z13** — kategoria dla twórczości | ⛔ **wstrzymane: `golden_trafnosc.py` nie istnieje** |
| **4** | **Z12** — `fold()` i `ł` | ⏸ gotowe do zrobienia, czeka na decyzję o kolejności |
| **5** | H1 + H2 | nie zaczęte (po ustabilizowaniu zapisu) |

**Najważniejszy wynik:** zdanie z 28 sierpnia, od którego zaczęła się cała wrześniowa diagnoza,
zapisuje się teraz poprawnie. Szczegóły w §3.

---

## 1. Krok 5b — nowa reguła procesu i jej pierwszy efekt

Dopisane do `CLAUDE.md`:

> **Krok 5b — MAPA KLASY PROBLEMU. Obowiązkowa PRZED pierwszą linijką kodu.**
> Wypisz jawnie: (1) gdzie jeszcze w systemie ten sam typ problemu może występować,
> (2) czy ta konkretna naprawa to pokrywa, czy tylko jeden przypadek, (3) co świadomie
> zostawiasz poza zakresem i dlaczego. **Bez tej listy nie zaczynamy kodu.**
> Pusta lista też jest wynikiem — ale ma być zapisana, nie domyślna.

Uzasadnienie w pliku: tabela czterech wystąpień z jednego tygodnia, gdzie diagnoza była
trafna, naprawa poprawna, a zasięg za wąski (gesty, typy śmieciowe, progi kanałów, oraz
Twój scenariusz — naprawiono *czy wolno zapisać*, nie sprawdzając *czy jest gdzie zapisać*).

**Reguła zwróciła się natychmiast — mapa zmieniła zakres trzech z czterech zadań:**

| zadanie | zakres wg rejestru | zakres po mapie |
|---|---|---|
| Z2b | jeden regex | **dwa miejsca** + rozjazd foldowania między nimi |
| Z1 | `raw[:80]` → granica zdania | bez zmian (potwierdzone: jedno miejsce) |
| Z13 | kategoria dla scenariusza | **cała dziedzina** — muzyka i wideo mają ten sam brak |
| Z12 | `fold()` w jednym pliku | **trzy kopie, dwie poprawne, jedna zepsuta** |

Pełna mapa: `polecenia/work-order_warstwa_zapis_2026-09-18.md`.

---

## 2. Z2b — daty pisane słownie ✅

**Commit:** `bbff52d` · **Pliki:** `semantic_extractor.py`

### Co zrobione
1. **`FUTURE_DATE_PATTERNS`** (bramka „czy to termin") — wzorzec
   `\b\d{1,2}\s+(stycznia|…|grudnia)\b` w formach foldowanych.
2. **`_extract_date_value`** (wartość „jaka to data") — ten sam wzorzec + konwersja na
   `YYYY-MM-DD`. Rok bieżący, a gdy data minęła o ponad 30 dni — następny.

### Przy okazji: naprawiony rozjazd, który działał do dziś

`_has_appointment_marker` foldował tekst i szukał form **bez** ogonków, a `_extract_date_value`
używało gołego `.lower()` i szukało form **z** ogonkami. Skutkiem **trzy grupy wzorców były
martwe od zawsze** — `za tydzień`, `miesięcy`, `dziś` oraz cały słownik dni tygodnia
w `weekdays_pl` nigdy nie trafiały, bo docierał do nich tekst już zfoldowany.

Zmierzone przed zmianą:

| tekst | bramka „to termin?" | wyliczenie daty |
|---|---|---|
| `W piatek mam wizyte` *(tak piszesz)* | TAK | **NIE** |
| `za tydzień przyjdę` | **NIE** | TAK |

### Kanarek — test offline (data odniesienia 18.09)

```
14 wrzesnia mam zabieg        -> termin, 2026-09-14
mam zabieg 16 września        -> termin, 2026-09-16
W piatek mam wizyte           -> termin, 2026-09-25   (było: brak daty)
za tydzien / za tydzień       -> oba działają          (było: tylko jedno)
5 pazdziernika kontrola       -> termin, 2026-10-05
31 lutego                     -> brak daty, bez wyjątku
dzisiaj pracowalem nad kodem  -> NIE termin            (bez regresji)
```

### Kanarek — na produkcji, po deployu

```
"Umowilem sie na kontrole 5 pazdziernika"
→ [DATE:appointment] 2026-10-05: Umowilem sie na kontrole 5 pazdziernika
```

Wcześniej ta bramka odrzucała daty słowne, więc encja `appointment` w ogóle nie powstawała.

### Czego Z2b NIE załatwia — ważne przy odbiorze

Kanarek **przed** zmianą pokazał, że `„14 wrzesnia mam zabieg w szpitalu"` idzie do
`FACT:health`, bo `DATE:medical_visit` ma tam **0,68 i przegrywa w anty-multi-label**.
To jest **Z2a**, osobne zadanie. Z2b jest warunkiem **koniecznym** (bez niego data i tak
by się nie wyliczyła), **nie wystarczającym**. Krótsza forma zdania działa, dłuższa nie.

---

## 3. Z1 — koniec ucinania na 80. znaku ✅

**Commit:** `8fe7d37` · **Pliki:** `semantic_pipeline.py`

### Co zrobione
Nowa funkcja `_skroc_do_zdania`: bierze **całe zdania** do progu `MIN=60`, przerywa gdy
dobicie kolejnego przekroczyłoby `MAX=240`, a pojedyncze zdanie dłuższe niż MAX tnie
**na granicy słowa**, nie w środku wyrazu. Dodany brakujący `import re`.

### Kanarek — przed i po, na tym samym zdaniu

```
PRZED (101 zn.): [DATE:medical_visit] Dzisiaj rano poszedlem do kliniki i lekarz
                 powiedzial mi ze zwezenie jelita jest
PO    (129 zn.): [DATE:medical_visit] Dzisiaj rano poszedlem do kliniki i lekarz
                 powiedzial mi ze zwezenie jelita jest powazniejsze niz myslelismy
```

Przed zmianą zdanie urywało się dokładnie przed informacją, po co w ogóle padło.
Krótkie wpisy bez zmian (`„Wyznaczyli mi date zabiegu. 14 wrzesnia"` = 39 znaków, w całości).

### Zakres wg mapy
Przejrzałem wszystkie obcięcia `[:N]` w `backend/`. **Obcięcie treści w ścieżce zapisu
trwałego jest w tym jednym miejscu.** `[:200]` w `fact_store`/`cross_talk` to prezentacja
w prompcie, `[:500]` to cap na JSON stanu, `[:100]` to skrót w powiadomieniu (pełny tekst
leci w `full=`), `[:120]` w `main.py` to R1 — osobne zadanie.

Z1 działa **w przód**. ~4700 już amputowanych wektorów zostaje — to `Z7`, osobna decyzja.
`Z5` (prefiksy `[MILESTONE:…]`, dwie linie niżej w tej samej funkcji) **świadomie nie ruszany**,
zgodnie z Twoją decyzją.

---

## 4. ⭐ Dowód, że Z2b + Z1 zamknęły przypadek źródłowy

Przepuściłem przez produkcję **zdanie z 28 sierpnia** — to, którego zgubienie uruchomiło
całą wrześniową diagnozę. Wtedy nie utworzyło **żadnego wektora** (log 01.09 §2.4).
Dziś:

```
[DATE:medical_visit] 2026-09-14: Wyznaczyli mi date zabiegu. 14 wrzesnia
```

**Właściwa kategoria · wyliczona data · całe zdanie.** Trzy niezależne awarie, które wtedy
złożyły się na ten jeden brak, są naprawione: ekstraktor rozpoznaje datę słowną (Z2b),
wylicza jej wartość (Z2b, drugie miejsce), i nie ucina zdania w połowie (Z1).

---

## 5. ⛔ Blocker przed Z13: przyrządu nie ma

Work-order zakładał golden przed/po dla Z13, bo nowe prototypy zmieniają rozkład
`confidence` dla **wszystkich** wiadomości (anty-multi-label bierze `max`). Poszedłem po ten
golden i:

**`golden_trafnosc.py` nie istnieje.** Sprawdzone: nie ma go w repo, **nigdy nie był
commitowany** (`git log --all --diff-filter=AD` — pusto), nie ma go na VPS ani w `/tmp`.

A metodologia w trzech miejscach każe używać wyłącznie jego:
- `CLAUDE.md` krok 3: *„wyłącznie `golden_trafnosc.py`, nigdy golden objętościowy"*
- `REJESTR.md` §11 pkt 2: to samo
- `pomiar_klamie.md`: *„`golden_trafnosc.py` — mierzy trafność (recall + czystość),
  nie objętość. **To jest właściwy przyrząd**"*

**Jedyny golden, który mamy** — `golden_harness.py` — zapisuje `final_count`, `prompt_len`,
`hard_facts`, `milestones_in_final`. Czyli **objętość**. To dokładnie Rodzina A z `pomiar_klamie.md`,
ta, która zatwierdziła trzy złe zmiany (`main_n=8`, MMR, kanał leksykalny).

### Co to znaczy

Narzędzie z 21.08, na którym stoi cała metodologia pomiarowa, **zginęło** — powstało,
było używane (są z niego wnioski w `pomiar_klamie.md` #7 i #8), i nigdy nie trafiło do repo.
To ten sam wzorzec, co reszta tego tygodnia: zasada *„diagnostyka zostaje w kodzie"* istnieje
w `CLAUDE.md`, a przyrząd, którego dotyczy, nie został zachowany.

### Dobra wiadomość

Probes w `golden_harness.py` mają w **komentarzach** wpisane, co powinno wrócić:
```python
# 1. Fleksja polska (altanka) — 4 echo-docs z 2026-07-01 to JEDYNA tresc altanki
("F1a", "1_fleksja", "a pamietasz co chcialem pisac w altance", 0, False),
```
Autor wiedział, jaka jest odpowiedź — po prostu nie zakodował tego jako asercji.
**Dorobienie pola „oczekiwane" do istniejącego harnessu jest tańsze niż pisanie od zera.**

---

## 6. Decyzja do podjęcia — trzy opcje

1. **Dorobić asercje do `golden_harness.py`** (~pół godziny), potem Z13 z prawdziwym
   pomiarem przed/po. Golden trafności będzie potrzebny na stałe, nie tylko tutaj.
2. **Zrobić najpierw Z12** — ma czysty kanarek („nie będę ćpał" → `permanent`), dotyczy
   ścieżki zapisu, nie wymaga pomiaru retrievalu. Golden przy Z13.
3. **Wejść w Z13 bez goldenu** — **odradzam**. To byłoby jedenaste wystąpienie
   `pomiar_klamie.md`, i akurat przy zmianie, która rusza rozkład dla wszystkich wiadomości.

**Rekomendacja: 2 → 1 → Z13.**

---

## 7. Stan produkcji po tej turze

- VPS na `8fe7d37`, serwis `active`, health OK, **4822 wektory** (powyżej progu kanarka).
- Start czysty, zero tracebacków.
- Rytm wiadomości bez zmian od rana: nocna + poranna **pon/śr/pt**, spontaniczna wyłączona.
  Pierwsze uruchomienie w nowym rytmie: **pon 21.09, 03:00 i 07:00**.
- Backupy `.env` na VPS: `.env.bak_2026-09-13`, `.env.bak_2026-09-18`.

## Czego NIE sprawdziłem

- **Z2b i Z1 są potwierdzone kanarkiem na pojedynczych zdaniach**, nie pomiarem na całym
  goldenie — bo goldenu trafności nie ma (patrz §5). Nie wiem, czy zmiana długości wpisów
  (Z1) nie wpłynęła na retrieval dla innych zapytań. **To jest realne ryzyko i trzeba je
  zmierzyć, gdy przyrząd powstanie.**
- **Nie zmierzyłem mediany długości wpisu po zmianie** — Z1 działa w przód, więc efekt
  będzie widoczny dopiero na nowych wpisach, za kilka dni.
- **Z2a (margines w anty-multi-label) nie tknięty** — dłuższe zdania z datą nadal trafiają
  do `FACT:health` zamiast `DATE:medical_visit`.
