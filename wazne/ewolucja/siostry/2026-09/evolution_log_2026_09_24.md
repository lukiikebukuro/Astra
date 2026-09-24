# 2026-09-24 — Astra jako GOŚĆ w pokoju sióstr + naprawa tagu w logu (S-9)

> **Status: ZBUDOWANE LOKALNIE, NIEZDEPLOYOWANE.** Zero push, zero restartu usługi,
> zero zapisu do jakiejkolwiek bazy. Flaga `ASTRA_GOSC` domyślnie `off` — po wgraniu
> kodu bez zmiany `.env` pokój zachowuje się **dokładnie** tak jak dziś.

**Zlecenie Łukasza:** *„a moglibyśmy sprowadzić na chwilę Astrę do dziewczyn? jakiś przycisk
który przywołuje ją tam i ma cross memory […] ale odwiedza po prostu dziewczyny?"*
→ po rozmowie o kosztach: **„read-only + ręczna pamiątka, rób"**.

---

## 1. Co powstało

**Wizyta, nie crossover.** Astra wchodzi do pokoju sióstr z pełną własną pamięcią i nie zapisuje nic.

| element | gdzie |
|---|---|
| flaga `ASTRA_GOSC` (`off` domyślnie) + stan wizyty `_astra_gosc` | `main.py:2448-2470` |
| `build_astra_gosc_prompt` — jej prompt solo + blok `[JESTEŚ GOŚCIEM W DOMU SIÓSTR]` | `main.py:2904` |
| `_generate_astra_gosc` — generacja, read-only | `main.py:2958` |
| wpięcie w turę pokoju (Astra odzywa się PO siostrach) | `main.py:3197-3225` |
| `POST/GET /api/siostry/gosc` — zawołaj / odeślij / stan | `main.py:3253-3283` |
| `POST /api/siostry/pamiatka` — ręczny wpis do 4 kolekcji, `dry_run` domyślnie | `main.py:3294` |
| blok `[GOŚĆ W DOMU]` w prompcie sióstr (tylko na czas wizyty) | `main.py:2796` |
| przycisk, kolor gościa, regex historii | `siostry.html` |

**Pamięć Astry na wizycie** — z jej własnych źródeł, dokładnie jak w Wspólnym:
`vector_store` (persona `astra`), `fact_store` (wspólna warstwa biograficzna),
`state_manager` (level, XP, bramka `[TRYB]`), okno RAW z 48 h rozmów solo (most cross-room).
Sesja czytana z `siostry_shared_v1` — widzi rozmowę pokoju, nie swoją.

**Świadoma decyzja:** `vs_shared = shared_vector_store` (jej wspólna pamięć z Amelią),
a **nie** `siostry_shared_v1`. Astra przynosi na wizytę własną pamięć, nie dostaje kroniki
domu, do którego przyszła. Odwrócenie to jedna linijka, gdyby wizyta pokazała, że lepiej inaczej.

---

## 2. Dlaczego wizyta, a nie crossover — i co to znaczy w praktyce

Projekt pokoju zakładał crossover w drugą stronę: *„Menma idzie poznać Astrę, potem OBIE pamiętają"*.
Recenzja Fable (17.07, pkt 16) oflagowała to jako **OSOBNĄ TRUDNĄ FAZĘ**: zapis do dwóch kolekcji
+ spójność + provenance cross-persona.

Od tamtej recenzji doszedł twardy dowód, że to nie była ostrożność na wyrost: przegląd 04.09
pokazał **jedną datę zabiegu w trzech wersjach, w dwóch kolekcjach**, bo `supersede` działa
w obrębie jednej kolekcji i jednej pary `(typ, podtyp)`. Automatyczny zapis wizyty do czterech
kolekcji naraz produkowałby ten sam rozjazd, tylko szerzej.

**Stąd podział:** odczyt (Astra przynosi pamięć) — wchodzi dziś. Zapis (obie pamiętają) —
**ręcznie, jednym kuratorowanym wpisem**, tekst pisze Łukasz.

