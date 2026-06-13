# Briefing dla Claude Code — 2026-04-27

## WAŻNA ZASADA — od teraz obowiązkowa

**ZAWSZE pushuj na GitHub PRZED edycją VPS.**
Workflow:
1. Edytuj lokalnie (lub na VPS)
2. `git add` + `git commit`
3. `git push origin main` ← **obowiązkowe przed restartem serwisu**
4. `systemctl restart myastra`

Bez push → GitHub i VPS się rozjeżdżają → konflikty → bałagan.

---

## Co zrobiliśmy dzisiaj lokalnie (nie ma jeszcze na VPS)

Wszystkie zmiany są w lokalnych plikach na Windows. Trzeba je zintegrować z VPS.

### 1. `backend/vector_store.py` — 3 zmiany

**a) EXCLUDED_SOURCES w Kanale 1 (user_message_raw exclusion)**
```python
EXCLUDED_SOURCES = {'character_core', 'md_import', 'user_message_raw'}
raw_mem = _query({"source": {"$ne": "md_import"}}, limit=pool_size, apply_user_filter=True)
mem_results = [
    r for r in raw_mem
    if r.get('metadata', {}).get('source') not in EXCLUDED_SOURCES
    and not (
        r.get('metadata', {}).get('source') == 'extracted_person'
        and len(r.get('text', '')) < 50
    )
]
```
Wcześniej `user_message_raw` wracało w RAG z similarity ~0.965 (ten sam styl pisania usera) i wypychało wartościowe wspomnienia. Teraz jest twardo wykluczone.

**b) Milestone boost: +1.0 → +0.5**
```python
# Zmień:
if is_milestone:
    final_score += 1.0
# Na:
if is_milestone:
    final_score += 0.5  # +1.0 było nadmiarowe odkąd half_life=365 chroni milestony
```
Milestony nadal mają priorytet, ale nie wypychają trafniejszych faktów.

**c) search_memories default n=5 → n=6**
```python
def search_memories(self, query: str, persona_id: str = "astra",
                    n: int = 6, pool_size: int = 30,
```
Jedno dodatkowe miejsce w kontekście — 2 milestony + 4 fakty zamiast 2+3.

**UWAGA:** VPS ma już `RECENCY_HALF_LIFE_BY_TYPE` (commit c768b46). To jest dobra implementacja, zostaw ją. Nie podmieniaj na `RECENCY_HALF_LIFE_BY_SOURCE` z lokalnych plików — implementacje są równoważne, BY_TYPE jest czystsza.

---

### 2. `backend/semantic_extractor.py` — 2 zmiany

**a) CORRECTION_KEYWORDS (globalna stała, przed `extract_persons()`)**
```python
# Słowa kluczowe wskazujące na korektę faktu — blokują klasyfikację MILESTONE.
# Gdy user poprawia błąd AI, zdanie jest emocjonalne ("nigdy bym nie") i
# bez tej listy trafia jako MILESTONE:vulnerability zamiast FACT:correction.
CORRECTION_KEYWORDS = {
    'nigdy tego', 'nigdy bym', 'to nieprawda', 'pomyliłaś', 'pomylił',
    'mylisz się', 'to nie tak', 'źle pamiętasz', 'nie pamiętasz',
    'wcale nie mówiłem', 'nie powiedziałem', 'błędnie', 'masz błędną',
    'nie mówiłem że', 'poprawiam cię', 'to było inaczej', 'nie zgadza się',
    'poprawiam:', 'korygując:', 'to jest nieprawidłowe', 'złą informację',
}
```

**b) Użycie CORRECTION_KEYWORDS w `_find_best_match()` — blokowanie MILESTONE**

W metodzie `_find_best_match()`, na początku pętli przez `category_embeddings`:
```python
# Twarde blokowanie MILESTONE gdy to korekta faktu.
is_correction = any(kw in text_lower for kw in CORRECTION_KEYWORDS)

for entity_type, subtypes in self.category_embeddings.items():
    base_threshold = self.ENTITY_THRESHOLDS.get(entity_type, threshold)
    for subtype, data in subtypes.items():
        # Blokuj MILESTONE jeśli to korekta — korekty są FACT:correction
        if entity_type == 'MILESTONE' and is_correction:
            continue
        # ... reszta bez zmian
```

**UWAGA:** VPS ma już `FACT:correction` subtype w ENTITY_DEFINITIONS (commit 432fe5d). To zostaje. Dodajesz tylko CORRECTION_KEYWORDS i blokowanie w _find_best_match.

---

### 3. `backend/main.py` — timestamp prefix w memory block

W funkcji `build_system_prompt()`, w pętli budującej `memory_lines`, dodaj prefix z informacją kiedy dane wspomnienie powstało. Astra będzie wiedzieć że fakt sprzed 3 miesięcy jest stary.

Dodaj na początku `build_system_prompt()`:
```python
from datetime import datetime  # (lub przenieś do globalnych importów)
```

W pętli `for mem in fitted:`:
```python
# Timestamp prefix — Astra wie kiedy było dane wspomnienie
time_prefix = ""
ts_str = meta.get('timestamp', '')
if ts_str:
    try:
        ts = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
        ts = ts.replace(tzinfo=None)
        delta = datetime.utcnow() - ts
        if delta.days > 30:
            time_prefix = f"[{delta.days // 30} mies. temu] "
        elif delta.days > 0:
            time_prefix = f"[{delta.days} dni temu] "
        elif delta.seconds > 3600:
            time_prefix = f"[{delta.seconds // 3600} godz. temu] "
        elif delta.seconds > 300:
            time_prefix = f"[{delta.seconds // 60} min temu] "
        else:
            time_prefix = "[przed chwilą] "
    except (ValueError, TypeError):
        pass
```

Zmień linię budującą `memory_lines.append(...)` żeby zawierała `{time_prefix}` przed `{mem['text']}`.

---

### 4. `backend/memory_enricher.py` — FACT:correction importance + supersede

**a) W `IMPORTANCE_RULES['FACT']`** — dodaj:
```python
'correction': 8,  # Korekta błędu AI — ważne, wysoki priorytet
```

**b) W `SUPERSEDABLE_TOPICS`** — dodaj:
```python
'correction': 'topic:fact_correction',  # Nowa korekta nadpisuje starą
```

---

## Weryfikacja po zmianach

Uruchom test suite (jest już w repo lokalnie, skopiuj na VPS lub uruchom lokalnie po pull):
```bash
cd /var/www/myastra/astra/backend
python test_astra_behaviors.py 2>/dev/null
```
Oczekiwany wynik: **17/17 testów (100%)**

Jeśli nie 100% — nie restartuj serwisu dopóki wszystkie testy nie przejdą.

---

## Kolejność działań

1. Wprowadź zmiany na VPS
2. `git add` wszystkich zmienionych plików
3. `git push origin main` ← OBOWIĄZKOWE
4. `python -m py_compile backend/*.py` — sprawdź kompilację
5. `python test_astra_behaviors.py 2>/dev/null` — sprawdź testy
6. `systemctl restart myastra`
7. `journalctl -u myastra --since '1 minute ago' | tail -20` — sprawdź logi
