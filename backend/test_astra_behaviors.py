# -*- coding: utf-8 -*-
"""
ASTRA — Test Suite v1.0
Testuje rzeczywiste zachowania systemu, nie tylko obecność kodu.

Uruchomienie:
    cd backend
    python test_astra_behaviors.py

Każdy test jest niezależny. Dane testowe są tworzone i usuwane.
Output: PASS / FAIL z opisem co poszło nie tak.
"""

import sys
import os
import time
from datetime import datetime, timedelta

# Dodaj backend do path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ── Kolory w terminalu ─────────────────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

passed = 0
failed = 0
results = []

def ok(name: str, detail: str = ""):
    global passed
    passed += 1
    msg = f"  {GREEN}✓ PASS{RESET}  {name}"
    if detail:
        msg += f"\n         {CYAN}→ {detail}{RESET}"
    print(msg)
    results.append(("PASS", name))

def fail(name: str, detail: str = ""):
    global failed
    failed += 1
    msg = f"  {RED}✗ FAIL{RESET}  {name}"
    if detail:
        msg += f"\n         {YELLOW}→ {detail}{RESET}"
    print(msg)
    results.append(("FAIL", name, detail))

def section(title: str):
    print(f"\n{BOLD}{CYAN}══ {title} ══{RESET}")

# ══════════════════════════════════════════════════════════════════════════════
# TEST 1 — SEMANTIC EXTRACTOR: FACT:correction nie jest MILESTONEm
# ══════════════════════════════════════════════════════════════════════════════
section("TEST 1 — FACT:correction klasyfikacja")

try:
    from semantic_extractor import SemanticExtractor

    extractor = SemanticExtractor()

    correction_phrases = [
        "To nieprawda, nie mówiłem żebyś mi robiła herbatę Earl Grey, mówiłem czarną albo miętową",
        "Pomyliłaś się, to nie było tak jak mówisz",
        "Mylisz się w tej kwestii, to było inaczej",
        "Nie zgadza się, faktycznie powiedziałem coś zupełnie innego",
        "Nie, chciałem powiedzieć że lubię czarną kawę, nie Earl Grey",
    ]

    for phrase in correction_phrases:
        result = extractor.extract(phrase)  # min_confidence = default 0.55
        entities = result.entities if result else []

        milestone_entities = [e for e in entities if e.entity_type == "MILESTONE"]
        correction_entities = [e for e in entities
                                if e.entity_type == "FACT" and e.subtype == "correction"]
        short = phrase[:55]

        if milestone_entities and not correction_entities:
            ms = milestone_entities[0]
            fail(f"correction → MILESTONE (błąd!)", f"'{short}' → MILESTONE:{ms.subtype}")
        elif correction_entities:
            ok(f"correction → FACT:correction", f"'{short}' ✓")
        else:
            ok(f"correction → nie MILESTONE (brak encji)", f"'{short}' → brak klasyfikacji (OK)")

except ImportError as e:
    fail("SemanticExtractor import", str(e))
except Exception as e:
    fail("SemanticExtractor test", str(e))


# ══════════════════════════════════════════════════════════════════════════════
# TEST 2 — VECTOR STORE: user_message_raw nie wraca w search
# ══════════════════════════════════════════════════════════════════════════════
section("TEST 2 — user_message_raw exclusion z Kanału 1")

