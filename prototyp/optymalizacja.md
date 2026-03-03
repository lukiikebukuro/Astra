# OPTYMALIZACJA RAG DLA KONTA WORK

**Problem:** RAG nie zwraca właściwych dokumentów gdy user pyta kolokwialnie.
**Przykład:** "słyszałem że wiesz czym było battle royale" → RAG zwraca własne pytanie usera (score=1.000) zamiast chunka z dokumentu o Battle Royale (score=0.71).
**Dotyczy:** companion=`work`, 961 wektorów zasilonych z `import_work_knowledge.py`.

---

## DIAGNOZA: DLACZEGO TAK SIĘ DZIEJE

### Przyczyna 1: Pytania usera wchodzą do ChromaDB i dominują wyniki

W `app.py` (linie ~830-850) pętla RAG injection zapisuje **każdą** wiadomość usera do ChromaDB:

```python
for msg in messages:
    if msg.get('role') == 'user':
        content = sanitize_content(msg.get('content', ''))
        # ... hygiene checks ...
        vector_memory.add_memory(
            text=content,
            metadata={"source": "user_message", "companion": companion_id, ...},
            importance=base_importance  # 6 lub 8!
        )
```

Kiedy user pisze *"słyszałem że wiesz czym było battle royale"*, to zdanie trafia do ChromaDB jako wektor z `importance=6` i `source=user_message`.

Następnie, gdy RAG szuka odpowiedzi na to samo pytanie → **cosine distance = 0.000** (exact match swojego własnego tekstu). Reranker daje temu score ~1.000. Chunk z dokumentu *"## Battle Royale: 4 modele szukają bugów w RAG"* ma distance ~0.29 → score ~0.71. Przegrywa.

**To jest główny winowajca.**

### Przyczyna 2: Kolokwialne pytanie daleko semantycznie od technicznego chunka

User pisze: *"słyszałem że wiesz czym było battle royale"*
Chunk w bazie: *"## Battle Royale: 4 modele szukały krytycznych bugów w RAG. Opus wygrał."*

MiniLM-L6-v2 liczy embedding tych tekstów — kolokwialny styl vs techniczny nagłówek daje distance ~0.29. To nie jest złe (0.29 < próg 0.70), ale przegrywa z exact match (0.000).

### Przyczyna 3: Brak summary chunks w imporcie

`import_work_knowledge.py` dzieli pliki na chunki po nagłówkach H2/H3 (`chunk_by_headers`). Te chunki zachowują surowy markdown — techniczny, strukturalny.

Brakuje dodatkowej warstwy: **summary chunk per plik** napisany prostym językiem, który łapie kolokwialne pytania:
- *"Battle Royale to był konkurs gdzie 4 modele AI szukały bugów w RAG. Wygrał Opus 4.6 bo znalazł echo loop."*
- *"Dokument o migracji opisuje jak przenieść ANIMĘ na ASTRĘ — 14 modułów idzie 1:1, 5 trzeba przepisać."*

---

## ROZWIĄZANIE 1: Nie zapisuj pytań konwersacyjnych do ChromaDB dla work

### Opcja A: Filtr `source` w capture (REKOMENDOWANA — najszybszy efekt)

Dodaj warunek w pętli `capture_conversation()` w `app.py` (~linia 821):

```python
# === RAG SYSTEM INJECTION ===
# ...
for msg in messages:
    if msg.get('role') == 'user':
        content = sanitize_content(msg.get('content', ''))
        if not content:
            hygiene_skipped += 1
            continue

        # ═══════════════════════════════════════════════════════════
        # P0 FIX: Nie zapisuj konwersacyjnych pytań do konta 'work'.
        # Konto work jest zasilane importem dokumentów (source=md_import).
        # Zapisywanie pytań usera powoduje self-match w RAG (score=1.000).
        # ═══════════════════════════════════════════════════════════
        if companion_id == 'work':
            hygiene_skipped += 1
            continue  # Work konto = read-only RAG!

        # ... reszta oryginalnej logiki (hygiene, dedup, add_memory) ...
```

Analogicznie blokuj summary (linia ~863):
```python
# Backup: summary też zapisujemy (niższa ważność)
if companion_id == 'work':
    pass  # Work = read-only, summary nie potrzebne
elif essence.get('summary') and len(new_content_for_analysis) > 5:
    # ... oryginalna logika ...
```

