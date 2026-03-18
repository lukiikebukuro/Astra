"""
TEST 4: End-to-End RAG Test
Pełny flow: wiadomości → semantic pipeline → zapis do ChromaDB → retrieval → sprawdzenie.

Symuluje prawdziwą rozmowę i testuje czy:
1. Pipeline poprawnie wyciąga encje z konwersacji
2. Encje lądują w ChromaDB z poprawnymi metadanymi
3. Retrieval zwraca właściwe wyniki na zapytania

NIE dotyka produkcyjnej bazy.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from datetime import datetime
from rag_tests.test_config import (
    TEST_COLLECTION_NAME, TEST_USER_ID, TEST_SALT, TEST_PERSONA,
    E2E_CONVERSATIONS,
)
from vector_store import VectorStore
from semantic_pipeline import SemanticPipeline


def run_e2e_test() -> dict:
    """Testuje pełny flow ingestion → storage → retrieval."""
    print("\n" + "=" * 60)
    print("TEST 4: END-TO-END RAG")
    print("=" * 60)

    vs = VectorStore(collection_name=TEST_COLLECTION_NAME)
    pipeline = SemanticPipeline(vector_store=vs, database=None)

    # Wyczyść kolekcję
    try:
        all_data = vs.collection.get()
        if all_data['ids']:
            vs.collection.delete(ids=all_data['ids'])
    except Exception:
        pass

    results = []
    passed = 0
    failed = 0
    total = len(E2E_CONVERSATIONS)

    for conv in E2E_CONVERSATIONS:
        conv_id = conv["id"]
        messages = conv["messages"]
        test_query = conv["test_query"]
        expected_kw = conv["expected_keywords"]
        desc = conv["description"]

        print(f"\n--- {conv_id}: {desc} ---")

        # FAZA 1: Ingestion — przetwórz wiadomości przez pipeline
        total_entities = 0
        for msg in messages:
            print(f"    Ingesting: {msg[:60]}...")
            processed = pipeline.process_message(msg, companion_id=TEST_PERSONA)

            for p in processed:
                # Zapisz wyciągniętą encję do ChromaDB
                vs.add_memory(
                    text=p.text,
                    user_id=TEST_USER_ID,
                    salt=TEST_SALT,
                    persona_id=TEST_PERSONA,
                    source="enriched",
                    importance=p.importance,
                    is_milestone=(p.importance >= 9),
                    timestamp=datetime.utcnow().isoformat(),
                )
                total_entities += 1
                print(f"    → Stored: {p.entity_type}:{p.subtype} (imp={p.importance}) | {p.text[:50]}")

            # Również zapisz raw message jako session memory
            vs.add_memory(
                text=msg,
                user_id=TEST_USER_ID,
                salt=TEST_SALT,
                persona_id=TEST_PERSONA,
                source="enriched",
                importance=5,
                timestamp=datetime.utcnow().isoformat(),
            )

        print(f"    Total entities extracted: {total_entities}")
        print(f"    Total vectors in collection: {vs.collection.count()}")

        # FAZA 2: Retrieval — zapytaj i sprawdź
        print(f"    Query: {test_query}")

        try:
            search_results = vs.search_memories(
                query=test_query,
                persona_id=TEST_PERSONA,
                n=5, pool_size=20,
                user_id=TEST_USER_ID, salt=TEST_SALT,
            )
        except Exception as e:
            print(f"    RETRIEVAL ERROR: {e}")
            results.append({"id": conv_id, "status": "ERROR", "error": str(e)})
            failed += 1
            continue

        # FAZA 3: Sprawdź czy expected keywords są w wynikach
        all_result_text = " ".join(r.get("text", "").lower() for r in search_results[:3])
        issues = []
        keyword_hits = 0

        for kw in expected_kw:
            if kw.lower() in all_result_text:
                keyword_hits += 1
            else:
                issues.append(f"Keyword '{kw}' NOT found in top-3 results")

        keyword_rate = keyword_hits / len(expected_kw) if expected_kw else 1.0

        # Sprawdź czy w ogóle coś wróciło
        if not search_results:
            issues.append("ZERO results returned!")

        # Sprawdź quality score
        top_score = search_results[0].get("final_score", 0) if search_results else 0
        if top_score < 0.4:
            issues.append(f"Top score very low: {top_score:.3f}")

        # PASS: brak issues LUB keyword_rate >= 0.5 i top_score ok
        # (synthesized entity text != raw text, więc 100% keyword match nierealne)
        issues_no_kw = [i for i in issues if "Keyword" not in i]
        status = "PASS" if (not issues_no_kw and keyword_rate >= 0.5) else "FAIL"
        if status == "PASS":
            passed += 1
            print(f"    PASS ✓ | Keywords: {keyword_hits}/{len(expected_kw)} | Top score: {top_score:.3f}")
        else:
            failed += 1
            print(f"    FAIL ✗ | Keywords: {keyword_hits}/{len(expected_kw)} | Top score: {top_score:.3f}")
            for issue in issues:
                print(f"           | {issue}")

        for j, r in enumerate(search_results[:3]):
            print(f"    [{j+1}] score={r.get('final_score', 0):.3f} | {r.get('text', '')[:70]}")

        results.append({
            "id": conv_id,
            "status": status,
            "entities_extracted": total_entities,
            "keyword_rate": round(keyword_rate, 2),
            "top_score": round(top_score, 3),
            "issues": issues,
            "description": desc,
        })

    # Score
    score = (passed / total * 10) if total > 0 else 0

    print(f"\n{'=' * 60}")
    print(f"E2E SCORE: {score:.1f}/10 ({passed}/{total} passed)")
    print(f"{'=' * 60}")

    # Cleanup
    try:
        all_data = vs.collection.get()
        if all_data['ids']:
            vs.collection.delete(ids=all_data['ids'])
    except Exception:
        pass

    return {
        "test_name": "End-to-End RAG",
        "score": round(score, 1),
        "passed": passed,
        "failed": failed,
        "total": total,
        "details": results,
    }


if __name__ == "__main__":
    result = run_e2e_test()
    print(f"\nFinal score: {result['score']}/10")
