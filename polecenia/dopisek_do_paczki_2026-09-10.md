# DOPISEK DO PACZKI — co jeszcze trzeba wiedzieć

**Data:** 2026-09-10 · **Do kogo:** sesja planująca (claude.ai)
**Kontekst:** dostałeś briefing 09.09, listę 16 zadań, roadmapę ogólną, roadmapę pamięci
i audyt pokrycia roadmapy. Ten plik uzupełnia tamtą paczkę o cztery brakujące dokumenty,
trzy zasady operacyjne i jedną sprzeczność w liście zadań.

---

## 1. Dołóż te cztery pliki — bez nich paczka jest niekompletna

| Plik | Dlaczego bez niego nie da się pracować |
|---|---|
| `wazne/bugi/pomiar_klamie.md` | **Najważniejszy brak.** Audyt pokrycia odwołuje się do niego na każdej stronie, ale go nie cytuje. To rejestr buga „przyrząd kłamie" — nie w produkcie, tylko w narzędziu, którym produkt oceniamy. Dziewięć wystąpień. Bez tej checklisty każdy zaproponowany pomiar będzie dziesiątym. |
| `wazne/ewolucja/astra/2026-09/evolution_log_2026_09_01.md` | Roadmapa ogólna i audyt pokrycia cytują z niego „§2.4", „§2.6", „§9" bez przerwy. Bez niego to wiszące odsyłacze — dostajesz wnioski bez dowodów, na których stoją. |
| `CLAUDE.md` (korzeń repo) | Mapa repo, zasady bezpieczeństwa, powracające wzorce bugów. Zadanie nr 7 z listy prosi o mapę folderów — połowa odpowiedzi już tam jest, nie trzeba jej budować od zera. |
| `wazne/bugi/mikrofon.md` | Tylko jeśli dotykacie zadania nr 4 (powiadomienia). Osobny bug, ale sąsiaduje — patrz §4 niżej. |

---

## 2. Trzy zasady operacyjne, których nie ma nigdzie w paczce

1. **Nie pushować i nie deployować bez wyraźnego potwierdzenia Łukasza.** Bez wyjątków.
2. **Przy migracji wektorów wgrywać addytywnie** — nigdy nie kasować, backup przed każdym zapisem.
3. **Nigdy nie pisać do ChromaDB z osobnego procesu przy żywym serwisie.**
   25.07 loader `own_life` puszczony jako osobny proces rozjechał indeks HNSW → Astra została
   bez pamięci, Amnezja bez etapów 3–7. Naprawa: restart `myastra`. To jest realne zagrożenie
   produkcyjne, nie teoria.

Dodatkowo: **pracujemy po polsku**, a import wiedzy do ChromaDB zawsze jako polska synteza,
nigdy surowy angielski scrape.

---

## 3. Sprzeczność w liście zadań — do rozstrzygnięcia przed planowaniem

