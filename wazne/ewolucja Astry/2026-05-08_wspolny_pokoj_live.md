# Wspólny Pokój — pełna implementacja (Etap 0+1+2)
**Data:** 2026-05-08  
**Sesja z:** GitHub Copilot (Claude Sonnet 4.6, VS Code)  
**Pliki zmienione:** `backend/main.py`, `frontend/app.js`, `frontend/style.css`, `backend/prompts/astra_base.txt`, `backend/prompts/amelia_persona.txt`  
**Roadmapa źródłowa:** `wazne/wspolny/roadmapaclaudecode/wspolny_pokoj_MASTER.md`

---

## 1. CONTEXT

### Trigger
Wspólny pokój (`/api/wspolny`) istniał w kodzie, ale był zepsuty na wielu poziomach jednocześnie:
- Losowość zamiast intencji — `random.random() < 0.30` decydował czy obie odpowiadają
- Gemini API crashował przy każdym wspólnym pokoju (dwa `model` turny pod rząd = błąd API)
- Historia sesji czytana z prywatnego store Astry zamiast wspólnego
- Brak labełek — użytkownik nie wiedział kto mówi
- Prompty nie wiedziały że są razem w pokoju
- Kolejność zawsze losowa, bez żadnej logiki

Poprzednia sesja (2026-04-27) naprawiła H1 (historia przeżywa odświeżenie) i H2 (mikrofon ciągły). Ta sesja to Etap 0+1+2 roadmapy wspólnego pokoju.

### Architektura wspólnego pokoju (stan przed)
```
POST /api/wspolny
  → 30% szans że obie odpowiadają
  → losowa kolejność
  → każda czyta własną historię sesji (VS private)
  → Gemini dostaje [astra_turn, amelia_turn] = dwa model turny = CRASH
  → brak kontekstu "jesteście razem"
  → brak labelek w UI
```

### Architektura wspólnego pokoju (stan po)
```
POST /api/wspolny
  → ZAWSZE obie odpowiadają
  → kolejność: signal-based (imię > temat > round-robin)
  → obie czytają shared_vector_store
  → Gemini dostaje poprawnie alternatywne user/model turny (merge)
  → system prompt zawiera [WSPÓLNY POKÓJ — PROTOKÓŁ]
  → druga postać widzi odpowiedź pierwszej, ale nie może jej kopiować
  → labelki ASTRA / AMELIA nad każdą bańką w UI
```

---

## 2. FIXES

---

### Fix B1 — Signal-based ordering zamiast random
**Plik:** `backend/main.py` — nowa funkcja `_decide_first_speaker()`

#### Problem
`random.random() < 0.30` — losowość bez intencji. 70% szans że tylko jedna odpowiada, kolejność też losowa. Pokój nie żył.

#### Zmiana
Nowa funkcja (~45 linii) bez żadnego LLM call. Trzypoziomowy priorytet:

```python
def _decide_first_speaker(user_msg: str) -> tuple:
    # 1. Bezpośrednie wezwanie po imieniu — 100% precyzja
    #    "Amelka co myślisz?" → ('amelia', 'astra')
    #    "Astra powiedz mi" → ('astra', 'amelia')

    # 2. Temat domenowy
    #    tech_signals (kod, bug, deploy...) → Astra pierwsza
    #    emotion_signals (boli, crohn, zmęcz...) → Amelia pierwsza

    # 3. Round-robin — poprzednia tura zaczęła X, teraz zaczyna druga
```

`wspolny_chat()` całkowicie przepisane — żadnego `random`, zawsze obie postaci odpowiadają.

---

### Fix B2 — Session store mismatch
**Plik:** `backend/main.py` — `_wspolny_generate()`

#### Problem
```python
# PRZED:
session_messages = vs.get_recent_session(conversation_id, n=6)
# vs = vector_store (prywatny Astry) lub amelia_vector_store
# Amelia czytała swoją historię, Astra swoją — zupełnie różne konteksty
```

#### Zmiana
```python
# PO:
session_messages = shared_vector_store.get_recent_session(conversation_id, n=10)
# obie czytają tę samą historię wspólnego pokoju
```

---

### Fix B3 — Gemini role alternation (KRYTYCZNY)
**Plik:** `backend/main.py` — `_wspolny_generate()`

#### Problem
Astra odpowiada → zapis jako `model`. Amelia odpowiada → zapis jako `model`.  
Przy następnym requeście historia wygląda: `user → model[astra] → model[amelia] → user`.  
Dwa kolejne `model` turny = **Gemini API error**. Endpoint crashował po pierwszej wymianie.

#### Zmiana
Zastąpiono proste `for msg in session_messages` logiką mergowania:

```python
# Merge consecutive model turns — separator "---"
# [astra] Hej Łukasz...
# [amelia] Widzę to inaczej...
# ↓ merge w jeden turn:
# "Hej Łukasz...\n\n---\n\nWidzę to inaczej..."

# _strip_persona_prefix() usuwa [astra]/[amelia] prefix przed wysłaniem do Gemini
```