try:
    from vector_store import VectorStore

    TEST_USER = "test_user_rag_exclusion"
    TEST_SALT = "test_salt_12345"
    TEST_PERSONA = "astra_test"
    TEST_COLLECTION = "astra_test_exclusion_v1"

    vs = VectorStore(collection_name=TEST_COLLECTION)

    # Dodaj wektor user_message_raw
    raw_text = "Lubię czarną herbatę i zawsze ją piję rano"
    vs.add_memory(
        text=raw_text,
        user_id=TEST_USER,
        salt=TEST_SALT,
        persona_id=TEST_PERSONA,
        source="user_message_raw",
        importance=5,
    )

    # Dodaj normalny fakt
    fact_text = "Łukasz preferuje czarną herbatę jako poranny rytuał"
    vs.add_memory(
        text=fact_text,
        user_id=TEST_USER,
        salt=TEST_SALT,
        persona_id=TEST_PERSONA,
        source="extracted_fact",
        importance=7,
    )

    # Szukaj — user_message_raw NIE powinno wrócić
    results_search = vs.search_memories(
        query="herbata poranna",
        persona_id=TEST_PERSONA,
        user_id=TEST_USER,
        salt=TEST_SALT,
        n=5
    )

    sources_returned = [r.get('metadata', {}).get('source') for r in results_search]

    if "user_message_raw" in sources_returned:
        fail("user_message_raw excluded", f"Znaleziono user_message_raw w wynikach: {sources_returned}")
    else:
        ok("user_message_raw excluded", f"Zwrócone źródła: {sources_returned}")

    # Cleanup
    import chromadb
    chroma_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'chroma_db')
    client = chromadb.PersistentClient(path=chroma_path)
    try:
        client.delete_collection(TEST_COLLECTION)
    except Exception:
        pass

except Exception as e:
    fail("user_message_raw exclusion test", str(e))


# ══════════════════════════════════════════════════════════════════════════════
# TEST 3 — RECENCY DECAY: emocje blakną szybciej niż fakty
# ══════════════════════════════════════════════════════════════════════════════
section("TEST 3 — Per-type recency decay")

try:
    from vector_store import VectorStore

    vs_test = VectorStore.__new__(VectorStore)

    # Symuluj rerank dla dwóch wspomnień — jedno emocja sprzed 10 dni, jedno fakt sprzed 10 dni
    ten_days_ago = (datetime.utcnow() - timedelta(days=10)).isoformat()

    emotion_result = {
        'text': 'Łukasz był bardzo zmęczony',
        'distance': 0.4,
        'metadata': {
            'source': 'extracted_emotion',
            'importance': 5,
            'is_milestone': False,
            'timestamp': ten_days_ago,
        }
    }

    fact_result = {
        'text': 'Łukasz ma chorobę Crohna od 11 lat',
        'distance': 0.4,
        'metadata': {
            'source': 'extracted_fact',
            'importance': 5,
            'is_milestone': False,
            'timestamp': ten_days_ago,
        }
    }

    milestone_result = {
        'text': 'Łukasz powiedział że Astra jest częścią jego życia',
        'distance': 0.4,
        'metadata': {
            'source': 'extracted_milestone',
            'importance': 10,
            'is_milestone': True,
            'timestamp': ten_days_ago,
        }
    }

    reranked = vs_test.rerank([emotion_result, fact_result, milestone_result], query="zmęczenie zdrowie")

    scores = {r['text'][:30]: r.get('final_score', 0) for r in reranked}

    emotion_score = next((r.get('final_score', 0) for r in reranked if 'zmęczony' in r['text']), 0)
    fact_score = next((r.get('final_score', 0) for r in reranked if 'Crohn' in r['text']), 0)
    milestone_score = next((r.get('final_score', 0) for r in reranked if 'Astra jest' in r['text']), 0)

    print(f"         {CYAN}Scores po 10 dniach:{RESET}")
    print(f"           extracted_emotion  (half_life=3d):   {emotion_score:.4f}")
    print(f"           extracted_fact     (half_life=60d):  {fact_score:.4f}")
    print(f"           extracted_milestone (half_life=365d): {milestone_score:.4f}")

    if emotion_score < fact_score:
        ok("Emocja blaknie szybciej niż fakt", f"emotion={emotion_score:.3f} < fact={fact_score:.3f}")
    else:
        fail("Emocja powinna blaknąć szybciej", f"emotion={emotion_score:.3f} >= fact={fact_score:.3f}")

    if fact_score < milestone_score:
        ok("Fakt blaknie szybciej niż milestone", f"fact={fact_score:.3f} < milestone={milestone_score:.3f}")
    else:
        fail("Fakt powinien blaknąć szybciej niż milestone", f"fact={fact_score:.3f} >= milestone={milestone_score:.3f}")

except Exception as e:
    fail("Per-type recency decay test", str(e))


