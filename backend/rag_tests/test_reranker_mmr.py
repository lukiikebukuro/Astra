"""
TEST 3: Reranker Weights + MMR Diversity
Dwa testy w jednym:

A) RERANKER: Testuje różne zestawy wag (similarity/importance/recency)
   na tych samych danych i porównuje precision@3. Wskazuje optymalny zestaw.

B) MMR: Testuje różne diversity_penalty i sprawdza czy wyniki nie są klonami.
   Mierzy: cluster diversity (ile różnych klastrów w top-N).

NIE dotyka produkcyjnej bazy.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from datetime import datetime, timedelta
from rag_tests.test_config import (
    TEST_COLLECTION_NAME, TEST_USER_ID, TEST_SALT, TEST_PERSONA,
    RETRIEVAL_DOCUMENTS, RETRIEVAL_QUERIES,
    RERANKER_WEIGHT_SETS,
    MMR_TEST_DOCUMENTS, MMR_DIVERSITY_PENALTIES,
)
from vector_store import VectorStore


def _setup_test_collection(vs: VectorStore, documents: list):
    """Czyści i wstawia dokumenty do testowej kolekcji."""
    try:
        all_data = vs.collection.get()
        if all_data['ids']:
            vs.collection.delete(ids=all_data['ids'])
    except Exception:
        pass

    base_time = datetime.utcnow()
    for i, doc in enumerate(documents):
        ts = (base_time - timedelta(days=30 - i)).isoformat()
        vs.add_memory(
            text=doc["text"] if isinstance(doc.get("text"), str) else doc["text"],
            user_id=TEST_USER_ID,
            salt=TEST_SALT,
            persona_id=TEST_PERSONA,
            source=doc.get("source", "enriched"),
            importance=doc.get("importance", 5),
            is_milestone=doc.get("is_milestone", False),
            timestamp=ts,
        )


def _find_doc_id(result_text: str, documents: list) -> str | None:
    for doc in documents:
        if doc["text"][:50] in result_text or result_text[:50] in doc["text"]:
            return doc.get("id", None)
    return None


# ──────────────────────────────────────────────────────────────
# A) RERANKER WEIGHTS TEST
# ──────────────────────────────────────────────────────────────

def run_reranker_test() -> dict:
    """Testuje różne zestawy wag rerankersa."""
    print("\n" + "=" * 60)
    print("TEST 3A: RERANKER WEIGHTS COMPARISON")
    print("=" * 60)

    vs = VectorStore(collection_name=TEST_COLLECTION_NAME)
    _setup_test_collection(vs, RETRIEVAL_DOCUMENTS)

    weight_results = []

    for weight_set in RERANKER_WEIGHT_SETS:
        name = weight_set["name"]
        weights = weight_set["weights"]
        desc = weight_set["description"]

        print(f"\n--- Testing: {name} ---")
        print(f"    Weights: sim={weights['similarity']} imp={weights['importance']} rec={weights['recency']}")

        # Zapisz oryginalne wagi i podmień
        original_weights = vs.DEFAULT_WEIGHTS.copy()
        vs.DEFAULT_WEIGHTS = weights

        total_precision = 0.0
        must_include_hits = 0
        must_include_total = 0
        must_exclude_violations = 0
        must_exclude_total = 0
        query_scores = []

        for case in RETRIEVAL_QUERIES:
            must_include = case.get("must_include", [])
            must_exclude = case.get("must_exclude", [])

            try:
                search_results = vs.search_memories(
                    query=case["query"],
                    persona_id=TEST_PERSONA,
                    n=5, pool_size=20,
                    user_id=TEST_USER_ID, salt=TEST_SALT,
                )
            except Exception:
                continue

            result_ids = []
            for r in search_results:
                doc_id = _find_doc_id(r.get("text", ""), RETRIEVAL_DOCUMENTS)
                result_ids.append(doc_id)

            top3 = result_ids[:3]
            expected = case["expected_doc_ids"]

            if expected:
                hits = sum(1 for rid in top3 if rid in expected)
                precision = hits / min(3, len(expected))
            else:
                precision = 1.0
            total_precision += precision

            for mid in must_include:
                must_include_total += 1
                if mid in top3:
                    must_include_hits += 1

            for xid in must_exclude:
                must_exclude_total += 1
                if xid in top3:
                    must_exclude_violations += 1

            top_score = search_results[0].get("final_score", 0) if search_results else 0
            query_scores.append({"query": case["query"][:40], "p@3": precision, "top_score": top_score})

        # Przywróć oryginalne wagi
        vs.DEFAULT_WEIGHTS = original_weights

        n_queries = len(RETRIEVAL_QUERIES)
        avg_p = total_precision / n_queries if n_queries > 0 else 0
        mi_rate = must_include_hits / must_include_total if must_include_total > 0 else 1.0
        # Kara za wpuszczenie noise doc do top-3 (każde naruszenie = -0.1 z combined_score)
        noise_penalty = (must_exclude_violations / must_exclude_total) * 2.0 if must_exclude_total > 0 else 0.0
        combined_score = max(0.0, avg_p * 5 + mi_rate * 3 + (1.0 - noise_penalty / 2) * 2)

        print(f"    Avg P@3: {avg_p:.2f} | Must-Include: {mi_rate:.2f} | Noise violations: {must_exclude_violations}/{must_exclude_total} | Score: {combined_score:.1f}/10")

        weight_results.append({
            "name": name,
            "weights": weights,
            "description": desc,
            "avg_precision_at_3": round(avg_p, 3),
            "must_include_rate": round(mi_rate, 3),
            "noise_violations": must_exclude_violations,
            "combined_score": round(combined_score, 1),
            "per_query": query_scores,
        })

    # Posortuj wg score
    weight_results.sort(key=lambda x: x["combined_score"], reverse=True)

    best = weight_results[0]
    current = next((w for w in weight_results if w["name"] == "current_production"), None)

    print(f"\n{'=' * 60}")
    print(f"BEST WEIGHTS: {best['name']} (score: {best['combined_score']}/10)")
    print(f"  Weights: {best['weights']}")
    if current and current["name"] != best["name"]:
        delta = best["combined_score"] - current["combined_score"]
        print(f"  vs Current: {'+' if delta > 0 else ''}{delta:.1f} improvement")
    print(f"{'=' * 60}")

    return {
        "test_name": "Reranker Weights",
        "best_weights": best["name"],
        "best_score": best["combined_score"],
        "current_score": current["combined_score"] if current else None,
        "recommendation": best["weights"] if best["name"] != "current_production" else "Aktualne wagi są optymalne",
        "all_results": weight_results,
    }


# ──────────────────────────────────────────────────────────────
# B) MMR DIVERSITY TEST
# ──────────────────────────────────────────────────────────────

def run_mmr_test() -> dict:
    """Testuje różne diversity_penalty w MMR."""
    print("\n" + "=" * 60)
    print("TEST 3B: MMR DIVERSITY")
    print("=" * 60)

    vs = VectorStore(collection_name=TEST_COLLECTION_NAME)

    # Przygotuj dokumenty z tagami klastrów
    docs_with_clusters = []
    clusters = ["crohn", "crohn", "crohn", "project", "project", "dreams"]
    for i, doc in enumerate(MMR_TEST_DOCUMENTS):
        docs_with_clusters.append({**doc, "cluster": clusters[i], "source": "enriched", "is_milestone": False})
    _setup_test_collection(vs, [{"text": d["text"], "importance": d["importance"],
                                  "source": "enriched", "is_milestone": False}
                                 for d in docs_with_clusters])

    query = "Opowiedz mi o Łukaszu"  # Szeroki query — powinien trafić we wszystkie klastry
    mmr_results = []

    for penalty in MMR_DIVERSITY_PENALTIES:
        print(f"\n--- diversity_penalty={penalty} ---")

        # Pobierz surowe wyniki (pool)
        try:
            raw_results = vs.collection.query(
                query_texts=[query],
                n_results=len(MMR_TEST_DOCUMENTS),
                include=["documents", "metadatas", "distances"]
            )
        except Exception as e:
            print(f"    ERROR: {e}")
            continue

        # Zbuduj listę wyników
        pool = []
        for i, doc in enumerate(raw_results['documents'][0]):
            pool.append({
                'text': doc,
                'metadata': raw_results['metadatas'][0][i],
                'distance': raw_results['distances'][0][i],
            })

        # Rerank
        pool = vs.rerank(pool, query=query)

        # MMR select z różnymi penalties
        selected = vs._mmr_select(pool, n=3, diversity_penalty=penalty)

        # Sprawdź diversity: ile różnych klastrów w top-3
        selected_clusters = []
        for s in selected:
            s_text = s.get('text', '')
            for dc in docs_with_clusters:
                if dc['text'][:40] in s_text or s_text[:40] in dc['text']:
                    selected_clusters.append(dc['cluster'])
                    break

        unique_clusters = len(set(selected_clusters))
        total_clusters = len(set(clusters))
        diversity_score = unique_clusters / min(3, total_clusters)

        print(f"    Selected clusters: {selected_clusters}")
        print(f"    Unique: {unique_clusters}/{min(3, total_clusters)} | Diversity: {diversity_score:.2f}")

        for j, s in enumerate(selected):
            print(f"    [{j+1}] score={s.get('final_score', 0):.3f} | {s['text'][:60]}")

        mmr_results.append({
            "penalty": penalty,
            "selected_clusters": selected_clusters,
            "unique_clusters": unique_clusters,
            "diversity_score": round(diversity_score, 2),
        })

    # Znajdź optymalne penalty (highest diversity while keeping relevance)
    best_mmr = max(mmr_results, key=lambda x: x["diversity_score"])
    current_penalty = 0.4
    current_result = next((r for r in mmr_results if r["penalty"] == current_penalty), None)

    print(f"\n{'=' * 60}")
    print(f"BEST MMR PENALTY: {best_mmr['penalty']} (diversity: {best_mmr['diversity_score']})")
    if current_result:
        print(f"CURRENT (0.4): diversity={current_result['diversity_score']}")
    print(f"{'=' * 60}")

    # Cleanup
    try:
        all_data = vs.collection.get()
        if all_data['ids']:
            vs.collection.delete(ids=all_data['ids'])
    except Exception:
        pass

    return {
        "test_name": "MMR Diversity",
        "best_penalty": best_mmr["penalty"],
        "best_diversity": best_mmr["diversity_score"],
        "current_diversity": current_result["diversity_score"] if current_result else None,
        "recommendation": best_mmr["penalty"] if best_mmr["penalty"] != current_penalty else "Aktualne penalty=0.4 jest optymalne",
        "all_results": mmr_results,
    }


if __name__ == "__main__":
    reranker = run_reranker_test()
    mmr = run_mmr_test()
    print(f"\nReranker best: {reranker['best_weights']} ({reranker['best_score']}/10)")
    print(f"MMR best penalty: {mmr['best_penalty']} (diversity: {mmr['best_diversity']})")
