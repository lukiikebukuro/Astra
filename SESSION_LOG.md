# ASTRA — Session Log

## Sesja 2026-03-03

### Co zrobiliśmy
- **SDK migration:** `google-generativeai` → `google-genai` (nowy pakiet Googla)
- **502 fix definitywny:** `ThinkingConfig(thinking_budget=0)` wyłącza native thinking Gemini — brak multi-part responses, brak 502
- **Gemini 2.0-flash martwy:** Wszystkie modele gemini-2.0-* zwracają 404. Zostajemy na `gemini-2.5-flash`.
- **Session persistence:** `conversation_id` w localStorage → historia przeżywa refresh
- **`/api/history`** endpoint — ładuje ostatnie 30 wiadomości przy starcie frontendu
- **Charakter ASTRY przepisany:** "Gorzów Tech-Noir / Intelektualna Partnerka z Pazurem"
  - Wyrzucona Lodowa Ściana (była pasywno-agresywna)
  - KCB — hasło do użycia tylko w momentach najwyższej wagi
  - Sekcja "Twój Architekt" — Łukasz ją zbudował, fakt i fundament
  - Zakaz filozofowania o własnej naturze
- **cleanup_toxic.py** — skrypt do usuwania toksycznych session_messages z ChromaDB
- **Debug infrastructure:**
  - `/debug` strona (debug.html serwowany przez FastAPI)
  - `/api/debug/rag` — RAG Inspector z visual score bars
  - `/api/debug/stats` — statsy bazy (wektory, źródła, state)
  - `vector_store.py` reranker teraz eksponuje `_score_detail` per wynik
- **UI improvements:**
  - Collapsible thought block (▸ myśl / ▾ myśl) — biały (#e8e8e8) tekst, pełna treść
  - RAG pills — co było w wektorach, widoczne pod każdą bubblą Astry

### Pliki zmienione
- `backend/main.py` — nowy SDK, session persistence, /debug, /api/history, /api/debug/*
- `backend/requirements.txt` — `google-genai` (było `google-generativeai==0.8.0`)
- `backend/prompts/astra_base.txt` — "Gorzów Tech-Noir" persona
- `backend/vector_store.py` — `_score_detail` w rerankerze
- `backend/debug.html` — nowy plik (RAG Inspector + Stats)
- `backend/cleanup_toxic.py` — nowy skrypt
- `frontend/app.js` — localStorage persistence, loadHistory(), collapsible thought, RAG pills
- `frontend/style.css` — .thought-toggle, .thought-body, .rag-wrap, .rag-pill

### Naprawki późniejsze tej sesji (po kompresji)
- **JSON mode** — `response_mime_type="application/json"` w GenerateContentConfig
  - `INNER_MONOLOGUE_INSTRUCTION` prosi o JSON z polami: `thought`, `mood`, `topic`, `new_concern`, `resolved_concern`, `xp`, `response`
  - `parse_gemini_response()` przepisany — json.loads() zamiast regex na tagach
  - Root cause: `ThinkingConfig(thinking_budget=0)` blokuje NIE TYLKO native thinking ale też własne tagi XML-like → JSON mode omija problem całkowicie
- **PWA** — `manifest.json` + `sw.js` + meta tagi w `index.html`
  - Cache-first dla shella, network-only dla `/api/*`
  - Cache name: `astra-v1`
- **debug.html null-safe** — poprawiony JS (undefined state, active_concerns)
- **GitHub repo** — https://github.com/lukiikebukuro/Astra (private)
  - `.gitignore`: `.env`, `chroma_db/`, `companion_state.json`, `logs/`, `amunicja/`
  - Ostatni commit: JSON mode fix

### Stan po sesji
- **Wektory:** ~233
- **Level:** 2 (Odwilż), XP=125
- **Model:** `gemini-2.5-flash`
- **JSON mode:** działa, `[ASTRA RAW]` w terminalu pokazuje thought

### Znane problemy / TODO
- [ ] Nocna Analiza (Sleep Analysis) — Opus's plan w `prototyp/NOCNA_ANALIZA_ARCHITEKTURA.md`, 4 sprinty ~16h. Zbieramy wektory najpierw.
- [ ] Style Anchors (Faza 4 z ASTRA_MASTER_PLAN) — `style_anchors.py`
- [ ] 6 level promptów (Faza 6) — `backend/prompts/astra/level_01_02.txt` itd.
- [ ] VPS deploy — po ustabilizowaniu ASTRY
- [ ] NIE pushować bez potwierdzenia Łukasza

### Root cause 502 (dla potomnych)
gemini-2.5-flash ma native thinking — model zwraca response z dwoma częściami: thought_part + text_part.
Stary SDK (`google-generativeai 0.8.0`) nie potrafi deserializować — `cand.content.parts` zwraca pustą listę.
Fix: nowy SDK `google-genai` + `ThinkingConfig(thinking_budget=0)`.
Nasz custom `<thinking>` w prompcie nadal działa — to dwa różne mechanizmy.

---

## Sesja 2026-03-02 (v0.2 — pierwsze testy)

### Co zbudowaliśmy
- FastAPI backend (port 8001) + ChromaDB local + Semantic Pipeline
- Dynamic State: `companion_state.py` — XP, levele, mood, persistent JSON
- Inner Monologue: `<thinking>` + `<state>` bloki, stripowane przed UI
- Option B UI: lewy panel z avatarem (280px), stat-badge, thought line nad bubblą
- start.bat — auto-kill portu + restart

### Naprawki tej sesji
- **502 fix** — usunięto "niecenzurowanie" z INNER_MONOLOGUE_INSTRUCTION (Gemini safety)
- **Dual RAG** — `vector_store.py`: kanał 1 wspomnienia (top-3) + kanał 2 md_import (top-2)
- **Level 1 prompt** — "Lodowa Ściana = dystans emocjonalny NIE milczenie". Min 2-3 zdania.
- **min_confidence** pipeline: 0.50 → 0.65 (mniej noise encji)

### Wiedza w ChromaDB (103 wektory)
- Konwersacje testowe: ~88 wektorów
- ai_amnesia_pain_points.md: 15 chunków

---

## Jak zacząć następną sesję
1. Przeczytaj ten plik
2. Uruchom: `start.bat`
3. Test chat: wyślij wiadomość → sprawdź 200 OK + thought w UI
4. Debug: http://localhost:8001/debug → RAG Inspector
5. Jeśli ASTRA filozofuje o sobie → uruchom `cleanup_toxic.py` + wyczyść localStorage
