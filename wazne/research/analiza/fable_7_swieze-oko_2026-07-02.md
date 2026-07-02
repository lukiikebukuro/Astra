# FABLE 7 — Świeże oko na repo (read-only, 2026-07-02)

Audyt „pierwszy dzień w projekcie" — ulepszenia, których zespół mógł nie zauważyć. Zero zmian w kodzie.

## TOP 5 — warte zrobienia od razu

1. **`DELETE /api/state` kasuje stan relacji bez auth** — `main.py:1921-1925`. Endpoint destrukcyjny („dev/debug only"), a przy CORS `*` i braku zamka aplikacyjnego jedno żądanie wymazuje Level/XP/concerns. Fix: `Depends(check_debug_auth)` + ewentualnie `?confirm=`. Koszt S, ryzyko niskie.
2. **Znikające powtórzone wiadomości w historii sesji** — `vector_store.py:186-188`: ID = `hash(salt:conv:role:content)` → identyczna treść w tej samej rozmowie („ok", „tak") nadpisuje poprzednią (upsert), timestamp starej przepisywany. Deterministyczne ID to celowy dedup dla PAMIĘCI — dla HISTORII sesji niezauważony side-effect. Fix: dodać `_seq`/epoch do materiału hasha. Koszt S, ryzyko niskie.
3. **Nieograniczony wzrost promptu (~86k znaków/turę)** — `fact_store.py:156` `get_facts_for_prompt` bez LIMIT (typy akumulujące rosną wiecznie); `main.py:503` `fit_to_budget` budżetuje TYLKO wspomnienia i rezerwuje tylko `len(template)` — nie widzi hard_facts/RAW/state/lukasz_core/monologue. Koszt+latencja rosną, uwaga modelu się rozmywa. Fix: LIMIT+priorytet w SQL + jeden globalny budżet promptu. Koszt M, ryzyko średnie (zmienia prompt → PRZED zamrożeniem golden setu albo świadomie razem).
4. **RAW window i historia czytają CAŁĄ kolekcję co turę** — `vector_store.py:590-598` (`.get()` wszystkich wiadomości usera ever, filtr 48h dopiero w Pythonie) i `:214`. O(N)/turę, ×2 store'y. Fix: numeryczne `ts_epoch` w metadanych + `$gte` w `where`; stare fallbackiem. Koszt M, ryzyko niskie.
5. **Niespójna ochrona endpointów z danymi osobistymi + CORS** — zamek `check_debug_auth` dostały TYLKO `/amnezja` i `/api/debug/inspect`; a `/api/debug/facts` zrzuca twarde fakty ZDROWOTNE, `/api/debug/rag`, `/api/debug/stats`, `/api/state`, `/debug` (stary debugger!) — bez zamka. `main.py:437-443`: `allow_origins=["*"]` + `allow_credentials=True` (sprzeczne ze spec CORS, szerokie bez potrzeby — origin znany: myastra.pl). Fix: `Depends` na WSZYSTKIE `/api/debug/*`, jawna lista origins. Koszt S, ryzyko niskie (uwaga: `/api/history*` używa frontend — objąć tym samym nginx auth co front).

## BACKLOG (wg wartości)

6. `to_prompt_block()` używa surowego `utcnow()` — `companion_state.py:101`: przy symulacji daty w Amnezji „Ostatnia rozmowa: X godzin temu" liczy z czasu REALNEGO (luka now_override poza zasięgiem Fable 6, który grepował tylko main/vector_store). Koszt S.
7. Zero retry na Gemini — chat: jeden timeout = 502; nocna/poranna: błąd = utracona doba. Fix: 1 retry z backoff. Koszt S.
8. API kłamie o stanie — `main.py:1187-1190`: `ChatResponse` hardcoduje `state_level=6`, „Absolutna Więź", gdy realnie Level 5. Zwracać `state.level` albo usunąć pola. Koszt S.
9. `load_prompt_template()`/`load_lukasz_core()` czytają dysk co turę — `main.py:459-492`; cache z mtime. Koszt S.
10. Wildcard delete insightów — `nocna_analiza.py:164`: `delete(where={"source":"night_insight"})` bez persona_id — po dojściu person skasuje cudze. Koszt S.
11. `VectorStore._seq` klasowy, resetowany restartem — `vector_store.py:174` + podwójny sufiks timestampu; ujednolicić przy #2. Koszt S.
12. Dwa modele embeddingów w RAM? — Chroma EF + osobny SentenceTransformer w `semantic_extractor.py:17`. Zweryfikować mem na VPS; jeśli 2 kopie — współdzielić (~0.5 GB). Koszt M.
13. Proteza `+=1/-=1` na liczniku — `main.py:1006/1170`: obejście; docelowo compose dostaje wartość bez mutacji stanu. Koszt S.
14. `push_subscriptions.json` z 3 ścieżek bez locka — teoretyczny race, single-user, niski priorytet.
15. Eksperyment kosztowy (nie zmiana): `thinking_budget=4096` co turę — sprawdzić przez golden konwersacje, czy 1024/dynamicznie nie trzyma jakości person przy niższej latencji. Najpierw pomiar.

## Do WYWALENIA
- `backend/prompts/vector_store.py` (17 KB) — stary kod w folderze promptów; nic go nie importuje.
- `backend/debug.html` + route `/debug` (`main.py:1884`) — stary debugger zastąpiony Amnezją, wystawiony BEZ auth.
- `format_gemini_history()` + użycie — `main.py:842,1022`: wynik nieużywany (dead od starego SDK).
- One-off skrypty w `backend/` → `backend/scripts/`: cleanup_toxic, cleanup_vectors, migrate_sessions..., reingest_sessions, db_inspector, load_character_vectors, load_project_knowledge, saas_readiness_test, semantic_density_audit. Żeby nikt nie odpalił migracji na prodzie.
- Pola-atrapy w `ChatResponse` (state_xp=0) — patrz #8.

## Czego NIE ruszać
- Wspólny Pokój (`_route_wspolny`, `_wspolny_generate`) — gęsto od blizn (merge model-turns, thought isolation, do_not_repeat, anti-sync, subtext). Każda dziwność ma powód.
- `EXCLUDED_SOURCES`, echo-loop filter (<80 znaków PERSON), `strip_memory_echo` — blizny po echo-loopach.
- Deterministyczne ID w `add_memory` — celowy dedup PAMIĘCI (NIE mylić z #2 = sesja).
- Supersede / `delete_by_entity_subtype` — przemyślana higiena.
- Wagi rerank/MMR/keyword — tor strojenia przez Amnezję.
- `astra_base.txt`/`amelia_persona.txt` — osobowość, nie kod (choć #3 może wymusić rozmowę o rozmiarze).

## Metryka kosztów (kontekst #3/#15)
Każda tura: ~86k znaków ≈ ~21k tokenów wejścia + historia 10 + thinking 4096 + JSON out. Na gemini-2.5-flash to grosze/turę, ale: latencja thinking co turę + prompt ROŚNIE bez limitu + Wspólny ×2 calle. Kierunek: globalny budżet promptu (#3) da przewidywalność, zanim koszt/latencja staną się odczuwalne.

*Audyt: Fable (terminal, read-only). Jedyny zapis: ten plik.*
