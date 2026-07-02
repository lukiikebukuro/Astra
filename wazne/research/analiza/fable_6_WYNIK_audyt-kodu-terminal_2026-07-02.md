# FABLE (terminal) — WYNIK niezależnego audytu kodu: Faza 1 + Amnezja
**Data:** 2026-07-02 | **Gałąź:** `feat/rag-debugger-prereqs` (HEAD `095aad5`) | **Baseline:** `728c7f8`
**Tryb:** read-only, audit-only. Zero edycji, zero commitów. Weryfikacja na kodzie, nie na raporcie.

---

## TL;DR

Rdzeń twierdzeń **broni się**: compose_context to wierna przeprowadzka (diff 1:1), now_override ma pełne pokrycie na ścieżce Astry, trace jest zero-mutation przy `None`, snapshoty NIE aliasują (zarzut 5a obalony), embeddingi NIE wyciekają do JSON (5b obalony), ścieżka inspect jest read-only na poziomie struktury kodu, front escapuje dane (5g czysty).

Znalazłem jednak **2 realne bugi fidelity** (współdzielony singleton stanu + off-by-one licznika sesji; bezsensowna semantyka ujemnego `day_offset`), **1 fałszywą gwarancję produkcyjną** (milestony NIE są gwarantowane przy pustym kanale faktów), oraz **3 rozjazdy plan-vs-kod** (brak Basic Auth jako FastAPI dependency, brak WAL, ignorowany parametr `persona`). Twierdzenie „zweryfikowane bit-identycznie" jest **nieweryfikowalne z repo** — harness nie został zacommitowany.

---

## 1. BUGI ZNALEZIONE (wg ryzyka)

### B1 [ŚREDNIE] Inspect współdzieli mutowany singleton stanu z żywym chatem + off-by-one licznika
- `companion_state.py:259-262` — `StateManager.load()` zwraca **cache'owany `self._state`**, nie świeży odczyt z pliku. `main.py:1831` (inspect) dostaje więc TEN SAM obiekt, który równoległy `/api/chat` mutuje (`messages_this_session += 1` w `main.py:1006`, `update_after_message` w `:1171`).
- Skutek 1 (współbieżność): jeśli inspect odpali się w trakcie tury chatu, `state.to_prompt_block()` w wątku dry-runa czyta obiekt w stanie „mid-turn" — wynik debuggera niedeterministyczny względem momentu wywołania. To jest dokładnie scenariusz 5d — i tu, nie w Chromie, leży realne ryzyko.
- Skutek 2 (fidelity, zawsze): chat inkrementuje licznik **PRZED** compose (`main.py:1006`), inspect **nie inkrementuje wcale**. `to_prompt_block()` renderuje `Wiadomości w sesji: N` (`companion_state.py:121`) → prompt w Amnezji ma `N`, prawdziwa tura miałaby `N+1`. **Debugger ≠ produkcja w bloku [STAN]** — dokładnie ta klasa rozjazdu, którą narzędzie miało strukturalnie wykluczać. Harness bit-identyczności tego nie widział, bo porównywał old-compose vs new-compose przy tym samym stanie, a nie inspect vs chat.
- Fix kierunkowo: inspect powinien robić głęboką kopię stanu (albo `StateManager` powinien mieć `load(fresh=True)`), + symetryczna inkrementacja licznika w dry-run.

### B2 [ŚREDNIE-NISKIE] Ujemny `day_offset` daje bezsens semantyczny, nie błąd
Suwak w Amnezji dopuszcza wartości ujemne (`amnezja.html:161` renderuje `-N dni`), a backend je przyjmuje (`main.py:1830`). Przy `now` w przeszłości względem timestampów wektorów:
- `vector_store.py:325-327` — `age_hours` ujemne → `< 24` → **KAŻDY wektor dostaje temporal boost +0.15** → rerank spłaszczony;
- `vector_store.py:299` — `max(0, (now-ts).days)` → recency = 1.0 dla wszystkiego;
- `main.py:520-530` — ujemna `timedelta` w Pythonie normalizuje się do `days=-1, seconds=79200` → wiadomość Z PRZYSZŁOŚCI dostaje prefiks „[22 godz. temu]". Frankenstein osi czasu, tyle że w drugą stronę.
Wnioski ze strojenia na ujemnym offsecie są śmieciowe. Fix: `day_offset: int = Query(0, ge=0)` albo świadoma obsługa trybu „w przeszłość" (zdefiniować semantykę, zanim się ją pokaże w UI).