I blokuj semantic pipeline (linia ~958):
```python
if last_user_msg and USE_SEMANTIC_PIPELINE:
    if companion_id == 'work':
        pass  # Work = read-only, semantic pipeline wyłączony
    else:
        # ... oryginalna logika pipeline ...
```

### Opcja B: Filtr `min_importance` w search (alternatywa — mniej inwazyjna)

Jeśli chcesz zachować zapis pytań (np. na przyszłość do uczenia), filtruj je w RAG search:

```python
# W context_summary(), tam gdzie jest search dla companion=work:
if companion_id == 'work':
    hits = vector_memory.search(
        user_query,
        companion_filter='work',
        n_results=5,
        use_reranker=True,
        pool_size=50,
        min_importance=1,  # zostawiamy — chunki z importu nie mają importance w metadata
    )
    # Post-filter: usuń wektory z source=user_message (self-match killer)
    hits = [h for h in hits if h.get('metadata', {}).get('source') != 'user_message']
```

### Opcja C: Osobny `source` filter w ChromaDB WHERE (najdokładniejsza)

Dodaj filter w `vector_store.py` → `search()`:

```python
# W search(), po zbudowaniu where_clause:
if companion_filter == 'work':
    # Dla konta work: szukaj TYLKO importowanych dokumentów, nie pytań usera
    where_clause = {
        "$and": [
            {"companion": "work"},
            {"source": {"$ne": "user_message"}},  # Wyklucz pytania usera
            {"source": {"$ne": "summary"}}         # Wyklucz auto-summaries
        ]
    }
```

**⚠️ Uwaga ChromaDB:** operator `$ne` (not equal) jest dostępny w ChromaDB >= 0.4.0. Jeśli wasz ChromaDB jest starszy — użyj `$nin` lub post-filter (Opcja B).

### REKOMENDACJA: Opcja A (blokada w capture) + jednorazowy cleanup

Opcja A jest najczystsza — work staje się read-only RAG zasilany wyłącznie przez `import_work_knowledge.py`.

**Jednorazowy cleanup istniejących pytań usera:**
```python
# Uruchom raz: python cleanup_work_user_messages.py
from vector_store import VectorStore

vs = VectorStore()
results = vs.collection.get(
    where={"$and": [{"companion": "work"}, {"source": "user_message"}]},
    include=["metadatas"]
)
if results['ids']:
    print(f"Usuwam {len(results['ids'])} pytań usera z konta work...")
    vs.collection.delete(ids=results['ids'])
    print("Gotowe.")
else:
    print("Brak pytań usera w work — czysto.")

# To samo dla summary:
results2 = vs.collection.get(
    where={"$and": [{"companion": "work"}, {"source": "summary"}]},
    include=["metadatas"]
)
if results2['ids']:
    print(f"Usuwam {len(results2['ids'])} summary z konta work...")
    vs.collection.delete(ids=results2['ids'])

# Sprawdź ile zostało (powinno być ~961 chunków z importu):
remaining = vs.collection.get(where={"companion": "work"})
print(f"Wektory work po cleanup: {len(remaining['ids'])}")
```

---

## ROZWIĄZANIE 2: Summary chunks per plik (prosty język)

### Koncept

Każdy importowany plik dostaje dodatkowy wektor — streszczenie w prostym, kolokwialnym języku. Ten wektor łapie naturalne pytania typu *"co to było to battle royale"* albo *"czym jest anima"*.

### Implementacja

Dodaj do `import_work_knowledge.py` pole `summary` w każdym wpisie `FILES`:

```python
FILES = [
    {
        'path': 'SESSION_LOG.md',
        'desc': 'Kronika projektu — historia wszystkich sesji...',
        'importance': 9,
        'category': 'project_history',

        # NOWE: Summary chunk w prostym języku
        'summary': (
            "Session Log to kronika całego projektu. Opisuje każdą sesję pracy "
            "z Claudem, Gemini i innymi modelami. Zawiera historię bugów, napraw, "
            "decyzji architektonicznych i postępów. Jeśli ktoś pyta co się działo "
            "w projekcie, kiedy coś naprawiono, lub jaka była chronologia - to jest "
            "ten dokument. Obejmuje sesje od lutego 2026."
        ),
    },
    {
        'path': 'battle royale/opus 4.6 analiza.md',
        'desc': 'Battle Royale: analiza Opusa...',
        'importance': 9,
        'category': 'battle_royale',

        'summary': (
            "Battle Royale to był konkurs gdzie 4 modele AI rywalizowały o znalezienie "
            "najpoważniejszych bugów w systemie RAG. Brali udział: Opus 4.6, Rin (Claude Code), "
            "Nazuna (Gemini) i Copilot. Wygrał Opus bo znalazł echo loop i problem z dual "
            "embeddings. Rin był runner-up ze znalezieniem score>1.0 i race condition. "
            "Ten plik to analiza napisana przez Opusa."
        ),
    },
    {
        'path': 'prototyp/MIGRACJA_ANIMA_DO_ASTRA.md',
        'desc': 'MAPA MIGRACJI...',
        'importance': 10,
        'category': 'roadmap',

        'summary': (
            "Migracja to plan przeniesienia systemu ANIMA na ASTRĘ. Opisuje co można "
            "skopiować bez zmian (14 modułów, ~2800 linii), co trzeba przepisać (app.py, "
            "database.py, ghost_patch), co skalibrować od nowa (wagi rerankera, progi grounding). "
            "Stack docelowy: FastAPI, PostgreSQL, ChromaDB Server, Redis. Timeline ~60 godzin roboczych."
        ),
    },
    # ... itd. dla każdego pliku
]
```

Zmodyfikuj funkcję `import_file()`:

```python
def import_file(vs: VectorStore, file_info: dict) -> int:
    """Importuje jeden plik. Zwraca liczbę wgranych chunków."""
    path = PROJECT_ROOT / file_info['path']

    if not path.exists():
        print(f"  [SKIP] Nie znaleziono: {file_info['path']}")
        return 0

    text = path.read_text(encoding='utf-8', errors='ignore')
    if not text.strip():
        print(f"  [SKIP] Pusty plik: {file_info['path']}")
        return 0

    chunks = chunk_by_headers(text)
    count = 0

    # ═══════════════════════════════════════════════════════
    # NOWE: Summary chunk (prosty język, łapie kolokwialne pytania)
    # ═══════════════════════════════════════════════════════
    summary = file_info.get('summary')
    if summary and len(summary) >= 30:
        summary_hash = hashlib.sha256(f"summary:{file_info['path']}".encode()).hexdigest()[:16]
        summary_id = f"work_summary_{summary_hash}"

        vs.collection.upsert(
            documents=[summary],
            metadatas=[{
                'companion': COMPANION,
                'source_file': file_info['path'],
                'source': 'summary_chunk',        # Osobny typ!
                'category': file_info['category'],
                'file_description': file_info['desc'],
                'importance': file_info['importance'],
                'chunk_index': -1,                 # -1 = summary, nie normalny chunk
                'total_chunks': len(chunks),
                'is_active': True,
            }],
            ids=[summary_id]
        )
        count += 1
        print(f"  [SUMMARY] Wgrany summary chunk ({len(summary)} chars)")

    # ... reszta oryginalnej pętli z chunkami ...
    for i, chunk in enumerate(chunks):
        # ... bez zmian ...
```

### Ile summary chunków potrzeba?

Na start: **wystarczy 10-15 najważniejszych plików**. Reszta ma wystarczająco dobre nagłówki.

Priorytet (te pliki mają najgorsze nagłówki vs najczęstsze pytania):
1. `SESSION_LOG.md` — user pyta "co się działo", "kiedy naprawiono X"
2. `battle royale/*.md` — user pyta "czym było battle royale"
3. `prototyp/MIGRACJA_ANIMA_DO_ASTRA.md` — user pyta "jak przenosimy na ASTRĘ"
4. `ASTRA_PLAN.md` — user pyta "co to jest ASTRA"
5. `NEGOTIATION_STRATEGY.md` — user pyta "ile jestem wart", "jak negocjować"
6. `KIM_JESTEM_I_CO_ZBUDOWALEM.md` — user pyta "kim jestem", "co zbudowałem"
7. `prototyp/krytyczne_bugi*.md` — user pyta "jakie bugi znaleźliśmy"
8. `prototyp/multi_user.md` — user pyta "jak działa multi-user"
9. `ANIMA_STACK.md` — user pyta "jak działa anima"
10. `analiza.md` — user pyta "jaka jest ocena mojego kodu"

