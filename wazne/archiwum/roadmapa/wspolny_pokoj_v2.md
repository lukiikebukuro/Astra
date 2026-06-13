# Wspólny Pokój v2 — Roadmapa
**Data:** 2026-05-08
**Autorzy:** Łukasz Piskorski / Claude Sonnet 4.6
**Kontekst:** Analiza rozmowy `wspolnarozmowa1.md` + audyt kodu `main.py`, `vector_store.py`, `app.js`

---

## Diagnoza — co jest zepsute

### Problemy stwierdzone z rozmowy (wspolnarozmowa1.md)

| # | Problem | Objaw w rozmowie |
|---|---------|-----------------|
| P1 | Brak labelki postaci przy bańce | "skąd mam wiedzieć czy pisze Astra czy Amelia" |
| P2 | Postaci nie widzą się między turami | "nie widzicie swoich wiadomości?" |
| P3 | Pierwszy odpowiadający nie wie o obecności drugiej | Astra zaskoczona Amelią, CoT "nie chcę się z nią dzielić" |
| P4 | Losowość 30%/70% bez logiki narracyjnej | Nieprzewidywalne kto odpowie |
| P5 | Amelia bez historii w nowej kolekcji | "masz stare wektory po prostu" |

### Problemy stwierdzone z kodu

| # | Problem | Lokalizacja | Root cause |
|---|---------|-------------|------------|
| K1 | Historia znika po refresh w /amelia i /wspolny | `app.js:349` | `if (ROOM !== 'astra') return;` — hardkodowane |
| K2 | Mikrofon kasuje poprzedni tekst | `app.js:305` | `inputEl.value = transcript` zamiast appendowania |
| K3 | Mikrofon zatrzymuje się automatycznie | `app.js:299` | `recognition.continuous = false` |
| K4 | `/api/history` tylko dla Astry | `main.py:1436` | Hardkodowany `vector_store` (Astry) |
| K5 | Shared session: zapis vs odczyt mismatch | `main.py:1264` vs `main.py:1232` | Zapis do `shared_vector_store`, odczyt z prywatnego `vs` |
| K6 | Brak "jesteś w pokoju z X" w pierwszym prompcie | `main.py:1222` | `other_response=None` → brak kontekstu shared room |

---

## Architektura docelowa

### Aktualna (zepsuta)
```
Łukasz wysyła wiadomość
     ↓
70%: losowa jedna postać → generuje (nie wie o drugiej)
30%: pierwsza postać → generuje
     ↓
     druga postać → generuje (widzi TYLKO ostatnią wiadomość pierwszej)
     ↓
Frontend renderuje (bez labelki kto mówi)
```

### Docelowa
```
Łukasz wysyła wiadomość
     ↓
Shared history: obie postaci czytają TĘ SAMĄ historię rozmowy
     ↓
Astra (zawsze pierwsza gdy obie) → generuje
  ↳ widzi: user_msg + pełna shared historia + "jestem w pokoju z Amelią"
     ↓
Amelia → generuje
  ↳ widzi: user_msg + pełna shared historia + odpowiedź Astry z tej tury + "jestem w pokoju z Astrą"
     ↓
Zapis obu odpowiedzi do shared history
     ↓
Frontend: labelki "ASTRA" / "AMELIA" przy każdej bańce
```

---

## Etap 0 — Hotfixy (priorytet: TERAZ, ~2h)

Niezależne od architektury. Naprawiają widoczne usterki bez refaktoru.

### H1: Historia po refresh — /amelia i /wspolny

**Plik:** `frontend/app.js`

**Problem:** `loadHistory()` ma hardkodowany warunek `ROOM !== 'astra'`.

