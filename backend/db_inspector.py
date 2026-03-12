"""
ASTRA - DB Inspector
Diagnostyka bazy wektorowej: jakość danych, szum, reranker.

Uruchomienie: venv/bin/python3 db_inspector.py
"""

import os
import sys
from collections import Counter
from datetime import datetime
from vector_store import VectorStore

vs = VectorStore()
col = vs.collection

print("=" * 60)
print("ASTRA DB INSPECTOR")
print(f"Łączna liczba wektorów: {col.count()}")
print("=" * 60)

# ── 1. Rozkład źródeł ──
print("\n[1] ROZKŁAD ŹRÓDEŁ (source)")
all_data = col.get(include=["metadatas"])
sources = Counter(m.get("source", "?") for m in all_data["metadatas"])
for source, count in sorted(sources.items(), key=lambda x: -x[1]):
    bar = "█" * min(count, 40)
    print(f"  {source:<30} {count:>4}  {bar}")

# ── 2. Rozkład importance ──
print("\n[2] ROZKŁAD IMPORTANCE (1-10)")
importances = Counter(m.get("importance", 0) for m in all_data["metadatas"])
for imp in range(1, 11):
    count = importances.get(imp, 0)
    bar = "█" * min(count, 40)
    print(f"  imp={imp}  {count:>4}  {bar}")

# ── 3. Szum — krótkie wektory (potencjalny bałagan) ──
print("\n[3] POTENCJALNY SZUM (teksty < 5 słów)")
all_texts = col.get(include=["documents", "metadatas"])
noise = []
for text, meta in zip(all_texts["documents"], all_texts["metadatas"]):
    if text and len(text.split()) < 5:
        noise.append((text, meta.get("source", "?"), meta.get("importance", 0)))

if noise:
    print(f"  Znaleziono {len(noise)} krótkich wektorów:")
    for text, source, imp in noise[:20]:
        print(f"  [{source}, imp={imp}] '{text}'")
    if len(noise) > 20:
        print(f"  ... i {len(noise)-20} więcej")
else:
    print("  Brak szumu. Czysto.")

# ── 4. Test rerankera — zapytanie próbne ──
print("\n[4] TEST RERANKERA")
test_queries = [
    "Crohn choroba jelita",
    "projekt LDI AI",
    "zmęczony energia",
]

for query in test_queries:
    print(f"\n  Query: '{query}'")
    try:
        results = vs.search(
            query=query,
            user_id="lukasz",
            salt=os.getenv("USER_ID_SALT", "default_salt"),
            persona_id="astra",
            n_results=3,
        )
        if results:
            for r in results:
                score = r.get("final_score", 0)
                dist = r.get("distance", 0)
                src = r.get("metadata", {}).get("source", "?")
                imp = r.get("metadata", {}).get("importance", 0)
                text = r.get("text", "")[:60]
                print(f"    score={score:.3f} dist={dist:.3f} [{src}, imp={imp}] {text}")
        else:
            print("    Brak wyników (baza pusta lub brak pasujących)")
    except Exception as e:
        print(f"    Błąd: {e}")

# ── 5. Ostatnio dodane wektory ──
print("\n[5] OSTATNIO DODANE (top 5 najnowszych)")
try:
    all_with_ts = col.get(include=["documents", "metadatas"])
    items = list(zip(all_with_ts["documents"], all_with_ts["metadatas"]))
    items_with_ts = [
        (doc, meta) for doc, meta in items
        if meta.get("timestamp") and meta.get("source") != "session_message"
    ]
    items_with_ts.sort(key=lambda x: x[1].get("timestamp", ""), reverse=True)
    for doc, meta in items_with_ts[:5]:
        ts = meta.get("timestamp", "?")[:16]
        src = meta.get("source", "?")
        imp = meta.get("importance", 0)
        print(f"  [{ts}] [{src}, imp={imp}] {doc[:70]}")
except Exception as e:
    print(f"  Błąd: {e}")

print("\n" + "=" * 60)
print("KONIEC DIAGNOSTYKI")
print("=" * 60)
