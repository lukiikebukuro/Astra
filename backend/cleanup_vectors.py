# -*- coding: utf-8 -*-
"""
ASTRA — Czyszczenie zatrutych wektorów z ChromaDB.

Usuwa 3 kategorie śmieci:
  1. user_message_raw       — własny styl pisania Łukasza, similarity ~0.965, bezużyteczne
  2. Błędne milestony       — korekty błędów AI zaindeksowane jako MILESTONE:trust_declaration
  3. Stare emocje           — EMOTION bez entity_subtype w metadata (supersede ich nie wyczyściło)

Uruchomienie (dry run):
  python cleanup_vectors.py

Uruchomienie (faktyczne usunięcie):
  python cleanup_vectors.py --delete

ZAWSZE zrób backup przed usunięciem:
  cp -r chroma_db chroma_db_backup_$(date +%Y%m%d)
"""

import sys
import os
from datetime import datetime, timezone

import chromadb

DRY_RUN = "--delete" not in sys.argv

CORRECTION_KEYWORDS = [
    'nigdy tego', 'nigdy bym', 'to nieprawda', 'pomyliłaś', 'pomylił',
    'mylisz się', 'to nie tak', 'źle pamiętasz', 'nie pamiętasz',
    'wcale nie mówiłem', 'nie powiedziałem', 'błędnie', 'masz błędną',
    'nie mówiłem że', 'poprawiam cię', 'to było inaczej', 'nie zgadza się',
    'poprawiam:', 'korygując:', 'to jest nieprawidłowe', 'złą informację',
    'earl grey', 'pomyliłeś', 'nieprawda że',
]

# Emocje starsze niż X dni bez entity_subtype → kandydaci do usunięcia
OLD_EMOTION_DAYS = 60

persist_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'chroma_db')
client = chromadb.PersistentClient(path=persist_dir)
collection = client.get_or_create_collection("astra_memory_v1")

print("=" * 60)
print("ASTRA — CLEANUP VECTORS")
print(f"Tryb: {'DRY RUN (bez zmian)' if DRY_RUN else '⚠️  FAKTYCZNE USUNIĘCIE'}")
print(f"Wektorów przed: {collection.count()}")
print("=" * 60)

all_data = collection.get(include=["documents", "metadatas"])
all_ids = all_data["ids"]
all_docs = all_data["documents"]
all_metas = all_data["metadatas"]

to_delete = {}  # id -> powód

# ── 1. user_message_raw ──────────────────────────────────────────────────────
print("\n[1] USER_MESSAGE_RAW — własne wiadomości Łukasza")
count = 0
for i, meta in enumerate(all_metas):
    if meta.get("source") == "user_message_raw":
        to_delete[all_ids[i]] = "user_message_raw"
        count += 1
        if count <= 5:
            print(f"  USUŃ: [{all_ids[i][:8]}...] {all_docs[i][:80]}")
if count > 5:
    print(f"  ... i {count - 5} więcej")
print(f"  Razem: {count} wektorów")

# ── 2. Błędne milestony (korekty) ───────────────────────────────────────────
print("\n[2] BŁĘDNE MILESTONY — korekty błędów AI")
count = 0
for i, (doc, meta) in enumerate(zip(all_docs, all_metas)):
    if not meta.get("is_milestone"):
        continue
    doc_lower = (doc or "").lower()
    matched_kw = next((kw for kw in CORRECTION_KEYWORDS if kw in doc_lower), None)
    if matched_kw:
        to_delete[all_ids[i]] = f"milestone+correction_keyword:{matched_kw}"
        count += 1
        print(f"  USUŃ: [{meta.get('source','?')}] '{doc[:80]}' (kw: {matched_kw})")
print(f"  Razem: {count} wektorów")

# ── 3. Stare emocje bez entity_subtype ──────────────────────────────────────
print(f"\n[3] STARE EMOCJE — source=extracted_emotion, brak entity_subtype, starsze niż {OLD_EMOTION_DAYS} dni")
count = 0
now = datetime.now(timezone.utc).replace(tzinfo=None)
for i, (doc, meta) in enumerate(zip(all_docs, all_metas)):
    if meta.get("source") != "extracted_emotion":
        continue
    if meta.get("entity_subtype"):
        continue  # ma subtype — supersede może go ogarnąć
    ts_str = meta.get("timestamp", "")
    if not ts_str:
        # Brak timestamp → stary wpis, usuń
        to_delete[all_ids[i]] = "extracted_emotion+no_timestamp+no_subtype"
        count += 1
        if count <= 5:
            print(f"  USUŃ (brak ts): [{all_ids[i][:8]}...] {doc[:80]}")
        continue
    try:
        ts = datetime.fromisoformat(ts_str.replace('Z', '+00:00')).replace(tzinfo=None)
        age_days = (now - ts).days
        if age_days > OLD_EMOTION_DAYS:
            to_delete[all_ids[i]] = f"extracted_emotion+no_subtype+{age_days}d_old"
            count += 1
            if count <= 5:
                print(f"  USUŃ ({age_days}d): [{all_ids[i][:8]}...] {doc[:80]}")
    except (ValueError, TypeError):
        pass
if count > 5:
    print(f"  ... i {count - 5} więcej")
print(f"  Razem: {count} wektorów")

# ── Podsumowanie ─────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print(f"DO USUNIĘCIA: {len(to_delete)} wektorów")
print(f"ZOSTAJE:      {collection.count() - len(to_delete)} wektorów")
print("=" * 60)

if DRY_RUN:
    print("\nDRY RUN — nic nie usunięto.")
    print("Aby faktycznie usunąć: python cleanup_vectors.py --delete")
else:
    if not to_delete:
        print("\nNic do usunięcia.")
    else:
        ids_to_delete = list(to_delete.keys())
        # ChromaDB przyjmuje max ~5000 na raz
        batch_size = 500
        for j in range(0, len(ids_to_delete), batch_size):
            batch = ids_to_delete[j:j + batch_size]
            collection.delete(ids=batch)
        print(f"\n✅ Usunięto {len(to_delete)} wektorów.")
        print(f"Wektorów po: {collection.count()}")
