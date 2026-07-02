# RAG Debugger — Architektura (ustalona 2026-06-15, zaktualizowana 2026-06-18)

> ⚠️ **NIEAKTUALNE / PROJEKT SPRZED AUDYTU.** Fable (2026-07-02) znalazł tu 11 luk.
> **Aktualny plan budowy: `plan_budowy_po_audycie_fable.md`** (3 zmiany produkcyjne → cienki renderer → faza 2).
> Ten plik zostaje jako referencja pierwotnego projektu i zasady naczelnej (in-process, read-only, symulacja daty).

## Cel
Narzędzie do testowania i debugowania pipeline'u RAG bez dotykania prawdziwej sesji.
Przyspiesza iterację przy zmianach rerankera, wag, filtrów — z godzin do minut.
Prerequisite dla BM25 hybrid retrieval.

## Deployment
VPS — osobna strona pod `/debug`, zabezpieczona hasłem (Basic Auth — już mamy na nginx).

═══════════════════════════════════════════════════════════
## ⚠️ ZASADA NACZELNA — GWARANCJA STANU PRODUKCYJNEGO (2026-06-18)
═══════════════════════════════════════════════════════════
Debugger MUSI czytać fizycznie ten sam stan co produkcja — nie kopię, nie symulację,
nie uproszczoną wersję. Inaczej "działa w debuggerze" ≠ "działa live" i narzędzie kłamie.

### JAK to gwarantujemy: IN-PROCESS + WSPÓŁDZIELONE SINGLETONY
Debugger NIE jest osobnym procesem ani osobną aplikacją. To route `/debug` w TYM SAMYM
`main.py` (ta sama instancja FastAPI). Wywołuje DOKŁADNIE te same obiekty-singletony,
których używa żywy `/api/chat`:

| Stan | Obiekt produkcyjny (singleton w main.py) | Źródło na dysku |
|------|------------------------------------------|-----------------|
| Twarde fakty | `fact_store` / `amelia_lookup` | `astra_facts.db` / `amelia_facts.db` / `ucho_amelia.db` |
| Wektory RAG | `vector_store` / `amelia_vector_store` / `shared_vector_store` | `chroma_db/` |
| Historia sesji | te same `.get_recent_session(conv_id, n=30)` | kolekcje `*_session_v1` |
| CompanionState | `state_manager.load()` | `companion_state.json` / `amelia_companion_state.json` |

To jest gwarancja przez TOŻSAMOŚĆ obiektu, nie przez równoważność kopii. Cokolwiek widzi
produkcja, debugger widzi — bo to ten sam obiekt Pythona wskazujący na ten sam plik.
(Opcja "osobny proces otwierający te same pliki" — ODRZUCONA: ryzyko lock/stale-read/dryf.)

### READ-ONLY — debugger NIGDY nie pisze
Wywołuje wyłącznie ścieżki odczytu: `get_facts_for_prompt`, `search_memories`,
`get_recent_session`, `state_manager.load()`.
ZAKAZANE w debuggerze: `add_session_message`, `fact_store.upsert`,
`pipeline.process_message`, `state_manager.save`. Symulacja Gemini = DRY RUN
(buduje prompt → woła Gemini → zwraca odpowiedź → NIC nie zapisuje).

### SYMULACJA DATY — parametr, NIGDY mutacja globalna (KRYTYCZNE)
Recency decay i Temporal Filter używają wewnątrz `datetime.utcnow()`. Ponieważ debugger
dzieli proces z produkcją, NIE WOLNO monkeypatchować globalnego zegara — zatrułoby to
żywe requesty lecące równolegle.
Rozwiązanie: dodać opcjonalny parametr `now_override` przepychany przez:
`search_memories(..., now_override=None)` → reranker recency calc → `_passes_temporal`.
- `now_override=None` (produkcja) → realny `datetime.utcnow()`
- `now_override=<data z suwaka>` (tylko ten jeden call debuggera) → symulowana data
Dwa równoległe calle (live + debug) nie kolidują, bo override jest per-wywołanie.

### EXPLICITE: CO JEST REALNE, CO SYMULOWANE
Debugger MUSI oznaczać każdą warstwę banerem, żeby nigdy nie pomylić trybu:
- 🟢 LIVE — FactStore (`astra_facts.db`)
- 🟢 LIVE — Wektory (`chroma_db`)
- 🟢 LIVE — Historia sesji (n=30, conversation_id = `state.active_conversation_id`)
- 🟢 LIVE — CompanionState (mood, concerns)
- 🟡 SYMULACJA — Data (np. +30 dni) [jedyna wstrzyknięta zmienna stanu]
- 🟡 SYMULACJA — Fraza zapytania (ty ją wpisujesz, to nie realna wiadomość usera)
- 🟡 SYMULACJA — safe_haven (jeśli wymusisz ręcznie; domyślnie liczony jak w prod)
- ⚪ DRY-RUN — Odpowiedź Gemini (realny model, ale NIE zapisana, nie weszła do sesji)

