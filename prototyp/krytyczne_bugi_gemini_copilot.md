# KRYTYCZNE BUGI BEZPIECZEŃSTWA (MULTI-USER ASTRA)

**Dotyczy:** Bezpieczeństwo danych po przejściu z single-user (Łukasz) na multi-user (ASTRA).
**Status:** Krytyczne (P0) przed jakimkolwiek wdrożeniem produkcyjnym z prawdziwymi użytkownikami.

---

Obydwa zgłoszone błędy (Wyciek/Nadpisanie wektorów oraz Wyścig w Cache) mają ten sam mianownik: **ASTRA ma scentralizowany state tam, gdzie powinna mieć state izolowany per-user (per-tenant)**.

Poniżej kompletny audyt z planem i gotowym kodem dla Twojego inżyniera (Claude Code).

## 1. WSZYSTKIE MIEJSCA GDZIE BRAKUJE `user_id`

### 🔴 W pliku `vector_store.py`:
1. `add_memory()` — generowanie ID wektora (twój BUG #1).
2. `add_memory()` — brak zapisywania `metadata['user_id'] = user_id`. Bez tego ChromaDB nie wie, do kogo należy wektor.
3. `search()` — `where_clause` używa tylko `companion_filter`. User A zobaczy wspomnienia Usera B! (Krytyczny wyciek danych / Data Leakage).
4. `search_with_milestones()` — `where={"$and": [{"is_milestone": True}, {"companion": ...}]}` wyszuka kamienie milowe wszystkich użytkowników na raz.
5. `search_with_ids()` — j.w.
6. `search_with_persona()` / `get_secrets_for_persona()` — wyciek "sekretów" pomiędzy instancjami tych samych person (np. sekret dodany przez usera A będzie widoczny u usera B).
7. `forget_memory()` — wyszukiwanie do usunięcia wg `query` lub `text_contains` BEZ `user_id` w klauzuli `where` **usunie wspomnienia wszystkich użytkowników w aplikacji**, którzy kiedykolwiek użyli danego słowa!

### 🔴 W pliku `app.py` (API):
8. `_dedup_ttl_cache` + `is_vector_duplicate()` — globalny cache blokujący/uszkadzający zapis (twój BUG #2).
9. `_hygiene_recent_hashes` + `is_hygiene_pass()` / `hygiene_register()` — ten sam problem co wyżej.
10. `capture_conversation()` — `content_hash = hashlib.md5(raw_conversation_text)`. Jeśli 2 użytkowników jednocześnie powie "hej", drugi zostanie zablokowany przez `get_last_conversation_hash` i usunięty jako duplikat.
11. `capture_conversation()`, `inject_memory()`, `context_summary()`, `chat()`, `forget_memory_endpoint()` — te endpointy MUSZĄ wyciągać `user_id` payloadu JSON (a docelowo z tokenu JWT) i przekazywać go do metod RAG: `vector_memory.*`.
12. `export_memory()` / `get_dashboard_stats()` — bez `user_id` zwrócą statystyki i całą zawartość wektorów dla wszystkich w bazie.

---

## 2 & 3. MINIMALNE FIXY (CHIRURGICZNE) I PRIORYTETY

Strategia obronna (Zero-Trust) wymaga punktowych łat a nie przepisywania całości.

**P0 (Krytyczne bezpieczeństwo - Zablokować wyciek danych i nadpisywanie):**
- Modyfikacja `vector_store.py`: w 6 zaznaczonych miejscach operacji wektorowych dodać wymuszony parametr `user_id`.
- Modyfikacja ID w ChromaDB oraz wstrzykiwanie `user_id` w metadane wspomnień.
- Aktualizacja słowników `$and` w `where_clause` w RAG, by zawsze ograniczały się do `{"user_id": user_id}`.
- Przekazanie `user_id` z top-level requestów (`app.py`) do funkcji `vector_store`.

**P1 (Race Conditions / Data Corruption / Global Caches):**
- Fix BUG #2: Zmiana budowy kluczy dedupujących w słownikach na `f"{user_id}:{companion_id}:{hash}"`.
- Fix hasha na powtarzalne konwersacje w module capture (zapobieganie blokadzie zapisu dubli u różnych userów).

---

## 4. GOTOWY KOD DLA P0 FIXÓW (DO PRZEKAZANIA DLA CLAUDE CODE)

Oto instrukcja chirurgicznych cięć do wykonania przez model wykonawczy.

### Krok 1: Wymuszenie tożsamości w ID i Metadanych (`vector_store.py`)

Zmień sygnaturę i implementację `add_memory`:

```python
    # DODANO: argument user_id obowiązkowy dla multi-user!
    def add_memory(self, text, metadata, importance=5, is_milestone=False,      
                   is_secret=False, secret_for_persona=None, shared_with=None, user_id=None): 
        
        if not user_id:
            raise ValueError("[PRIVACY FAULT] user_id is absolutely required for multi-tenant storage!")

        if not text or len(text) < 10:
            return None

        companion = metadata.get('companion', '')
        
        # P0 FIX: BUG #1 (ID z hashem użytkownika - tak zabezpieczamy przez nadpisywaniem kolizji usera A przez usera B)
        mem_id = hashlib.sha256(f"{user_id}:{companion}:{text}".encode('utf-8')).hexdigest()[:32]
        
        # P0 FIX: Wymuszenie wrzucenia user_id do metadanych dla filtrów ChromaDB
        metadata['user_id'] = user_id
        # ... [ZACHOWAJ RESZTĘ ORYGINALNEGO KODU] ...
```

### Krok 2: Uszczelnienie ChromaDB Search Queries (Wycieki) (`vector_store.py`)

Główna metoda `search()` rzuca wyciekiem danych. Wstrzyknij to:

```python
    # DODANO: wymuszony parametr user_id
    def search(self, query, user_id, companion_filter=None, n_results=5, min_importance=1,
                 use_reranker=True, pool_size=20, strict_privacy=True,
                 requesting_persona=None, persona_filter=None):

        if not user_id:
            raise ValueError("[PRIVACY FAULT] Missing user_id in search context")

        # P0 FIX: Złota zasada RAG po migracji! WHERE zawsze musi filtrować user_id
        if companion_filter:
            where_clause = {
                "$and": [
                    {"user_id": user_id},
                    {"companion": companion_filter}
                ]
            }
        else:
            where_clause = {"user_id": user_id}

        # ... [ZACHOWAJ RESZTĘ KODU WYWOŁUJĄCĄ self.collection.query] ...
```

*🔥 Claude Code musi pamiętać: analogicznie dodaj parametr `user_id` i wstrzyknij warunek `{"user_id": user_id}` podczas modyfikowania reguł `$and` w funkcjach `search_with_milestones()`, `forget_memory()`, `search_with_ids()`, oraz `search_with_persona()`.*

### Krok 3: Naprawa BUG #2 (Caches w `app.py`)

Klucze w globalnych cache'ach muszą uwzględniać tożsamość.

```python
# app.py

def is_vector_duplicate(text: str, companion_id: str, user_id: str) -> bool:
    """Sprawdza czy TEN SAM text był ostatnio zapisywany (dedup cache)."""
    now = time.time()
    # P1 FIX: Klucz zależny od usera (Ochrona przed wyścigiem)
    key = hashlib.sha256(f"{user_id}:{companion_id}:{text.strip()[:500]}".encode('utf-8')).hexdigest()
    # ... reszta oryginału

def is_hygiene_pass(text: str, companion_id: str, user_id: str) -> tuple[bool, str]:
    # ...
    text_hash = hashlib.md5(text.strip()[:200].encode('utf-8', errors='ignore')).hexdigest()
    
    # P1 FIX: Izolacja cache'u per user + companion
    cache_key = f"{user_id}:{companion_id}"
    cache = _hygiene_recent_hashes.get(cache_key, set())
    # ...

def hygiene_register(text: str, companion_id: str, user_id: str):
    # ...
    cache_key = f"{user_id}:{companion_id}"
    if cache_key not in _hygiene_recent_hashes:
        _hygiene_recent_hashes[cache_key] = set()
    cache = _hygiene_recent_hashes[cache_key]
    # ...
```

### Krok 4: Wstrzyknięcie `user_id` na szczycie flow frontendu (w API `app.py`)

Wyciągamy ID jako warstwę ochronną z JSON dla głównych endpointów. Przepisanie wywołań w `capture_conversation()`, `/api/chat`, itp.:

Przykład minimalnej łaty dla autoryzacji do wywołań the-backend:
```python
    try:
        data = request.json
        user_id = data.get('user_id', 'legacy_lukasz_fallback_id')  # Docelowo na Astrze: token JWT extraction
        companion_id = data.get('companion_id', 'amelia')
        # ...
        
        # Fixing hash kolizji: 
        content_hash = hashlib.md5(f"{user_id}:{raw_conversation_text}".encode('utf-8')).hexdigest()
        
        # Dopasowanie calla dedup/memory by przekazać usera
        if is_vector_duplicate(content, companion_id, user_id):
        # ...
        vector_memory.add_memory(
            text=content,
            metadata=metadata,
            importance=importance,
            user_id=user_id  # BARDZO WAZNE: przekazanie na dol do RAGA!
        )
```

**Kolejność wdrożenia:**
1. Zaktualizowanie sygnatur i zapytań WHERE/$and w ChromaDB (`vector_store.py`) - To jest bezwzględne zabezpieczenie przed wyciekiem (Wykonaj natychmiast).
2. Podpięcie globalnych cache w `app.py` pod klucze łączące `user_id` - To poprawi błąd blokady zapisów.
3. Przepuszczenie `user_id` przez ścieżki w widokach tras (*routers flask*).
