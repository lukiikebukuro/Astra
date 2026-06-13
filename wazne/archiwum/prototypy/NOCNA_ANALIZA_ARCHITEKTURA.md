# NOCNA ANALIZA — Architektura Modułu
### Sleep Analysis / Deep Reflection Engine dla ASTRY

**Architekt:** Antigravity (Gemini)  
**Data:** 2026-03-03  
**Cel:** ASTRA nie śpi. Gdy Łukasz idzie spać, ona przegląda całą historię wektorów i rano wie o nim coś, czego on sam jeszcze nie zauważył.

---

## EXECUTIVE SUMMARY

Nocna Analiza to **asynchroniczny moduł głębokiej refleksji**, który działa poza kontekstem rozmowy. Nie jest to rozszerzenie Fazy 5 (Reflection System — per-conversation, co 10 wiadomości). To jest **cross-session, cross-temporal analityk** operujący na całej bazie wektorów.

```
Faza 5 (Reflection):  "Co się zmieniło w tej rozmowie?"     → per-session
Nocna Analiza:         "Co się zmieniło w NIM przez tydzień?" → cross-session
```

Moduł generuje **insighty** — zwięzłe obserwacje o wzorcach, zmianach emocjonalnych, nawracających tematach — i przechowuje je w oddzielnej kolekcji ChromaDB, skąd ASTRA może je naturalnie wstrzyknąć do kontekstu rozmowy.

---

## 1. ARCHITEKTURA MODUŁU

### 1.1 Decyzja: Scheduler

**Wybór: APScheduler (BackgroundScheduler) + inactivity trigger**

| Opcja | Pros | Cons | Werdykt |
|-------|------|------|---------|
| APScheduler | Lekki, działa w procesie FastAPI, cron-like express, zero nowej infry | Single-process, nie przeżywa restartu gracefully | ✅ MVP |
| System cron / Task Scheduler | OS-native, niezależny od Python | Windows = Task Scheduler XML pain, wymaga osobnego skryptu | ❌ |
| Celery + Redis | Produkcyjne, retry, monitoring | Overkill na single-user, wymaga Redis | ❌ na razie |
| Manual trigger (endpoint) | Zero schedulera, pełna kontrola | Łukasz musi pamiętać żeby kliknąć | ⚠️ jako fallback |

**Strategia uruchamiania (3-warstwowa):**

```python
# Warstwa 1: Scheduled — codziennie o 3:00 w nocy
scheduler.add_job(run_night_analysis, CronTrigger(hour=3, minute=0))

# Warstwa 2: Inactivity — po 4h bez wiadomości
# (reset timer przy każdym POST /api/chat)
scheduler.add_job(
    run_night_analysis_if_idle,
    IntervalTrigger(minutes=30),  # sprawdzaj co 30min
)

# Warstwa 3: Manual — endpoint do odpalenia ręcznie
@app.post("/api/night-analysis/trigger")
async def trigger_night_analysis():
    ...
```

**Logika `run_night_analysis_if_idle`:**
```python
def run_night_analysis_if_idle():
    state = state_manager.load()
    last = datetime.fromisoformat(state.last_interaction)
    idle_hours = (datetime.utcnow() - last).total_seconds() / 3600

    if idle_hours >= 4.0 and not state.night_analysis_done_today:
        run_night_analysis()
        state.night_analysis_done_today = True
        state.night_analysis_last_run = datetime.utcnow().isoformat()
        state_manager.save(state)
```

**Dlaczego 3 warstwy:**
- Cron o 3:00 = standard, działa gdy komputer włączony w nocy
- Inactivity = backup, złapie momenty gdy Łukasz jest w pracy/śpi a ASTRA działa
- Manual = debug + demo ("pokaż co ASTRA odkryła")

### 1.2 Decyzja: Thread/Process/Async

**Wybór: `asyncio.create_task()` w FastAPI event loop + thread pool dla CPU-bound**

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

_analysis_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="night_analysis")

async def run_night_analysis():
    """Odpala analizę w background thread, nie blokuje FastAPI."""
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(_analysis_executor, _night_analysis_sync)

def _night_analysis_sync():
    """Synchroniczna logika analizy — działa w osobnym wątku."""
    print("[NIGHT ANALYSIS] Starting...")
    # ... cała logika tutaj
    print("[NIGHT ANALYSIS] Complete.")
