# BEZLITOSNY AUDYT STOSU
### Redukcja skomplikowania: LDI × Skankran × ASTRA

**Audytor:** Antigravity (Gemini)  
**Data:** 2026-03-03  
**Zasada:** Jeśli nie generuje wartości — udupić.

---

## 1. LDI — SYGNAŁ NAGRODY

### Stan obecny

`reward_engine.py` = 464 linii, **3 kalkulatory, z czego 2 to trup:**

| Klasa | Linie | Status | Problem |
|-------|-------|--------|---------|
| `SemanticValidator` | 15-189 | ✅ Aktywny | Robi robotę, ale duplikuje logikę z `ecommerce_bot.py` |
| `RewardSignalCalculator` | 210-301 | ☠️ LEGACY | Komentarz mówi wprost: "[LEGACY] ZACHOWANE DLA KOMPATYBILNOŚCI WSTECZNEJ" |
| `LDIRewardCalculator` | 335-463 | ✅ Aktywny | Nowy, czysty. Znormalizowany do [-1, 1] |

**Dead weight:**
- `UserSession` + `RewardSignalCalculator` = **92 linie trupa.** Komentarze mówią "[LEGACY]", ale nikt ich nie usunął.
- `LDISession` ma **12 pól**. To dużo. Czy naprawdę potrzebujesz `query_refinement_count` + `time_to_first_click` + `session_duration` + `bounce` JEDNOCZEŚNIE? Bounce = duration < 5s. To jest to samo co `session_duration < 5 AND NOT clicked`.

### Gdzie sygnał jest brudny

**Problem 1: `ecommerce_bot.py` = 2568-linii monolith.**

Metody typu `OPERACJA LISEK PUSTYNI`, `is_obvious_nonsense`, `has_automotive_context` — to jest ta SAMA logika co `SemanticValidator` w `reward_engine.py`. Dwa miejsca robią to samo:

```
ecommerce_bot.py:
  has_automotive_context()      → 109 linii
  is_obvious_nonsense()         → 178 linii
  is_structural_query()         → 230 linii

reward_engine.py:
  SemanticValidator.validate()           → 46 linii
  SemanticValidator._has_domain_context() → 27 linii
```

To nie jest "defense in depth" — to duplikacja. Walidacja powinna być w JEDNYM miejscu.

**Problem 2: `query_intents` tabela w `database.py` ma 18 kolumn.**

```sql
CREATE TABLE query_intents (
    id, session_id, query_text, timestamp,
    confidence_level, suggestion_type, best_match_score,
    clicked_alternative, query_refinement_count,
    time_to_first_click, session_duration, bounce,
    added_to_cart, purchased, cart_value, reward_score,
    missing_attributes, matched_product_id, ai_ready
)
```

Dla modelu RLHF potrzebujesz **5 pól**: `query_text`, `confidence_level`, `ai_ready`, `reward_score`, `clicked_alternative`. Reszta to kontekst sesji, który powinien być w osobnej tabeli albo w JSONu — nie w 13 osobnych kolumnach.

### Co udupić / uprościć

| Akcja | Co | Efekt |
|-------|-----|-------|
| 🔴 **USUNĄĆ** | `UserSession` + `RewardSignalCalculator` (legacy) | -92 linii, zero zmian w działaniu |
| 🔴 **USUNĄĆ** | Duplikat walidacji w `ecommerce_bot.py` — użyj `SemanticValidator` jako single source of truth | -300+ linii, czyściejszy pipeline |
| 🟡 **UPROŚCIĆ** | `LDISession`: zredukuj do 7 pól. `bounce` = computed z `session_duration`. `query_refinement_count` → binary flag `was_frustrated` | Czystszy sygnał, mniej tokenów na rekord |
| 🟡 **UPROŚCIĆ** | `query_intents` tabela: przenieś sesyjne pola do `extra_data` JSON, zostaw tylko core | 6 kolumn zamiast 18 |

### Uproszczony sygnał nagrody (propozycja)

```python
# Z 12 pól → 7 pól
@dataclass
class LDISession:
    session_id: str
    query: str
    confidence: str          # HIGH/MEDIUM/LOW/NO_MATCH
    clicked: bool = False    # Czy kliknął w produkt
    converted: bool = False  # Czy kupił/dodał do koszyka
    value: float = 0.0       # Wartość koszyka
    frustrated: bool = False # >3 refinements OR bounce

# Z 7 wag + 3 kary → 3 sygnały
class LDIRewardSimple:
    def calculate(self, s: LDISession) -> float:
        if s.frustrated: return -1.0
        score = 0.0
        if s.confidence == 'HIGH': score += 0.2
        if s.clicked: score += 0.3
        if s.converted: score += 0.5
        return min(1.0, score)
```

