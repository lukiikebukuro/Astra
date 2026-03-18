"""
Migracja session_messages z astra_memory_v1 → astra_memory_session_v1

Uruchom RAZ na VPS po wdrożeniu nowego vector_store.py:
    cd /var/www/myastra/astra/backend
    venv/bin/python3 migrate_sessions_to_separate_collection.py

Bezpieczny — kopiuje wektory, NIE kasuje oryginałów do momentu potwierdzenia.
Po sukcesie wyświetla one-liner do usunięcia starych session_messages z głównej kolekcji.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from vector_store import VectorStore
from datetime import datetime

MEMORY_COL = "astra_memory_v1"
SESSION_COL = "astra_memory_session_v1"


def main():
    print(f"[MIGRATE] Start — {datetime.now().isoformat()}")

    # Otwórz główną kolekcję bezpośrednio (nie przez VectorStore, żeby nie tworzyć session_col)
    import chromadb
    from chromadb.utils import embedding_functions

    persist_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'chroma_db')
    client = chromadb.PersistentClient(path=persist_dir)
    ef = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="paraphrase-multilingual-MiniLM-L12-v2"
    )

    mem_col = client.get_or_create_collection(name=MEMORY_COL, embedding_function=ef)
    ses_col = client.get_or_create_collection(name=SESSION_COL, embedding_function=ef)

    print(f"[MIGRATE] astra_memory_v1: {mem_col.count()} wektorów")
    print(f"[MIGRATE] astra_memory_session_v1: {ses_col.count()} wektorów (przed migracją)")

    # Pobierz wszystkie session_messages z głównej kolekcji
    all_data = mem_col.get(
        where={"source": "session_message"},
        include=["documents", "metadatas", "embeddings"]
    )

    ids = all_data.get("ids", [])
    docs = all_data.get("documents", [])
    metas = all_data.get("metadatas", [])
    embeddings = all_data.get("embeddings", [])

    print(f"[MIGRATE] Session_messages do przeniesienia: {len(ids)}")

    if not ids:
        print("[MIGRATE] Brak session_messages w głównej kolekcji — migracja zbędna.")
        return

    # Kopiuj do session_collection w batchach po 100
    BATCH = 100
    migrated = 0
    for i in range(0, len(ids), BATCH):
        batch_ids = ids[i:i+BATCH]
        batch_docs = docs[i:i+BATCH]
        batch_metas = metas[i:i+BATCH]
        batch_embs = embeddings[i:i+BATCH] if embeddings else None

        if batch_embs:
            ses_col.upsert(
                ids=batch_ids,
                documents=batch_docs,
                metadatas=batch_metas,
                embeddings=batch_embs,
            )
        else:
            ses_col.upsert(
                ids=batch_ids,
                documents=batch_docs,
                metadatas=batch_metas,
            )
        migrated += len(batch_ids)
        print(f"[MIGRATE] {migrated}/{len(ids)} przeniesiono...")

    print(f"\n[MIGRATE] Sukces — {migrated} wektorów w astra_memory_session_v1")
    print(f"[MIGRATE] astra_memory_session_v1: {ses_col.count()} wektorów (po migracji)")

    print("""
[MIGRATE] NASTĘPNY KROK — usuń stare session_messages z głównej kolekcji:

    cd /var/www/myastra/astra/backend && venv/bin/python3 -c "
import chromadb
client = chromadb.PersistentClient(path='chroma_db')
col = client.get_collection('astra_memory_v1')
r = col.get(where={'source': 'session_message'})
ids = r['ids']
if ids:
    col.delete(ids=ids)
    print(f'Usunieto {len(ids)} session_messages z astra_memory_v1')
else:
    print('Brak session_messages do usuniecia')
"
""")


if __name__ == "__main__":
    main()
