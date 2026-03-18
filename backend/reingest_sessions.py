"""
Re-ingestion script — przepuszcza istniejące session_messages przez nowy pipeline
i zapisuje przetworzone encje jako enriched wektory.

Uruchom RAZ na VPS:
    cd /var/www/myastra/astra/backend
    venv/bin/python3 reingest_sessions.py

Bezpieczny — nie usuwa nic, tylko DODAJE nowe wektory.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from vector_store import VectorStore
from semantic_pipeline import SemanticPipeline
from datetime import datetime

PERSONA_ID = "astra"
USER_ID = os.getenv("USER_ID", "lukasz")
USER_ID_SALT = os.getenv("USER_ID_SALT", "")
MIN_LENGTH = 30  # pomijaj bardzo krótkie wiadomości
MIN_CONFIDENCE = 0.50

def main():
    vs = VectorStore()
    pipeline = SemanticPipeline()

    print(f"[REINGEST] Start — {datetime.now().isoformat()}")
    print(f"[REINGEST] Baza: {vs.collection.count()} wektorów")

    # Pobierz wszystkie session_messages roli user (nie Astry)
    all_data = vs.collection.get(
        where={"$and": [
            {"source": "session_message"},
            {"persona_id": PERSONA_ID},
        ]},
        include=["documents", "metadatas"]
    )

    docs = all_data.get("documents", [])
    metas = all_data.get("metadatas", [])

    user_msgs = [
        (doc, meta) for doc, meta in zip(docs, metas)
        if meta.get("role") == "user" and len(doc) >= MIN_LENGTH
    ]

    print(f"[REINGEST] User session_messages do przetworzenia: {len(user_msgs)}")

    stored = 0
    skipped = 0

    for i, (text, meta) in enumerate(user_msgs):
        try:
            memories = pipeline.process_message(text, companion_id=PERSONA_ID,
                                                min_confidence=MIN_CONFIDENCE)
            if not memories:
                skipped += 1
                continue

            for mem in memories:
                if mem.action == 'skip':
                    continue

                source_map = {
                    'EMOTION': 'extracted_emotion',
                    'FACT': 'extracted_fact',
                    'PERSON': 'extracted_person',
                    'DATE': 'extracted_date',
                    'MILESTONE': 'enriched',
                    'SHARED_THING': 'enriched',
                    'GOAL': 'extracted_goal',
                    'MEDICATION': 'extracted_medication',
                    'MEASUREMENT': 'enriched',
                    'FINANCIAL': 'enriched',
                }
                source = source_map.get(mem.entity_type, 'enriched')

                is_milestone = mem.entity_type in ('MILESTONE', 'SHARED_THING')
                vs.add_memory(
                    text=mem.text,
                    source=source,
                    importance=mem.importance,
                    persona_id=PERSONA_ID,
                    user_id=USER_ID,
                    salt=USER_ID_SALT,
                    is_milestone=is_milestone,
                    timestamp=meta.get('timestamp'),
                )
                stored += 1

        except Exception as e:
            print(f"[REINGEST] Błąd dla msg {i}: {e}")
            skipped += 1

        if (i + 1) % 10 == 0:
            print(f"[REINGEST] {i+1}/{len(user_msgs)} — zapisano {stored}, pominięto {skipped}")

    print(f"\n[REINGEST] DONE — zapisano {stored} encji, pominięto {skipped}")
    print(f"[REINGEST] Baza po: {vs.collection.count()} wektorów")

if __name__ == "__main__":
    main()