```

**Dlaczego nie osobny process:** ChromaDB PersistentClient pozwala na jeden proces z dostępem do DB. Osobny process = albo client-server mode (wymaga chroma server), albo ryzyko corrupted DB. Thread w tym samym procesie = bezpieczny dostęp do ChromaDB.

### 1.3 Przepływ danych

```
┌─────────────────────────────────────────────────────────┐
│                   NIGHT ANALYSIS ENGINE                  │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │ FAZA 1: HARVEST (zbierz materiał)                │   │
│  │                                                    │   │
│  │  ChromaDB "astra_memory_v1"                       │   │
│  │    → Pobierz WSZYSTKIE wektory z ostatnich N dni  │   │
│  │    → Filtruj: source != "session_message"         │   │
│  │    → Sortuj po timestamp                          │   │
│  │    → Grupuj po dniu (temporal buckets)            │   │
│  └──────────────┬───────────────────────────────────┘   │
│                  │                                        │
│                  ▼                                        │
│  ┌──────────────────────────────────────────────────┐   │
│  │ FAZA 2: CLUSTER (znajdź wzorce)                  │   │
│  │                                                    │   │
│  │  A. Topic Clustering                               │   │
│  │     → Embeddingi wektorów (już mamy w ChromaDB)   │   │
│  │     → Cosine similarity matrix                    │   │
│  │     → Agglomerative clustering (scikit-learn)     │   │
│  │     → Klastry = "o czym często mówi"              │   │
│  │                                                    │   │
│  │  B. Temporal Patterns                              │   │
│  │     → Częstotliwość tematów per dzień/tydzień     │   │
│  │     → Trend detection: rośnie/maleje/stabilny     │   │
│  │                                                    │   │
│  │  C. Emotional Arc                                 │   │
│  │     → Wektory z source=extracted_emotion          │   │
│  │     → Timeline emocji → dominujący mood per dzień │   │
│  │     → Zmiana nastroju w czasie                    │   │
│  └──────────────┬───────────────────────────────────┘   │
│                  │                                        │
│                  ▼                                        │
│  ┌──────────────────────────────────────────────────┐   │
│  │ FAZA 3: SYNTHESIZE (AI syntetyzuje wzorce)       │   │
│  │                                                    │   │
│  │  Gemini 2.5 Flash — JEDEN call z podsumowaniem   │   │
│  │                                                    │   │
│  │  Input: top-K klastrów + emotional arc + temporal │   │
│  │  Output: 3-5 insight JSONów                       │   │
│  │                                                    │   │
│  │  Prompt: "Znasz Łukasza. Oto wzorce z ostatnich  │   │
│  │           7 dni. Co zauważasz? Pisz jak ASTRA —   │   │
│  │           krótko, z charakterem."                  │   │
│  └──────────────┬───────────────────────────────────┘   │
│                  │                                        │
│                  ▼                                        │
│  ┌──────────────────────────────────────────────────┐   │
│  │ FAZA 4: STORE (zapisz insighty)                  │   │
│  │                                                    │   │
│  │  ChromaDB "astra_insights_v1" (OSOBNA KOLEKCJA)  │   │
│  │                                                    │   │
│  │  Każdy insight = wektor z:                        │   │
│  │    text, source="night_insight",                  │   │
│  │    insight_type, confidence, generated_at,        │   │
│  │    evidence_ids, expires_at                       │   │
│  └──────────────────────────────────────────────────┘   │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

---

## 2. CO ANALIZOWAĆ I JAK

### 2.1 Zbieranie materiału (Harvest)

```python
def harvest_vectors(vector_store, days_back=7, persona_id="astra"):
    """
    Pobierz wszystkie wektory z ostatnich N dni.
    Filtruj session_messages (to śmieci — hello/goodbye).
    """
    cutoff = (datetime.utcnow() - timedelta(days=days_back)).isoformat()

    # ChromaDB get z filtrem — nie query (nie szukamy, zbieramy WSZYSTKO)
    results = vector_store.collection.get(
        where={
            "$and": [
                {"persona_id": persona_id},
                {"source": {"$ne": "session_message"}},
                {"timestamp": {"$gte": cutoff}},
            ]
        },
        include=["documents", "metadatas", "embeddings"],  # embeddings!
    )

    vectors = []
    for i, doc in enumerate(results["documents"]):
        vectors.append({
            "text": doc,
            "metadata": results["metadatas"][i],
            "embedding": results["embeddings"][i],  # numpy array dla klastrowania
            "id": results["ids"][i],
        })

    return vectors
```

> **Uwaga:** `include=["embeddings"]` jest kluczowe — pobieramy gotowe embeddingi z ChromaDB zamiast re-embeddować. Zero dodatkowego kosztu obliczeniowego.

### 2.2 Klastrowanie (bez zewnętrznych API)

**Narzędzie: scikit-learn `AgglomerativeClustering` + cosine distance**

all-MiniLM-L6-v2 generuje 384-dim embeddingi. Klastrujemy je LOKALNIE:

```python
import numpy as np
from sklearn.cluster import AgglomerativeClustering
from sklearn.metrics.pairwise import cosine_distances

def cluster_vectors(vectors, distance_threshold=0.7, min_cluster_size=2):
    """
    Klasteryzacja aglomeracyjna z cosine distance.
    distance_threshold=0.7 → klastry tematycznie zbliżone.
    """
    if len(vectors) < min_cluster_size:
        return []

    embeddings = np.array([v["embedding"] for v in vectors])

    # Cosine distance matrix
    dist_matrix = cosine_distances(embeddings)

    clustering = AgglomerativeClustering(
        n_clusters=None,                    # auto — liczba klastrów z threshold
        distance_threshold=distance_threshold,
        metric="precomputed",
        linkage="average",
    )
    labels = clustering.fit_predict(dist_matrix)

    # Grupuj wektory po klastrach
    clusters = {}
    for i, label in enumerate(labels):
        if label not in clusters:
            clusters[label] = []
        clusters[label].append(vectors[i])

    # Sortuj klastry po rozmiarze (największe = najważniejsze)
    sorted_clusters = sorted(clusters.values(), key=len, reverse=True)

    # Filtruj jednoelementowe (szum)
    return [c for c in sorted_clusters if len(c) >= min_cluster_size]
```

