#!/usr/bin/env python3
"""
ASTRA RAG TEST SUITE — Master Runner
=====================================
Uruchamia wszystkie testy sekwencyjnie i generuje:
1. Raport na konsolę
2. Plik Markdown z pełnym raportem i rekomendacjami

Użycie:
    cd backend
    python -m rag_tests.run_all                   # pełny suite + prod audit
    python -m rag_tests.run_all --skip-prod        # bez audytu produkcyjnej bazy
    python -m rag_tests.run_all --only ingestion   # tylko jeden test
"""

import sys
import os
import argparse
import traceback
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


# ──────────────────────────────────────────────────────────────
# IMPORT TESTÓW
# ──────────────────────────────────────────────────────────────

from rag_tests.test_ingestion import run_ingestion_test
from rag_tests.test_retrieval import run_retrieval_test
from rag_tests.test_reranker_mmr import run_reranker_test, run_mmr_test
from rag_tests.test_e2e import run_e2e_test
from rag_tests.test_prod_audit import run_prod_audit, run_prod_retrieval_check


TEST_REGISTRY = {
    "ingestion":  ("1. Ingestion Quality",        run_ingestion_test),
    "retrieval":  ("2. Retrieval Precision",       run_retrieval_test),
    "reranker":   ("3A. Reranker Weights",         run_reranker_test),
    "mmr":        ("3B. MMR Diversity",            run_mmr_test),
    "e2e":        ("4. End-to-End RAG",            run_e2e_test),
}

PROD_TESTS = {
    "prod_audit":     ("5. Production DB Audit",          run_prod_audit),
    "prod_retrieval": ("6. Prod Retrieval Sanity Check",  run_prod_retrieval_check),
}


# ──────────────────────────────────────────────────────────────
# RUNNER
# ──────────────────────────────────────────────────────────────

def run_all(skip_prod: bool = False, only: str | None = None) -> dict:
    """Uruchamia testy i zbiera wyniki."""
    timestamp = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    all_results = {}
    errors = {}

    # Wybierz testy do uruchomienia
    if only:
        tests_to_run = {}
        if only in TEST_REGISTRY:
            tests_to_run[only] = TEST_REGISTRY[only]
        elif only in PROD_TESTS:
            tests_to_run[only] = PROD_TESTS[only]
        else:
            print(f"ERROR: Unknown test '{only}'. Available: {list(TEST_REGISTRY) + list(PROD_TESTS)}")
            sys.exit(1)
    else:
        tests_to_run = dict(TEST_REGISTRY)
        if not skip_prod:
            tests_to_run.update(PROD_TESTS)

    # Uruchom testy sekwencyjnie
    for key, (label, func) in tests_to_run.items():
        print(f"\n{'#' * 70}")
        print(f"# RUNNING: {label}")
        print(f"{'#' * 70}")
        try:
            result = func()
            all_results[key] = result
        except Exception as e:
            print(f"\n!!! ERROR in {label}: {e}")
            traceback.print_exc()
            errors[key] = str(e)
            all_results[key] = {"test_name": label, "score": 0, "error": str(e)}

    return {
        "timestamp": timestamp,
        "results": all_results,
        "errors": errors,
    }


# ──────────────────────────────────────────────────────────────
# SCORE CALCULATION
# ──────────────────────────────────────────────────────────────

def calculate_overall_score(results: dict) -> tuple[float, str]:
    """
    Oblicza łączny RAG score z wagami:
    - Ingestion:  20%
    - Retrieval:  30%
    - Reranker:   15%
    - MMR:        10%
    - E2E:        25%
    (Prod audit nie wchodzi do łącznego score — to osobny health check)
    """
    weights = {
        "ingestion": 0.20,
        "retrieval": 0.30,
        "reranker":  0.15,
        "mmr":       0.10,
        "e2e":       0.25,
    }

    weighted_sum = 0.0
    total_weight = 0.0
    breakdown = []

    for key, weight in weights.items():
        if key not in results:
            continue

        r = results[key]

        # Normalizacja score do 0-10
        if key == "reranker":
            score = r.get("best_score", 0)
        elif key == "mmr":
            score = r.get("best_diversity", 0) * 10  # diversity 0-1 → 0-10
        else:
            score = r.get("score", 0)

        weighted_sum += score * weight
        total_weight += weight
        breakdown.append(f"  {key}: {score:.1f}/10 × {weight:.0%} = {score * weight:.2f}")

    overall = weighted_sum / total_weight if total_weight > 0 else 0

    # Klasyfikacja
    if overall >= 8.0:
        grade = "EXCELLENT"
    elif overall >= 7.0:
        grade = "GOOD — cel RAG 7/10 osiągnięty!"
    elif overall >= 6.0:
        grade = "ACCEPTABLE — blisko celu, wymaga tuning"
    elif overall >= 4.0:
        grade = "NEEDS WORK — znaczące gap do 7/10"
    else:
        grade = "CRITICAL — fundamentalne problemy"

    breakdown_str = "\n".join(breakdown)
    return overall, grade, breakdown_str


