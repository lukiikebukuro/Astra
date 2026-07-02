# anomalytech.eu — Portfolio Copy
## Ready-to-use content for all 4 project cards
gemini
---

# 🎬 FILMIK: ANOMALY TECH — WARSTWA DECYZYJNA (60s)

## SHOT LIST + VOICE-OVER + KOD DO POKAZANIA

---

### [0:00 - 0:05] HOOK

**Na ekranie:** VSCode ciemny motyw. Szybkie pisanie. Stop. Pojawia się:
```python
wrapper == dead_end
```

**Voice-over:**
> "Wszyscy pakują gotowe API w ładne interfejsy. Ja buduję systemy, które łapią to, czego inni nawet nie widzą."

---

### [0:05 - 0:20] PROBLEM: Krwawienie danych

**Na ekranie:** Cięcia między:
1. Czerwone logi błędów w terminalu
2. Wykres "LOST DEMAND" spadający
3. Tekst rozmywający się w szum (symbolika gubienia kontekstu)
4. Pulsujący na czerwono: `UNSATISFIED_INTENT`

**Voice-over:**
> "Firmy krwawią na twardych danych. E-commerce traci popyt, bo trenuje tylko na tym, co się sprzedało. AI traci zaufanie, bo ma pamięć złotej rybki. Gubicie sygnał. Ja go przechwytuję."

---

### [0:20 - 0:28] PROJEKT 1: LDI

**Na ekranie:**
1. Schemat pipeline: `intent → context → signal → reward`
2. Zbliżenie na kod:
```python
# reward_engine.py
clicked_despite_no_match = True  # GOLD SIGNAL
```
3. Miga liczba: **92.3% ACCURACY**
 copy
**Voice-over:**
> "Projekt LDI. Silnik przechwytujący niespełniony popyt na żywym organizmie. Prawie 93 procent skuteczności w wyciąganiu twardego sygnału z ludzkiej frustracji. Prawdziwe dane behawioralne, nie syntetyki."

**Fakt do pokazania:** 183 scenariuszy testowych, 2 domeny (automotive + electronics)

---

### [0:28 - 0:36] PROJEKT 2: ANIMA

**Na ekranie:**
1. Trzy strumienie łączące się (3-channel RAG)
2. Kod rerankera:
```python
# vector_store.py linia 260
final_score = (
    0.60 * similarity +
    0.25 * importance +
    0.15 * recency +
    keyword_boost
)
# + milestone_boost (+1.0)
# + MMR diversity (0.8)
```
3. Animacja: `[EMOTION:tired]` nadpisuje `[EMOTION:energetic]`

**Voice-over:**
> "ANIMA. Suwerenna architektura pamięci. To nie jest głupia baza z wyszukiwarką. To system, który sam decyduje, co nadpisać i jak zarządzać własnym kontekstem. Zero degradacji logiki."

**Fakt do pokazania:** 1,476 memory vectors · supersede logic · nocna analiza 3AM

---

### [0:36 - 0:45] PROJEKT 3: SKANKRAN

**Na ekranie:**
1. Dashboard Skankran (scroll przez mapę/wykresy)
2. GitHub contribution graph (green squares)
3. Terminal flash:
```
DEPLOYED_IN: 4_MONTHS
PRIOR_EXP: ZERO
CITIES: 35
```

**Voice-over:**
> "Skankran. Pełny system SaaS dla gmin, zbudowany od zera w cztery miesiące, bez wcześniejszego zaplecza w kodowaniu. Tak wygląda bezwzględna realizacja celu, kiedy inni szukają wymówek."

**Fakt do pokazania:** 35 polskich miast, compliance EU 2020/2184, AquaBot AI

---

### [0:45 - 0:55] WARSTWA ŁĄCZĄCA

**Na ekranie:**
1. Kod z projektów zaczyna się przenikać/nakładać
2. Schemat: `HUMAN ↔ [ANOMALY LAYER] ↔ LLM`
3. Kamera wjeżdża w środkowy blok

**Voice-over:**
> "Nie jestem front-endem. Buduję kluczową warstwę między człowiekiem a modelem językowym: pamięć, pobieranie, architekturę zachowań. Systemy, które działają na produkcji, a nie na demówkach."

---

### [0:55 - 1:00] CTA

**Na ekranie:** Fade to black. Biały tekst:
```
ŁUKASZ PISKORSKI
AI SYSTEMS ARCHITECT
ANOMALYTECH.EU
```
Mrugający kursor terminala.

**Voice-over:**
> "Łukasz Piskorski. Zbudujmy coś, co faktycznie ma znaczenie. Wejdź na anomalytech.eu."

---

## 📁 PLIKI KODU DO NAGRANIA EKRANU

| Scena | Plik | Linie |
|-------|------|-------|
| LDI | `forteca_finalna/reward_engine.py` | 1-50 |
| ANIMA reranker | `astra/backend/vector_store.py` | 250-290 |
| ANIMA supersede | `astra/backend/vector_store.py` | 95-115 |
| XHR hack (bonus) | `ucho-VPS/ucho_extension/ghost_patch.js` | 60-80 |

---

## 🎤 VOICE-OVER SCRIPT (pełny, do nagrania)

```
Wszyscy pakują gotowe API w ładne interfejsy. 
Ja buduję systemy, które łapią to, czego inni nawet nie widzą.

Firmy krwawią na twardych danych. 
E-commerce traci popyt, bo trenuje tylko na tym, co się sprzedało. 
AI traci zaufanie, bo ma pamięć złotej rybki. 
Gubicie sygnał. Ja go przechwytuję.

Projekt LDI. Silnik przechwytujący niespełniony popyt na żywym organizmie. 
Prawie 93 procent skuteczności w wyciąganiu twardego sygnału z ludzkiej frustracji. 
Prawdziwe dane behawioralne, nie syntetyki.

ANIMA. Suwerenna architektura pamięci. 
To nie jest głupia baza z wyszukiwarką. 
To system, który sam decyduje, co nadpisać i jak zarządzać własnym kontekstem. 
Zero degradacji logiki.

Skankran. Pełny system SaaS dla gmin, zbudowany od zera w cztery miesiące, 
bez wcześniejszego zaplecza w kodowaniu. 
Tak wygląda bezwzględna realizacja celu, kiedy inni szukają wymówek.

Nie jestem front-endem. 
Buduję kluczową warstwę między człowiekiem a modelem językowym: 
pamięć, pobieranie, architekturę zachowań. 
Systemy, które działają na produkcji, a nie na demówkach.

Łukasz Piskorski. 
Zbudujmy coś, co faktycznie ma znaczenie. 
Wejdź na anomalytech.eu.
```

**Czas voice-over:** ~55 sekund (zostaje 5s na intro/outro)