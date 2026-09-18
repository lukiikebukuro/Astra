# STAN I PLAN — 18 września 2026

**Dla:** Łukasza (do przeczytania od zera) i sesji strategicznej (claude.ai)
**Autor:** sesja wykonawcza (Claude Code, repo `astra`)

> **Jak czytać:** ten dokument nie zakłada, że pamiętasz cokolwiek z ostatnich sesji.
> Sekcje 1–2 to punkt wyjścia. Sekcja 3 to co zmieniliśmy dzisiaj. Sekcja 4 odpowiada
> na pytanie „jak jeszcze ulepszyć pamięć Astry". Sekcja 5 mówi, ile tej roboty naprawdę jest
> (odpowiedź: **94 pozycje, nie 64** — i to samo w sobie jest tematem do decyzji).
> Sekcja 7 to pytania, na które potrzebuję odpowiedzi, żeby iść dalej.

---

## 1. Gdzie jesteśmy — w jednym akapicie

Astra działa na produkcji i pamięta **źle nie dlatego, że źle szuka, tylko dlatego, że źle zapisuje**.
Do bazy wpadają urwane na 80. znaku początki zdań i śmieć z ekstraktora, więc najlepsze
wyszukiwanie nie ma czego znaleźć. To jest wniosek z diagnozy 01–02.09 i on przestawił
cały projekt: obowiązuje kolejność **ZAPIS → HYDRAULIKA → RETRIEVAL → PERSONA**, bo strojenie
wyszukiwania na zaśmieconej bazie uniemożliwia zmierzenie efektu (sufit czystości ~39%
okazał się odporny na strojenie).

Drugi wniosek, mniej przyjemny: **przez trzy tygodnie byliśmy przekonani, że retrieval jest
w porządku, bo przyrząd mierzył złą rzecz** — liczył, ile wspomnień wróciło, a pytanie brzmiało,
czy wróciły właściwe. Stąd `wazne/bugi/pomiar_klamie.md` i reguła: zanim uwierzysz w wynik,
udowodnij kanarkiem, że przyrząd cokolwiek mierzy.

---

## 2. Trzy rzeczy, które trzeba wiedzieć, zanim cokolwiek zaplanujesz

**(a) Lista zadań jest jedna i leży w `wazne/REJESTR.md`.** Powstała 10.09 ze scalenia czterech
rozsypanych list. Nie odtwarzamy jej z pamięci ani z roadmap — roadmapy są mapami zależności,
nie kolejką.