# ──────────────────────────────────────────────────────────────
# RECOMMENDATIONS ENGINE
# ──────────────────────────────────────────────────────────────

def generate_recommendations(results: dict) -> list[str]:
    """Generuje konkretne rekomendacje na podstawie wyników."""
    recs = []

    # Reranker recommendations
    if "reranker" in results:
        r = results["reranker"]
        if r.get("best_weights") != "current_production" and not r.get("error"):
            best = r.get("recommendation", {})
            if isinstance(best, dict):
                recs.append(
                    f"🔧 RERANKER: Zmień wagi na {r['best_weights']}: "
                    f"sim={best.get('similarity')}, imp={best.get('importance')}, "
                    f"rec={best.get('recency')} "
                    f"(+{r.get('best_score', 0) - (r.get('current_score') or 0):.1f} score)"
                )
        else:
            recs.append("✓ RERANKER: Aktualne wagi (sim=0.65/imp=0.20/rec=0.15) są optymalne")

    # MMR recommendations
    if "mmr" in results:
        r = results["mmr"]
        if not r.get("error"):
            best_p = r.get("best_penalty", 0.4)
            if best_p != 0.4:
                recs.append(
                    f"🔧 MMR: Zmień diversity_penalty z 0.4 na {best_p} "
                    f"(diversity: {r.get('current_diversity', '?')} → {r.get('best_diversity', '?')})"
                )
            else:
                recs.append("✓ MMR: Aktualne penalty=0.4 jest optymalne")

    # Ingestion recommendations
    if "ingestion" in results:
        r = results["ingestion"]
        if not r.get("error"):
            score = r.get("score", 0)
            if score < 7.0:
                failed_cases = [d for d in r.get("details", []) if d.get("status") == "FAIL"]
                if failed_cases:
                    failed_types = set()
                    for f in failed_cases:
                        for issue in f.get("issues", []):
                            if "typu" in issue or "type" in issue.lower():
                                failed_types.add(f.get("id", "?"))
                    recs.append(
                        f"🔧 INGESTION: {len(failed_cases)} cases failed — "
                        f"sprawdź SemanticExtractor zero-shot labels i thresholds"
                    )

    # Retrieval recommendations
    if "retrieval" in results:
        r = results["retrieval"]
        if not r.get("error"):
            score = r.get("score", 0)
            if score < 7.0:
                recs.append(
                    "🔧 RETRIEVAL: Precision@3 poniżej celu — "
                    "rozważ: keyword_boost > 0.10, pool_size > 20, lub dodanie cross-encoder reranker"
                )

    # E2E recommendations
    if "e2e" in results:
        r = results["e2e"]
        if not r.get("error"):
            score = r.get("score", 0)
            if score < 7.0:
                recs.append(
                    "🔧 E2E: Full-flow ma gap — "
                    "problem prawdopodobnie w ingestion (entity extraction) lub retrieval (ranking)"
                )

    # Prod audit recommendations
    if "prod_audit" in results:
        r = results["prod_audit"]
        if not r.get("error"):
            for issue in r.get("issues", []):
                recs.append(f"🔧 PROD DB: {issue}")
            if r.get("exact_duplicates", 0) > 10:
                recs.append(
                    "🔧 PROD DB: Uruchom cleanup_toxic.py lub deduplikację — "
                    f"{r['exact_duplicates']} duplikatów"
                )

    if not recs:
        recs.append("✓ Brak krytycznych rekomendacji — system działa dobrze!")

    return recs


# ──────────────────────────────────────────────────────────────
# MARKDOWN REPORT
# ──────────────────────────────────────────────────────────────

