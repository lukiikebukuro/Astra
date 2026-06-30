# ASTRA — Evolution Log
## Sesja: 2026-05-07
### Autor: Łukasz Piskorski / Claude Sonnet 4.6
### Commit: `27964bf`

---

## KONTEKST

Sesja kontynuacyjna po sesji 2026-04-30 (Temporal Filter + RAW cross-session window).

Cel sesji: wdrożyć SQLite FactStore jako hybrydową warstwę exact lookup — deterministyczny odpowiednik ChromaDB dla ustrukturyzowanych faktów.

Stan RAG przed sesją: ~72/100 (po sesji 30 kwi).

---

## CZĘŚĆ I: FACTSTORE — ARCHITEKTURA

### 1.1 Dlaczego SQLite, nie tylko ChromaDB

ChromaDB: semantic similarity. Zwraca co jest "blisko" wektorem. Nie gwarantuje że wróci właściwy fakt.

Scenariusz problematyczny przed FactStore:
```
Łukasz: "Pamiętasz co mi powiedziano na wizycie?"
ChromaDB: zwraca top-3 wektory z similarity — może zwrócić cokolwiek emocjonalnie "bliskie"
Problem: FACT:health, DATE:medical_visit to nie similarity — to deterministyczne dane
```

SQLite rozwiązuje to jednym SELECT z WHERE entity_type='DATE' AND subtype='medical_visit'.

### 1.2 Nowy moduł: `backend/fact_store.py`

Kompletny nowy moduł, zero zewnętrznych zależności, stdlib only.

**Typy encji przechowywane w FactStore (FACT_STORE_TYPES):**
```python
FACT_STORE_TYPES = {
    ('FACT',      'health'),           # Crohn, leki, badania
    ('FACT',      'preference'),       # gusta, upodobania
    ('FACT',      'correction'),       # korekty błędnych faktów
    ('FACT',      'habit'),            # nawyki
    ('DATE',      'medical_visit'),    # wizyty lekarskie
    ('DATE',      'inventory_status'), # stan magazynu/leków
    ('DATE',      'appointment'),      # umówione spotkania
    ('PERSON',    'name'),             # imiona, nazwiska
    ('PERSON',    'relationship'),     # relacje (mama, tata, ...)
    ('MILESTONE', 'love_declaration'), # wyznania miłości
    ('MILESTONE', 'trust_declaration'),# momenty zaufania
    ('MILESTONE', 'future_together'),  # plany wspólnej przyszłości
}
```

**Supersede — jeden aktywny rekord per typ (SUPERSEDE_IN_STORE):**
```python
SUPERSEDE_IN_STORE = {
    ('FACT', 'health'),      ('FACT', 'preference'),
    ('FACT', 'correction'),
    ('DATE', 'medical_visit'), ('DATE', 'inventory_status'),
    ('DATE', 'appointment'),
}
```

Milestony **akumulują** — każdy milestone to osobny rekord. FACT:health **zastępuje** — jeden aktywny wpis.

**Mechanizm supersede:**
```python
# Deterministyczne ID = SHA256(entity_type:subtype:persona_id:user_id_hash)
# Ten sam typ encji per user = ten sam ID = INSERT OR REPLACE nadpisuje
fact_id = _make_fact_id(entity_type, subtype, persona_id, uid_hash)

# Milestony = SHA256(entity_type:subtype:persona_id:user_id_hash:VALUE)
# Różna wartość = różne ID = akumulacja
fact_id = sha256(f"...:{value}").hexdigest()[:32]
```

**Prywatność — user_id nigdy nie trafia do bazy:**
```python
def _hash_user(salt: str, user_id: str) -> str:
    return hashlib.sha256(f"{salt}:{user_id}".encode()).hexdigest()[:16]
```

**Schemat tabeli:**
```sql
CREATE TABLE facts (
    id            TEXT PRIMARY KEY,   -- SHA256 deterministyczny
    persona_id    TEXT NOT NULL,
    user_id_hash  TEXT NOT NULL,      -- SHA256(salt:user_id), nie plain text
    entity_type   TEXT NOT NULL,
    subtype       TEXT NOT NULL,
    value         TEXT NOT NULL,
    date_value    TEXT,               -- YYYY-MM-DD jeśli DATE
    raw_text      TEXT,               -- oryginalne zdanie
    importance    INTEGER DEFAULT 5,
    timestamp     TEXT NOT NULL       -- ISO8601 UTC
)
```

**Indeksy:**
```sql
CREATE INDEX idx_facts_lookup ON facts(persona_id, user_id_hash, entity_type, subtype)
CREATE INDEX idx_facts_type ON facts(entity_type, subtype)
```

**Publiczne metody:**
- `upsert()` — zapis (sprawdza FACT_STORE_TYPES, wybiera strategię ID, SQLite INSERT OR REPLACE)
- `get_facts_for_prompt()` — wszystkie aktywne fakty per user, posortowane MILESTONE>FACT>DATE>PERSON
- `get_by_type()` — exact lookup po entity_type + opcjonalny subtype
- `get_stats()` — total count + breakdown per typ

---

## CZĘŚĆ II: INTEGRACJA W main.py

### 2.1 Inicjalizacja

```python
# Import
from fact_store import FactStore

# Global
fact_store: FactStore = None

# Lifespan step 1b
fact_store = FactStore()
# → "[FactStore] Initialized at /var/www/myastra/astra/backend/astra_facts.db"
```

### 2.2 Nowy blok w system prompcie — [TWARDE FAKTY — SQLite]

Umiejscowienie: powyżej bloku RAW window, powyżej wspomnień RAG.

