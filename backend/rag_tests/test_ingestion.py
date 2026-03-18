"""
TEST 1: Ingestion Quality
Sprawdza czy SemanticExtractor + MemoryEnricher poprawnie wyciągają encje z wiadomości.

Co testuje:
- Czy wyciąga właściwe typy encji (MILESTONE, EMOTION, FACT, PERSON, DATE, SHARED_THING)
- Czy subtypy się zgadzają
- Czy confidence jest powyżej minimum
- Czy krótkie wiadomości są odrzucane
- Czy [MEMORY] tagi są stripowane
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from rag_tests.test_config import INGESTION_CASES
from semantic_pipeline import SemanticPipeline


def run_ingestion_test() -> dict:
    """Uruchamia testy ingestion i zwraca wyniki."""
    print("\n" + "=" * 60)
    print("TEST 1: INGESTION QUALITY")
    print("=" * 60)

    pipeline = SemanticPipeline(vector_store=None, database=None)

    results = []
    passed = 0
    failed = 0
    total = len(INGESTION_CASES)

    for case in INGESTION_CASES:
        case_id = case["id"]
        input_text = case["input"]
        expected_types = case["expected_types"]
        expected_subtypes = case["expected_subtypes"]
        min_conf = case["min_confidence"]
        desc = case["description"]

        print(f"\n--- {case_id}: {desc} ---")
        print(f"    Input: {input_text[:80]}...")

        try:
            processed = pipeline.process_message(input_text, companion_id="astra", min_confidence=0.3)
        except Exception as e:
            print(f"    ERROR: {e}")
            results.append({"id": case_id, "status": "ERROR", "error": str(e)})
            failed += 1
            continue

        found_types = [p.entity_type for p in processed]
        found_subtypes = [p.subtype for p in processed]
        found_confs = [p.confidence for p in processed]

        # Sprawdź oczekiwania
        issues = []

        if not expected_types:
            # Oczekujemy PUSTEGO wyniku
            if processed:
                issues.append(f"Oczekiwano pustego wyniku, dostano: {found_types}")
        else:
            # Sprawdź czy przynajmniej jeden oczekiwany typ został znaleziony
            type_match = any(t in found_types for t in expected_types)
            if not type_match:
                issues.append(f"Brak oczekiwanego typu: {expected_types}, znaleziono: {found_types}")

            # Sprawdź subtypes (przynajmniej jeden match)
            if expected_subtypes:
                subtype_match = any(s in found_subtypes for s in expected_subtypes)
                if not subtype_match:
                    issues.append(f"Brak oczekiwanego subtypu: {expected_subtypes}, znaleziono: {found_subtypes}")

            # Sprawdź confidence
            if found_confs and min_conf > 0:
                max_conf = max(found_confs)
                if max_conf < min_conf:
                    issues.append(f"Confidence za niski: {max_conf:.2f} < {min_conf:.2f}")

        status = "PASS" if not issues else "FAIL"
        if status == "PASS":
            passed += 1
            print(f"    PASS ✓ | Types: {found_types} | Subtypes: {found_subtypes}")
        else:
            failed += 1
            for issue in issues:
                print(f"    FAIL ✗ | {issue}")

        results.append({
            "id": case_id,
            "status": status,
            "found_types": found_types,
            "found_subtypes": found_subtypes,
            "found_confidences": [round(c, 3) for c in found_confs],
            "issues": issues,
            "description": desc,
        })

    score = (passed / total * 10) if total > 0 else 0
    print(f"\n{'=' * 60}")
    print(f"INGESTION SCORE: {score:.1f}/10 ({passed}/{total} passed)")
    print(f"{'=' * 60}")

    return {
        "test_name": "Ingestion Quality",
        "score": round(score, 1),
        "passed": passed,
        "failed": failed,
        "total": total,
        "details": results,
    }


if __name__ == "__main__":
    result = run_ingestion_test()
    print(f"\nFinal score: {result['score']}/10")