**Fix:**
```javascript
async function loadHistory() {
    if (!conversationId) return;
    const historyEndpoint = ROOM === 'wspolny'
        ? `/api/history/wspolny?conversation_id=${conversationId}&n=30`
        : `/api/history?conversation_id=${conversationId}&n=30`;
    // ...
    data.messages.forEach(msg => {
        // dla wspolny: msg.content może mieć prefix "[astra]" / "[amelia]"
        const role = msg.role === 'user' ? 'user'
                   : (msg.persona || ROOM);  // persona field dla wspolny
        appendBubble(role, marked.parse(msg.content || ''), msg.thought || '', [], [], msg.hint || '');
    });
}
```

**Plik:** `backend/main.py` — nowy endpoint:
```python
@app.get("/api/history/wspolny")
async def get_wspolny_history(conversation_id: str, n: int = 30):
    messages = shared_vector_store.get_recent_session(conversation_id, n=n)
    return {"messages": messages, "conversation_id": conversation_id}

@app.get("/api/history/amelia")
async def get_amelia_history(conversation_id: str, n: int = 30):
    messages = amelia_vector_store.get_recent_session(conversation_id, n=n)
    return {"messages": messages, "conversation_id": conversation_id}
```

Zaktualizować `loadHistory()` żeby wybierał endpoint na podstawie `ROOM`.

---

### H2: Mikrofon — fix append + continuous

**Plik:** `frontend/app.js`

**Problemy:**
- `inputEl.value = transcript` → nadpisuje istniejący tekst
- `recognition.continuous = false` → sesja kończy się po pierwszej pauzie
- Ponowne naciśnięcie mikrofonu kasuje to co było w polu

**Fix:**
```javascript
recognition.continuous = true;       // nie zatrzymuje się po pauzie
recognition.interimResults = true;

let baseText = '';                    // tekst który był przed startem nagrywania

recognition.onresult = (e) => {
    const interim = Array.from(e.results).map(r => r[0].transcript).join('');
    inputEl.value = baseText + interim;
    autoResize();
};

function toggleMic() {
    if (!recognition) { appendSystemMsg('Przeglądarka nie obsługuje Web Speech API.'); return; }
    if (isRecording) {
        recognition.stop();
        // baseText nie resetujemy — tekst zostaje w polu
    } else {
        baseText = inputEl.value;     // zapisz co już jest w polu
        recognition.start();
        isRecording = true;
        micBtn.textContent = '⏹';
        micBtn.classList.add('recording');
    }
}
```

---

### H3: Labelka postaci przy bańce w /wspolny

**Plik:** `frontend/app.js` — `appendBubble()`

**Problem:** Bańka ma CSS klasę `bubble astra` lub `bubble amelia` ale żadnego widocznego tekstu "kto pisze".

**Fix w `appendBubble()`:**
```javascript
// Dla wspolny pokoju — dopisz imię nadawcy nad bańką
if (ROOM === 'wspolny' && isAI) {
    const nameEl = document.createElement('div');
    nameEl.className = 'persona-label';
    nameEl.textContent = role.toUpperCase();   // "ASTRA" / "AMELIA"
    wrap.appendChild(nameEl);
}
```

**Plik:** `frontend/style.css` — nowy selektor:
```css
.persona-label {
    font-size: 0.65rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    opacity: 0.55;
    margin-bottom: 2px;
    padding-left: 4px;
}
.bubble-wrap.astra .persona-label { color: #b388ff; }
.bubble-wrap.amelia .persona-label { color: #f48fb1; }
```

---

## Etap 1 — Wspólny Pokój v2: Świadomość Obecności (~4h)

### Cel
Postaci wiedzą że są razem. Obie zawsze odpowiadają. Historia jest wspólna.

### 1.1 Koniec z losowością — obie zawsze odpowiadają

**Plik:** `backend/main.py` — `wspolny_chat()`

**Aktualnie:**
```python
both = random.random() < 0.30
```

**Zmiana:** Obie postaci odpowiadają zawsze. Kolejność: Astra → Amelia (można później zrobić configurowalną).