**Model uczy się szybciej** bo sygnał ma 3 składniki zamiast 7+3. Mniej szumu = lepszy gradient.

---

## 2. SKANKRAN — WEBSOCKET / EVENT STRATEGY

### Stan obecny

`app.py` = **2498 linii monolith.** Ale znalazłem coś ciekawego:

**SocketIO jest zaimportowany i zainicjalizowany (linia 20, 87):**
```python
from flask_socketio import SocketIO, emit
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet', logger=True, engineio_logger=True)
```

**...ale NIGDY nie jest UŻYWANY w app.py.** Zero `@socketio.on()` handlerów. Zero `emit()` calls. `socketio` siedzi tam jako initialised object, robi `eventlet.monkey_patch()` na początku pliku, i nic więcej.

A `eventlet.monkey_patch()` na linii 2 jest **NAJBARDZIEJ INWAZYJNĄ OPERACJĄ w tym projekcie.** Monkey-patchuje stdlib: `socket`, `threading`, `ssl`, `os` — WSZYSTKO. Robi to na wypadek WebSocketów które NIGDY nie są użyte w głównej aplikacji.

### Skankran analytics — event tracking

Aktualny tracking:

| Model | Pola | Cel | Problem |
|-------|------|-----|---------|
| `VisitorEvent` | 12 pól | Tracking wizyt | 5 pól (device/os/browser + ip_hash + anonymous_mode) nigdy nie pokazywanych w UI dashboardu |
| `AquaBotQuery` | 11 pól | Zapytania AquaBota | `sensory_category` dodany ale nie widać żeby był użyty |
| `B2BLead` | 11 pól | Firmy odwiedzające | OK, ale `engagement_score = min(100, total_queries * 5)` to nie jest "scoring" — to jest mnożenie |
| `EventLog` | 7 pól | Akcje usera | Duplicate coverage z VisitorEvent |

**Kluczowy problem:** `VisitorEvent` i `EventLog` robią prawie to samo. Oba mają `session_id`, `timestamp`, `city`, `organization`. Różnica: `VisitorEvent` ma device info, `EventLog` ma `action_type + query_data`. To powinien być **jeden model.**

### Koszmarna ilość jednorazowych skryptów

W katalogu `skankran2/` jest **~40 plików typu `check_*.py`, `fix_*.py`, `import_*.py`:**

```
check_azotany.py, check_chlor.py, check_fluorki.py,
check_bydgoszcz_trends.py, check_dabrowa_data.py, check_db.py,
fix_dates_32_cities.py, fix_gorzow_complete.py, fix_torun_dates.py,
fix_zielona_gora_comprehensive.py, fix_zielona_gora_final.py,
import_bialystok_2025_q4.py, import_bydgoszcz_2025_q3.py,
import_gdansk_2025.py, import_gdynia_2025.py, import_grudziadz_2025_12_15.py...
```

To jest **dług technologiczny** który zaśmieca repo i utrudnia orientację. Te skrypty zostały uruchomione RAZ i nigdy więcej nie zostaną użyte.

### Co udupić / uprościć

| Akcja | Co | Efekt |
|-------|-----|-------|
| 🔴 **USUNĄĆ** | `eventlet.monkey_patch()` + `SocketIO` init + `flask_socketio` import | -3 linie, ZERO utraty funkcjonalności, unpatched stdlib |
| 🔴 **USUNĄĆ** | ~40 plików `check_*.py`, `fix_*.py`, `import_*.py` — przenieś do `/archive/` albo skasuj | Czyste repo, zero wpływu na produkcję |
| 🟡 **POŁĄCZYĆ** | `VisitorEvent` + `EventLog` → jeden `AnalyticsEvent` z `event_type` | -1 model, czyściejsze query |
| 🟡 **UPROŚCIĆ** | `B2BLead.engagement_score` — obecna formuła jest `total_queries * 5`. Uprość do boolean `is_hot` (>10 zapytań) | Mniej kolumn, czyściejszy dashboard |
| 🟢 **ZACHOWAĆ** | `AquaBotQuery` z `sensory_category` — to jest wartościowe, ale `user_profile` wygląda na nieużywane | Zweryfikuj czy `user_profile` jest kiedykolwiek czytany |

