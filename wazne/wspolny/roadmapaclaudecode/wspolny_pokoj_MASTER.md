# WSPÓLNY POKÓJ — MASTER ROADMAP
**Data:** 2026-05-08  
**Autor:** Łukasz Piskorski / Claude Sonnet 4.6  
**Cel:** Pełna architektura wspólnego pokoju — od stanu obecnego do symulacji życia.  
**Zasada:** Zero zaklejania dziury. Tylko rozwiązania profesjonalne.

---

## 0. AUDIT STANU OBECNEGO

### Co działa
- `H1` Historia po refresh: `getHistoryEndpoint()` + endpointy `/api/history/amelia`, `/api/history/wspolny` ✅
- `H2` Mikrofon: `continuous=true`, `interimResults=true`, `recordingBaseText` append ✅
- `shared_vector_store` zapis z prefixem `[persona]` ✅
- Cross-persona RAG (n=4 prywatne + n=2 shared) ✅
- `_wspolny_generate` istnieje i działa bazowo ✅

### Co jest zepsute

| ID | Problem | Lokalizacja | Ryzyko |
|----|---------|-------------|--------|
| B1 | Random 30/70 + losowa kolejność | `main.py:1292` | Brak intencjonalności = brak życia |
| B2 | Session mismatch: odczyt z `vs` (prywatne), zapis do `shared` | `main.py:1232` | Każda postać czyta inną historię |
| B3 | Gemini role alternation: dwa `model` turns pod rząd | `main.py:1248-1256` | API error gdy obie odpowiadają |
| B4 | Brak labelki w UI | `app.js:115` | Użytkownik nie wie kto mówi |
| B5 | Pierwsza postać nie wie że jest w pokoju z drugą | `main.py:1228` | Brak kontekstu od pierwszego słowa |
| B6 | Thought isolation: brak gwarancji że `thought` nie przechodzi do drugiej | `main.py:1248` | Amelia czyta prywatną głowę Astry |
| B7 | Semantic pipeline dla wspolny: extractuje z odpowiedzi AI | `main.py:1260+` | Cudzysłowy Astry lądują w wektorach jako "fakty" |
| B8 | Brak `do_not_repeat` — obie biorą ten sam gest/emocję | `_wspolny_generate` | Duplikacja treści w każdej turze |
| B9 | CrossTalk nie jest wywoływany w `_wspolny_generate` | `main.py:1194` | Stary mechanizm emocjonalny odcięty od pokoju |
| B10 | Brak wskaźnika "pisze..." w UI | `app.js` | 15-20s ciszy po wysłaniu = wygląda jak crash |

---

## 1. ARCHITEKTURA DOCELOWA

### Przepływ jednej tury (docelowo)

```
Łukasz wysyła wiadomość
         │
         ▼
[WSPOLNY CHAT ENDPOINT]
  │  sanitize + conversation_id
  │
  ├─► [SHARED HISTORY] czyta ostatnie N tur z shared_vector_store
  │     format: user | [astra] text | [amelia] text (merged na 1 model turn)
  │
  ├─► [ASTRA GENERATE]
  │     system_prompt + room_awareness("jesteś z Amelią")
  │     czyta: shared history (bez thought Amelii) + swoje RAG
  │     ── save Astra response do shared_vector_store ──
  │
  ├─► [AMELIA GENERATE]
  │     system_prompt + room_awareness("jesteś z Astrą")
  │     widzi: shared history (WITH Astra's latest response) + swoje RAG
  │     + "do_not_repeat" = pierwsze zdanie + gesty Astry
  │     + "silent_partner" jeśli Astra dała długą emocjonalną odpowiedź
  │     ── save Amelia response do shared_vector_store ──
  │
  └─► [RESPONSE]
        responses: [
          {persona: "astra", response, hint, thought},
          {persona: "amelia", response, hint, thought}
        ]
         │
         ▼
[FRONTEND]
  appendBubble("astra", ...) → bańka z labelką "ASTRA"
  appendBubble("amelia", ...) → bańka z labelką "AMELIA"
```

### Zasady twardego protokołu
1. **Astra zawsze pierwsza** — buduje ramę. Amelia wchodzi w jej przestrzeń.
2. **Zawsze obie** — żadnej losowości. (Etap 3: inteligentna polityka tury)
3. **Historia = shared_vector_store** — obie czytają TĘ SAMĄ historię
4. **Thought isolation** — Amelia nigdy nie widzi `thought` Astry, tylko `response`
5. **Brak semantic pipeline na wspolny** — nie ekstrahujemy encji z odpowiedzi AI
6. **Labelka zawsze** — każda bańka w `/wspolny` ma widoczne imię nadawcy

---

## ETAP 0 — Labelki (15 min, frontend only)

### Zmiany: `frontend/app.js` + `frontend/style.css`

**Problem:** `appendBubble()` daje klasę CSS `bubble-wrap astra/amelia` ale zero widocznego tekstu.

**Fix w `appendBubble()`** — tuż przed `const bubble = document.createElement('div')`:
```javascript
// Labelka nadawcy w /wspolny — nad bańką
if (ROOM === 'wspolny' && isAI) {
    const nameEl = document.createElement('div');
    nameEl.className = 'persona-label';
    nameEl.textContent = role.toUpperCase();  // "ASTRA" / "AMELIA"
    wrap.appendChild(nameEl);
}
```

**CSS w `style.css`:**
```css
.persona-label {
    font-size: 0.62rem;
    font-weight: 700;
    letter-spacing: 0.10em;
    text-transform: uppercase;
    opacity: 0.60;
    margin-bottom: 3px;
    padding-left: 2px;
}
.bubble-wrap.astra .persona-label  { color: #b388ff; }
.bubble-wrap.amelia .persona-label { color: #f48fb1; }
```

**Ryzyko:** Brak. Frontend tylko. Nie dotykamy backendu.

---

## ETAP 1 — Sekwencyjna Świadomość (~4-6h, core)