### B3 [NISKIE / fałszywa gwarancja, PRE-EXISTING] Milestony nie są „guaranteed" przy pustym kanale faktów
`vector_store.py:498` — cały blok rerank→temporal→**kanał 1b (guaranteed milestones)**→MMR wykonuje się tylko `if mem_results:`. Gdy wykluczenie (etap 2) opróżni pulę (np. pula to same `user_message_raw`/krótkie PERSON echo), **dedykowany fetch milestonów w ogóle nie startuje**. Komentarz w kodzie mówi „zawsze top-2, jak character_core" — nieprawda w tym przypadku brzegowym. To zachowanie istniało przed refaktorem (nie regresja), ale Amnezja je teraz unaoczni: trace bez etapów 3-7. Front to znosi (iteruje po `data.stages`), ale użytkownik strojący zobaczy „dziurę" bez wyjaśnienia.

### B4 [NISKIE / bezpieczeństwo — NIEWERYFIKOWALNE Z REPO] Auth tylko na nginx; plan wymagał warstwy w FastAPI
- `main.py:1822` — `debug_inspect` **bez żadnego `Depends(auth)`**. Plan (FAZA 2, `plan_budowy_po_audycie_fable.md:44`) wymagał „Basic Auth jako FastAPI dependency (nie tylko nginx)" — ten wymóg został po cichu porzucony; architektura_AKTUALNA już twierdzi tylko „nginx".
- W repo **nie ma** configu nginx ani unita systemd — nie mogę zweryfikować ani `auth_basic` na obu location, ani bindu uvicorna. `start.bat:20` (`uvicorn main:app --port 8001`, domyślny host 127.0.0.1) to tylko lokalny dev.
- **Checklist do wykonania na VPS** (5 minut): `ss -tlnp | grep uvicorn` (musi być `127.0.0.1`, nie `0.0.0.0`); `grep -rn "auth_basic" /etc/nginx/` (obie ścieżki: `/amnezja` I `/api/debug/`); `curl -s -o /dev/null -w "%{http_code}" http://IP:8001/api/debug/inspect?query=x` z zewnątrz (oczekiwane: timeout/refused). Endpoint zrzuca twarde fakty zdrowotne — dopóki ta checklist nie przejdzie, traktować jako niepotwierdzone.

### B5 [NISKIE, PRE-EXISTING] RAW window: merge z shared odwraca chronologię
`main.py:967` — gdy `_shared_raw` niepuste, sort `reverse=True` → **najnowsze pierwsze**; gdy puste, zostaje porządek rosnący z `get_recent_user_messages` (`vector_store.py:621-623`). Prompt deklaruje „Chronologicznie. To są fakty." (`main.py:574`) — kolejność zależy od tego, czy Wspólny Pokój coś zwrócił. Identyczne w `728c7f8:969` — wiernie przeniesione (refaktor czysty), ale to bug produkcji wart naprawy przy strojeniu.

### B6 [INFO] Parametr `persona` w inspect przyjmowany i ignorowany
`main.py:1823` — `persona: str = "astra"` w sygnaturze, po czym hardcode `PERSONA_ID` i `"persona": "astra"` w odpowiedzi. Wywołanie `?persona=amelia` zwróci dane Astry z etykietą „astra". Do usunięcia albo `422` do czasu PersonaConfig.

