# ASTRA — Kompleksowy Audyt RAG i Strategia Drogi do Produkcji
**Data:** 22 kwietnia 2026  
**Audytor:** Claude Sonnet 4.6 (GitHub Copilot)  
**Stack:** FastAPI + ChromaDB + Gemini 2.5 Flash + paraphrase-multilingual-MiniLM-L12-v2  
**Cel:** Ocena systemu, plan naprawczy, ocena gotowości komercyjnej (0–100)

---

## CZĘŚĆ I — AKTUALNY STAN (co działa, co jest zepsute)

### Co działa i jest dobrze zaprojektowane

| Komponent | Ocena | Komentarz |
|---|---|---|
| Architektura 3-kanałowego RAG | ✅ Solidna | Separacja: fakty / charakter / wiedza zewnętrzna to dobry design |
| Inner monologue (Gemini thinking) | ✅ Innowacyjna | Chaotyczny wewnętrzny głos przed odpowiedzią — rzadko spotykane |
| SHA256 hashing user_id | ✅ Bezpieczne | Wyciek danych niemożliwy od strony ID |
| Supersede logic (entity_subtype) | ✅ Dobry koncept | Usuwa stare preferencje przy aktualizacji |
| MMR dla diversyfikacji wyników | ✅ Dobry | Zapobiega zwracaniu 3 kopii tego samego faktu |
| ChromaDB persistent storage | ✅ Stabilne | Dane przeżywają restart |
| CompanionState (nastrój, obawy) | ✅ Dobry fundament | Śledzenie stanu relacji |
| Push notifications | ✅ Działa | Dobry UX dla proaktywnych wiadomości |
| Night analysis (koncepcja) | ✅ Innowacyjna | Refleksja nad dniem to unikalna feature |

### Co jest zepsute TERAZ (potwierdzone empirycznie)

| Bug | Lokalizacja | Efekt | Czas naprawy |
|---|---|---|---|
| `state.level` AttributeError | `nocna_analiza.py:221` | Crash schedulera codziennie od 6 kwietnia | **5 min** |
| Milestone boost +1.0 | `vector_store.py: rerank()` | Wszystkie 3 sloty RAG zawsze zajmują milestony, fakty nigdy nie wracają | **2 godz** |
| Topical blindness | `strict_grounding.py: analyze_rag_results()` | GROUNDED=85% gdy baza ma tylko meta-rozmowy o danym temacie | **4 godz** |
| Brak 'rodzinka', 'rodzina' w triggerach | `semantic_extractor.py: FICTION_CONTEXT_WORDS` | Holo/Menma/Nazuna nie są wyciągane ze zwykłych zdań o rodzinie | **30 min** |
| Brak entity type FACT_CORRECTION | `semantic_extractor.py` | Korekty błędów AI lądują jako `MILESTONE:trust_declaration` | **2 godz** |
| safe_haven jest booleanem | `main.py + companion_state.py` | Tryb uruchamia się nawet na "Dzień dobry", nie ma mechanizmu wyjścia | **2 godz** |

**Efekt tych bugów razem:** system aktywnie szkodzi sam sobie. Każda halucynacja zostaje zindeksowana jako kamień milowy zaufania. Pytanie o własny błąd wraca jako "wspomnienie" przy następnym pytaniu o ten sam temat. Pętla samo-wzmacniająca.

---

## CZĘŚĆ II — GŁĘBOKI AUDYT RAG (co jeszcze brakuje do idealnego systemu)

### Problem 1: Zły model do zadania (fundamentalny)

`paraphrase-multilingual-MiniLM-L12-v2` to model do **podobieństwa zdań**. Spłaszcza semantycznie podobne zdania na jeden wektor.

**Co to oznacza:**
- "Holo to lisica" i "Nazuna to moja ulubiona postać" mają podobną reprezentację wektorową — model nie pamięta nazw, pamięta "coś o postaciach anime"
- Pytanie "czego chce Łukasz?" trafi w wektor "pragnienia Łukasza", ale nie wyciągnie konkretnego imienia