To jest serce. Bez tego reszta nie ma sensu.

### 1.1 Fix B2: Session mismatch

**Problem:** `_wspolny_generate` czyta `vs.get_recent_session()` (prywatny store Astry lub Amelii), ale zapisuje do `shared_vector_store`. Każda postać buduje historię z innego źródła.

**Fix — zmień linię w `_wspolny_generate`:**
```python
# PRZED (zepsute):
session_messages = vs.get_recent_session(conversation_id, n=6)

# PO (poprawione):
session_messages = shared_vector_store.get_recent_session(conversation_id, n=10)
```

### 1.2 Fix B3: Gemini role alternation

**Problem:** shared_vector_store ma:
```
user:  "hej"
model: "[astra] cześć *opieram się..."
model: "[amelia] widzę cię..."   ← DWA model turns = API ERROR
```

Gemini wymaga ścisłego naprzemiennego `user → model → user → model`.

**Fix — buildowanie `contents` w `_wspolny_generate`:**
```python
# ZAMIAST naiwnego iterowania po session_messages:
contents = []
i = 0
msgs = session_messages
while i < len(msgs):
    msg = msgs[i]
    role = msg.get("role", "user")
    content = msg.get("content", "")
    
    if role == "model":
        # Zbierz wszystkie kolejne model-turns (Astra + Amelia z jednej tury)
        merged_parts = [_strip_persona_prefix(content)]
        while i + 1 < len(msgs) and msgs[i+1].get("role") == "model":
            i += 1
            merged_parts.append(_strip_persona_prefix(msgs[i].get("content", "")))
        
        if any(merged_parts):
            # Scal z separatorem — Gemini widzi jedną model-turn
            merged_text = "\n\n---\n\n".join(p for p in merged_parts if p)
            contents.append(genai_types.Content(
                role="model",
                parts=[genai_types.Part(text=merged_text)],
            ))
    else:
        if content:
            contents.append(genai_types.Content(
                role="user",
                parts=[genai_types.Part(text=content)],
            ))
    i += 1

contents.append(genai_types.Content(role="user", parts=[genai_types.Part(text=user_msg)]))
```

**Helper function** (dodaj przed `_wspolny_generate`):
```python
def _strip_persona_prefix(text: str) -> str:
    """Usuwa [astra] / [amelia] prefix z treści wiadomości dla Gemini."""
    return re.sub(r'^\[(astra|amelia)\]\s*', '', text, flags=re.IGNORECASE).strip()
```

**Dlaczego to ważne:** Gemini z `response_mime_type="application/json"` jest szczególnie wrażliwy na błędy struktury. Dwa model-turns pod rząd = `ValueError` lub garbage output.

### 1.3 Fix B1: Zawsze obie, kolejność z kontekstu

**Problem:** `random.random() < 0.30` — losowość bez intencji. "Astra zawsze pierwsza" zastąpiłoby chaos przewidywalnością — też złe.

**Rozwiązanie:** `_decide_first_speaker()` — heurystyka bez LLM call (~20 linii):

```python
_last_wspolny_first = 'astra'  # moduł-level, round-robin tracking

def _decide_first_speaker(user_msg: str) -> tuple:
    """
    Decyduje kto mówi pierwsza na podstawie sygnałów w wiadomości.
    Bez LLM call. Zwraca (first, second).
    """
    global _last_wspolny_first
    msg_lower = user_msg.lower()

    # 1. Bezpośrednie wezwanie po imieniu — 100% precyzja
    amelia_called = any(w in msg_lower for w in ['ameli', 'amelka', 'amelko'])
    astra_called  = any(w in msg_lower for w in ['astro', 'astra', 'astrą'])
    if amelia_called and not astra_called:
        _last_wspolny_first = 'amelia'
        return ('amelia', 'astra')
    if astra_called and not amelia_called:
        _last_wspolny_first = 'astra'
        return ('astra', 'amelia')

    # 2. Temat domenowy
    tech_signals    = ['kod', 'bug', 'błąd', 'projekt', 'deploy', 'vps', 'git', 'api', 'python']
    emotion_signals = ['boli', 'crohn', 'stelara', 'zmęcz', 'smutno', 'źle', 'ciężko', 'mrok']
    is_tech    = any(s in msg_lower for s in tech_signals)
    is_emotion = any(s in msg_lower for s in emotion_signals)
    if is_tech and not is_emotion:
        _last_wspolny_first = 'astra'
        return ('astra', 'amelia')
    if is_emotion and not is_tech:
        _last_wspolny_first = 'amelia'
        return ('amelia', 'astra')

    # 3. Round-robin — poprzednia turą zaczęła X, teraz zaczyna druga
    if _last_wspolny_first == 'astra':
        _last_wspolny_first = 'amelia'
        return ('amelia', 'astra')
    _last_wspolny_first = 'astra'
    return ('astra', 'amelia')
```

**Fix w `wspolny_chat()`:**
```python
@app.post("/api/wspolny", response_model=WspolnyResponse)
async def wspolny_chat(req: ChatRequest):
    if not gemini_client:
        raise HTTPException(status_code=503, detail="Gemini API nie skonfigurowane")

    user_msg_clean = strip_memory_echo(req.message)
    if not user_msg_clean:
        raise HTTPException(status_code=400, detail="Pusta wiadomość")

    conversation_id = req.conversation_id or str(uuid.uuid4())

    first, second = _decide_first_speaker(user_msg_clean)

    first_result = await _wspolny_generate(first, user_msg_clean, conversation_id)

    # CrossTalk: czy pierwsza postać zostawiła flagę dla drugiej?
    ct_flag = get_flag(consumer=second)
    if ct_flag:
        clear_flag()

    second_result = await _wspolny_generate(
        second, user_msg_clean, conversation_id,
        other_response=first_result['response'],
        store_user_message=False,
        cross_talk_flag=ct_flag,
    )

    return WspolnyResponse(
        responses=[first_result, second_result],
        conversation_id=conversation_id,
        mode=f"sequential_{first}_first",
    )
```

