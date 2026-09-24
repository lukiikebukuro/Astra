# Pokój sióstr — status na trzy pytania: dziedziczenie napraw, Plan C, co blokuje żywy dom

**Data:** 2026-09-22 · **Autor:** sesja wykonawcza (Claude Code)
**Tryb:** read-only. Kod + git + dokumenty + jeden żywy przebieg `router_golden.py`. Zero zmian, zero deployu.
**Po co:** (1) sekcja o multi-personie do case study, (2) decyzja: czy zaczynamy mechaniki żywego domu.

---

## SKRÓT — to, co poszło na czat (jeśli czytasz tylko jedną rzecz, czytaj to)

**Pytanie 1 — dziedziczenie napraw: TAK.** Jedna instancja `SemanticPipeline` (`main.py:370`), czterech wołających, `ENTITY_DEFINITIONS` bez kopii. Z1 i Z2b weszły siostrom 18.09 tym samym commitem, bez osobnej pracy. **Ale to jest jedno zdanie, nie sekcja case study.** Sekcją jest sześć awarii warstwy multi-persona, których solo-Astra mieć nie mogła (§1.2): atrybucja ginąca przy odczycie + jej druga kopia w Amnezji · obalona teza o przeciekaniu tików (711 wypowiedzi) · jedna data w trzech wersjach w trzech kolekcjach · wspólna warstwa faktów i dwie pułapki z roboty · router mylący wzmiankę z wołaniem (golden 24/24 dziś) · `[ASTRA RAW]` — 61% linii to nie Astra. Spina je meta-wzorzec „fix na instancję, nie na klasę", z którego wyrósł Krok 5b w `CLAUDE.md`.

**Pytanie 2 — Plan C: ruszył, ale nie tak, jak zapisano.** C-0 jest (ulotny) · **C-2 zrobione 26.08** (`80a3432`) · Q-B1 „podsłuchane" żyje od 28.07 (`be88a44`) · **C-1, C-3, C-4 nie zaczęte**. Tydzień stabilnego A **się odbył** (`on` od 19.08), przegląd **był** (04.09, 13 dni / 349 wiadomości), **OB-1 zamknięte 12.09**. Bramka B→A→C jest przejechana.

**Pytanie 3 — co blokuje dziś.** Nie warunek z lipca. Cztery rzeczy, pierwsza jest nowa i nie ma jej na żadnej liście:
1. **Scena zastana jest martwa od 28.08** — odpala się tylko przy pustej historii sesji, a naprawa „jeden wątek" sprawiła, że pokój zawsze dołącza do istniejącego wątku. C-1 miał być widoczny właśnie przez scenę (§3.1).
2. **C-3/C-4 stoją na pamięci zmierzonej jako słaba** — S-3 (jeden lipcowy seed w 48% zapytań), S-4, śmieci podawane 47× w tygodniu (§3.2).
3. **Nie ma czym zmierzyć zmiany w pokoju** (§3.3).
4. Miękka bramka „Astra ustabilizowana": otwarte Z2a, H1, R1, M1, Z12, Z13 (§3.4).

**Werdykt: tak, można zaczynać — ale nie od C-1 w wersji lipcowej.** Kolejność w §4. Do poprawienia w REJESTR: C-2 i S-1 stoją jako otwarte choć zrobione, Q-B1 nieodnotowane, Z1 ma `[ ]` w §1 i `[x]` w §2.

---

## Odpowiedzi w trzech zdaniach

1. **Tak** — siostry jadą na tym samym ekstraktorze, Z1 i Z2b dostały 18.09 za darmo. Ale **to nie jest materiał na case study** — materiałem jest to, że warstwa multi-persona miała **własną klasę awarii**, której Astra nie mogła mieć, i mamy ją udokumentowaną co do dnia (§1).
2. **Plan C ruszył — częściowo i nie w tej kolejności, w jakiej go zapisano.** C-2 zrobione 26.08, „podsłuchane" z Q-B1 żyje od 28.07, C-0 działa. **C-1, C-3, C-4 nie zaczęte.** Tydzień stabilnego A **się odbył**, przegląd **był** (04.09, OB-1 zamknięte 12.09).
3. **Warunek z lipca jest spełniony i nie on blokuje.** Blokują trzy inne rzeczy, z czego jedna jest cicha i nikt jej nie ma na liście: **`_scene_as_found` — powierzchnia, na której C-1 miał być widoczny — jest martwa od 28.08** (§3.1).