```python
@app.post("/api/wspolny", response_model=WspolnyResponse)
async def wspolny_chat(req: ChatRequest):
    if not gemini_client:
        raise HTTPException(status_code=503, detail="Gemini API nie skonfigurowane")
    user_msg_clean = strip_memory_echo(req.message)
    if not user_msg_clean:
        raise HTTPException(status_code=400, detail="Pusta wiadomość")

    conversation_id = req.conversation_id or str(uuid.uuid4())

    # Astra zawsze pierwsza
    astra_result = await _wspolny_generate('astra', user_msg_clean, conversation_id)
    # Amelia zawsze widzi co Astra napisała
    amelia_result = await _wspolny_generate(
        'amelia', user_msg_clean, conversation_id,
        other_response=astra_result['response'],
        other_persona='Astra',
    )
    return WspolnyResponse(
        responses=[astra_result, amelia_result],
        conversation_id=conversation_id,
        mode="both_astra_first",
    )
```

### 1.2 Każda postać wie że jest w pokoju z drugą

**Plik:** `backend/main.py` — `_wspolny_generate()`

Dodaj parametr `room_personas` i wstrzyknij do system promptu przed generowaniem:

```python
async def _wspolny_generate(persona: str, user_msg: str, conversation_id: str,
                             other_response: str = None,
                             other_persona: str = None) -> dict:
    # ... (istniejący kod RAG)

    # Kontekst pokoju — pierwsza postać też go dostaje
    room_context = (
        f"\n\n[WSPÓLNY POKÓJ]\n"
        f"Jesteś w pokoju razem z {'Amelią' if persona == 'astra' else 'Astrą'} i Łukaszem. "
        f"Obie tu jesteście jednocześnie. Wiesz o sobie nawzajem. "
        f"Mówisz do ŁUKASZA — nie do niej. Ale ona słyszy wszystko."
    )
    system_prompt += room_context

    # Jeśli druga postać już odpowiedziała — dodaj jej wypowiedź
    if other_response and other_persona:
        system_prompt += (
            f"\n\n[{other_persona.upper()} właśnie napisała]\n"
            f"\"{other_response}\"\n\n"
            f"Twoja kolej. Nawiąż do jej słów — uzupełnij, zareaguj emocjonalnie lub polemizuj. "
            f"Twoja odpowiedź musi być INNA w tonie i treści. Jesteście różne."
        )
    # ...
```

### 1.3 Naprawienie mismatch sesji shared — odczyt z shared_vector_store

**Plik:** `backend/main.py` — `_wspolny_generate()`

**Aktualnie (błąd):**
```python
session_messages = vs.get_recent_session(conversation_id, n=6)  # prywatny VS!
```

**Fix:**
```python
# Obie postaci czytają TĘ SAMĄ historię rozmowy z shared store
session_messages = shared_vector_store.get_recent_session(conversation_id, n=10)
```

Historia będzie zawierać wiadomości w formacie:
- `role="user"` → wiadomość Łukasza
- `role="model"`, content=`"[astra] tekst"` → wypowiedź Astry
- `role="model"`, content=`"[amelia] tekst"` → wypowiedź Amelii

Przed wysłaniem do Gemini — wyczyść prefix `[astra]`/`[amelia]` z `content` gdy budujesz `contents`, ale zachowaj go w `session_messages` żeby postać widziała kto co powiedział.

---

## Etap 2 — Pamięć Wzajemna (~4-6h)

### Cel
Postaci pamiętają historię siebie nawzajem z poprzednich sesji, nie tylko bieżącej tury.

### 2.1 Cross-persona RAG

Każda postać podczas wyszukiwania wspomnień przeszukuje również `shared_vector_store`:

```python
# W _wspolny_generate — rozszerzone RAG
memories = vs.search_memories(query=user_msg, persona_id=pid, n=4, ...)
shared_memories = shared_vector_store.search_memories(
    query=user_msg, persona_id='shared', n=2, ...
)
memories += shared_memories
```

