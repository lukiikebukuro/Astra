"""
Skrypt jednorazowy: wgrywa 20 wektorów character_core do ChromaDB.
Uruchom NA VPS po resecie bazy:
  cd /root/[ścieżka]/backend
  python3 load_character_vectors.py
"""
import json
from pathlib import Path
from vector_store import VectorStore

vs = VectorStore()

vectors_path = Path(__file__).parent / "prompts" / "character_vectors.json"
with open(vectors_path, "r", encoding="utf-8") as f:
    vectors = json.load(f)

print(f"Wgrywam {len(vectors)} wektorów character_core...\n")

for v in vectors:
    trigger = v["metadata"]["trigger"]
    vs.add_memory(
        text=v["text"],
        user_id="system",
        salt=f"character_core_{trigger}",
        persona_id="astra",
        source=v["source"],
        importance=v["importance"],
    )
    print(f"  ✓ {trigger}")

print(f"\nGotowe. Załadowano {len(vectors)} wektorów.")
print("Możesz teraz zrestartować serwis: systemctl restart myastra.service")
