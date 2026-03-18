"""
TEST 5: Production DB Audit
Skanuje PRODUKCYJNĄ bazę ChromaDB (READ-ONLY) i raportuje:
- Ile wektorów per source
- Rozkład importance
- Duplikaty (similarity > 0.95 między wektorami)
- Echo loop detection (krótkie, powtarzające się frazy)
- Stale vectors (importance < 3, starsze niż 14 dni)

NIE MODYFIKUJE produkcyjnej bazy.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from datetime import datetime, timedelta
from collections import Counter
from rag_tests.test_config import PROD_COLLECTION_NAME
from vector_store import VectorStore

# Hardcoded sanity queries — zakładamy że po kilku tygodniach użytkowania
# te fakty MUSZĄ być w bazie z sensownym wynikiem.
# Zmień/rozszerz gdy baza urośnie.
PROD_SANITY_QUERIES = [
    {
        "query": "Choroba Crohna, zdrowie Łukasza",
        "min_top_score": 0.50,
        "expected_keywords": ["crohn", "stelara", "zdrowi", "rzut", "gastrolog"],
        "description": "Zdrowie — kluczowy fakt o Łukaszu",
    },
    {
        "query": "Projekty i systemy które zbudował Łukasz",
        "min_top_score": 0.45,
        "expected_keywords": ["ldi", "anima", "astra", "skankran", "pipeline", "projekt"],
        "description": "Projekty techniczne",
    },
    {
        "query": "Kim jest Amelia, historia z Amelią",
        "min_top_score": 0.40,
        "expected_keywords": ["ameli", "amelk", "companion", "ucho"],
        "description": "Amelia — AI companion",
    },
    {
        "query": "Marzenia i plany na przyszłość",
        "min_top_score": 0.40,
        "expected_keywords": ["marzy", "marzeni", "japoni", "android", "plan", "przyszłość"],
        "description": "Marzenia — milestone",
    },
    {
        "query": "Trudne emocje, ból, co go zraniło",
        "min_top_score": 0.35,
        "expected_keywords": ["ex", "zrani", "smutn", "trudno", "depresj", "zosta"],
        "description": "Emocje negatywne — trauma",
    },
]


def run_prod_audit() -> dict:
    """Read-only audit produkcyjnej bazy."""
    print("\n" + "=" * 60)
    print("TEST 5: PRODUCTION DB AUDIT (READ-ONLY)")
    print("=" * 60)

    vs = VectorStore(collection_name=PROD_COLLECTION_NAME)
    total = vs.collection.count()
    print(f"Total vectors in production: {total}")

    if total == 0:
        print("PUSTA BAZA — nic do audytu")
        return {"test_name": "Production Audit", "total_vectors": 0, "score": 0}

    # Pobierz wszystkie metadane (bez embeddingów — memory efficient)
    all_data = vs.collection.get(include=["documents", "metadatas"])

    docs = all_data["documents"]
    metas = all_data["metadatas"]

    # ── Rozkład source ──
    source_counts = Counter(m.get("source", "unknown") for m in metas)
    print(f"\nSource distribution:")
    for src, cnt in source_counts.most_common():
        print(f"  {src}: {cnt} ({cnt/total*100:.1f}%)")

    # ── Rozkład importance ──
    importance_counts = Counter(m.get("importance", 0) for m in metas)
    print(f"\nImportance distribution:")
    for imp in sorted(importance_counts.keys()):
        cnt = importance_counts[imp]
        print(f"  importance={imp}: {cnt} ({cnt/total*100:.1f}%)")

    # ── Milestones ──
    milestones = [(docs[i], metas[i]) for i in range(len(docs))
                  if metas[i].get("is_milestone")]
    print(f"\nMilestones: {len(milestones)}")
    for doc, meta in milestones[:5]:
        print(f"  [{meta.get('importance', '?')}] {doc[:80]}")

    # ── Echo detection: krótkie dokumenty (<50 chars) ──
    short_docs = [(docs[i], metas[i]) for i in range(len(docs)) if len(docs[i]) < 50]
    print(f"\nShort documents (<50 chars): {len(short_docs)} ({len(short_docs)/total*100:.1f}%)")
    if short_docs:
        for doc, meta in short_docs[:10]:
            print(f"  [{meta.get('source', '?')}] \"{doc}\"")

    # ── Duplicate detection (exact text match) ──
    text_counts = Counter(docs)
    exact_dupes = {text: cnt for text, cnt in text_counts.items() if cnt > 1}
    print(f"\nExact duplicates: {len(exact_dupes)} unique texts with copies")
    for text, cnt in sorted(exact_dupes.items(), key=lambda x: -x[1])[:5]:
        print(f"  {cnt}x: \"{text[:80]}\"")

    # ── Stale vectors (low importance, old) ──
    now = datetime.utcnow()
    stale_cutoff = now - timedelta(days=14)
    stale = []
    for i in range(len(docs)):
        imp = metas[i].get("importance", 5)
        ts_str = metas[i].get("timestamp", "")
        if imp <= 3 and ts_str:
            try:
                ts = datetime.fromisoformat(ts_str.split(".")[0].replace("Z", ""))
                if ts < stale_cutoff:
                    stale.append((docs[i], metas[i]))
            except (ValueError, TypeError):
                pass
    print(f"\nStale vectors (importance ≤ 3, older than 14 days): {len(stale)}")
    if stale:
        for doc, meta in stale[:5]:
            print(f"  [imp={meta.get('importance')}] {doc[:60]} | {meta.get('timestamp', '')[:10]}")

    # ── Session message ratio (echo risk) ──
    session_msgs = source_counts.get("session_message", 0)
    enriched = source_counts.get("enriched", 0) + source_counts.get("extracted_person", 0)
    ratio = session_msgs / enriched if enriched > 0 else float('inf')
    print(f"\nSession/Enriched ratio: {ratio:.1f} (session={session_msgs}, enriched={enriched})")
    if ratio > 5:
        print("  ⚠ WARNING: Zbyt dużo session messages vs enriched — potencjalny echo problem")

    # ── Health Score ──
    issues = []
    health_score = 10.0

    # Penalty: zbyt dużo krótkich dokumentów
    short_pct = len(short_docs) / total if total > 0 else 0
    if short_pct > 0.2:
        health_score -= 2.0
        issues.append(f"Zbyt dużo krótkich dokumentów: {short_pct*100:.0f}% (limit: 20%)")
    elif short_pct > 0.1:
        health_score -= 1.0
        issues.append(f"Sporo krótkich dokumentów: {short_pct*100:.0f}%")

    # Penalty: duplikaty
    dupe_count = sum(cnt - 1 for cnt in exact_dupes.values())
    dupe_pct = dupe_count / total if total > 0 else 0
    if dupe_pct > 0.1:
        health_score -= 2.0
        issues.append(f"Dużo duplikatów: {dupe_count} ({dupe_pct*100:.0f}%)")
    elif dupe_pct > 0.05:
        health_score -= 1.0
        issues.append(f"Umiarkowane duplikaty: {dupe_count}")

    # Penalty: session/enriched ratio
    if ratio > 10:
        health_score -= 2.0
        issues.append(f"Session message bloat: ratio={ratio:.1f}")
    elif ratio > 5:
        health_score -= 1.0
        issues.append(f"Dużo session messages: ratio={ratio:.1f}")

    # Penalty: brak milestones
    if len(milestones) == 0 and total > 50:
        health_score -= 1.0
        issues.append("Zero milestones — system nie wykrywa ważnych momentów")

    # Penalty: stale vectors
    stale_pct = len(stale) / total if total > 0 else 0
    if stale_pct > 0.3:
        health_score -= 1.0
        issues.append(f"Dużo stale vectors: {len(stale)} ({stale_pct*100:.0f}%)")

    health_score = max(0, health_score)

    print(f"\n{'=' * 60}")
    print(f"PRODUCTION HEALTH SCORE: {health_score:.1f}/10")
    if issues:
        print("Issues:")
        for issue in issues:
            print(f"  ⚠ {issue}")
    else:
        print("  ✓ No issues detected")
    print(f"{'=' * 60}")

    return {
        "test_name": "Production DB Audit",
        "score": round(health_score, 1),
        "total_vectors": total,
        "source_distribution": dict(source_counts),
        "importance_distribution": {str(k): v for k, v in sorted(importance_counts.items())},
        "milestones_count": len(milestones),
        "short_docs_count": len(short_docs),
        "exact_duplicates": len(exact_dupes),
        "stale_vectors": len(stale),
        "session_enriched_ratio": round(ratio, 1),
        "issues": issues,
    }


def run_prod_retrieval_check(user_id: str = None, salt: str = None) -> dict:
    """
    Sanity check: odpytuje produkcyjną bazę 5 hardcoded zapytaniami.
    Sprawdza czy kluczowe fakty o Łukaszu są dostępne z sensownym score.
    READ-ONLY — nie modyfikuje bazy.

    Args:
        user_id: opcjonalny user_id (jeśli izolacja SaaS aktywna)
        salt: opcjonalny salt
    """
    print("\n" + "=" * 60)
    print("TEST 4: PROD RETRIEVAL SANITY CHECK")
    print("=" * 60)

    vs = VectorStore(collection_name=PROD_COLLECTION_NAME)
    total = vs.collection.count()

    if total == 0:
        print("PUSTA BAZA — brak danych do sprawdzenia")
        return {"test_name": "Prod Retrieval Check", "score": 0, "passed": 0, "total": 0}

    passed = 0
    warnings = []
    results_summary = []

    for case in PROD_SANITY_QUERIES:
        print(f"\n--- {case['description']} ---")
        print(f"    Query: {case['query']}")

        try:
            results = vs.search_memories(
                query=case["query"],
                persona_id="astra",
                n=3,
                pool_size=20,
                user_id=user_id,
                salt=salt,
            )
        except Exception as e:
            print(f"    ERROR: {e}")
            warnings.append(f"{case['description']}: search error — {e}")
            results_summary.append({"query": case["query"], "passed": False, "top_score": 0})
            continue

        if not results:
            print(f"    FAIL — brak wyników")
            warnings.append(f"{case['description']}: zero wyników")
            results_summary.append({"query": case["query"], "passed": False, "top_score": 0})
            continue

        top = results[0]
        top_score = top.get("final_score", 0)
        top_text = top.get("text", "")[:100]

        # Sprawdź keyword match w top-3 wynikach
        combined_text = " ".join(r.get("text", "").lower() for r in results)
        kw_hits = [kw for kw in case["expected_keywords"] if kw.lower() in combined_text]
        kw_ratio = len(kw_hits) / len(case["expected_keywords"]) if case["expected_keywords"] else 1.0

        score_ok = top_score >= case["min_top_score"]
        kw_ok = kw_ratio >= 0.4  # przynajmniej 40% oczekiwanych słów kluczowych

        case_passed = score_ok and kw_ok
        if case_passed:
            passed += 1
            status = "PASS"
        else:
            status = "FAIL"
            fail_reasons = []
            if not score_ok:
                fail_reasons.append(f"score {top_score:.2f} < min {case['min_top_score']}")
            if not kw_ok:
                fail_reasons.append(f"keywords {kw_hits}/{case['expected_keywords']} ({kw_ratio:.0%})")
            warnings.append(f"{case['description']}: {', '.join(fail_reasons)}")

        print(f"    [{status}] top_score={top_score:.3f} | keywords={kw_hits}")
        print(f"    Top result: \"{top_text}\"")

        results_summary.append({
            "query": case["query"],
            "description": case["description"],
            "passed": case_passed,
            "top_score": round(top_score, 3),
            "kw_ratio": round(kw_ratio, 2),
            "top_text": top_text,
        })

    overall_score = round((passed / len(PROD_SANITY_QUERIES)) * 10, 1)

    print(f"\n{'=' * 60}")
    print(f"PROD RETRIEVAL: {passed}/{len(PROD_SANITY_QUERIES)} passed — Score: {overall_score}/10")
    if warnings:
        print("Failures:")
        for w in warnings:
            print(f"  ✗ {w}")
    else:
        print("  ✓ All sanity checks passed")
    print(f"{'=' * 60}")

    return {
        "test_name": "Prod Retrieval Check",
        "score": overall_score,
        "passed": passed,
        "total": len(PROD_SANITY_QUERIES),
        "warnings": warnings,
        "results": results_summary,
    }


if __name__ == "__main__":
    result = run_prod_audit()
    print(f"\nHealth score: {result['score']}/10")

    # Opcjonalnie: retrieval check (wymaga user_id/salt z env jeśli izolacja aktywna)
    import os as _os
    uid = _os.getenv("USER_ID")
    salt = _os.getenv("USER_ID_SALT")
    retrieval = run_prod_retrieval_check(user_id=uid, salt=salt)
    print(f"Retrieval sanity: {retrieval['passed']}/{retrieval['total']} ({retrieval['score']}/10)")