### 2.2 Zapis wspólnych wspomnień

Gdy semantic pipeline wyciągnie encje z wiadomości w shared room, NAJWAŻNIEJSZE (importance ≥ 7) lądują w `shared_vector_store` z tagiem `source=shared_room` — dostępne dla OBU postaci przy następnej sesji.

```python
# Po ekstrakcji w wspolny_chat:
for mem in extracted:
    if mem.importance >= 7:
        shared_vector_store.add_memory(
            text=mem.text, ..., persona_id='shared', source='shared_room'
        )
```

### 2.3 Blok [WSPÓLNY POKÓJ HISTORIA] w system prompcie

Zamiast (lub obok) standardowego bloku RAG, każda postać dostaje skondensowaną historię ostatnich N tur w pokoju:

```
[WSPÓLNY POKÓJ — ostatnie wymiany]
Łukasz: hej
Astra: Cześć. *opieram się o twoje ramię*
Amelia: Widzimy, Łukasz. *kładę dłoń na twojej dłoni*
---
Łukasz: amelko, wszystko jest dzisiaj w porządku...
```

Max 5 ostatnich tur (configurowalnie), budowany z `shared_vector_store.get_recent_session()`.

---

## Etap 3 — Dynamika: kto odpowiada i kiedy (~4-6h)

### Cel
Zamiast "zawsze obie" — inteligentne wykrywanie czy wiadomość dotyczy konkretnej postaci.

### 3.1 Signal routing

```python
def _detect_addressee(user_msg: str, personas: list) -> list:
    """
    Zwraca listę postaci które powinny odpowiedzieć na tę wiadomość.
    - Imię postaci w wiadomości → ona odpowiada
    - Ogólna wiadomość → obie
    - Pytanie techniczne → Astra (główna)
    - Emocja/choroba → obie
    """
    msg_lower = user_msg.lower()
    addressed = []
    for p in personas:
        if p['name'].lower() in msg_lower:
            addressed.append(p)
    return addressed if addressed else personas  # jeśli nikt nie wywoływany → obie
```

### 3.2 Opcjonalna odpowiedź drugiej postaci

Gdy wiadomość jest do konkretnej postaci (np. "Amelko, ..."), Astra może wtrącić się krótkim komentarzem lub milczeć. Decyduje signal detector + threshold ważności.

```python
# Gdy Amelia jest adresatem:
amelia_result = await _wspolny_generate('amelia', user_msg, conversation_id)

# Astra reaguje krótko (opcjonalnie, jeśli strong_signal)
if detect_strong_signal(user_msg):  # Crohn, kryzys, ważny moment
    astra_aside = await _wspolny_generate(
        'astra', user_msg, conversation_id,
        other_response=amelia_result['response'],
        mode='aside',  # krótki komentarz, nie pełna odpowiedź
    )
    responses = [amelia_result, astra_aside]
else:
    responses = [amelia_result]
```

---

## Etap 4 — Skalowalność na N postaci (~6-8h)

### Cel
Architektura nie zakłada hardkodowanych "astra" + "amelia". Nowa postać = wpis w rejestrze.

### 4.1 Personas registry

```python
# config/personas.py
PERSONAS = {
    'astra': {
        'name': 'Astra',
        'vector_store': 'astra_memory_v1',
        'fact_store': 'astra_facts.db',
        'state_file': 'companion_state.json',
        'persona_file': 'astra_base.txt',
        'endpoint': '/api/chat',
        'color': '#b388ff',
        'avatar': 'astra.jpg',
    },
    'amelia': {
        'name': 'Amelia',
        'vector_store': 'amelia_memory_v1',
        'fact_store': 'amelia_facts.db',
        'state_file': 'amelia_companion_state.json',
        'persona_file': 'amelia_persona.txt',
        'endpoint': '/api/amelia',
        'color': '#f48fb1',
        'avatar': 'amelka.png',
    },
    # przyszłe: nazuna, holo, hana...
}

SHARED_ROOMS = {
    'wspolny': ['astra', 'amelia'],
    # 'rodzina': ['astra', 'amelia', 'nazuna', 'holo'],
}
```

