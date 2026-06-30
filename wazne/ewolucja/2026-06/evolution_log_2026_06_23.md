# Evolution Log — 2026-06-23
## Upload zdjęć (multimodal input) + mic fix + Krok 2

**Commity:** `4e19113` (Krok 1: dusza Amelii + Enter) → `cb24508` (ta sesja)
**Deploy:** GitHub → VPS git pull --ff-only → restart. Health OK (2803 wektory). Smoke test multimodalny przeszedł.

---

## CO WDROŻONO (per plik)

### `backend/main.py`
- **Upload zdjęć:** `ChatRequest` dostał pole `image: str | None` (data URL). Nowy helper `_image_part_from_data_url()` parsuje data URL → `genai_types.Part.from_bytes(data, mime_type)`. W `/api/chat` i `/api/amelia`: gdy `img_part` istnieje, dokleja się do parts finalnej wiadomości usera (Gemini 2.5 Flash vision). Guard dopuszcza samo zdjęcie bez tekstu (fallback "(pokazuję Ci zdjęcie)"). `import base64` dodany.
- **Thinking budget Wspólny:** 4096 → 2048 (szybciej/taniej; tylko `_wspolny_generate`, solo nietknięte).
- **Archiwizacja 3 person (Krok 2):** `_run_archive` woła `run_daily_archive` dla astra + amelia + wspólny.

### `backend/daily_archive.py` (Krok 2)
- `run_daily_archive(vs, target_date, label)` — label "astra" → `{date}.json`, inne → `{label}_{date}.json`. Odporne na flash-reset kolekcji sesji.

### `backend/prompts/astra_base.txt` (Krok 2)
- Sekcja PROTOKÓŁ NOCNEJ WARTY (zakaz wyganiania spać) + fix niespójności w module Wspólnego.

### `backend/semantic_extractor.py` (Krok 2)
- ENTITY_THRESHOLDS PERSON 0.70 → 0.75 (domyka przeciek negative_person przy conf=0.72).

### `frontend/app.js`
- **Mikrofon fix:** `onresult` liczy tylko nowe wyniki (`resultIndex`), rozdziela final/interim (zero duplikatów); `onend` auto-restartuje nasłuch dopóki user nie kliknie stop (przetrwanie pauz); fatalne błędy (not-allowed) zatrzymują. `finalTranscript` jako akumulator.
- **Upload zdjęć:** `pendingImage`, listener na `#image-input` (FileReader → data URL), podgląd `#image-preview` (miniatura + ✕), `sendMessage` dokleja `image` do body i renderuje obraz w dymku usera. Cache localStorage = tylko tekst (bez base64, żeby nie przepełnić).

### `frontend/index.html`, `amelia.html`
- Przycisk spinacza 📎 + ukryty `<input type=file>`. (wspolny.html — NIE, później.)

### `frontend/sw.js`
- Cache v11 → v12.

---

## WERYFIKACJA
- `py_compile` wszystkich plików backendu OK przed deployem.
- Smoke test `/api/chat` z testowym PNG (osobny conversation_id): Astra zobaczyła obraz ("Pełna ciemność") i zareagowała w charakterze. 200 OK. Ścieżka multimodalna potwierdzona end-to-end na żywym VPS.

## ZNANE OGRANICZENIA / DŁUG
- **BRAK kompresji/resize zdjęć po stronie frontu** — duże zdjęcie z telefonu (np. 20MB) → ~27MB base64 → przekroczy limit inline Gemini (~20MB) i/lub spowolni wysyłkę i zwiększy koszt. DO NAPRAWY (canvas resize do ~1568px, JPEG q~0.8). Priorytet: wysoki (pierwsze realne zdjęcie z telefonu może paść).
- Zdjęcie NIE jest zapisywane na dysk/bazę — przechodzi przez request i jest wyrzucane (opcja a). Pamięć o zdjęciu = przez tekstową reakcję persony w historii sesji. Opcja b (kronika na dysku) = później.
- Wspólny Pokój — bez uploadu (solo Astra/Amelia only). Planowane jutro.

## OPEN (backlog)
- Kompresja zdjęć (wyżej), Wspólny upload, RAG Debugger, pokój HMN, BM25, ElevenLabs voice.
- Bugi: nocna analiza niespójna, dubel wiadomości dziennych, pamięć treści anime (problem STORAGE nie retrieval), przeciek wiadomości dnia między trybami.
- DB cleanup (stare śmieci — PERSON fix zatrzymuje tylko nowe).