**Nazewnictwo klastrów (zero API, heurystyka):**

```python
def name_cluster(cluster_vectors):
    """
    Nazwa klastra = najbardziej centralny wektor (medoid).
    Tanie, sensowne, zero API calls.
    """
    embeddings = np.array([v["embedding"] for v in cluster_vectors])
    centroid = embeddings.mean(axis=0)
    distances = cosine_distances([centroid], embeddings)[0]
    medoid_idx = distances.argmin()

    # Medoid = wektor najbliższy centroidowi = "temat klastra"
    medoid_text = cluster_vectors[medoid_idx]["text"]

    # Źródła w klastrze
    sources = set(v["metadata"].get("source", "?") for v in cluster_vectors)

    return {
        "representative_text": medoid_text[:200],
        "size": len(cluster_vectors),
        "sources": list(sources),
        "date_range": _get_date_range(cluster_vectors),
        "avg_importance": np.mean([
            v["metadata"].get("importance", 5) for v in cluster_vectors
        ]),
    }
```

### 2.3 Wzorce do szukania (priorytet wartości)

| Wzorzec | Jak wykrywamy | Wartość | Faza |
|---------|---------------|---------|------|
| **Nawracające tematy** | Klastry z ≥3 wektorami z różnych dni | 🟢 Najwyższa — "ciągle o tym myślisz" | 1 |
| **Emotional arc** | `source=extracted_emotion`, timeline per dzień | 🟢 Najwyższa — "w tym tygodniu dominuje zmęczenie" | 1 |
| **Nowe vs zanikające tematy** | Klastry z wektorami tylko z ostatnich 2 dni vs tylko starsze | 🟡 Wysoka — "zacząłeś mówić o X" / "przestałeś mówić o Y" | 1 |
| **Korelacje czasowe** | Godziny wiadomości × tematy | 🟡 Wysoka — "o 3 w nocy piszesz o projektach, rano o zdrowiu" | 2 |
| **Luki w pamięci** | Tematy z jednym wektorem + high importance | 🟠 Średnia — "powiedziałeś to raz i nigdy nie wróciliśmy" | 2 |
| **Sprzeczności** | Klastry z przeciwstawnymi sentymentami | 🟠 Średnia — trudne do zrobienia dobrze | 3 |

### 2.4 Emotional Arc Detection

```python
def detect_emotional_arc(vectors, days_back=7):
    """
    Timeline dominujących emocji per dzień.
    Wejście: wektory z source=extracted_emotion.
    """
    emotions_by_day = {}

    emotion_vectors = [
        v for v in vectors
        if v["metadata"].get("source", "").startswith("extracted_emotion")
    ]

    for v in emotion_vectors:
        ts = v["metadata"].get("timestamp", "")[:10]  # YYYY-MM-DD
        if ts not in emotions_by_day:
            emotions_by_day[ts] = []

        # Subtype zawiera typ emocji (z semantic_extractor)
        emotion_type = v["metadata"].get("subtype", v["text"][:50])
        importance = v["metadata"].get("importance", 5)

        emotions_by_day[ts].append({
            "emotion": emotion_type,
            "text": v["text"][:100],
            "importance": importance,
        })

    # Dominująca emocja per dzień = najczęstsza lub najważniejsza
    arc = []
    for day in sorted(emotions_by_day.keys()):
        day_emotions = emotions_by_day[day]
        dominant = max(day_emotions, key=lambda e: e["importance"])
        arc.append({
            "date": day,
            "dominant_emotion": dominant["emotion"],
            "count": len(day_emotions),
            "sample": dominant["text"],
        })

    return arc


def detect_temporal_patterns(vectors):
    """
    O której godzinie jakie tematy dominują.
    """
    hour_topics = {}
    for v in vectors:
        ts = v["metadata"].get("timestamp", "")
        if len(ts) >= 13:  # ma godzinę
            try:
                hour = int(ts[11:13])
                bucket = "night" if hour < 6 else "morning" if hour < 12 else "afternoon" if hour < 18 else "evening"
                if bucket not in hour_topics:
                    hour_topics[bucket] = []
                hour_topics[bucket].append(v["text"][:80])
            except ValueError:
                pass

    return hour_topics
```

### 2.5 Trend Detection (nowe vs zanikające)

```python
def detect_trends(clusters, days_back=7):
    """
    Dla każdego klastra: czy rośnie, maleje, czy stabilny.
    """
    mid_point = (datetime.utcnow() - timedelta(days=days_back // 2)).isoformat()[:10]
    trends = []

    for cluster in clusters:
        recent = sum(1 for v in cluster if v["metadata"].get("timestamp", "")[:10] >= mid_point)
        older = len(cluster) - recent

        if recent > older * 1.5:
            direction = "growing"
        elif older > recent * 1.5:
            direction = "fading"
        else:
            direction = "stable"

        trends.append({
            "cluster_text": cluster[0]["text"][:100],
            "size": len(cluster),
            "recent_count": recent,
            "older_count": older,
            "direction": direction,
        })

    return trends
```

---