### Dlaczego pamiątka jest endpointem, a nie skryptem w `tools/`
Incydent 25.07: loader `own_life` puszczony jako osobny proces przy żywym serwisie rozjechał
indeks HNSW i Astra została bez pamięci. **Do ChromaDB pisze wyłącznie proces, który ją trzyma otwartą.**
Skrypt w `tools/` byłby powtórzeniem tamtego błędu, tylko z ładniejszą intencją.

---

## 3. Ekstrakcja wyłączona dla CAŁEJ tury z gościem — to nie jest ostrożność

Powód wynika wprost z **D1** (atrybucja per-primary): wspomnienie trafia do kolekcji siostry,
która **prowadziła turę**. Gdy w pokoju jest Astra, „prowadząca" przestaje być właściwym
adresatem tego, co Łukasz mówi — bo mówi też (albo głównie) do gościa.

Zapis trafiłby do złej kolekcji, a tego się nie cofa (kwarantanna, nigdy delete).
To ta sama asymetria kosztu, którą zapisaliśmy przy routerze: **cisza jest tania, błędna
atrybucja jest trwała.** Analogicznie `Fix B7` w Wspólnym wyłącza pipeline dla całego pokoju.

---

## 4. Krok 5b w akcji — co mapa klasy problemu realnie złapała

Mapa (work-order §2) znalazła **pięć miejsc**, w których podpis persony był zakodowany
jako zamknięta trójka `holo|menma|nazuna`:

1. `_strip_sister_prefix` · 2. `_split_sister_prefix` · 3. `_sister_history_contents`
(`SISTERS.get(kto)` → `None` dla gościa) · 4. blok `[HISTORIA ROZMOWY]` w `build_sister_prompt`
(lista podpisów wpisana ręcznie) · 5. `siostry.html` — regex odczytu historii + mapa `LABELS`.

