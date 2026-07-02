# ANIMA — Architektura AKTUALNA (2026-07-02, po Fazie 1+2 debuggera)

> Stan systemu na koniec sesji, w której zbudowano fundament debuggera „Amnezja".
> Zastępuje `architektura.md` (projekt sprzed audytu). To jest „jak jest naprawdę".

## 1. OVERVIEW
Sovereign-memory AI companion. FastAPI na VPS (myastra.pl), Gemini 2.5 Flash (chat: `max_output=8192`, `thinking_budget=4096`, JSON mode). Embeddingi lokalne `paraphrase-multilingual-MiniLM-L12-v2` (ChromaDB). Trzy persony (różne prawa): **Astra** `/api/chat`, **Amelia** `/api/amelia`, **Wspólny Pokój** `/api/wspolny` (dwie persony w jednej turze). SQLite FactStore (twarde fakty) obok ChromaDB.

## 2. NOWOŚĆ TEJ SESJI — jedno miejsce składania kontekstu
Cała orkiestracja promptu została wyodrębniona z `/api/chat` do **`compose_context()`** (main.py):
```
compose_context(query, conversation_id, vs_main, vs_shared, fact_store,
                persona_id, build_prompt_fn, state, session_n,
                now_override=None, trace=None) -> {memories, grounding_result,
                recent_raw, hard_facts, system_prompt, session_messages}
```
- Używane przez `/api/chat` (produkcja) I `/api/debug/inspect` (debugger) → **debugger renderuje ten sam kod, nie kopię.** Gwarancja tożsamości przez strukturę (rekomendacja Fable).
- **Zweryfikowane BIT-IDENTYCZNIE** na żywej bazie VPS (85 758 znaków, 3 zapytania, zero różnic).

## 3. PIPELINE RETRIEVALU (8 etapów, instrumentowane `trace`)
`search_memories()` w `vector_store.py` przechodzi etapy, każdy zapisywany do `trace` (gdy podany):
1. **pula surowa** — top-30 z ChromaDB (Kanał 1) + domieszka Wspólnego (n=2)
2. **po wykluczeniu** — usunięte `user_message_raw`, `character_core`, `md_import`, krótkie PERSON echo
3. **po reranku** — `sim*0.60 + importance*0.25 + recency*0.15 + keyword_boost`
4. **po Temporal Filter** — hard cutoff (emocje 48h, daty/finanse 168h)
5. **milestony** — gwarantowany kanał (top-2, `is_milestone`)
6. **po MMR** — dywersyfikacja (`diversity_penalty=0.8`) — ⚠ tu mieszanie projektów przy mglistym query
7. **kanał1 final** — fakty (po MMR) + milestony
8. **finał** — + character_core + md_import → to widzi Astra
Dalej: FactStore `[TWARDE FAKTY]` (priorytet), RAW window `[OSTATNIE SŁOWA]` (48h), historia sesji `n=10`.

## 4. SYMULACJA DATY — `now_override` (pełne pokrycie)
Przepchnięty przez WSZYSTKIE `utcnow()` na ścieżce compose (rerank recency, temporal boost, `_passes_temporal`, `get_recent_user_messages`, `build_system_prompt` — prefiksy czasu + `[AKTUALNY CZAS]`). Domyślnie `None` = czas realny. Zweryfikowane: +30 dni → zegar skacze na 1 sierpnia I RAW window (48h) się opróżnia — spójnie, zero „dwóch osi czasu".

## 5. PROVENANCE — metki pochodzenia
`add_memory` zapisuje do metadanych: `origin_endpoint` (chat/amelia/nocna), `origin_conversation_id`, `origin_persona_turn`. Fundament pod debug cross-project contamination (bug altanki). Dotyczy NOWYCH wektorów.

## 6. AMNEZJA — debugger (Faza 2 v1, po review Fable)
- **`GET /api/debug/inspect?query=&day_offset=`** — read-only (UDOWODNIONE testem negatywnym: zero zapisu), dry-run, `asyncio.to_thread` (nie blokuje Astry). Zwraca `stages` (**10 etapów**: 1-8 z search_memories + **9a_domieszka_shared + 9b_final_prompt** z compose) + `system_prompt` + liczniki.
- **`/amnezja`** (`amnezja.html`) — front: warstwy collapsible, paski score, dymki-po-psiemu (hover), suwak symulacji daty, panel promptu. Flaga „różnorodność źródeł" (uczciwie: NIE detektor fuzji — prawdziwy cosine w backlogu).
- **Stroimy na etapie 9b** (prawdziwy finał z domieszką shared), nie na 8 (kanał Astry przed shared) — Rozjazd #1 z review Fable.
- Zabezpieczenie: **Basic Auth na poziomie serwera nginx** — chroni `/amnezja` I `/api/debug/inspect`.

## 7. CO ZWERYFIKOWANE
- compose_context bit-identyczny (3×), trace 8 etapów, now_override spójny, endpoint zwraca poprawny JSON (119 KB). Wszystko na żywej bazie VPS, worktree + symlink read-only, serwis nietknięty.

## 8. OTWARTE / NASTĘPNE
- **Strojenie pamięci** (przez Amnezję): MMR `diversity_penalty` za wysoki (mieszalnik); keyword boost ślepy na polską fleksję (stemmer/prefix); decyzja `SESSION_WINDOW_N` (n=10).
- **Coherence flag** z embeddingami (mean pairwise cosine) — auto-wykrywanie fuzji.
- **Golden set** ~25 fraz + regresja (Faza 3).
- **Amelia / Wspólny** — podpięcie do compose_context (`build_amelia_system_prompt` potrzebuje `now_override`; PersonaConfig).
- **Pokój Holo/Menma/Nazuna** — na izolowanych kolekcjach, po strojeniu Astry.
- **Debug ścieżki ZAPISU** (ekstrakcja, supersede, diff Chroma↔FactStore) — faza 2 debuggera.