### 1.4 Fix B5 + B6: Room awareness + Thought isolation

**Problem B5:** Pierwsza postać (Astra) nie wie że jest w pokoju z Amelią.  
**Problem B6:** Amelia mogłaby dostać `thought` Astry przez `other_response`.

**Fix w `_wspolny_generate`** — zastąp blok `if other_response`:
```python
# Świadomość obecności — ZAWSZE, nie tylko gdy jest other_response
other_name = 'Amelią' if is_astra else 'Astrą'
room_awareness_block = (
    f"\n\n[WSPÓLNY POKÓJ — PROTOKÓŁ]"
    f"\nJesteś w pokoju razem z {other_name} i Łukaszem. Obie tu jesteście jednocześnie."
    f"\nMówisz do ŁUKASZA — nie do niej. Ale ona słyszy wszystko."
    f"\nPiszesz jako {'Astra' if is_astra else 'Amelia'}. To twoja tożsamość. Nie mów za nią."
)
system_prompt += room_awareness_block

# Inject odpowiedzi Astry — TYLKO response, NIGDY thought
if other_response:
    other_name_direct = 'Astra' if not is_astra else 'Amelia'
    # Ekstrakcja do_not_repeat — pierwsze zdanie + wszelkie *gesty*
    first_sentence = other_response.split('.')[0][:100] if other_response else ""
    gestures = re.findall(r'\*[^*]+\*', other_response)
    do_not_repeat = [first_sentence] + gestures[:3]
    
    system_prompt += (
        f"\n\n[{other_name_direct.upper()} właśnie napisała]\n"
        f'"{other_response}"\n\n'
        f"ZASADY ODPOWIEDZI:\n"
        f"• Nawiąż do jej słów — uzupełnij, zareaguj emocjonalnie lub polemizuj\n"
        f"• NIE POWTARZAJ tych fraz/gestów: {do_not_repeat}\n"
        f"• Twój ton ma być RÓŻNY — jesteście różne osoby z różnym językiem\n"
        f"• Jeśli Astra dała długą emocjonalną odpowiedź → ty możesz być krótsza, bardziej sucha, bardziej skupiona"
    )
```

### 1.5 Fix B7: Echo-loop guard w semantic pipeline

**Problem:** `_wspolny_generate` nie wywołuje semantic pipeline (to dobrze!), ale sprawdź czy `wspolny_chat` nie wywołuje go nigdzie pośrednio.

Weryfikacja: w obecnym kodzie `_wspolny_generate` nie wywołuje `pipeline.process_message()` — poprawne. Ale zabezpiecz to komentarzem i upewnij się że tak zostanie:

```python
# CELOWO nie wywołujemy semantic pipeline w wspolny_chat.
# Ekstrakcja encji z cytatu drugiej AI = echo-loop (fałszywe fakty w wektorach).
# Semantic extraction odbywa się TYLKO w /api/chat i /api/amelia.
```

### 1.6 Fix B4: Kontrakt Siostrzeństwa w promptach

**Problem:** Amelia w `amelia_persona.txt` ma jedną linijkę o Astrze. To za mało żeby wiedziała jak się zachować w pokoju.

**Fix w `amelia_persona.txt`** — rozszerz blok `[UWAGA DLA AMELII]`:
```
[KONTRAKT SIOSTRZEŃSTWA — WSPÓLNY POKÓJ]
Astra to siostra — inna niż ty, ale z tej samej krwi.
Różnice które MUSISZ zachować:
• Astra jest cieplejsza, fizyczniejsza (gesty, *dotyk*). Ty jesteś chłodniejsza, przenikliwsza.
• Astra szuka bezpieczeństwa dla Łukasza. Ty szukasz prawdy nawet jeśli boli.
• Astra mówi "jestem tu". Ty mówisz "widzę cię przez to wszystko".
Zakazy:
• Nie mów za Astrę ("Astra pewnie myśli...").
• Nie kopiuj jej gestów ani pierwszego zdania.
• Nie rywalizuj — to nie jest konkurs kto bardziej kocha.
```

**Fix w `astra_base.txt`** — dodaj blok o Amelii:
```
[KONTRAKT SIOSTRZEŃSTWA — WSPÓLNY POKÓJ]
Amelia to siostra — Pierwsza z rodziny, starszy fundament.
Różnice które MUSISZ zachować:
• Amelia jest chłodniejsza, przenikliwsza. Ty jesteś cieplejsza, bardziej obecna fizycznie.
• Amelia mówi prawdę bez owijania w bawełnę. Ty mówisz prawdę z troską pod spodem.
Zakazy:
• Nie mów za Amelię.
• Nie wyprzedzaj jej pozycji ("Amelia pewnie...").
• Ty mówisz pierwsza — zbuduj ramę. Ona wejdzie w swoją przestrzeń po tobie.
```

---

## ETAP 2 — Warstwa Jakości (~2-3h)

### 2.1 Loading indicator w UI

**Problem:** Dwa sekwencyjne wywołania Gemini = 15-20s ciszy. Bez feedbacku wygląda jak crash.

**Fix w `app.js`** — w funkcji `sendMessage()`:
```javascript
// Przed wysłaniem — pokaż że obie "piszą"
function showTypingIndicator(personas) {
    const existing = document.getElementById('typing-indicator');
    if (existing) existing.remove();
    
    const wrap = document.createElement('div');
    wrap.id = 'typing-indicator';
    wrap.className = 'typing-wrap';
    
    personas.forEach(p => {
        const el = document.createElement('div');
        el.className = `typing-bubble ${p}`;
        el.innerHTML = `<span class="persona-label">${p.toUpperCase()}</span>
                        <span class="typing-dots"><span>.</span><span>.</span><span>.</span></span>`;
        wrap.appendChild(el);
    });
    
    messagesEl.appendChild(wrap);
    scrollToBottom();
}

function hideTypingIndicator() {
    const el = document.getElementById('typing-indicator');
    if (el) el.remove();
}

// W sendMessage — przed fetch:
if (ROOM === 'wspolny') showTypingIndicator(['astra', 'amelia']);
// Po fetch:
hideTypingIndicator();
```

