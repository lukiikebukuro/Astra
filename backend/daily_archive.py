#!/usr/bin/env python3
"""
ASTRA — Daily Archive
Zapisuje wszystkie wiadomości sesji (Astra + Łukasz) z poprzedniego dnia UTC.
Uruchamiane codziennie o 04:00 przez APScheduler w main.py.
Output: backend/sesje_archiwum/YYYY-MM-DD.json
Format: identyczny jak wazne/logi/*.json (timestamp, role, content, thought, hint)
"""

from datetime import datetime, timedelta
from pathlib import Path
import json


def run_daily_archive(vector_store, target_date=None, label="astra"):
    """
    Archiwizuje wiadomości sesji z target_date (default: wczoraj UTC).
    Pomija dni bez rozmów — nie tworzy pustych plików.

    label: "astra"  → plik {date}.json (kompatybilność wsteczna)
           inne (np. "amelia", "wspolny") → plik {label}_{date}.json
    Dzięki temu sesje Amelii i Wspólnego Pokoju też mają trwałe archiwum na dysku,
    odporne na flash-reset kolekcji sesji w ChromaDB.
    """
    if target_date is None:
        target_date = (datetime.utcnow() - timedelta(days=1)).date()

    date_str = str(target_date)  # "YYYY-MM-DD"
    date_prefix = date_str + "T"

    archive_dir = Path(__file__).parent / "sesje_archiwum"
    archive_dir.mkdir(exist_ok=True)
    fname = f"{date_str}.json" if label == "astra" else f"{label}_{date_str}.json"
    output_path = archive_dir / fname

    if output_path.exists():
        print(f"[ARCHIVE:{label}] {date_str}: plik już istnieje, pomijam")
        return str(output_path)

    try:
        results = vector_store.session_collection.get(
            include=["documents", "metadatas"]
        )
    except Exception as e:
        print(f"[ARCHIVE:{label}] Błąd pobierania sesji: {e}")
        return None

    if not results["documents"]:
        print(f"[ARCHIVE:{label}] Brak wiadomości w kolekcji sesji")
        return None

    messages = []
    for i, doc in enumerate(results["documents"]):
        meta = results["metadatas"][i]
        ts = meta.get("timestamp", "")
        if not ts.startswith(date_prefix):
            continue
        if meta.get("source") != "session_message":
            continue
        messages.append({
            "timestamp": ts,
            "role": meta.get("role", ""),
            "content": doc,
            "thought": meta.get("thought", ""),
            "hint": meta.get("hint", ""),
        })

    if not messages:
        print(f"[ARCHIVE:{label}] {date_str}: brak rozmów — plik nie zostanie utworzony")
        return None

    messages.sort(key=lambda m: m["timestamp"])

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(messages, f, ensure_ascii=False, indent=2)

    print(f"[ARCHIVE:{label}] {date_str}: {len(messages)} wiadomości → sesje_archiwum/{fname}")
    return str(output_path)


if __name__ == "__main__":
    import sys
    from vector_store import VectorStore

    # Ręczne uruchomienie: python daily_archive.py [YYYY-MM-DD]
    vs = VectorStore(collection_name="astra_memory_v1")

    if len(sys.argv) > 1:
        from datetime import date
        target = date.fromisoformat(sys.argv[1])
        print(f"[ARCHIVE] Tryb ręczny: archiwizuję {target}")
        run_daily_archive(vs, target_date=target)
    else:
        yesterday = (datetime.utcnow() - timedelta(days=1)).date()
        print(f"[ARCHIVE] Tryb ręczny: archiwizuję wczoraj ({yesterday})")
        run_daily_archive(vs)
