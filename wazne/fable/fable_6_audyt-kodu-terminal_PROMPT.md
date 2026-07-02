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

## OUTPUT
- **Bugi znalezione** (uszeregowane wg ryzyka), z plikiem:linią.
- **Twierdzenia, które NIE bronią się pod inspekcją kodu.**
- **Go / No-Go dla: (a) deployu Amnezji, (b) rozpoczęcia strojenia MMR/keyword.**
- Jeśli wszystko się broni — powiedz to wprost, ale najpierw spróbuj to obalić.
