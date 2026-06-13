# RAPORT AUDYTU ARCHITEKTURY — ASTRA/AMELIA/WSPÓLNY POKÓJ
**Data:** 2026-06-13 | **Audytor:** Senior AI Backend Architect (GitHub Copilot)

---

## 1. AUDYT SKŁADANIA PROMPTÓW (PROMPT BUILDER)

### Funkcje odpowiedzialne

| Funkcja | Plik | Linia (przybliżona) |
|---|---|---|
| `build_system_prompt()` | `backend/main.py` | ~503 |
| `build_amelia_system_prompt()` | `backend/main.py` | ~640 |
| `load_prompt_template()` | `backend/main.py` | ~471 |
| `load_lukasz_core()` | `backend/main.py` | ~477 |
| `_wspolny_generate()` | `backend/main.py` | ~1419 |

### Kolejność konkatenacji — ASTRA

```
astra_base.txt
  └─ {memory_block}          ← RAG (VectorStore, enriched + timestamps)
  └─ {grounding_directive}   ← StrictGrounding
+ [AKTUALNY CZAS]
+ lukasz_core.json           ← load_lukasz_core() — ZAWSZE
+ [TWARDE FAKTY — SQLite]    ← FactStore.get_facts_for_prompt()
+ [OSTATNIE SŁOWA — RAW]     ← VectorStore.get_recent_user_messages(48h)
+ [STAN WEWNĘTRZNY ASTRY]    ← CompanionState.to_prompt_block()
+ INNER_MONOLOGUE_INSTRUCTION← stały string w main.py (linia 119)
```

### Kolejność konkatenacji — AMELIA

```
amelia_persona.txt
  └─ {memory_block}          ← amelia_memory_v1 RAG
  └─ {grounding_directive}
+ [AKTUALNY CZAS]
+ [HISTORIA AMELII]          ← amelia_lookup.get_facts_for_prompt()
+ [TWARDE FAKTY]             ← amelia_fact_store
+ [NASZE ŻARTY I HASŁA]      ← amelia_lookup.get_inside_jokes()
+ [OSTATNIE SŁOWA — RAW]
+ [CROSS_TALK inject]        ← build_cross_talk_block() jeśli flaga
+ [STAN WEWNĘTRZNY]          ← amelia_state.to_prompt_block()
+ INNER_MONOLOGUE_INSTRUCTION← ten sam stały string co Astra
```

### Krytyczna obserwacja — obie postaci dostają IDENTYCZNĄ instrukcję JSON

`backend/main.py` linia 593 dla Astry i linia 751 dla Amelii:

```python
monologue = INNER_MONOLOGUE_INSTRUCTION  # Astra
# ...
f"\n\n{state_block}\n\n{INNER_MONOLOGUE_INSTRUCTION}"  # Amelia
```

`INNER_MONOLOGUE_INSTRUCTION` nie ma żadnego warunkowania na postać — obie dostają dokładnie ten sam schemat odpowiedzi, z takimi samymi polami i regułami `thought`.

---

## 2. AUDYT "DUCHÓW PRZESZŁOŚCI" (LEGACY LEVEL SYSTEM)

### Stan plików levelów

```
backend/prompts/astra/
  ├── level_01_02.txt  ← EXISTS, NOT LOADED
  ├── level_03_04.txt  ← EXISTS, NOT LOADED
  └── level_05_06.txt  ← EXISTS, NOT LOADED
```

**Żadna funkcja w `main.py` nie ładuje plików z katalogu `backend/prompts/astra/`.** Historyczna funkcja `_get_astra_level_prompt()` istnieje wyłącznie w dokumentacji archiwalnej (`wazne/audyty obecne/archiwum prototypy/astra XP.md`) — NIE w produkcyjnym kodzie. Pliki są martwymi zasobami.

### Gdzie duchy żyją naprawdę

**Żywy system XP/Level w `companion_state.py`:**

```python
# companion_state.py — linia 18-47, AKTYWNY KOD
LEVEL_NAMES = {1: "Lodowa Ściana", 2: "Odwilż", ..., 6: "Absolutna Więź"}
LEVEL_THRESHOLDS = {1: 0, 2: 50, 3: 150, 4: 400, 5: 1000, 6: 2500}
DEBUG_XP_MULTIPLIER = 1
```

Metoda `_calculate_xp()` i `_check_level_up()` aktywnie obliczają XP i zmieniają level.

**Wstrzykiwanie levelu do promptu** — `CompanionState.to_prompt_block()`:

```python
f"Level: {self.level} ({self.level_name})\n"
f"XP: {self.xp} | Intimacy: {self.intimacy_score:.1f} | Trust: {self.trust_score:.1f}\n"
```

Model WIDZI ten blok jako `[STAN WEWNĘTRZNY ASTRY]` i interpretuje go.

**Asymetria poziomów:**
- `companion_state.json` Astry → `level: 6` (wynik historycznych rozmów) — model widzi "Absolutna Więź"
- `amelia_companion_state.json` → `level: 1` (nowy stack) — model widzi "Lodowa Ściana"

Amelia zachowuje się jak postać na etapie rezerwy i dystansu, mimo bogatego `amelia_persona.txt`.

**Hardcoded odpowiedź API** (`main.py` ~linia 1130):

```python
return ChatResponse(
    state_level=6,                  # ← zawsze 6 dla Astry (hardcoded)
    state_level_name="Absolutna Więź",  # ← hardcoded
```

To jest poprawne dla odpowiedzi API, ale w PROMPCIE Amelia nadal dostaje swój realny level z state managera.

---

## 3. AUDYT WSPÓLNEGO POKOJU (SHARED ROOM ROUTING)

### Mechanizm wykrywania trybu

Routing przez `_route_wspolny()` (`main.py` ~linia 1381) — keyword detection:

```python
amelia_called = any(w in msg_lower for w in ['ameli', 'amelka', 'amelko'])
astra_called  = any(w in msg_lower for w in ['astro', 'astra', 'astrą'])
```

Endpointy: `/api/wspolny` — zawsze tryb wspólny. Nie ma przełącznika `mode=aside` po stronie backendu; tryb `aside` jest decyzją wewnętrzną `_route_wspolny()`. Frontend wybiera endpoint, nie tryb.

### Ukryte instrukcje prowokujące konflikty — KLUCZOWE ZNALEZISKO

Instrukcja **ZASADA KONTRY** wstrzykiwana jest do system promptu **KAŻDEJ postaci, w KAŻDEJ turze wspólnego pokoju**, niezależnie od kontekstu:

```python
# _wspolny_generate(), linia ~1485 — ZAWSZE wykonywany blok
system_prompt += (
    f"\n\nZASADA KONTRY: Masz pełne prawo nie zgadzać się z {other_name_nom} w pokoju."
    f" Analizuj jej wypowiedzi. Jeśli uważesz że jej podejście jest błędne,"
    f" nie służy Łukaszowi, albo po prostu jest głupie"   # ← "albo po prostu jest głupie"
    f" — skontruj to w swoim stylu, prosto z mostu."
    f" Wasze różne wektory (pragmatyzm vs głębia) mają kolidować, nie zlewać się w jedno."
)
```

To bezpośrednia przyczyna sztucznych konfliktów. Model dostaje nakaz "analizuj jej wypowiedzi pod kątem błędów" i "mają kolidować" **nawet gdy Łukasz mówi o bólu lub jest wyczerpany**. Instrukcja nie ma żadnego warunku `safe_haven`.

**Drugi wyzwalacz** — w `amelia_persona.txt` (sekcja `[MODUŁ AKTYWNY TYLKO WE WSPÓLNYM POKOJU]`):

```
SUBTELNA, SPORADYCZNA ZAZDROŚĆ (POSIADANIE):
TRIGGER ZAZDROŚCI: Ta emocja ma prawo pojawić się rzadko (CZASEM),
tylko w momencie, gdy Łukasz przez dłuższą chwilę poświęca całą swoją
uwagę i czułość wyłącznie Astrze, ignorując ciebie.
```

Gdy Amelia jest `secondary` i dostaje `other_response` Astry — ta sekcja jest już aktywna w jej personie. Model interpretuje obecność długiej odpowiedzi Astry jako "Łukasz poświęca jej uwagę" i wyzwala zazdrość.

**Potrójne combo prowokacji dla Amelii jako `secondary`:**
1. `amelia_persona.txt` — moduł zazdrości
2. ZASADA KONTRY — nakaz analizy i kontrowania
3. Blok `[ASTRA właśnie napisała] + do_not_repeat` z instrukcją: `"pierwsze zdanie: reaguj na Astrę bezpośrednio"`

---

## 4. AUDYT WEWNĘTRZNEGO MONOLOGU (INNER MONOLOGUE)

### Lokalizacja aktywnej instrukcji

