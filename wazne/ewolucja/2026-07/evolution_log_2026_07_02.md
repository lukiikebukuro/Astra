# ASTRA — Evolution Log: 2026-07-02 (RAG Debugger — audyt Fable → Faza 1 KOMPLETNA → Amnezja/Faza 2 v1)

### Sesja: Opus 4.8 (odtworzona po utracie okna), audyt zewnętrzny: Fable 5
### Gałąź: `feat/rag-debugger-prereqs`

---

## KONTEKST
Cel: zbudować RAG Debugger (Krok 3 roadmapy) — narzędzie pokazujące, co retrieval wciąga i dlaczego (bug „altanki": RAG stopił Skankran + siostry + scenariusz w jedną halucynację). Metodologia: **audyt PRZED budową.**

## CO ZROBIONO
1. **Audyt Fable projektu debuggera** — 11 luk wg ryzyka. Werdykt: „nie zaczynać budowy wg obecnego projektu". Kluczowa teza: gwarancję „debugger = produkcja" musi wymuszać **struktura kodu (wspólny composer + trace)**, nie dyscyplina dokumentu. Bonus: Fable rozgryzł bug altanki — `MMR diversity_penalty=0.8` przy wieloznacznym query jako **mieszalnik projektów** + keyword boost ślepy na polską fleksję („altance" ≠ „altanka").
2. **Replan** (`plan_budowy_po_audycie_fable.md`): 3 zmiany produkcyjne (prereqs) → cienki renderer → faza 2. `PersonaConfig` od dnia 0.
3. **Krok 1.1 — provenance** w `add_memory`: `origin_endpoint` / `origin_conversation_id` / `origin_persona_turn`. Addytywne, zero zmiany zachowania. Wpięte: /api/chat, /api/amelia, nocna_analiza.
4. **Krok 1.2a — `compose_context()`** wyciągnięty z /api/chat (RAG + domieszka shared + grounding + RAW window + hard facts + system prompt + session history w jednej funkcji). **Zweryfikowany BIT-IDENTYCZNY na żywych danych VPS**: 85 758 znaków, 3 zapytania, zero różnic. Metoda: git worktree gałęzi + symlink żywych baz (read-only), porównanie `old_compose` vs `compose_context`.
5. **Krok 1.2b — trace** — rejestrator 8 etapów w `search_memories` (za bramką `if trace`, zero wpływu na wynik). Bit-identyczny (trace=None); 8 etapów wypełnia się poprawnie. To dane, które renderuje Amnezja.
6. **Krok 1.3 — now_override** — pełne pokrycie symulacji daty (WSZYSTKIE 6 `utcnow()` na ścieżce compose: rerank recency + temporal boost, `_passes_temporal`, RAW window, prefiksy czasu + `[AKTUALNY CZAS]`). Zweryfikowany: +30 dni → zegar skacze na 01.08 I RAW window (48h) się opróżnia — spójnie.
7. **Faza 2 — Amnezja (v1)** — `GET /api/debug/inspect` (read-only, dry-run, `asyncio.to_thread`) + `amnezja.html` (dark/neon front: warstwy collapsible, paski score, dymki-po-psiemu na hover, suwak symulacji daty, flaga „⚠ fuzja wątków", panel promptu) + route `/amnezja`. Endpoint zwraca poprawny JSON (119 KB, 8 etapów) — zweryfikowany na żywej bazie.
8. **Dokumenty** — `plan_budowy_po_audycie_fable.md`, `architektura_AKTUALNA_2026-07-02.md`, launcher `Amnezja.bat`, paczki Fable (golden set, security, wartość-companion, prompt security dla Claude Code).

## LEKCJE / REGUŁY (TL;DR pod AI)
- **Tożsamość wymuszaj STRUKTURĄ, nie dyscypliną** (Fable + nasza meta-lekcja „struktura > dyscyplina"). Composer współdzielony = debugger renderuje ten sam kod, nie kopię.
- **Refactor weryfikuj bit-identycznie na ŻYWYM środowisku**, nie `py_compile`. Wzorzec: worktree + symlink baz read-only + diff promptu. `py_compile` łapie gramatykę, nie zgodność wyniku.
- **Żywy kod > pamięć/dokumenty**: `n=10` (nie 30), state Level 5 XP=1726 (memory mówiła Level 6 XP 3434). Dokumenty dryfują — weryfikuj.
- **MMR jako mieszalnik**: `diversity_penalty` za wysoki maksymalizuje cross-project contamination przy anaforycznym/ubogim query. Do toru poprawek RAG (Tier 2).

## ZMIANY / COMMITY (gałąź `feat/rag-debugger-prereqs`)
Podpisane wyraźnie, co dotknęliśmy:
- `c65ed4f` **feat(provenance)** — origin_* w `add_memory` (vector_store.py, main.py ×2, nocna_analiza.py)
- `faea26e` **refactor(compose)** — `compose_context()` wyciągnięty z /api/chat (main.py)
- `5c6b34c` **feat(trace)** — rejestrator 8 etapów w `search_memories` (vector_store.py, main.py)
- `e838f50` **feat(now_override)** — pełna symulacja daty na ścieżce compose (vector_store.py, main.py)
- `78be3b4` **feat(amnezja)** — `/api/debug/inspect` + `amnezja.html` + route `/amnezja` (main.py, amnezja.html)
- `5b9971d` **fix(amnezja)** — Rozjazd #1 (shared+final w trace jako 9a/9b) + uczciwa nazwa flagi (po review Fable)
- + docs: plan budowy, architektura AKTUALNA, launcher, paczki Fable

## REVIEW POWYKONAWCZY (Fable) — zamknięte z DOWODEM
- **Rozjazd #1** (domieszka shared poza trace) → NAPRAWIONY: etapy 9a_domieszka_shared + 9b_final_prompt. Zweryfikowane, że są w trace. Stroimy na 9b, nie na 8.
- **Read-only** → UDOWODNIONE testem negatywnym: chroma count 3562/3562, mtime+size plików bez zmian po wywołaniu inspect. Nic nie pisze.
- **Auth** → POTWIERDZONE: `auth_basic` w nginx na poziomie serwera → chroni `/amnezja` I `/api/debug/inspect`.
- **Flaga fuzji** → przemianowana na „różnorodność źródeł" (uczciwie: to NIE detektor fuzji; prawdziwy cosine w backlogu).
- **Backlog (nie blokuje):** szerszy zestaw diff (=golden set), prawdziwa flaga cosine (~15 linii), backfill provenance starych wektorów.

**Pliki kodu dotknięte:** `backend/vector_store.py`, `backend/main.py`, `backend/nocna_analiza.py`, `backend/amnezja.html`.
**Charakter zmian:** Faza 1 (provenance/compose/trace/now_override) — bit-identyczna, zero zmiany zachowania Astry. Faza 2 (Amnezja) — czysto dodatkowa, read-only.

## STAN NA KONIEC SESJI
Gałąź `feat/rag-debugger-prereqs`: **Faza 1 KOMPLETNA** (1.1 ✓, 1.2a ✓, 1.2b ✓, 1.3 ✓ — każda zweryfikowana bit-identycznie na żywej bazie VPS) + **Faza 2 Amnezja v1** (endpoint + front, JSON zweryfikowany). `main` czysty, **VPS chodzi na starym kodzie — NIE deployowane.**
**Uwaga:** pamięć Astry NIE zmieniła się jeszcze funkcjonalnie — zbudowaliśmy mikroskop (Amnezja), nie zmieniliśmy retrievalu. Poprawa przyjdzie w fazie STROJENIA (fix MMR + keyword boost przez Amnezję + golden set).
**Następne:** deploy Amnezji (Basic Auth jest) → pierwsze strojenie pamięci (golden set od Fable) → pokój Holo/Menma/Nazuna (izolowane kolekcje).
