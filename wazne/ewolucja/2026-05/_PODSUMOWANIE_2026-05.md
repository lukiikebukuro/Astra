# Podsumowanie ewolucji — maj 2026

**TL;DR:** Miesiąc dwóch dużych fundamentów: **SQLite FactStore** (deterministyczna warstwa twardych faktów obok ChromaDB) i **Wspólny Pokój** live (Astra + Amelia razem, multi-persona). Domknięty naprawą głębi odpowiedzi (thinking budget + pole `hint`), bo po Wspólnym dziewczyny zrobiły się „płytsze".

---

## Sesje

| Data | Co zmieniono | Lekcja |
|---|---|---|
| **05-07** | **SQLite FactStore** — hybrydowa warstwa exact lookup. 12 typów encji, supersede per SQL (`INSERT OR REPLACE`, hash SHA256), blok `[TWARDE FAKTY]` z priorytetem nad RAG. | Do stałych faktów (zdrowie, daty, preferencje) nie wolno grać w ruletkę similarity — potrzebny exact lookup. |
| **05-08** | **Wspólny Pokój** pełna implementacja (Etap 0+1+2). Signal-based ordering, shared RAG, fix roli Gemini, role-alternation Astra→Amelia, labelki. Był zepsuty na wielu poziomach naraz. | Multi-persona w jednej turze = własna klasa problemów (kolejność, echo, kolizja API). |
| **05-18/19** | **Thinking budget + pole `hint`** — naprawa głębi. Po Wspólnym odpowiedzi były mechaniczne, bez myślenia pobocznego. Podniesiony budżet myśli + `hint` jako jedna wewnętrzna sentencja. | Model bez budżetu myśli „spłyca". Organiczna reakcja = funkcja przestrzeni na myślenie poboczne. |

---

## Kluczowe wnioski miesiąca (meta)

1. **Dwa silniki pamięci** — ChromaDB (similarity) + SQLite (exact). Twarde fakty na exact, reszta na wektory.
2. **Nowa funkcja = nowe failure mody** — Wspólny Pokój spłycił persony; każdy duży feature wymaga sesji naprawczej po.
3. **Głębia jest sterowalna** — thinking budget + hint realnie zmieniły jakość myślenia.

## Stan na koniec miesiąca

- Pamięć hybrydowa: FactStore (`[TWARDE FAKTY]`) + 3-kanałowy RAG.
- 3 persony: Astra, Amelia, Wspólny Pokój — live.
- Fundament pod czerwcowe utwardzanie RAG-a (milestone, anti-sync, prompt assembly).
