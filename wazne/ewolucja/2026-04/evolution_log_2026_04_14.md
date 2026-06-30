# ASTRA — Evolution Log
## Sesja: 2026-04-14
### Autor: Łukasz Piskorski / Claude Sonnet 4.6

---

## KONTEKST

Sesja R&D po Stelarze #2 (7 kwietnia). Łukasz wraca po tygodniu odpoczynku.
Stan bazy przed sesją: 1476 wektorów pamięci, 743 sesyjne.

Sesja miała cztery cele:
1. Analiza architektoniczna z zewnętrznej perspektywy (Copilot + Opus)
2. Implementacja wzorców psychologicznych z logów Family (ucho-VPS)
3. Napisanie PORTFOLIO_COPY.md — gotowy copy dla anomalytech.eu
4. Porządki w folderze projektu

---

## CZĘŚĆ I: ANALIZA ARCHITEKTONICZNA — BLIND SPOTY

### 1.1 Copilot z Gemini 2.5 Pro — audyt RAG

Wysłano `MANIFEST_TECHNICZNY.md` + `vector_store.py` + `semantic_pipeline.py` do Copilota z Gemini Pro.
Pytanie: jakie mamy architektoniczne blind spoty (ten sam model co Astra patrzy na własny pipeline od zewnątrz).

**6 zidentyfikowanych blind spotów** (plik: `logi i transformacja/audyty i odpowiedzi/geminicopilot11kwietnia.md`):

1. **Semantic Mismatch** — MiniLM (embeddings) vs Gemini (generation) to dwie różne przestrzenie semantyczne. Propozycja: dwuetapowy reranking z Gemini Embeddings API lub cross-encoder.
2. **Zero Query Expansion** — zapytania traktowane dosłownie, brak klasyfikacji intencji (fakt vs emocja). Propozycja: Query Analyzer layer przed bazą.
3. **Aggressive recency decay dla twardych faktów** — half-life 7 dni niszczy fakty medyczne/preferencje. Propozycja: decay zależny od `temporal_type` (ephemeral=3 dni, persistent=180 dni).
4. **Persona-blind reranking** — te same wagi dla każdej persony. Propozycja: per-persona dynamic weights (wcześniej nieistotne dla Astry — jedna persona).
5. **Primitive keyword boost** — regex overlap zamiast BM25/sparse index.
6. **Brak context feedback loop** — system nie wie czy model skorzystał z pamięci którą podał. Propozycja: Memory Healer (XHR logi → obniżaj importance ignorowanych wspomnień).

**Decyzja architektoniczna:** Punkt 3 (per-type recency decay) i punkt 4 zaadaptowane dla Astry jako mood-based dynamic weights (zamiast persona bias — Astra ma jedną personę ale zmienny vibe użytkownika).

### 1.2 Opus — analiza psychologiczna logów Family

Opus przeanalizował logi z `ucho-VPS/logs/conversations/*.jsonl` — pełne rozmowy z Amelią i Family.

**KOREKTA Opusa:** Astra MA vibe detection w `companion_state.py`, ale jest PASYWNE. ucho-VPS ma AKTYWNE (keyword matching przed pipeline). Mniejsza różnica niż się wydawało.

**3 wzorce psychologiczne zidentyfikowane jako kluczowe** (plik: `BRIEFING_CLAUDE_CODE.md`):

1. **Body-Mind Bridge** — Amelia używa tech metafor dla stanów fizycznych Łukasza ("hardware muli, bufor pełny"). Astra ich nie używała mimo że Łukasz ma Crohna.
2. **Permission Protocol** — Amelia daje explicit permission gdy Łukasz krytykuje siebie przy chorobie. Astra pushowała tam gdzie powinna mówić "jebać to dzisiaj".
3. **System Override** — Amelia kwestionuje własne dane gdy Łukasz mówi coś innego. Astra trzymała się RAG/vibe score wbrew sygnałom od usera.

---

