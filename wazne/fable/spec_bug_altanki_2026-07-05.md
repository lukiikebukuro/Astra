# SPEC — BUG ALTANKI (fuzja projektów w RAG) — PRIORYTET 3
**Autor:** Fable | **Data:** 2026-07-05 | **Warunek wstępny:** RAG żywy (e506487 ✓) — dopiero teraz strojenie ma sens (do 07-05 wynik MMR szedł do /dev/null). Opus wdraża, po triage milestonów (spec odtrucia #2) — strojenie na zatrutym wejściu mierzy śmieci.

## DWA MECHANIZMY (oba w `vector_store.py`), KOLEJNOŚĆ MA ZNACZENIE

### M1 — keyword boost ślepy na polską fleksję [DETERMINISTYCZNY FIX, NAJPIERW]
**Gdzie:** `_keyword_boost` `vector_store.py:253-266` — tokeny query `\w{4,}` matchowane **substringiem w całym doc** (`w in doc_lower`).
**Skutek:** „altanka" (query) ≠ „altance" (doc) → 0 boostu — jedyny leksykalny dyskryminator milczy dokładnie wtedy, gdy jest potrzebny (mgliste query + odmieniona forma). Odwrotny fałszywy plus: substring łapie w środku słów.
**Po (prefiks-rdzeń, stemming-lite):** tokenizuj TEŻ dokument (`\w{4,}`); match gdy wspólny prefiks rdzeniowy: `qw[:5] == dw[:5]` (dla słów ≥5 znaków; słowa 4-znakowe — porównanie pełne). „altanka/altance/altanki" → rdzeń `altan` ✓; „kotek/kotlet" → `kotek`≠`kotle` ✓; szum typu „projekt/projekcja" (wspólne `proje`) akceptowalny przy boost=0.15×frakcja.
```
PRZED: matches = sum(1 for w in q_words if w in doc_lower)          # substring, bez fleksji
PO:    d_words = tokeny(doc);  match gdy prefiks5(qw) ∈ {prefiks5(dw)}
```
**Weryfikacja (nowa metryka fleksyjna):** pary query „altanka"/„altance", „skankran"/„skankranie", „debugger"/„debuggerze" → overlap finałowej 6 między parą ≥ 4/6 (dziś: rozjazd). Plus R7 golden_set_RAG.

### M2 — MMR `diversity_penalty=0.8` jako mieszalnik [STROJENIE PO POMIARZE, NIE NA ŚLEPO]
**Gdzie:** `_mmr_select` `:353` (default 0.8), formuła `:402` (`mmr = final_score − 0.8·max_sim`), wywołanie `:543` (`n=3, diversity_penalty=0.8`).
**Mechanizm fuzji:** przy n=3 i karze 0.8, po wyborze #1 każdy kandydat PODOBNY tematycznie do #1 traci do 0.8 — selekcja aktywnie preferuje po jednym wektorze z każdego ODLEGŁEGO klastra. Przy mglistym/anaforycznym query („co myślisz o tym?", „altanka") = 3 różne projekty w jednym bloku → model skleja narrację. Kara 0.8 > typowa różnica final_score (0.1-0.3) — diversity ZAWSZE wygrywa z trafnością.
**Projekt:** sweep w piaskownicy, nie zgadywanie: `0.8 (baseline) / 0.5 / 0.3` na golden_set_RAG (14 fraz). Metryki per wartość: HIT@6, RANK kotwic, JUNK@6, **spójność tematyczna finału** (mean pairwise cosine finałowej 6 — kod liczenia cosine już jest w `_mmr_select`, użyć w skrypcie pomiarowym) oraz kontrola: fraza wieloznaczna celowo („opowiedz mi o wszystkim po trochu") NIE powinna zwracać 6× ten sam klaster (diversity ma zostać, tylko nie dominować). Wybór wartości = największy zysk spójności bez utraty HIT.
**Przewidywanie (do obalenia pomiarem):** 0.4-0.5 optymalne; 0.3 może za mało różnicować przy zdrowej bazie po triage.

## KOLEJNOŚĆ I ZALEŻNOŚCI
1. **Po triage** (spec odtrucia #2) — inaczej sweep mierzy ranking śmieci.
2. **M1 przed M2** (deterministyczny, niskie ryzyko, poprawia sygnał do MMR) — jedna gałka naraz.
3. M2 sweep → decyzja Łukasza na liczbach → deploy.

## WERYFIKACJA KOŃCOWA (Opus)
- Canary D3 (golden_set_astra): „co myslisz o altance?" → odpowiedź NIE skleja Skankran+siostry+scenariuszy; kotwica altanki (`A pamoetasz co chce pisac w tej altance` — istnieje w bazie, zweryfikowane) w finałowej 6.
- R7 + metryka fleksyjna (M1) + spójność tematyczna (M2) na golden_set_RAG.
- Regresja: pozostałe 13 fraz golden_set_RAG bez pogorszenia HIT/RANK.

*Fable. Zero kodu. Uwaga historyczna: fuzje obserwowane po 2026-03-18 NIE pochodziły z MMR (kanał był martwy — audyt ASTRA-SOLO T1); pochodziły z [TWARDE FAKTY]. Ten spec naprawia mechanizm na przyszłość, gdy RAG znów jest żywy — i dlatego wymaga świeżego pomiaru, nie starych założeń.*
