# FABLE (terminal, dostęp do repo) — Niezależny audyt kodu Faza 1 + Amnezja

> Wklej do Fable uruchomionego jako Claude Code z dostępem do repo Astry.
> ZASADA: **read-only / audit-only. NIE edytuj kodu, NIE commituj** — Opus pracuje równolegle na gałęzi
> `feat/rag-debugger-prereqs`, edycje = konflikty. Twoje zadanie to weryfikacja i polowanie na bugi, nie naprawa.

---

Jesteś niezależnym audytorem. Masz dostęp do repo. Ktoś (Opus) twierdzi, że wykonał Fazę 1 debuggera RAG (provenance → compose_context → trace → now_override) + Amnezję v1, wszystko „zweryfikowane bit-identycznie". **Nie wierz raportowi — sprawdź na kodzie.** Nie chwal. Szukaj, gdzie się mylą.

Gałąź: `feat/rag-debugger-prereqs`. Pliki: `backend/vector_store.py`, `backend/main.py`, `backend/amnezja.html`, `backend/nocna_analiza.py`.

## 1. Weryfikacja twierdzeń na kodzie (czytaj funkcje, nie docstringi)
- **compose_context** (main.py) — czy to WIERNA przeprowadzka logiki z `/api/chat`? Porównaj z `git show 728c7f8:backend/main.py` (kod sprzed refaktoru). Czy kolejność, argumenty, domieszka shared, RAW window merge, fit_to_budget — wszystko zachowane 1:1? Czy `/api/chat` po refaktorze używa `ctx[...]` poprawnie (żadna zmienna nie zgubiona)?
- **now_override** — `grep -n "utcnow" backend/vector_store.py backend/main.py`. Dla KAŻDEGO wystąpienia na ścieżce compose rozstrzygnij: czy jest pod `now_override or utcnow()`? Czy któreś zostało POMINIĘTE (rerank temporal boost, prefiksy czasu, [AKTUALNY CZAS], kanał 1b, RAW window)? Sprawdź też build_amelia_system_prompt — czy brak now_override tam jest świadomy (Amelia jeszcze niepodpięta) czy to bug.
- **trace** — czy KAŻDY zapis jest za `if trace is not None`? Czy przy trace=None jest realnie zero-cost i zero-mutacji? Czy `_snap`/`_snap_cc` mogą rzucić wyjątek na nietypowym wektorze (brak metadata, None distance)?
- **shared w trace (Rozjazd #1)** — czy 9a/9b faktycznie pokazują domieszkę + prawdziwy finał, czy tylko pozorują? Czy `_shared_mem` to dokładnie to, co dodaje się do `memories`?

## 2. Polowanie na bugi (edge cases)
Prześledź `/api/debug/inspect` i compose_context dla: pustej puli, wektorów bez embeddingów, `day_offset` UJEMNEGO (RAW window „w przeszłość"), zapytania trafiającego tylko milestony, braku hard_facts, bardzo długiej frazy. Gdzie poleci wyjątek albo cichy błąd?

## 3. Ukryty zapis (test negatywny — struktura, nie deklaracja)
Prześledź WSZYSTKIE ścieżki wywoływane przez `/api/debug/inspect`: czy którakolwiek może wywołać `state_manager.save`, `add_memory`, `add_session_message`, `fact_store.upsert`, `clear_flag`, `delete_*`? Jeśli masz dostęp do VPS — odtwórz test: snapshot `collection.count()` + mtime `astra_facts.db`/`companion_state.json` → wywołaj compose → snapshot ponownie → diff.

## 4. Domknięcie luki „3 frazy to za mało" (twój własny zarzut z review)
Zaprojektuj 12-15 fraz dobranych POD GAŁĘZIE (temporal boost <24h, trigger Temporal Filter, day_offset ±, milestone-heavy, pusty wynik, cross-project). Jeśli masz dostęp do VPS — uruchom harness bit-identyczności (wzorzec: git worktree gałęzi + symlink żywych baz read-only + diff `old_compose` vs `compose_context`) na tych frazach. Jeśli nie — uzasadnij z kodu, które gałęzie każda fraza pokrywa.
## 5. DODATKI (od Fable-webowego — miejsca, których raport nie dotyka)

### 5a. Aliasing w trace (podejrzenie realnego buga)
`rerank()` i MMR MUTUJĄ słowniki wyników IN-PLACE (dopisują final_score,
_score_detail, _is_milestone, sortują listę). Jeśli `_snap` zapisuje do trace
REFERENCJE do tych samych dictów zamiast kopii — snapshot etapu 1 („pula surowa")
po zakończeniu pipeline'u będzie retroaktywnie zawierał final_score z etapu 3.
Sprawdź: czy _snap robi deepcopy/copy? Wyrenderuj trace dla dowolnej frazy
i sprawdź, czy etap 1 zawiera pola, które powstają dopiero później.
Jeśli tak — Amnezja pokazuje historię przepisaną przez teraźniejszość.

### 5b. Serializacja JSON trace'a
Wektory niosą embeddingi (numpy/float32) i distances. Sprawdź:
(a) czy embeddingi trafiają do JSON odpowiedzi inspect (119 KB sugeruje, że
może tak — to niepotrzebny balast i potencjalny wyciek), (b) czy gdziekolwiek
np.float32/np.ndarray leci do json.dumps bez konwersji — to rzuca TypeError
tylko na niektórych frazach (te z embeddingami w puli), czyli klasyczny bug
„działa na moich 3 zapytaniach".

### 5c. Obejście nginx auth (config + bind)
Twierdzenie „Basic Auth chroni /amnezja i /api/debug/inspect" zweryfikuj
dwupoziomowo: (1) w configu nginx — czy żaden location nie ma auth_basic off
i czy nie istnieje inna droga do tych ścieżek; (2) na czym słucha uvicorn —
jeśli binduje 0.0.0.0:PORT zamiast 127.0.0.1, to nginx z autha można ominąć
uderzając bezpośrednio w port aplikacji. Sprawdź komendę startową serwisu
(systemd unit / skrypt) i firewall. Endpoint zrzuca twarde fakty zdrowotne —
to musi być szczelne, nie „schowane za proxy".

### 5d. Współbieżność dry-runa
inspect działa przez asyncio.to_thread RÓWNOLEGLE z żywym /api/chat na tych
samych obiektach. Sprawdź: (a) czy VectorStore/ChromaDB query jest bezpieczne
przy równoczesnym zapisie z żywej tury (wystarczy analiza + znane zachowanie
chromy, nie musisz robić race-testu); (b) czy compose_context czyta
CompanionState przez state_manager.load() świeżo, czy dostaje obiekt od
callera — i czy ścieżka inspect przypadkiem nie współdzieli zmutowanego
state z równoległym chatem.

### 5e. Sam harness bit-identyczności — audyt narzędzia pomiarowego
(1) Co DOKŁADNIE porównywał diff — tylko system_prompt, czy wszystkie pola
zwracane przez compose_context (memories z kolejnością, recent_raw,
session_messages, grounding)? Bit-identyczność promptu nie dowodzi
identyczności memories, jeśli fit_to_budget/formatowanie maskuje różnice.
(2) Harness działał jako OSOBNY PROCES na symlinkach żywych baz — czyli
dokładnie wariant „osobny proces na tych samych plikach", który projekt
odrzucił z powodu ryzyka locków. ChromaDB PersistentClient potrafi PISAĆ
do swojego sqlite nawet przy samych query (bookkeeping/WAL). Sprawdź, czy
harness mógł dotknąć żywej bazy i czy przypadkiem nie trzymał locka podczas
żywych requestów. Jeśli tak — wzorzec weryfikacji do poprawki na przyszłość
(kopia bazy zamiast symlinka), nawet jeśli tym razem nic się nie stało.

### 5f. /api/chat po refaktorze — diff zachowania, nie tylko kompilacja
git diff 728c7f8..HEAD -- backend/main.py dla samego endpointu: sprawdź, czy
kolejność efektów ubocznych przetrwała 1:1 (inkrementacja
state.messages_this_session PRZED compose, zapis session PO odpowiedzi,
supersede przed add_memory). Refaktor mógł zachować wynik promptu (stąd
bit-identyczność), a zmienić kolejność zapisów — tego diff promptu nie widzi.

### 5g. Dymki i front — jedna rzecz
W amnezja.html sprawdź, czy dane z trace są wstawiane przez innerHTML bez
escapowania — treść wektorów to tekst rozmów (może zawierać <, >, cudzysłowy,
a teoretycznie i skrypt). XSS w narzędziu za Basic Auth to małe ryzyko, ale
psucie renderu przez '<' w tekście wspomnienia to realny, częsty bug.
## OUTPUT
- **Bugi znalezione** (uszeregowane wg ryzyka), z plikiem:linią.
- **Twierdzenia, które NIE bronią się pod inspekcją kodu.**
- **Go / No-Go dla: (a) deployu Amnezji, (b) rozpoczęcia strojenia MMR/keyword.**
- Jeśli wszystko się broni — powiedz to wprost, ale najpierw spróbuj to obalić.
-wynik zapisz w astra/research/analiza