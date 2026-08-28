# AUDYT AMNEZJI — 2026-08-28

**Zakres:** czy Amnezja pokazuje prawdę o tym, co dostaje model.
**Metoda:** wyłącznie read-only, na produkcji (`859b36e`). Zmiany z 26.08 (C-2, synchronizacja
pokoju sióstr) NIE są wdrożone, więc audyt dotyczy kodu, który realnie chodzi.
**Powód:** Amnezja przestała być ciekawostką i stała się konstrukcją nośną — stoi na niej
`golden_trafnosc.py`, a na nim decyzje o parametrach pamięci. Nigdy nie była testowana.

> **Uwaga do poprzedniej rozmowy (27–28.08):** przedstawiłem wtedy listę „sześciu trybów awarii,
> które już wystąpiły". Było to nieścisłe — dwa z nich nigdy się nie zmaterializowały
> (podwójne lustro sióstr złapane przed rozjazdem; `now_override` u sióstr nie miał czego
> symulować). Ten dokument zastępuje tamtą listę i opiera się wyłącznie na pomiarach.

---

## WERDYKT

**Amnezja nie kłamie o tym, co pokazuje. Jest natomiast NIEKOMPLETNA co do tego, skąd to się bierze —
i ma jeden zrealizowany rozjazd w piaskownicy.**

Konkretnie: **jedna czwarta wpisów w prompcie Astry nie ma w trace'ie żadnego źródła.**
Nie da się prześledzić, skąd przyszły. Wszystko, co Amnezja *twierdzi*, jest prawdą — ale
o części promptu nie twierdzi nic, a wygląda to jak twierdzenie kompletne.

Ocena użyteczności: **wiarygodna jako podgląd, jeszcze nie audytowalna jako przyrząd.**

---

## USTALENIA

### F1 — ROZJAZD ZREALIZOWANY: piaskownica Astry składa historię inaczej niż produkcja
**Waga: wysoka. Nowe.**

Produkcja (`chat`, `main.py:1690-1697`) dokleja do tur użytkownika **znaczniki upływu czasu**:
```
[— 3 dni później —]
[— przerwa 5 godz. —]
```
Powstały jako WO-2 (25.07), bo model nie widział luk między turami — stąd persystencja pozy
z 18→20.07. Opcjonalnie działa też sanitizer WO-6 (dziś za flagą, domyślnie `false`).

Amnezja (`debug_inspect`, gałąź `else`, `main.py:3406-3412`) składa `contents` **zwykłą pętlą**:
bez znaczników czasu, bez sanitizera.

Parametry generacji są identyczne (`max_output_tokens=8192`, `temperature=0.85`,
`thinking_budget=4096`, JSON) — rozjazd dotyczy wyłącznie historii.

**Zasięg:** tylko `generate=true` (piaskownica). Trace odczytu nietknięty.
**Znaczenie:** to jest BLIŹNIAK błędu naprawionego 25.08 dla sióstr. Naprawiłem jedną kopię
i przeszedłem obok drugiej, stojącej 15 linijek niżej. Dowód, że `grep` nie zastępuje metody.

### F2 — DZIURA W ŚLEDZENIU: dwa wpisy w `8_final` nie istnieją w żadnym wcześniejszym etapie
**Waga: wysoka. Nowe. Powtarzalne w 5/5 zapytań.**

Sprawdzone niezmiennikami na pięciu zapytaniach. Za każdym razem `8_final` zawiera dwa wpisy,
których nie ma w `7_kanal1_final`, `5b_own_life`, `5_milestony`, `6_po_mmr_facts`,
`4_po_temporal` ani `2_po_wykluczeniu`. Treść:

```
"Kiedy user odnosi sukces — cieszę się SZCZERZE. Nie mówię 'a nie mówiłam'..."
"Kiedy user czuje się winny, bezużyteczny, ciężarem dla rodziny..."
```

To **Kanał 2 (`character_core`)**. Razem z **Kanałem 3 (`md_import`)** nie ma w trace'ie
ANI JEDNEGO etapu. Przy `8_final` = 7–8 wpisów oznacza to, że **~25% promptu materializuje się
znikąd** z punktu widzenia debuggera.