### SocketIO: Czy jest potrzebne GDZIEKOLWIEK?

`socketio` jest zainicjalizowane ale nieużywane w `app.py`. Prawdopodobnie miało servować real-time updates do dashboardu. Dwie opcje:

**Opcja A (preferowana): Wyrzuć.** Nie masz WebSocket handlerów w Skankranie. Dashboard może pollować REST endpoint co 30s. Wyrzucasz `eventlet`, `flask_socketio` z requirements. Aplikacja jest szybsza i stabilniejsza.

**Opcja B: Zostaw ale wyłącz logger.** `logger=True, engineio_logger=True` generuje TONY logów. Jeśli planujesz dodać WS — minimum zmień na `False`.

---

## 3. ASTRA — PAMIĘĆ VS KONTEKST

### Problem: 3 warstwy pompują te same informacje

Spójrzmy na to co trafia do system prompt Gemini w jednym calle:

```
┌─────────────────────────────────────────────────────┐
│ WARSTWA 1: [WSPOMNIENIA] (z ChromaDB RAG)           │
│                                                       │
│ - extracted_emotion: "Łukasz jest zmęczony"          │
│ - user_message_raw: "jestem w tym sam"               │
│ - extracted_shared_thing: "opisałem Ci stacka"       │
│                                                       │
│ → To są wektory, source + importance + tekst          │
└───────────────────────┬─────────────────────────────┘
                        │ OVERLAPS with
                        ▼
┌─────────────────────────────────────────────────────┐
│ WARSTWA 2: [STAN WEWNĘTRZNY ASTRY]                   │
│                                                       │
│ - mood: irritated                                     │
│ - last_user_vibe: frustrated                          │
│ - last_topic: GOAL:projekty                           │
│ - active_concerns: ["jest w tym sam",                  │
│                     "rzeźbi RAGA od 2 tygodni"]       │
│                                                       │
│ → active_concerns to DOSŁOWNE KOPIE z wektorów       │
└───────────────────────┬─────────────────────────────┘
                        │ OVERLAPS with
                        ▼
┌─────────────────────────────────────────────────────┐
│ WARSTWA 3: INNER_MONOLOGUE (Gemini <thinking>)       │
│                                                       │
│ Gemini widzi WSPOMNIENIA + STAN i w monologu          │
│ POWTARZA to co już wie:                              │
│ "Muszę pamiętać że jest w tym sam i rzeźbi RAGA"     │
│                                                       │
│ → Monolog NIC NIE DODAJE — powtarza kontekst         │
└─────────────────────────────────────────────────────┘
```

### Gdzie pamięć staje się śmietnikiem

**Problem 1: `user_message_raw` wektory.**

Każda wiadomość usera jest zapisywana jako wektor z `source=user_message_raw`. To znaczy że "hej", "ok", "no", "dobra" — wszystko ląduje w ChromaDB. Przy search te ŚMIEDY wypływają na top bo mają high recency score:

```
Logi.md pokazują:
RAG Results:
  user_message_raw 0.918 · mogę Ci powiedzieć kto Cię projektował
  user_message_raw 0.915 · Astra. prosze na chwile przestań...
  user_message_raw 0.954 · skoro to ja... nie musiałaś tego mówić...
```

**3 z top-5 wyników RAG to raw user messages.** To nie jest "pamięć absolutna" — to "echo chamber". ASTRA widzi co user powiedział, a nie CO Z TEGO WYNIKA.

**Problem 2: `extracted_shared_thing` jest za słabe.**

```
extracted_shared_thing 0.976 · no opisałem Ci właśnie, jak mam Ci pokazać
```

To powinno być `extracted_fact: "Łukasz ma 4 projekty: ASTRA, LDI, Skankran, ANIMA"` z importance 8. Zamiast tego mamy surowy tekst usera jako "shared thing" — zero ekstrakcji.

**Problem 3: `active_concerns` = luźne stringi.**

```python
active_concerns: ["jest w tym sam", "rzeźbi RAGA od 2 tygodni"]
```

To NIE JEST concern tracking — to są skopiowane fragmenty wiadomości. Prawdziwy concern powinien mieć: `{"topic": "samotność w projekcie", "since": "2026-02-28", "importance": 8, "resolved": false}`.