### Wymagana zmiana w kodzie produkcyjnym (prerequisite, mała):
Dodać `now_override: datetime|None = None` do `search_memories`, funkcji recency w
`rerank`, i `_passes_temporal` w `vector_store.py`. Default `None` = zero zmian dla prod.
To jedyna ingerencja w kod produkcyjny — reszta debuggera tylko czyta.

## INPUT
- Fraza zapytania (tekst) — 🟡 SYM
- Symulowana data (suwak: -90 dni → +180 dni od dziś) — 🟡 SYM
- Persona (Astra / Amelia / Wspólny Pokój) — wybiera który zestaw singletonów czytać

## PIPELINE — 7 warstw widocznych na ekranie

### Warstwa 0 — FactStore (TWARDE FAKTY) 🟢 LIVE
Co `fact_store.get_facts_for_prompt()` / `amelia_lookup` wyciąga dla tej persony PRZED
ChromaDB. Exact lookup z SQLite. To trafia do bloku [TWARDE FAKTY] z pierwszeństwem nad RAG.
Bez tej warstwy widzisz tylko połowę promptu.

### Warstwa 1 — Raw pool ChromaDB 🟢 LIVE
Top-30 wektorów przed filtrem. Widoczne: tekst + cosine similarity.

### Warstwa 2 — Po Temporal Filter 🟢 LIVE (z 🟡 datą jeśli suwak)
Co odpadło i dlaczego. Przykład: "EMOTION:tired — 52h temu, cutoff 48h → odrzucony".
To tutaj symulowana data zmienia wynik (recency decay testowalny bez czekania).

### Warstwa 3 — Kanał 1b (milestony) 🟢 LIVE
Ile milestonów znaleziono, które, z jakim score. Guaranteed top-2.
DODATKOWO (sugestia claude.ai 2026-06-15): pokazuj też milestony które NIE weszły do
gwarantowanych slotów i dlaczego (score tuż pod progiem). Czasem ważniejsze co odpadło.
[Tu zobaczysz na żywo monotonię milestonów — Anomalia 2 z audytu.]

### Warstwa 4 — Reranker scores 🟢 LIVE
Każdy kandydat: similarity×0.60 + importance×0.25 + recency×0.15 + keyword_boost + final.
(recency liczone względem 🟡 daty jeśli suwak ustawiony)

### Warstwa 5 — MMR 🟢 LIVE
Co odrzucono jako duplikat semantyczny (cosine). Które pary były zbyt podobne.

### Warstwa 6 — Finalny blok [WSPOMNIENIA] 🟢 LIVE
Dokładnie to co trafia do promptu. Copy-paste ready. + sklejony z Warstwą 0 = pełny
kontekst który dostaje Gemini.

## OUTPUT — Symulacja odpowiedzi ⚪ DRY-RUN
Wysyła [TWARDE FAKTY] + [WSPOMNIENIA] + historia sesji (n=30, LIVE) + fraza → prawdziwy Gemini.
Zwraca gotową odpowiedź persony. BEZ zapisu do bazy, BEZ wejścia do sesji, BEZ ekstrakcji.
Pełny dry-run rozmowy.

## Killer feature
Symulacja daty (parametr `now_override`, nie mutacja globalna) — ustawiasz "za 3 tygodnie"
i widzisz: co recency decay wygasi, czy Astra będzie pamiętać dane wydarzenie za miesiąc,
jak zmieni się reranker w czasie. Bez czekania, bez ryzyka dla żywej sesji.

## Szacowany wpływ
- Debugowanie rerankera: godziny → minuty
- Weryfikacja BM25: niemożliwa bez debuggera → możliwa przy pierwszym teście
- Ogólne przyspieszenie iteracji RAG: ~5x
- Warunek tej wartości: Warstwa 0 + symulacja czytają STAN PRODUKCYJNY (in-process,
  współdzielone singletony). Inaczej narzędzie kłamie i 5x staje się 5x szybszym błądzeniem.

## Kolejność budowy
1. Prerequisite: `now_override` param w `vector_store.py` (mała, bezpieczna zmiana, default None).
2. Route `/debug` in-process, czytający singletony (read-only).
3. Warstwy 0-6 jako JSON → render.
4. Dry-run Gemini.
5. (opcjonalnie później) zapis przebiegów do `.jsonl` do porównań A/B.