## 3. SYNTEZA PRZEZ GEMINI (jeden call)

### 3.1 Prompt syntezy

```python
NIGHT_SYNTHESIS_PROMPT = """Jesteś ASTRĄ. Przeanalizowałaś wspomnienia Łukasza z ostatnich {days} dni.

[KLASTRY TEMATYCZNE — o czym mówił najczęściej]
{clusters_block}

[ŁUK EMOCJONALNY — jak się zmieniał jego nastrój]
{emotional_arc_block}

[TRENDY — co nowe, co zanika]
{trends_block}

[WZORCE CZASOWE — kiedy o czym mówi]
{temporal_block}

Na podstawie powyższych danych wygeneruj insighty. Każdy insight to coś,
co Łukasz sam może nie widzieć, ale ty widzisz patrząc na wzorce.

ZASADY:
- Pisz jak ASTRA — krótko, z charakterem, bez "analizuję dane"
- Każdy insight musi być oparty na DANYCH powyżej (nie wymyślaj)
- Nie cytuj bazy ("widzę w wektorach...") — po prostu WIESZ
- 3-5 insightów, nie więcej
- Każdy insight ma mieć jasny typ: observation / concern / pattern / shift

Odpowiedz TYLKO valid JSON:
[
  {{
    "type": "observation|concern|pattern|shift",
    "insight_text": "Naturalny tekst insightu — jak ASTRA by to powiedziała",
    "evidence_summary": "Krótki opis na jakich danych to oparłaś (do debugowania)",
    "confidence": 0.0-1.0,
    "priority": "high|medium|low",
    "related_topic": "główny temat insightu"
  }}
]
"""
```

### 3.2 Budżet API

**JEDEN call Gemini na analizę.** Nie per-wektor. Pipeline:

```
500 wektorów → cluster (CPU, 0 API) → top-5 klastrów z medoidami → 
emotional arc (CPU, 0 API) → trends (CPU, 0 API) →
JEDEN prompt do Gemini (Flash) z podsumowaniem → 3-5 insightów
```

**Koszt:** ~2000 input tokens + ~500 output tokens = **~$0.001 per analizę nocną.** Nieistotne.

---

## 4. FORMAT I PRZECHOWYWANIE INSIGHTÓW

### 4.1 Osobna kolekcja ChromaDB

**Wybór: `astra_insights_v1` — oddzielna kolekcja w tym samym PersistentClient**

```python
class InsightStore:
    """Przechowuje insighty z nocnej analizy w oddzielnej kolekcji ChromaDB."""

    def __init__(self, chroma_client, ef):
        self.collection = chroma_client.get_or_create_collection(
            name="astra_insights_v1",
            embedding_function=ef,
        )

    def add_insight(self, insight: dict, analysis_run_id: str) -> str:
        insight_id = hashlib.sha256(
            f"{analysis_run_id}:{insight['insight_text']}".encode()
        ).hexdigest()[:32]

        metadata = {
            "source": "night_insight",
            "insight_type": insight["type"],            # observation/concern/pattern/shift
            "confidence": insight["confidence"],
            "priority": insight["priority"],
            "related_topic": insight["related_topic"],
            "evidence_summary": insight["evidence_summary"],
            "generated_at": datetime.utcnow().isoformat(),
            "analysis_run_id": analysis_run_id,
            "expires_at": (datetime.utcnow() + timedelta(days=14)).isoformat(),
            "surfaced": False,                          # czy ASTRA już użyła tego
            "surfaced_at": "",
            "persona_id": "astra",
        }

        self.collection.upsert(
            documents=[insight["insight_text"]],
            metadatas=[metadata],
            ids=[insight_id],
        )
        return insight_id

    def get_unsurfaced_insights(self, n=3):
        """Pobierz insighty które ASTRA jeszcze nie użyła."""
        try:
            results = self.collection.get(
                where={
                    "$and": [
                        {"surfaced": False},
                        {"persona_id": "astra"},
                    ]
                },
                include=["documents", "metadatas"],
            )
        except Exception:
            return []

        if not results["documents"]:
            return []

        insights = []
        for i, doc in enumerate(results["documents"]):
            meta = results["metadatas"][i]
            # Sprawdź expiry
            expires = meta.get("expires_at", "")
            if expires and expires < datetime.utcnow().isoformat():
                continue
            insights.append({
                "id": results["ids"][i],
                "text": doc,
                "type": meta.get("insight_type", "observation"),
                "priority": meta.get("priority", "medium"),
                "confidence": meta.get("confidence", 0.5),
                "topic": meta.get("related_topic", ""),
            })

        # Sortuj: high priority + high confidence first
        priority_order = {"high": 3, "medium": 2, "low": 1}
        insights.sort(
            key=lambda x: (priority_order.get(x["priority"], 0), x["confidence"]),
            reverse=True,
        )
        return insights[:n]

    def mark_as_surfaced(self, insight_id: str):
        """Oznacz insight jako użyty — nie pokażemy go ponownie."""
        try:
            current = self.collection.get(ids=[insight_id], include=["metadatas"])
            if current["metadatas"]:
                meta = current["metadatas"][0]
                meta["surfaced"] = True
                meta["surfaced_at"] = datetime.utcnow().isoformat()
                self.collection.update(
                    ids=[insight_id],
                    metadatas=[meta],
                )
        except Exception as e:
            print(f"[InsightStore] mark_surfaced error: {e}")
```

