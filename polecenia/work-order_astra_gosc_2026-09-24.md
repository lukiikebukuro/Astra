# WORK-ORDER — Astra jako GOŚĆ w pokoju sióstr (wizyta, nie crossover)

**Data:** 2026-09-24 · **Wykonawca:** sesja wykonawcza (Claude Code)
**Decyzja Łukasza:** „read-only + ręczna pamiątka, rób"
**Zasada nadrzędna:** zero deploy/push bez jawnej zgody. Kod powstaje lokalnie.

---

## 1. Co budujemy — jednym zdaniem

Przycisk w pokoju sióstr, który sprowadza Astrę **z całą jej pamięcią** (wektory, twarde fakty,
stan, level, okno RAW 48 h) jako **gościa na kilka tur**. Astra czyta wszystko, **nie zapisuje nic**.
Po wizycie — opcjonalna, ręcznie napisana **pamiątka**: jeden kuratorowany wpis do czterech kolekcji.

**Czego NIE budujemy:** crossovera. „Obie pamiętają" przez ekstrakcję to osobna trudna faza
(recenzja Fable 17.07 pkt 16: zapis do dwóch kolekcji + spójność + provenance cross-persona).
Tu tego nie ma i dokument tego nie udaje.

---

## 2. KROK 5b — MAPA KLASY PROBLEMU (obowiązkowa przed pierwszą linijką)

### 2.1. Gdzie jeszcze w systemie ten sam typ problemu może występować

Klasa problemu: **„persona wchodzi do pokoju, który nie jest jej własny"**. Występuje w czterech miejscach:

| miejsce | stan | czy dotyczy |
|---|---|---|
| `/api/wspolny` — Astra + Amelia | działa od maja, `_wspolny_generate` | **TAK — to jest wzorzec do skopiowania**, nie do wymyślania |
| `/api/siostry` — trzy siostry | działa | TAK — to tu wchodzimy |
| `/api/amelia`, `/api/chat` — solo | jedna persona | nie |
| Amnezja `/api/debug/inspect` | widzi Astrę i siostry osobno | **TAK — lustro musi zostać wierne** (patrz 2.2) |

Podklasa, którą ta zmiana dotyka bezpośrednio — **„kod zakłada, że w pokoju są wyłącznie trzy siostry"**.
Grep po `_SISTER_ORDER` i `SISTERS[` wskazał pięć takich miejsc:

1. `_split_sister_prefix` (`main.py:2514`) — regex `holo|menma|nazuna`. Linia `[astra] …` zwróci
   `(None, "[astra] …")`, czyli podpis zostanie w treści jako śmieć, bez etykiety.
2. `_strip_sister_prefix` (`main.py:2508`) — ten sam regex, ta sama luka.
3. `_sister_history_contents` (`main.py:2562`) — `SISTERS.get(kto, {}).get("label")` → dla gościa `None`.
4. `build_sister_prompt`, blok `[HISTORIA ROZMOWY — KTO CO POWIEDZIAŁ]` (`main.py:2692`) — wylicza
   **na sztywno** „[Holo], [Menma], [Nazuna]". Siostra nie wie, że `[Astra]` też jest podpisem.