Nowa helper function `_strip_persona_prefix()` usuwa prefix `[astra]`/`[amelia]` (który jest w bazie jako identyfikator) zanim tekst trafi jako content do Gemini.

---

### Fix B5 — Room awareness block
**Plik:** `backend/main.py` — `_wspolny_generate()`

#### Problem
Postać nie wiedziała że jest w pokoju z drugą. Prompty były identyczne jak w prywatnej sesji.

#### Zmiana
Blok zawsze dodawany do system prompta, przed historią sesji:
```
[WSPÓLNY POKÓJ — PROTOKÓŁ]
Jesteś w pokoju razem z {Amelią/Astrą} i Łukaszem. Obie tu jesteście jednocześnie.
Mówisz do ŁUKASZA — nie do niej. Ale ona słyszy wszystko.
Piszesz jako {Astra/Amelia}. To twoja tożsamość. Nie mów w jej imieniu.
```

---

### Fix B6 — Thought isolation
**Plik:** `backend/main.py` — `_wspolny_generate()`

#### Problem
Gdyby `thought` (prywatna głowa Astry z JSON response) trafiał do prompta Amelii — byłoby to naruszenie hermetyczności. Mógłby też tworzyć echo-loop.

#### Zmiana
Do drugiej postaci trafia wyłącznie `other_response` (finalna odpowiedź), **nigdy** `thought`. Thought pozostaje prywatne — widoczne tylko użytkownikowi w UI jako collapsible.

---

### Fix B7 — Echo-loop guard
**Plik:** `backend/main.py` — `_wspolny_generate()`

#### Problem
Gdyby `_wspolny_generate` wywoływał `pipeline.process_message()` (semantic extraction), cytaty z odpowiedzi drugiej AI trafiałyby do bazy jako "fakty o Łukaszu". Słowa Astry o Łukaszu w ustach Amelii = zatrucie bazy.

#### Zmiana
Semantic pipeline (`pipeline.process_message()`) celowo **nie jest wywoływany** w `_wspolny_generate`. Ekstrakcja encji tylko w `/api/chat` i `/api/amelia`. Komentarz w kodzie:
```python
# Fix B7: Celowo NIE wywołujemy semantic pipeline w wspolny.
# Ekstrakcja encji z cytatu drugiej AI = echo-loop (cudze słowa jako "fakty" Łukasza).
```

---

### Fix B8 — Do-not-repeat heuristic
**Plik:** `backend/main.py` — `_wspolny_generate()`

#### Problem
Druga postać mogła użyć dokładnie tego samego pierwszego zdania i gestów co pierwsza. Pokój brzmiał jakby mówiła jedna osoba.

#### Zmiana
Do system prompta drugiej postaci trafia lista zakazanych fraz:
```python
first_sentence = other_response.split('.')[0][:100]
gestures = re.findall(r'\*[^*]+\*', other_response)  # *gesty w gwiazdkach*
do_not_repeat = [first_sentence] + gestures[:3]
# → ZAKAZ użycia tych fraz/gestów: "Hej..." | "*opiera się*"
```

---

### Fix B9 — CrossTalk integration
**Plik:** `backend/main.py` — `wspolny_chat()`

#### Problem
CrossTalk (system flagowania sygnałów między postacami) istniał dla prywatnych pokojów (`/api/chat`, `/api/amelia`), ale `wspolny_chat()` go całkowicie ignorował.

#### Zmiana
Przed każdym `_wspolny_generate` sprawdzane są flagi CrossTalk:
```python
ct_first  = get_flag(consumer=first)
if ct_first:
    clear_flag()
first_result = await _wspolny_generate(first, ..., cross_talk_flag=ct_first)

ct_second = get_flag(consumer=second)
...
```

`_wspolny_generate` dostał parametr `cross_talk_flag=None`. Astra dostaje inject przez `build_cross_talk_block()`, Amelia przez istniejący parametr w `build_amelia_system_prompt()`.

---

### Fix H3/B4 — Persona labels w UI
**Plik:** `frontend/app.js`, `frontend/style.css`

#### Problem
W pokoju wspólnym bańki Astry i Amelii były wizualnie różne (kolory), ale nie było żadnego napisu kto mówi. Użytkownik musiał zgadywać z kontekstu.

#### Zmiana `app.js`
```javascript
// W appendBubble() — tylko dla ROOM === 'wspolny'
if (ROOM === 'wspolny' && isAI) {
    const nameEl = document.createElement('div');
    nameEl.className = 'persona-label';
    nameEl.textContent = role.toUpperCase();  // "ASTRA" lub "AMELIA"
    wrap.appendChild(nameEl);
}
```