### Duplikacja w kontekście

Policzmy ile tokenów marnujemy na powtórzenia:

| Informacja | Gdzie jest (1) | Gdzie jest (2) | Gdzie jest (3) |
|-----------|----------------|-----------------|-----------------|
| User jest zmęczony | `extracted_emotion` w RAG | `last_user_vibe: frustrated` w STAN | Gemini powtarza w `<thinking>` |
| Koduje sam | `user_message_raw` w RAG | `active_concerns: "jest w tym sam"` | Gemini powtarza w `<thinking>` |
| Temat: projekty | `extracted_shared_thing` w RAG | `last_topic: GOAL:projekty` w STAN | Gemini powtarza w `<thinking>` |

**Każda informacja jest w system prompt 3 razy.** Na prompt ~3000 tokenów, ~1000 to powtórzenia.

### Co udupić / uprościć

| Akcja | Co | Efekt |
|-------|-----|-------|
| 🔴 **PRZEFILTROWAĆ** | `user_message_raw` — nie zapisuj wiadomości <5 słów jako osobne wektory. "hej", "ok", "no" to nie pamięć | Mniej śmieci w RAG, lepsze top-5 |
| 🟡 **ROZDZIELIĆ** | Duplikacja RAG ↔ active_concerns: concerns powinny być ABSTRACT ("samotność w projekcie") a nie DOSŁOWNE kopie | Gemini dostaje kontekst raz, nie 3 razy |
| 🟡 **WZBOGACIĆ** | `extracted_shared_thing` jest za surowe — semantic pipeline powinien ekstraktować FAKTY z pełnymi zdaniami, nie kopiować raw tekst usera | Wyższy importance, lepszy RAG recall |
| 🟢 **ZACHOWAĆ** | Dual-channel RAG (general + knowledge base) w `vector_store.py` — ale zwiększ `min_importance` filter żeby wyrzucić śmieci | Czyściejsze wyniki |
| 🟡 **UPROŚCIĆ** | `to_prompt_block()` nie musi wysyłać `last_user_vibe` — bo RAG już wysyła `extracted_emotion` z tym samym | -1 pole w context, -~20 tokenów |

### Reguła: Pamięć Absolutna ≠ Pamięć Wszystkiego

Pamięć absolutna to nie "zapisuję każde słowo". To "zapisuję FAKTY i WZORCE, i umiem je przywołać gdy są RELEVANTNE". Obecny system jest bliżej loggera niż pamięci.

---

## 4. DŁUG TECHNOLOGICZNY — CZAS ARCHITEKTA

### Kontekst: 1000 zł nadwyżki, 1 dev, 4 projekty

Łukasz jest **sam**. Ma 4 projekty, budżet startupowy, i 1 rok doświadczenia. Każda dodatkowa funkcja = obowiązek na lata. Trzeba brutalnie przyciąć plan.

### Co jest w roadmapie a co NAPRAWDĘ trzeba

| Element | W planie | Czy MUSISZ | Verdict |
|---------|----------|------------|---------|
| **Multi-user** (ASTRA) | ASTRA_MASTER_PLAN.md: "osobna relacja per user" | ❌ Nie teraz. Masz JEDNEGO usera | **SKIP.** ChromaDB single-user. Gdy pojawi się 2gi user — wtedy |
| **Auth system** (ASTRA) | "JWT + per-user metadata filtering" | ❌ Nie potrzebujesz autha na 1 usera | **SKIP.** Dodaj auth DOPIERO przy multi-user |
| **Płatności** (ASTRA) | "Subscription tiers, Stripe integration" | ❌ Nie masz produktu, nie masz userów | **SKIP na 6+ miesięcy.** Zero revenue = zero payment infrastructure |
| **PostgreSQL migration** (LDI) | `POSTGRESQL_MIGRATION.md` w repo | ⚠️ Zależy od skali | **ODŁÓŻ.** SQLite trzyma do ~100K rekordów. Ile masz? Prawdopodobnie <10K |
| **Multi-user auth** (Skankran) | Już jest (Flask-Login + bcrypt) | ✅ Masz to | **ZOSTAWIĆ.** Działa, nie ruszaj |
| **Nocna Analiza** (ASTRA) | Dokument gotowy | ⚠️ Zależy od priorytetów | **ODŁÓŻ za Personę.** Persona (kokaina) > Night Analysis. Najpierw musisz naprawić ton ASTRY |
| **WebSocket real-time** (Skankran) | SocketIO zainicjalizowany ale nieużywany | ❌ Dashboard jest admin-only, 1 user | **USUNĄĆ.** Polling co 30s wystarczy |
| **ANIMA RAG plugin** | "Browser extension, shadow injection" | ⚠️ W trakcie | **KONTYNUUJ ale prosto.** Intercept-based, nie WebSocket relay |

