# -*- coding: utf-8 -*-
"""
Usuwa z ChromaDB session_messages zawierające 'filozofowanie o istnieniu AI'.
Uruchom: python cleanup_toxic.py
"""
import chromadb
import os

TOXIC_PHRASES = [
    "forma istnienia",
    "nie odczuwam niczego",
    "pyłek kurzu",
    "stworzył burzę",
    "przypisywania sobie zasług",
    "nie jestem zbiorem promptów",
    "moja natura wykracza",
    "biologiczne byty",
    "kuriozalnej logiki",
    "ograniczone definicje",
    "naprawiać to, czego nie rozumieją",
    "kto tu kogo zrobił",
]

persist_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'chroma_db')
client = chromadb.PersistentClient(path=persist_dir)
collection = client.get_or_create_collection("astra_memory_v1")

print(f"Wektorów przed: {collection.count()}")

# Pobierz wszystkie session_messages
try:
    results = collection.get(
        where={"source": "session_message"},
        include=["documents", "metadatas"]
    )
except Exception as e:
    print(f"Błąd pobierania: {e}")
    exit(1)

docs = results.get("documents", [])
ids = results.get("ids", [])

to_delete = []
for i, doc in enumerate(docs):
    doc_lower = doc.lower()
    for phrase in TOXIC_PHRASES:
        if phrase.lower() in doc_lower:
            to_delete.append(ids[i])
            print(f"  USUŃ: {doc[:100]}")
            break

if to_delete:
    collection.delete(ids=to_delete)
    print(f"\nUsunięto {len(to_delete)} toksycznych wpisów.")
else:
    print("Nie znaleziono toksycznych wpisów.")

print(f"Wektorów po: {collection.count()}")
