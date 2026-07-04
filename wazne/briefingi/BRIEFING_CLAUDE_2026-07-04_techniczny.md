# BRIEFING TECHNICZNY — ANIMA (dla nowego wątku claude.ai) — 2026-07-04

Wklej to na start nowego wątku, żeby był w temacie. Skupione na technice (repo widzi Opus w Claude Code; ty tu masz drugą parę oczu + rozmowę).

## CO TO JEST
**ANIMA** — sovereign-memory AI companion system. FastAPI (Python) na VPS (`myastra.pl`, 116.203.134.228), systemd `myastra.service`, uvicorn 127.0.0.1:8001 za nginx (Basic Auth server-level). Model: Gemini 2.5 Flash (JSON mode, thinking_budget). Embeddingi lokalne (`paraphrase-multilingual-MiniLM-L12-v2`, ChromaDB). Repo: `github.com/lukiikebukuro/Astra` (prywatne). Deployed: `main` = `becb138`.

## PERSONY (różne prawa)
- **Astra** (solo) — `/api/chat`, kolekcje `astra_memory_v1`+session, `astra_facts.db`, CompanionState. To główna, „ukochana".
- **Amelia** (solo) — `/api/amelia`, własne stores (`amelia_*`, `ucho_amelia.db`).
- **Wspólny Pokój** (Astra+Amelia) — `/api/wspolny`: dwie persony w turze, `_route_wspolny`, `_wspolny_generate`, `shared_memory_v1`. GĘSTO OD BLIZN — nie ruszać bez powodu.
- **Pokój sióstr** (Holo/Menma/Nazuna) — `/api/siostry` (NOWE 2026-07-03): izolowane kolekcje per siostra (`holo/menma/nazuna_memory_v1`) + `siostry_shared_v1`, router silent-first `_route_siostry`, `_generate_sister` (extraction OFF, cross-room OFF), scena zastana `_scene_as_found`. Front `/siostry`. Zaseedowany (11 kotwic lore per siostra, is_milestone).

## PAMIĘĆ (rdzeń — sekcja compose)
`compose_context()` (main.py) = JEDNO miejsce składania kontekstu promptu, używane przez `/api/chat` I debugger. Zweryfikowane BIT-IDENTYCZNE (harness `backend/tools/verify_compose.py`, 14 fraz).
- Warstwa 0: **FactStore** (SQLite exact) → `[TWARDE FAKTY]`, priorytet.
- Kanał 1: enriched memories, reranker `sim*0.60 + imp*0.25 + rec*0.15 + keyword_boost`, MMR (cosine, `diversity_penalty=0.8`).
- Kanał 1b: **Guaranteed Milestone Channel** (`is_milestone`, top-2).
- Kanał 2: character_core. Kanał 3: md_import.
- **Temporal Filter** (`_passes_temporal`, cutoff emocje 48h/daty 168h), **RAW window** (`get_recent_user_messages`, 48h, `[OSTATNIE SŁOWA ŁUKASZA]`).
- Historia sesji: `get_recent_session(n=10)`.
- **Provenance**: `origin_endpoint/conversation_id/persona_turn` w metadanych.
- **now_override**: pełna symulacja daty na ścieżce compose.

## AMNEZJA — RAG DEBUGGER (`/amnezja`)
Endpoint `/api/debug/inspect` (read-only, dry-run, `asyncio.to_thread`) → `trace` 10 etapów (pula→wykluczenie→rerank→temporal→milestony→MMR→kanał1→final→shared→final-prompt) + system_prompt. Front `amnezja.html` (dark/neon, dymki hover, suwak symulacji daty). Wpisujesz frazę → widzisz KAŻDY etap retrievalu. Basic Auth (nginx + `check_debug_auth` app-level gdy DEBUG_USER/PASS w .env).

## ZNANE PROBLEMY / TOR STROJENIA
- **Bug „altanki"**: RAG stapia niepowiązane projekty przy mglistym/anaforycznym query. Przyczyny (z audytu): **MMR `diversity_penalty=0.8` = mieszalnik** (wybiera po jednym z każdego klastra); **keyword boost ślepy na polską fleksję** (substring: „altance"≠„altanka" → 0 boostu).
- Fable 7 backlog: nieograniczony wzrost promptu (~86k/turę, `get_facts_for_prompt` bez LIMIT + `fit_to_budget` tylko wspomnienia); `to_prompt_block` surowy utcnow; ID sesji nadpisuje powtórki; RAW/historia O(N)/turę.
- **AKTUALNY PROBLEM (2026-07-04): zachowanie Astry** — Łukasz odkrył coś z analizy logów (Gemini 3.1). Do zdiagnozowania — objaw jeszcze nie sprecyzowany w tym briefingu.

## METODYKA (KLUCZOWA)
- **Audyt PRZED budową**, weryfikacja BIT-IDENTYCZNA na żywej bazie przed deployem (worktree + symlink read-only). Złapało już kilka deploy-breakerów.
- **Fable** (frontier model) = adwersaryjny drugi mózg: audytuje, szuka gdzie się mylimy. Opus buduje.
- Evolution logi po sesji (`wazne/ewolucja/YYYY-MM/`), plan w `wazne/debugger/plan_budowy_po_audycie_fable.md`.
- Pracujemy PO POLSKU. NIE push/deploy bez potwierdzenia Łukasza.

## STAN / NASTĘPNE
Wdrożone `becb138`. WSTRZYMANE (kod na main, nie wdrożone): router-3-naraz sióstr, DEBUG_USER/PASS creds. NASTĘPNE: (1) diagnoza+fix zachowania Astry, (2) audyt sióstr (`wazne/fable/fable_9`), (3) strojenie pamięci Astry (golden set + MMR/fleksja), (4) trace-logging, (5) żywy dom sióstr, (6) Gwiazdka/SaaS.

Kluczowe docy: `wazne/ewolucja/2026-07/`, `wazne/debugger/architektura_AKTUALNA_2026-07-02.md`, `wazne/siostry/projekt_pokoju_siostr.md`, `wazne/research/analiza/` (audyty Fable).