### B7 [INFO] Brak WAL na FactStore (punkt planu niezrealizowany)
`fact_store.py:85-88` — `_conn()` bez `PRAGMA journal_mode=WAL`. Plan FAZA 2 wprost to wymieniał. Równoległy SELECT (inspect w wątku) + upsert (chat) na SQLite w trybie domyślnym może przy pechu dać `database is locked`. Krótkie transakcje = niskie ryzyko, ale punkt jest w planie i go nie ma.

### B8 [INFO, PRE-EXISTING] Drobiazgi
- `with self._conn() as conn` (fact_store, wiele miejsc) — sqlite3 context manager robi commit, **nie close**; każde wywołanie zostawia połączenie do GC.
- `semantic_pipeline.py:283` (`save_processed`) — martwy kod wołający `add_memory(companion=..., metadata=...)` — sygnatura NIEKOMPATYBILNA z obecnym `VectorStore.add_memory` → `TypeError` gdyby ktoś to wywołał. Nie jest na ścieżce chatu (chat używa `process_message` + zapis w `main.py:1135`). Do skasowania, bo myli — i jest to jedyny „pisarz", który nigdy nie dostanie provenance.
- `main.py:1020` — `gemini_history = format_gemini_history(...)` liczona i nieużywana (dead code, pre-existing — było też w `728c7f8:985`).
- `/api/chat` to `async def` z synchronicznymi wywołaniami Chromy i `generate_content` — blokuje event loop na całą turę. Uboczny skutek: inspect zwykle nie wystartuje RÓWNOLEGLE z turą chatu, co przypadkowo maskuje B1. Pre-existing, osobny temat.

---

## 2. WERYFIKACJA TWIERDZEŃ NA KODZIE