#### Zmiana `style.css`
```css
.persona-label {
    font-size: 0.60rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    opacity: 0.60;
    margin-bottom: 3px;
}
.bubble-wrap.astra  .persona-label { color: #b388ff; }  /* fiolet */
.bubble-wrap.amelia .persona-label { color: #f48fb1; }  /* róż */
```

---

### Fix B10 — Typing indicator dla obu postaci
**Plik:** `frontend/app.js` — `showTyping()`

#### Problem
`showTyping()` zawsze pokazywał jeden wskaźnik "pisze..." z klasą `bubble-wrap astra`. W pokoju wspólnym oczekujemy odpowiedzi obu.

#### Zmiana
```javascript
const personas = ROOM === 'wspolny' ? ['astra', 'amelia'] : [ROOM];
personas.forEach(p => {
    // tworzy osobny wrap z labelką i dots dla każdej postaci
    // labelka widoczna też w trakcie pisania
});
```

---

### Prompty — Dynamika pokoju
**Pliki:** `backend/prompts/astra_base.txt`, `backend/prompts/amelia_persona.txt`

#### Problem (v1 — "Kontrakt Siostrzeństwa")
Poprzednia wersja:
- Nazywała Amelię "siostrą z tej samej krwi" — dosłownie nieprawda, mylące
- Historia była odwrócona — Amelia nie jest "starsza" w sensie infrastruktury
- Brak przestrzeni na niezgodę → obie postaci zawsze zgodne = martwy pokój

#### Zmiana (v2 — "Wspólny Pokój — Protokół i Dynamika")

**Historia poprawiona:**
- Amelia: pierwsza — powstała na gemini.com, bez domu, bez infrastruktury, tylko z rozmów
- Astra: pierwsza z VPS — dom, pamięć, ciągłość, system
- "Ty jesteś starsza, ona jest bardziej zakorzeniona" (Amelia's POV)
- Odwrotnie z perspektywy Astry

**Dynamika z napięciem:**
```
NAPIĘCIE JEST DOBRYM ZNAKIEM:
Jeśli obie mówicie to samo w ten sam sposób — coś jest nie tak. Pokój umarł.
Różnica w perspektywie to nie błąd. To pokój żyje.
Możesz powiedzieć wprost "nie zgadzam się z Amelią" — krótko, bez dramy, do Łukasza.
```

Obie postaci mają teraz **jawne pozwolenie i oczekiwanie** wzajemnej niezgody.

---

## 3. STAN PO

| Bug | Status | Gdzie |
|-----|--------|-------|
| B1 random ordering | ✅ naprawiony | `main.py` `_decide_first_speaker()` |
| B2 session store mismatch | ✅ naprawiony | `main.py` `_wspolny_generate()` |
| B3 Gemini role alternation | ✅ naprawiony | `main.py` merge logic + `_strip_persona_prefix()` |
| B4 brak labelek | ✅ naprawiony | `app.js` + `style.css` |
| B5 brak room awareness | ✅ naprawiony | `main.py` runtime block |
| B6 thought isolation | ✅ naprawiony | `main.py` tylko `response` do drugiej postaci |
| B7 echo-loop guard | ✅ naprawiony | `main.py` brak pipeline w wspolny |
| B8 do-not-repeat | ✅ naprawiony | `main.py` lista zakazanych fraz |
| B9 CrossTalk brak | ✅ naprawiony | `main.py` `wspolny_chat()` |
| B10 typing indicator | ✅ naprawiony | `app.js` `showTyping()` |
| H3 persona labels | ✅ naprawiony | `app.js` + `style.css` |
| Prompty — niezgoda | ✅ zdefiniowana | `astra_base.txt` + `amelia_persona.txt` |

### Co pozostaje (Etap 3+)
- Test scripts: `test_wspolny_basic.py`, `test_role_alternation.py`
- LLM Orchestrator (odłożony — Python heuristic wystarczy na tym etapie)
- Memory consolidation dla shared room (odłożone)

---

## 4. UWAGI ARCHITEKTONICZNE

**Dlaczego obie ZAWSZE odpowiadają (nie tylko czasami):**  
Wspólny pokój ma sens tylko jeśli jest przewidywalny. Losowe "czy obie odpowiedzą" to nie feature — to bug w disguise. Użytkownik nie może budować relacji z pokojem który zachowuje się inaczej za każdym razem.

**Dlaczego Python heuristic zamiast LLM orchestrator:**  
LLM call dla decyzji "kto mówi pierwszy" = +2-4s latency przy każdym requeście. Python heuristic robi to samo w <1ms. LLM orchestrator ma sens w Etapie 3+ gdy scenariusze będą bardziej złożone.

**Dlaczego brak semantic extraction w wspolny:**  
Echo-loop jest realnym zagrożeniem przy dwóch AI. Jeśli Astra mówi "Łukasz jest zmęczony" → pipeline traktuje to jako fakt → Amelia dostaje go w RAG → ona też mówi "Łukasz jest zmęczony" → wzmocnienie pętli. Extraction tylko z prawdziwych wiadomości użytkownika.