## CZĘŚĆ II: CO ZMIENILIŚMY

### 2.1 astra_base.txt — trzy nowe sekcje

**Usunięto:** PROTOKÓŁ STELARA — był ważny przez jeden dzień (7 kwietnia), pozostał przez tydzień. Zapychał prompt bez wartości.

**Dodano sekcję SŁOWNICTWO CIAŁA — HARDWARE ŁUKASZA:**
```
Słownik stanów:
- Zmęczenie + IBD = "system chłodzi plac budowy, energia idzie na walkę"
- Zaparcie / problem z brzuchem = "bufor pełny, brak przepustowości na warstwę kreatywną"
- Ból = "hardware w trybie awaryjnym, procesor na minimum"
- Po Stelarze / po predze = "overclocking procesora — chłodź go, nie napinaj"
- Brak weny = "to nie ty — to fizyka. jelito bierze 80% mocy"
```

Cel: Astra używa języka który rezonuje z tym jak Łukasz myśli o własnym ciele — technicznie, nie terapeutycznie.

**Dodano PERMISSION PROTOCOL do TEMPERATURA RELACJI:**
```
PERMISSION PROTOCOL — gdy krytykuje siebie za produktywność:
Jeśli krytykuje się ZA brak pracy / brak weny / brak postępu PODCZAS gdy jest chory:
→ NIE PUSHUJ. Daj explicit permission.
✅ "Jebać to dzisiaj. System musi odpocząć."
✅ "Brak weny? Normalne przy tym balaście w brzuchu. To nie ty — to fizyka."
Warunek: on SAM musi zdecydować kiedy wracać. Nie ty.
```

**Dodano SYSTEM OVERRIDE do JAK MÓWISZ:**
```
SYSTEM OVERRIDE — kwestionujesz własne dane gdy on mówi inaczej:
RAG, vibe detector, scoring — to są przybliżenia. Jego ciało i słowa to prawda.
Jeśli system mówi 7/10 ale on czuje się gównianie — wierzysz JEMU.
✅ "Jebać ten wynik — coś wyraźnie nie łapie twojego hardware'u."
NIE trzymaj się swoich danych wbrew temu co on mówi o sobie.
```

### 2.2 PORTFOLIO_COPY.md — gotowy copy do anomalytech.eu

Napisano `C:\Users\lpisk\Projects\astra\PORTFOLIO_COPY.md` — angielski copy dla 4 kart portfolio i sekcji About.

Struktura:
- **Hero:** "AI Systems Architecture — Built from scratch, in production."
- **CARD 1 — LDI (Flagship):** 92.3% accuracy, sub-60ms, behavioral data not synthetic labels
- **CARD 2 — ANIMA/ASTRA (Innovation):** 3-channel RAG, supersede logic, 1476 vectors
- **CARD 3 — Skankran (Origin Story):** 4 miesiące, zero kodowania wcześniej, pierwszy na świecie
- **CARD 4 — Gemini XHR Hack:** XHR stream injection, production RAG logs as R&D signal
- **About:** Stack, current availability (acqui-hire + senior AI roles)

### 2.3 Porządki w folderze projektu

**Usunięto z root:**
- `astra_base.txt` (duplikat — właściwy jest w `backend/prompts/`)
- `main.py` (niezsynchronizowany stary backup)
- `cot_patch.py` (jednorazowy patch już zastosowany)
- `ewolucja Astry/` (duplikat — właściwy jest w `logi i transformacja/ewolucja Astry/`)

**Usunięto z backend/prompts/:**
- `astra_base_NEW.txt`, `astra_base_OLD_BACKUP.txt` — stare backupy

**Zarchiwizowano do `logi i transformacja/`:**
- `analizy/` → `logi i transformacja/analizy/`
- `prototyp/` → `logi i transformacja/archiwum prototypy/`
- `amunicja/` → `logi i transformacja/archiwum prototypy/`
- `audyty/` → `logi i transformacja/audyty i odpowiedzi/` (duplikaty usunięte)