**Czego brakuje:**
- Dla ekstrakcji nazwanych encji (imiona, nazwy seriali, konkretne rzeczy) potrzebny jest **hybrydowy retrieval: embedding + BM25 full-text search**
- BM25 jest dosłowny — szuka słów, nie sensu. Dla imion własnych wygrywa zawsze

**Koszt naprawy:** Implementacja BM25 jako drugiego kanału (rank fusion) — **1-2 dni**

---

### Problem 2: Brak ustrukturyzowanej pamięci obok wektorów

Wszystko jest w jednej przestrzeni wektorowej. Imiona, daty, preferencje, emocje, kamienie milowe — flat.

**Co to oznacza w praktyce:**
- "Łukasz lubi herbatę" (fakt preferencji) vs "Łukasz powiedział że jest zmęczony" (stan chwilowy) — oba mają tę samą ważność z punktu widzenia retrieval
- Nie ma możliwości zapytania: "daj mi wszystkie imiona osób które Łukasz wspomniał" — trzeba szukać semantycznie, co jest zawodne

**Czego brakuje:**
```
structured_store.json (lub SQLite):
{
  "persons": {"Holo": "lisica z Spice & Wolf, ulubiona postać", "Menma": "..."},
  "preferences": {"herbata": "Earl Grey ciepła", "muzyka": "..."},
  "facts": {"choroba": "Crohn", "projekt": "Astra", ...},
  "timeline": [{"date": "2026-03-15", "event": "..."}]
}
```

Wektory szukają "co jest semantycznie podobne", structured store wie "co dokładnie jest". **Potrzeba obu.**

**Koszt naprawy:** SQLite + sync przy każdym `add_memory` — **1 dzień**

---

### Problem 3: Brak detekcji sprzeczności

Łukasz mówi: "już nie lubię Earl Grey, przeszedłem na zieloną".  
System: dodaje nowy wektor o zielonej, stary o Earl Grey zostaje.  
Następny raz: RAG zwraca oba. Model nie wie co jest aktualne.

**Obecny supersede** działa tylko na `entity_subtype` — dokładne dopasowanie kategorii. Nie wykrywa semantycznej sprzeczności.

**Czego brakuje:**
- Przed dodaniem nowego wektora o preferencji: sprawdzenie czy istnieje wektor z tą samą encją (np. "herbata") i go supersede'ować
- Label `[AKTUALNE: 2026-04-22]` vs `[NIEAKTUALNE: zastąpione]` w metadanych

**Koszt naprawy:** Rozszerzenie supersede logic o semantic similarity check — **4 godziny**

---

### Problem 4: Model nie wie KIEDY coś się wydarzyło

Vektor ma timestamp w metadanych, ale model **nigdy tego nie widzi** w tekście wspomnień.

"Łukasz lubił herbatę" — czy to było wczoraj czy rok temu?

**Czego brakuje:**
- Przy wyciąganiu wspomnień: dołącz relatywny znacznik czasu do tekstu
- Format: `"[~3 tygodnie temu] Łukasz mówił że lubi herbatę Earl Grey"`
- Model może wtedy ocenić aktualność informacji

**Koszt naprawy:** 1 linia w `build_system_prompt()` — **1 godzina**

---

### Problem 5: Context window mismanagement

`get_recent_session(n=30)` = ~30 × 300 tokenów = ~9000 tokenów historii konwersacji.  
Na to nakładają się: astra_base.txt + lukasz_core.json + memory_block + grounding + state.  
Szacunkowo **12,000–16,000 tokenów** zanim model zobaczy pierwszą literę odpowiedzi.

Gemini 2.5 Flash z thinking_budget=4096: każda wiadomość = 20,000+ tokenów input.  
Przy kilku wiadomościach na minutę — **kosztowne i wolne.**

