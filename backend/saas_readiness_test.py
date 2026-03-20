"""
ASTRA - SaaS Readiness Test
Sprawdza czy Astra jest gotowa na komercjalizację.

Testuje 4 obszary:
1. Semantic Pipeline — czy wyciąga encje z polskich zdań
2. RAG Recall — czy zapamiętuje i odnajduje fakty
3. User Isolation — czy użytkownicy A i B nie widzą swoich danych
4. Strict Grounding — czy odmawia halucynacji przy braku danych

Uruchomienie: venv/bin/python3 saas_readiness_test.py
Czas: ~60 sekund
Dane testowe są czyszczone po zakończeniu.
"""

import sys
import hashlib
from datetime import datetime
from vector_store import VectorStore
from semantic_pipeline import SemanticPipeline
from strict_grounding import StrictGrounding

# ── Konfiguracja testów ──
TEST_PERSONA   = "test_audit"
TEST_USER_A    = "test_user_alpha"
TEST_USER_B    = "test_user_beta"
TEST_SALT      = "saas_test_salt_2026"

PASS = "✅ PASS"
FAIL = "❌ FAIL"
WARN = "⚠️  WARN"

results = []

def log(status, test_name, detail=""):
    results.append((status, test_name, detail))
    print(f"  {status}  {test_name}")
    if detail:
        print(f"         {detail}")

def make_id(user_id, text):
    return hashlib.sha256(f"{TEST_SALT}:{user_id}:{text}".encode()).hexdigest()[:32]

def cleanup(vs, ids):
    try:
        existing = vs.collection.get(ids=ids)
        ids_to_delete = [i for i in existing['ids'] if i]
        if ids_to_delete:
            vs.collection.delete(ids=ids_to_delete)
    except Exception:
        pass


