"""
TEST 2: Retrieval Precision
Wstawia znane dokumenty do TESTOWEJ kolekcji, potem pyta i sprawdza:
- Czy właściwe dokumenty wracają w top-3 (precision@3)
- Czy must_include dokumenty SĄ w wynikach
- Czy must_exclude dokumenty NIE SĄ w wynikach
- Czy NO_MATCH queries mają niski top score

NIE dotyka produkcyjnej bazy.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from datetime import datetime, timedelta
from rag_tests.test_config import (
    TEST_COLLECTION_NAME, TEST_USER_ID, TEST_SALT, TEST_PERSONA,
    RETRIEVAL_DOCUMENTS, RETRIEVAL_QUERIES,
)
from vector_store import VectorStore


def _setup_test_collection() -> VectorStore:
    """Tworzy izolowaną kolekcję testową z known documents."""
    vs = VectorStore(collection_name=TEST_COLLECTION_NAME)

    # Wyczyść kolekcję jeśli istnieje
    try:
        existing = vs.collection.count()
        if existing > 0:
            # Pobierz wszystkie ID i usuń
            all_data = vs.collection.get()
            if all_data['ids']:
                vs.collection.delete(ids=all_data['ids'])
            print(f"[TEST] Wyczyszczono {existing} starych wektorów z testowej kolekcji")
    except Exception as e:
        print(f"[TEST] Cleanup warning: {e}")

    # Wstaw dokumenty testowe
    base_time = datetime.utcnow()
    for i, doc in enumerate(RETRIEVAL_DOCUMENTS):
        # Starsze dokumenty mają timestamp w przeszłości (spread 1-30 dni)
        ts = (base_time - timedelta(days=30 - i)).isoformat()

        vs.add_memory(
            text=doc["text"],
            user_id=TEST_USER_ID,
            salt=TEST_SALT,
            persona_id=TEST_PERSONA,
            source=doc.get("source", "enriched"),
            importance=doc.get("importance", 5),
            is_milestone=doc.get("is_milestone", False),
            timestamp=ts,
        )
    print(f"[TEST] Wstawiono {len(RETRIEVAL_DOCUMENTS)} dokumentów testowych")
    print(f"[TEST] Total vectors: {vs.collection.count()}")
    return vs


def _find_doc_id_for_result(result_text: str, documents: list) -> str | None:
    """Mapuje tekst wyniku na ID dokumentu z golden datasetu."""
    for doc in documents:
        # Partial match — wynik może mieć obcięty tekst
        if doc["text"][:50] in result_text or result_text[:50] in doc["text"]:
            return doc["id"]
    return None


def run_retrieval_test() -> dict:
    """Uruchamia testy retrieval precision."""
    print("\n" + "=" * 60)
    print("TEST 2: RETRIEVAL PRECISION")
    print("=" * 60)

    vs = _setup_test_collection()

    results = []
    passed = 0
    failed = 0
    total = len(RETRIEVAL_QUERIES)

    total_precision = 0.0
    total_must_include_hit = 0
    total_must_include_count = 0
    total_must_exclude_miss = 0
    total_must_exclude_count = 0

    for case in RETRIEVAL_QUERIES:
        case_id = case["id"]
        query = case["query"]
        expected_ids = case["expected_doc_ids"]
        must_include = case.get("must_include", [])
        must_exclude = case.get("must_exclude", [])
        max_top_score = case.get("max_top_score", None)
        desc = case["description"]

        print(f"\n--- {case_id}: {desc} ---")
        print(f"    Query: {query}")

        try:
            search_results = vs.search_memories(
                query=query,
                persona_id=TEST_PERSONA,
                n=5,
                pool_size=20,
                user_id=TEST_USER_ID,
                salt=TEST_SALT,
            )
        except Exception as e:
            print(f"    ERROR: {e}")
            results.append({"id": case_id, "status": "ERROR", "error": str(e)})
            failed += 1
            continue

        # Mapuj wyniki na doc IDs
        result_doc_ids = []
        for r in search_results:
            doc_id = _find_doc_id_for_result(r.get("text", ""), RETRIEVAL_DOCUMENTS)
            result_doc_ids.append(doc_id)

        top3_ids = result_doc_ids[:3]
        top_score = search_results[0].get("final_score", 0) if search_results else 0

        issues = []

        # Precision@3: ile z top-3 jest w expected
        if expected_ids:
            hits = sum(1 for rid in top3_ids if rid in expected_ids)
            precision = hits / min(3, len(expected_ids))
            total_precision += precision
        else:
            precision = 1.0 if not search_results else 0.0
            total_precision += precision

        # Must include check
        for mid in must_include:
            total_must_include_count += 1
            if mid in top3_ids:
                total_must_include_hit += 1
            else:
                issues.append(f"MUST_INCLUDE {mid} NOT in top-3: {top3_ids}")

        # Must exclude check
        for eid in must_exclude:
            total_must_exclude_count += 1
            if eid in top3_ids:
                issues.append(f"MUST_EXCLUDE {eid} FOUND in top-3: {top3_ids}")
            else:
                total_must_exclude_miss += 1

        # Max top score check (for NO_MATCH queries)
        if max_top_score is not None and top_score > max_top_score:
            issues.append(f"Top score {top_score:.3f} > max allowed {max_top_score:.3f}")

        status = "PASS" if not issues else "FAIL"
        if status == "PASS":
            passed += 1
            print(f"    PASS ✓ | Top-3: {top3_ids} | Score: {top_score:.3f} | P@3: {precision:.2f}")
        else:
            failed += 1
            print(f"    FAIL ✗ | Top-3: {top3_ids} | Score: {top_score:.3f}")
            for issue in issues:
                print(f"           | {issue}")

        # Pokaż detale wyników
        for j, r in enumerate(search_results[:5]):
            rid = result_doc_ids[j] if j < len(result_doc_ids) else "?"
            score_detail = r.get("_score_detail", {})
            print(f"    [{j+1}] {rid or '?'} | score={r.get('final_score', 0):.3f} "
                  f"sim={score_detail.get('similarity', 0):.3f} "
                  f"imp={score_detail.get('importance', 0):.3f} "
                  f"rec={score_detail.get('recency', 0):.3f} "
                  f"kw={score_detail.get('keyword', 0):.3f} "
                  f"| {r.get('text', '')[:60]}")

        results.append({
            "id": case_id,
            "status": status,
            "precision_at_3": round(precision, 2),
            "top_score": round(top_score, 3),
            "top3_doc_ids": top3_ids,
            "issues": issues,
            "description": desc,
        })

    # Oblicz metryki
    avg_precision = total_precision / total if total > 0 else 0
    must_include_rate = (total_must_include_hit / total_must_include_count
                         if total_must_include_count > 0 else 1.0)
    must_exclude_rate = (total_must_exclude_miss / total_must_exclude_count
                         if total_must_exclude_count > 0 else 1.0)

    # Score = ważona kombinacja
    score = (avg_precision * 5 + must_include_rate * 3 + must_exclude_rate * 2)

    print(f"\n{'=' * 60}")
    print(f"RETRIEVAL SCORE: {score:.1f}/10 ({passed}/{total} passed)")
    print(f"  Avg Precision@3:    {avg_precision:.2f}")
    print(f"  Must-Include Rate:  {must_include_rate:.2f} ({total_must_include_hit}/{total_must_include_count})")
    print(f"  Must-Exclude Rate:  {must_exclude_rate:.2f} ({total_must_exclude_miss}/{total_must_exclude_count})")
    print(f"{'=' * 60}")

    # Cleanup testowej kolekcji
    try:
        all_data = vs.collection.get()
        if all_data['ids']:
            vs.collection.delete(ids=all_data['ids'])
        print(f"[TEST] Cleanup: usunięto testowe wektory")
    except Exception:
        pass

    return {
        "test_name": "Retrieval Precision",
        "score": round(score, 1),
        "passed": passed,
        "failed": failed,
        "total": total,
        "avg_precision_at_3": round(avg_precision, 2),
        "must_include_rate": round(must_include_rate, 2),
        "must_exclude_rate": round(must_exclude_rate, 2),
        "details": results,
    }


if __name__ == "__main__":
    result = run_retrieval_test()
    print(f"\nFinal score: {result['score']}/10")