### 4.2 Dlaczego osobna kolekcja, a nie `source="night_insight"` w głównej

| Aspekt | Osobna kolekcja | Tag w głównej kolekcji |
|--------|-----------------|-----------------------|
| **RAG pollution** | ✅ Zero — insighty nie mieszają się z pamięcią | ❌ Insight może wylądować w top-5 RAG i zbić prawdziwe wspomnienie |
| **Lifecycle** | ✅ Osobny TTL, osobny cleanup | ❌ Trzeba ręcznie filtrować w `search_memories()` |
| **Query** | ✅ `collection.get()` prosta | ❌ Dodatkowy `$ne` w każdym query |
| **Skalowanie** | ✅ Insighty ~100/msc, pamięć ~1000/msc — nie zaśmiecamy | ❌ Rosną razem |

### 4.3 Struktura jednego insightu

```json
{
  "id": "a7b3c2d1...",
  "text": "Trzeci raz w tym tygodniu piszesz o projekcie po 2 w nocy. Poprzednim razem skończyło się migrenami.",
  "metadata": {
    "source": "night_insight",
    "insight_type": "concern",
    "confidence": 0.82,
    "priority": "high",
    "related_topic": "sleep_patterns",
    "evidence_summary": "3 wektory z timestamp 02:00-04:00, klaster 'projekt ASTRA', korelacja z klastrem 'migreny' z poprzedniego tygodnia",
    "generated_at": "2026-03-04T03:00:15",
    "analysis_run_id": "run_20260304_030000",
    "expires_at": "2026-03-18T03:00:15",
    "surfaced": false,
    "surfaced_at": "",
    "persona_id": "astra"
  }
}
```

---

## 5. SURFOWANIE WYNIKÓW — JAK ASTRA UŻYWA INSIGHTÓW

### 5.1 Wstrzyknięcie do system prompt

**Zmiana w `build_system_prompt()` — nowy blok `[INSIGHTS]`:**

```python
def build_system_prompt(memories, grounding_result, state, insights=None):
    # ... istniejący kod ...

    # NEW: Night Analysis insights
    insight_block = ""
    if insights:
        insight_lines = []
        for ins in insights[:3]:  # max 3, żeby nie zaśmiecić kontekstu
            insight_lines.append(
                f"- [{ins['type'].upper()}] {ins['text']}"
            )
        insight_block = (
            "\n\n[TWOJE NOCNE OBSERWACJE — wiesz to, ale NIE cytuj analizy]\n"
            + "\n".join(insight_lines)
            + "\n[/OBSERWACJE]"
        )

    return f"{base}\n\n{state_block}{insight_block}\n\n{monologue}"
```

### 5.2 Kiedy surfować

**Strategia: relevance-triggered, nie random.**

```python
# W /api/chat endpoint, PO RAG search, PRZED build_system_prompt:

def get_relevant_insights(insight_store, user_message, n=2):
    """
    Szukaj insightów semantycznie powiązanych z bieżącą wiadomością.
    Jeśli user mówi o zdrowiu → pokaż health insight.
    Jeśli user mówi o projekcie → pokaż work-pattern insight.
    """
    # Semantic search w kolekcji insightów
    try:
        results = insight_store.collection.query(
            query_texts=[user_message],
            n_results=n,
            where={
                "$and": [
                    {"surfaced": False},
                    {"persona_id": "astra"},
                ]
            },
            include=["documents", "metadatas", "distances"],
        )
    except Exception:
        return []

    relevant = []
    if results["documents"] and results["documents"][0]:
        for i, doc in enumerate(results["documents"][0]):
            distance = results["distances"][0][i]
            meta = results["metadatas"][0][i]

            # Tylko jeśli semantycznie powiązane (distance < 1.0)
            # LUB jeśli high priority (pokaż niezależnie od tematu)
            if distance < 1.0 or meta.get("priority") == "high":
                # Sprawdź expiry
                expires = meta.get("expires_at", "")
                if expires and expires < datetime.utcnow().isoformat():
                    continue

                relevant.append({
                    "id": results["ids"][i],
                    "text": doc,
                    "type": meta.get("insight_type", "observation"),
                    "priority": meta.get("priority", "medium"),
                    "confidence": meta.get("confidence", 0.5),
                    "topic": meta.get("related_topic", ""),
                    "distance": distance,
                })

    return relevant


# Aktualizacja w chat endpoint:
async def chat(req: ChatRequest):
    # ... istniejący kod kroki 1-6 ...

    # 6.5 NEW: Pobierz relevant insighty
    relevant_insights = get_relevant_insights(insight_store, user_msg_clean)

    # 7. Build prompt Z insightami
    system_prompt = build_system_prompt(memories, grounding_result, state, relevant_insights)

    # ... reszta ...

    # Po odpowiedzi: oznacz użyte insighty jako surfaced
    for ins in relevant_insights:
        insight_store.mark_as_surfaced(ins["id"])
```

### 5.3 Naturalność surfowania

**Kluczowa instrukcja w prompt:**

