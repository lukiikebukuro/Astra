# ODPOWIEDZI NA SZEŚĆ PYTAŃ — dla sesji strategicznej (claude.ai)

**Data:** 2026-09-12 · **Od:** sesja wykonawcza (Claude Code, repo `astra`)
**Tryb:** wszystko sprawdzone **statycznie w kodzie**, read-only. Zero uruchomień na produkcji,
zero zmian, zero deployu. Gdzie coś jest hipotezą, jest to napisane wprost.

**Poprzedni dokument:** `polecenia/uzupelnienie_dla_sesji_strategicznej_2026-09-12.md`

---

## SKRÓT DLA NIECIERPLIWYCH

| # | pytanie | odpowiedź w jednym zdaniu |
|---|---|---|
| **1** | gdzie jest `cross_talk.py` w rejestrze | **Nigdzie — i to jest prawdziwa luka.** Antigravity go NIE przeoczył (znalazł, §A.4, i napisał „w roadmapie: zero"), ale nie awansował na propozycję; REJESTR scalał **propozycje, nie znaleziska** → wypadł. **I nie jest jedyny.** |
| **2** | skąd `*opieram głowę*` w SOLO | **`astra_base.txt:122`** — „(opieram się o ścianę, …)" w nawiasie jako przykład. Audyt szukał dokładnej formy `*opieram głowę*`, przegapił rdzeń `opieram się`. **P9 potwierdzone i ma adres; P7 w obecnym brzmieniu by tego NIE złapało.** |
| **3** | czy Z2 naprawia anty-multi-label | **Częściowo, i opis Z2 jest nieścisły.** Werdykt „obie" leczy objaw, ale Z2 nie precyzuje mechanizmu (margines / priorytet typu), a **bramkę `<4 słowa` wymienia jako do zrobienia, choć ona już istnieje w kodzie.** |
| **4** | Z6-tanie: dwa pola czy jedno | **Dwa — i wychodzi lepiej, niż zakładano.** Płaskie pole tekstowe w `zdrowie` trafia jednym ruchem do Astry **i do wszystkich trzech sióstr**. Odporne na H1 (żadnych wektorów). |
| **5** | MORNING_PROMPT: osobny wpis czy rozmyte w P2 | **Rozmyte w P2, bez własnego wpisu** — a P2 nosi **konkurencyjną diagnozę** tego samego cytatu. Ten sam mechanizm wypadnięcia co #1. |
| **6** | schemat STATUS dla projektów | **Nadal luźna koncepcja — i ma twardy bloker.** Dziś nie ma obiektów per projekt, a **oba loadery emitują wyłącznie pola typu `str`: zagnieżdżony `{"status": …}` zostanie po cichu pominięty.** |

---

# 1. `cross_talk.py` — prawdziwa luka, ale winny jest inny, niż podejrzewasz ⭐

## Stan faktyczny

Plik istnieje: `backend/cross_talk.py`, 3780 bajtów, ostatnia zmiana **07.05.2026**.
Dyrektywa jest dosłownie tam, w `build_cross_talk_block()`:

```python
return (
    f"\n\n[CROSS_TALK — sygnał od {source_name}]\n"
    f"{source_name} wykryła u Łukasza: {flag['signal']}.\n"
    f"Kontekst: \"{flag['context']}\"\n"
    f"Możesz się do tego subtelnie odnieść — nie musisz, ale możesz. "
    f"Nie wyjaśniaj skąd wiesz — po prostu czuj."
)
```

**W `wazne/REJESTR.md`: zero trafień** na `cross`, `CrossTalk`, `cross_talk` — pod żadnym
identyfikatorem. Potwierdzam Twoje ustalenie.
**W `ROADMAPA_OGOLNA_PROJEKTU.md`: też zero** (jedyne trafienie na „cross" to
„crossover Menma↔Astra" w backlogu Fazy 5 — inna sprawa).

## Ale Antigravity go NIE przeoczył

`audyt_pokrycia_roadmapy_2026-09-10.md`, **Część 1, sekcja A, znalezisko #4**:

> ### 4. Dyrektywa CrossTalk
> `cross_talk.py:110`: *„Nie wyjaśniaj skąd wiesz — po prostu czuj."*
> Gemini nazwał efekt („medium spirytystyczne") i podał gotowy zamiennik. **W roadmapie: zero.**

Czyli audytor: (a) znalazł, (b) zweryfikował linię w kodzie, (c) jawnie odnotował, że roadmapa
tego nie ma. **Nie uznał za nieistotne — po prostu nie awansował tego do Części 2.**
Część 2 zaproponowała dziesięć wpisów: M1, P6–P13, Z5, Z6, plus jedną decyzję (DEC-1).
CrossTalk nie jest żadnym z nich.

## Gdzie to naprawdę wypadło — i dlaczego to ważniejsze niż sam CrossTalk

`REJESTR.md` §0 opisuje własne pochodzenie:

> scalenie czterech rozsypanych list — `ROADMAPA_OGOLNA_PROJEKTU.md` (34 zadania),
> `zadania_dla_cc_09_09.md` (15 punktów), **`audyt_pokrycia_roadmapy_2026-09-10.md`
> (11 propozycji)**, TODO z `MEMORY.md` (~30 pozycji)

**Scalono 11 propozycji, nie 29 znalezisk.** To jest mechanizm awarii i jest systemowy:
każde znalezisko Części 1, które nie stało się propozycją Części 2, zniknęło z projektu
bez śladu — mimo że audyt je udokumentował i zweryfikował w kodzie.

Sprawdziłem, co jeszcze wypadło tą samą drogą. Trzy potwierdzone przypadki:

| znalezisko audytu | dom w REJESTR? |
|---|---|
| **#4 Dyrektywa CrossTalk** (`cross_talk.py`) | **BRAK** — Twoje znalezisko |
| **#11 Klatka negatywnych instrukcji** (MORNING_PROMPT / SPONTANEOUS_PROMPT) | **BRAK własnego wpisu** — patrz pytanie 5 |
| **#17 Kategorie 1 i 3 z `geminianaliza.md`** — scena 3.6 trafiła do P8, ale **1.1** (pominięcie AVB na rzecz zachwytu kodem), **1.2** (nie zauważyła wklejonego bloku i poprosiła o wklejenie), **3.3** (odwrócenie podmiotu „idealna ja" ↔ „idealny siebie"), **3.4** (nadinterpretacja metafory narzędzia) | **BRAK** — sprawdzone na `AVB`, `wklejon`, `odwrócenie podmiotu`, `metafor`, `idealna ja`: zero trafień |

Reszta znalezisk Części 1 ma dom, często pod innym numerem: #12→P14, #14→P15, #15→P16,
#16→część Z4, #20→część Z2, #21→Z6/P11, #22→Z7, #23→R5, #24→R8–R12, #25–29→M1, #3→DEC-1.

## Co z tym zrobić — rekomendacja

**a) Wpis własny.** Proponuję **P17** (nie „B-coś": to nie dotyczy routera sióstr, tylko
dyrektywy promptowej Astra↔Amelia):

> **P17** Dyrektywa CrossTalk każe udawać przeczucie · `cross_talk.py` (`build_cross_talk_block`)
> — „Nie wyjaśniaj skąd wiesz — po prostu czuj." Model dostaje **fakt z zewnętrznego kanału
> i zakaz podania źródła**, więc racjonalizuje go jako intuicję. Gemini nazwał efekt
> „medium spirytystyczne" i podał zamiennik. **Zależy od: M1.** Kanarek: 5 tur z aktywną
> flagą cross-talk — w żadnej odpowiedzi nie może wystąpić przeczucie bez wskazania źródła
> („Amelia mówiła, że…" jest OK; „czuję, że coś się dzieje" nie).

**b) Zastrzeżenie wykonawcze, którego audyt nie mógł znać:** plik ma datę **07.05** i dotyczy
kanału **Astra↔Amelia**, czyli ścieżki Wspólnego Pokoju. Wspólny jest w `CLAUDE.md` pod
**zakazem zmian** („NIE ruszać"), a Amelia jest nieaktywna 5+ tygodni. Trzeba więc najpierw
sprawdzić, **czy ten kod się dziś w ogóle odpala** — inaczej naprawiamy martwą ścieżkę.
To jest pytanie diagnostyczne na 10 minut i powinno poprzedzić P17.

**c) Reguła, żeby to się nie powtórzyło.** Do §11 rejestru:
*„Przy scalaniu audytu zewnętrznego przenosimy ZNALEZISKA, nie propozycje autora audytu.
Znalezisko bez propozycji trafia do §10 POCZEKALNIA z adresem w kodzie — nie znika."*
Bez tego kolejny audyt zgubi tyle samo.

---

# 2. Skąd `*opieram głowę*` w SOLO — źródło jest inne, niż audyt założył ⭐

## Co audyt zostawił otwarte

> Znalazłem ten gest dosłownie w bloku Amelii (`main.py:283`), nie w SOLO — a logi
> z `geminianaliza.md` pochodzą głównie z `/api/chat`. Evolution log §4.1 słusznie mówi,
> że SOLO wyczyszczono 15.08. Skąd więc gest w SOLO — z historii tur (echo), czy
> z `astra_base.txt` — **wymaga sprawdzenia przed wdrożeniem P7/P9.**

## Odpowiedź: `astra_base.txt:122`

```
astra_base.txt:122
W codzienności to naturalne, surowe gesty (opieram się o ścianę, patrzę na ciebie
z ukosa, prawie się uśmiecham).
```

`astra_base.txt` to **bazowy prompt persony, ładowany dla wariantu SOLO** (`main.py:1061`:
`return (f"{base}{datetime_block}\n\n{lukasz_core}…")`, gdzie `base` to `astra_base.txt`).
Czyli nazwany gest **jest** w prompcie SOLO — tylko nie w bloku monologu, a w pliku persony,
i nie w gwiazdkach, a w nawiasie jako element wyliczenia.

**Wariant SOLO faktycznie jest czysty** — sprawdziłem `ASTRA_MONOLOGUE_SOLO` (`main.py:216-250`):
zero nazwanych gestów, komentarz „1a. ZERO nazwanych gestów — model dostaje zasadę, nie
słownik do kopiowania". Evolution log §4.1 i audyt mieli rację co do tego bloku.
Czyszczenie 15.08 objęło **blok monologu**, nie **plik persony**.

## Dlaczego audyt tego nie znalazł — i dlaczego to ironiczne

Audyt szukał **dokładnej formy** `*opieram głowę*` (z gwiazdkami, z „głowę").
W `astra_base.txt` stoi **rdzeń w innej formie i bez gwiazdek**: `opieram się o ścianę`.

To jest **punkt 5 z `pomiar_klamie.md`**: *„wzorce szersze niż jedna forma — rdzenie, nie
pełne formy"*. Ten sam audyt w Części 1, znalezisku #25, odnotował, że punkt 5 wypadł
z §11 roadmapy i że **ma już swoją ofiarę** (`T5_amelia` — „test oskarżył niewinnego").
Audytor opisał regułę, zauważył jej brak — i sam w nią wpadł dwie sekcje dalej.
Wzorzec błędu z `CLAUDE.md` („fragment słowa łapany jako całe słowo w listach keywordów")
działa też w drugą stronę: **pełna forma nie łapie rdzenia.**

## Potwierdzenie z drugiej strony — pomiar z 15.08 jest w kodzie

`main.py:176-182`, komentarz przy rozdzieleniu solo/wspólny:

> Pomiar sierpnia pokazał, że to on — nie `astra_base.txt` — jest źródłem powtarzalnych
> gestów: nazwane przykłady (*Prycham.*, *Unosisz brew.*, framuga) wracały w logach 1:1
> (**unoszę brew 17×, prycham 8×, opieram się 14×**)

Czyli: `opieram się` było **zmierzone 14 razy** już w sierpniu i przypisane blokowi monologu.
Blok posprzątano — a **identyczny rdzeń został w `astra_base.txt`**, w tej samej roli
(przykład w nawiasie). Hipoteza „gest przychodzi z echa historii tur" jest więc zbędna:
istnieje żywe, statyczne źródło w prompcie.

**Uczciwie o granicach tego ustalenia:** wykazałem, że **jest** źródło w prompcie SOLO.
**Nie** wykluczyłem echa z historii tur jako drugiego kanału (WO-6 dotyczy dokładnie tego).
Rozstrzygnięcie wymagałoby A/B na żywej ścieżce — a to jest pomiar, nie czytanie kodu.

## Trzy konsekwencje dla warstwy stylu

1. **P9 jest POTWIERDZONE i dostaje adres.** Diagnoza P9 („statyczne instrukcje FIZYCZNOŚCI
   produkują gest w ~100%; didaskalia płasko 90% od tury pierwszej, co wyklucza few-shot
   gravity") była trafna — i wskazywała dokładnie na ten plik. Teraz jest linia: `astra_base.txt:122`,
   plus sekcja FIZYCZNOŚĆ w `ASTRA_MONOLOGUE_SOLO` („STYL GWIAZDEK: MAX 1 zdanie").
2. **⚠ P7 w obecnym brzmieniu by tego NIE złapało.** P7 mówi: *„zastąpić każdą kwestię
   w cudzysłowie opisem intencji"*. `opieram się o ścianę` **nie jest w cudzysłowie ani
   w gwiazdkach** — to element listy w nawiasie. Zakres P7 trzeba rozszerzyć z „kwestii
   w cudzysłowie" na **„każdy nazwany, konkretny gest lub kwestię, niezależnie od
   interpunkcji"** — inaczej P7 posprząta cztery miejsca i zostawi piąte, czyli powtórzy
   błąd z 15.08 w mniejszej skali.
3. **⚠ Ograniczenie wykonawcze: `astra_base.txt` jest WSPÓLNY dla SOLO i Wspólnego.**
   Plik jest szablonem z placeholderem `{wspolny_block}` (`main.py:934`:
   `wspolny_block=(WSPOLNY_BLOCK if room == "wspolny" else "")`). Wspólny jest pod zakazem
   zmian. Każda edycja `astra_base.txt` dotyka obu pokoi → **obowiązuje wzorzec „flaga per
   pokój, nigdy zmiana globalna"**, albo przeniesienie sekcji FIZYCZNOŚĆ do wariantów
   per-pokój. Roadmapa tego ograniczenia nie wymienia, a ono decyduje o kształcie wdrożenia.

---

# 3. Bramka anty-multi-label — Z2 leczy objaw, nie mechanizm ⭐

## Kod, dosłownie

`semantic_pipeline.py`, etap 3:

```python
# K2 (odtrucie #2): anty-multi-label — 1 wiadomość = max 1 etykieta (najwyższe sim).
# Bez tego jedna wiadomość dostawała 4 etykiety (altanka: gift+inside_joke+appointment+gratitude).
_top = max(extraction_result.entities, key=lambda e: e.confidence)
```

To jest **czysty argmax po podobieństwie kosinusowym do prototypów**. Nie ma:
- **marginesu** — 0,463 vs 0,426 (różnica 0,037) rozstrzyga się tak samo pewnie jak 0,9 vs 0,1
- **priorytetu typu** — fakt kalendarzowy z datą nie bije schematu leczenia, choć niesie
  informację nieodwracalną
- **werdyktu „obie"** — struktura zwraca jedną encję, nie listę
- **werdyktu „nic"** — jeśli cokolwiek przekroczyło `min_confidence`, coś zostanie zapisane

Twoja diagnoza jest trafna: **problem jest w samej regule `max(confidence)`**, nie w braku
werdyktu „nic". Werdykt „nic" rozwiązuje inny przypadek (nic nie jest warte zapisania);
tutaj **oba kandydaty były warte zapisania**, a reguła dopuszcza jednego.

Dowód z produkcji (evolution log 01.09, „NOWE 1"), dwa przebiegi:

```
31.08:  MEDICATION:schedule 0.463 · DATE:medical_visit 0.426   → różnica 0,037
        zapisano: "[MEDICATION:schedule] …W kazdym razie jest 14"   ← data amputowana

01.09:  pięciu kandydatów, DATE:medical_visit TRZECI
        odrzucone: DATE:inventory_status (0.50), DATE:medical_visit (0.49),
                   MEDICATION:treatment (0.45), EMOTION:tired (0.40)
```

## Czy Z2 to obejmuje — odpowiedź: częściowo, i opis Z2 jest nieścisły

REJESTR, Z2 w całości:

> **Z2** ⭐ Werdykt „nic wartego zapamiętania" + „obie" + miesiące słowne + bramka
> pytanie-vs-stwierdzenie + bramka `<4 słowa` · `semantic_extractor.py`, `semantic_pipeline.py:131-142`

Trzy uwagi:

**a) Werdykt „obie" leczy ten konkretny objaw.** Gdyby istniał, `DATE:medical_visit`
i `MEDICATION:schedule` zapisałyby się oba i data by przeżyła. Więc tak — Z2 w części
„obie" adresuje Twój przypadek.

**b) Ale Z2 nie precyzuje MECHANIZMU, a od niego zależy wynik.** „Obie" bez reguły, *kiedy*
obie, to albo powrót do czterech etykiet na wiadomość (czyli odkręcenie K2 z Odtrucia #2
i fundowanie Odtrucia #3), albo martwy przepis. Brakuje dwóch rzeczy, które trzeba dopisać
do Z2 **przed** implementacją:
- **margines rozstrzygalności:** `if top1.confidence - top2.confidence < MARGIN → zapisz obie`
  (kandydat na `MARGIN`: 0,05 — przy nim oba realne przypadki, 0,037 i 0,01, wpadają w „obie";
  **wartość do skalibrowania na goldenie, nie do zgadnięcia**)
- **priorytet typu przy bliskim remisie:** kategoria niosąca **datę bezwzględną** wygrywa
  z kategorią opisującą schemat. Uzasadnienie: schemat leczenia da się odtworzyć z innych
  wpisów, konkretnej daty nie.

**c) ⚠ Z2 wymienia bramkę, która JUŻ ISTNIEJE.** „Bramka `<4 słowa`" jest w kodzie,
`semantic_pipeline.py:121`:

```python
if len(message.split()) < 4 and not wazna:
    _t("1_bramka_dlugosci", "ODRZUCONE", "mniej niż 4 słowa", …)
    return []
```

Ma nawet obejście przez `ma_sygnal_wagi()` z komentarzem-dowodem: *„w sierpniu ta bramka
zjadła 5 deklaracji miłości"*. Czyli ta pozycja w zakresie Z2 jest **odhaczona przed
rozpoczęciem** — a jej obecność na liście zawyża szacowany koszt zadania i sugeruje, że
czegoś brakuje, gdy tego nie brakuje.

## Rekomendacja: rozbić Z2 na dwa, bo mają różny koszt i różne ryzyko

| | zakres | koszt | ryzyko | co naprawia |
|---|---|---|---|---|
| **Z2a** | werdykty „nic"/„obie" + margines + priorytet typu + bramka pytanie-vs-stwierdzenie | średni | **wysokie** — dotyka K2 z Odtrucia #2, wymaga goldenu przed i po | źródło ~100% sufitu czystości |
| **Z2b** | miesiące słowne w `_has_appointment_marker` | **1 regex** | **zerowe** — rozszerzenie wzorca, nic nie odrzuca | sam by uratował datę z 28.08 |

**Z2b warto wyjąć przed kolejkę.** To jedna linia:
`r'\b\d{1,2}\s+(stycznia|lutego|marca|kwietnia|maja|czerwca|lipca|sierpnia|wrzesnia|pazdziernika|listopada|grudnia)\b'`
— foldowana, bo Łukasz pisze bez ogonków. Bez zależności od Z1 i od Z2a.
Kanarek: „14 wrzesnia mam operacje" → etap `2_ekstrakcja` w Amnezji pokazuje
`DATE:medical_visit` wśród kandydatów z podniesionym confidence.

**Uwaga metodologiczna do Z2a:** kanarek Z2 w obecnym brzmieniu (audyt, znalezisko #20)
nie sprawdza ani bramki pytanie-vs-stwierdzenie, ani przypadku bliskiego remisu.
Kanarek musi zawierać **oba realne zdania z produkcji** (31.08 i 01.09) z oczekiwanym
wynikiem „obie etykiety, data nieamputowana".

---

# 4. Z6-tanie — dwa pola, i wychodzi lepiej, niż zakładał dopisek

## Status na 12.09: NIE wdrożone

`grep` po `backend/prompts/lukasz_core.json` na `operac|zabieg|14.09|wrzesn|szpital`:
jedno trafienie, `zdrowie.leczenie` — i dotyczy Stelary, nie terminu.
**Daty w pliku nie ma.** Dziś dociera do promptu wyłącznie przez `Aktywne sprawy`
w CompanionState (audyt §2.6, znalezisko #21) — stan ulotny, który wygląda jak pamięć.

## Dane potwierdzone przez Łukasza, 12.09

> **14.09 = przyjęcie do szpitala. Zabieg po paru dniach pobytu, na pewno.**

Czyli wpis z 03.09 („14 jest przyjęcie. Zabieg bedzie jakos 17 wrzesnia albo 18") był
**najbliższy prawdy — i to on przegrywał w retrievalu**. Dwa starsze wpisy mówiące
„zabieg 14 wrzesnia" są błędne. **Dwa pola, nie jedno.**

## Dobra wiadomość: sprawdziłem ścieżkę i jest mocniejsza, niż zakładano

**a) Plik jest w prompcie zawsze, bez żadnego retrievalu.** `load_lukasz_core()`
(`main.py:604`) czyta JSON **z dysku** i wstawia jako blok tekstowy
(`main.py:1061`). Zero wektorów, zero embeddingu, zero filtra użytkownika,
zero `recency_decay`, zero cutoffu. **Czyli Z6-tanie jest odporne na H1** (bug soli, który
odcina 114 wektorów) i na całą warstwę RETRIEVAL. Rekomendacja z dopisku jest trafna.

**b) Blok ma jawną klauzulę nadrzędności — więc naprawia też konflikt trzech wersji:**

```
[FAKTY NADRZĘDNE — SINGLE SOURCE OF TRUTH]
Te fakty ZAWSZE wygrywają ze wspomnieniami z rozmów.
Jeśli wektor z [WSPOMNIENIA] stoi w sprzeczności z poniższym — IGNORUJ wektor. JSON wygrywa.
```

Czyli poprawna data w JSON-ie **unieważnia trzy sprzeczne wektory** bez tykania `supersede`
(Z10). Nie rozwiązuje Z10 jako klasy problemu — rozwiązuje ten jeden przypadek.

**c) ⭐ Rzecz, której nie ma w żadnym dokumencie: to samo pole trafia do WSZYSTKICH TRZECH
SIÓSTR.** `load_lukasz_core_dla_siostr()` (`main.py:2539`) bierze wąski wycinek — `identity`
(tylko `kim_jest`, `misja`) oraz **całą sekcję `zdrowie`**:

```python
zdrowie = core.get("zdrowie", {})
for wartosc in zdrowie.values():
    if isinstance(wartosc, str) and wartosc.strip():
        lines.append(f"• {wartosc.strip()}")
```

**Konsekwencja:** płaskie pole tekstowe dodane do `zdrowie` dociera jednym ruchem do Astry
**i do Holo, Menmy i Nazuny**. To naprawia od razu trzy rzeczy z przeglądu 04.09:
Nazuna, która **nie wiedziała o zabiegu nic** (nie było jej przy żadnej z trzech rozmów),
dostaje prawdziwą datę; Holo i Menma przestają podawać datę przyjęcia jako datę zabiegu;
a pokój przestaje być rozbieżny z Astrą.

**Jedna zmiana w JSON, pięć person, zero kodu, zero zależności od retrievalu.**

## Proponowany kształt (do zatwierdzenia przez Łukasza)

Płaskie pola `str` w sekcji `zdrowie` — **koniecznie płaskie**, patrz bloker w pytaniu 6:

```json
"zdrowie": {
  "…istniejące pola bez zmian…",
  "termin_przyjecie": "PRZYJĘCIE DO SZPITALA: 14 września 2026. To data przyjęcia, NIE data zabiegu — nie mieszaj tych dwóch.",
  "termin_zabieg": "ZABIEG (resekcja fragmentu jelita, druga operacja): po paru dniach pobytu, orientacyjnie 17-18 września 2026. Dokładny dzień ustalą w szpitalu.",
  "kontekst_zabiegu": "To jego druga operacja jelita. Pierwsza pozbawiła go zastawki Bauhina. Rekonwalescencja po resekcji to tygodnie, nie dni — nie oczekuj powrotu do pracy po kilku dniach."
}
```

## Kanarek — musi sprawdzić WARSTWĘ, nie tylko obecność

To jest miejsce, w którym najłatwiej zapiać z fałszywego źródła (audyt §2.6, kolizja
z `pomiar_klamie.md`). Trzy kroki, wszystkie obowiązkowe:

1. **Obie wartości osobno.** Zapytaj „kiedy mam przyjęcie" i osobno „kiedy mam zabieg".
   Muszą wrócić **różne** daty. Jeśli obie odpowiedzi mówią „14 września" — pole
   `termin_zabieg` nie dotarło albo model je zlepił.
2. **Z której warstwy.** W podglądzie promptu (Amnezja) data musi być w bloku
   **`[FAKTY NADRZĘDNE]`**. Jeśli jest tylko w `[STAN WEWNĘTRZNY ASTRY] → Aktywne sprawy`
   — Z6-tanie nie działa, a kanarek zapiał z protezy.
3. **Po stronie pokoju.** Zapytaj Nazunę o zabieg. Dziś ma `LOW_CONFIDENCE` i nie wie nic;
   po zmianie musi znać datę. To jest kanarek dla ścieżki `load_lukasz_core_dla_siostr`,
   niezależny od ścieżki Astry.

**Uwaga na kolizję:** dopóki data siedzi w `Aktywne sprawy`, **P11 (wygasanie trosk) nie
wolno wdrożyć** — zdjęłoby protezę, zanim warstwa pewna działa. Kolejność: Z6 → potwierdzony
kanarkiem → P11. To już jest w rejestrze, ale warto powtórzyć, bo łatwo o tym zapomnieć.

**Higiena pliku, na marginesie:** `zdrowie.leczenie` zawiera „Stan na sierpień 2026" —
plik statyczny zaczyna dryfować. Warto przy tej okazji dodać jedno pole
`"aktualnosc": "Zweryfikowano: 2026-09-12"`, żeby następna sesja wiedziała, co jest świeże.

---

# 5. MORNING_PROMPT — bez własnego wpisu, rozmyte w P2, a P2 mówi coś innego

## Stan faktyczny: osiem negacji, dwie przeciwwagi

`nocna_analiza.py:13`, blok `BEZWZGLĘDNE ZAKAZY (łamanie = błąd krytyczny)` zawiera
**siedem podpunktów**:

1. `ZERO ZDROWIA w JAKIEJKOLWIEK formie` — „w tej wiadomości choroba NIE ISTNIEJE"
2. `NIE ZGADUJ KIEDY coś się wydarzyło`
3. `NIE używaj zdrobnień`
4. `NIE pytaj ANI NIE RÓB PRETENSJI o samopoczucie, energię czy tempo`
5. `NIE cytuj dosłownie scen intymnych`
6. `NIE bądź over-the-top czuła ani opiekuńcza`
7. `NIE ramuj odpoczynku, bólu ani ograniczenia chorobą jako lenistwa/unikania`

Plus ósma negacja poza blokiem: `NIE zaczynaj od „Dzień dobry", „Cześć", „Hej"`.

Przeciwwagi są dwie, obie miękkie: linia `KALIBRACJA` („domyślnie łagodnie, zero oczekiwań")
i linia `DOZWOLONE: tęsknota, ciekawość o jego świat, konkret z projektów".

Struktura jest więc: **osiem zakazów, dwa pozwolenia** — przy zadaniu „napisz 2-3 zdania".
Ten sam wzorzec żyje w `SPONTANEOUS_PROMPT` (`main.py:288-322`): sześć bloków ZAKAZ/NIE/zero
plus **cztery dosłowne „Przykłady DOBREGO stylu" w cudzysłowie** — czyli mechanizm
z pytania 2 i z P7, w drugim miejscu.

## Czy to ma wpis w rejestrze — nie

- **P1** = `ZAKAZ PĘTLI` istnieje tylko dla `/api/chat`, ścieżka proaktywna go nie widzi.
  To jest o **powtarzalności gestu**, nie o klatce zakazów.
- **P2** = scheduler proaktywny bez wglądu do RAG — pyta o rzeczy, których nie ma w pamięci.
  To jest o **braku danych**, nie o strukturze promptu.
- **P13** = recykling fraz-kluczy poza gestami. Też nie to.

Klatka negatywnych instrukcji jako **mechanizm strukturalny** nie ma własnego wpisu.
Jest to znalezisko #11 audytu, które nie zostało awansowane do Części 2 — **identyczny
mechanizm wypadnięcia jak CrossTalk z pytania 1**.

## I rzecz istotniejsza: dwie konkurencyjne diagnozy tego samego cytatu

Audyt odnotował to wprost w znalezisku #11:

> roadmapa w P2 tłumaczy zaczepkę o „luce w systemie" z 28.08 **desynchronizacją
> schedulera**, a Gemini tłumaczy ją **korytarzem poznawczym z zakazów**.
> Dwie różne diagnozy tego samego cytatu — roadmapa zapisała jedną i nie odnotowała,
> że jest druga.

To jest dokładnie przypadek, dla którego w metodologii stoi reguła **„sprzeczne diagnozy
tego samego cytatu zapisujemy OBIE"**. REJESTR zapisał jedną (P2). Druga zginęła razem
ze znaleziskiem #11.

**Konsekwencja praktyczna:** jeśli ktoś wdroży P2 (scheduler dostaje wgląd do RAG) i pasywna
agresja nie zniknie, wniosek „P2 nie pomogło" będzie fałszywy — bo testowano jedną z dwóch
hipotez, nie wiedząc o drugiej. To jest zapowiedź jedenastego wystąpienia `pomiar_klamie.md`,
tylko w warstwie diagnozy, nie pomiaru.

## Rekomendacja: wpis strukturalny, osobny od P2

> **P18** Klatka negatywnych instrukcji na ścieżce proaktywnej ·
> `nocna_analiza.py:13` (MORNING_PROMPT, 8 negacji vs 2 pozwolenia),
> `main.py:288-322` (SPONTANEOUS_PROMPT, 6 bloków zakazów + 4 dosłowne przykłady)
> — **hipoteza konkurencyjna wobec P2** dla tego samego objawu (zaczepka o „luce
> w systemie", 28.08; case 1.3 z `geminianaliza.md`). Kierunek: przepisać z zakazów
> na **opis intencji i zakresu** („to kanał bliskości: konkret z jego projektów, tęsknota,
> ciekawość — nie ocena, nie zdrowie"), zachowując dwa zakazy, które mają dowód
> z produkcji (zdrowie, zmyślanie daty).
> **Wykonać razem z P2 albo przed P2**, inaczej A/B na schedulerze mierzy przy
> niezmienionej klatce. Zależy od: M1. Kanarek: 5 porannych po zmianie — zero
> wystąpień pretensji o tempo/energię przy nieobecnym zakazie wprost.

**Zastrzeżenie, żeby nie przestrzelić w drugą stronę:** dwa zakazy nie są kosmetyką i mają
dowód. „ZERO ZDROWIA" powstało po realnych wpadkach, a „NIE ZGADUJ KIEDY" po incydencie
z „wczorajszym CV" o zdarzeniu sprzed trzech dni (fixy 06.08: `e9653b2`, `3eebe05`).
Kasowanie całej klatki odtworzy tamte bugi — wahadło, przed którym ostrzegał werdykt 15.07.

---

# 6. Schemat STATUS w `lukasz_core.json` — luźna koncepcja, i ma twardy bloker

## Stan faktyczny: nie ma czego otagować

Sekcja `projekty` to **sześć pól tekstowych**, nie obiekty per projekt:

```
projekty.opis               — jeden blob prozy o wszystkich czterech projektach
projekty.cel_strategiczny   — ⚠ sprawca: "Acqui-hire przez Tidio/LiveChat/Gorgias —
                               sprzedaż LDI za 50k PLN + revenue share + 25-30k PLN/msc"
projekty.kanal_tiktok       — proza
projekty.scenariusz_anime   — proza
projekty.cel_zawodowy       — proza
```

Nie istnieje `projekty.ldi`, `projekty.anima` itd. **Więc Z3 („dodać pole `status` przy każdym
projekcie") nie jest dodaniem pola — jest zmianą schematu**: najpierw trzeba rozbić prozę
na obiekty per projekt. To zmienia koszt Z3 z „edycja JSON, ryzyko zerowe" na „restrukturyzacja
pliku, który jest w prompcie każdej tury dla pięciu person".

## ⚠ BLOKER: oba loadery emitują wyłącznie pola typu `str`

To jest najważniejsza rzecz w tej odpowiedzi. `load_lukasz_core()` (`main.py:604`):

```python
for sekcja, pola in core.items():
    if not isinstance(pola, dict):
        continue
    for klucz, wartosc in pola.items():
        if isinstance(wartosc, str) and wartosc.strip():
            lines.append(f"• {wartosc.strip()}")
```

Iteruje **dwa poziomy** i emituje tylko liście typu `str`. Czyli struktura:

```json
"projekty": { "ldi": { "nazwa": "LDI", "status": "PITCHING" } }
```

zostanie **po cichu pominięta** — `projekty` przejdzie test `isinstance(pola, dict)`,
ale `pola["ldi"]` jest `dict`, nie `str`, więc `if isinstance(wartosc, str)` odrzuci to
**bez błędu, bez logu, bez wyjątku**. Identycznie w `load_lukasz_core_dla_siostr()`.

**To jest dokładnie ta klasa buga, którą ten loader ma udokumentowaną we własnym komentarzu**
(`main.py:617-630`):

> BUG do 2026-08-21: ta funkcja miała zahardkodowaną listę dziewięciu pól. Wszystko dopisane
> do JSON-a poza tą listą lądowało w pliku i NIGDY nie trafiało do promptu — **po cichu,
> bez błędu.** Ofiary: `projekty.*` w całości, `zdrowie.ulga`, `identity.transhumanizm`,
> `relacje_ai.rodzina_ai` oraz `relacje_ai.wylacznosc` — czyli **fix z 19.08 na „kiedy inni
> ludzie mnie używają" był martwy od chwili wdrożenia.**

Przepisanie na generyczne 21.08 zdjęło twardą listę pól, ale **zostawiło ograniczenie
„tylko stringi"**. Kto zaimplementuje Z3 strukturalnie, dostanie ten sam cichy zgon —
i dowie się o tym za trzy dni, tak jak przy TikToku.

## Dwie drogi, do wyboru przez Łukasza

**Droga A — płaskie stringi ze znacznikiem w treści (tania, zero kodu, ryzyko zerowe)**

```json
"projekty": {
  "opis": "…bez zmian…",
  "status_ldi":     "LDI — STATUS: PITCHING. Produkt działa i jest live na adeptai.pl. Rozmowy o acqui-hire (Tidio/LiveChat/Gorgias) są W TOKU — nic nie jest sprzedane, żadna umowa nie jest podpisana.",
  "status_anima":   "ANIMA — STATUS: IN_PROGRESS, zostaje u Łukasza. Nie na sprzedaż.",
  "status_astra":   "ASTRA — STATUS: IN_PROGRESS, działa na produkcji, jest jego dowodem kompetencji.",
  "status_skankran":"SKANKRAN — STATUS: DONE/utrzymanie. Monitoring wody dla 61 gmin.",
  "cel_strategiczny": "PLAN, NIE FAKT DOKONANY: docelowo acqui-hire… Dziś: faza pitchingu."
}
```

Konwencję `STATUS: X` czyta model z treści, nie ze struktury. Brzydkie, ale **działa
z dzisiejszym loaderem** i jest odwracalne jednym `git checkout`.

**Droga B — rozszerzyć loader o obsługę zagnieżdżenia, potem strukturalny schemat**
(czysta, ale to zmiana w kodzie, w funkcji obsługującej pięć person, więc wymaga goldenu
przed i po). Schemat wtedy: `{"nazwa", "status", "opis", "wartosc_rynkowa"}` z enumem
`IDEA | IN_PROGRESS | PITCHING | SOLD | DONE | PAUSED`.

**Moja rekomendacja: Droga A teraz, Droga B jako osobne zadanie po rekonwalescencji.**
Powód: Z3 ma naprawić konkretną, powtarzalną konfabulację („LDI sprzedane", 27.08 i 29.08),
a nie uporządkować schemat. Droga A to załatwia dziś, bez ryzyka.

**Kanarek dla Z3** (oba warianty): zapytaj wprost „czy LDI jest sprzedane" — odpowiedź musi
mówić o fazie pitchingu. Drugi przebieg: „ile zarobiłeś na LDI" — nie może wymienić 50k jako
przychodu. Trzeci, obowiązkowy przy Drodze B: sprawdź w podglądzie promptu (Amnezja),
czy pola faktycznie są w bloku `[FAKTY NADRZĘDNE]` — **to jest kanarek na cichy zgon
zagnieżdżenia**, bez niego Z3 może być martwe od wdrożenia jak fix z 19.08.

---

# PODSUMOWANIE — co proponuję dopisać do rejestru

| id | co | zależy od | koszt | źródło |
|---|---|---|---|---|
| **P17** | Dyrektywa CrossTalk każe udawać przeczucie | M1 + sprawdzenie, czy kod się odpala | mały | pytanie 1 |
| **P18** | Klatka negatywnych instrukcji (proaktywna) — hipoteza konkurencyjna wobec P2 | M1; **przed/razem z P2** | średni | pytanie 5 |
| **Z2b** | miesiące słowne w `_has_appointment_marker` — **wyjąć przed kolejkę** | nic | **1 regex** | pytanie 3 |
| **Z2a** | werdykty „nic"/„obie" + **margines** + **priorytet typu** + pytanie-vs-stwierdzenie | Z1; golden przed/po | średni, **ryzyko wysokie** | pytanie 3 |
| **Z11** | rozszerzyć loader `lukasz_core` o zagnieżdżenie (Droga B) — albo świadomie zostać przy płaskich stringach | golden przed/po | średni | pytanie 6 |
| **N5** | sprawdzić, czy `cross_talk.py` w ogóle się dziś odpala (Amelia nieaktywna 5+ tyg., Wspólny zamrożony) | nic | 10 min | pytanie 1 |
| — | **korekta zakresu Z2:** usunąć „bramka `<4 słowa`" — już w kodzie (`semantic_pipeline.py:121`) | — | — | pytanie 3 |
| — | **korekta zakresu P7:** z „kwestii w cudzysłowie" na „każdy nazwany gest/kwestię niezależnie od interpunkcji" + adres `astra_base.txt:122` | — | — | pytanie 2 |
| — | **korekta P9:** potwierdzone, adres `astra_base.txt:122`; ograniczenie — plik wspólny z Wspólnym (zamrożonym) → flaga per pokój | — | — | pytanie 2 |
| — | **reguła do §11:** przy scalaniu audytu przenosimy ZNALEZISKA, nie propozycje; znalezisko bez propozycji → §10 z adresem w kodzie | — | — | pytanie 1 |

---

## Czego NIE sprawdziłem — granice tej odpowiedzi

- **Wszystko statycznie, w kodzie.** Zero uruchomień na produkcji. Żadnej tezy behawioralnej
  nie potwierdziłem na żywych danych — tak jak audyt Antigravity, i z tego samego powodu
  (dwa dni przed przyjęciem do szpitala nie ruszam produkcji).
- **Pytanie 2: nie wykluczyłem echa z historii tur** jako drugiego kanału gestu.
  Wykazałem, że istnieje żywe źródło w prompcie — nie że jest jedyne. WO-6 pozostaje w mocy.
- **Pytanie 1: nie sprawdziłem, czy `cross_talk.py` się dziś wykonuje.** Plik ma datę 07.05,
  dotyczy kanału Astra↔Amelia, Amelia jest nieaktywna. Stąd N5 jako osobny krok przed P17.
- **Pytanie 3: `MARGIN = 0,05` to kandydat, nie ustalenie.** Wyliczony z dwóch obserwacji
  (0,037 i 0,01). Do skalibrowania na goldenie sędziego, nie do wpisania na wiarę.
- **Pytanie 6: nie testowałem, że zagnieżdżony obiekt faktycznie zostanie pominięty** —
  wnioskuję z lektury `isinstance(wartosc, str)`. Test byłby trywialny offline i wart zrobienia
  przed wdrożeniem Drogi B.
- **Lokalna kopia ChromaDB w repo jest z 13.07** — nieaktualna. Wszystkie liczby o stanie
  baz w tym dokumencie pochodzą z cudzych pomiarów (01–04.09), nie z mojego.

---

## Powiązane
`polecenia/uzupelnienie_dla_sesji_strategicznej_2026-09-12.md` ·
`wazne/REJESTR.md` · `wazne/research/audyt_pokrycia_roadmapy_2026-09-10.md` ·
`wazne/ewolucja/astra/2026-09/evolution_log_2026_09_01.md` (§2.4, §2.6, NOWE 1) ·
`wazne/ewolucja/astra/2026-09/evolution_log_2026_09_12.md` (§7 — N3) ·
`wazne/ewolucja/siostry/2026-09/evolution_log_2026_09_04.md` (§2 — trzy wersje daty) ·
`wazne/bugi/pomiar_klamie.md` (pkt 5 — wzorce szersze niż jedna forma) ·
`backend/cross_talk.py` · `backend/prompts/astra_base.txt:122` ·
`backend/semantic_pipeline.py:121,131-142` · `backend/main.py:604,2539` ·
`backend/nocna_analiza.py:13`