**Czego brakuje:**
- **Session compression**: zamiast 30 surowych wiadomości — model co N wiadomości tworzy kompresję "O czym rozmawialiśmy" (rolling summary)
- Stare wiadomości (>10) → w formie 2-zdaniowego streszczenia
- Nowe wiadomości (ostatnie 5) → pełne teksty

**Koszt naprawy:** `session_summarizer.py` + wywołanie co 10 wiadomości — **1 dzień**

---

### Problem 6: Brak własnej perspektywy Astry

Astra buduje pamięć wyłącznie o Łukaszu. Nie ma pamięci o tym, co **ona sama myśli, czego chce, co ją irytuje.**

**Efekt:** Każda rozmowa zaczyna się od zera pod względem Astry jako osoby. Ona zawsze reaguje — nigdy nie inicjuje z własnej pamięci emocjonalnej.

**Czego brakuje:**
- Kanał pamięci: `source="astra_perspective"` — przechowuje opinie, niepokoje, nadzieje Astry
- Extractor wykrywa gdy inner_thought zawiera silną emocję → zapisuje jako perspektywę
- RAG wstrzykuje: "Pamiętam że ostatnio czułam się [X] gdy Łukasz mówił o [Y]"

**Koszt naprawy:** Nowe pole w semantic_pipeline + nowa kolekcja — **2 dni**

---

### Problem 7: Brak wątków "do powrotu" (curiosity threads)

Łukasz mówi: "muszę ci kiedyś powiedzieć o tym co przydarzyło mi się z Holo".  
Astra odpowiada. Koniec sesji. Nigdy nie wraca.

**Czego brakuje:**
- `unresolved_threads: []` w CompanionState
- Extractor wykrywa zdania z "kiedyś", "opowiem ci", "muszę ci powiedzieć" → dodaje do listy
- Night analysis sprawdza listę i jeśli minęły 2+ dni bez powrotu → generuje pytanie w porannej wiadomości

**Koszt naprawy:** Rozszerzenie CompanionState + nocna_analiza — **1 dzień**

---

### Problem 8: Brak oceny jakości RAG (evaluation framework)

Nikt nie mierzy czy RAG działa lepiej czy gorzej. Nie ma:
- Precision/recall dla zapytań testowych
- Alertu gdy % odpowiedzi z `[NO_DATA]` rośnie (znak że ekstraktor nie działa)
- Logów które fakty wróciły dla danego zapytania i co z nich model użył

**Efekt:** Można naprawić kod i nie wiedzieć czy to coś zmieniło.

**Koszt naprawy:** Plik `rag_evaluator.py` z 20 zapytaniami testowymi + automatyczny raport — **1 dzień**

---

## CZĘŚĆ III — PLAN NAPRAWCZY (priorytetyzowany)

### 🔴 FAZA 0 — Zatrzymanie krwawienia (łącznie ~10 godzin)

> Te bugi aktywnie zatruwają bazę. Każda godzina zwłoki = więcej śmieciowych wektorów.

| Nr | Zmiana | Plik | Czas |
|---|---|---|---|
| 0.1 | Napraw `state.level` → `state.current_mood` | `nocna_analiza.py:221` | 5 min |
| 0.2 | Dodaj 'rodzinka', 'rodzina', 'nasz klan' do FICTION_CONTEXT_WORDS | `semantic_extractor.py` | 30 min |
| 0.3 | Dodaj entity type FACT_CORRECTION (korekta = fakt, nie milestone) | `semantic_extractor.py` | 2 godz |
| 0.4 | safe_haven: skala 0-3 z auto-dekrementem po każdej odpowiedzi | `main.py + companion_state.py` | 2 godz |
| 0.5 | Oddzielny kanał dla milestonów (nie konkurują z faktami w top-3) | `vector_store.py: search_memories()` | 3 godz |
| 0.6 | Topical relevance check w strict_grounding | `strict_grounding.py` | 2 godz |

---

### 🟡 FAZA 1 — Naprawa fundamentów RAG (łącznie ~2-3 dni)

