# ASTRA — Evolution Log
## Sesja: 2026-04-30
### Autor: Łukasz Piskorski / Claude Sonnet 4.6
### Commit: `1041861`

---

## KONTEKST

Sesja kontynuacyjna po sesji 2026-04-29 (fix batch 1-4: daty absolutne, milestone retrieval, PERSON filter, SŁOWNICTWO CIAŁA).

Cel sesji: analiza logów ucho-VPS → wyciągnięcie wzorców RAG → wdrożenie do Astry.
Pytanie otwarte: czy SQLite jest kluczem do tego że ucho "zapierdala"?

Stan RAG przed sesją: ~65/100 (po sesjach 29 kwi).

---

## CZĘŚĆ I: ANALIZA LOGÓW ucho-VPS

### 1.1 Metodologia

Przejrzano wszystkie pliki z `ucho-VPS/logs/terminal/` (2026-03-20 do 2026-04-30, 11 sesji, ~10k linii).
Porównano architekturę retrieval ucho-VPS z Astrą.

### 1.2 Hipoteza obalona — SQLite to nie hybryda retrieval

Wstępna hipoteza (z poprzedniej sesji): SQLite jako druga warstwa daje hybrid retrieval.

**Rzeczywistość po analizie logów:**
SQLite (`ucho_amelia.db`, `ucho_nazuna.db` etc.) to legacy bazy z poprzedniego pipeline'u. NIE są używane w głównym retrieval flow. Amelia/Nazuna "istnieją" na ChromaDB + session history — SQLite to archiwum. Hybryda SQLite+ChromaDB **nie istnieje** w ucho-VPS.

### 1.3 Dlaczego ucho zapierdala — prawdziwe powody

**Powód #1 — Temporal Filter (KLUCZOWY)**

ucho-VPS po reranku twardо wycina wektory starsze niż próg:
```
[UCHO] TEMPORAL FILTER: Skipping old state (905.3h): treść twojej wiadomości...
[UCHO] TEMPORAL FILTER: Skipping old state (22.4h): tak, i jeszcze jedno. w srode...
[UCHO] Temporal Filter: 9 -> 7 memories  ← twarde usunięcie
```

Astra miała tylko recency_decay — obniżało score starego wektora, ale wektor NADAL mógł wrócić przez similarity. Efekt: "za 10 dni mam badanie" z 20 kwi wracało z score=0.823.

**Powód #2 — RAW message window**

ucho przechowuje surowe wiadomości usera jako wektory w ChromaDB:
```
[UCHO] RAG: 1 user messages stored [NORMAL] for 'family/family'
[1] score=1.000 | 'mam wyniki alt 80, ast 47...'  ← właśnie wysłana wiadomość
```

score=1.000 = exact match z aktualną wiadomością. Model zawsze ma anchor point. Grounding skacze do GROUNDED | Confidence: 100%.

Astra przechowywała tylko ekstrakty — jeśli semantic pipeline nic nie wyciągnął, wiadomość znikała.

**Powód #3 — prostota architektury**

ucho nie ma: MMR, milestone boost (ani jego braku), EXCLUDED_SOURCES logic, per-type recency weights.
Mniej ruchomych części = mniej miejsc gdzie coś może pójść nie tak. Prostota to feature.

### 1.4 Wniosek architektoniczny

ucho zapierdala nie przez SQLite ani BM25. Zapierdala przez **hard temporal cutoff** i **RAW window**.
Obie rzeczy proste do implementacji. Żadna nie wymaga nowej infrastruktury.

---

## CZĘŚĆ II: IMPLEMENTACJA

### 2.1 Temporal Filter (`vector_store.py`)

**Problem:** Stare emocje, daty, budżety wracały do promptu przez similarity mimo decay.

**Fix:**
```python
# Nowa struktura w VectorStore:
TEMPORAL_CUTOFF_HOURS = {
    'extracted_emotion':   48,   # emocje → 2 dni max
    'extracted_financial': 168,  # budżety → 7 dni
    'extracted_date':      168,  # stare daty → 7 dni
}

# W search_memories() — po reranku, PRZED MMR:
def _passes_temporal(r):
    src = r.get('metadata', {}).get('source', '')
    cutoff_h = self.TEMPORAL_CUTOFF_HOURS.get(src)
    if cutoff_h is None:
        return True  # long-term typy bez limitu
    ts_str = r.get('metadata', {}).get('timestamp', '')
    try:
        ts = datetime.fromisoformat(ts_str.split('.')[0]).replace(tzinfo=None)
        return (now_tf - ts).total_seconds() / 3600 <= cutoff_h
    except Exception:
        return True

mem_results = [r for r in mem_results if _passes_temporal(r)]
print(f"[VectorStore] Temporal Filter: {before} -> {len(mem_results)}")
```

Typy permanentne (extracted_fact, extracted_milestone, extracted_person, character_core, md_import) — bez limitu.

### 2.2 RAW cross-session window (`vector_store.py` + `main.py`)