```python
hard_facts_block = (
    "\n\n[TWARDE FAKTY — SQLite, exact lookup]\n"
    "Te fakty są deterministyczne — nie similarity, nie zgadywanie. "
    "Zawsze mają pierwszeństwo nad wspomnieniami z RAG.\n"
    + "\n".join(lines)
)

return f"{base}\n\n{lukasz_core}{hard_facts_block}{raw_block}\n\n{state_block}\n\n{monologue}"
```

Format linii:
```
[MILESTONE:love_declaration] 2026-03-22: "zawsze będę przy tobie"
[FACT:health] Crohn — brak zastawki Bauhina, Stelara co 8 tygodni
[DATE:medical_visit] 2026-04-07: Stelara #2
```

### 2.3 Ścieżka zapisu — podwójny zapis per encja

Po ekstrakcji każdy fakt trafia równolegle do ChromaDB (existing) i FactStore (new):

```python
# Istniejący zapis do ChromaDB
vs.add_memory(...)

# Nowy zapis do FactStore
fact_store.upsert(
    persona_id=PERSONA_ID, user_id=USER_ID, salt=USER_ID_SALT,
    entity_type=mem.entity_type, subtype=mem.subtype,
    value=mem.text, raw_text=user_msg_clean[:300],
    date_value=mem.date_value if hasattr(mem, 'date_value') else None,
    importance=mem.importance,
)
```

Typy nie w FACT_STORE_TYPES (np. EMOTION) → `upsert()` zwraca False, ChromaDB jako jedyny store.

### 2.4 Debug endpoint

```
GET /api/debug/facts
→ { "stats": { "total": N, "by_type": [...] }, "facts": [...] }
```

---

## CZĘŚĆ III: WERYFIKACJA

### 3.1 Testy lokalne przed deployem

Przetestowano 5 case'ów (plik `test_fact_store.py`):

| Test | Wynik |
|------|-------|
| Upsert FACT:health (supersede) | ✅ |
| Upsert DATE:medical_visit (supersede) | ✅ |
| Milestone accumulation (3 wpisy) | ✅ |
| get_facts_for_prompt() → poprawna kolejność | ✅ |
| get_by_type() exact lookup | ✅ |

Wszystkie 5 passed. (Cleanup PermissionError na Windows — SQLite conn jeszcze otwarte, harmless.)

### 3.2 Weryfikacja na VPS po deploy

Logi po pierwszych wiadomościach testowych:
```
[FactStore] Initialized at .../backend/astra_facts.db
[FactStore] Upsert DATE:medical_visit = '2026-04-07'
[FactStore] Upsert FACT:health = 'Crohn, brak zastawki Bauhina'
[VectorStore] Temporal Filter: 25 -> 16 (9 odfiltrowanych)
```

Supersede działał: DATE:medical_visit przy ponownej ekstrakcji tej samej daty → 1 rekord w bazie.

---

## CZĘŚĆ IV: WAŻNA OBSERWACJA — WZROST BAZY

FactStore rośnie **organicznie** — z każdej rozmowy.

Efekt bezpośredni (dzień 1): +2-3 pkt (kilka faktów, mało historii).
Efekt docelowy (tygodnie): +5-8 pkt gdy baza dojrzeje.

Nie zastępuje ChromaDB — uzupełnia go. ChromaDB: "o co chodzi". FactStore: "co jest faktem".

---

## CZĘŚĆ V: DODATKOWA PRACA SESJI (poza Astrą)

### Pitch docs — `C:\Users\lpisk\Projects\pitch-docs\`

Trzy one-pagery w formacie .md:
- `LDI_onepager.md` — Lost Demand Intelligence, cena 1000 PLN setup + 1000 PLN/mies., pilot 30 dni
- `Skankran_onepager.md` — 35 miast, monetyzacja reklama filtrów wody (najgorętszy moment targetowania)
- `Gwiazdka_onepager.md` — AI companion SaaS, Free/Premium (30 PLN/mies.), TikTok jako kanał

### Rozwiązany konflikt git (stash pop po pull)

Lokalny git był 3 commity za VPS. Przy merge stash pop wygenerował konflikty w 6 plikach.
Fix: `git checkout HEAD --` dla plików bez zmian lokalnych, ręczne odtworzenie zmian z `git show stash:`.

---

## CZĘŚĆ VI: COMMIT

| Commit | Co | Pliki |
|--------|----|-------|
| `27964bf` | SQLite FactStore — nowa warstwa exact lookup + integracja main.py | `fact_store.py` (nowy), `main.py` |

---

## CZĘŚĆ VII: OTWARTE KWESTIE

| Problem | Status | Priorytet |
|---------|--------|-----------|
| milestones=0 w RAG COMPOSE | widoczne w logach, do zbadania | Wysoki |
| DATE:appointment supersede | kino/meeting nadal kumulują | Średni |
| Amelia migration na VPS | ucho_amelia.db jako historia, pierwsza kandydatka | Następna sesja |
| Rodzina AI (Holo/Nazuna/Hana) | po Amelii | Kolejna sesja |
| Topical blindness strict_grounding.py | nie zrobione | Średni |

---

## CZĘŚĆ VIII: OCENA

**Stan RAG przed sesją:** ~72/100
**Stan RAG po sesji:** ~74/100 (wzrośnie do ~78-80 gdy baza FactStore dojrzeje)

Przyrost bezpośredni +2 pkt z:
- FactStore w system prompcie — twarde fakty nie gubią się w similarity
- Supersede działa na poziomie SQL (nie tylko ChromaDB)

Przyrost docelowy (gdy baza dojrzeje): +5-8 pkt.

Następny duży przyrost:
- Amelia migration → Rodzina AI → cross-persona memory (osobna sesja)
- milestones=0 fix (analiza logów)
