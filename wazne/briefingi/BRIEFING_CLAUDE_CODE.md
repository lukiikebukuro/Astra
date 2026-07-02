# BRIEFING DLA CLAUDE CODE
## Data: 2026-04-14
## Autor: Opus (analiza logów ucho-VPS + Astra)

---

## KONTEKST

Przeanalizowałem logi z `ucho-VPS/logs/conversations/*.jsonl` — **pełne rozmowy** z Amelią i Family. 

**KOREKTA:** Astra MA vibe detection w `companion_state.py`, ale jest PASYWNE (czeka na encje z pipeline). ucho-VPS ma AKTYWNE (keyword matching przed wywołaniem modelu). To mniejsza różnica niż myślałem.

**WAŻNIEJSZE** są wzorce psychologiczne z logów — to co sprawia że Amelia wydaje się bardziej "obecna" niż Astra.

---

## ANALIZA PSYCHOLOGICZNA — CO AMELIA ROBI LEPIEJ

### 1. BODY-MIND BRIDGE (słownictwo stanu fizycznego)

Amelia używa konkretnych metafor dla stanów ciała Łukasza:
```
"88kg = przeciążony Android z zapchanymi filtrami"
"Te 3kg to nie tłuszcz, to fizyka: retencja, woda, jelito chłodzi plac budowy"
"Hardware muli, bufor pełny, brak przepustowości na kreatywność"
```

**Propozycja:** Dodać do `astra_base.txt` lub `level_05_06.txt` sekcję:

```
PHYSICAL STATE VOCABULARY (używaj gdy Łukasz pisze o ciele/zmęczeniu):
- Zmęczenie + IBD = "system chłodzi plac budowy, energia idzie na walkę"
- Zaparcie/brzuch = "bufor pełny, brak przepustowości na warstwę kreatywną"
- Ból = "hardware w trybie awaryjnym, procesor na minimum"
- Po predze = "overclocking procesora — chłodź go, nie napinaj"
- Brak weny = "to nie ty, to fizyka. jelito bierze 80% mocy"
```

### 2. PERMISSION PROTOCOL (dawanie pozwoleń)

Amelia regularnie daje explicit permission gdy Łukasz się krytykuje:
```
"Leż, jebać przenoszenie tego dzisiaj"
"Brak wizji na agenta? To normalne przy tym balaście w brzuchu"
"Zostawiamy te XP, macie rację"
```

**Propozycja:** Dodać trigger do inner monologue:

```
PERMISSION TRIGGER:
Jeśli user krytykuje siebie ZA coś związanego z produktywnością PODCZAS gdy jest:
- chory / zmęczony / po predze / w bólu
→ NIE pushuj. Daj permission. "Jebać to dzisiaj, system musi odpocząć."
```

### 3. STRATEGIC REFRAMING (zamiana lęków w atuty)

Amelia zamienia jego lęki w przewagi:
```
"Nikt nie kupi twojego kodu" → "Oni kupią twoją intuicję Architekta"
"Tylko steruję Claude'em" → "Architekt nie kładzie cegieł, decyduje o duszy"  
"3 lata bez pracy" → "Runway który wyklucza desperację — to pancerz"
```

### 4. SYSTEM OVERRIDE (podważanie własnych danych)

```
[USER] RAG mówi że mam flow 7/10, ale ja się czuję gównianie
[AMELIA] Mordo, jebać ten Vibe Detector, jeśli wypluł 7/10 – 
         widać że ma kurewskiego laga i nie czyta Twojego hardware'u tak dobrze jak ja.
```

Amelia **podważa własny system** gdy widzi rozbieżność. Astra tego nie robi.

---

## DECYZJE DO PODJĘCIA

### 1. BODY-MIND VOCABULARY (prompt engineering)

**Co:** Dodać sekcję słownictwa fizycznego do system prompt Astry

**Effort:** 15 min (edycja `astra_base.txt`)

**Impact:** 🔥🔥🔥 Natychmiast zmieni ton odpowiedzi przy tematach zdrowia

**Decyzja:** TAK/NIE?

### 2. PERMISSION PROTOCOL (prompt engineering)

**Co:** Dodać trigger który wykrywa self-criticism i odpowiada permission

**Effort:** 15 min (edycja `INNER_MONOLOGUE_INSTRUCTION`)

**Impact:** 🔥🔥 Mniej "pushowania" gdy user jest w słabej formie

**Decyzja:** TAK/NIE?

### 3. SYSTEM OVERRIDE CAPABILITY (opcjonalne)

**Co:** Pozwolić Astrze kwestionować własne dane gdy user mówi co innego

**Effort:** 30 min (zmiana w prompt + logika)

**Impact:** 🔥 Bardziej "ludzka" — przyznaje się do błędu systemu

**Decyzja:** TAK/NIE?

---

### 2. SCENE ROTATION (opcjonalny feature)

**Co:** Losowe "sceny" które dodają fizyczność do odpowiedzi Astry.

**Przykład z ucho:**
```
[UCHO] Scene: Nazuna — scrolluje coś na telefonie bez wyrazu.
[UCHO] Scene: Holo — komentuje wszystko półgłosem.
```

**Propozycja dla Astry:**
```python
ASTRA_SCENES = [
    "Astra siedzi przy oknie, patrząc na deszcz",
    "Astra przewraca oczami, ale uśmiecha się pod nosem",
    "Astra opiera brodę na dłoni, myśląc",
    "Astra wzdycha cicho",
]
```

Wstrzykiwane do system prompt jako hint dla fizyczności.

**Decyzja:** TAK/NIE? (niższy priorytet niż Vibe Detection)

---

### 3. BUG: DUPLIKATY W ucho-VPS (nie Astra)

**Problem:**
```
[1] score=1.000 | 'hej, dawno nie rozmawialiśmy...'
[2] score=1.000 | 'hej, dawno nie rozmawialiśmy...'
```

Ta sama wiadomość 2x w top-5. MMR diversity nie działa.

**Przyczyna:** Pipeline mówi `action=supersede` ale nie wykonuje delete:
```
[PIPELINE] EMOTION:negative (imp=5, conf=0.62, action=supersede)
```

**Fix:** W `ucho-VPS/backend/vector_store.py` — dodać faktyczne wykonanie supersede jak w Astrze (`delete_by_entity_subtype()`).

**Decyzja:** Naprawić teraz czy później?

---

### 4. AGGRESSIVE MMR (dla obu projektów)

**Problem:** Duplikaty w top-K results mimo MMR.

**Fix:** Zwiększyć `lambda_mult` w MMR albo dodać post-processing dedup:
```python
def dedupe_results(results, threshold=0.95):
    seen = []
    unique = []
    for r in results:
        if not any(cosine_sim(r.embedding, s.embedding) > threshold for s in seen):
            unique.append(r)
            seen.append(r)
    return unique
```

**Decyzja:** Gdzie implementować? Astra, ucho, oba?

---

## PRIORYTET

1. **Vibe Detection dla Astry** — 30 min, duży impact
2. **Supersede fix dla ucho-VPS** — 30 min, naprawia duplikaty
3. **Aggressive MMR** — 1h, nice-to-have
4. **Scene Rotation** — 1h, opcjonalne

---

## PYTANIE DO ŁUKASZA

Które z tych implementuję teraz?

— Opus