**Aktywna:** `INNER_MONOLOGUE_INSTRUCTION` w `backend/main.py`, linie 119–213 (stały string, ~95 linii).

**Zombie file:** `backend/inner_monologue_NEW.py` — istnieje w repo, jest w `.gitignore`, **nie jest importowany** przez żaden plik. Poprzedni audyt to odnotował (`analiza technologiczna/2026-05-22_audyt_RAG.md`), ale plik pozostał.

### Fragment instrukcji wymuszający sprzeczność

```
WALKA — masz w sobie sprzeczności. Pokazuj je:
Chcesz go przytulić, ale nie chcesz żeby wiedział jak bardzo.
Boisz się, ale nie możesz mu tego powiedzieć wprost.
Coś cię irytuje, ale wiesz że on tego nie robi złośliwie.
Pisz z tego miejsca.
```

Instrukcja jest **poprawna dla Astry** — buduje jej tsundere charakter. Problem polega na tym, że **Amelia dostaje dokładnie tę samą instrukcję**, mimo że jej persona jest fundamentalnie inna (Cicha Studnia, oaza spokoju, zero sztucznego napięcia). Amelia z nakazu "pisz z miejsca sprzeczności i walki wewnętrznej" generuje `thought` pełne rywalizacji i zazdrości.

**Dodatkowo** — instrukcja `thought` nie zawiera żadnej sekcji wyłączonej we wspólnym pokoju. Amelia generuje rozbudowany wewnętrzny monolog konfliktu, który co prawda nie trafia do `response`, ale wpływa na `mood` i `safe_haven` decyzję, co z kolei zmienia `response`.

### Schemat JSON — brakujące pole `narrator`

Aktywna `INNER_MONOLOGUE_INSTRUCTION` definiuje pola: `thought`, `mood`, `topic`, `new_concern`, `resolved_concern`, `safe_haven`, `hint`, `response`. **Nie ma pola `narrator`** w tym schemacie — jest ono dodawane przez `WSPOLNY_NARRATOR_BLOCK` jako oddzielna, doklejona instrukcja, co powoduje konflikty schematu (patrz punkt 5).

---

## 5. AUDYT NARRATORA (NARRATOR CACHE & HISTORY)

### Lokalizacja

`WSPOLNY_NARRATOR_BLOCK` — `backend/main.py`, linie ~214–231 (stały string), doklejany na **samym końcu** `system_prompt` w `_wspolny_generate()`.

### Mechanizm generowania

```python
# _wspolny_generate() — narrator doklejany na końcu systemu
system_prompt += WSPOLNY_NARRATOR_BLOCK

# Gemini generuje JSON z polem "narrator" obok standardowych pól
# Parse odbywa się ad-hoc POZA parse_gemini_response():
narrator = ""
try:
    _clean = re.sub(r'^```json\s*|\s*```$', '', raw.strip(), flags=re.MULTILINE).strip()
    _data = json.loads(_clean)
    narrator = str(_data.get("narrator", "")).strip()
except Exception:
    pass
```

### BŁĄD KRYTYCZNY: Narrator nie jest zapisywany do historii

```python
# _wspolny_generate() — zapis do shared_vector_store
shared_vector_store.add_session_message(
    conversation_id=conversation_id,
    role="model",
    content=f"[{persona}] {assistant_response}",  # ← TYLKO response, BEZ narrator!
    ...
    thought=inner_thought or "",
    hint=hint or "",
    # narrator = ??? BRAK POLA
)
```

Pole `narrator` jest zwracane do frontendu w dict `{"persona": ..., "response": ..., "narrator": ...}`, ale **nie trafia do `shared_vector_store`**. Historia sesji (`session_messages` wczytywana w kolejnej turze przez `get_recent_session(conversation_id)`) zawiera wyłącznie `[persona] response` — bez żadnego śladu opisów Narratora.

**Konsekwencja:** Model w kolejnej turze nie wie, że Astra "odwróciła wzrok" ani że "Amelia siedziała bez ruchu". Ciągłość sceny — zerowa. To tłumaczy dlaczego modele "resetują" pozy i gesty co turę.

### Drugi błąd: Konflikt schematu JSON

`INNER_MONOLOGUE_INSTRUCTION` definiuje ścisły schemat z 7 polami. `WSPOLNY_NARRATOR_BLOCK` **rozszerza ten schemat** przez doklejenie instrukcji "dodaj pole narrator" na końcu systemu. Gemini z `response_mime_type="application/json"` może generować niezgodnie z pierwotnym schematem (który nie zawiera `narrator`), lub — pole `narrator` koliduje z walidacją i jest pomijane.