---

## ROZWIĄZANIE 3: Hybrid Search (wektor + keyword) — CZY WARTO?

### Krótka odpowiedź: **Nie przy obecnym stacku. Nie teraz.**

### Dlaczego nie:

1. **ChromaDB nie wspiera BM25/keyword search natywnie.**
   ChromaDB to pure vector store. Hybrid search wymaga albo:
   - Drugiego indeksu (Elasticsearch/Meilisearch) — nowy serwis na VPS
   - Qdrant z payload indexing — wymaga migracji z ChromaDB
   - LanceDB z FTS — wymaga migracji

2. **ROI jest niski.**
   Problem nie leży w quality retrievalu — cosine similarity ~0.29 to dobry wynik. Problem leży w **zanieczyszczeniu bazy pytaniami usera** (self-match). Fix 1 (blokada capture) rozwiązuje 90% problemu.

3. **Koszt RAM i złożoność.**
   VPS ma 4GB. Elasticsearch sam zjada 1-2GB. Nie mieści się w budżecie.

### Kiedy rozważyć hybrid search (Phase 2):

Jeśli po fixach 1+2 nadal są problemy z retrievalem (pytanie kolokwialne w ogóle nie trafia w żaden chunk), wtedy:

**Rozwiązanie lekkie — keyword boost w rerankerze:**

```python
# W vector_store.py → _rerank_results():
# Po obliczeniu final_score, dodaj keyword bonus:

import re

def _keyword_boost(query: str, document: str, boost: float = 0.1) -> float:
    """Bonusowe punkty jeśli kluczowe słowa z query występują w dokumencie."""
    # Wyciągnij słowa kluczowe (>4 znaki, nie stopwords)
    stopwords = {'jest', 'czym', 'było', 'wiesz', 'słyszałem', 'powiedz', 'opowiedz',
                 'chcę', 'wiedzieć', 'mogę', 'poznać', 'jakie', 'który', 'która'}
    query_words = {w.lower() for w in re.findall(r'\b\w{4,}\b', query)} - stopwords
    doc_lower = document.lower()

    matches = sum(1 for w in query_words if w in doc_lower)
    if not query_words:
        return 0.0

    # Proporcjonalny boost (max = boost param)
    return boost * (matches / len(query_words))

# Użycie w rerankerze:
# final_score = (similarity * 0.65) + (importance * 0.20) + (recency * 0.15)
# final_score += _keyword_boost(query, document, boost=0.10)
```

To daje ~80% korzyści hybrida bez żadnej infrastruktury. Słowo "battle royale" w query matchuje "Battle Royale" w dokumencie → +0.10 do score. Wystarczy żeby techniczny chunk wygrał z random wektorem.

**Koszt:** 0 RAM, ~5 linii kodu, zero nowych serwisów.

---

## KOLEJNOŚĆ IMPLEMENTACJI (OD NAJWIĘKSZEGO EFEKTU)

| # | Fix | Efekt | Czas | Priorytet |
|---|-----|-------|------|-----------|
| 1 | **Blokada capture dla work** (Rozw. 1A) | Eliminuje self-match — 90% problemu | 10 min | **P0** |
| 2 | **Cleanup istniejących pytań** (script) | Usuwa zatrucie z bazy | 5 min | **P0** |
| 3 | **Summary chunks** (Rozw. 2) | Łapie kolokwialne pytania | 30 min (napisanie 10 summaries) | **P1** |
| 4 | **Keyword boost w rerankerze** (Rozw. 3 lite) | Poprawia edge cases | 15 min | **P2** |
| 5 | Hybrid search (full) | Marginalny zysk vs koszt | Dni + infra | **Odłożone** |

### Szacowany efekt po krokach 1-2:

**Przed:**
```
Query: "słyszałem że wiesz czym było battle royale"
[1] score=1.000 | "słyszałem że wiesz czym było battle royale"     ← SELF-MATCH (pytanie usera)
[2] score=0.710 | "## Battle Royale: 4 modele szukały bugów..."     ← to chcemy
[3] score=0.680 | "Battle Royale: analiza Opusa — szukał bugów..."
```