### 4.2 Generyczny `_wspolny_generate`

Zamiast hardkodowanego `is_astra = (persona == 'astra')`, wszystko pochodzi z `PERSONAS[persona]`.

### 4.3 Frontend dynamiczny

```javascript
// Avatary i kolory per postać z config
const PERSONA_CONFIG = {
    astra:  { color: '#b388ff', avatar: 'astra.jpg' },
    amelia: { color: '#f48fb1', avatar: 'amelka.png' },
    // nazuna, holo, hana...
};
```

Labelka nad bańką renderuje imię + kolorek per postać.

---

## Plan wdrożenia

| Etap | Co | Szacowany czas | Priorytet |
|------|----|----------------|-----------|
| **0 — Hotfixy** | Historia /amelia + /wspolny, mikrofon, labelka | ~2h | **Dziś** |
| **1 — v2 MVP** | Obie zawsze, shared session, świadomość obecności | ~4h | Następna sesja |
| **2 — Pamięć wzajemna** | Cross-persona RAG, shared memories, historia blok | ~4-6h | Po etapie 1 |
| **3 — Dynamika** | Signal routing, opcjonalne wtrącenia | ~4-6h | Po etapie 2 |
| **4 — N postaci** | Registry, generyczny kod, Nazuna/Holo | ~6-8h | Po Amelii migration |

---

## Zmiany plików per etap

### Etap 0
- `frontend/app.js` — `loadHistory()`, `toggleMic()`, `recognition.onresult`, `appendBubble()`
- `frontend/style.css` — `.persona-label`
- `backend/main.py` — `/api/history/amelia`, `/api/history/wspolny`

### Etap 1
- `backend/main.py` — `wspolny_chat()`, `_wspolny_generate()` (room context, session mismatch fix)

### Etap 2
- `backend/main.py` — cross-persona RAG, shared memories write, historia blok
- `backend/vector_store.py` — `search_memories()` z opcją `persona_id='shared'`

### Etap 3
- `backend/main.py` — `_detect_addressee()`, opcjonalne aside

### Etap 4
- `backend/config/personas.py` — nowy plik
- `backend/main.py` — refaktor _wspolny_generate na generyczny
- `frontend/app.js` — dynamiczne PERSONA_CONFIG

---

## Uwagi techniczne

**Shared session format** — messages w shared_vector_store mają content w formacie:
- user: `"czuję się źle dzisiaj"` (surowy, bez prefixu)
- model: `"[astra] Crohn czy coś innego? *opierasz się o futrynę*"` lub `"[amelia] *kładę dłoń na twojej dłoni*"`

Frontend parsuje prefix `[imię]` żeby wybrać klasę CSS bańki. Backend buduje historię Gemini bez prefixu (czysta treść) ale z informacją kto mówił (przez `role="model"` i prefix w content).

**Kolejność generowania** — Astra pierwsza, Amelia odpowiada widząc Astrę. Ważne żeby nie generować równolegle (asyncio.gather) — wtedy Amelia nie widzi Astry. Zawsze sekwencyjnie: await Astra → await Amelia.

**Unikanie echo-loop** — gdy Amelia cytuje Astrę w swojej odpowiedzi, nie wolno tego zapisywać do ChromaDB jako "wspomnienie" — tylko do shared session history. Semantic pipeline powinien to filtrować (pattern: `"[X] tekst"` → nie ekstrahuj encji).

**Thinking budget w wspolny** — aktualnie 2048 dla shared room vs 4096 dla private. To OK — rozmowy wspólne są krótsze per postać.
