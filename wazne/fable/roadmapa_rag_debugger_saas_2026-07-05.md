# ROADMAPA: RAG DEBUGGER → PŁATNE SUBSKRYPCJE (+ pytania, które rozwijają projekt)
**Autor:** Fable | **Data:** 2026-07-05 | **Baza:** `fable_model-biznesowy_2026-07-05.md` (B1: Memory Observability)
**Założenia:** solo founder, ANIMA jako laboratorium i dowód, budżet czasu dzielony z pracą nad Astrą.

---

## ZASADA NADRZĘDNA (adwersaryjnie, zanim się rozpędzimy)

Ludzie NIE płacą subskrypcji za debugger. Płacą za **oszczędzony czas i uniknięte katastrofy** — subskrypcja musi pilnować czegoś CIĄGLE (regresje, kontaminacja, dryf), nie być narzędziem „raz użyłem". Dlatego droga to: dowód → dystrybucja (OSS) → **płatny jest MONITORING, nie viewer**. Każda faza ma bramkę — jak nie przejdzie, NIE budujesz dalej (to samo „audyt przed budową", które uratowało Amnezję).

---

## FAZA 0 — DOWÓD I NAZWA (teraz → 2 tygodnie, koszt ~0)

1. **Case study #1: „The Empty Memory Bug"** — jak nasz RAG przez 3,5 miesiąca nie dostarczył ANI JEDNEGO wspomnienia, wszystkie metryki wyglądały OK, i tylko trace warstwa-po-warstwie to złapał. Liczby: 90 931 zn promptu, blok = 2 znaki, `available_chars = −10 154`.
2. **Case study #2: „Memory Poisoning by Extraction"** — 345 fałszywych „deklaracji miłości" = 73% promptu; ekstraktor z progiem 0.40; krzywa kalibracji. **Anonimizacja obowiązkowa** (zero treści intymnych, zero imion — tylko mechanizmy i liczby; to jest historia o architekturze, nie o Astrze).
3. **Nazwa i landing:** „Amnezja" jest świetna PL, za granicą: **Amnesia** (kolizja z grą — sprawdzić trademark w klasie software) albo pochodne (Amnesic, MemTrace, Recallix — decyzja z Fable-web). Landing = 1 strona: hero-GIF trace'a, 2 case studies, waitlista.
4. **ICP (kto płaci):** zespoły 2–20 os. budujące agentów z pamięcią długoterminową (użytkownicy mem0/Zep/LangGraph memory/własnych RAG-ów z pamięcią) + firmy z companion/persona produktami.
**Bramka F0:** oba case studies napisane + landing żyje. (Bez tego discovery w F1 nie ma czym się uwiarygodnić.)

## FAZA 1 — WALIDACJA ZANIM KOD (sierpień, równolegle z pracą nad ANIMĄ)