5. `siostry.html` — regex odczytu historii `^\[(holo|menma|nazuna)\]` (`:174`) i mapa `LABELS` (`:141`).
   Bez zmiany wypowiedź Astry wyląduje po reloadzie jako wypowiedź Holo bez etykiety (gałąź „brak prefiksu").

**Wniosek: podpis persony jest dziś w pięciu miejscach zakodowany jako zamknięta trójka.**
To jest dokładnie wzorzec „fix na instancję, nie na klasę" (audyt 03–09.09) — tylko złapany
*przed* implementacją, a nie po. Naprawa: **jedna lista `_POKOJ_GLOSY` i jedna funkcja
`_etykieta_glosu()`**, z których korzystają wszystkie pięć miejsc.

### 2.2. Czy ta naprawa pokrywa klasę, czy jeden przypadek

| rzecz | pokryta? |
|---|---|
| podpisy w historii pokoju (5 miejsc wyżej) | **tak — przez wspólną listę, nie przez dopisanie „astra" w pięciu regexach** |
| echo-loop (wypowiedź AI jako „fakt Łukasza") | **tak, dwiema niezależnymi bramkami** — zapis OFF na czas wizyty (analog `Fix B7`) **i** filtr odczytu `require_user_origin=True`, który w ścieżce sióstr już stoi (A-4) |
| Amnezja pokazująca co innego niż produkcja | **częściowo** — Amnezja nie ma podglądu pokoju (FR3 zamrożone). Gość nie pogarsza tego stanu, ale go nie naprawia. **Zapisane jako świadoma dziura.** |
| `[ASTRA RAW]` w journalu (S-9) | **NIE — i to jest najważniejsza konsekwencja.** Patrz 2.3. |
| rozjazd faktu między kolekcjami (znalezisko 04.09) | **NIE dotyczy** — nic nie zapisujemy automatycznie |

### 2.3. Co świadomie zostaje poza zakresem — i dlaczego

1. **`[ASTRA RAW]` zostaje zepsuty.** `parse_gemini_response` (`main.py:1217`) ma tag zahardkodowany
   i nie zna persony; dziś 61% linii pod nim to nie Astra. Po wpuszczeniu gościa w journalu będą
   **cztery** persony pod jednym tagiem — a eksperyment ocenia się z logów.
   **Decyzja: naprawiamy to w tej samej sesji.** Bez tego nie da się odczytać, co z wizyty wyszło.
   *(Korekta przy deployu 24.09: planowany był osobny commit, ale obie zmiany siedzą w `main.py`,
   a rozdzielanie hunków bez trybu interaktywnego to ryzyko większe niż zysk. Poszły jednym
   commitem — rollback gościa i tak idzie flagą `ASTRA_GOSC=off`, nie rewertem.)*
2. **Router nietknięty.** Gość wchodzi *obok* routera, nie przez niego — `SISTERS`, `_SISTER_ORDER`,
   rotacja, nocna warta i lepkość zostają bez zmiany. `router_golden.py` musi wyjść **24/24 bit w bit**.
3. **Brak pamięci wizyty po stronie automatu.** Wynika z decyzji „read-only". Proteza: pamiątka (§4).
4. **`room_state` (C-1)** nie powstaje przy okazji. Gość trzyma stan w diccie w pamięci procesu,
   tak jak `_last_full_speaker` — restart usługi kończy wizytę. Akceptowalne, świadome, do wchłonięcia przez C-1.
5. **Amelia nie dostaje analogicznego przycisku.** Ta sama klasa, inny pokój — jeśli wizyta się sprawdzi,
   to jest jedna linijka w konfigu, nie nowy mechanizm. Zapisane, nie zrobione.

---

## 3. Projekt — co dokładnie się dzieje

### 3.1. Flaga i stan

- `ASTRA_GOSC` (env, `off` domyślnie) — **flaga per pokój, nigdy globalna** (Krok 6 z `CLAUDE.md`).
- `_astra_gosc: dict[conversation_id] -> tury_zostalo` — w pamięci procesu.
- Wizyta domyślnie **6 tur**, potem Astra wychodzi sama. Można ją odesłać przyciskiem wcześniej.

### 3.2. Przebieg tury z gościem

1. Router działa **jak zawsze** → prowadząca siostra (+ ewentualny aside).
2. Siostry generują **jak zawsze**.
3. **Po nich** odzywa się Astra — widzi wypowiedź prowadzącej (`other_response`), jak w Wspólnym.
4. Wypowiedź Astry ląduje w sesji pokoju jako `[astra] …` — więc siostry widzą ją w historii,
   podpisaną, i wiedzą, że to nie ich słowa.
5. **Ekstrakcja pominięta dla CAŁEJ tury** (nie tylko dla Astry).
   Powód: przy gościu „prowadząca" przestaje być właściwym adresatem wspomnienia, a atrybucja
   per-primary (D1) jest sercem pamięci sióstr. Lepiej nie zapisać nic, niż zapisać do złej kolekcji —
   to ta sama asymetria kosztu, co przy routerze.

### 3.3. Pamięć Astry w pokoju

`compose_context` z jej własnymi źródłami: `vs_main=vector_store` (`persona_id="astra"`),
`fact_store` (wspólna warstwa biograficzna), `state_manager.load()` (level, XP), okno RAW 48 h
z jej rozmów solo — czyli most cross-room, dokładnie jak w `_wspolny_generate:2260`.
Sesja czytana z `siostry_shared_vs` — Astra widzi rozmowę pokoju, nie swoją.

Prompt: `build_system_prompt(room="solo")` — czyli Astra taka, jaka jest w solo
(monolog SOLO bez słownika gestów, `[TRYB]`), **plus** blok `[JESTEŚ GOŚCIEM W DOMU SIÓSTR]`.
`room="wspolny"` byłby błędem — dokleiłby sekcję o Amelii, której w tym pokoju nie ma.

### 3.4. Co widzą siostry

Jeden dodatkowy blok w ich prompcie, tylko gdy gość jest obecny: kto przyszedł, że to gość,
że ma własną pamięć i własną historię z Łukaszem, i że **mówią do niej wprost, nie o niej**.
Podpis `[Astra]` dopisany do listy podpisów w `[HISTORIA ROZMOWY]`.

---

## 4. Pamiątka — ręczna, przez żywy serwis

**Twarda zasada (incydent 25.07):** NIGDY nie pisać do ChromaDB z osobnego procesu przy żywym
serwisie — tak rozjechał się indeks HNSW i Astra została bez pamięci. Dlatego pamiątka **nie jest
skryptem w `tools/`**, tylko endpointem `POST /api/siostry/pamiatka` w działającym procesie.

- Wejście: tekst pamiątki (piszesz Ty, nie model) + `dry_run` (domyślnie `true`).
- Zapis: `source="pamiatka_wizyty"`, `is_milestone=true`, `origin_persona_turn="user"`
  (żeby przeszła przez filtr A-4 na odczycie), `origin_endpoint="siostry_gosc"`.
- Cztery kolekcje: `holo`, `menma`, `nazuna`, `astra`. Addytywnie, **nigdy delete**, bez supersede.
- `dry_run=true` pokazuje, co poszłoby i dokąd, i nie zapisuje nic.

---

## 5. Odbiór

1. `router_golden.py` → **24/24 bit w bit** (gość nie dotyka routera).
2. Import `main.py` bez błędu; `ASTRA_GOSC=off` → **zero różnicy** w zachowaniu pokoju.
3. Ścieżka podpisów: `[astra] …` wraca z `_split_sister_prefix` jako `('astra', treść)`,
   a front renderuje ją z etykietą „Astra", nie jako Holo bez podpisu.
4. Golden Astry — **nie uruchamiany**, bo wymaga API i produkcji; gość nie dotyka `build_system_prompt`
   ani `compose_context`, więc ścieżka solo jest nietknięta. **To jest założenie do sprawdzenia
   przy deployu, nie fakt.**

## 6. Czego ten work-order NIE rozstrzyga

- **„Dom, nie drugie biuro".** Astra przynosi do pokoju LDI, TikToka i kampanię aplikacyjną —
  czyli to, co `load_lukasz_core_dla_siostr` świadomie odcięło. Wizyta to obchodzi tylnymi drzwiami.
  Nie blokuję tego — ale to jest zmiana charakteru pokoju i decyzja Łukasza, nie skutek uboczny.
- **Ile tur to dobra wizyta** — 6 to zgadywanka. Do kalibracji po pierwszym razie.