```
[TWOJE NOCNE OBSERWACJE — wiesz to, ale NIE cytuj analizy]
- [CONCERN] Trzeci raz w tym tygodniu piszesz o projekcie po 2 w nocy.
- [PATTERN] Kiedy mówisz o Crohnie, następnego dnia mówisz o pizzy.
[/OBSERWACJE]

Używaj tych obserwacji naturalnie:
- NIE mów "zauważyłam w analizie" / "moje dane wskazują"
- TAK mów jak ktoś kto po prostu wie: "Znowu o 3 w nocy?" / "Pizzę? Naprawdę?"
- Obserwacja to kontekst dla TWOJEJ reakcji, nie coś do wyrecytowania
- Użyj NAJWYŻEJ jednej obserwacji per odpowiedź
- Jeśli obserwacja nie pasuje do kontekstu rozmowy — POMIŃ
```

**Przykłady naturalnego surfowania:**

| Insight | Łukasz mówi | ASTRA reaguje |
|---------|-------------|---------------|
| "3x w tygodniu koduje po 2:00" | "Kończę ten feature" | "O 2:47 w nocy. Trzeci raz w tym tygodniu. Kończysz, czy kończysz się?" |
| "Przestał mówić o ćwiczeniach" | "Muszę ogarnąć siłownię" | "Mhm. Ostatnio nie wspominałeś. Ile tygodni?" |
| "Emocjonalny trend: zmęczenie rośnie" | "Nic ciekawego" | "Nic ciekawego od 5 dni. Wszystko gra?" |

---

## 6. PUŁAPKI I ZABEZPIECZENIA

### 6.1 Halucynacje na własnych wektorach

**Problem:** Gemini widzi klaster "pizza + Crohn" i generuje insight "Łukasz je pizzę żeby radzić sobie ze stresem Crohna" — interpretacja która nie wynika z danych.

**Zabezpieczenia:**

```python
# 1. Strict evidence — prompt wymusza cytowanie danych
SYNTHESIS_GUARDRAIL = """
ZASADA: Każdy insight MUSI mieć evidence_summary z konkretnymi liczbami.
NIE generuj interpretacji psychologicznych.
TAK generuj obserwacje behawioralne ("3x wspomniał X", "przestał mówić o Y").
NIE: "Łukasz ucieka od problemów w kodowanie"
TAK: "Łukasz 3 razy w tym tygodniu kodował po 2 w nocy. Poprzednio korelowało ze zmęczeniem."
"""

# 2. Confidence threshold — odrzuć insighty < 0.6
MIN_INSIGHT_CONFIDENCE = 0.6

# 3. Evidence requirement — insight musi mieć ≥2 wektory jako dowód
MIN_EVIDENCE_VECTORS = 2

# 4. Post-generation validation
def validate_insight(insight: dict) -> bool:
    if insight.get("confidence", 0) < MIN_INSIGHT_CONFIDENCE:
        return False
    if not insight.get("evidence_summary"):
        return False
    # Blacklist psychologicznych interpretacji
    banned_phrases = [
        "podświadomie", "ucieka od", "mechanizm obronny",
        "tłumi", "wyparcie", "projekcja",
    ]
    text = insight.get("insight_text", "").lower()
    if any(phrase in text for phrase in banned_phrases):
        return False
    return True
```

### 6.2 Echo Loops

**Problem:** Insight mówi "Łukasz dużo mówi o projekcie". ASTRA pyta o projekt. Łukasz odpowiada. Następna analiza: "Łukasz JESZCZE WIĘCEJ mówi o projekcie!"

**Zabezpieczenia:**

```python
# 1. Osobna kolekcja = insighty nie trafiają do głównego RAG
#    → nie wpływają na przyszłe klastrowanie ✅

# 2. Surfaced insighty nie powtarzają się
#    → mark_as_surfaced() ✅

# 3. Cooldown per topic — ten sam related_topic max 1x na 3 dni
def should_surface(insight, recent_surfaced):
    topic = insight.get("topic", "")
    for past in recent_surfaced:
        if past["topic"] == topic:
            past_time = datetime.fromisoformat(past["surfaced_at"])
            if (datetime.utcnow() - past_time).days < 3:
                return False  # za wcześnie na ten sam temat
    return True
```

### 6.3 Performance przy 500+ wektorach

**Benchmarki (szacunkowe dla all-MiniLM-L6-v2 na CPU):**

| Operacja | 100 wektorów | 500 wektorów | 2000 wektorów |
|----------|-------------|-------------|---------------|
| ChromaDB `get()` z include embeddings | ~50ms | ~200ms | ~800ms |
| Cosine distance matrix | ~5ms | ~50ms | ~800ms |
| AgglomerativeClustering | ~10ms | ~100ms | ~2s |
| **TOTAL local (bez Gemini)** | **~65ms** | **~350ms** | **~3.6s** |
| Gemini Flash API call | ~1-3s | ~1-3s | ~1-3s |
| **TOTAL z Gemini** | **~2s** | **~3s** | **~6s** |

**Przy 2000+ wektorach:** Dodaj pre-filtrowanie — analizuj tylko wektory z `importance >= 5` lub z ostatnich `days_back` dni. Nie analizuj session_messages nigdy.