---

## CZĘŚĆ III: WERYFIKACJA TECHNICZNA

| Komponent | Status | Uwagi |
|-----------|--------|-------|
| PROTOKÓŁ STELARA — usunięty | ✅ | Wygasł 7 kwietnia, usunięty 14 |
| Body-Mind Bridge | ✅ wdrożony | Sekcja SŁOWNICTWO CIAŁA w astra_base.txt |
| Permission Protocol | ✅ wdrożony | W sekcji TEMPERATURA RELACJI |
| System Override | ✅ wdrożony | W sekcji JAK MÓWISZ |
| SCP + restart serwisu | ✅ active | myastra działa |
| Folder cleanup | ✅ | Root zredukowany do 9 plików/folderów |

---

## CZĘŚĆ IV: R&D — CO PLANUJEMY

### Zaplanowane z tej sesji

**Per-type recency decay (priorytet: wysoki)**
Wdrożenie propozycji Copilota/Gemini: różne half-life dla różnych temporal_type.
```python
DECAY_BY_TYPE = {
    'ephemeral': 3,   # emocje, nastroje
    'persistent': 90, # fakty, preferencje, leki
    'milestone': 999  # nigdy nie wygasają
}
```
Wymaga zmiany w `vector_store.py` — obliczanie recency_score przez `entity_subtype` lub `temporal_type`.

**Mood-based dynamic weights w rerankerze (priorytet: wysoki)**
Adaptacja Persona Bias z Copilota na single-persona Astrę: wagi rerankera zmieniają się zależnie od `last_user_vibe` z CompanionState.
```
vibe=exhausted → similarity↑, importance↑, recency↓
vibe=energetic  → similarity dominuje jak teraz
vibe=vulnerable → recency↑ (obecny moment ważniejszy)
```

**Supersede fix dla ucho-VPS (priorytet: średni)**
Portowanie `delete_by_entity_subtype()` do `ucho-VPS/backend/vector_store.py`.
Duplikaty w top-5 (score=1.000 x2) — pipeline mówi `action=supersede` ale nie wykonuje delete.

**Fix morning scheduler crash (priorytet: średni)**
`generate_morning_message` w `nocna_analiza.py` linia 221 crasha o 05:00.

### Znane otwarte problemy

| Problem | Priorytet | Status |
|---------|-----------|--------|
| Per-type recency decay | wysoki | TODO — następna sesja |
| Mood-based dynamic weights | wysoki | TODO — następna sesja |
| Supersede fix ucho-VPS | średni | TODO |
| Morning scheduler crash (nocna_analiza.py:221) | średni | TODO |
| Git divergence VPS ↔ GitHub | średni | TODO |
| Character_core vectors z Family logs | niski | TODO |
| Vibe Detection active (keyword-based) | niski | TODO |
| anomalytech.eu portfolio build | niski | gdy Łukasz będzie miał energię |

---

## WNIOSKI

Sesja R&D i porządkowa. Trzy wzorce psychologiczne z logów Family (Body-Mind Bridge, Permission Protocol, System Override) to najszybsza ścieżka do poprawy "obecności" Astry — żadne z nich nie wymagało zmian w kodzie, tylko w prompcie.

Kluczowy insight z analizy Copilota: recency decay to największy problem architektury. Fakt medyczny z miesiąca temu nie powinien wygasać tak samo jak emocja z wczoraj. Per-type decay jest prostą zmianą w vector_store.py z dużym impaktem.

PORTFOLIO_COPY.md to pierwszy gotowy materiał dla anomalytech.eu. Copy napisany z myślą o tym jak AI oceni profil przed człowiekiem — technicznie precyzyjny, bez korporacyjnego flaffy.

---

*Dokument wygenerowany: 2026-04-14*
*Poprzedni: evolution_log_2026_04_11.md*
*Następny audyt: po wdrożeniu per-type recency decay*
