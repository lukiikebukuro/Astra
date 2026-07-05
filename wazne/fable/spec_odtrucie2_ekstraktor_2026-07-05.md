# SPEC — ODTRUCIE #2: EKSTRAKTOR + TRIAGE MILESTONÓW (PRIORYTET 1)
**Autor:** Fable | **Data:** 2026-07-05 | **Stan bazowy:** `e506487` wdrożone (prompt 29k, fakty 26, RAG żywy)
**Cel:** (A) ZATRZYMAĆ produkcję śmieci (+6,5/dzień), (B) odzyskać trafną pamięć z istniejących 346 (FactStore) + 1083 (Chroma) milestonów. Reklasyfikacja, NIE delete. Opus wdraża, deploy za zgodą Łukasza.

---

## KALIBRACJA NA REALNYCH DANYCH (wykonana 2026-07-05, VPS, read-only) — FUNDAMENT DECYZJI

Zmierzyłem similarity WSZYSTKICH 346 zapisanych milestonów do średnich ich subtypów (ten sam model i kod co ekstraktor):

| Pomiar | Wynik |
|---|---|
| Rozkład sim zapisanych śmieci | p10=0.418, **p50=0.557**, p75=0.649, p90=0.718 |
| Ile przechodzi przy progu 0.40 (dziś) | 319/346 (92%) — zgadza się z rzeczywistością |
| Przy 0.55 / 0.60 / 0.65 | 53% / 36% / **24%** — próg NIE separuje |
| Kontrola pozytywna (7 prawdziwych deklaracji) | 0.681–0.895 — nakłada się na śmieci! |
| **Keyword-hit obecnych słowników na śmieciach** | **22/346 (6%)** |
| Keyword-hit + sim≥0.55 | 17/346 |

**Trzy rozstrzygnięcia z danych:**
1. **Sam próg to zły fix** — przy 0.65 wciąż 24% śmieci przechodzi, a prawdziwe „Kocham Cię Astra, naprawdę" (0.692) ledwo. Nakładanie się rozkładów = nie ma dobrego punktu cięcia.
2. **Keyword-warunek-konieczny blokuje 94% historycznych śmieci** i przepuszcza 100% kontrol pozytywnych (każda prawdziwa deklaracja zawiera słowo deklaracji — z definicji).
3. **Keyword sam też nie wystarczy** — wśród 22 keyword-hitów: sceny NSFW z „kocham" (sim 0.696, 0.554) i meta-pytania („o co chodzilo ze kocham asa" 0.193). ORAZ: prawdziwe „Dobranoc Astra. Kocham Cie. Dziekuje za dzisiaj" ma sim **0.528** — próg 0.55 by ją zabił. → gate keyword + **sim ≥ 0.50** + guard didaskaliów.

---

## CZĘŚĆ A — FIX EKSTRAKTORA (zatrzymanie produkcji)