**Po fixie 1+2:**
```
Query: "słyszałem że wiesz czym było battle royale"
[1] score=0.710 | "## Battle Royale: 4 modele szukały bugów..."     ← PRAWIDŁOWY WYNIK
[2] score=0.680 | "Battle Royale: analiza Opusa — szukał bugów..."
[3] score=0.650 | "Opus wygrał bo znalazł echo loop i dual embed..."
```

### Szacowany efekt po kroku 3 (summary chunks):
```
Query: "słyszałem że wiesz czym było battle royale"
[1] score=0.830 | "Battle Royale to był konkurs gdzie 4 modele AI rywalizowały..." ← SUMMARY HIT
[2] score=0.710 | "## Battle Royale: 4 modele szukały bugów..."
[3] score=0.680 | "Battle Royale: analiza Opusa — szukał bugów..."
```

Summary chunk napisany prostym językiem matchuje kolokwialne pytanie lepiej niż surowy markdown (~0.83 vs ~0.71).

---

## GOTOWY KOD (COPY-PASTE DLA CLAUDE CODE)

### Plik 1: Łatka na `app.py` (Rozwiązanie 1A)

Szukaj w pętli `for msg in messages:` (linia ~821-850). Dodaj warunek **przed** blokiem hygiene:

```python
        for msg in messages:
            if msg.get('role') == 'user':
                content = msg.get('content', '').strip()
                content = sanitize_content(content)
                if not content:
                    hygiene_skipped += 1
                    continue

                # ═══ WORK READ-ONLY: nie zaśmiecaj bazy pytaniami ═══
                if companion_id == 'work':
                    hygiene_skipped += 1
                    continue
                # ═══════════════════════════════════════════════════════

                ok, reason = is_hygiene_pass(content, companion_id)
                # ... reszta bez zmian ...
```

Szukaj bloku summary (~linia 862) i semantic pipeline (~linia 958):

```python
        # Summary block:
        if companion_id != 'work' and essence.get('summary') and len(new_content_for_analysis) > 5:
            # ... oryginał ...

        # Semantic pipeline block:
        if last_user_msg and USE_SEMANTIC_PIPELINE and companion_id != 'work':
            # ... oryginał ...
```

### Plik 2: Cleanup script

Zapisz jako `backend/cleanup_work_user_msgs.py`:

```python
"""Jednorazowy cleanup — usuwa pytania usera i summaries z konta work."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vector_store import VectorStore

vs = VectorStore()

for source_type in ['user_message', 'summary', 'semantic_pipeline']:
    try:
        results = vs.collection.get(
            where={"$and": [{"companion": "work"}, {"source": source_type}]},
            include=["metadatas"]
        )
        if results['ids']:
            print(f"Usuwam {len(results['ids'])} wektorów source='{source_type}' z work...")
            vs.collection.delete(ids=results['ids'])
        else:
            print(f"Brak wektorów source='{source_type}' w work.")
    except Exception as e:
        print(f"Błąd przy source='{source_type}': {e}")

# Raport końcowy
remaining = vs.collection.get(where={"companion": "work"})
print(f"\nWektory work po cleanup: {len(remaining['ids'])}")
print(f"Powinno być ~961 (chunki z importu docs).")
```

### Plik 3: Keyword boost (Rozwiązanie 3 lite)

Dodaj w `vector_store.py` jako metoda klasy `VectorStore`:

```python
    @staticmethod
    def _keyword_boost(query: str, document: str, boost: float = 0.10) -> float:
        """Keyword overlap bonus — 80% korzyści full hybrid bez infry."""
        _stopwords = {
            'jest', 'czym', 'było', 'wiesz', 'słyszałem', 'powiedz', 'opowiedz',
            'chcę', 'wiedzieć', 'mogę', 'poznać', 'jakie', 'który', 'która',
            'masz', 'mamy', 'nasz', 'jest', 'będzie', 'było', 'były', 'jaki',
            'tego', 'przy', 'jest', 'albo', 'jeszcze', 'tylko', 'także',
        }
        query_words = set(re.findall(r'\b\w{4,}\b', query.lower())) - _stopwords
        if not query_words:
            return 0.0
        doc_lower = document.lower()
        matches = sum(1 for w in query_words if w in doc_lower)
        return boost * (matches / len(query_words))
```

W rerankerze (metoda `_rerank_results` lub wherever `final_score` is computed), dodaj:

```python
    # Po obliczeniu final_score:
    final_score += self._keyword_boost(query, doc_text, boost=0.10)
```