def generate_report(run_data: dict) -> str:
    """Generuje pełny raport Markdown."""
    results = run_data["results"]
    errors = run_data["errors"]
    timestamp = run_data["timestamp"]

    overall, grade, breakdown = calculate_overall_score(results)
    recommendations = generate_recommendations(results)

    lines = [
        f"# ASTRA RAG Test Report",
        f"**Date**: {timestamp}",
        f"**Overall RAG Score**: **{overall:.1f}/10** — {grade}",
        "",
        "## Score Breakdown",
        "```",
        breakdown,
        f"  ────────────────────────────",
        f"  OVERALL: {overall:.1f}/10",
        "```",
        "",
    ]

    # ── Per-test details ──
    lines.append("## Test Results")
    lines.append("")

    # Ingestion
    if "ingestion" in results and not results["ingestion"].get("error"):
        r = results["ingestion"]
        lines.append(f"### 1. Ingestion Quality — {r['score']}/10")
        lines.append(f"Passed: {r['passed']}/{r['total']}")
        lines.append("")
        lines.append("| Case | Status | Types Found | Subtypes | Issues |")
        lines.append("|------|--------|-------------|----------|--------|")
        for d in r.get("details", []):
            issues_str = "; ".join(d.get("issues", [])) or "—"
            lines.append(
                f"| {d['id']} | {'✓' if d['status'] == 'PASS' else '✗'} "
                f"| {', '.join(d.get('found_types', []))} "
                f"| {', '.join(d.get('found_subtypes', []))} "
                f"| {issues_str} |"
            )
        lines.append("")

    # Retrieval
    if "retrieval" in results and not results["retrieval"].get("error"):
        r = results["retrieval"]
        lines.append(f"### 2. Retrieval Precision — {r['score']}/10")
        lines.append(f"Passed: {r['passed']}/{r['total']}")
        lines.append("")
        lines.append("| Case | Status | P@3 | Top Score | Top-3 IDs | Issues |")
        lines.append("|------|--------|-----|-----------|-----------|--------|")
        for d in r.get("details", []):
            issues_str = "; ".join(d.get("issues", [])) or "—"
            top3 = ", ".join(str(x) for x in d.get("top3_doc_ids", []))
            lines.append(
                f"| {d['id']} | {'✓' if d['status'] == 'PASS' else '✗'} "
                f"| {d.get('precision_at_3', 0):.2f} "
                f"| {d.get('top_score', 0):.3f} "
                f"| {top3} "
                f"| {issues_str} |"
            )
        lines.append("")

    # Reranker
    if "reranker" in results and not results["reranker"].get("error"):
        r = results["reranker"]
        lines.append(f"### 3A. Reranker Weights — Best: {r['best_weights']} ({r['best_score']}/10)")
        lines.append("")
        lines.append("| Weight Set | Weights | Avg P@3 | Must-Include | Score |")
        lines.append("|-----------|---------|---------|--------------|-------|")
        for w in r.get("all_results", []):
            wts = w["weights"]
            lines.append(
                f"| {w['name']} "
                f"| s={wts['similarity']}/i={wts['importance']}/r={wts['recency']} "
                f"| {w['avg_precision_at_3']:.3f} "
                f"| {w['must_include_rate']:.3f} "
                f"| **{w['combined_score']:.1f}** |"
            )
        lines.append("")

    # MMR
    if "mmr" in results and not results["mmr"].get("error"):
        r = results["mmr"]
        lines.append(f"### 3B. MMR Diversity — Best penalty: {r['best_penalty']}")
        lines.append("")
        lines.append("| Penalty | Unique Clusters | Diversity Score |")
        lines.append("|---------|----------------|-----------------|")
        for m in r.get("all_results", []):
            marker = " ← current" if m["penalty"] == 0.4 else ""
            marker += " ★" if m["penalty"] == r["best_penalty"] else ""
            lines.append(
                f"| {m['penalty']}{marker} "
                f"| {m['unique_clusters']} "
                f"| {m['diversity_score']:.2f} |"
            )
        lines.append("")

    # E2E
    if "e2e" in results and not results["e2e"].get("error"):
        r = results["e2e"]
        lines.append(f"### 4. End-to-End — {r['score']}/10")
        lines.append(f"Passed: {r['passed']}/{r['total']}")
        lines.append("")
        for d in r.get("details", []):
            status = "✓" if d["status"] == "PASS" else "✗"
            lines.append(f"- **{d['id']}** {status}: {d['description']}")
            lines.append(f"  - Entities extracted: {d.get('entities_extracted', '?')}")
            lines.append(f"  - Keyword rate: {d.get('keyword_rate', '?')}")
            lines.append(f"  - Top score: {d.get('top_score', '?')}")
            if d.get("issues"):
                for issue in d["issues"]:
                    lines.append(f"  - ⚠ {issue}")
        lines.append("")

    # Prod Audit
    if "prod_audit" in results and not results["prod_audit"].get("error"):
        r = results["prod_audit"]
        lines.append(f"### 5. Production DB Health — {r['score']}/10")
        lines.append(f"Total vectors: {r['total_vectors']}")
        lines.append("")

        if r.get("source_distribution"):
            lines.append("**Source distribution:**")
            for src, cnt in sorted(r["source_distribution"].items(), key=lambda x: -x[1]):
                lines.append(f"- {src}: {cnt}")
            lines.append("")

        if r.get("importance_distribution"):
            lines.append("**Importance distribution:**")
            for imp, cnt in sorted(r["importance_distribution"].items()):
                lines.append(f"- importance={imp}: {cnt}")
            lines.append("")

        lines.append(f"- Milestones: {r.get('milestones_count', 0)}")
        lines.append(f"- Short docs (<50 chars): {r.get('short_docs_count', 0)}")
        lines.append(f"- Exact duplicates: {r.get('exact_duplicates', 0)}")
        lines.append(f"- Stale vectors: {r.get('stale_vectors', 0)}")
        lines.append(f"- Session/Enriched ratio: {r.get('session_enriched_ratio', '?')}")

        if r.get("issues"):
            lines.append("")
            lines.append("**Issues:**")
            for issue in r["issues"]:
                lines.append(f"- ⚠ {issue}")
        lines.append("")

    # ── Errors ──
    if errors:
        lines.append("## Errors")
        for key, err in errors.items():
            lines.append(f"- **{key}**: {err}")
        lines.append("")

    # ── Recommendations ──
    lines.append("## Recommendations")
    for rec in recommendations:
        lines.append(f"- {rec}")
    lines.append("")

    # ── Action Items ──
    lines.append("## Next Steps (Priority Order)")
    lines.append("")

    action_items = []
    if overall < 7.0:
        # Ingestion
        ing_score = results.get("ingestion", {}).get("score", 10)
        if ing_score < 7:
            action_items.append(
                f"1. **Fix Ingestion** (score: {ing_score}/10) — "
                f"Popraw entity extraction w SemanticExtractor (zero-shot labels, confidence thresholds)"
            )
        # Retrieval
        ret_score = results.get("retrieval", {}).get("score", 10)
        if ret_score < 7:
            action_items.append(
                f"2. **Fix Retrieval** (score: {ret_score}/10) — "
                f"Zwiększ keyword_boost, rozważ cross-encoder, popraw pool_size"
            )
        # Reranker tune
        if "reranker" in results:
            rr = results["reranker"]
            if rr.get("best_weights") != "current_production":
                action_items.append(
                    f"3. **Apply better weights** — Zmień na {rr.get('best_weights')} w vector_store.py"
                )
        # MMR tune
        if "mmr" in results:
            mm = results["mmr"]
            if mm.get("best_penalty") != 0.4:
                action_items.append(
                    f"4. **Adjust MMR penalty** — Zmień diversity_penalty na {mm['best_penalty']} w vector_store.py"
                )
    else:
        action_items.append("✓ RAG score ≥ 7.0 — cel osiągnięty! Można przejść do portowania pipeline do agenta sprzedażowego.")

    for item in action_items:
        lines.append(item)

    lines.append("")
    lines.append("---")
    lines.append(f"*Report generated by Astra RAG Test Suite at {timestamp}*")

    return "\n".join(lines)