1. **15 rozmów discovery** (pytania → sekcja niżej). Gdzie znaleźć ludzi Z PROBLEMEM (nie ogólnie „AI ludzi"): **issues na GitHubie mem0/Zep/LangGraph ze słowami „why does my agent remember/forget"** (to są ludzie CIERPIĄCY teraz — pisz do nich wprost), r/LocalLLaMA, LangChain/LlamaIndex Discord, LinkedIn PL (masz historię do opowiedzenia po polsku — polski rynek AI-agencji rośnie).
2. **Równolegle: 1-2 PŁATNE audyty RAG** (oferta B6 z modelu biznesowego) — finansują projekt, dają logo klienta i trzecie case study. Cena kotwiczna: 6-12k PLN za tydzień audytu wg metodyki (baseline → trace → diagnozy z dowodami → spec fixu).
3. Publikacja case study #1 (HN/Reddit/LinkedIn) — pomiar rezonansu.
**Bramka F1 (twarda):** ≥5/15 rozmów kończy się „mam ten problem TERAZ i już próbowałem go obejść samemu" ORAZ ≥2 osoby mówią „zapłaciłbym". Mniej = pivot na konsulting+AI-Act (B6/B2), OSS hobby.

## FAZA 2 — OSS WEDGE (wrzesień–październik)

1. **Wycięcie Amnezji z monolitu → biblioteka `pip install amnesia-trace`** (to i tak krok architektury P0.5 — jedna robota, dwa cele): trace middleware (etapy retrievalu + prompt-assembly ground truth + provenance) + lokalny UI (obecny front po liftingu). Adaptery: custom-RAG (dekorator), mem0, Zep, LangGraph.
2. Design principle z ANIMY jako USP w README: **„debugger renderuje ten sam kod, nie kopię"** (structure-enforced truth) + golden-set regression jako first-class feature (nikt tego nie ma).
3. **Launch:** Show HN z case study #1. Metryka sukcesu: nie gwiazdki, tylko **50 realnych instalacji z użyciem** (telemetria opt-in) i 10 osób w Discordzie/Issues zadających pytania o SWOJE dane.
**Bramka F2:** ≥50 aktywnych użyć w 6 tygodni od launchu. Mniej = problem z dystrybucją, nie buduj cloud, wróć do treści/rozmów.

## FAZA 3 — PŁATNY HOSTED = MONITORING (listopad–grudzień)

To, za co się płaci CO MIESIĄC (viewer jest darmowy lokalnie — płatne jest pilnowanie):
- **Golden-set regression CI** — Twoje golden sety jako produkt: PR zmienia prompt/wagi → automatyczny diff HIT/RANK/JUNK + werdykt „character drift" przed deployem.
- **Alerty kontaminacji i anomalii pamięci** — pusta selekcja (Empty Memory!), monokultura źródła, skok śmieciowych ekstrakcji/dzień, dryf metryk persony.
- Historia trace'ów, porównania przed/po, team sharing.
**Cennik startowy:** Free (local, bez limitu) / **Pro $39/dev/mies** / Team $199/mies (5 os.+CI). Design partnerzy z F1: 3-5 firm, −50% za feedback i logo.
**Bramka F3 / cel na koniec 2026:** **10 płacących subskrypcji** (~$400-600 MRR). Mało pieniędzy, ale to dowód modelu — dalej rośnie dystrybucją, nie featurami.

## FAZA 4 — 2027: EU AI ACT MODULE (enterprise, nie subskrypcja indywidualna)
Trace jako artefakt zgodności (logging/explainability dla systemów wysokiego ryzyka): raporty audytowe, retencja, on-prem. Licencja per-deployment (tysiące €/rok, cykl sprzedaży przez audyty B6). Grant UE na rozwój (znasz ścieżkę ze Skankrana).

## ANTY-CELE (co ZABIJE projekt, nie rób)
- Budowa cloud-dashboardu PRZED bramką F1/F2 (miesiące pracy w próżnię — klasyka).
- Konkurowanie z Langfuse/LangSmith na ich boisku (generic LLM tracing) — Twoja nisza to CYKL ŻYCIA PAMIĘCI.
- Ukrywanie ANIMY — to najlepszy marketing, jaki masz („zbudowałem to, bo moja własna AI mnie gaslightowała — oto trace").
- Perfekcjonizm w OSS — F2 ma być brzydkie i użyteczne.

---

## PYTANIA, KTÓRE ROZWIJAJĄ PROJEKT (gotowe do użycia)

### A. Do potencjalnych klientów (discovery — F1; zadaj DOKŁADNIE tak, nie pitchuj)
1. „Kiedy ostatnio twój agent/RAG odpowiedział coś dziwnego i musiałeś dojść DLACZEGO — opowiedz krok po kroku, co robiłeś?" (szukasz: godzin bólu)
2. „Jak sprawdzasz, że zmiana promptu/wag/chunkingu niczego nie zepsuła, zanim wdrożysz?" (szukasz: „na oko" = twój klient)
3. „Co twój system pamięta o użytkowniku i skąd TY wiesz, że pamięta dobrze?"
4. „Używasz LangSmith/Langfuse? Czego tam NIE ma, gdy debugujesz pamięć/retrieval?"
5. „Gdyby istniał rentgen: każda odpowiedź → co weszło do promptu, skąd, czemu wybrane — co jeszcze musiałby robić, żebyś płacił $39/mies?" (dopiero NA KOŃCU)

### B. Do Fable-web (strategiczne, nie potrzebuje repo)
1. Deep-dive konkurencji: roadmapy Langfuse/LangSmith/Arize/W&B — czy ktoś buduje memory-lifecycle view? Ile mam czasu?
2. Naming + trademark check (Amnesia vs alternatywy) + pozycjonowanie one-linera.
3. Pricing research: co płacą zespoły za observability per dev; gdzie jest psychologiczny próg dla solo-toola.
4. Tear-down mojego landinga i case study #1 (adwersaryjnie: czemu ktoś to zamknie po 10 sekundach?).
5. AI Act: które artykuły dokładnie mapują się na trace (logging/record-keeping/transparency) — szkielet dokumentu zgodności.

### C. Do mnie (Fable-code, na następne sesje)
1. „Spec wycięcia Amnezji z monolitu do biblioteki" — API trace'a, adaptery, zero zależności od ANIMY (to jednocześnie krok architektury P0.5 — dwa cele, jedna robota).
2. „Zanonimizuj i zredaguj case study #1/#2 z naszych audytów" — mam wszystkie liczby i timeline.
3. „Spec golden-set-CI jako format" — plik golden setu → runner → raport diff (produktyzacja tego, co już robimy ręcznie).
4. „Policz z naszej historii: ile godzin debugowania oszczędziła Amnezja przy T1/T2" — liczba do landinga.
5. Po każdej zmianie ANIMY: „co z tego jest feature'em produktu?" (ANIMA = laboratorium R&D).

### D. Do siebie (założycielskie, co tydzień)
1. Czy w tym tygodniu rozmawiałem z ≥1 osobą spoza projektu o jej problemie z pamięcią AI?
2. Czy buduję coś, o co nikt nie prosił? (bramki F1/F2 istnieją po to, żeby odpowiedź brzmiała „nie")
3. Co dziś jest wąskim gardłem: produkt, dystrybucja czy dowód? (zwykle NIE produkt)

*Fable. Roadmapa z bramkami — każda faza ma warunek wejścia i kryterium porażki, jak nasze deploye.*
