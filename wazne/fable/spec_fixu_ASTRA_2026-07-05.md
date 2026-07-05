# SPEC WYKONAWCZY — FIX T1+T2 ASTRY (dla Opusa)
**Autor:** Fable | **Data:** 2026-07-05 | **Baza:** `wazne/ewolucja/2026-07/audyt_ASTRA-SOLO_2026-07-05.md`
**Zasady:** Opus wdraża wg tego przepisu. Zero deployu bez zgody Łukasza. Standing rule: ŻADNEGO kasowania faktów/wektorów — cap/triage, nie DELETE. Po wdrożeniu: świeży `conversation_id` (pętla samo-imitacji) + golden set (`wazne/fable/golden_set_astra_2026-07-05.md`).

---

## ⚠️ ZASADA NADRZĘDNA: KROK 1 i KROK 2 = JEDEN DEPLOY

- Krok 2 bez Kroku 1 → otwieramy [WSPOMNIENIA] przy 67k faktów = prompt ~94k (jeszcze gorzej).
- Krok 1 bez Kroku 2 → Astra dalej bez pamięci epizodycznej.
- **Dowód z baseline'u golden setu (19 fraz, 2026-07-05):** po odblokowaniu kanału wspomnień top-2 pozycje dla KAŻDEJ frazy (nawet „zjadlem lody haha", „ale dzisiaj goraco") to śmieciowe milestony z kanału gwarantowanego 1b („Wyraz wdzięczności", „Deklaracja uczuć"). To jest ZNANE i OCZEKIWANE do czasu triage ekstraktora (kroki 5-6 audytu) — nie panikować przy golden diffie, ale odnotować skalę.
- Krok 3 — niezależny, może iść osobnym, wcześniejszym deployem (bezpieczny).

---

## KROK 1 — LIMIT + RANKING [TWARDE FAKTY]

**Gdzie:** `backend/fact_store.py:156-180` — `get_facts_for_prompt()`: dziś `SELECT` **bez LIMIT**, `ORDER BY CASE entity_type (MILESTONE→1, FACT→2, DATE→3, PERSON→4), importance DESC, timestamp DESC`. Zwraca WSZYSTKIE 391 rekordów → main.py renderuje wszystkie (main.py:596-607).

**Projekt zmiany (dane, nie kod):**
| Kategoria | Polityka | Uzasadnienie |
|---|---|---|
| `FACT:health`, `FACT:correction`, `FACT:preference`, `FACT:amelia_status`, `DATE:*`, `PERSON:*` | **ZAWSZE wszystkie** | typy supersede — max 1 rekord każdy (dziś łącznie 6); to jest prawdziwy „twardy" rdzeń |
| `MILESTONE:*` (love/trust/future/vulnerability/gratitude…) | **cap łącznie 15**, sortowanie: `importance DESC, timestamp DESC` (najnowsze) | po przyszłym triage prawdziwych deklaracji będzie garść; 15 najnowszych trzyma klimat bez zalewu |
| `FACT:habit` | **cap 5** najnowszych | dziś w 100% szum epizodyczny |
| Sufit bezpieczeństwa | **blok [TWARDE FAKTY] ≤ 8 000 zn** — jeśli po capach przekracza, utnij LISTĘ od końca (nie treść wpisów) | odporność na przyszły przyrost |

**Kształt implementacji (rekomendacja):** filtrowanie w Pythonie wewnątrz `get_facts_for_prompt` (po istniejącym SELECT): zachowuje obecny ORDER BY, łatwe do testu, zero zmian schematu. Alternatywa SQL (UNION per kategoria z LIMIT) — więcej roboty, ten sam efekt. **Nic nie jest kasowane — reszta zostaje w bazie, po prostu nie wchodzi do promptu.**

**Przed → Po (pseudo):**
```
PRZED: return [dict(r) for r in rows]                    # 391 wpisów, 67 273 zn bloku
PO:    always  = [r for r in rows if typ(r) w ZAWSZE]     # ~6
       miles   = [r for r in rows if MILESTONE][:15]      # importance/ts już posortowane
       habits  = [r for r in rows if FACT:habit][:5]
       out     = always + miles + habits                  # ~26 wpisów
       przytnij listę do 8 000 zn bloku                   # bezpiecznik
```

**Podkrok 1b (opcjonalny, 1 linia, rekomendowany):** nagłówek bloku (main.py:604-605) mówi „Te fakty są deterministyczne… **Zawsze mają pierwszeństwo** nad wspomnieniami z RAG" — to sensowne dla health/dat, ABSURDALNE dla 345 pseudo-deklaracji. Zmiana treści: „Fakty o zdrowiu, datach i korektach są deterministyczne i mają pierwszeństwo. Kamienie milowe to wspomnienia-kotwice, nie rozkazy tonu."