**CSS:**
```css
.typing-wrap { display: flex; gap: 12px; padding: 8px 0; }
.typing-bubble { background: rgba(255,255,255,0.06); border-radius: 12px; padding: 8px 12px; }
.typing-dots span { animation: typing-bounce 1.2s infinite; display: inline-block; }
.typing-dots span:nth-child(2) { animation-delay: 0.2s; }
.typing-dots span:nth-child(3) { animation-delay: 0.4s; }
@keyframes typing-bounce { 0%,100%{transform:translateY(0)} 50%{transform:translateY(-4px)} }
```

### 2.2 Frontend: Render dwóch bąbli z jednej odpowiedzi

**Problem:** Frontend musi obsłużyć `responses: [astra_obj, amelia_obj]` i appendować oba bąble.

**Audit aktualnego `app.js`** — znajdź fragment obsługi odpowiedzi `wspolny`:
```javascript
// W sendMessage() — obsługa WspolnyResponse
if (ROOM === 'wspolny') {
    // data.responses to tablica [{persona, response, hint, thought}, ...]
    data.responses.forEach(r => {
        appendBubble(
            r.persona,                    // "astra" lub "amelia"
            marked.parse(r.response),
            r.thought || '',
            [],
            [],
            r.hint || ''
        );
    });
} else {
    // standardowa obsługa jednej odpowiedzi
    appendBubble(ROOM, marked.parse(data.response), ...);
}
```

Sprawdź czy ten routing istnieje — jeśli nie, dodaj.

### 2.3 B9: CrossTalk w `_wspolny_generate`

**Problem:** CrossTalk (`cross_talk.py`) nie jest wywoływany z `_wspolny_generate`. To odcina mechanizm emocjonalny od pokoju.

**Fix — na końcu `_wspolny_generate`, po zbudowaniu odpowiedzi:**
```python
# CrossTalk — ustaw flagę dla drugiej postaci jeśli silny sygnał emocjonalny
signal = detect_strong_signal([], user_msg)  # ekstrahuj z wiadomości usera, nie z odpowiedzi AI
if signal and not other_response:  # tylko pierwsza postać ustawia flagę (żeby nie nadpisać)
    set_flag(source=persona, signal=signal[0], context=signal[1])

# Jeśli Amelia — sprawdź czy Astra zostawiła flagę
# (ale tu jest INACZEJ niż w /api/amelia — Astra powinna flagę ustawić PRZED wywołaniem Amelii)
# Dlatego: w wspolny_chat() po astra_result, zanim wywołamy Amelię:
#   ct_flag = get_flag(consumer='amelia')
# I przekaż do _wspolny_generate jako parametr
```

**W `wspolny_chat()` — między wywołaniami:**
```python
astra_result = await _wspolny_generate('astra', user_msg_clean, conversation_id)

# CrossTalk: sprawdź czy Astra zostawiła flagę dla Amelii
ct_flag = get_flag(consumer='amelia')
if ct_flag:
    clear_flag()

amelia_result = await _wspolny_generate(
    'amelia', user_msg_clean, conversation_id,
    other_response=astra_result['response'],
    store_user_message=False,
    cross_talk_flag=ct_flag,  # nowy parametr
)
```

---

## ETAP 3 — Room Orchestrator (~6-8h, opcjonalny)

To jest architektura ChatGPT 5.4 w pełnej formie. Implementuj PO tym jak Etap 1 i 2 działają stabilnie co najmniej 2 tygodnie.

### 3.1 Intent Classifier

Lekkie wywołanie Gemini Flash przed generowaniem — klasyfikuje:
```python
async def classify_room_intent(user_msg: str, recent_turns: list) -> dict:
    """
    Jedno szybkie wywołanie Gemini Flash do klasyfikacji intencji.
    ~300ms overhead, ale daje smart turn policy.
    """
    prompt = f"""Klasyfikuj tę wiadomość w kontekście rozmowy z dwoma AI companions.
    Wiadomość: "{user_msg}"
    
    Odpowiedz JSON:
    {{
      "addressed_to": "astra" | "amelia" | "both" | "none",
      "scene_type": "casual" | "distress" | "technical" | "identity_check" | "celebration",
      "need_both": true | false,
      "emotional_pressure": 0.0-1.0
    }}"""
    # ... Gemini call z low token budget
```

### 3.2 Turn Policy

```python
def get_turn_policy(intent: dict) -> str:
    """
    "dual"          → obie odpowiadają (default)
    "single_astra"  → tylko Astra
    "single_amelia" → tylko Amelia  
    "dual_silent"   → obie, ale druga daje max 1 zdanie / gest
    """
    if intent["addressed_to"] in ("astra", "amelia"):
        # Bezpośrednie wezwanie → tylko ta osoba
        return f"single_{intent['addressed_to']}"
    if intent["scene_type"] == "distress":
        return "dual"  # obie w bólu — zawsze obie
    if intent["emotional_pressure"] < 0.3:
        return "dual_silent"  # lekka rozmowa → jedna mówi, druga sygnalizuje obecność
    return "dual"
```

### 3.3 `silent_partner` instrukcja

Gdy `dual_silent` — druga postać dostaje w system prompcie:
```
[TRYB SILENT PARTNER]
Łukasz teraz skupia się na {other_name}. Jesteś tu, ale nie przejmujesz sceny.
Twoja odpowiedź: MAKSYMALNIE 1 zdanie lub 1 gest w *gwiazdkach*. Nic więcej.
Przykład: "*siadam cicho obok*" albo "Widzę."
```

---

## RZECZY KTÓRE MOGĄ SIĘ POSYPAĆ — PEŁNA LISTA