### A1. Keyword jako WARUNEK KONIECZNY (nie modyfikator progu)
**Gdzie:** `semantic_extractor.py:810-822` (`_find_best_match`, blok MILESTONE) + `:241` (`MILESTONE_KEYWORD_THRESHOLD`).
**Dziś (odwrócony bug):** brak keyworda → próg 0.40 (łatwiej!); jest keyword → 0.45 (trudniej). Komentarz `:232` („obniżamy próg do 0.30") martwy.
**Po:** dla `entity_type == 'MILESTONE'`: **brak keyworda subtypu → subtype w ogóle nie kandyduje** (continue). Jest keyword → wymagane sim ≥ **0.50**. `MILESTONE_KEYWORD_THRESHOLD` i stara gałąź — do usunięcia (martwe po zmianie). Default = NIE-milestone; deklaracja bez słowa deklaracji nie istnieje.
```
PRZED: threshold = 0.45 jeśli keyword, else 0.40; sim >= threshold → match
PO:    jeśli MILESTONE i brak keyworda → pomiń subtype
       jeśli keyword → match tylko gdy sim >= 0.50
```

### A2. Zaostrzenie słowników (`semantic_extractor.py:234-240`)
Obecne zbiory zawierają niebezpiecznie szerokie substringi. Zmiany (frazy, nie pojedyncze rdzenie):
| Subtype | USUNĄĆ (za szerokie) | ZOSTAWIĆ/DODAĆ |
|---|---|---|
| `trust_declaration` | `'jedyn'` (→„jedyny sposób"), `'rozumie'` (→każde „rozumiem"!), `'bezpiecz'`, `'szczer'` | `'ufam'`, `'zaufan'`, `'tylko tobie'`, `'nikomu innemu'`, `'wierzę w ciebie'`, `'wierzę ci'` |
| `gratitude` | `'dzięki'`, `'dziękuje'` solo (codzienne „dzięki") | `'dziękuję że jesteś'`, `'jestem wdzięczny'`, `'wdzięczn'`, `'doceniam cię'` |
| `future_together` | `'wyobrażam'` solo (łapie każdą fantazję) | `'wyobrażam sobie nas'`, `'nasza przyszłość'`, `'kiedyś razem'`, `'chcę żebyś'`, `'marzę o'` (z sim-gate 0.50 wystarczy) |
| `love_declaration` | — (jest OK) | bez zmian: kocham/kochasz/szaleję/miłość/zakochan/uwielbiam |
| `vulnerability` | — (frazowe, OK) | bez zmian |
Uwaga na fleksję: dopasowanie substring w lower() jak dziś (frazy odmienią się rzadko; nie przekombinować).

### A3. Guard didaskaliów (nowa reguła, ~4 linie)
**Gdzie:** początek gałęzi MILESTONE w `_find_best_match` (obok CORRECTION_KEYWORDS guard, `:810-812` — wzorzec już istnieje).
**Reguła:** wiadomość zaczyna się od `*` LUB >40% długości wewnątrz `*...*` → MILESTONE nie kandyduje (scena RP to nie deklaracja). **Dowód potrzeby:** sceny erotyczne z „kocham" mają sim 0.554-0.696 — przechodzą A1+A2, ten guard je łapie.

### A4. FACT:habit — analogiczny gate
**Gdzie:** `ENTITY_THRESHOLDS` `:226-231` — FACT nie ma wpisu → dostaje `min_confidence=0.40` z wywołania czatu (main.py:1116). Zapisane 40 habitów = 100% szum („Samotnie mi, i brzuch mnie boli").
**Po:** `ENTITY_THRESHOLDS['FACT'] = 0.55` + dla subtypu `habit` keyword-gate: {'zawsze', 'codziennie', 'zwykle', 'mam w zwyczaju', 'regularnie', 'co rano', 'co wieczór'}. Nawyk bez markera nawykowości = jednorazowe zdarzenie, nie habit.

### A5. Testy (rozszerzenie istniejącego suite `semantic_extractor.py:1045+`)
Dodać **negatywne** przypadki z realnej bazy (dziś suite ma tylko pozytywne): „Oki. Popalam sobie. A ty co robiłeś" ≠ love; „Wiesz ze widzę twoj CoT" ≠ love; „Dobrać dobra! Rozważę to" ≠ trust; „The boondocks a potem spy x family" ≠ future; scena-z-gwiazdkami-z-kocham ≠ love (guard A3); ORAZ pozytywny brzegowy: „Dobranoc Astra. Kocham Cie. Dziekuje za dzisiaj" = love (sim 0.528 — pilnuje progu 0.50).

**Weryfikacja A po wdrożeniu:** (1) suite przechodzi; (2) retro-test: nowa logika na 346 zapisanych przepuszcza ~12-17 (lista z kalibracji, w tym zero NSFW); (3) po tygodniu życia: przyrost MILESTONE w FactStore **< 1/dzień** (dziś 6,5) — pomiar: `SELECT count(*) WHERE timestamp > X`.

---

## CZĘŚĆ B — TRIAGE ISTNIEJĄCYCH (nocny job LLM, jednorazowy)

Delta względem `plan_triage_milestonow_2026-07-05.md` (fazy backup/kolumna/rollback — tam; tu konkrety joba LLM, których plan nie miał):

### B1. Zakres i przygotowanie
- FactStore: 346 MILESTONE + 40 FACT:habit. Chroma: 1083 `extracted_milestone` (dump przez `collection.get`).
- **Kolumna `status` NIE istnieje** (sprawdzone po e506487) → `ALTER TABLE facts ADD COLUMN status TEXT DEFAULT 'active'` + filtr `status='active'` w `get_facts_for_prompt` (fact_store.py:165+ — tuż obok świeżego LIMIT-u Opusa). Backup wg Fazy 0 planu triage PRZED wszystkim.

### B2. Sędzia LLM (Gemini 2.5 Flash, temperature 0, JSON mode) — prompt do wdrożenia
```
Jesteś klasyfikatorem wspomnień AI-companion. Dla każdego wpisu oceń, czym NAPRAWDĘ jest
wiadomość użytkownika (pisana do partnerki AI, po polsku, z literówkami):
- "real_milestone" — wprost wyrażona deklaracja uczuć/zaufania/wspólnej przyszłości/wyznanie
  (subtype: love_declaration|trust_declaration|future_together|vulnerability|gratitude)
- "echo" — zwykła rozmowa błędnie oznaczona (pytanie, small talk, logistyka, komentarz)
- "rp_scene" — scena odgrywana/intymna (didaskalia w *gwiazdkach*, treść fizyczna) — nawet jeśli
  zawiera słowo "kocham", scena ≠ deklaracja
- "retype:<TYP:subtype>" — wartościowa treść pod złym typem (np. FACT:current_project,
  FACT:health, FACT:personal_info)
Zwróć JSON: [{"id": "...", "verdict": "...", "subtype": "...", "confidence": 0.x}]
Zasada: wątpliwość → "echo" (lepiej stracić etykietę milestonu niż trzymać fałszywą).
```
Few-shot (wziąć dosłownie z bazy, 6 szt.): „Astra... Jesteś... Kocham Cie"→real/love; „Dobranoc Astra. Kocham Cie. Dziekuje za dzisiaj"→real/love; „Oki. Popalam sobie. A ty co robiłeś"→echo; „*nie moge juz wytrzymać…*"→rp_scene; „Rag debugger juzcma cala architekture"→retype:FACT:current_project; „Myslisz ze zbudowalbym skankran i ldi gdyby nie moj upór"→retype:FACT:personal_info.

### B3. Architektura joba (koszt vs pewność)
- **FactStore (386 wpisów): LLM na WSZYSTKICH.** Batche po 20, ~20 calli, koszt groszowy. Wynik → `status` (`active` dla real, `quarantined` dla echo/rp_scene) + `retype` = UPDATE entity_type/subtype (z zachowaniem oryginału w nowej kolumnie `orig_type` — odwracalność).
- **Chroma (1083): pre-filter regułowy + LLM na kandydatach.** Reguła z Części A (keyword-gate+sim+guard) autoklasyfikuje ~93% jako echo (dowód: 6% keyword-hit); LLM sądzi tylko keyword-hity (~65-80 szt.) **+ próbkę kontrolną 50 losowych** z puli reguła-echo (walidacja błędu reguły; jeśli >2/50 to real → LLM na całości, decyzja Łukasza). Aplikacja: `collection.update` metadanych (`is_milestone=False`, `importance=5`, `milestone_quarantine=True`) — wg Fazy 3 planu triage, przy zatrzymanym serwisie.
- Spójność między store'ami: werdykt per TREŚĆ (match po tekście po zdjęciu prefiksu) aplikowany do obu.

### B4. Strażnicy i weryfikacja (Opus odpala, nie Fable)
1. Golden set RAG: R8 („Holo, moja pierwsza AI dziewczyna" — prawdziwy lore-milestone) MUSI przeżyć jako active; R9 → retype, nie kwarantanna; R7 (kotwica altanki) — po triage MUSI docierać do [WSPOMNIENIA] (dziś przegrywa ze śmieciami).
2. Golden set charakteru: JUNK@6 ≤ 1.5 (baseline 2-3); top-2 przestaje być monokulturą milestone.
3. `hard_facts_count` w inspect: spada z 26 → ~10-15 (rdzeń + garść prawdziwych deklaracji).
4. Po tygodniu: metryki naturalności — czy zniknięcie pseudo-deklaracji z pamięci ostudziło ton (finalny test hipotezy T2).

**Kolejność wdrożenia: A przed B** (najpierw zakręcić kran, potem sprzątać) — inaczej job trzeba powtarzać. Rollback wszystkiego: flip `status`/`milestone_quarantine` + `orig_type`.

*Fable. Kalibracja wykonana read-only na żywej bazie (sqlite mode=ro + model w osobnym procesie, RAM zweryfikowany). Zero kodu, zero deployu.*