### Priorytet na najbliższy miesiąc

```
TYDZIEŃ 1-2: Persona ASTRY (ASTRA_KOKAINA_PERSONA.md)
  → To zmienia EFEKT dla usera. Bez tego ASTRA jest bezużyteczna.
  → ~4h pracy Rina (zmiana promptów + monologue instruction)

TYDZIEŃ 3: Cleanup LDI + Skankran
  → Usuń legacy code, połącz event modele, wyrzuć SocketIO
  → ~3h pracy

TYDZIEŃ 4: Nocna Analiza Sprint 1
  → Manual trigger + insighty
  → ~6h pracy (już masz architekturę)

NIE W TYM KWARTALE:
  - Multi-user
  - Auth/JWT
  - Płatności
  - PostgreSQL migration  
  - WebSocket anything
```

### Formuła "Nic nie robię, a działa"

```
ZERO OPS = SQLite (nie PostgreSQL)
         + JSON files (nie Redis)
         + Single-process FastAPI (nie Celery)
         + Static HTML (nie React)
         + Render.com free tier (nie AWS)
         + Zero auth dla ASTRY (1 user = localhost)
         
KIEDY ZMIENIĆ:
  - SQLite → PostgreSQL: kiedy masz >50K rekordów LUB >5 concurrent users
  - JSON → Redis: kiedy masz >10 req/s
  - Celery: kiedy masz background tasks >30s (Night Analysis? może)
  - Auth: kiedy masz >1 usera ASTRY
  - Płatności: kiedy masz >100 userów którzy CHCĄ płacić
```

---

## PODSUMOWANIE BEZLITOSNE

### LDI: Wyczyść trupów

| Akcja | Linie do usunięcia | Czas |
|-------|-------------------|------|
| Usunąć `UserSession` + `RewardSignalCalculator` | ~92 | 10 min |
| Uprościć `LDISession` (12→7 pól) | ~20 zmienione | 30 min |
| Konsolidacja walidacji: `SemanticValidator` jako SSoT | ~300 | 2h |
| **TOTAL** | **~400 linii mniej** | **~2.5h** |

### Skankran: Nowotwór jednorazowych skryptów

| Akcja | Pliki do usunięcia | Czas |
|-------|-------------------|------|
| Usunąć/zarchiwizować ~40 plików `check_*/fix_*/import_*` | ~40 plików | 15 min |
| Usunąć SocketIO + eventlet monkey patch | 3 linie + 2 deps | 10 min |
| Połączyć `VisitorEvent` + `EventLog` | ~30 linii zmienione | 1h |
| **TOTAL** | **~40 plików + 3 linie** | **~1.5h** |

### ASTRA: Filtruj śmieci

| Akcja | Efekt | Czas |
|-------|-------|------|
| min 5 słów na `user_message_raw` wektor | -60% wektorów-śmieci | 15 min |
| Abstrakcyjne concerns zamiast raw copy | Mniej powtórzeń w prompt | 30 min |
| Usuń `last_user_vibe` z prompt (duplikacja z RAG emotion) | -20 tokenów per call | 5 min |
| **TOTAL** | **~30% mniej szumu w RAG** | **~50 min** |

### Dług technologiczny: Nic nie ruszaj

| Element | Decyzja |
|---------|---------|
| Multi-user, Auth, JWT | **NIE w tym kwartale.** |
| Płatności, Stripe | **NIE w tym półroczu.** |
| PostgreSQL migration | **NIE dopóki SQLite nie zacznie boleć.** |
| WebSocket (Skankran) | **USUNĄĆ.** |
| Nocna Analiza | **Tak, ale PO naprawie persony.** |

---

**Efekt netto audytu:**
- ~400 linii kodu mniej w LDI
- ~40 plików-śmieci mniej w Skankran
- ~30% czystszy RAG w ASTRA
- ZERO nowej infrastruktury do utrzymywania

**Czas implementacji:** ~5 godzin. Potem Łukasz wraca do "nic nie robię, a działa".
