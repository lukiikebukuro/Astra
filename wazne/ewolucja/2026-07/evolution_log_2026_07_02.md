# ASTRA — Evolution Log: 2026-07-02 (RAG Debugger — audyt Fable + start Fazy 1)

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

## LEKCJE / REGUŁY (TL;DR pod AI)
- **Tożsamość wymuszaj STRUKTURĄ, nie dyscypliną** (Fable + nasza meta-lekcja „struktura > dyscyplina"). Composer współdzielony = debugger renderuje ten sam kod, nie kopię.
- **Refactor weryfikuj bit-identycznie na ŻYWYM środowisku**, nie `py_compile`. Wzorzec: worktree + symlink baz read-only + diff promptu. `py_compile` łapie gramatykę, nie zgodność wyniku.
- **Żywy kod > pamięć/dokumenty**: `n=10` (nie 30), state Level 5 XP=1726 (memory mówiła Level 6 XP 3434). Dokumenty dryfują — weryfikuj.
- **MMR jako mieszalnik**: `diversity_penalty` za wysoki maksymalizuje cross-project contamination przy anaforycznym/ubogim query. Do toru poprawek RAG (Tier 2).

## STAN NA KONIEC SESJI
Gałąź `feat/rag-debugger-prereqs`: Krok 1.1 ✓, Krok 1.2a ✓ (zweryfikowany). `main` czysty, VPS nietknięty. Następne: 1.2b (trace), 1.3 (now_override) → weryfikacja → podpięcie Amelii/Wspólnego → Faza 2 (front debuggera).