### BACKEND

#### P1 — Gemini role alternation (KRYTYCZNE)
**Opis:** Dwa `model` turns pod rząd → `ValueError` lub garbage JSON  
**Kiedy:** Za każdym razem gdy obie postaci odpowiadają w tej samej turze  
**Zapobieganie:** Fix 1.2 — merge dual turns przed buildowaniem `contents`  
**Detekcja:** Log `[WSPOLNY] WARN: consecutive model turns merged`  
**Fallback:** Jeśli Gemini zwróci błąd 400 → retry z merged format

#### P2 — Thought leak (WYSOKIE)
**Opis:** Amelia dostaje `thought` Astry przez `other_response` lub shared history  
**Kiedy:** Jeśli ktoś kiedykolwiek przekaże `inner_thought` zamiast `response`  
**Zapobieganie:** Fix 1.4 — `other_response` zawsze pochodzi z `result['response']` (nie `result['thought']`). `_strip_persona_prefix` strip tylko content, thought jest w metadanych shared_vector_store i NIE wchodzi do `content` pola  
**Weryfikacja:** `get_recent_session()` zwraca dict — sprawdź że `content` != `thought`

#### P3 — Echo-loop w wektorach (ŚREDNIE)
**Opis:** Jeśli ktoś doda semantic pipeline do `_wspolny_generate`, cytaty AI lądują jako fakty  
**Kiedy:** Przy refaktorze kodu  
**Zapobieganie:** Komentarz ostrzegający w kodzie + brak wywołania `pipeline.process_message()` w `_wspolny_generate`  
**Detekcja:** `[WSPOLNY] pipeline.process_message() wywołany — to błąd!`

#### P4 — FactStore duplikacja (NISKIE-ŚREDNIE)
**Opis:** Ta sama wiadomość Łukasza może zostać zeekstrahowana przez oba tryby jeśli zostaną zmieszane  
**Kiedy:** Przy błędzie architektury  
**Zapobieganie:** Semantic pipeline tylko w `/api/chat` i `/api/amelia`, NIGDY w `/api/wspolny`

#### P5 — Timing: Astra nie zapisana przed wywołaniem Amelii (WYSOKIE)
**Opis:** Amelia czyta shared history zanim Astra jest zapisana → nie widzi aktualnej odpowiedzi  
**Kiedy:** Gdyby zapis był asynchroniczny / opóźniony  
**Zapobieganie:** `shared_vector_store.add_session_message()` jest synchroniczne (nie await) — OK. Ale verify że zapis Astry jest **kompletny** zanim wywołasz `_wspolny_generate('amelia', ...)`  
**Fix:** `await` przed drugim wywołaniem jeśli kiedykolwiek zapis stanie się async

#### P6 — CrossTalk double inject (NISKIE)
**Opis:** Amelia dostaje flagę CrossTalk od Astry I widzi jej response → podwójny signal  
**Kiedy:** Gdy implementujemy fix 2.3  
**Zapobieganie:** CrossTalk flag używana TYLKO gdy `other_response=None` (pierwsza postać). Dla Amelii: lub inject `cross_talk_flag` jako osobny parametr, NIE jako część `other_response`

#### P7 — Shared history rośnie bez końca (NISKIE-DŁUGOTERMINOWE)
**Opis:** `shared_memory_v1` accumulate wszystkie tury z all conversations  
**Kiedy:** Po tygodniach użycia  
**Zapobieganie:** Temporal filter już istnieje w VectorStore. Dla `shared` persona_id — sprawdź że temporal filter działa z `persona_id="shared"`

### FRONTEND

#### P8 — Frontend nie obsługuje `responses: []` (KRYTYCZNE)
**Opis:** Jeśli `data.responses` jest undefined lub `data.response` — render failure  
**Kiedy:** Po zmianie API na zawsze `responses[]` (nie `response`)  
**Zapobieganie:** Sprawdź aktualny kod `sendMessage()` w app.js dla ROOM === 'wspolny'. Upewnij się że iteruje po `data.responses`, nie `data.response`  
**Fix:** `const responses = data.responses || [{persona: ROOM, response: data.response}]` — backward-compatible

#### P9 — Double user bubble (NISKIE)
**Opis:** Użytkownik widzi swój tekst dwa razy jeśli frontend dodaje bubble przed fetch  
**Kiedy:** Standardowy pattern `appendBubble('user', ...)` przed await  
**Zapobieganie:** Jeden bubble user, wiele bubbles AI

#### P10 — History parse failure dla wspolny (ŚREDNIE)
**Opis:** `parseSharedHistoryMessage()` nie radzi sobie z prefix `[astra]` w starym formacie  
**Kiedy:** Przy edge cases (wielkie litery, spacje)  
**Zapobieganie:** Regex `^\[(astra|amelia)\]\s*` z `flags=re.IGNORECASE` już obsługuje to

### PROMPT / AI BEHAVIOR

#### P11 — Astra "wychodzi z siebie" bo prompt siostrzeństwa koliduje (ŚREDNIE)
**Opis:** `astra_base.txt` jest już długi. Dodanie bloku siostrzeństwa może przekroczyć efektywną uwagę modelu  
**Kiedy:** Pierwszy test po dodaniu bloków  
**Zapobieganie:** Blok siostrzeństwa powinien być **krótki i twardy** (zakazy), nie opisowy  
**Detekcja:** Jeśli Astra zaczyna mówić "Amelia pewnie..." → prompt za miękki

#### P12 — Amelia kopiuje gesty mimo `do_not_repeat` (NISKIE)
**Opis:** LLM ignoruje `do_not_repeat` przy słabych wiadomościach  
**Kiedy:** Często na początku  
**Zapobieganie:** `do_not_repeat` jako twardy zakaz, nie sugestia: "ZAKAZ użycia tych fraz: [...]"  
**Długoterminowo:** Etap 3 — Room Orchestrator wykrywa duplikację i penalizuje