**To jest bezpośrednia przyczyna zgłoszenia „anty-lustro wraca" (25.08).** Zasada pojawiała się
w podglądzie i nie było jak prześledzić, skąd. Nie dało się, bo trace jej nie zawiera.

### F3 — KANAŁ LEKSYKALNY NIEWIDOCZNY, a nazwa etapu myli
**Waga: średnia. Nowe.**

```
1_pula_surowa        30
2_po_wykluczeniu     36   <- ROŚNIE
```
Etap nazwany „po wykluczeniu" **przyrasta**, bo kanał leksykalny (`$contains`) wstrzykuje wpisy
pomiędzy etapami 1 i 2, nie mając własnego etapu. Ma tylko `print` do logu serwisu.

Skutek praktyczny: kanał, którego szukaliśmy trzy dni (sprawa LDI), jest w debuggerze
niewidoczny. Widać wyłącznie niewyjaśniony przyrost pod mylącą nazwą.

### F4 — SCHEMAT WYPEŁNIONY W POŁOWIE: `entity_type` nie jest zapisywany NIGDZIE
**Waga: średnia. Potwierdzone twardo.**

Na **4729 wpisach** `astra_memory_v1`:
```
entity_subtype    3732 wpisow
entity_type          0 wpisow   <- pole nie istnieje w ogóle
```
`vector_store.py:219` przekazuje `entity_type` do `compute_persistence(...)`, ale **nie zapisuje go
do metadanych**. Typ semantyczny przeżywa wyłącznie jako prefiks w tekście (`[FACT:health] ...`),
obecny na 4667 z 4729 wpisów.

`main.py:883` ma cichy fallback:
```python
entity_type = meta.get('entity_type', meta.get('source', '?'))
```
Przez co **każda linia wspomnienia w prompcie powtarza to samo słowo dwa razy**:
```
- [extracted_fact, type:extracted_fact, importance:5] ...
```
Dwa koszty: (1) filtrowanie po typie w metadanych jest niemożliwe — cicho nic nie dopasowuje;
(2) marnujemy tokeny w każdej turze na pole, które nie niesie informacji.

To samo dotyczy sióstr (44 wpisy, wszystkie bez `entity_type`) — czyli moja hipoteza z 26.08,
że „jedno z dwóch narzędzi kłamie", była błędna. Nie kłamie żadne. Zapisywacz jest niekompletny.

### F5 — DOBRA WIADOMOŚĆ: zakładka ZAPIS jest solidna
**Hipoteza z 26.08 OBALONA.**

`/api/debug/inspect-write` na zdaniu „Boli mnie brzuch od wczoraj, chyba znowu Crohn" zwraca
pełen przewód decyzyjny: bramkę długości, **wszystkich 7 kandydatów z confidence**, zwycięzcę,
listę odrzuconych, importance, trwałość i finalny tekst wspomnienia. Co więcej — sama się
denuncjuje:

```json
"uwaga": "ta bramka ZAWSZE wybiera jakas etykiete - nie istnieje werdykt 'nic'"
```

**To jest w praktyce gotowe „dlaczego ta etykieta"** z Twojej listy życzeń do Amnezji.
Nie trzeba go budować — trzeba go pokazać w UI.

Efekt uboczny: audyt na żywo pokazał `importance: 10` za zdanie o bólu brzucha oraz
`DATE:inventory_status` wśród kandydatów (0.46) — czyli oba znane problemy ekstraktora,
widoczne jak na dłoni.

### F6 — POKRYCIE: Amnezja odbija 2 z 6 ścieżek generacyjnych
**Waga: strukturalna.**

| ścieżka | lustro w Amnezji |
|---|---|
| `chat` (Astra) | ✅ jest, ale **rozjechane** (F1) |
| `_generate_sister` (siostry) | ✅ poprawne (wspólna funkcja od 25.08) |
| `amelia_chat` | ❌ brak |
| `_wspolny_generate` | ❌ brak |
| `_scene_as_found` (narrator sceny) | ❌ brak |
| `nocna_analiza.py` — nocna + poranna | ❌ brak (2 wywołania Gemini poza `main.py`) |

