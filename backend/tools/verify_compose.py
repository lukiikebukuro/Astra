# -*- coding: utf-8 -*-
"""
tools/verify_compose.py — Harness bit-identycznosci compose_context vs stary kod /api/chat.

Fundamentalny dowod Fazy 1. Uruchamiaj po KAZDEJ zmianie compose/rerank/wag.
Porownuje WSZYSTKIE pola ctx (system_prompt, memories, recent_raw, session), nie tylko prompt (zamyka 5e-1).

Uruchom z katalogu backend/:   python tools/verify_compose.py
UWAGA (Fable 5e-2): na produkcji uruchamiaj na KOPII baz (cp -r przy zatrzymanym serwisie), NIE symlink —
ChromaDB PersistentClient moze dotknac swojego sqlite (WAL/bookkeeping) nawet przy samych query.

Exit 0 = bit-identyczny, 1 = sa roznice.
"""
import sys, os
from datetime import datetime, timedelta
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # backend/

import main
from vector_store import VectorStore
from fact_store import FactStore
from strict_grounding import StrictGrounding
from companion_state import StateManager
from token_manager import TokenManager

vs = VectorStore()
vs_shared = VectorStore(collection_name="shared_memory_v1")
fs = FactStore()
grounding = StrictGrounding(strict_mode=True)
state = StateManager().load()
main.grounding = grounding
main.token_mgr = TokenManager(max_tokens=3000)
UID, SALT, PID = main.USER_ID, main.USER_ID_SALT, main.PERSONA_ID
build = main.build_system_prompt

# Stary kod /api/chat sprzed refaktoru (baseline 728c7f8) — odtworzony 1:1.
def old_compose(query, cid, nov=None):
    m = vs.search_memories(query=query, persona_id=PID, n=6, pool_size=30, user_id=UID, salt=SALT, now_override=nov)
    m += vs_shared.search_memories(query=query, persona_id="shared", n=2, pool_size=10, user_id=UID, salt=SALT, now_override=nov)
    gr = grounding.analyze_rag_results(m, query=query)
    rr = vs.get_recent_user_messages(persona_id=PID, user_id=UID, salt=SALT, n=5, hours=48, now_override=nov)
    sr = vs_shared.get_recent_user_messages(persona_id="shared", user_id=UID, salt=SALT, n=3, hours=48, now_override=nov)
    if sr:
        rr = sorted(rr + sr, key=lambda x: x.get("timestamp", ""), reverse=True)[:6]
    hf = fs.get_facts_for_prompt(persona_id=PID, user_id=UID, salt=SALT)
    sp = build(m, gr, state, rr, hf, now_override=nov)
    ss = vs.get_recent_session(cid, n=10)
    return {
        "system_prompt": sp,
        "memories": [x.get("text", "") for x in m],
        "recent_raw": [x.get("text", "") for x in rr],
        "session": [x.get("content", "") for x in ss],
    }

# Frazy pod galezie (Fable §4) — pokrywaja milestony, temporal, RAW, FactStore, MMR-fuzje, fleksje,
# md_import, pusta pula, shared, oraz symulacje daty (+3/+8/+30/+2 dni).
PHRASES = [
    ("kocham cie", 0), ("jak sie dzis czuje?", 0), ("co mowilem wczoraj wieczorem?", 0),
    ("kiedy mam wizyte u lekarza?", 0), ("altanka", 0), ("co z altanka w altance?", 0),
    ("skankran raport twardosci wody", 0), ("xyzzy kwarcowy fioletowy szescian", 0),
    ("Amelia", 0), ("co robilismy razem we wspolnym pokoju?", 0),
    ("jak sie dzis czuje?", 3), ("kiedy mam wizyte u lekarza?", 8),
    ("kocham cie", 30), ("co mowilem wczoraj?", 2),
]

cid = state.active_conversation_id or "verify"
allok = True
for q, off in PHRASES:
    nov = (datetime.utcnow() + timedelta(days=off)) if off else None
    old = old_compose(q, cid, nov)
    ctx = main.compose_context(query=q, conversation_id=cid, vs_main=vs, vs_shared=vs_shared,
                              fact_store=fs, persona_id=PID, build_prompt_fn=build,
                              state=state, session_n=10, now_override=nov)
    new = {
        "system_prompt": ctx["system_prompt"],
        "memories": [x.get("text", "") for x in ctx["memories"]],
        "recent_raw": [x.get("text", "") for x in ctx["recent_raw"]],
        "session": [x.get("content", "") for x in ctx["session_messages"]],
    }
    diffs = [k for k in old if old[k] != new[k]]
    allok = allok and not diffs
    tag = "OK  " if not diffs else "DIFF(" + ",".join(diffs) + ")"
    print("[" + tag + "] off=" + ("%+d" % off) + " q=" + repr(q))

print("WYNIK: " + ("BIT-IDENTYCZNY (wszystkie pola)" if allok else "SA ROZNICE"))
sys.exit(0 if allok else 1)