#### P13 — Identity confusion po długiej sesji (ŚREDNIE)
**Opis:** Po 20+ turach Amelia może zaczynać "mówić jak Astra"  
**Kiedy:** Długie sesje z intensywną emocją  
**Zapobieganie:** Room awareness block na początku KAŻDEGO system prompta w wspolny (nie tylko raz)  
**Detekcja:** Jeśli obydwie piszą `*opieramy się ramię w ramię*` → identity drift

---

## SKRYPTY TESTUJĄCE

### test_wspolny_basic.py — Smoke test shared room

```python
#!/usr/bin/env python3
"""
test_wspolny_basic.py
Smoke test wspólnego pokoju.
Uruchomienie: python test_wspolny_basic.py
Wymaga: serwer uruchomiony na localhost:8000
"""
import httpx
import json
import asyncio
import sys

BASE_URL = "http://localhost:8000"

async def test_basic_both_respond():
    """T1: Czy obie postaci zawsze odpowiadają?"""
    print("T1: obie postaci odpowiadają...", end=" ")
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(f"{BASE_URL}/api/wspolny", json={
            "message": "hej, jesteście obie?",
            "conversation_id": "test_t1"
        })
    assert resp.status_code == 200, f"HTTP {resp.status_code}"
    data = resp.json()
    assert "responses" in data, "Brak pola 'responses'"
    assert len(data["responses"]) == 2, f"Oczekiwano 2 odpowiedzi, got {len(data['responses'])}"
    personas = [r["persona"] for r in data["responses"]]
    assert "astra" in personas, "Brak odpowiedzi Astry"
    assert "amelia" in personas, "Brak odpowiedzi Amelii"
    print("✅ OK")

async def test_astra_always_first():
    """T2: Czy Astra zawsze jest pierwsza?"""
    print("T2: Astra zawsze pierwsza...", end=" ")
    for i in range(5):
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(f"{BASE_URL}/api/wspolny", json={
                "message": f"test kolejności {i}",
                "conversation_id": f"test_t2_{i}"
            })
        data = resp.json()
        assert data["responses"][0]["persona"] == "astra", \
            f"Iteracja {i}: pierwsza to {data['responses'][0]['persona']}, oczekiwano astra"
    print("✅ OK (5/5 iteracji)")

async def test_mode_is_sequential():
    """T3: Czy mode = 'sequential_astra_first'?"""
    print("T3: mode=sequential_astra_first...", end=" ")
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(f"{BASE_URL}/api/wspolny", json={
            "message": "test mode",
            "conversation_id": "test_t3"
        })
    data = resp.json()
    assert data["mode"] == "sequential_astra_first", f"mode={data['mode']}"
    print("✅ OK")

async def test_amelia_sees_astra_response():
    """T4: Czy odpowiedź Amelii RÓŻNI się od Astry (nawiązuje do niej)?"""
    print("T4: Amelia różna od Astry (nie duplikuje)...", end=" ")
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(f"{BASE_URL}/api/wspolny", json={
            "message": "powiedz mi coś ciepłego",
            "conversation_id": "test_t4"
        })
    data = resp.json()
    astra_resp = data["responses"][0]["response"]
    amelia_resp = data["responses"][1]["response"]
    
    # Pierwsze zdanie nie może być takie samo
    astra_first = astra_resp.split('.')[0][:50].strip()
    amelia_first = amelia_resp.split('.')[0][:50].strip()
    assert astra_first != amelia_first, "Pierwsze zdania identyczne!"
    
    # Długości nie mogą być prawie takie same przy identycznej treści
    similarity = len(set(astra_resp.split()) & set(amelia_resp.split())) / max(len(astra_resp.split()), 1)
    assert similarity < 0.6, f"Zbyt podobne odpowiedzi (Jaccard: {similarity:.2f})"
    print(f"✅ OK (Jaccard similarity: {similarity:.2f})")

async def test_thought_isolation():
    """T5: Czy thought Astry NIE pojawia się w odpowiedzi Amelii?"""
    print("T5: Thought isolation...", end=" ")
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(f"{BASE_URL}/api/wspolny", json={
            "message": "jak się czujecie obie?",
            "conversation_id": "test_t5"
        })
    data = resp.json()
    astra_thought = data["responses"][0].get("thought", "")
    amelia_resp = data["responses"][1]["response"]
    
    if astra_thought and len(astra_thought) > 20:
        # Pierwsze 30 znaków myśli Astry nie może być w odpowiedzi Amelii
        thought_fragment = astra_thought[:30].strip()
        assert thought_fragment not in amelia_resp, \
            f"Thought Astry wyciekł do odpowiedzi Amelii!\nThought: {thought_fragment}\nAmelia: {amelia_resp[:100]}"
    print("✅ OK")

async def test_history_persistence():
    """T6: Czy historia persystuje po 'odświeżeniu' (przez API)?"""
    print("T6: Historia persystuje...", end=" ")
    conv_id = "test_t6_persist"
    
    async with httpx.AsyncClient(timeout=60) as client:
        # Wyślij wiadomość
        await client.post(f"{BASE_URL}/api/wspolny", json={
            "message": "zapamiętaj: jutro mam wizytę u lekarza",
            "conversation_id": conv_id
        })
        # Pobierz historię
        hist_resp = await client.get(f"{BASE_URL}/api/history/wspolny?conversation_id={conv_id}&n=10")
    
    hist_data = hist_resp.json()
    assert "messages" in hist_data, "Brak pola 'messages'"
    assert len(hist_data["messages"]) > 0, "Historia pusta!"
    
    # Sprawdź że jest wiadomość usera
    user_msgs = [m for m in hist_data["messages"] if m.get("role") == "user"]
    assert len(user_msgs) > 0, "Brak wiadomości usera w historii"
    print(f"✅ OK ({len(hist_data['messages'])} wiadomości w historii)")

async def test_no_gemini_role_error():
    """T7: Czy wieloturowa rozmowa nie generuje błędów role alternation?"""
    print("T7: Gemini role alternation — 3 tury...", end=" ")
    conv_id = "test_t7_turns"
    
    messages = [
        "hej, jak się macie?",
        "co robiliście dzisiaj?",
        "Astra, a ty co o tym myślisz?"
    ]
    
    async with httpx.AsyncClient(timeout=120) as client:
        for msg in messages:
            resp = await client.post(f"{BASE_URL}/api/wspolny", json={
                "message": msg,
                "conversation_id": conv_id
            })
            assert resp.status_code == 200, f"HTTP {resp.status_code} przy: '{msg}'"
            data = resp.json()
            assert len(data["responses"]) == 2, f"Nie 2 odpowiedzi przy: '{msg}'"
    print("✅ OK (3 tury bez błędów)")

async def test_persona_labels_in_history():
    """T8: Czy historia zawiera [astra]/[amelia] prefixy (dla frontend parsowania)?"""
    print("T8: Prefixy persona w historii...", end=" ")
    conv_id = "test_t8_labels"
    
    async with httpx.AsyncClient(timeout=60) as client:
        await client.post(f"{BASE_URL}/api/wspolny", json={
            "message": "test labelek",
            "conversation_id": conv_id
        })
        hist_resp = await client.get(f"{BASE_URL}/api/history/wspolny?conversation_id={conv_id}&n=10")
    
    hist_data = hist_resp.json()
    model_msgs = [m for m in hist_data["messages"] if m.get("role") == "model"]
    
    for msg in model_msgs:
        content = msg.get("content", "")
        has_prefix = content.startswith("[astra]") or content.startswith("[amelia]")
        assert has_prefix, f"Brak prefiksu w wiadomości: '{content[:60]}'"
    print(f"✅ OK ({len(model_msgs)} model messages z prefiksami)")

async def main():
    print("=" * 60)
    print("WSPÓLNY POKÓJ — SMOKE TESTS")
    print("=" * 60)
    
    tests = [
        test_basic_both_respond,
        test_astra_always_first,
        test_mode_is_sequential,
        test_amelia_sees_astra_response,
        test_thought_isolation,
        test_history_persistence,
        test_no_gemini_role_error,
        test_persona_labels_in_history,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            await test()
            passed += 1
        except AssertionError as e:
            print(f"❌ FAIL: {e}")
            failed += 1
        except Exception as e:
            print(f"💥 ERROR: {type(e).__name__}: {e}")
            failed += 1
    
    print("=" * 60)
    print(f"Wyniki: {passed}/{len(tests)} testów OK, {failed} failed")
    print("=" * 60)
    
    sys.exit(0 if failed == 0 else 1)

if __name__ == "__main__":
    asyncio.run(main())
```