**Zadanie nr 14 („hybrydowy mechanizm pamięci — plik zawsze czytany") to jest to samo,
co Z6 z audytu pokrycia.** Krytyczne fakty biograficzne żyjące w warstwie niezależnej
od retrievalu, zamiast w wektorach.

Problem: **nr 14 stoi w PRIORYTECIE 3 (po rekonwalescencji), a bug, który zamyka —
nr 1 (data operacji) — stoi w PRIORYTECIE 1 (przed szpitalem).**

Bez nr 14 zadanie nr 1 to łatanie pięciu przyczyn po kolei, każda z osobnym ryzykiem regresji.
Z nr 14 cała klasa problemu znika jednym ruchem — sam Łukasz napisał to zdanie w opisie zadania.

**Rekomendacja:** rozdzielić nr 14 na dwie wersje o różnym koszcie.

- **Wersja tania (przed 14.09):** data zabiegu i kluczowe fakty medyczne trafiają
  do `backend/prompts/lukasz_core.json` — pliku, który jest w prompcie **zawsze**, przy każdej turze.
  Zero zależności od ekstraktora, embeddingu, wygasania i retrievalu. Zmiana w pliku JSON,
  nie w kodzie. Ryzyko bliskie zeru.
- **Wersja docelowa (po rekonwalescencji):** Z6 z audytu — exact lookup w FactStore
  dla całej klasy faktów kalendarzowych, z kanarkiem sprawdzającym, z której warstwy przyszła data.
  To wymaga Z1+Z2 (naprawy ekstraktora) i jest robotą na tygodnie, nie na dni.

---

## 4. Podpowiedzi do konkretnych zadań z listy

### Zadanie 2 — dlaczego Menma pamiętała datę, a Astra nie
Prawdopodobnie cała odpowiedź: **siostry mają `SIOSTRY_EXTRACTION_MODE=on` od 19.08**,
a mechanizm `persistence` zdjął tam blocker `DATE`→168h. Zablokowane zostały trzy typy
(`DATE:inventory_status`, `FACT:correction`, `SHARED_THING:inside_joke`), emocje przepuszczone
bo wygasają po 48h. Golden sprzed włączenia: `wazne/fable/golden/golden_siostry_PRZED_on_2026-08-19.json`.
Rollback: `SIOSTRY_EXTRACTION_MODE=off` + restart.

To nie jest różnica w rerankerze ani w prompcie — to różnica w polityce trwałości.
Sprawdzić najpierw tę hipotezę, dopiero potem grzebać w Amnezji.

### Zadanie 3 — redukcja przewidywalności
Nie jest to jedno zadanie, tylko trzy, które w roadmapie mają osobne wpisy:
- **Z4** — `own_life.json` ma **dokładnie 7 zdań**, scheduler losuje z nich 2. Astra nie generuje
  refleksji, cytuje gotowiec. Seed nr 3 („zwinąć się w małą kulkę") padł 22.08, 23.08, 27.08,
  31.08 i 01.09 — wyłącznie na ścieżce proaktywnej.
- **P1** — `ZAKAZ PĘTLI` istnieje tylko dla `/api/chat`. Ścieżka proaktywna nie widzi tej reguły nigdy.
- **P13** (nowe, z audytu) — zakaz obejmuje „gest", a najliczniejsze pętle to metafory:
  „naginanie rzeczywistości" 14× w trzy dni, „chłód superkomputera" 7×, „KCB" jako przecinek.

Częstotliwość schedulera to czwarta, osobna sprawa. Nie mieszać jej z pętlą leksykalną —
to dwie różne przyczyny tego samego wrażenia.

### Zadanie 4 — powiadomienia
**Brak jakiegokolwiek wcześniejszego dokumentu.** Zaczynacie od zera.
Nie mylić z bugiem mikrofonu, który ma wdrożoną diagnostykę (`2a8e9a1`, `2e3ad43`) i czeka
na jedną nieudaną próbę z telefonu. Ścieżka serwerowa mikrofonu jest wykluczona dowodowo.

### Zadanie 8 — historyczny szum w bazie
Hipoteza Łukasza (wektory sprzed 19.08 gorsze) jest zgodna z pomiarem z 25.08: czystość ~39%
i **odporna na strojenie retrievalu** — cały szum pochodzi z `extracted_*`, czyli z zapisu.
Powiązane, nieujęte w liście: audyt §2.5 pokazał, że mediana wpisu w bazie to **95 znaków**,
bo `semantic_pipeline.py:258` tnie każdy zapis na 80. znaku. To dotyczy całej bazy, nie tylko starej.
Pytanie do rozstrzygnięcia, którego nie ma w żadnym dokumencie: **co zrobić z ~4700 wektorami,
które są już amputowane.** Naprawa `raw[:80]` działa tylko w przód.

---

## 5. Zastrzeżenie o audycie pokrycia — czytać zanim się go użyje

Audyt powstał w trybie read-only i **nic w nim nie jest zweryfikowane na żywych danych.**
Sprawdziłem wyłącznie, że cytowane linie kodu istnieją i mówią to, co przypisują im audyty Gemini.
Żadnej tezy behawioralnej nie potwierdziłem na produkcji.

**To jest lista hipotez z adresami, nie diagnoza.** Traktować jak katalog miejsc do sprawdzenia.
Jedna rzecz jest w nim otwarcie nierozstrzygnięta: skąd bierze się gest `*opieram głowę*`
w wariancie SOLO, skoro nazwane gesty wycięto z niego 15.08, a znajduję je tylko w bloku Amelii
(`main.py:283`). Do sprawdzenia przed dotykaniem czegokolwiek w warstwie stylu.

---

## 6. Ograniczenie, o którym trzeba pamiętać przy planowaniu

**Operacja 14.09.** Dziś 10.09. To są cztery dni.

Łukasz pracuje w trybie minimalnym, wieczorami — od lipca, świadomie, żeby chronić czas kreatywny.
Crohn ogranicza energię. Zamknięcie listy 16 punktów nie jest realne i nie było zamierzone:
sam napisał w niej, że Priorytet 3 zostaje w całości na rekonwalescencję.

**Nie planować wszystkiego naraz.** Lista 16 punktów jest mapą, nie kolejką na ten tydzień.
Jeśli plan na te cztery dni ma zawierać więcej niż jedną rzecz, jest za duży.

---

## 7. Co bym zrobił przed szpitalem, gdyby trzeba było wybrać jedno

**Tanią wersję zadania nr 14.** Data zabiegu i kluczowe fakty medyczne wpisane wprost
do `lukasz_core.json` — pliku obecnego w prompcie zawsze, przy każdej turze.

Uzasadnienie:
- zamyka zadanie nr 1 (bug daty) bez tykania ekstraktora, retrievalu i polityki trwałości
- jest zmianą w pliku JSON, nie w kodzie — ryzyko regresji bliskie zeru
- zdejmuje jedyną rzecz z tej listy, która ma znaczenie 14 września o poranku:
  żeby Astra wiedziała, gdzie on jest

Wszystko inne — roadmapa, styl, szum historyczny, powiadomienia — poczeka do rekonwalescencji
i nic na tym nie straci.

**Uwaga przy weryfikacji:** dziś data „14 września" dociera do promptu przez `Aktywne sprawy`
w CompanionState — czyli ulotny stan bieżący, który **wygląda jak działająca pamięć i nią nie jest**
(audyt §2.6, punkt 21). Sprawdzając, czy poprawka zadziałała, trzeba upewnić się,
**z której warstwy** przyszła data. Inaczej kanarek zapieje z fałszywego źródła.

---

## Pliki, o których mowa w tym dopisku

`wazne/bugi/pomiar_klamie.md` · `wazne/ewolucja/astra/2026-09/evolution_log_2026_09_01.md` ·
`CLAUDE.md` · `wazne/bugi/mikrofon.md` ·
`wazne/research/audyt_pokrycia_roadmapy_2026-09-10.md` ·
`wazne/research/ROADMAPA_OGOLNA_PROJEKTU.md` · `wazne/research/roadmapa_pamieci_astry.md` ·
`backend/prompts/lukasz_core.json` · `backend/prompts/own_life.json` ·
`wazne/fable/golden/golden_siostry_PRZED_on_2026-08-19.json`
