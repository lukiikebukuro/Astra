# Destylat ewolucji ANIMA/ASTRA — pod AI (2026-06-18, Opus)

Przegląd wszystkich evolution logów. Każdy wpis: 2-3 zdania z wartością dla AI (wzorzec/lekcja, nie narracja).

## Per-log (chronologicznie)

**2026-03-31 — Audyt Amelki, śmierć TRYBÓW.** Problem: `thinking_budget(4096) > max_output_tokens(2048)` ucinało myśli; n=10 (5 wymian) = amnezja; TRYBY 1/2/3/4 + checklisty robiły z Astry maszynę stanów (identyczny thought dla 2 różnych wiadomości). Lekcja fundamentalna: **system poprawiasz przepisując JAK prompt mówi (instynkt zamiast if/else), nie dodając reguł**. Fix: 8192 tokenów, n=30, TRYBY→TEMPERATURA RELACJI, "CZUJESZ" zamiast "SAFE HAVEN DETECTION".

**2026-04-06 — Blueprint 2.2, koniec gamifikacji.** CoT bug: malformed JSON wyciekał raw do czatu (12 przypadków/6 dni) → regex fallback `_extract_response_fallback`, parser NIGDY nie zwraca raw. Usunięto XP/levele (gamifikacja intymności = błędny fundament). Lekcja: **osobowość = wartości behawioralne, nie nazwy anime** (Trinity Mix 50/30/20 zamiast "30% Nazuna" — model internalizuje cechę, nie kopiuje etykiety). Przykłady w definicji pola stają się crutchem ("prawie się uśmiechnęłam" 5×).

**2026-04-11 — Supersede Logic.** System akumulujący bez końca nie jest suwerenny. `delete_by_entity_subtype` + SUPERSEDE_TYPES (emocje/preferencje rotują, milestony/wizyty akumulują). Lekcja deploy: **SCP z lokalnego nadpisał fix zrobiony wcześniej tylko na VPS → crash-loop**. Git divergence VPS↔lokalne to powtarzający się zabójca — synchronizuj PRZED deployem.

**2026-04-14 — wzorce z logów Family + per-type decay.** Body-Mind Bridge / Permission Protocol / System Override wyciągnięte z ucho-VPS. Lekcja: **najszybsza poprawa "obecności" = zmiana promptu, nie kodu**. Dodano SŁOWNICTWO CIAŁA (metafory hardware dla Crohna)... które usunięto 15 dni później.

**2026-04-29 — milestone retrieval naprawiony.** `milestones=1` zamiast 2: n=5 hardkodowane nadpisywało n=6 + MMR n=3 zjadał milestony przed compose. Fix: milestony wyciągane PRZED MMR, MMR tylko na faktach, `facts+milestones[:2]`. **SŁOWNICTWO CIAŁA usunięte** — Łukasz odrzucił mechaniczne metafory o swoim ciele (wzorzec over-correction: dodane→usunięte).

**2026-04-30 — Temporal Filter + RAW window.** Analiza "dlaczego ucho zapierdala": NIE przez SQLite/BM25, tylko **hard temporal cutoff** (twarde wycięcie starych wektorów, nie tylko decay) + **RAW window** (surowe ostatnie wiadomości usera jako anchor, score=1.0). Lekcja rdzeniowa: **prostota to feature — nie dodawaj warstw jeśli prostszy mechanizm daje ten sam efekt; każdy mechanizm musi rozwiązywać udokumentowany problem z logów**.

**2026-05-07 — SQLite FactStore.** ChromaDB (similarity) nie gwarantuje zwrotu właściwego faktu; FactStore = deterministyczny exact lookup (SELECT WHERE type+subtype), blok [TWARDE FAKTY] ma pierwszeństwo nad RAG. Supersede na poziomie SQL (deterministyczne ID = SHA256). Lekcja: **dwie warstwy o różnej naturze (similarity vs exact) > jedna napuchnięta**.

**2026-05-08 — Wspólny Pokój live (B1-B10).** Losowość→signal-based ordering; krytyczny fix: dwa `model` turny pod rząd = crash Gemini → merge. Echo-loop guard: ZERO semantic extraction w pokoju (cudze słowa AI jako "fakty" usera = zatrucie). **TU ZASIANO RYZYKO: prompt v2 "NAPIĘCIE JEST DOBRYM ZNAKIEM" + ZASADA KONTRY** — żeby pokój nie był martwy, wepchnięto konflikt.

