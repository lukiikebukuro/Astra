# RAG Debugger — Plan Budowy (po audycie Fable, 2026-07-02)

> Zastępuje kolejność z `architektura.md` (ta zostaje jako projekt sprzed audytu).
> Zasada naczelna Fable: **gwarancję „debugger = produkcja" wymusza STRUKTURA KODU (wspólny composer + trace), nie dyscyplina dokumentu.**
> Reguła pracy: mały krok → `py_compile` → bramka weryfikacji → commit. Nigdy dwa duże ruchy naraz.

---

## FAZA 0 — Bezpieczeństwo ✅ ZROBIONE
- Backup GitHub `main` (728c7f8), gałąź robocza `feat/rag-debugger-prereqs`.
- Nic nie idzie na VPS bez potwierdzenia Łukasza. `main` zostaje wdrażalny.

---

## FAZA 1 — Trzy zmiany produkcyjne (prerequisity, PRZED debuggerem)

### Krok 1.1 — Provenance w metadanych (luka #3) ⟵ ROBIMY PIERWSZE
**Co:** do `vector_store.add_memory()` dodać do metadanych: `origin_endpoint` (chat|amelia|wspolny|nocna), `origin_conversation_id`, `origin_persona_turn`.
**Dlaczego pierwsze:** każdy dzień zwłoki = kolejne anonimowe wektory, których potem nie odtworzymy do źródła. Zmiana **addytywna** — nie zmienia zachowania, tylko wzbogaca zapis. Zero ryzyka.
**Pliki:** `vector_store.py` (sygnatura + zapis metadanych), wywołania `add_memory` w `main.py` (przekazać origin z kontekstu endpointu), `semantic_pipeline.py` jeśli tam leci zapis.
**Bramka:** nowy wektor zapisany po zmianie ma pola `origin_*` w Chroma (sprawdzić na VPS przez `collection.get`).

### Krok 1.2 — `compose_context()` + `trace` (luka #1) ⟵ SERCE REFACTORU
**Co:** wyodrębnić z `/api/chat` funkcję:
`compose_context(persona_cfg, query, conversation_id, now_override=None, trace=None) -> ContextBundle`
Obejmuje CAŁĄ orkiestrację promptu: FactStore [TWARDE FAKTY] → 3 kanały RAG → milestone 1b → Temporal Filter → RAW window (**merge solo + shared**, o którym projekt zapominał) → historia sesji → `fit_to_budget` → grounding.
`/api/chat`, `/api/amelia`, `/api/wspolny` wołają `compose_context` i tylko generują. `trace` (obiekt `RagTrace`) zbiera snapshoty po każdym etapie (pool→temporal→milestone→rerank→MMR→merge→fit).
**Dlaczego:** to jedyny sposób, żeby debugger renderował DOKŁADNIE to co produkcja — bo to ten sam kod, nie kopia.
**Pliki:** `main.py` (ekstrakcja z `/api/chat`, potem podmiana w amelia/wspolny), `vector_store.py` (`trace` param w `search_memories`).
**Bramka KRYTYCZNA:** przed/po refactorze — **ta sama wiadomość → bit-identyczny blok [WSPOMNIENIA]**. Refactor bez zmiany funkcjonalnej. Jak się różni choć znakiem — nie idziemy dalej.

### Krok 1.3 — Pełny `now_override` (luka #2)
**Co:** przepchnąć `now_override` przez WSZYSTKIE `utcnow()` na ścieżce compose (nie 3, a ~6): `search_memories`, recency w `rerank`, temporal boost `+0.15` w `rerank`, `_passes_temporal`, `get_recent_user_messages` (RAW cutoff 48h), `build_system_prompt` (prefiksy „[X dni temu]" + blok [AKTUALNY CZAS]), rerank w kanale 1b.
**Default `None` = produkcja bez zmian.**
**Bramka:** `now_override = dziś+30dni` → RAW window pusty, prefiksy czasu spójne z symulowaną datą, zero „Frankensteina dwóch osi czasu".

---

## FAZA 2 — Debugger jako cienki renderer

- Route **`/debug/inspect/*`** (read-only) — ODDZIELONY od `/admin/trigger/*` (obecne `/api/debug/nocna-analiza`, `morning-message` PISZĄ — wyprowadzić z „debug").
- Woła `compose_context(dry_run=True, trace=RagTrace())` → renderuje trace: **Warstwy 0–6 + 6a (token budget pre/post fit) + 6b (grounding_status) + coherence flag (mean pairwise cosine selekcji) + inspektor keyword boost per słowo.**
- **`PersonaConfig` od dnia 0** (mapa persona → {singletony, composer}) zamiast `if persona=='astra'` — żeby pokój 3 sióstr nie wymagał przepisania.
- Bezpieczeństwo (luka #11): **Basic Auth jako FastAPI dependency** (nie tylko nginx), `asyncio.to_thread` dla dry-run (nie zamrażać żywej rozmowy), `PRAGMA journal_mode=WAL` na SQLite.
- **Bramka naczelna:** ta sama fraza → debugger `[WSPOMNIENIA]` == produkcja `[WSPOMNIENIA]`. Jak się zgadza — narzędziu można ufać.

---

## FAZA 3 — później (zaprojektowane, nie budowane teraz)
- Golden set ~25 fraz + regresja `.jsonl` (porównanie przed/po dla zmian wag).
- Tryb Wspólny Pokój: Warstwa R (routing trace `_route_wspolny`), tryb dwuprzebiegowy (2 calle Gemini), **odczyt flag bez konsumpcji** (`get_flag` w dry-run nie może `clear_flag`), `_last_wspolny_first` bez mutacji.
- Debug ścieżki ZAPISU: extraction dry-run, reverse lookup wektora, diff Chroma↔FactStore.
- Zapisywać `active_conversation_id` per pokój (luka #7) + selektor conv_id w UI.

---

## Poprawki RAG wyłapane przy okazji (osobny tor — PO debuggerze, bo wtedy mierzalne)
Te tłumaczą bug „altanki" (Skankran+siostry+scenariusz stopione w jedno):
- **MMR jako mieszalnik:** `diversity_penalty=0.8` przy top-3 aktywnie preferuje po jednym wektorze z każdego odległego klastra → maksymalizuje cross-project contamination przy wieloznacznym query.
- **Keyword boost ślepy na polską fleksję:** substring match — „altance" (miejscownik) ≠ „altanka" → jedyny dyskryminator daje 0 boostu. Fix: stemmer PL lub match po prefiksie 5 znaków.
- **`SESSION_WINDOW_N`** jako wspólna stała + decyzja n=10 vs więcej.
→ Te idą przez debugger (coherence flag je unaoczni), walidowane golden setem. To jest Tier 2 (`fable_2_audyt-rag_NA-POZNIEJ.md`).