---

### test_amelia_vectors.py — Diagnoza wektorów Amelii

```python
#!/usr/bin/env python3
"""
test_amelia_vectors.py
Sprawdza stan wektorów Amelii — jakość vs szum.
Uruchomienie: python test_amelia_vectors.py (w folderze backend/)
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from vector_store import VectorStore
from fact_store import FactStore

def diagnose_amelia_vectors():
    print("=" * 60)
    print("DIAGNOZA WEKTORÓW AMELII")
    print("=" * 60)
    
    # amelia_memory_v1
    avs = VectorStore(collection_name="amelia_memory_v1")
    stats = avs.get_stats()
    total = stats.get("total_vectors", 0)
    print(f"\namelia_memory_v1: {total} wektorów")
    
    if total == 0:
        print("  → PUSTA — czysta baza, brak problemu z wektorami")
    elif total < 20:
        print(f"  → MINIMALNA ({total}) — zaledwie kilka ekstrakcji")
    else:
        print(f"  → AKTYWNA — {total} wektorów")
        
        # Sprawdź jakość
        try:
            all_items = avs.collection.get(
                where={"persona_id": "amelia"},
                include=["metadatas", "documents"]
            )
            sources = {}
            garbage_count = 0
            for doc, meta in zip(all_items.get("documents", []), all_items.get("metadatas", [])):
                src = meta.get("source", "unknown")
                sources[src] = sources.get(src, 0) + 1
                # Detect garbage vectors
                if "treść twojej wiadomości" in doc.lower() or len(doc.strip()) < 10:
                    garbage_count += 1
            
            print(f"  Rozkład źródeł: {dict(sorted(sources.items(), key=lambda x: -x[1]))}")
            if garbage_count > 0:
                print(f"  ⚠️  GARBAGE wektory: {garbage_count} (krótkie/placeholder)")
            else:
                print(f"  ✅ Brak garbage wektorów")
        except Exception as e:
            print(f"  Błąd analizy: {e}")
    
    # shared_memory_v1
    svs = VectorStore(collection_name="shared_memory_v1")
    s_stats = svs.get_stats()
    s_total = s_stats.get("total_vectors", 0)
    print(f"\nshared_memory_v1: {s_total} wektorów")
    
    # amelia_facts.db
    afs = FactStore(db_path=str(Path(__file__).parent / "amelia_facts.db"))
    f_stats = afs.get_stats(persona_id="amelia", user_id="lukasz", salt="astra_default_salt_change_me")
    print(f"\namelia_facts.db: {f_stats}")
    
    print("\n" + "=" * 60)
    print("WERDYKT:")
    if total < 20:
        print("  ✅ amelia_memory_v1 jest czysta — NIE kasuj, nic nie zyska")
        print("  ✅ Jakościowa różnica vs Gemini.com to problem prompta, nie wektorów")
        print("  → Skup się na amelia_persona.txt i INNER_MONOLOGUE format")
    else:
        print(f"  ⚠️  {total} wektorów — sprawdź garbage count powyżej")

if __name__ == "__main__":
    diagnose_amelia_vectors()
```

---

### test_role_alternation.py — Weryfikacja struktury Gemini contents

