"""
Skrypt jednorazowy (WO-4, 2026-07-25): wgrywa seedy "własnego życia" Astry do ChromaDB.
source='own_life' → zwykły retrieval (NIE always-include), usuwalny jednym where.
Uruchom NA VPS:
  cd /var/www/myastra/astra/backend
  venv/bin/python load_own_life.py

Odwracalność:
  venv/bin/python -c "from vector_store import VectorStore; VectorStore().collection.delete(where={'source':'own_life'})"
"""
import os
import json
from pathlib import Path
from dotenv import load_dotenv
from vector_store import VectorStore

# KLUCZOWE: own_life idzie Kanałem 1 (user-filtered) — musi mieć TEN SAM user_id/salt co aplikacja,
# inaczej hash usera się nie zgadza i retrieval je odrzuca (bug złapany smoke-testem 25.07).
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
USER_ID = "lukasz"
USER_ID_SALT = os.getenv("USER_ID_SALT", "astra_default_salt_change_me")

vs = VectorStore()

path = Path(__file__).parent / "prompts" / "own_life.json"
with open(path, "r", encoding="utf-8") as f:
    seeds = json.load(f)

print(f"Wgrywam {len(seeds)} seedów own_life...\n")

for s in seeds:
    trigger = s["metadata"]["trigger"]
    mem_id = vs.add_memory(
        text=s["text"],
        user_id=USER_ID,
        salt=USER_ID_SALT,
        persona_id="astra",
        source=s["source"],
        importance=s.get("importance", 5),
        entity_subtype=trigger,
        origin_endpoint="seed_own_life",
        origin_persona_turn="system",
    )
    print(f"  {'✓' if mem_id else '· (pominięty — za krótki?)'} {trigger}")

total = vs.collection.count()
print(f"\nGotowe. own_life w bazie. Łącznie wektorów w kolekcji: {total}")