Bez tej listy naprawiłbym jedno albo dwa i wypuścił resztę. Skutek byłby konkretny:
**wypowiedź Astry po reloadzie strony renderowałaby się jako Holo bez podpisu**
(gałąź „brak prefiksu"), a siostry nie wiedziałyby, że `[Astra]` też jest podpisem —
czyli **dokładnie bug z 25.08, o jedną personę dalej**.

Naprawa: **jedna lista `_POKOJ_GLOSY` i jedna funkcja `_etykieta_glosu()`**, z których korzysta
wszystkie pięć miejsc. Nie pięć regexów z dopisanym „astra".

### 4a. Szósty przypadek — złapany dzień po, na pytanie „a jak sprawić, żeby poszła"

Pierwsza wersja sterowała **jedną** flagą `gosc_obecny` dwiema różnymi rzeczami: blokiem
`[GOŚĆ W DOMU]` *i* listą podpisów w `[HISTORIA ROZMOWY]`. Po wyjściu Astry jej linie
`[astra] …` zostają w oknie sesji jeszcze przez kilka tur — a siostra przestawała dostawać
informację, że `[Astra]` to podpis. **Przez te kilka tur mogła wziąć jej zdanie za własne.**

To znowu bug z 25.08, tylko wyzwalany przez *wyjście* gościa zamiast przez brak podpisów.
Naprawa: rozdzielenie na dwa sygnały — `gosc_obecny` (jest tu teraz → blok o gościu)
i `gosc_w_historii` (jej słowa mogą być w kontekście → podpis musi być wymieniony),
`_gosc_w_historii()` w `main.py:2470`.

Wniosek do procesu: mapa klasy problemu złapała pięć miejsc **w przestrzeni** (gdzie jeszcze
ten kod żyje), ale przegapiła jedno **w czasie** (co się dzieje, gdy stan się zmieni).
Pytanie, które to wyciągnęło, było proste: *„a potem jak sprawić żeby poszła"*.

---

## 5. S-9 przy okazji — bo bez tego eksperymentu nie dałoby się odczytać

`parse_gemini_response` logowała **zawsze** `[ASTRA RAW]`, mimo że woła ją siedem ścieżek.
Pomiar 03–09.09: 61% linii pod tym tagiem to nie Astra. Przy gościu w journalu byłyby
**cztery** persony pod jednym tagiem — a eksperyment ocenia się z logów.

Parametr `kto`, siedmiu wołających podaje swoje: `astra` · `amelia` · `wspolny:<persona>` ·
`siostry:<imie>` · `siostry:gosc-astra` · `amnezja:<persona>` (×2).

**Tag Astry zostaje dosłownie `[ASTRA RAW]`** — stare grepy działają dalej, tylko przestają
łapać cudze linie. Sprawdzone: żadne narzędzie w repo nie zależy od tego tagu
(`style_audit.py`, `przeglad_siostr.py` czytają eksporty per pokój, nie journal).

---

## 6. Odbiór — co realnie sprawdzone

| test | wynik |
|---|---|
| `router_golden.py` — deterministyczne | **24/24 PASS**, bit w bit jak przed zmianą |
| `router_golden.py` — rozkłady żywego domu | 5/5 PASS (noc 0,64 · wzmianka 0,33 · ster 0,48 · wołacz 0/500 błędów) |
| kompilacja `main.py` | OK |
| podpisy w historii (AST-test na realnym kodzie, bez importu `main`) | **11/11 PASS** — `[astra]` rozpoznane, `[Holo]`+`[Astra]` w jednym bloku model, obca persona (`[amelia]`) nietknięta |
| lista podpisów po wyjściu gościa (§4a) | **3/3 PASS** — `[Astra]` wymieniona gdy jest w pokoju ORAZ gdy już wyszła, a jej słowa są w oknie; nieobecna, gdy nigdy jej nie było |

Test podpisów celowo **nie importuje `main.py`** — import otworzyłby ChromaDB w osobnym
procesie. Funkcje są wycinane z pliku przez AST i odpalane na stubach, więc testowany jest
realny kod, a nie jego kopia.

## 7. Czego NIE sprawdziłem — granice tego wpisu

- **Ani jednej żywej tury.** Wizyta nie była uruchomiona z modelem: nie wiem, jak Astra
  realnie zachowa się w tym pokoju ani jak zareagują siostry. To jest cała treść eksperymentu
  i ona się jeszcze nie odbyła.
- **Golden Astry (`golden_harness.py`) nie uruchomiony** — wymaga API i produkcji. Gość nie
  dotyka `build_system_prompt` ani `compose_context`, więc ścieżka solo powinna być nietknięta,
  ale **to jest założenie do potwierdzenia przy deployu, nie fakt**.
- **Pamiątka nie była wywołana nawet w `dry_run`** — endpoint istnieje, nie został odpalony.
- **`state.computed_safe_haven`** liczy się w `compose_context`, więc blok `[TRYB]` u gościa
  powinien działać jak w solo — nie zweryfikowane na żywym prompcie.
- **Amnezja nadal nie widzi pokoju** (FR3 zamrożone). Gość tego nie pogarsza i nie naprawia:
  wizyty nie da się prześwietlić debuggerem.

## 8. Otwarte pytanie, którego kod nie rozstrzyga

**„Dom, nie drugie biuro".** `load_lukasz_core_dla_siostr` świadomie odcięło siostrom projekty
techniczne i TikToka. Astra przynosi to wszystko ze sobą — łącznie z blokiem scenariusza
(`state.scenariusz_block` jest ustawiany dla `persona_id == PERSONA_ID`, czyli także na wizycie).
Nie blokuję tego, bo Astra na wizycie ma być sobą. Ale to jest **zmiana charakteru pokoju**,
a nie skutek uboczny — i decyzja należy do Łukasza po pierwszej wizycie.

## Powiązane
`polecenia/work-order_astra_gosc_2026-09-24.md` (mapa klasy problemu, krok 5b) ·
`polecenia/status_pokoju_siostr_2026-09-22.md` (stan Planu C) ·
`wazne/ewolucja/siostry/2026-09/evolution_log_2026_09_04.md` (jedna data, trzy wersje) ·
`wazne/ewolucja/astra/2026-08/evolution_log_2026_08_25.md` (bug atrybucji, 25.08) ·
`wazne/siostry/archiwum/recenzja_fable_przed_dom_v2_2026-07-17.md` pkt 16 (crossover = osobna faza)