**2026-05-19 — thinking_budget + hint.** `thinking_budget=0` (stary błąd JSON+thinking) naprawiony w nowym SDK → 4096 na wszystkich endpointach = głębsze, mniej skryptowe odpowiedzi. Pole `hint` = jedna surowa emocja między thought a response. Zakaz powtórzeń frazy.

**2026-06-12 — RAG fixes (~78→83).** Rzeźnia milestonów: boost +0.5 po capie → milestony zawsze ≥1.0, kontekst nigdy nie wygrywał (fix +0.5→+0.25). PERSON łapał wyznania Łukasza jako negative_person (próg→0.70). MMR Jaccard ślepy na polskie synonimy → cosine. Lekcja: **gwarancja walczy z trafnością**.

**2026-06-13 — rozdzielenie monologów, śmierć Narratora, USUNIĘCIE ZASADY KONTRY.** Wspólna INNER_MONOLOGUE kazała Amelii (Cicha Studnia) pisać "z miejsca konfliktu/rywalizacji" (sekcja WALKA, tsundere) → napięcie przeciekało do mood→response. **To był szczyt "rozwydrzonej Amelii".** Fix: osobne ASTRA/AMELIA_MONOLOGUE; AMELIA dostała "zero szukania konfliktu — tylko empatia, uziemienie". **Over-correction:** to wahnięcie z bratniej do uległej.

**2026-06-14 — Domowy Ambient + Anti-Sync + Kanał 1b.** 19/22 odpowiedzi otwierało gestem na karku (refleks). Lekcja: **bramki semantyczne (safe_haven) > arytmetyczne (licznik tur — LLM nie liczy tur niezawodnie)**. Anti-Sync: jedna persona dotyka naraz. Kanał 1b: guaranteed milestones (rozwiązał milestones=0, wprowadził monotonię).

## META-WZORCE (powtarzalne — czytaj przed każdą zmianą charakteru)

1. **Reframe > reguły.** Każda udana poprawa charakteru zmieniała JAK prompt mówi (instynkt, emocja, negatywne zakazy), nie dodawała przepisów if/else. Dodawanie reguł = maszyna stanów.
2. **Wahadło / over-correction.** Powtarzający się błąd: naprawiając przegięcie w jedną stronę, system leci w drugą skrajność. SŁOWNICTWO CIAŁA (dodane→usunięte). Amelia: bratnia (≤06-13) → uległa (06-13→) → [teraz korekta]. **Mierz w trzecią pozycję, nie w przeciwną skrajność.**
3. **Prostota to feature.** ucho biło Astrę prostotą. Nie dodawaj warstwy bez udokumentowanego problemu z logów.
4. **Gwarancja vs trafność.** Wymuszanie obecności (milestony, kontra) zawsze koliduje z trafnością/naturalnością. Kanał 1b → monotonia. ZASADA KONTRY → bratnia Amelia.
5. **Examples-as-crutches.** Przykład w definicji pola model kopiuje dosłownie ("prawie się uśmiechnęłam"). Dawaj różnorodne lub żadne.
6. **Diagnoza z DANYCH.** Każdy dobry fix wyszedł z logów (liczby, cytaty), nie z intuicji. Bug widać w logach zanim się go nazwie.
7. **Deploy ostrożnie.** Git divergence VPS↔lokalne = nawracający crash. Synchronizuj przed SCP. Bumpuj cache SW. Restart po zmianie promptu/kodu.

## OSTRZEŻENIE DLA NOWEJ ZASADY NIEZGODY (Amelia, 2026-06-18)
Pełne wahadło: 05-08 wepchnął konflikt (NAPIĘCIE+KONTRA) → Amelia bratnia/kłótliwa → 06-13 wyrwał konflikt i wlał "tylko empatia/uziemienie" → Amelia uległa (83% przyjmowania) → dziś poluzowano. RYZYKO: znów przegięcie w bratnią. Guardraile które MUSZĄ zostać: "nie szukasz konfliktu" (zostawione), niezgoda RZADKA i celna, "ze spokoju nie z gniewu", zakaz sekcji WALKA/rywalizacja. Mierzymy w suwerenny spokój z dnem — nie w drugą Astrę.