# ──────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Astra RAG Test Suite Runner")
    parser.add_argument("--skip-prod", action="store_true",
                        help="Pomiń audyt produkcyjnej bazy")
    parser.add_argument("--only", type=str, default=None,
                        choices=list(TEST_REGISTRY) + list(PROD_TESTS),
                        help=f"Uruchom tylko wybrany test: {list(TEST_REGISTRY) + list(PROD_TESTS)}")
    parser.add_argument("--no-report", action="store_true",
                        help="Nie generuj pliku raportu")
    args = parser.parse_args()

    print("=" * 70)
    print("  ASTRA RAG TEST SUITE")
    print(f"  {datetime.utcnow().isoformat(timespec='seconds')}Z")
    print("=" * 70)

    # Uruchom testy
    run_data = run_all(skip_prod=args.skip_prod, only=args.only)

    # Podsumowanie na konsolę
    results = run_data["results"]
    overall, grade, breakdown = calculate_overall_score(results)

    print("\n" + "#" * 70)
    print("#  FINAL SUMMARY")
    print("#" * 70)
    print(f"\n{breakdown}")
    print(f"\n  OVERALL RAG SCORE: {overall:.1f}/10 — {grade}")

    if run_data["errors"]:
        print(f"\n  ERRORS: {len(run_data['errors'])} tests failed to run")
        for key, err in run_data["errors"].items():
            print(f"    {key}: {err}")

    # Rekomendacje
    recommendations = generate_recommendations(results)
    print("\n  RECOMMENDATIONS:")
    for rec in recommendations:
        print(f"    {rec}")

    # Generuj raport Markdown
    if not args.no_report:
        report = generate_report(run_data)
        report_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'analizy')
        os.makedirs(report_dir, exist_ok=True)
        ts_file = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        report_path = os.path.join(report_dir, f"rag_test_report_{ts_file}.md")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"\n  Report saved to: {report_path}")

    print("\n" + "=" * 70)
    return overall


if __name__ == "__main__":
    score = main()
    sys.exit(0 if score >= 7.0 else 1)