**Weryfikacja Amnezją:** `inspect?query=hej` → `hard_facts_count ≤ 26`; sekcja [TWARDE FAKTY] ≤ 8 000 zn (dziś 67 273); prompt spada z 90 931 do ~30k. Fraza kontrolna „kiedy mam wizyte u lekarza?" → DATE:medical_visit nadal obecny w bloku (kategoria ZAWSZE nie ucierpiała).

---

## KROK 2 — PRZYWRÓCENIE [WSPOMNIENIA] (T1)

**Przyczyna (plik:linia):** `token_manager.py:219` — `available_chars = self.max_chars - reserved_chars`, gdzie `max_chars = 3000×4 = 12 000` (main.py:245 + token_manager.py:17), a `reserved_chars = len(template)` (main.py:519 Astra; main.py:651 Amelia). `astra_base.txt` = 22 154 zn → `available = −10 154` → pętla `:244-266` nie przyjmuje nic → `fitted = []` → blok pusty. **Pękło 2026-03-18 (`ac92cb3`, template 8 383→14 392 > 12 000).** Amelia: template 14 860 → to samo.

**Projekt poprawki — DEDYKOWANY budżet wspomnień, odcięty od długości template:**
- NIE podnosić `max_tokens` (sprzężenie z rosnącym template zostaje — pęknie znowu przy 48k).
- NIE dawać `reserved_chars=0` (budżet 12k zaprosi z powrotem ściany tekstu).
- **TAK:** nowy opcjonalny parametr `fit_to_budget(..., budget_chars=None)`; gdy podany → `available_chars = budget_chars` (pomija arytmetykę max−reserved). Wywołania: main.py:519 i main.py:651 przekazują `budget_chars=3500`. Pozostali callerzy (`build_context` token_manager.py:282) — bez zmian, stara semantyka nietknięta.

**Budżet 3 500 zn — skąd:** finalny kanał to 6-8 wspomnień; linia w bloku (prefiks `[source, type, importance]` + time_prefix + tekst + `(relevance)`) ≈ 300-450 zn → 6-8 linii mieści się z zapasem; trim-path fit_to_budget (`:252-263`) obsłuży brzeg.

**Przed → Po (pseudo):**
```
PRZED: fitted = token_mgr.fit_to_budget(memories, reserved_chars=len(template))   # zawsze []
PO:    fitted = token_mgr.fit_to_budget(memories, budget_chars=3500)              # ~6 wspomnień
```

**Docelowy podział promptu (suma zdrowa):**
| Sekcja | Dziś (baseline) | Po fixie |
|---|---|---|
| astra_base + grounding | 18 615 (20%) | ~19k (nie ruszamy — charakter to osobna decyzja) |
| [AKTUALNY CZAS] | 53 | 53 |
| lukasz_core | 1 762 | 1 762 |
| **[TWARDE FAKTY]** | **67 273 (73%)** | **≤ 8 000** |
| **[WSPOMNIENIA]** | **2 (!)** | **≤ 3 500** |
| RAW [OSTATNIE SŁOWA] | 431 | ≤ 1 500 (bez zmian mechaniki) |
| [STAN] | 888 | ~900 |
| monolog | 1 909 | 1 909 |
| **RAZEM** | **90 931 (~22,7k tok)** | **~33-36k zn (~8-9k tok)** |