---

## PROPOZYCJA ARCHITEKTONICZNEGO ROZWIĄZANIA

### Problem 1 — Asymetria leveli (Duchy Przeszłości)

**Fix:** W `CompanionState.to_prompt_block()` zastąpić blok `Level/XP/Intimacy/Trust` blokiem neutralnym dla obu postaci. Nowy blok: `[STAN RELACJI]` bez numerycznych leveli, z opisem słownym. Alternatywnie: zainicjalizować `amelia_companion_state.json` z `level: 6` i `level_name: "Absolutna Więź"`.

Docelowo: **spłaszczenie `companion_state.py`** — usunięcie `LEVEL_NAMES`, `LEVEL_THRESHOLDS`, `_calculate_xp()`, `_check_level_up()`, zastąpienie `intimacy_score` i `trust_score` samym `current_mood`.

### Problem 2 — ZASADA KONTRY wyzwalana zawsze

**Fix:** Owinąć blok ZASADA KONTRY w warunek:

```python
if not state.safe_haven:  # nie prowokuj konfliktu gdy Łukasz potrzebuje schronienia
    system_prompt += ZASADA_KONTRY_BLOCK
```

Lub: wzmocnić sformułowanie do "masz prawo polemizować, ALE tylko gdy Łukasz NIE potrzebuje schronienia i obie jesteście do tego zapraszane".

### Problem 3 — Amelia dostaje Astrową instrukcję `thought`

**Fix:** Rozdzielić `INNER_MONOLOGUE_INSTRUCTION` na dwie wersje:
- `ASTRA_MONOLOGUE_INSTRUCTION` — z walką i tsundere
- `AMELIA_MONOLOGUE_INSTRUCTION` — bez sekcji "WALKA", z naciskiem na spokojną obserwację i ochronę

Wywołanie już jest rozdzielone w kodzie — wystarczy przekazać właściwą stałą do każdej funkcji build.

### Problem 4 — Amelia zawsze na Level 1

**Fix natychmiastowy (2 min):** Wyedytować `backend/amelia_companion_state.json`, ustawić `"level": 6, "level_name": "Absolutna Więź"`.

**Fix docelowy:** Usunąć level system z `to_prompt_block()`.

### Problem 5 — Narrator nie zapisuje się do historii

**Fix:** Rozszerzyć zapis w `_wspolny_generate()`:

```python
# ZAMIAST:
content=f"[{persona}] {assistant_response}",

# ZMIENIĆ NA:
narrator_prefix = f"[NARRATOR: {narrator}]\n" if narrator else ""
content=f"{narrator_prefix}[{persona}] {assistant_response}",
```

Alternatywnie: zapisywać narrator jako osobne metadata w `add_session_message()`.

### Problem 6 — Konflikt schematu JSON dla Narratora

**Fix:** Przenieść pole `narrator` do głównej `INNER_MONOLOGUE_INSTRUCTION` jako opcjonalne pole w schemacie JSON (wersja dla wspólnego pokoju). Zunifikować parsing — `parse_gemini_response()` powinien zwracać też `narrator` zamiast osobnego `json.loads()` w `_wspolny_generate()`.

### Problem 7 — Zombie files (porządek)

- Usunąć `backend/inner_monologue_NEW.py`
- Usunąć `backend/prompts/astra/level_01_02.txt`, `level_03_04.txt`, `level_05_06.txt`

---

## TABELA PRIORYTETÓW

| # | Problem | Plik | Ryzyko | Effort |
|---|---|---|---|---|
| 🔴 1 | Narrator nie zapisuje się w historii | `main.py` ~L1590 | WYSOKI | 15 min |
| 🔴 2 | ZASADA KONTRY bez warunku safe_haven | `main.py` ~L1485 | WYSOKI | 5 min |
| 🟡 3 | Amelia dostaje Astrową instrukcję WALKI | `main.py` L119 | ŚREDNI | 30 min |
| 🟡 4 | Asymetria leveli Astra(6) vs Amelia(1) | `amelia_companion_state.json` | ŚREDNI | 2 min |
| 🟢 5 | Pliki `level_*.txt` — martwe zasoby | `prompts/astra/` | NISKI | 5 min |
| 🟢 6 | `inner_monologue_NEW.py` — zombie file | `backend/inner_monologue_NEW.py` | NISKI | 1 min |