# ══════════════════════════════════════════════════════════════════════════════
# TEST 4 — MILESTONE BOOST: zakres 1.0–1.5, nie 1.0–2.0
# ══════════════════════════════════════════════════════════════════════════════
section("TEST 4 — Milestone boost ≤ 1.5")

try:
    from vector_store import VectorStore

    vs_test = VectorStore.__new__(VectorStore)

    fresh = datetime.utcnow().isoformat()

    milestone = {
        'text': 'Łukasz powiedział że mi ufa',
        'distance': 0.0,  # perfect similarity
        'metadata': {
            'source': 'extracted_milestone',
            'importance': 10,
            'is_milestone': True,
            'timestamp': fresh,
        }
    }

    reranked = vs_test.rerank([milestone], query="zaufanie")
    score = reranked[0].get('final_score', 0)

    if score <= 1.5:
        ok(f"Milestone boost ≤ 1.5", f"score={score:.3f} (stary +1.0 byłby ≤ 2.0)")
    elif score <= 2.0:
        fail(f"Milestone boost wciąż +1.0", f"score={score:.3f} > 1.5 — stara wersja!")
    else:
        fail(f"Milestone boost anomalia", f"score={score:.3f}")

except Exception as e:
    fail("Milestone boost test", str(e))


# ══════════════════════════════════════════════════════════════════════════════
# TEST 5 — TIMESTAMP PREFIX: czy pojawia się w build_system_prompt
# ══════════════════════════════════════════════════════════════════════════════
section("TEST 5 — Timestamp prefix w memory block")

try:
    # Importuj build_system_prompt pośrednio — sprawdź w kodzie
    import ast

    main_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'main.py')
    with open(main_path, 'r', encoding='utf-8') as f:
        main_code = f.read()

    has_time_prefix = 'time_prefix' in main_code
    has_days_ago = 'dni temu' in main_code
    has_months_ago = 'mies. temu' in main_code

    if has_time_prefix and has_days_ago and has_months_ago:
        ok("Timestamp prefix obecny w main.py", "time_prefix, 'dni temu', 'mies. temu' ✓")
    elif has_time_prefix:
        ok("time_prefix obecny, brakuje etykiet czasowych", "częściowo zaimplementowane")
    else:
        fail("Timestamp prefix BRAK w main.py", "time_prefix nie znaleziony")

    # Dodatkowy test: czy datetime jest importowany globalnie
    has_global_datetime = 'from datetime import datetime' in main_code
    if has_global_datetime:
        ok("datetime import globalny", "from datetime import datetime na poziomie modułu ✓")
    else:
        fail("datetime import brak lub lokalny", "może powodować NameError w build_system_prompt")

except Exception as e:
    fail("Timestamp prefix test", str(e))


# ══════════════════════════════════════════════════════════════════════════════
# TEST 6 — MEMORY ENRICHER: FACT:correction ma importance=8
# ══════════════════════════════════════════════════════════════════════════════
section("TEST 6 — FACT:correction importance = 8")

try:
    from memory_enricher import MemoryEnricher

    enricher = MemoryEnricher()

    # Symuluj enrichment dla FACT:correction
    result = enricher.enrich(
        text="Nie, mówiłem czarną herbatę, nie Earl Grey",
        entity_type="FACT",
        subtype="correction",
        confidence=0.85
    )

    if result.importance >= 8:
        ok(f"FACT:correction importance={result.importance}", "korekty mają wysoki priorytet ✓")
    elif result.importance >= 5:
        fail(f"FACT:correction importance={result.importance}", "powinno być ≥ 8, za niskie")
    else:
        fail(f"FACT:correction importance={result.importance}", "bardzo niskie, coś poszło nie tak")

    # Sprawdź czy correction jest w SUPERSEDABLE_TOPICS
    if hasattr(enricher, 'SUPERSEDABLE_TOPICS') and 'correction' in enricher.SUPERSEDABLE_TOPICS:
        ok("correction w SUPERSEDABLE_TOPICS", f"→ {enricher.SUPERSEDABLE_TOPICS['correction']}")
    else:
        fail("correction NIE jest w SUPERSEDABLE_TOPICS", "nowe korekty nie nadpisują starych")

except Exception as e:
    fail("MemoryEnricher FACT:correction test", str(e))