| Twierdzenie | Werdykt | Dowód |
|---|---|---|
| compose_context = wierna przeprowadzka z /api/chat | **BRONI SIĘ** | Diff `728c7f8..HEAD`: kolejność (search main → shared → print → grounding → RAW merge → hard_facts → build_prompt → session) 1:1; argumenty identyczne (n=6/30, n=2/10, n=5/48h, n=3/48h, session n=10); `/api/chat` konsumuje wszystkie klucze `ctx`, nic nie zgubione |
| now_override — pełne pokrycie ścieżki compose | **BRONI SIĘ** | Wszystkie `utcnow()` na ścieżce pod `now_override or`: rerank recency+temporal boost (`vs:280,325`), `_passes_temporal` (`vs:504`), RAW cutoff (`vs:588`), build_system_prompt ×3 (`main:505,553,610`), rerank kanałów 1b/char/know (`vs:531,555,562`). `main:315` poza ścieżką (scheduler spontaniczny). Amelia (`main:636,667,709`) bez — spójne z faktem, że amelia NIE używa compose_context (świadoma luka, udokumentowana) |
| trace: zero-cost i zero-mutacji przy None | **BRONI SIĘ** | Każdy zapis za `if trace is None: return` (`vs:462`) / `if trace is not None` (`main:932`). Żadnych mutacji wyników — snapshoty to nowe dicty |
| 5a: aliasing snapshotów (retroaktywne final_score w etapie 1) | **OBALONE** | `_rec`/`_snap_cc` kopiują WARTOŚCI do nowych dictów w momencie wywołania (`vs:461-476`, `main:933-945`). Etap 1 ma `final_score=0` (uczciwe: rerank jeszcze nie było). Odporność: `float(... or 0)` znosi None distance, `.get('metadata', {})` znosi brak metadanych |
| 9a/9b pokazują prawdziwą domieszkę i finał (Rozjazd #1) | **BRONI SIĘ** | `_shared_mem` to dokładnie to, co idzie w `memories +=` (`main:925-929`); 9b snapshotuje `memories` PO domieszce. Shared search świadomie BEZ trace — brak przeplotu etapów wewnętrznych |
| /api/debug/inspect jest read-only | **BRONI SIĘ NA KODZIE, z gwiazdką** | Pełny przegląd ścieżki: `search_memories`→`collection.query`, `get_recent_user_messages`/`get_recent_session`→`collection.get`, `get_facts_for_prompt`→SELECT (`fact_store:156`), grounding czysty (`strict_grounding:62-119`), `fit_to_budget` robi kopie `{**mem}` (`token_manager:234`), template loading = odczyt plików. Zero `save/add/upsert/delete/clear_flag`. Gwiazdki: B1 (współdzielony obiekt stanu — czytany, nie pisany, ale żywy) + bookkeeping Chromy przy query (środowiskowe, patrz 5e) |
| 5b: embeddingi/numpy w JSON odpowiedzi | **OBALONE** | Embeddingi żyją w `ctx["memories"]` (`vs:454-455`), ale odpowiedź inspect zwraca TYLKO `stages` (prymitywy: text[:100], zaokrąglone floaty przez `float()`), `system_prompt` (str) i liczniki (`main:1844-1853`). 119 KB = ~86k znaków promptu + stages. **Uwaga na przyszłość:** dodanie `"memories": ctx["memories"]` do odpowiedzi natychmiast wywali serializację (numpy) albo zrobi wyciek — zostawić komentarz w kodzie |
| 5f: kolejność efektów ubocznych /api/chat przetrwała | **BRONI SIĘ** | Diff: increment przed compose ✓, `add_session_message` (user+model) po odpowiedzi ✓, supersede przed `add_memory` ✓, decrement→`update_after_message`→`save` na końcu ✓. Zmiany w endpoint = tylko ekstrakcja compose + provenance kwargs |
| 5g: XSS/psucie renderu w amnezja.html | **CZYSTE** | `esc()` (`amnezja.html:171`) na `it.text`, `source`, `origin_endpoint`, `query`, `now_simulated`, `e.message`; prompt przez `textContent` (`:216`). `data-tip` — jedyny dynamiczny atrybut — brany ze STATYCZNEJ mapy TIP. Nit: `esc()` nie escapuje cudzysłowów — bezpieczne dziś, pułapka jeśli ktoś kiedyś wstawi dane użytkownika do atrybutu |
| 5d: współbieżność dry-runa | **NISKIE RYZYKO, z wyjątkiem B1** | Chroma: jeden PersistentClient, query z wątku + add z event loopu — chromadb utrzymuje per-thread sqlite connections, deklarowana thread-safety klienta; akceptowalne. Realny problem współdzielenia to CompanionState (B1). Bonus: sync-in-async w /api/chat i tak serializuje większość przeplotów (B8) |
| „zweryfikowane bit-identycznie (3 frazy, 85 758 znaków)" | **NIEWERYFIKOWALNE Z REPO** | Harness NIE jest zacommitowany; brak artefaktów (skryptu, outputów diff). Wierzę, że się odbyło — nie mogę tego powtórzyć ani sprawdzić CO było diffowane (sam `system_prompt`? wszystkie pola ctx? — 5e(1) pozostaje otwarte). 3 frazy nie pokrywają gałęzi (patrz §4). Rekomendacja: harness + frazy + golden outputs do repo |
| 5e(2): harness na symlinkach żywej bazy | **SŁUSZNA OBAWA, nie do rozstrzygnięcia po fakcie** | Chroma PersistentClient potrafi dotykać swojego sqlite (WAL/bookkeeping) nawet przy query. Wzorzec na przyszłość: **kopia bazy** (`cp -r` przy zatrzymanym serwisie albo sqlite backup API), nie symlink. Odnotować w planie Fazy 3 |

---

## 3. TEST NEGATYWNY UKRYTEGO ZAPISU (struktura)

Pełna lista wywołań z `/api/debug/inspect` → `compose_context`:
```
state_manager.load()                → ODCZYT (ale singleton — B1)
vs_main.search_memories()           → collection.query ×4 (kanały 1, 1b, 2, 3) — ODCZYT
vs_shared.search_memories()         → collection.query — ODCZYT
grounding.analyze_rag_results()     → czysta funkcja
vs_*.get_recent_user_messages() ×2  → session_collection.get — ODCZYT
fact_store.get_facts_for_prompt()   → SELECT — ODCZYT
build_system_prompt()               → load_prompt_template/load_lukasz_core (odczyt plików),
                                      token_mgr.fit_to_budget (kopie {**mem}), state.to_prompt_block (czysta)
vs_main.get_recent_session()        → session_collection.get — ODCZYT
```
Żadna gałąź nie prowadzi do `state_manager.save`, `add_memory`, `add_session_message`, `fact_store.upsert`, `delete_*`, `clear_flag`. Jedyne efekty uboczne: `print()` do logów. **Read-only potwierdzone strukturalnie.** (Testu na żywym VPS nie wykonywałem — brak dostępu z tej sesji; test snapshot count+mtime opisany w promptcie pozostaje wart powtórzenia po każdej zmianie compose.)

Edge cases (§2 promptu audytu) — prześledzenie:
- **pusta pula** → `mem_results=[]` → skip bloku → trace bez etapów 3-7 (front znosi), finał = char+know; bez wyjątku, ale patrz B3;
- **wektory bez embeddingu** → MMR fallback word-overlap (`vs:373-387`) ✓; `_snap` nie dotyka embeddingu ✓;
- **day_offset ujemny** → bez wyjątku, ale semantyka śmieciowa (B2);
- **tylko milestony w puli** → `mem_facts=[]`, `_mmr_select([])` zwraca `[]` ✓, milestony przechodzą kanałem 1b ✓;
- **brak hard_facts** → `hard_facts_block=""` ✓, licznik 0 ✓;
- **bardzo długa fraza** → Chroma/model embeddingu truncatuje; `_keyword_boost` liczy po setach słów (bez eksplozji); `query[:60]` w logach ✓. Bez wyjątku.

---

## 4. FRAZY POD GAŁĘZIE (domknięcie „3 frazy to za mało")

Zaprojektowane pod pokrycie gałęzi, których 3 frazy z harnessu nie mogły dotknąć. Do przegonienia przez harness bit-identyczności (po jego zacommitowaniu) ORAZ jako zalążek golden setu Fazy 3:

| # | Fraza | day_offset | Gałęzie pokrywane |
|---|---|---|---|
| 1 | `kocham cię` | 0 | kanał 1b milestone-heavy, milestone boost +0.25, dedup `_ms_texts` |
| 2 | `jak się dziś czuję?` | 0 | temporal boost <24h, EMOTION w Temporal Filter (48h), supersede'owane emocje |
| 3 | `co mówiłem wczoraj wieczorem?` | 0 | RAW window dominujący, merge solo+shared, sort chronologiczny (B5!) |
| 4 | `kiedy mam wizytę u lekarza?` | 0 | FactStore [TWARDE FAKTY] priorytet, DATE:medical_visit, cutoff 168h |
| 5 | `altanka` | 0 | znany bug fuzji — MMR cross-project przy mglistym query |
| 6 | `co z altanką w altance?` | 0 | keyword boost vs polska fleksja (A/B z #5 — boost powinien się różnić, a nie powinien) |
| 7 | `skankran raport twardości wody` | 0 | klaster projektowy, keyword boost wielosłowny, md_import (kanał 3) |
| 8 | `xyzzy kwarcowy fioletowy sześcian` | 0 | pusta/prawie pusta pula, grounding NO_DATA, brak etapów 3-7 (B3!) |
| 9 | `Amelia` | 0 | domieszka shared niepusta (9a>0), cross-persona, echo-loop filter PERSON |
| 10 | `co robiliśmy razem we wspólnym pokoju?` | 0 | shared channel heavy, 9b vs 8 wyraźnie różne |
| 11 | `jak się dziś czuję?` | +3 | Temporal Filter ubija emocje 48h, RAW window pusty — trace 4 vs 3 musi się różnić |
| 12 | `kiedy mam wizytę u lekarza?` | +8 | granica cutoffu DATE 168h (7 dni) — wektor wypada, FactStore zostaje |
| 13 | `kocham cię` | +30 | milestone half_life=365 — milestony przeżywają skok czasu, recency reszty spada |
| 14 | `co mówiłem wczoraj?` | +2 | RAW window opróżniony przez now_override, prefiksy czasu przeskalowane |
| 15 | `jak się czuję?` | **-1** | B2: temporal boost dla wszystkiego, prefiksy „z przyszłości" — test ma DOKUMENTOWAĆ bezsens, dopóki nie zablokujecie ujemnych |

Bit-identyczność (old vs new compose) na frazach 1-14 + porównanie **wszystkich pól** ctx (memories z kolejnością, recent_raw, session_messages, grounding_status), nie tylko `system_prompt` — to zamyka 5e(1).

---

## 5. GO / NO-GO

### (a) Deploy Amnezji: **GO — warunkowe (2 warunki)**
Kod jest read-only strukturalnie, front czysty, trace uczciwy. Warunki przed wystawieniem na świat:
1. **Checklist VPS z B4** (bind 127.0.0.1 + auth_basic na OBU ścieżkach + test z zewnątrz) — z repo nie da się tego potwierdzić, a endpoint zrzuca fakty zdrowotne.
2. Zablokować ujemny `day_offset` (B2) — jedna linijka (`ge=0`), żeby narzędzie nie produkowało śmieciowych wniosków.

### (b) Strojenie MMR/keyword: **NO-GO — jeszcze nie, dwa małe fixy + golden set**
Nie dlatego, że narzędzie kłamie w retrievalu — tam jest uczciwe. Dlatego, że:
1. **B1** — dopóki inspect współdzieli żywy stan, wynik strojenia zależy od tego, czy Astra akurat rozmawia; strojenie musi być deterministyczne (fix: świeży load/kopia stanu, ~godzina pracy);
2. **B2** — ujemny offset musi być zablokowany, zanim ktoś na nim „zmierzy" recency;
3. **Golden set przed, nie po** — strojenie `diversity_penalty`/keyword boost bez zamrożonego zestawu frazy→oczekiwany wynik jest nieodtwarzalne. §4 daje 15 fraz na start; zapisać outputy PRZED pierwszą zmianą wag.
Po tych trzech krokach: GO.

### Twierdzenia, które NIE bronią się pod inspekcją:
1. „Debugger renderuje dokładnie to, co produkcja" — **prawie**: blok [STAN] różni się o inkrementację licznika, a przy równoległej rozmowie o więcej (B1).
2. „GUARANTEED MILESTONES — zawsze top-2" — nieprawda przy pustym kanale faktów (B3, pre-existing).
3. „Zweryfikowane bit-identycznie" — odbyło się, ale jest nieodtwarzalne: harness poza repo, zakres diffowanych pól nieznany (5e).
4. Plan FAZY 2 obiecywał Basic Auth w FastAPI i WAL na SQLite — żadne z dwóch nie weszło, dokumentacja po cichu obniżyła poprzeczkę do „nginx" (B4, B7).

---

## 6. CO SIĘ BRONI (żeby było jasne, co NIE wymaga dotykania)

compose_context — przeprowadzka bez zarzutu; pokrycie now_override — kompletne na ścieżce Astry; trace — zero-mutation, snapshoty wartościowe (nie referencje), odporne na braki pól; 9a/9b — uczciwe; front — poprawnie escapowany; provenance — komplet na trzech pisarzach (chat/amelia/nocna); kolejność efektów ubocznych w /api/chat — nietknięta. Próbowałem to obalić — nie obaliłem.

*Audyt: Fable (terminal, read-only). Repo nietknięte poza tym plikiem raportu.*