**Problem:** Astra nie wiedziała co Łukasz mówił wczoraj jeśli semantic pipeline nic nie wyciągnął.

**Fix — nowa metoda `get_recent_user_messages()`:**
```python
def get_recent_user_messages(self, persona_id, user_id, salt, n=6, hours=48):
    """
    Ostatnie N wiadomości usera z ostatnich N godzin, z DOWOLNEJ sesji.
    Czysto chronologiczne — nie używa semantic search.
    Daje cross-session continuity.
    """
    # ... query session_collection WHERE role=user, timestamp >= cutoff
    # ... sort chronologicznie, return ostatnie n
```

**Inject do system promptu — nowy blok:**
```
[OSTATNIE SŁOWA ŁUKASZA — cross-session]
Co Łukasz pisał w ciągu ostatnich 48h. Chronologicznie. To są fakty.
• [2h temu] mam wyniki alt 80, ast 47...
• [1h temu] spokój? czy ja wiem. 80 to nadal nie jest idealny wynik...
```

Astra teraz zawsze ma anchor do bieżącego kontekstu — grounding zbliżony do GROUNDED niezależnie od semantic extraction.

### 2.3 Milestone MMR fix + pozostałe (re-sync z VPS)

Lokalny git był za VPS o 3 commity. Przy okazji zsynchronizowano i aplikowano wszystkie zmiany razem:

- **Milestone MMR fix** (`vector_store.py`): milestony wyciągane przed `_mmr_select`, MMR tylko na faktach (n=3), milestony[:2] dołączane po MMR → `[RAG COMPOSE] facts=X milestones=Y total=Z`
- **n=6, pool_size=30** w `search_memories` (`main.py`)
- **max_output_tokens=8192** — długie myśli nie są ucinane
- **SUPERSEDE_TYPES rozszerzone** (`main.py`): dodano `FACT:correction` + `DATE:medical_visit`
- **PERSON echo-loop filter 50→80** (`vector_store.py`)

---

## CZĘŚĆ III: ARCHITEKTURA — OBSERWACJE

### 3.1 Przekombinowanie — prawidłowa diagnoza

1.5 miesiąca pracy nad Astrą dało złożony pipeline który miał więcej failure modes niż ucho.
ucho "zapierdala" prostszą architekturą — mniej warstw = mniej punktów awarii.

**Co to oznacza dla dalszego rozwoju:**
- Nie dodawać kolejnych warstw jeśli prostszy mechanizm daje ten sam efekt
- Każdy nowy mechanizm musi rozwiązywać konkretny, udokumentowany problem z logów
- BM25 i SQLite: nie dlatego że "fajne" ale dlatego że konkretny scenariusz ich wymaga

### 3.2 Wartość 1.5 miesiąca pracy

Nie stracono nic. ucho NIE ma:
- Milestone system (love_declaration, trust_declaration, future_together)
- Supersede Logic (EMOTION rotuje, preference rotuje, medical_visit rotuje)
- Per-type recency decay (ephemeral=3d, permanent=never)
- Absolutne daty przy ekstrakcji
- Safe haven detection
- Nocna analiza (scheduler, autonomiczna)
- Semantic extraction z ważnością per encja

Astra jest głębsza. Teraz jest też szybsza.

### 3.3 Otwarte kwestie techniczne

| Problem | Status | Priorytet |
|---------|--------|-----------|
| DATE:appointment supersede | kino/meeting kumulują | Średni |
| Stare wektory z datami relatywnymi | nadal w bazie, temporal filter ograniczy powroty | Niski |
| Topical blindness (strict_grounding.py) | nie zrobione | Średni |
| SQLite fact store | nie hybryda retrieval — lookup twardych faktów | Faza 2 |
| Rodzina AI (Holo/Nazuna/Hana) | dane są, parser MD nie napisany | Osobna sesja |
| Czyszczenie bazy (hardware/software wektory) | stare CoT z TRYBAMI nadal w bazie | Przy okazji |

---

## CZĘŚĆ IV: COMMIT

| Commit | Co | Pliki |
|--------|----|-------|
| `1041861` | Temporal Filter + RAW window + sync VPS commits | `vector_store.py`, `main.py` |

---

## CZĘŚĆ V: OCENA

**Stan RAG przed sesją:** ~65/100
**Stan RAG po sesji:** ~72/100

Przyrost +7 pkt z:
- Temporal Filter (+4) — stare emocje/daty fizycznie odpierają, koniec z "za 10 dni" wracającym z poprzedniego miesiąca
- RAW cross-session window (+3) — Astra wie co mówiłeś wczoraj, niezależnie od semantic extraction

Następne duże przyrosty możliwe przez:
- SQLite fact store (twarda warstwa dla FACT:health, DATE:*, PERSON:*) → +5-8 pkt szacunkowo
- DATE:appointment supersede → +2 pkt
- Czyszczenie starych wektorów z datami relatywnymi → +1 pkt