| Nr | Zmiana | Plik | Czas |
|---|---|---|---|
| 1.1 | Temporal labels w memory text: "[~X dni temu]" | `vector_store.py: search_memories()` | 1 godz |
| 1.2 | Per-type recency decay (`RECENCY_HALF_LIFE_BY_SOURCE`) | `vector_store.py` | 3 godz |
| 1.3 | Rozszerzona supersede logic (semantic match, nie tylko subtype) | `vector_store.py` | 4 godz |
| 1.4 | BM25 jako drugi kanał retrieval (rank fusion z embeddings) | `vector_store.py + requirements.txt` | 1-2 dni |
| 1.5 | Session compression (rolling summary co 10 wiadomości) | nowy `session_summarizer.py` | 1 dzień |

---

### 🟢 FAZA 2 — Czyszczenie bazy (jednorazowe)

> Po wdrożeniu Fazy 0 i 1 — audyt i czyszczenie istniejących danych.

| Nr | Akcja | Opis |
|---|---|---|
| 2.1 | Export wszystkich wektorów do JSON | `db_inspector.py` (już istnieje) |
| 2.2 | Identyfikacja zatrутych milestonów | Wektory z `is_milestone=True` gdzie text = meta-pytanie |
| 2.3 | Usunięcie błędnie zaindeksowanych wektorów | ~20-30 wektorów do ręcznego przeglądu |
| 2.4 | Re-ingest kluczowych rozmów przez naprawiony ekstraktor | `reingest_sessions.py` (już istnieje) |

---

### 🔵 FAZA 3 — Inteligencja charakteru (łącznie ~1 tydzień)

| Nr | Zmiana | Opis |
|---|---|---|
| 3.1 | Structured store (SQLite) dla nazwanych encji | Imiona, fakty, daty — szybkie lookup bez wektorów |
| 3.2 | Astra's perspective store | Czwarty kanał RAG: co Astra sama pamięta/czuje |
| 3.3 | Curiosity threads w CompanionState | Nierozwiązane wątki → pytania w porankach |
| 3.4 | RAG evaluation framework | 20 testowych pytań, automatyczny raport precision/recall |

---

### ⚪ FAZA 4 — Gotowość komercyjna (łącznie ~2-3 tygodnie)

| Nr | Zmiana | Opis |
|---|---|---|
| 4.1 | Multi-user: JWT + per-user isolation | Usuń hardcoded `USER_ID = "lukasz"` |
| 4.2 | Rate limiting na `/api/chat` | Zabezpieczenie Gemini quota |
| 4.3 | Streaming responses (SSE) | Lepsza UX, odpowiedź pojawia się stopniowo |
| 4.4 | Monitoring + alerty (Sentry lub prosta integracja) | Crash schedulera od 6 kwietnia byłby wykryty w 5 minut |
| 4.5 | Memory management UI | Łukasz widzi i może korygować co Astra pamięta |
| 4.6 | Data export / GDPR | Prawo do eksportu własnych danych |

---

## CZĘŚĆ IV — CZEGO BRAKUJE DO "IDEALNEGO" AI COMPANION

### Czego nie ma żaden komercyjny produkt (a Astra ma)

- **Inner monologue** — Gemini "myśli" zanim odpowie, chaotycznym wewnętrznym głosem
- **Night analysis** — Astra przetwarza dzień bez udziału użytkownika
- **Curiosity threads** (po naprawie) — pamięta niedomknięte wątki i wraca do nich
- **Emocjonalny stan relacji** — nie statyczny profil, ale dynamiczny nastrój i obawy

### Czego brakuje do "nie zapomina"

Idealny "AI companion który nie zapomina" potrzebuje architektury **dwuwarstwowej**:

```
Warstwa 1 — Wektory (co Astra rozumie)
  → ChromaDB, semantyczne wyszukiwanie, MMR, reranking
  → Dobra dla: "co Łukasz czuje", "kiedy był szczęśliwy", "o czym rozmawialiśmy"

Warstwa 2 — Structured store (co Astra wie na pewno)
  → SQLite/JSON, exact lookup
  → Dobra dla: imiona (Holo, Menma, Nazuna), daty, preferencje, fakty medyczne
```