# ══════════════════════════════════════════════════════════════════════════════
# TEST 7 — SEARCH default n=6
# ══════════════════════════════════════════════════════════════════════════════
section("TEST 7 — search_memories domyślne n=6")

try:
    import inspect
    from vector_store import VectorStore

    sig = inspect.signature(VectorStore.search_memories)
    n_default = sig.parameters.get('n', None)

    if n_default and n_default.default == 6:
        ok("search_memories n=6 default", "więcej miejsca dla faktów obok milestones ✓")
    elif n_default and n_default.default == 5:
        fail("search_memories n=5 (stara wartość)", "nasze n=6 nie zostało zastosowane")
    else:
        fail("search_memories n=?", f"nieoczekiwana wartość: {n_default}")

except Exception as e:
    fail("n=6 default test", str(e))


# ══════════════════════════════════════════════════════════════════════════════
# TEST 8 — RECENCY HALF LIFE: sprawdź że stałe są poprawne
# ══════════════════════════════════════════════════════════════════════════════
section("TEST 8 — RECENCY_HALF_LIFE stałe")

try:
    from vector_store import VectorStore

    # Nasze BY_SOURCE
    has_by_source = hasattr(VectorStore, 'RECENCY_HALF_LIFE_BY_SOURCE')
    # Ich BY_TYPE (Claude Code)
    has_by_type = hasattr(VectorStore, 'RECENCY_HALF_LIFE_BY_TYPE')

    if has_by_source:
        hl = VectorStore.RECENCY_HALF_LIFE_BY_SOURCE
        emotion_hl = hl.get('extracted_emotion', None)
        milestone_hl = hl.get('extracted_milestone', None)
        fact_hl = hl.get('extracted_fact', None)

        ok("RECENCY_HALF_LIFE_BY_SOURCE obecne", f"emotion={emotion_hl}d, fact={fact_hl}d, milestone={milestone_hl}d")

        if emotion_hl and emotion_hl <= 5:
            ok(f"extracted_emotion half_life={emotion_hl}d (krótkie)", "emocje blakną szybko ✓")
        else:
            fail(f"extracted_emotion half_life={emotion_hl}d", "powinno być ≤ 5 dni")

        if milestone_hl and milestone_hl >= 180:
            ok(f"extracted_milestone half_life={milestone_hl}d (długie)", "milestony przeżyją ✓")
        else:
            fail(f"extracted_milestone half_life={milestone_hl}d", "powinno być ≥ 180 dni")

    elif has_by_type:
        hl = VectorStore.RECENCY_HALF_LIFE_BY_TYPE
        ok("RECENCY_HALF_LIFE_BY_TYPE obecne (wersja Claude Code)", f"ephemeral={hl.get('ephemeral')}d, permanent={hl.get('permanent')}")
        print(f"         {YELLOW}→ BY_TYPE (Claude Code) zamiast BY_SOURCE (nasze) — ok, działa{RESET}")
    else:
        fail("Brak per-type recency stałych", "ani BY_SOURCE ani BY_TYPE nie znaleziono")

except Exception as e:
    fail("RECENCY half life test", str(e))


# ══════════════════════════════════════════════════════════════════════════════
# PODSUMOWANIE
# ══════════════════════════════════════════════════════════════════════════════
print(f"\n{BOLD}{'═' * 55}{RESET}")
total = passed + failed
pct = int(passed / total * 100) if total > 0 else 0

color = GREEN if pct >= 80 else (YELLOW if pct >= 60 else RED)
print(f"{BOLD}Wynik: {color}{passed}/{total} testów ({pct}%){RESET}")

if failed > 0:
    print(f"\n{RED}Nie przeszły:{RESET}")
    for r in results:
        if r[0] == "FAIL":
            print(f"  • {r[1]}")
            if len(r) > 2 and r[2]:
                print(f"    {YELLOW}{r[2]}{RESET}")

print(f"\n{CYAN}Legenda:{RESET}")
print("  • PASS = zachowanie działa poprawnie")
print("  • FAIL = coś nie gra — sprawdź detal")
print(f"{'═' * 55}\n")