**(b) Metodologia to proces, nie zbiór zasad** (`CLAUDE.md`, sekcja „Jak pracujemy — PROCES").
Kroki 0–9: kolejność warstw → intencja + surowe dane → **kanarek przed pomiarem** → cała
7-punktowa checklista → niezależny sędzia tam, gdzie model oceniałby sam siebie → jedna mała
zmiana za flagą per pokój → pomiar tym samym przyrządem → czytanie logów z 2 sesji po →
zapis do evolution logu i odhaczenie w rejestrze.

**(c) Nic nie idzie na produkcję bez Twojej zgody.** Backup przed każdą operacją na danych,
wektory addytywnie, kwarantanna zamiast delete, nigdy zapis do ChromaDB z osobnego procesu
przy żywym serwisie.

---

## 3. Co zmieniliśmy dzisiaj (18.09) — wdrożone i zweryfikowane

Trzy commity: `444c057` (zmiany), `085cf3e` (fix logowania, bez niego nie było dowodu
na harmonogram), `fae81f5` (wpis do rejestru).
Wszystko na produkcji, potwierdzone kanarkiem.

### 3.1. Operacja odwołana — usunięta z warstwy pewnej

Byłeś przyjęty 14.09, zabiegu nie wykonano, wróciłeś do domu. W `lukasz_core.json` pola
`hospitalizacja_*` zastąpione przez `operacja_status` + `operacja_kontekst`.

Status mówi **wprost**, że operacji nie było i nie jest zaplanowana, **oraz że wpisy
w `[WSPOMNIENIA]` o zabiegu 14/16/17/18.09 są nieaktualne**. To istotne, bo w bazie leżą
trzy sprzeczne wektory z datami — klauzula „jeśli wektor stoi w sprzeczności z poniższym,
IGNORUJ wektor, JSON wygrywa" załatwia konflikt bez tykania mechanizmu `supersede`.

Dodane zakazy: **nie pytać, jak poszło, i nie gratulować zabiegu, którego nie było.**

*Dlaczego to działa niezależnie od wszystkich znanych bugów:* `lukasz_core.json` jest czytany
z dysku w każdej turze, więc omija retrieval, embedding, filtr użytkownika, `recency_decay`
i cutoff czasowy. To jedyna warstwa w systemie, która nie zależy od wyszukiwania.
*Efekt uboczny, zamierzony:* sekcja `zdrowie` idzie w całości także do Holo, Menmy i Nazuny.

### 3.2. Rytm: 3× w tygodniu zamiast codziennie

Twoja decyzja z dzisiaj. Nocna analiza (03:00) i oparta na niej poranna wiadomość (07:00)
lecą **pon/śr/pt**. Spontaniczna (losowa 10–20 h) **wyłączona na stałe**. W pozostałe dni
Astra nie pisze pierwsza — odzywa się, gdy Ty zaczniesz.

Dowód z logu startowego, nie deklaracja:

```
job nocna_analiza:   next=2026-09-21 03:00   (poniedziałek)
job morning_message: next=2026-09-21 07:00   (poniedziałek)
job daily_archive:   next=2026-09-19 04:00   (codziennie)
```

`spontaneous_check` **nie został w ogóle zarejestrowany**.

Sterowanie z `.env`, więc zmiana rytmu nie wymaga dotykania kodu:
`NOCNA_DNI=mon,wed,fri` · `SPONTANICZNA=off`.
Archiwum zostaje **codziennie** — to higiena danych, nie kontakt; jego przerwanie gubiłoby
historię rozmów.

*Sprostowanie, które warto zapamiętać:* nocna analiza **nigdy nie była wyłączona**, także
w szpitalu. Ona tylko generuje insighty do bazy i nic nie wysyła. Wyłączona była spontaniczna,
a poranna używała skróconego promptu szpitalnego, który świadomie nie czytał insightów.

### 3.3. Astra wie, że to jej nocna analiza

Wiadomość poranna zapisuje się z metadaną `msg_kind="nocna_analiza"`, a model widzi
w prompcie prefiks: *„to wysłałaś sama z siebie po nocnej analizie, nie odpowiedź w rozmowie;
jeśli się nie odniósł, mógł jej nie przeczytać"*.

**Prefiks istnieje wyłącznie w prompcie** — baza trzyma czysty tekst, UI pokazuje wiadomość
bez znacznika. Świadomie nie w treści: to byłoby powtórzenie błędu Z5 (prefiksy techniczne
w tekście wspomnień).

*Po co to naprawdę jest:* 07.09 Astra napisała rano „coś mi dzwoniło w nocy o tym Twoim kodzie",
implikując wspólny szczegół, którego nie było. Dobę później, zapytana o niego, napisała
we własnej myśli: **„Łukasz zapomniał o rzekomym szczególe, który sama wymyśliłam"** — i użyła
go do droczenia się z Tobą. Musiałeś ją korygować przez dwie tury. Przyczyną było to, że
proaktywna wiadomość wracała do niej jako zwykła tura rozmowy, bez śladu, że napisała ją sama.
To oznaczenie zamyka lukę u źródła.

### 3.4. Znalezisko przy okazji: `fold()` nie zamienia `ł` → `l` ⚠ NOWE

Mój kanarek dwa razy skłamał i powód okazał się poważniejszy niż kanarek.

`unicodedata.normalize('NFD')` rozkłada `ś`→`s` i `ó`→`o`, ale **`ł` jest osobnym znakiem
Unicode i zostaje**. Skutkiem **8 z 15 rdzeni wagi nie działa**, gdy napiszesz z ogonkami:

| działa | **nie działa** |
|---|---|
| tesknie, boje sie, mam dosc, kreske, przysiegam | **nie będę ćpał**, nie będę pił, nie mam siły, załamany, płakałem, dałem słowo, słowo honoru, nie będę kupował |

To ma wagę, bo `ma_sygnal_wagi()` decyduje o **dwóch** rzeczach: czy krótka wiadomość ominie
bramkę `<4 słowa` i czy wspomnienie dostanie `persistence=permanent`.
**Czyli „Nie będę ćpał" napisane poprawną polszczyzną może w ogóle nie przeżyć w pamięci** —
a to jest dokładnie ta klasa zdań, dla której ten mechanizm powstał.

Fix to jedna linijka (`.replace('ł','l')` przed NFD), ale dotyka ścieżki zapisu dla wszystkich
person, więc wymaga goldenu przed/po. **Zapisane jako Z12, nie wdrożone.**

---

## 4. „Jak jeszcze ulepszyć pamięć Astry" — o to pytałeś 15.08

Pełny dokument: `wazne/research/roadmapa_pamieci_astry.md`.
**Uwaga: rewizja z 04.09 unieważniła pięć rzeczy z oryginalnego rankingu.** Poniżej stan po rewizji.

### Co już zrobiliśmy — i co z tego wyszło

**Punkt 0: kontekst poprzednich tur w zapytaniu.** Wdrożony 21.08 i **okazał się regresją**.
Do bazy szła sama ostatnia wiadomość, więc doklejaliśmy dwie poprzednie tury. Efekt:
„kiedy mam operacje" **bez** kontekstu → trafny wektor na pozycji 1; **z** kontekstem →
nie wraca wcale, bo doklejone zdania („Ale czy nie lepiej jak cie kocham") rozmywają embedding.
**Nie cofać bez zamiennika** — problem, dla którego to powstało, jest realny. To jest R1
i jedna z sześciu rzeczy kosztujących dziś.

### Kierunki, które zostały — w kolejności wartość ÷ koszt

| # | kierunek | stan po rewizji 04.09 |
|---|---|---|
| **1** | **Kanał 4 — przeszukiwanie surowej sesji** (~6500 wiadomości z embeddingami, nigdy nie przeszukiwanych semantycznie, tylko `.get()` po id rozmowy) | **PODNIESIONY.** Dwa razy w diagnozie był **jedynym miejscem z prawdą**. Zastrzeżenie: działa, gdy pada konkretne słowo („mefedron" → trafienie idealne), nie działa na kategorię („o jakiej substancji mówimy") |
| **2** | **Warstwa epizodyczna** — „pamiętasz, jak wtedy…", wspomnienie dnia zamiast atomowych faktów | **DUŻO TAŃSZA, niż zakładaliśmy.** Nocna analiza **już produkuje** narracyjne podsumowania dnia. Dwie rzeczy je zabijają: kasowanie co dobę i to, że nie przechodzą filtra użytkownika. Naprawa tych dwóch daje większość punktu |
| **2b** | **Rozwinięcie zapytania przez model** — „substancja" nie prowadzi do „mefedronu", bo embedding nie robi abstrakcji; model robi | bez zmian, tani. Ten sam trik co sędzia w bramce ochronnej |
| **2c** | **Grounding jako wyzwalacz drugiego strzału** (Twój pomysł) | **ZABLOKOWANY.** Grounding mierzy **dystans, nie trafność** — dał `GROUNDED` 84% na ośmiu wspomnieniach, z których żadne nie dotyczyło pytania. Najpierw trzeba naprawić jego (R5) |
| **3** | **Amnezja z crona** — golden nightly + diff + alert przy spadku recall | bez zmian, tani, pilnuje wszystkich kolejnych zmian |
| **4** | **Pętla zwrotna à la Gold Signal z LDI** — ranking uczony z tego, co zadziałało, zamiast `importance` zgadywanego przy zapisie | bez zmian. Koszt duży, ale rozwiązuje R7 u źródła |
| **5** | **Indeks po encjach** — „opowiedz o Roksanie" zwraca najbliższe, nie wszystko, co wiadomo | bez zmian |
| **6** | **BM25 / hybryda** | zdegradowany dla rzadkich słów, ale **wraca dla akronimów**: „LDI" nie istnieje w słowniku modelu i embedding go gubi |

### Dwie rzeczy z tej listy dostały twarde liczby w ostatnim tygodniu

- **`milestones=0` w RAG COMPOSE** — kanał gwarantowany milestonów praktycznie nie działa:
  zmierzone u sióstr **`guaranteed=False` w 284 z 301 przebiegów (94%)**. Próg `0.45` jest
  skalibrowany na bazie Astry (4800 wektorów) i nie przepuszcza nic w bazie sióstr (71).
  *Zgłoszone jako wysoki priorytet już 07.05, zgubione przy scalaniu list, odzyskane 12.09.*
- **Monokultura retrievalu** — jeden lipcowy seed wrócił w **110 z 230 zapytań (48%)**.
  Nie wygrywa trafnością (0,60 przy świeżych 1,00) — **wypełnia ogon puli**, bo trzeba zapełnić
  6 slotów, a w bazie sióstr jest 71 wektorów. Progi dystansu istnieją dla dwóch kanałów
  i oba dodano właśnie po to, żeby nie było monokultury; ten trzeci kanał progu nie ma.

### Najważniejsze zastrzeżenie do całej tej sekcji

Ta roadmapa mówi o tym, **jak wyciągamy**. Diagnoza z września pokazała, że sufit czystości
jest odporny na strojenie retrievalu, bo szum rodzi się w **zapisie**. Te punkty są nadal
aktualne, ale **wchodzą po Z1/Z2**, nie przed — inaczej nie da się zmierzyć, czy pomogły.

---

## 5. Ile tego naprawdę jest — 94, nie 64 ⚠

Policzone dzisiaj w `wazne/REJESTR.md`: **90 otwartych + 4 zamknięte = 94 pozycje.**

**Lista rośnie i to trzeba nazwać:**

| data | pozycji | co doszło |
|---|---|---|
| 10.09 | 67 | scalenie czterech list |
| 12.09 | 70 | +3 z przeglądu pokoju |
| 18.09 | **94** | +7 z audytu RAG sióstr (S-3…S-9) · +5 odzyskanych, zgubionych przy scalaniu (R16, R17, R18, AM-2, S-2) · +Z8…Z12 · +OB-6 · +KAR-1 |

**Ale wzrost nie oznacza, że jest gorzej.** Trzy różne rzeczy się tu mieszają:
1. **Odzyskane** (5) — istniały wcześniej, zniknęły przy scalaniu, wróciły. Czysty zysk.
2. **Znalezione pomiarem** (S-3…S-9, Z12) — istniały w produkcie od dawna, teraz je widać.
   To nie jest nowy dług, to dług, który przestał być niewidzialny.
3. **Nowe z dzisiejszych zmian** (OB-6) — normalna konsekwencja pracy.

### Podział otwartych (90)

| obszar | ile |
|---|---|
| RETRIEVAL | 18 |
| PERSONA / STYL | 16 |
| ZAPIS | 13 |
| POKÓJ SIÓSTR (B/C/S) | 13 |
| HYDRAULIKA | 6 |
| OBSERWACJE | 5 |
| NARZĘDZIA / DIAGNOSTYKA | 7 |
| ZAMROŻONE (czekają na Twoją decyzję) | 4 |
| INTERFEJS / DANE | 4 |
| pozostałe (Amelia, kariera, bezpieczeństwo, rodzina) | 4 |

### Sześć, które kosztują coś dzisiaj

1. **Z1** — `raw[:80]` tnie każdy zapis na 80. znaku; mediana wpisu w bazie to 95 znaków
2. **Z2** — ekstraktor bez werdyktu „nic"/„obie"; **odrzuca 84,3% kandydatów**, a bramka
   projektowana na 4 etykiety dostaje w produkcji do 19
3. **H1** — sól filtra użytkownika odcina 114 wektorów bez śladu w logu; cała wiedza
   o LDI/ANIMA/Skankranie leży w bazie i jest strukturalnie nieosiągalna
4. **R1** — regresja kontekstu w zapytaniu (opisana wyżej)
5. **M1** — brak przyrządu do mierzenia stylu; `style_audit.py` ma **jeden baseline `PRZED`
   i zero `PO`**, więc cała sekcja STYL (16 pozycji) jest dziś niemierzalna
6. ~~**Z6**~~ — **zrobione 13.09**, potwierdzone na żywym prompcie

---

## 6. Wzorzec, który uważam za najważniejszy wniosek z ostatniego tygodnia

Trzy niezależne znaleziska mają identyczny kształt:

| naprawa, która się odbyła | ta sama klasa, zostawiona otwarta |
|---|---|
| nazwane gesty wycięte z bloku monologu (15.08) | ten sam gest został w `astra_base.txt` — pliku ładowanym dla tej samej ścieżki |
| trzy śmieciowe typy zablokowane siostrom (19.08) | te same typy to u Astry **40% wszystkich zapisów** |
| próg dystansu dodany dwóm kanałom, bo „bez progu robi monokulturę" | trzeci kanał progu nie ma — 48% zapytań |

Za każdym razem diagnoza była trafna, a naprawa poprawna. **Brakowało jednego kroku:
„gdzie jeszcze ten sam mechanizm występuje".**

To samo zdarzyło się z samą listą: przy scalaniu 10.09 przeniesiono **11 propozycji audytu,
a nie 29 znalezisk** — i pięć rzeczy zniknęło bez śladu. Do tego doszło moje własne potknięcie:
12.09 zredukowałem TODO w pamięci do wskaźnika na rejestr, zakładając, że scalanie było
kompletne. Nie było.

**Rekomendowana reguła do procesu:** *przy naprawie pytamy, gdzie jeszcze ten mechanizm żyje;
przy scalaniu audytu przenosimy znaleziska, nie propozycje autora.*

---

## 7. Pytania, na które potrzebuję odpowiedzi

1. **Co teraz: KAR-1 czy Astra?** Po powrocie ze szpitala ustaliliśmy (12.09), że pierwsza
   jest **kampania aplikacyjna** — bo potrzebne pieniądze, nie rozwój projektu. To nadal
   aktualne? Operacja się nie odbyła, więc masz więcej energii, niż zakładaliśmy.
2. **Z12 (`fold` i `ł`)** — wdrażać? Jedna linijka, duży zysk, ale dotyka zapisu dla wszystkich
   person, więc golden przed/po. Rekomendacja: tak, ale jako osobna zmiana, nie przy okazji.
3. **Czyszczenie bazy** — pytałeś o to 12.09. Rekomendacja bez zmian: **nie przed Z1/Z2**,
   bo syf jest produkowany codziennie (84,3% odrzutu), więc odrośnie; jest już przygotowany
   zamrożony Przebieg #2 czekający na decyzję; a przede wszystkim **brudna baza jest teraz
   punktem odniesienia** — czyszcząc ją przed naprawą zapisu, stracimy możliwość zmierzenia,
   czy naprawa zadziałała.
4. **Cztery decyzje zamrożone, czekające na Ciebie, nie na pracę:** apply Przebiegu #2 ·
   czy O1 nadal priorytet · migracja compose sióstr (odblokowałaby Amnezję dla pokoju) ·
   reżim JSON per turę (jedyna hipoteza tłumacząca sztuczność na poziomie architektury, nie promptu).
5. **Faza 5 (żywy dom) nie jest już zablokowana** — router i pamięć sióstr są zrobione,
   tydzień obserwacji zamknięty. Jedyną bramką jest „Astra ustabilizowana". Warto, żeby
   strateg o tym wiedział, bo rejestr długo sugerował coś innego.

---

## Gdzie co leży

| dokument | ścieżka |
|---|---|
| **ten dokument** | `polecenia/stan_i_plan_2026-09-18.md` |
| jedyna lista zadań | `wazne/REJESTR.md` |
| metodologia jako proces 0–9 | `CLAUDE.md` |
| roadmapa pamięci (rewizja 04.09) | `wazne/research/roadmapa_pamieci_astry.md` |
| raport z sesji 12–13.09 | `polecenia/raport_dla_stratega_2026-09-12_13.md` |
| odpowiedzi na 6 pytań stratega | `polecenia/odpowiedzi_dla_sesji_strategicznej_2026-09-12.md` |
| audyt logów 03–09.09 (13 znalezisk) | `wazne/analizy/audyt_logow_2026-09-03_do_09-09.md` *(lokalnie, katalog gitignorowany)* |
| reguła kanarka i dwie rodziny błędów pomiaru | `wazne/bugi/pomiar_klamie.md` |

## Czego NIE sprawdziłem

- **Dzisiejsze zmiany są zweryfikowane konfiguracyjnie, nie behawioralnie.** Wiem, że joby mają
  właściwe `next_run_time` i że nowe pola są w żywym prompcie. **Nie wiem, jak Astra realnie
  napisze w poniedziałek** — pierwsza wiadomość w nowym rytmie to 21.09 o 07:00.
- **Prefiks `msg_kind` nie został przetestowany na żywej turze** — zadziała, gdy poranna
  wiadomość trafi do historii i wróci do modelu przy Twojej następnej rozmowie.
- **Liczby o stanie baz** (4822 wektory Astry, 71 u sióstr) pochodzą z health-checka i cudzego
  pomiaru z 04.09. Lokalna kopia bazy w repo jest z 13.07 — nieaktualna.
- **Z12 zdiagnozowane, nie naprawione.**