Trzynaście miejsc w kodzie składa `contents` ręcznie. Każde to potencjalny F1.

Najboleśniejsza luka to **ścieżki proaktywne** — tam gryzły zmyślone daty („wczorajsze CV"
o zdarzeniu sprzed 3 dni) i znikająca wiadomość dnia, czyli dokładnie te bugi, które kosztowały
najwięcej sesji. Nie mamy tam żadnego wglądu.

### F7 — NIEZMIENNIKI, KTÓRE PRZESZŁY
Rzetelności wymaga wypisanie też tego, co jest w porządku:

- **I2:** `9c_po_budzecie` ⊆ `9b_final_prompt` — zawsze. Budżet nie wymyśla wpisów.
- **I3:** każdy wpis z `9c` realnie ląduje w prompcie. Nic nie ginie po ostatnim etapie.
- **I4:** liczba linii w prompcie **co do jednej** zgadza się z `9c` (5+2=7, 6+2=8) — w 5/5 zapytań.
  Podział na `[WSPOMNIENIA]` i `[TWOJE ZASADY]` jest szczelny.

Czyli: **od momentu, w którym wpis pojawia się w trace'ie, Amnezja prowadzi go uczciwie do końca.**
Problem jest wyłącznie na wejściu — z tym, czego do trace'u nigdy nie wpuszczono.

---

## REKOMENDACJE (kolejność wg zysku do kosztu)

1. **Etapy dla Kanału 2 i 3** (F2) — dwie linijki `_rec(...)`. Domyka największą dziurę:
   25% promptu przestaje być bez rodowodu. **Robić pierwsze.**
2. **Etap dla kanału leksykalnego + przemianowanie `2_po_wykluczeniu`** (F3) — nazwa ma mówić
   prawdę o tym, że etap zarówno odejmuje, jak i dodaje.
3. **Wspólna funkcja składania `contents` dla Astry** (F1) — dokładnie ten sam ruch, który
   naprawił siostry 25.08. Piaskownica przestaje być osobnym kodem.
4. **Zapisywać `entity_type` do metadanych + usunąć zdublowane `type:` z linii promptu** (F4) —
   addytywne, bez migracji starych wektorów; przy okazji oszczędność tokenów w każdej turze.
5. **Pokazać przewód ZAPISU w UI Amnezji** (F5) — dane już są, brakuje tylko widoku.
6. **Rozszerzyć pokrycie na ścieżki proaktywne** (F6) — osobna, większa robota. Tam biją
   najdroższe bugi i tam mamy zero wglądu.

## CZEGO NIE ROBIMY
Nie przebazowujemy `golden_trafnosc`. Wszystkie niezmienniki dotyczące drogi wpisu przez trace
do promptu (I2/I3/I4) przeszły, a baseline z 25.08 mierzył `[WSPOMNIENIA]` — czyli dokładnie ten
fragment, który okazał się szczelny. Liczby stoją.

## METODY UŻYTE
- **A — prawa zachowania:** cztery niezmienniki (I1–I4) na 5 zapytaniach. Złapało F2.
- **B — konfrontacja narzędzi:** zakładka ZAPIS kontra surowy odczyt Chromy. Złapało F4, obaliło hipotezę → F5.
- **Czytanie różnicowe kodu:** produkcja kontra piaskownica, linia po linii. Złapało F1, F3.
- **Macierz pokrycia:** wszystkie wywołania Gemini w repo kontra lustra. Złapało F6.
- **Kanarek** (`pomiar_klamie.md`): każdy skrypt weryfikował liczbę wektorów przed pomiarem.
  Zadziałał — przy jednym przebiegu pokazał, że moduł startuje na pustej bazie.

Metody **C (replay różnicowy z przechwytywaniem promptów)**, **D (mutacja przyrządu)**
i **E (model jako świadek)** NIE zostały użyte — czekają na decyzję o przechwytywaniu treści
w produkcji. Po tym audycie ich pilność spadła: F1 i F2 znalazły się tańszymi środkami.