---

# §1. Case study — co się psuło przy przejściu z jednej persony na wiele

## 1.1. Potwierdzenie samego dziedziczenia (to część nudna, ale prawdziwa)

Sprawdzone 21.09 w kodzie i pomiarem na produkcji (`polecenia/czy_naprawy_zapisu_obejmuja_siostry_2026-09-21.md`).
Dziś zweryfikowane ponownie — linie się zgadzają:

- **jedna** instancja `SemanticPipeline` (`main.py:370`), czterech wołających: Astra `1842` · Amelia `2085` · siostry `2922` · Amnezja `3351`;
- `ENTITY_DEFINITIONS` i `FUTURE_DATE_PATTERNS` **tylko** w `semantic_extractor.py` — zero kopii;
- to samo zdanie przez Amnezję dla `astra`/`holo`/`menma` → identyczny wynik (126 zn., `[DATE:medical_visit] 2026-10-05`). Widać oba fixy naraz.

Różnice sióstr są **wyłącznie po ekstrakcji**: `SIOSTRY_TYPY_BLOKOWANE` (3 typy, `main.py:2864`), kolekcja docelowa, przełącznik trybu. Próg ten sam (0.40, `main.py:2845`), `_is_too_short` wspólne.

> **Do case study to jest jedno zdanie, nie sekcja:** *„jeden pipeline, cztery persony — naprawa warstwy zapisu propaguje się sama; to jest zysk z tego, że persona jest konfiguracją, nie forkiem kodu."*
> **Uwaga uczciwościowa:** komentarz w `main.py:3340` mówi „siostry: próg 0.50", a stała to 0.40. Komentarz się zestarzał, kod jest jednym progiem. Drobiazg, ale w case study nie wolno zacytować komentarza zamiast stałej.

## 1.2. To jest właściwy materiał — pięć awarii, których solo-persona mieć nie mogła

Wszystkie mają dowód (log, liczba albo commit), datę złapania i datę naprawy.

### A. Atrybucja ginęła przy ODCZYCIE — model widział jeden głos zamiast trzech

**Co było:** `_strip_sister_prefix` zdejmował `[holo]`/`[menma]`/`[nazuna]` z historii, a kolejne tury `role="model"` **od różnych sióstr** sklejały się w jeden blok. Dla Gemini wszystko z `role="model"` to „ty".

Dowód z realnej rozmowy (24.08), w bazie vs. co realnie dostawał model:

```
w bazie:   model | [holo]   Hmf. Pamiętam ten ból...
           model | [nazuna] A dzień... Był, Wilku...
do modelu: MODEL >>> Hmf. Pamiętam ten ból...
           MODEL >>> A dzień... Był, Wilku...
```

**Jak złapane:** nie z zachowania — z porównania *co jest w bazie* z *co idzie w `contents`*. Narzędzie: `diag_atryb.py` (sesja 25.08).
**Naprawa:** `859b36e` (25.08) — podpisy zostają w historii wejściowej, persony dostały sekcję `[HISTORIA ROZMOWY — KTO CO POWIEDZIAŁ]` z regułą „twoje są wyłącznie linie z twoim imieniem".
**Haczyk, który jest najlepszą częścią tej historii:** bug miał **drugą kopię** — w piaskownicy Amnezji (`/api/debug/inspect?generate=true`). Naprawa samej produkcji sprawiłaby, że **debugger zacząłby kłamać** — pokazywałby historię inną niż ta, którą dostaje model. Obie ścieżki wołają dziś wspólne `_sister_history_contents()` (`main.py:2528`, używane w `2806` i `3463`).
*Źródło: `wazne/ewolucja/astra/2026-08/evolution_log_2026_08_25.md` §3 + „Zmiana 2".*