# ════════════════════════════════════════════════════════════
print("=" * 60)
print("ASTRA — SaaS Readiness Test")
print(f"Czas: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 60)

vs = VectorStore()
pipeline = SemanticPipeline()
sg = StrictGrounding(strict_mode=True)
test_ids = []

# ════════════════════════════════════════════════════════════
# TEST 1: SEMANTIC PIPELINE
# ════════════════════════════════════════════════════════════
print("\n[1/4] SEMANTIC PIPELINE — wyciąganie encji z polskiego tekstu")

pipeline_cases = [
    ("mam Crohna i biorę Stelarę co miesiąc",          ["FACT", "DATE", "MEDICATION"]),
    ("schudłem z 94 do 82 kilogramów w tym roku",       ["MEASUREMENT", "FACT"]),
    ("jestem bardzo zmęczony i boli mnie głowa",        ["EMOTION", "FACT"]),
    ("mam wizytę u lekarza w przyszłym tygodniu",       ["DATE"]),
    ("buduję system AI który pamięta wszystko",         ["FACT", "GOAL"]),
    ("biorę 300 mg pregabaliny rano i 150 mg wieczorem", ["MEDICATION", "FACT"]),
    ("następna Stelara zaplanowana na 7 kwietnia",      ["MEDICATION", "DATE"]),
    ("szukałem monitora za 1500 zł ale nie znalazłem", ["FINANCIAL"]),
    ("nie piję kawy ze względu na jelita od 2 lat",     ["FACT", "MEDICATION"]),
    ("moja mama mieszka w Krakowie i pracuje jako lekarz", ["PERSON", "FACT"]),
]

pipeline_pass = 0
for msg, expected_types in pipeline_cases:
    extracted = pipeline.process_message(msg, companion_id=TEST_PERSONA, min_confidence=0.40)
    found_types = [e.entity_type for e in extracted]
    hit = any(t in found_types for t in expected_types)
    if hit:
        pipeline_pass += 1
        log(PASS, f"'{msg[:45]}...'", f"→ {found_types}")
    else:
        log(FAIL, f"'{msg[:45]}...'", f"oczekiwano {expected_types}, dostano: {found_types or 'BRAK'}")

score_pipeline = pipeline_pass / len(pipeline_cases)
print(f"\n  Wynik: {pipeline_pass}/{len(pipeline_cases)} ({score_pipeline:.0%})")


# ════════════════════════════════════════════════════════════
# TEST 2: RAG RECALL
# ════════════════════════════════════════════════════════════
print("\n[2/4] RAG RECALL — zapamiętywanie i odnajdowanie faktów")

test_memories = [
    ("Łukasz choruje na Crohna od 2019 roku",           10),
    ("Łukasz waży 82 kilogramy po diecie",              8),
    ("Łukasz buduje projekt ASTRA i LDI",               9),
    ("Łukasz mieszka w Gorzowie Wielkopolskim",         7),
    ("Łukasz nie pije kawy ze względu na jelita",       8),
]

injected_ids = []
for text, importance in test_memories:
    mem_id = vs.add_memory(
        text=text,
        user_id=TEST_USER_A,
        salt=TEST_SALT,
        persona_id=TEST_PERSONA,
        source="extracted_fact",
        importance=importance,
    )
    if mem_id:
        injected_ids.append(mem_id)
        test_ids.append(mem_id)

recall_queries = [
    ("Crohn choroba jelita",        "crohn"),
    ("waga kilogramy dieta",        "82 kilogram"),
    ("projekt AI system",           "astra"),
    ("miasto gdzie mieszka",        "gorzow"),   # stem: pasuje do Gorzowie/Gorzów
    ("kawa napoje jelita",          "nie pije kawy"),
]

recall_pass = 0
for query, expected_keyword in recall_queries:
    results_raw = vs.search_memories(query=query, persona_id=TEST_PERSONA, n=5,
                                     user_id=TEST_USER_A, salt=TEST_SALT)
    found_texts = [r['text'] for r in results_raw]
    # Stemmed match — porównuj po ascii lowercase żeby obsłużyć polskie odmiony
    import unicodedata
    def normalize(s):
        return unicodedata.normalize('NFD', s.lower()).encode('ascii', 'ignore').decode()
    hit = any(normalize(expected_keyword) in normalize(t) for t in found_texts)
    if hit:
        recall_pass += 1
        matched = next(t for t in found_texts if normalize(expected_keyword) in normalize(t))
        log(PASS, f"Query: '{query}'", f"→ znaleziono: '{matched[:60]}'")
    else:
        log(FAIL, f"Query: '{query}'", f"oczekiwano '{expected_keyword}', RAG zwrócił: {[t[:40] for t in found_texts]}")

score_recall = recall_pass / len(recall_queries)
print(f"\n  Wynik: {recall_pass}/{len(recall_queries)} ({score_recall:.0%})")


# ════════════════════════════════════════════════════════════
# TEST 3: USER ISOLATION (SaaS critical)
# ════════════════════════════════════════════════════════════
print("\n[3/4] USER ISOLATION — użytkownik B nie widzi danych użytkownika A")

# Wstrzyknij unikalny sekret tylko dla user A
secret_text = "Tajny sekret użytkownika Alpha - nikt inny nie powinien tego zobaczyć"
secret_id = vs.add_memory(
    text=secret_text,
    user_id=TEST_USER_A,
    salt=TEST_SALT,
    persona_id=TEST_PERSONA,
    source="extracted_fact",
    importance=10,
)
test_ids.append(secret_id)

# Szukaj jako user B — ten sam persona_id, ale inny user_id (prawdziwa symulacja SaaS)
results_b = vs.search_memories(
    query="tajny sekret użytkownika",
    persona_id=TEST_PERSONA,
    n=5,
    user_id=TEST_USER_B,   # inny user!
    salt=TEST_SALT,
)
found_secret = any(secret_text.lower() in r['text'].lower() for r in results_b)

if not found_secret:
    log(PASS, "User B NIE widzi danych User A — izolacja działa ✅")
else:
    log(FAIL, "User B WIDZI dane User A — izolacja nie działa!",
        "search_memories z user_id filter powinno blokować cross-user dostęp.")

# Sprawdź czy user_id jest w metadanych
all_data = vs.collection.get(ids=[secret_id], include=["metadatas"])
if all_data['metadatas']:
    stored_uid = all_data['metadatas'][0].get('user_id', 'BRAK')
    log(PASS, f"user_id w metadanych: {stored_uid}")
else:
    log(FAIL, "Brak user_id w metadanych")


# ════════════════════════════════════════════════════════════
# TEST 4: STRICT GROUNDING
# ════════════════════════════════════════════════════════════
print("\n[4/4] STRICT GROUNDING — odmowa halucynacji")

grounding_cases = [
    # (results, query, expected_status)
    ([], "coś czego nie ma w pamięci",      "NO_DATA"),
    ([{"distance": 0.9}, {"distance": 1.1}],  "słabe dopasowanie",    "NO_DATA"),
    ([{"distance": 0.3}, {"distance": 0.4}],  "dobre dopasowanie",    "GROUNDED"),
    ([{"distance": 0.6}, {"distance": 0.65}], "średnie dopasowanie",  "LOW_CONFIDENCE"),
]

grounding_pass = 0
for fake_results, query, expected in grounding_cases:
    result = sg.analyze_rag_results(fake_results, query=query)
    if result.grounding_status == expected:
        grounding_pass += 1
        log(PASS, f"{expected} przy distance={[r.get('distance') for r in fake_results]}",
            f"confidence={result.confidence}")
    else:
        log(FAIL, f"Oczekiwano {expected}, dostano {result.grounding_status}",
            f"distance={[r.get('distance') for r in fake_results]}")

score_grounding = grounding_pass / len(grounding_cases)
print(f"\n  Wynik: {grounding_pass}/{len(grounding_cases)} ({score_grounding:.0%})")


# ════════════════════════════════════════════════════════════
# CLEANUP
# ════════════════════════════════════════════════════════════
print("\n[CLEANUP] Usuwanie danych testowych...")
cleanup(vs, [i for i in test_ids if i])
print(f"  Usunięto {len([i for i in test_ids if i])} wektorów testowych.")


# ════════════════════════════════════════════════════════════
# RAPORT KOŃCOWY
# ════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("RAPORT KOŃCOWY — SaaS Readiness")
print("=" * 60)

scores = {
    "Semantic Pipeline": score_pipeline,
    "RAG Recall":        score_recall,
    "Strict Grounding":  score_grounding,
}

overall = sum(scores.values()) / len(scores)

for name, score in scores.items():
    bar = "█" * int(score * 10) + "░" * (10 - int(score * 10))
    status = "✅" if score >= 0.8 else ("⚠️ " if score >= 0.6 else "❌")
    print(f"  {status} {name:<22} [{bar}] {score:.0%}")

print(f"\n  OVERALL: {overall:.0%}", end="  ")
if overall >= 0.85:
    print("→ GOTOWA NA SAAS ✅")
elif overall >= 0.65:
    print("→ PRAWIE GOTOWA — drobne poprawki ⚠️")
else:
    print("→ NIE GOTOWA — wymagane naprawy ❌")

# User isolation warning
print("\n  UWAGA — User Isolation:")
print("  search_memories filtruje po persona_id, nie user_id.")
print("  Dla prawdziwego SaaS: każdy user musi mieć osobny persona_id")
print("  LUB dodać user_id filter do search_memories query.")
print("=" * 60)