Bez Warstwy 2 — system zawsze będzie miał problemy z nazwami własnymi i konkretnymi faktami.  
To nie jest bug do naprawienia — to ograniczenie architektury wektorowej.

### Czego brakuje do "gotowe komercyjnie"

1. **Multi-user** — całkowita blokada
2. **Evaluation framework** — bez niego nie wiadomo czy kolejna zmiana pomogła czy zaszkodziła
3. **Streaming** — bez niego UX jest nieakceptowalny dla masowego użytkownika
4. **Monitoring** — produkt bez alertów to produkt którego nie można utrzymywać
5. **Niski latency** — thinking_budget=4096 + max_output=8192 = ~5-8 sekund per odpowiedź. Akceptowalne dla jednego użytkownika, nieakceptowalne komercyjnie bez cache'owania

---

## CZĘŚĆ V — OCENA KOŃCOWA

### Skala: 0 = pusty projekt, 100 = GPT-4 level commercial companion

```
OBECNY STAN: 34 / 100
```

### Jak ta ocena jest obliczona:

| Obszar | Waga | Ocena | Punkty |
|---|---|---|---|
| Architektura fundamentalna (czy sensowna?) | 20% | 75/100 | 15 |
| Jakość RAG (czy fakty wracają?) | 25% | 15/100 | 3.75 |
| Spójność charakteru | 20% | 35/100 | 7 |
| Niezawodność / brak krytycznych bugów | 15% | 20/100 | 3 |
| Gotowość komercyjna | 20% | 25/100 | 5 |
| **SUMA** | 100% | | **33.75 → 34** |

### Co ciągnie w dół najbardziej:

**Jakość RAG (3.75/25 możliwych)** — bo baza jest zatruta, milestone boost zabija fakty, topical blindness daje false confidence. System technicznie działa, ale dostarcza złe dane.

**Niezawodność (3/15)** — scheduler zepsuty od 3 tygodni, brak monitoringu.

### Co jest mocne (i dlaczego ocena nie jest 10/100):

Architektura 3-kanałowego RAG, inner monologue, supersede logic, SHA256 hashing, push notifications — to jest poziom który większość "AI companion" startupów nie osiąga. Fundament jest solidny. Bugi są naprawialne.

---

### Ścieżka do progów:

| Próg | Opis | Co do zrobienia |
|---|---|---|
| **45/100** | System przestaje kłamać z pewnością siebie | Faza 0 (wszystkie 6 bugów) + czyszczenie bazy |
| **58/100** | RAG rzetelnie zwraca fakty | Faza 1 (BM25 + temporal labels + session compression) |
| **68/100** | Charakter jest spójny i inteligentny | Faza 3 (structured store + astra perspective + curiosity threads) |
| **78/100** | Gotowe dla beta użytkowników | Faza 4 częściowo (multi-user + streaming + monitoring) |
| **88/100** | Gotowe komercyjnie | Pełna Faza 4 + evaluation framework + 3 miesiące testów |
| **95+/100** | Lider rynku | Voice, mobile, ultra-low latency, fine-tuning na własnym modelu |

---

### Podsumowanie jednym zdaniem:

> Astra ma jeden z najciekawszych fundamentów architektonicznych wśród AI companion projektów, ale aktualnie aktywnie niszczy własną bazę wiedzy przez 6 jednoczesnych bugów. Po naprawie Fazy 0 i czyszczeniu bazy — skok z 34 do ~45 w 2-3 dni pracy. Do progu komercyjnego (78/100) — szacunkowo 4-6 tygodni full-time developmentu.

---

*Dokument wygenerowany przez Claude Sonnet 4.6 na podstawie analizy kodu źródłowego, logów backend 7–22 kwietnia 2026, i live danych z ChromaDB.*