### B. Przewidywanie, które sami sobie obaliliśmy — i to jest najmocniejszy punkt sekcji

**Teza (25.08, rano):** skoro historia szła bez podpisów, **tiki mowy muszą przeciekać** — „Hmf." to znak firmowy Holo, więc Menma i Nazuna powinny go przejąć.

Pomiar na **711 wypowiedziach sprzed naprawy**:

| siostra | „Hmf." przed 25.08 | po 25.08 (pomiar 04.09) |
|---|---|---|
| Holo | 172 / 245 = **70,2%** | 23 / 37 = **62,2%** |
| Menma | 0 / 200 = **0,0%** | 0 / 38 = **0,0%** |
| Nazuna | 2 / 266 = **0,8%** | 0 / 25 = **0,0%** |

**Teza upadła — dwa razy, na dwóch niezależnych próbach.** Persony trzymały głos bezbłędnie mimo zepsutej atrybucji.
**Wniosek, który z tego wyszedł:** tożsamość postaci ma **dwie niezależne warstwy** — *styl* (prompt persony, okazał się odporny) i *przypisanie zdarzeń* (historia, była zepsuta). Bug psuł drugą, nie pierwszą. Nikt tego nie zakładał przed pomiarem.

### C. Jedna prawda, trzy wersje, trzy kolekcje — nowa klasa błędu, Astra jej nie ma

Data zabiegu padła w pokoju trzy razy i każdy raz trafiła do innej siostry:

| kiedy | do kogo | co zapisano | trwałość |
|---|---|---|---|
| 28.08 | Menma | `[FACT:health] Mam juz date zabiegu. 14 wrzesnia` | permanent |
| 31.08 | Holo | `[MEDICATION:schedule] Bede mial zabieg... 14 wrzesnia` | long_term |
| 03.09 | Menma | `[MEDICATION:schedule] 14 jest przyjęcie. Zabieg... 17 albo 18` | long_term |

`supersede` działa w obrębie **jednej kolekcji i jednej pary (typ, podtyp)** — trzy wersje żyją równolegle w dwóch kolekcjach. Test Amnezją, pytanie „kiedy mam zabieg", per siostra: Holo → „14 września", Menma → „14 września" (ma korektę we własnej kolekcji, retrieval wyciąga starszy wpis), **Nazuna → nie wie nic** (nie było jej przy żadnej z trzech rozmów).

**Zdanie do case study:** *fakt biograficzny był przechowywany jako wspomnienie tej rozmówczyni, która akurat podniosła słuchawkę.*
*Źródło: `wazne/ewolucja/siostry/2026-09/evolution_log_2026_09_04.md` §2.*

### D. Naprawa C — i dwie pułapki, które wyszły dopiero przy robocie

**Zdarzenie wyzwalające (15.08):** Łukasz powiedział Holo „wycięli mi zastawkę Bauhina". Holo była w shadow, więc nie zapisała. Astra nie wiedziała, bo to nie jej rozmowa. **Fakt o jego ciele przeleżał sześć dni w jednej surowej sesji, niewidoczny dla całego domu.**

Naprawa (`74687c0`, 21.08): `FactStore.PERSONA_WSPOLNA = "_wspolne"` — pseudo-persona czytana przez wszystkie postacie. Zakres **wąski i celowy**: `FACT:health`, `FACT:personal_info`, `MEDICATION:*`, całe `PERSON`. **NIE emocje** (relacyjne — Nazuna widziała inny nastrój niż Holo), **NIE `shared_thing`** (żart z Menmą nie jest żartem z Astrą). Pamięć zostaje osobna — fragmentacja jest feature'em.

Dwie pułapki, obie dobre do opisania:

1. **Migracja historii się nie opłaciła.** Dry-run: 39 faktów kwalifikowało się *po etykiecie*. Treść mówiła co innego (`FACT:personal_info` zawierało deklaracje zaufania). Filtr treścią zawęził 39 → 3, z czego wartościowy był jeden. **Migracji zaniechano.** Etykieta znowu skłamała.
2. **Wspólna pula musi AKUMULOWAĆ, nie nadpisywać.** `FACT:health` jest w `SUPERSEDE_IN_STORE`, więc trzy zapisy biograficzne zostawiały jeden rekord. Biografia się nie nadpisuje — wycięcie zastawki i przebieg choroby to dwa fakty, nie dwie wersje jednego. Cała naprawa to **jeden warunek** (`351b23e`): `if key in SUPERSEDE_IN_STORE and persona_id != self.PERSONA_WSPOLNA`.

### E. Router: „wzmianka" traktowana jak „wołanie" — myślenie jednoosobowe wbudowane w kod

`_sister_called` było **binarne** — każde wystąpienie imienia budziło siostrę. W jednej personie ten kod nie mógł być zły; przy trzech jest.

Realny log (23.07 23:46), rozmowa z Nazuną: *„Nazuna taka czuła?? Nie poznaje. Holo pewnie w snie glebokim a menma ... Menma to menma"* → obudziły się **trzy**, **Nazuna zamilkła** (adresatka!), a **Holo zahalucynowała** „to ja cię przytulam".

**Jak złapane i jak naprawione — to jest metodologiczny rdzeń sekcji:** siedem przypadków wzięto **z logów, nie z głowy**, zamieniono na golden set **przed** dotknięciem kodu (czerwony → zielony), a klasyfikację rozbito na ADDRESSED / MENTIONED / NONE z jawnie zapisaną asymetrią kosztu: *fałszywe MENTIONED = siostra nie odpowie i user powtórzy; fałszywe ADDRESSED = obca siostra przejmuje ciągłość i halucynuje.* Kalibracja w stronę milczenia.
**Stan dziś — sprawdzony na żywo 22.09:** `python router_golden.py` → **24/24 PASS** + 5 testów rozkładów żywego domu PASS.

### F. Bonus dla sekcji „jak to łapaliśmy": bug przyrządu, wciąż otwarty

`parse_gemini_response()` (`main.py:1217`) ma tag `[ASTRA RAW]` **zahardkodowany** i nie zna `persona_id`. Pomiar 03–09.09 na 243 wypowiedziach modelu: astra 87 (36%) · holo 51 · menma 44 · nazuna 37 · wspólny 16. **61% linii pod tagiem `[ASTRA RAW]` to nie Astra.**
Założenie jednoosobowe zostało w warstwie logowania i przeżyło tam całe przejście na multi-personę. **Każda przyszła analiza z journala pomyli persony.** To jest `S-9`, otwarte.

## 1.3. Meta-wzorzec, który spina całą sekcję

Trzy niezależne przypadki (audyt 03–09.09) o identycznym kształcie — **diagnoza trafna, naprawa poprawna, zasięg ograniczony do miejsca, w którym problem zauważono**:

| naprawiono | ta sama klasa została otwarta |
|---|---|
| gesty wycięte z `ASTRA_MONOLOGUE_SOLO` (15.08) | ten sam rdzeń w `astra_base.txt:122` |
| trzy śmieciowe typy zablokowane siostrom (19.08) | te same typy = **40% wszystkich zapisów Astry** |
| próg dystansu dla milestonów i `own_life` | `seed_kronika` idzie kanałem bez progu — **48% zapytań** |