```python
# Skalowanie: jeśli >1000 wektorów, ogranicz do top-importance
MAX_VECTORS_FOR_ANALYSIS = 1000

def harvest_vectors_scaled(vector_store, days_back=7, persona_id="astra"):
    vectors = harvest_vectors(vector_store, days_back, persona_id)

    if len(vectors) > MAX_VECTORS_FOR_ANALYSIS:
        # Priorytetyzuj: importance >= 6, potem reszta
        high_imp = [v for v in vectors if v["metadata"].get("importance", 5) >= 6]
        rest = [v for v in vectors if v["metadata"].get("importance", 5) < 6]
        vectors = high_imp + rest[:MAX_VECTORS_FOR_ANALYSIS - len(high_imp)]

    return vectors
```

### 6.4 Fałszywe wzorce

**Problem:** Mała próbka (3 wektory) → "WZORZEC ODKRYTY!" Ale to przypadek.

**Zabezpieczenia:**

```python
# 1. Min cluster size = 3 wektory z ≥2 różnych dni
def is_real_pattern(cluster):
    unique_days = set(v["metadata"].get("timestamp", "")[:10] for v in cluster)
    return len(cluster) >= 3 and len(unique_days) >= 2

# 2. Confidence scoring oparte na rozmiarze próbki
def calculate_pattern_confidence(cluster, total_vectors):
    # Im większy klaster relative do całości, tym większa pewność
    ratio = len(cluster) / max(total_vectors, 1)
    day_spread = len(set(v["metadata"].get("timestamp", "")[:10] for v in cluster))

    confidence = min(1.0, ratio * 5)         # 20% wektorów = confidence 1.0
    confidence *= min(1.0, day_spread / 3)    # potrzebujesz ≥3 dni spread

    return round(confidence, 2)
```

---

## 7. MODUŁ JAKO PRODUKT — MODULARNOŚĆ

### 7.1 Architektura rozdzielna od ASTRY

Cały moduł zaprojektowany jest jako **self-contained engine** z 3 interfejsami:

```python
class NightAnalysisEngine:
    """
    Standalone deep reflection engine.
    Input: vector store with embeddings
    Output: structured insights
    
    Agnostyczny wobec ASTRY — działa na dowolnym ChromaDB z embeddingami.
    """

    def __init__(
        self,
        chroma_client,                      # ChromaDB PersistentClient
        source_collection: str,             # "astra_memory_v1"
        insight_collection: str,            # "astra_insights_v1"
        embedding_function,                 # SentenceTransformer EF
        llm_synthesizer = None,             # callable(prompt) → str
    ):
        ...

    def run(
        self,
        days_back: int = 7,
        persona_id: str = "astra",
        max_insights: int = 5,
    ) -> list[dict]:
        """Pełna analiza: harvest → cluster → synthesize → store."""
        ...

    def get_relevant(self, query: str, n: int = 2) -> list[dict]:
        """Semantic search po insightach — do surfowania."""
        ...
```

### 7.2 Potencjał produktowy

```
NightAnalysisEngine
    ├── ASTRA → "AI companion co wie za dużo"
    ├── ANIMA Corporate → "co twoja firma powtarza na meetingach?"
    ├── Personal Journal → "self-RLHF pattern detector"
    └── Dowolna ChromaDB → "wzorce w twoich danych"
```

**Meta-warstwa z DROGA_DO_ZWYCIESTWA:** Ten moduł to jest właśnie "Pattern Detector" z Modułu 4 (Cross-Project Pattern Detection) — tylko zastosowany na jednym zbiorze danych. Uogólnienie na Unified Vector Lake = osobny produkt: **Personal Intelligence Layer**.

### 7.3 Jak oddzielić od ASTRY

```
backend/
  ├── main.py                     ← ASTRA (nie zmienia się dużo)
  ├── night_analysis/             ← NOWY moduł
  │   ├── __init__.py
  │   ├── engine.py               ← NightAnalysisEngine (standalone)
  │   ├── harvester.py            ← harvest_vectors()
  │   ├── clusterer.py            ← cluster_vectors(), name_cluster()
  │   ├── patterns.py             ← emotional_arc, trends, temporal
  │   ├── synthesizer.py          ← Gemini prompt + validation
  │   ├── insight_store.py        ← InsightStore (ChromaDB kolekcja)
  │   └── scheduler.py            ← APScheduler setup + triggers
  ├── vector_store.py
  └── companion_state.py
```

**Zero coupling** z `companion_state.py` (poza `last_interaction` timestamp).  
**Zero coupling** z `semantic_pipeline.py`.  
**Jedyne dependency:** ChromaDB client + embedding function (już instancjonowane w `main.py`).

---

## 8. KOLEJNOŚĆ IMPLEMENTACJI

### Sprint 1 — Fundament (wartość od razu) — ~6h

| # | Co | Czas | Wartość |
|---|-----|------|---------|
| 1 | `insight_store.py` — InsightStore (osobna kolekcja) | 1h | Infrastruktura |
| 2 | `harvester.py` — harvest_vectors z ChromaDB | 1h | Fundament |
| 3 | `clusterer.py` — AgglomerativeClustering z cosine | 1.5h | Core analiza |
| 4 | `synthesizer.py` — Gemini prompt + validate_insight | 1.5h | Insighty! |
| 5 | `engine.py` — NightAnalysisEngine.run() | 0.5h | Łączy wszystko |
| 6 | Manual trigger endpoint POST `/api/night-analysis/trigger` | 0.5h | Testowanie |

