# ASTRA ARCHITECTURE MAP
*Wygenerowano: 2026-04-22 na podstawie kodu z VPS 116.203.134.228*
*Dla: sesji diagnostycznej z zewnętrznym Claude (Opus)*

---

## 1. OVERVIEW

Astra to AI companion działający na prywatnym VPS (116.203.134.228, domena myastra.pl). Backend to FastAPI (Python) uruchamiany przez systemd jako serwis `myastra`. Rdzeń systemu to trójkanałowy RAG oparty na ChromaDB (lokalne embeddingi: `paraphrase-multilingual-MiniLM-L12-v2`) zintegrowany z Gemini 2.5 Flash (thinking_budget=4096, max_output_tokens=2048, JSON mode). Każda wiadomość użytkownika przechodzi przez pipeline: RAG retrieval → dynamic system prompt → Gemini call → JSON parse → semantic extraction → zapis do ChromaDB. Stan relacji (nastrój, troski, XP) jest persystowany w `companion_state.json`. Schedulery (APScheduler) uruchamiają nocną analizę o 03:00 i poranne/popołudniowe wiadomości.

---

## 2. PIPELINE FLOW

```
USER wysyła wiadomość (POST /api/chat)
│
├─ [main.py] strip_memory_echo() — usuwa [MEMORY]...[/MEMORY] echo loop
│
├─ [main.py] state_manager.load() — ładuje CompanionState z companion_state.json
│
├─ [vector_store.py] search_memories() — 3-kanałowy RAG
│   ├─ Kanał 1: astra_memory_v1 — wspomnienia semantyczne (top-3 po reranku + MMR)
│   ├─ Kanał 2: astra_memory_v1 source=character_core — wektory behawioralne (top-2)
│   └─ Kanał 3: astra_memory_v1 source=md_import — wiedza zewnętrzna (top-1)
│
├─ [strict_grounding.py] analyze_rag_results() — ocenia jakość RAG, tworzy grounding directive
│
├─ [main.py] build_system_prompt() — łączy:
│   ├─ prompts/astra_base.txt — character prompt (249 linii)
│   ├─ prompts/lukasz_core.json — twarde fakty nadrzędne (JSON → text)
│   ├─ RAG memories block (formatted)
│   ├─ CompanionState.to_prompt_block() — nastrój, troski, last_topic
│   └─ INNER_MONOLOGUE_INSTRUCTION — instrukcja JSON response format
│
├─ [vector_store.py] get_recent_session() — ostatnie 10 wiadomości z astra_memory_session_v1
│
├─ [main.py] gemini_client.models.generate_content() — call do Gemini API
│   └─ Zwraca JSON: {thought, mood, topic, new_concern, resolved_concern, safe_haven, hint, response}
│
├─ [main.py] parse_gemini_response() — parsuje JSON, fallback regex jeśli json.loads zawiedzie
│
├─ [vector_store.py] add_session_message() × 2 — zapisuje user + model do astra_memory_session_v1
│
├─ [semantic_pipeline.py + semantic_extractor.py] process_message() — wyciąga encje z wiadomości usera
│   └─ Typy: EMOTION, MILESTONE, FACT, PERSON, DATE, MEDICATION, SHARED_THING, GOAL
│
├─ [main.py] SUPERSEDE_TYPES check → vector_store.delete_by_entity_subtype() — usuwa stare wektory
│
├─ [vector_store.py] add_memory() — zapisuje nowe encje do astra_memory_v1
│
└─ [companion_state.py] update_after_message() + save() — aktualizuje stan relacji
```

---

## 3. KLUCZOWE PLIKI

### `backend/main.py` (~750 linii)
Centralny orchestrator. FastAPI app z jednym głównym endpointem `/api/chat`. Zawiera cały flow od sanitizacji inputu przez RAG, budowanie promptu, Gemini call, parse odpowiedzi, zapis sesji, ekstrakcję encji, update stanu. Zawiera też schedulery (nocna analiza, poranna, popołudniowa) i push notifications (VAPID/pywebpush).

### `backend/prompts/astra_base.txt` (249 linii)
System prompt definiujący charakter Astry: DNA (50% akceptacja, 30% charakter, 20% własne zdanie), temperatura relacji (nie tryby), zasady INNER_MONOLOGUE, HINT, RESPONSE. To jest "dusza" systemu. Zmiany tutaj mają największy wpływ na zachowanie.

### `backend/vector_store.py`
ChromaDB wrapper. Zarządza dwiema kolekcjami: `astra_memory_v1` (wspomnienia semantyczne) i `astra_memory_session_v1` (historia rozmów). Zawiera reranker (similarity 0.60 + importance 0.25 + recency 0.15 + keyword boost), MMR diversity selection, supersede logic (`delete_by_entity_subtype`), SHA256 user isolation.