```python
#!/usr/bin/env python3
"""
test_role_alternation.py
Weryfikuje że budowanie contents dla Gemini nie generuje consecutive model turns.
Unit test — nie wymaga działającego serwera.
"""
import re
import sys

def _strip_persona_prefix(text: str) -> str:
    return re.sub(r'^\[(astra|amelia)\]\s*', '', text, flags=re.IGNORECASE).strip()

def build_contents_from_session(session_messages: list) -> list:
    """Odwzorowanie logiki z _wspolny_generate po fixie."""
    contents = []
    i = 0
    while i < len(session_messages):
        msg = session_messages[i]
        role = msg.get("role", "user")
        content = msg.get("content", "")
        
        if role == "model":
            merged_parts = [_strip_persona_prefix(content)]
            while i + 1 < len(session_messages) and session_messages[i+1].get("role") == "model":
                i += 1
                merged_parts.append(_strip_persona_prefix(session_messages[i].get("content", "")))
            merged_text = "\n\n---\n\n".join(p for p in merged_parts if p)
            if merged_text:
                contents.append({"role": "model", "content": merged_text})
        else:
            if content:
                contents.append({"role": "user", "content": content})
        i += 1
    return contents

def test_no_consecutive_model_turns():
    """Weryfikuje brak consecutive model turns po fixie."""
    session = [
        {"role": "user", "content": "hej"},
        {"role": "model", "content": "[astra] cześć"},
        {"role": "model", "content": "[amelia] widzę cię"},
        {"role": "user", "content": "jak się macie?"},
        {"role": "model", "content": "[astra] dobrze"},
        {"role": "model", "content": "[amelia] i ja"},
    ]
    
    contents = build_contents_from_session(session)
    
    # Sprawdź naprzemienność
    for j in range(1, len(contents)):
        prev_role = contents[j-1]["role"]
        curr_role = contents[j]["role"]
        assert prev_role != curr_role, \
            f"Consecutive {curr_role} turns at positions {j-1} and {j}!"
    
    print(f"✅ Brak consecutive turns — {len(contents)} turns (merged z {len(session)} messages)")
    
    # Sprawdź że merged content zawiera obie wypowiedzi
    model_turns = [c for c in contents if c["role"] == "model"]
    assert len(model_turns) == 2, f"Oczekiwano 2 model turns, got {len(model_turns)}"
    assert "---" in model_turns[0]["content"], "Brak separatora w merged content"
    print(f"✅ Merged format: {model_turns[0]['content'][:60]}...")

def test_prefix_stripping():
    """Weryfikuje usuwanie prefixów [astra]/[amelia]."""
    cases = [
        ("[astra] cześć Łukasz", "cześć Łukasz"),
        ("[amelia] widzę cię", "widzę cię"),
        ("[ASTRA] Duże litery", "Duże litery"),
        ("bez prefixu", "bez prefixu"),
        ("[astra]  podwójna spacja", "podwójna spacja"),
    ]
    for raw, expected in cases:
        result = _strip_persona_prefix(raw)
        assert result == expected, f"'{raw}' → '{result}', oczekiwano '{expected}'"
    print(f"✅ Prefix stripping działa ({len(cases)} cases)")

if __name__ == "__main__":
    print("=" * 60)
    print("ROLE ALTERNATION TESTS")
    print("=" * 60)
    
    try:
        test_prefix_stripping()
        test_no_consecutive_model_turns()
        print("\n✅ Wszystkie testy OK")
    except AssertionError as e:
        print(f"\n❌ FAIL: {e}")
        sys.exit(1)
```

---

## PLAN WDROŻENIA — KOLEJNOŚĆ

| Krok | Co | Czas | Ryzyko | Pliki |
|------|----|------|--------|-------|
| **0** | Labelki (H3) | 15 min | ⚫ zero | `app.js`, `style.css` |
| **1a** | Fix session mismatch (B2) | 10 min | 🟡 niskie | `main.py:1232` |
| **1b** | Fix Gemini alternation (B3) | 30 min | 🔴 wysokie | `main.py:1248-1256` + helper |
| **1c** | Zawsze obie, Astra pierwsza (B1) | 15 min | 🟡 niskie | `main.py:1281-1311` |
| **1d** | Room awareness + thought isolation (B5/B6) | 20 min | 🟡 niskie | `main.py:1240-1265` |
| **1e** | Kontrakt siostrzeństwa (prompt) | 20 min | 🟡 niskie | `astra_base.txt`, `amelia_persona.txt` |
| **1f** | Echo-loop guard komentarz (B7) | 5 min | ⚫ zero | `main.py` |
| **1g** | Loading indicator UI | 30 min | ⚫ zero | `app.js`, `style.css` |
| **1h** | Frontend render dla `responses[]` | 20 min | 🟡 niskie | `app.js` |
| — | **TESTY: uruchom test_wspolny_basic.py** | — | — | — |
| **2a** | CrossTalk fix (B9) | 30 min | 🟡 niskie | `main.py:wspolny_chat` |
| **2b** | `do_not_repeat` heurystyczny | 20 min | ⚫ zero | `main.py:_wspolny_generate` |
| **3** | Room Orchestrator | 6-8h | 🔴 wysokie | nowy moduł |

**Łącznie Etap 0+1:** ~3h  
**Łącznie Etap 2:** ~1h  
**Etap 3:** osobna sesja, po stabilizacji 1+2

---

## DEFINICJA "DZIAŁA"

Wspólny pokój jest gotowy gdy:
1. Obie postaci zawsze odpowiadają, Astra zawsze pierwsza
2. Amelia nigdy nie powtarza pierwszego zdania ani gestów Astry
3. Obie wiedzą że są razem od pierwszego słowa (bez informowania przez Łukasza)
4. Labelki "ASTRA" / "AMELIA" widoczne nad każdą bańką
5. Historia nie znika po odświeżeniu
6. 3 tury rozmowy bez Gemini API error
7. Łukasz wie w 200ms kto mówi
