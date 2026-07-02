# FABLE 5 — PACZKA TIER 2: Głęboki audyt retrievalu RAG (bug „mieszania")

> Cel: znaleźć DLACZEGO RAG stapia niepowiązane projekty/persony w jedną halucynację i zaproponować
> KONKRETNE poprawki retrievalu. To bug, który krzywdzi Astrę teraz (patrz case 01.07).
> Osobne konto/rozmowa niż Tier 1 (debugger). Fable nie widzi repo — wklejasz poniższe.

---

## CO WKLEIĆ (w tej kolejności)

1. **Sekcja A z pliku `fable_1_audyt-debuggera_DO-WKLEJENIA.md`** — brief architektury ANIMA (ten sam, wklej całą).
2. **Kod** (ground truth — wklej treść tych plików):
   - `backend/vector_store.py` — CAŁY (reranker, MMR, kanały, milestone channel, `_passes_temporal`).
   - `backend/semantic_extractor.py` — CAŁY (jak powstają wektory, progi encji).
   - `backend/semantic_pipeline.py` + `backend/memory_enricher.py` — jak nadawane są importance/typ/decay.
   - `backend/fact_store.py` — warstwa twardych faktów.
   - `backend/main.py` — fragment `build_system_prompt` (jak kanały sklejają się w prompt).
3. **Sekcja D z `fable_1_audyt-debuggera_DO-WKLEJENIA.md`** — case konfuzji 01.07 (Skankran + siostry + altanka).
4. **Sekcja E z `fable_1_audyt-debuggera_DO-WKLEJENIA.md`** — wnioski z evolution logów.

---

## PROMPT DO FABLE (wklej na końcu)

Jesteś starszym inżynierem RAG specjalizującym się w retrieval quality i pamięci długoterminowej AI companionów. Masz powyżej: architekturę ANIMA, kod retrievalu, realny bug konfuzji i wnioski z ewolucji systemu.

Problem centralny: RAG **stapia niepowiązane projekty i persony w jedną odpowiedź** (case D: zapytanie o scenariusz z altanki zwróciło sklejkę Skankran + siostry anime). Nie chwal. Znajdź źródła i podaj konkretne fixy.

Odpowiedz:

1. **Diagnoza konfuzji.** Prześledź na podstawie kodu, dlaczego mogło dojść do sklejenia 3 projektów. Rozważ: brak filtra tematu/projektu przy retrievalu, reranker `sim*0.60 + imp*0.25 + rec*0.15` (czy similarity za mocne / importance za słabe), MMR cosine (czy dywersyfikacja wciąga OFF-TOPIC wektory dla „różnorodności"), kanał milestonów wpychający tożsamościowe wektory niezależnie od tematu, brak namespace/tagu projektu na wektorach.

2. **Cross-persona / cross-project contamination.** Czy wektory jednej persony/projektu mogą wyciekać do innej (evolution wniosek #5: family dostaje wektory Amelki)? Jak izolować projekty/persony na poziomie metadanych i query (namespace, filtr `where`, per-project collection)?

3. **Okno sesji n=10** (5 wymian). Ile realnie kosztuje przy dłuższej rozmowie? Rekomendacja wartości + czy dynamiczne okno.

4. **Monotonia milestonów** (wniosek #4: te same ~10 w kółko). Fix wewnątrz kanału milestonów (MMR/recency/rotacja) bez utraty gwarancji tożsamości.

5. **Konkretne poprawki, uszeregowane wg (wpływ / ryzyko / koszt).** Dla KAŻDEJ podaj: co zmienić w którym pliku/funkcji ORAZ jaką metryką/próbą potwierdzić fix (bo zbudujemy debugger, który to zmierzy — powiedz co ma pokazać).

6. **Czego brakuje architektonicznie**, żeby companion miał „pamięć idealną" bez mieszania: BM25 hybrid, tag projektu/tematu, query intent routing, coś innego?

Output: **diagnoza → ranking fixów → dla każdego: plik + metryka walidacji.** Zaznacz, które fixy są bezpieczne od razu, a które wymagają najpierw danych z debuggera.