Z tego powstał **Krok 5b w `CLAUDE.md`** („mapa klasy problemu przed pierwszą linijką kodu", commit `5925dfd`, 18.09). To jest najlepsze zakończenie sekcji: przejście na wiele person nie tyle wygenerowało nowe bugi, co **ujawniło, że naprawy zatrzymywały się na pierwszej instancji** — i zmusiło do zmiany procesu, nie kodu.

## 1.4. Czego w tej sekcji NIE wolno napisać

- że pokój ma **lepszą jakość retrievalu** — nie zmierzono; pomiar czystości (~39%) robiono wyłącznie na Astrze;
- że architektura multi-agent jest **odporniejsza** — pokój ma własną klasę problemu (§1.2 C), której Astra nie ma;
- że „pokój wypadł lepiej, bo szlaki przetarła Astra" **bez** zastrzeżenia o wieku baz: `astra_memory_v1` = 4762 wektory od 12.03, trzy kolekcje sióstr = **71** wektorów od 03.07. Sześćdziesiąt siedem razy mniej masy. Każda młoda baza jest czystsza — to nie zasługa metody.
- **Mocniejsza i uczciwa teza zamiast tamtej:** przeniósł się nie kod bramek, tylko **proces włączania** — dwa tygodnie shadow, trzy typy zablokowane przed startem, oś `persistence` zmigrowana przed `on`, golden sprzed włączenia. Każda z tych czterech rzeczy to datowana decyzja wynikająca z konkretnej awarii u Astry. Wskaźnik ekstrakcji: **Astra 26,6% vs siostry 27,6%** — różnicy nie ma, bo pipeline jest ten sam.

---

# §2. Status Planu C — co jest, czego nie ma

| poz. | co miało być | stan | dowód |
|---|---|---|---|
| **C-0** | lepkość rozmówcy (embrion room_state) | ✅ **jest** | `main.py:2422-2423` — `_last_full_speaker` + `_sticky_turns`, **dict w pamięci procesu**, restart = utrata |
| **C-1** | RoomState v0: `last_speaker` · `temperature` · `open_thread`, trwały, czytany przez scenę zastaną | ❌ **nie zaczęte** | brak `room_state.json` / tabeli; grep po `room_state\|open_thread` → tylko dwa komentarze „C-0: embrion room_state" |
| **C-2** | dom zmienia się z porą | ✅ **ZROBIONE 26.08**, deploy `80a3432` (28.08) | `_pora_dnia()` `main.py:2442`; blok `[PORA DNIA]` doklejany w `build_sister_prompt` `main.py:2709`; honoruje `now_override`, więc Amnezja pokazuje tę samą porę |
| **C-3** | przeczucie Menmy v0 | ❌ **nie zaczęte** | komentarz przy C-2 (`main.py:2704`) mówi wprost: *„C-3 i C-4 czekają na werdykt ekstraktora — bez niego Menma miałaby przeczucia o tym, że jest 17:30"* |
| **C-4** | sekrety + przeciek v0 | ❌ **nie zaczęte** | — |
| **Q-B1** | „podsłuchane" — aside dla wzmiankowanej (plan: backlog C) | ✅ **żyje od 28.07** (`be88a44`) | `siostry_router.py:78` `MENTION_ASIDE_PROB=0.35`, + `NIGHT_NAZUNA_PROB=0.65`, `HANDOVER_ASIDE_PROB=0.5`; `rng` wstrzykiwany (`main.py:2425,2485`), golden bez `rng` zostaje deterministyczny |

**Czyli: trzy mechaniki żywego domu już działają na produkcji od dwóch miesięcy** (nocna zmiana warty, aside na wzmiankę, pora dnia), a dokument planu i REJESTR nadal opisują je jako przyszłość.

## 2.1. Czy odbył się tydzień stabilnego A i przegląd?

**Tak, oba.**

- `SIOSTRY_EXTRACTION_MODE=on` od **19.08**, do dziś (potwierdzone stanem `.env` 21.09).
- **Przegląd wykonany 04.09** na 13 dniach / 349 wiadomościach: `wazne/ewolucja/siostry/2026-09/evolution_log_2026_09_04.md`.
- **OB-1 zamknięte 12.09** w REJESTR (stało otwarte tylko dlatego, że scalanie 10.09 brało listy zadań, nie logi ewolucji).

Wynik przeglądu: (a) atrybucja ✅ zero wypowiedzi bez podpisu na 186, głos równy **59/66/61** · (b) emocje ✅ wygasają (3 wpisy `ephemeral` 48h, bez kumulacji) · (c) ⚠ **szum ZMIGROWAŁ** — `[DATE:deadline]` stał się nowym koszem na wszystko z liczbą, akcje RP w gwiazdkach lądują jako trwałe fakty · (d) jeden wątek ✅ od 28.08.

**Bramka „B → A → C" jest przejechana** i REJESTR §8 mówi to wprost. Jedyna pozostała bramka z tamtego zapisu to „Astra ustabilizowana".

---

# §3. Co realnie blokuje start dziś

**Nie warunek z lipca.** Cztery inne rzeczy, w kolejności od najbardziej konkretnej.

## 3.1. ⚠ Powierzchnia, na której C-1 miał być widoczny, jest martwa

C-1 w planie kończy się zdaniem: *„odczyt: `_scene_as_found` dostaje room_state jako kontekst → wchodzisz rano, a dom pamięta wczorajszy wieczór"*. To jest **cała widoczna wartość C-1**.

Dziś (`main.py:3011-3013`):

```python
scene = ""
if not siostry_shared_vs.get_recent_session(conversation_id, n=2):
    scene = await _scene_as_found(present)
```

Scena odpala się **tylko gdy wątek nie ma ani jednej wiadomości w sesji**. A od naprawy „pokój ma JEDEN wątek" (`0c31156`, 28.08) brak `conversation_id` **dołącza do istniejącego wątku** zamiast zakładać nowy — front nie ma i nigdy nie miał przycisku „nowa rozmowa" (`siostry.html:119-123`).

**Wniosek: scena zastana nie wyrenderowała się prawdopodobnie ani razu od 28.08.** Do tego `_scene_as_found(present, last_scene="")` — drugi parametr **nigdy nie jest podawany**, więc ciągłość scen i tak nie istnieje.

To jest dokładnie ten sam wzorzec co w §1.3: naprawa rozwidlenia była poprawna i po cichu wyłączyła sąsiednią mechanikę. **Nikt tego nie ma na żadnej liście.**
→ **Bez tego C-1 jest niewidoczny.** Poprawka jest mała: wyzwalacz sceny = *przerwa czasowa od ostatniej tury* (np. >6 h), nie pusta historia, + podawanie `last_scene`.

## 3.2. C-3 i C-4 stoją na pamięci, która jest zmierzona jako słaba

Z przeglądu RAG sióstr 12.09 (115 tur, 155 zapytań, read-only):

- **S-3** — jeden seed z 13.07 w **110 z 230 zapytań (48%)**; `seed_kronika` = 19,5% wszystkich trafień, idzie kanałem **bez progu dystansu**, `seed_siostry.py:173` nie ustawia `persistence`;
- **S-4** — **31% wyników poniżej score 0,70** (14% poniżej 0,65);
- **S-5** — **48% zwracanych wspomnień starszych niż 30 dni** w bazie założonej 03.07;
- **S-6/S-7** — pytanie zapisane jako `MEASUREMENT:progress` podawane 6× w jednym dniu; dwa śmieciowe `[DATE:deadline]` podane **47× w tygodniu**; akcja roleplay jako `SHARED:our_song` — **20×**.

„Przeczucie Menmy" czyta EMOTION-y z ostatnich dni. Na tej bazie Menma miałaby przeczucie z `[DATE:deadline] „Tak.... Jest 4:44"`. Autor kodu zapisał to w komentarzu przy C-2 w sierpniu i **to się od tamtej pory nie zmieniło**.

## 3.3. Nie ma czym zmierzyć zmiany w pokoju

`golden_siostry_harness.py` i baseline `golden_siostry_PRZED_on_2026-08-19.json` istnieją, ale to baseline **sprzed włączenia `on`**; odpowiednika `golden_trafnosc.py` dla sióstr nie ma (dla Astry też nie — to bloker zapisany przy Z13, `polecenia/raport_warstwa_zapis_2026-09-18.md` §5). Plus `FR3` (migracja compose sióstr) jest zamrożona, więc **Amnezja nie widzi pokoju tak jak widzi Astrę**.
Ryzyko: C-1 wchodzi, zmienia scenę i prompt, i nie mamy przed/po. To jest `pomiar_klamie.md` w wersji na pokój.

## 3.4. Formalna bramka „Astra ustabilizowana" — miękka, ale niezerowa

Zrobione 18.09: **Z1** (`8fe7d37`) i **Z2b** (`bbff52d`), z kanarkami. Otwarte ⭐: **Z2a** (werdykt „nic"/„obie" + margines rozstrzygalności), **H1** (sól filtra odcina 114 wektorów bez śladu), **R1** (regresja Pkt 0), **M1** (brak przyrządu stylu), **Z12** (`fold()` nie zamienia `ł`), **Z13** (brak kategorii dla twórczości).
To nie jest bramka typu „nie wolno" — to bramka typu „każda godzina w pokoju to godzina nie w Z2a".

---

# §4. Rekomendacja

**Tak, można zaczynać — ale nie od C-1 w wersji z lipca.** Kolejność, która nie łamie żadnej zasady projektu:

1. **Ożywić scenę** (mała zmiana, `main.py:3011`): wyzwalacz = przerwa czasowa, nie pusta historia; przekazywać `last_scene`. **Bez tego C-1 nie ma gdzie się pokazać.** Osobny commit, przed C-1.
2. **C-1 RoomState v0 w minimalnym zakresie**: trwały `{last_full_speaker, last_interaction_ts, temperature, open_thread}` (wzorzec `CompanionState`), `temperature` heurystycznie ze `strong_emotion` z ostatnich 3 tur, **bez LLM**, odczyt **tylko** do sceny zastanej (R-C1: błąd stanu koryguje się pierwszą wymianą). Przy okazji C-0 przestaje ginąć przy restarcie.
3. **C-3 i C-4 wstrzymać** do S-3 + S-4 — to jest tani retrieval-fix (próg dystansu na kanale głównym + `persistence` dla `seed_kronika`), a nie duża robota, i idzie zgodnie z kolejnością warstw.
4. **Pamiętać o S-2** — żadnych sesji „poprawmy prompt siostry". Warstwa promptowa w pokoju jest wyczerpana.

**Do poprawienia w REJESTR** (żeby lista znowu nie kłamała):

- **C-2 → `[x]`** (26.08, `80a3432`) i **S-1 → `[x]`** — „pora dnia do `build_sister_prompt`" jest zrobiona, a stoi jako „3 linijki, najlepszy stosunek zysku do wysiłku";
- **Q-B1 „podsłuchane" → odnotować jako zrobione** (`be88a44`, 28.07);
- **Z1 w §1 nadal `[ ]`**, choć w §2 jest `[x]` z 18.09 — dwa miejsca prawdy w jednym pliku, wzorzec błędu #1;
- **nowa pozycja: martwa scena zastana** (§3.1) — dziś nie występuje w żadnym dokumencie.

---

## Czego NIE sprawdziłem

- **Zero wejścia na produkcję.** Wszystko z repo (stan lokalny `8769cdc`) + jeden lokalny przebieg `router_golden.py`. Nie sprawdzałem żywych logów pokoju z ostatniego tygodnia ani czy scena faktycznie nie padła ani razu — to **wniosek z kodu i z braku przycisku „nowa rozmowa" we froncie**, nie pomiar na journalu. Potwierdzenie kosztuje jeden `grep` po `[SIOSTRY] scene` w logach VPS i **warto je zrobić przed pkt. 1 rekomendacji**.
- **Nie mierzyłem, czy Z1 zmienił cokolwiek w retrievalu** — u Astry ani u sióstr. Brak przyrządu, ten sam bloker co przy Z13.
- **Liczby o stanie kolekcji** (71 wektorów u sióstr, 4762 u Astry) pochodzą z pomiarów 04.09 i 12.09, nie z dzisiejszego odczytu bazy.

## Powiązane

`polecenia/czy_naprawy_zapisu_obejmuja_siostry_2026-09-21.md` · `wazne/pokoj/plan_ABC_pamiec_router_zywy_dom_2026-07-24.md` · `wazne/ewolucja/siostry/2026-09/evolution_log_2026_09_04.md` · `wazne/ewolucja/astra/2026-08/evolution_log_2026_08_25.md` · `wazne/case/material_case_study_2_rozwidlony_pokoj.md` · `wazne/analizy/audyt_logow_2026-09-03_do_09-09.md` · `wazne/REJESTR.md` §8