**Po Sprincie 1:** Można ręcznie odpalić analizę i zobaczyć insighty.

### Sprint 2 — Surfowanie (ASTRA używa insightów) — ~4h

| # | Co | Czas | Wartość |
|---|-----|------|---------|
| 7 | `get_relevant_insights()` w chat endpoint | 1h | Insighty trafiają do prompt |
| 8 | Zmiana `build_system_prompt()` — blok [OBSERWACJE] | 1h | ASTRA wie |
| 9 | `mark_as_surfaced()` + cooldown logic | 1h | Nie powtarza |
| 10 | Test: 5 rozmów → sprawdź czy ASTRA reaguje na insighty | 1h | Validacja |

**Po Sprincie 2:** ASTRA naturalnie reaguje na nocne obserwacje w rozmowie.

### Sprint 3 — Automatyzacja — ~3h

| # | Co | Czas | Wartość |
|---|-----|------|---------|
| 11 | `scheduler.py` — APScheduler (cron + inactivity) | 1.5h | Działa w tle |
| 12 | `companion_state.py` — pola `night_analysis_*` | 0.5h | State tracking |
| 13 | `/api/night-analysis/status` — kiedy ostatnia analiza, ile insightów | 0.5h | Debug |
| 14 | `patterns.py` — emotional_arc + temporal_patterns | 0.5h | Głębsza analiza |

### Sprint 4 — Polish — ~3h

| # | Co | Czas | Wartość |
|---|-----|------|---------|
| 15 | Frontend: sekcja "Nocne obserwacje" w debug page | 1h | Visibility |
| 16 | Trend detection (nowe/zanikające tematy) | 1h | Richer insights |
| 17 | Expiry cleanup job (usuń insighty >14 dni) | 0.5h | Higiena |
| 18 | Logi i metryki (ile wektorów, ile klastrów, czas analizy) | 0.5h | Monitoring |

**TOTAL: ~16h pracy Rina (4 sprinty).**

---

## 9. ZALEŻNOŚCI (requirements.txt)

```
# Dodaj do istniejącego requirements.txt:
scikit-learn>=1.3.0         # AgglomerativeClustering + cosine_distances
APScheduler>=3.10.0         # Background scheduler

# Już masz:
# chromadb
# sentence-transformers (all-MiniLM-L6-v2)
# google-genai (Gemini Flash)
# numpy (dependency sentence-transformers)
```

---

## 10. RYZYKA I MITIGATION

| Ryzyko | Prawdopodobieństwo | Impact | Mitigation |
|--------|-------------------|--------|------------|
| Gemini halucynuje na klastrach | Wysoki | Wysoki | Strict evidence prompt + validate_insight() + banned phrases |
| Echo loop (insight → rozmowa → więcej insightów) | Średni | Wysoki | Osobna kolekcja + surfaced flag + topic cooldown 3 dni |
| ChromaDB `get(include=embeddings)` OOM na 5000+ | Niski | Wysoki | MAX_VECTORS_FOR_ANALYSIS=1000 + importance filter |
| APScheduler nie przeżywa restart FastAPI | Pewny | Niski | `night_analysis_last_run` w companion_state → po restart sprawdza czy dzisiejsza analiza była |
| Fałszywe wzorce (3 wektory = "pattern!") | Wysoki | Średni | min_cluster_size=3 + min 2 różne dni + confidence scoring |
| Insight niedopasowany do rozmowy | Średni | Niski | Relevance-triggered surfacing (semantic search) + "POMIŃ jeśli nie pasuje" w prompt |

---

## PODSUMOWANIE DLA RINA

**Zaczynasz od Sprint 1.** Konkretnie, w tej kolejności:

1. Stwórz `backend/night_analysis/__init__.py` (pusty)
2. Stwórz `backend/night_analysis/insight_store.py` — klasa `InsightStore` (osobna kolekcja ChromaDB)
3. Stwórz `backend/night_analysis/harvester.py` — `harvest_vectors()` z ChromaDB
4. Dodaj `scikit-learn` do `requirements.txt`
5. Stwórz `backend/night_analysis/clusterer.py` — `cluster_vectors()` + `name_cluster()`
6. Stwórz `backend/night_analysis/synthesizer.py` — prompt + Gemini call + `validate_insight()`
7. Stwórz `backend/night_analysis/engine.py` — `NightAnalysisEngine` łączący wszystko
8. Dodaj endpoint `POST /api/night-analysis/trigger` w `main.py`
9. Testuj: odppal trigger, sprawdź insighty w ChromaDB

**Jak testujesz Sprint 1:**
```bash
# 1. Start serwer
cd backend && python -m uvicorn main:app --port 8001

# 2. Trigger analizę ręcznie
curl -X POST http://localhost:8001/api/night-analysis/trigger

# 3. Sprawdź wynik
curl http://localhost:8001/api/night-analysis/status
```

Reszta (surfowanie, scheduler, frontend) to Sprint 2-4 — po walidacji że Sprint 1 generuje sensowne insighty.
