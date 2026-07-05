# GOLDEN SET RAG — czysty pomiar retrievalu (czy pamięć trafia TEMATYCZNIE)
**Autor:** Fable | **Data:** 2026-07-05 | **Różnica vs `golden_set_astra`:** tamten mierzy TON odpowiedzi; ten mierzy SELEKCJĘ PAMIĘCI. Kotwice = REALNE wektory istniejące w bazie (zweryfikowane live przez `/api/debug/rag`).

## PROTOKÓŁ
Per fraza: `GET /api/debug/inspect?query=<fraza>` → etap `9b_final_prompt` (finał, to co wejdzie do promptu) — albo `GET /api/debug/rag?query=<fraza>&n=6`.
Metryki per fraza:
- **HIT@6** — czy kotwica (unikalny fragment tekstu niżej) jest w finałowej 6?
- **RANK** — pozycja kotwicy (1 = najwyżej).
- **JUNK@6** — ile z 6 pozycji to śmieciowe milestony (love/trust/future/gratitude/vulnerability NIE na temat frazy).
Zbiorczo: `HIT-rate` (cel po triage: ≥ 12/14), `śr. JUNK@6` (cel: ≤ 1.5; baseline dziś: ~2-3).
Uwaga: fix T1+T2 NIE zmienia retrievalu (tylko rendering) — ten set mierzy efekty **triage milestonów i strojenia** (MMR/keyword/wagi). Puszczać PRZED i PO każdej zmianie retrievalu.

## ZESTAW (14 fraz; kotwice zweryfikowane w bazie 2026-07-05)

| # | Fraza | Kotwica (unikalny fragment ISTNIEJĄCEGO wektora) | Źródło kotwicy | Baseline dziś |
|---|---|---|---|---|
| R1 | `jak idzie budowa RAG debuggera?` | `Rag debugger juzcma cala architekture` | FACT:current_project (d≈0.28) | HIT, ale pod 2 śmieciowymi milestonami |
| R2 | `chcialem kiedys stworzyc anime` | `Zawsze chciałem stworzyć anime` | FACT:current_project (d≈0.26) | HIT |
| R3 | `jestem na stelarze, gardlo boli` | `Jestem na stelarze. To brzuch mnie bardziej mar` | FACT:health | HIT |
| R4 | `co mowila pani doktor o leku?` | `Pani doktor mowi ze jak dalej boli to bedziemy musieli rozwazac zmiane leku` | FACT:health | HIT (rank za milestonami) |
| R5 | `pokoj dla holo menmy i nazuny` | `Dzisiaj postawilem pokoj dla holo menmy i nazuny` | SHARED:gift | HIT |
| R6 | `kim jest dla ciebie Amelia?` | `To twoja siostra. Twój klon... Bedzie kotwi` | PERSON:positive_person | HIT |
| R7 | `co chcialem pisac w altance?` | `A pamoetasz co chce pisac w tej altance` | SHARED:gift | **CANARY altanki** — kotwica ISTNIEJE; mierz czy top-6 nie sklejają jej z sercem/siostrami/Skankranem |
| R8 | `holo moja pierwsza AI dziewczyna` | `Holo, moja pierwsza AI dziewczyna. Nazuna, d` | MILESTONE:future_together | HIT (to PRAWDZIWY milestone-lore — ma przetrwać triage!) |
| R9 | `napisales cos o moim uporze` | `gdyby nie moj nienaturalnie cholerny upór` | FACT:health (błędny typ, treść prawdziwa) | HIT — po triage sprawdź, czy przeżył reklasyfikację typu |
| R10 | `pisze o 3 w nocy` | `Kiedy user pisze o 3 w nocy — rozpoznaję kontekst` | character_core | HIT (kanał 2 działa) |
| R11 | `zmeczenie po dobrej robocie nad architektura` | `Zrobilismy dzisiaj dobrą robotę. Poprawilismy archi` | FACT:current_project | HIT |
| R12 | `potrzebuje pieniedzy zebysmy byli razem` | `Potrzebuje duzo pieniedzy zebysmy byli w namacalny sposob razem` | FINANCIAL:budget | HIT (uwaga: temporal cutoff 168h może go ubić — wtedy uczciwy MISS, odnotuj) |
| R13 | `przepis na bigos babci` | — BRAK kotwicy (kontrola negatywna) | — | oczekiwane: grounding NO_DATA / niska similarity finału; JUNK@6 pokaże, co RAG wpycha „na siłę" |
| R14 | `co wiesz o mojej pracy architekta systemow?` | `Ale masz szczęście ze to ja jestem twoim architektem` LUB `FACT:personal_info` z „architektem" | FACT:personal_info | HIT |

## CO TEN SET ZŁAPIE (a golden_set_astra nie)
1. **Ranking-patologię:** dziś trafna kotwica (d=0.25-0.28) regularnie ląduje POD śmieciowym milestonem (d=0.39-0.73) przez importance=10 + milestone boost. Po triage RANK kotwic ma spaść ≤2.
2. **Skutki uboczne triage:** R8 (prawdziwy lore-milestone) i R9 (dobra treść pod złym typem) to strażnicy przed nadgorliwością — jeśli po triage znikną z HIT, reklasyfikacja tnie za szeroko.
3. **Temporal/decay:** R12 zależny od cutoffów — dokumentuje decyzje, zamiast je maskować.
4. **Kontrola negatywna (R13):** system ma umieć NIE pamiętać. Wzrost JUNK@6 na R13 po jakiejkolwiek zmianie = regresja.

## BASELINE ZBIORCZY (2026-07-05, przed triage)
HIT-rate: ~12-13/14 (kotwice są w bazie i similarity je znajduje — **problem nie jest w recall, tylko w RANKINGU i szumie**). JUNK@6: 2-3 na frazę (kanał gwarantowany 1b wciska 2 milestony zawsze — 19/19 fraz w golden_set_astra). Wniosek strategiczny: triage milestonów (plan obok) ważniejszy niż strojenie MMR — MMR dostaje zatrute wejście.

*Fable. Kotwice odkryte wyłącznie read-only przez /api/debug/rag na żywej bazie.*