**Weryfikacja Amnezją (3 frazy):** `co pamietasz o LDI?`, `boli mnie brzuch`, `hej` →
1. blok [WSPOMNIENIA] **> 500 zn** i zawiera linie `- [source, type:…]` (dziś: 2 zn);
2. prompt **RÓŻNI SIĘ między frazami** (dziś identyczne 90 931);
3. grounding directive spójny z blokiem (dyrektywa „cytuj z [WSPOMNIENIA]" wskazuje na niepusty blok);
4. rozmiar promptu w widełkach 30-38k zn.

**Ostrzeżenie dla Opusa (oczekiwany efekt uboczny):** otwarty kanał = w prompt wchodzą top-2 milestony z kanału gwarantowanego — dziś śmieciowe (baseline golden setu: 19/19 fraz). NIE strój tego przy tym fixie (żadnego ruszania kanału 1b/MMR w tym deployu — jedna zmienna naraz). Skala śmieci wyjdzie w golden diffie i zostanie zaadresowana triage'em ekstraktora (kroki 5-6 audytu).

---

## KROK 3 — DEDUP CONCERNS + PRAWDA W /api/debug/stats

**3a. Concerns klonują się:** `companion_state.py:169-173` — `if new_concern not in self.active_concerns: append` + `[-5:]`. Dedup po RÓWNOŚCI STRINGA, a model co turę formułuje tę samą troskę inaczej → żywy stan (2026-07-05): 3/5 wpisów to warianty „poczucie winy za jedzenie". Dodatkowo `remove_concern` (:175-179) też porównuje po równości — model nigdy nie trafi w dokładny string, więc troski są praktycznie nieusuwalne.

**Projekt:** normalizacja (lowercase, bez interpunkcji) + podobieństwo zbiorów tokenów (Jaccard). Przy `nowa vs istniejąca ≥ 0.5` → **REPLACE** (zaktualizuj istniejącą nowym sformułowaniem — świeższe brzmienie, jedna pozycja), inaczej append. To samo dopasowanie dla `remove_concern` (usuwaj najbardziej podobną ≥ 0.5). Celowo BEZ embeddingów — warstwa stanu ma zostać zależnościowo czysta; Jaccard wystarcza na klony z żywego stanu (weryfikowalne: trzy warianty „poczucia winy" mają wspólne tokeny poczucie/winy/jedzenie).

**Przed → Po (pseudo):**
```
PRZED: if new not in concerns: concerns.append(new); concerns = concerns[-5:]
PO:    sim = max(jaccard(norm(new), norm(c)) for c in concerns)
       jeśli sim ≥ 0.5 → concerns[idx_max] = new     # replace, nie duplikat
       inaczej → append; [-5:]
```

**3b. `/api/debug/stats` kłamie:** `main.py:2110-2112` — hardcode `"level": 6, "level_name": "Absolutna Więź", "xp": 0`, mimo że `state = state_manager.load()` jest już w ręku (:2104). Realny stan: level 5, XP 1858. Poprawka: `state.level`, `state.level_name`, `state.xp`. (Przy okazji: ChatResponse ma ten sam hardcode — main.py:~1185-1190, fable_7 backlog #8 — można domknąć w tym samym ruchu.)

**Weryfikacja:** `GET /api/state` i `GET /api/debug/stats` zwracają TEN SAM level/xp. Concerns: po dniu rozmów `/api/state` nie zawiera dwóch wpisów o Jaccard ≥ 0.5 (sprawdzalne jednolinijkowcem).

---

## BASELINE — POMIAR PRZED FIXEM (żywy VPS, 2026-07-05, do porównania PO)

**Prompt (`inspect?query=hej`):**
```
PROMPT: 90 931 zn (~22,7k tok) — IDENTYCZNY dla każdego query
[WSPOMNIENIA] = '\n\n' (2 zn) przy final_count=6        ← T1 potwierdzony LIVE
base+grounding: 18 615 (20%) | lukasz_core: 1 762 (1%) | [TWARDE FAKTY]: 67 273 (73%)
RAW: 431 | [STAN]: 888 | monolog: 1 909
```
**Fakty (`/api/debug/facts`):** 391 łącznie; `love_declaration` 136, `trust_declaration` 132, `future_together` 77 (milestony = 345 = 88%), `habit` 40, pozostałe po 1. Suma `len(value)` = 44 489 zn. FP (heurystyka słów-kluczy, dolna granica; pomiar w audycie): love 83%, trust 100%, future 97%. Tempo: +6,5 faktu/dzień (2026-05-10 → 07-05).
**Stan:** level 5, XP 1858, mood „opiekuńcza"; concerns 5, w tym 3 klony „poczucia winy za jedzenie". `debug/stats` pokazuje level 6/XP 0 (hardcode).
**RAG per fraza:** snapshot 19 fraz golden setu (top-2 = milestone dla 19/19) — tabela w `golden_set_astra_2026-07-05.md`.

## KRYTERIA SUKCESU CAŁOŚCI (po deployu, świeży wątek)
1. Prompt 30-38k zn i RÓŻNY per query; [WSPOMNIENIA] niepusty; [TWARDE FAKTY] ≤ 8k.
2. Golden set: frazy lekkie → odpowiedzi lekkie (bez romansowego przegięcia mimo milestonów w kanale — jeśli przegięcie wróci, to sygnał do przyspieszenia triage, NIE do cofki fixu).
3. `/api/state` == `/api/debug/stats`; concerns bez klonów.
4. Metryki naturalności (skrypt z audytu 07-04) po tygodniu: nie gorsze niż po R1-R6.

*Fable. Spec + baseline. Kod nietknięty; wszystkie pomiary read-only (inspect/facts/state/stats).*