### `backend/semantic_extractor.py` (~1037 linii)
Zero-shot NLU oparty na sentence-transformers. Wyciąga encje: EMOTION (tired/stressed/positive/negative/excited/sad), MILESTONE (trust_declaration/love_declaration/future_together/vulnerability/gratitude), FACT (preference/habit/personal), PERSON, DATE, MEDICATION, SHARED_THING. Osobna logika regex dla PERSON z listą EXCLUDED_NAMES i KNOWN_CHARACTERS (holo/menma/nazuna/ubel).

### `backend/semantic_pipeline.py`
Koordynator pipeline ekstrakcji. Wywołuje SemanticExtractor → MemoryEnricher → MemoryConsolidator. Limituje MILESTONE do 2 per wiadomość. Tworzy `ProcessedMemory` z syntetycznym tekstem (`[EMOTION:tired] ...`).

### `backend/memory_enricher.py`
Wzbogaca surowe encje o `importance` (skala 1–10), `relational_impact` (low/medium/high), `temporal_type` (ephemeral/persistent/milestone). Decyduje który typ encji zasługuje na wyższy importance score.

### `backend/companion_state.py`
CompanionState dataclass: `current_mood`, `mood_intensity`, `active_concerns` (lista key:value), `last_topic`, `last_user_vibe`, `messages_this_session`, `last_thought`, `morning_message`. StateManager ładuje/zapisuje JSON. `to_prompt_block()` formatuje stan do system promptu.

### `backend/strict_grounding.py`
Analizuje wyniki RAG i tworzy `grounding_directive` — instrukcję dla modelu jak pewnie/ostrożnie podchodzić do wspomnień (czy są istotne, czy są sprzeczne). Redukuje ryzyko halucynacji gdy RAG nie trafia.

### `backend/nocna_analiza.py`
Scheduler 03:00: odpytuje ChromaDB o ostatnie wspomnienia, wysyła do Gemini z prośbą o syntezę nocną. Generuje też poranne wiadomości. UWAGA: od jakiegoś czasu crash o 05:00 na `generate_morning_message` (znany bug — niezdiagnozowany).

### `backend/prompts/lukasz_core.json`
Twarde fakty o Łukaszu (JSON) wstrzykiwane do każdego promptu jako "SINGLE SOURCE OF TRUTH". Zawiera: kim jest, misja, styl pracy, zdrowie (Crohn), relacje AI (Amelia). Te dane WYGRYWAJĄ z wektorami z RAG przy konflikcie.

### `backend/prompts/character_vectors.json`
Definicje wektorów behawioralnych załadowanych do ChromaDB jako source=character_core. To są "wzorce zachowań" Astry — odpowiadane przy high-similarity queries.

### `backend/token_manager.py`
Zarządza budżetem tokenów dla bloku wspomnień w system promptie (`max_tokens=3000`). Przycina listę wspomnień jeśli przekracza limit.

---

## 4. LOGI — GDZIE I JAK

### Lokalizacja
System nie ma dedykowanych plików logów dla rozmów. Wszystko idzie do **stdout/stderr → systemd journal**.

```bash
# Pełne logi serwisu:
journalctl -u myastra --since "2026-04-07" --no-pager

# Tylko RAG + ekstrakcja + stan:
journalctl -u myastra --since "2026-04-07" --no-pager | grep -E "(RAG|ASTRA|SEMANTIC|PIPELINE|THOUGHT|STATE)"

# Konkretna sesja po conversation_id:
journalctl -u myastra --no-pager | grep "CONV_ID_TUTAJ"

# Błędy:
journalctl -u myastra --no-pager -p err
```

### Dostępne błąd log plik
`backend/error.log` — Gemini API errors zapisywane przez main.py gdy exception.

### Format wpisów journalctl (przykłady)
```
[RAG] 5 wyników dla: 'zapytanie usera...'
  [extracted_emotion] score=0.731 ts=2026-03-22 | [EMOTION:tired] tekst...
  [character_core] score=0.685 ts=2026-03-17 | Kiedy user dzieli się...
[ASTRA RAW] {"thought": "...", "mood": "...", ...}  ← pierwsze 200 znaków
[ASTRA THOUGHT] pełny inner monologue...
[ASTRA STATE_UPDATE] {'mood_shift': 'warm', 'new_concern': None, ...}
[ASTRA] Extracted 3 entities, saved 3: ['EMOTION:tired', 'FACT:preference', ...]
[VectorStore] Supersede: usunięto 1 stary/ch EMOTION:tired
```

