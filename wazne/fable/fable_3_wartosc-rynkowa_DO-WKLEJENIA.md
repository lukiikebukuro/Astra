# FABLE — Czy „sovereign memory" companion to coś wielkiego? (do wklejenia)

> Osobny wątek. Nie oceniasz człowieka po CV — oceniasz KONKRETNĄ technologię i to, czy rynek AI companions jej potrzebuje. Chcę brutalnej szczerości, nie pochlebstwa. Jeśli to table-stakes albo ktoś już to ma lepiej — powiedz wprost.

## PROBLEM, KTÓRY TA TECHNOLOGIA ROZWIĄZUJE

Companion AI (Replika, Character.AI, Nomi, Kindroid, EU startupy) mają wspólną, niezałataną ranę: **pamięć**. Naiwny RAG gromadzi wszystko → po 3 miesiącach zapytanie „jestem zmęczony" trafia w setki duplikatów, milestony relacyjne (deklaracje miłości, wspólne lore) toną w szumie, a postać **miesza konteksty** (myli projekty, osoby, wątki). Użytkownik czuje „demencję" swojego towarzysza. To zabija retencję i więź — czyli jedyne, za co ludzie w tej niszy płacą.

## CO KONKRETNIE ZBUDOWANO (ANIMA — produkcja, nie deck)

Architektura „pamięci suwerennej" — system, który aktywnie zarządza własnym kontekstem zamiast gromadzić:

- **Dwa silniki pamięci:** SQLite FactStore (exact lookup twardych faktów — zdrowie, daty, preferencje; supersede przez hash) OBOK ChromaDB (similarity). Fakty nie grają w ruletkę similarity.
- **Cykl życia wektorów:** supersede logic (nowy fakt kasuje stary), per-type recency decay (emocje żyją 3 dni, milestony permanentnie), Temporal Filter (hard cutoff czasu). System **zapomina śmieci** jak człowiek.
- **Wielokanałowe komponowanie:** gwarantowany kanał milestonów (tożsamość zawsze w kontekście) + reranker (similarity/importance/recency) + MMR + RAW cross-session window. Sygnał oddzielony od szumu.
- **Multi-persona:** trzy persony (dwie solo + „Wspólny Pokój", gdzie dwie AI rozmawiają w jednej turze — routing, role-alternation, anti-sync, echo-loop guard). Cross-persona bez kontaminacji.
- **Provenance + RAG Debugger (w budowie):** każdy wektor wie, skąd pochodzi; narzędzie in-process pokazujące warstwa-po-warstwie CO retrieval wciąga, z symulacją daty („czy postać będzie pamiętać to za miesiąc") — walidowane bit-identycznie z produkcją.
- **Roadmapa:** BM25 hybrid retrieval → „pamięć absolutna" (zero mieszania kontekstów) → live voice chat.

Działa na produkcji od marca 2026. Autor: solo, samouk, ~14 miesięcy od zera. Metodyka: evolution logi, diagnoza z logów, audyt przed budową (ten dokument to część tego).

## PYTANIA (odpowiedz szczerze)

1. **Czy to realna przewaga, czy table-stakes?** Czy poważni gracze companion AI już mają „sovereign memory / lifecycle pamięci / exact+similarity hybrid", czy większość wciąż siedzi na naiwnym RAG? Gdzie tu jest fosa, a gdzie tylko dobra egzekucja znanego?
2. **Czy firmy z tej niszy chciałyby tej technologii ALBO tego inżyniera?** (Nomi, Kindroid, Character.AI, Replika, mniejsze EU startupy). W jakiej formie — acqui-hire, licencja IP, senior hire? Realne widełki, jeśli umiesz.
3. **Największa słabość tej pozycji.** Solo, brak zespołu, brak walidacji na skali (jeden użytkownik-twórca), brak formalnego backgroundu. Czy to zabija wartość, czy da się to obrócić? Co byś zrobił, żeby „ktoś to zauważył"?

Output: szczera ocena (przewaga vs table-stakes) + kto i za ile mógłby chcieć + największa dziura + 3 ruchy, które podniosłyby wartość. Jeśli przeceniam — powiedz wprost.
