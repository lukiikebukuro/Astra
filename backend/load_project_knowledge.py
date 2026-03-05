"""
Wgrywa wiedzę o projektach Łukasza do ChromaDB.
Uruchom: venv/bin/python3 load_project_knowledge.py
"""
import json
from pathlib import Path
from vector_store import VectorStore

vs = VectorStore()

vectors_path = Path(__file__).parent / "prompts" / "project_knowledge.json"
with open(vectors_path, "r", encoding="utf-8") as f:
    vectors = json.load(f)

print(f"Wgrywam {len(vectors)} wektorów wiedzy o projektach...\n")

for v in vectors:
    project = v["metadata"]["project"]
    aspect = v["metadata"]["aspect"]
    vs.add_memory(
        text=v["text"],
        user_id="system",
        salt=f"project_knowledge_{project}_{aspect}",
        persona_id="astra",
        source=v["source"],
        importance=v["importance"],
    )
    print(f"  ✓ [{project}] {aspect}")

print(f"\nGotowe. Załadowano {len(vectors)} wektorów.")