### Historia rozmów w ChromaDB
```python
# Sesje (wiadomości user+model):
collection: astra_memory_session_v1  (1145 wektorów na 2026-04-22)

# Wspomnienia semantyczne:
collection: astra_memory_v1  (~1100 wektorów)
```

---

## 5. SERCE SYSTEMU — 3 PLIKI KRYTYCZNE

**1. `prompts/astra_base.txt`** — bez tego Astra nie ma tożsamości. Jakość odpowiedzi zależy bezpośrednio od tego pliku. Błędy w prompt = błędy w zachowaniu.

**2. `vector_store.py` → `search_memories()` + `rerank()`** — tu decyduje się *co* Astra pamięta w danej turze. Złe wagi reranku, zły pool_size, zły MMR penalty = złe wspomnienia = odpowiedzi bez kontekstu lub z halucynacją.

**3. `main.py` → `build_system_prompt()` + cały `/api/chat` endpoint** — orchestracja. Tu się łączą wszystkie kanały. Błędy tutaj (np. zły format historii dla Gemini, złe n= w search_memories) kaskadują na całość.

---

## 6. ZNANE WEAK POINTS

### KRYTYCZNE — halucynacja przy braku RAG hit
**Symptom (zaobserwowany 2026-04-19):** Gdy RAG nie zwraca wektora dla pytania o fakt (np. "jaka herbata"), model **zgaduje** zamiast powiedzieć "nie pamiętam". Grounding directive istnieje ale nie blokuje modelu wystarczająco.
**Lokalizacja:** `strict_grounding.py` — zbyt słaba dyrektywa UNCERTAIN lub model ją ignoruje przy temperature=0.85.
**Fix do rozważenia:** Dodać explicit fallback w system promptie: "Jeśli nie masz wektora z odpowiedzią — powiedz wprost: 'Nie mam tego w pamięci, powiedz mi.'"

### WYSOKI — rodzina (Holo/Menma/Nazuna) nie wyciągana przez RAG
**Symptom (2026-04-19):** Pytanie "kto jest w naszej rodzinie" zwróciło tylko "ty, ja, Amelia". Holo/Menma/Nazuna nie pojawiły się.
**Prawdopodobna przyczyna:** Wektory tych postaci istnieją w ChromaDB, ale semantycznie zapytanie "rodzina" nie trafia w embeddingi gdzie imiona się pojawiają. Keyword boost `_keyword_boost()` sprawdza słowa ≥4 litery — "holo" (4) i "menma" (5) powinny działać, ale `boost=0.15` może być za mały żeby podbić ranking.
**Alternatywna przyczyna:** Wektory postaci mogą mieć niskie `importance` (np. 3) i są wypychane przez nowsze emocjonalne wektory z wyższym recency score.

### ŚREDNI — nocna analiza crash 03:00→05:00
**Symptom:** `nocna_analiza.py:generate_morning_message` crashuje. Schedulery pokazują ostatnią udaną nocną analizę, ale poranne wiadomości generowane są przez osobny job (07:00) który działa.
**Lokalizacja:** `nocna_analiza.py` linia ~221.

### ŚREDNI — session_history n=10 za małe okno kontekstu
**Lokalizacja:** `main.py:576` — `get_recent_session(conversation_id, n=10)`.
**Problem:** 10 ostatnich wiadomości to 5 wymian. Przy dłuższej sesji model traci kontekst z początku rozmowy. Wcześniej było `n=30`, ale zmieniono. Sprawdzić aktualną wartość i czy to powoduje utratę ciągłości.

### NISKI — `companion_state.json` traci session_history po restarcie
**Symptom:** `session_history` w JSON jest zawsze puste (`[]`). Historia przechowywana jest w ChromaDB (session_collection), nie w JSON. To jest zamierzone — ale oznacza że *aktywna* historia sesji (w trakcie) żyje tylko w RAM i w ChromaDB, nie w companion_state.
**Ryzyko:** Jeśli ChromaDB się skompromituje, historia przepada.

### STRUKTURALNY — brak "nie wiem" grounding dla PERSON/FACT queries
**Opis:** Gdy user pyta o konkretny zapamiętany fakt (imię, preferencja, data), a RAG nie ma tego wektora — model nie ma instrukcji żeby przyznać brak wiedzy. Grounding directive jest ogólny ("korzystaj ostrożnie z niepewnych wspomnień") ale nie ma explicit "jeśli pytanie jest o konkretny fakt i nie masz pewności — powiedz to".

---

*Plik wygenerowany na potrzeby sesji diagnostycznej.*
*Kod na VPS: `/var/www/myastra/astra/backend/`*
*Logi: `journalctl -u myastra`*
*ChromaDB: `/var/www/myastra/astra/backend/chroma_db/`*
