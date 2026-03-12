"""
ASTRA - Semantic Density Audit
Kalibruje HIGH_CONFIDENCE_THRESHOLD po zmianie modelu embeddingów.

Problem: HIGH_CONFIDENCE_THRESHOLD = 0.25 był ustawiony pod all-MiniLM-L6-v2 (angielski).
         Po zmianie na paraphrase-multilingual-MiniLM-L12-v2 próg może być źle skalibrowany.

Działanie:
1. Ładuje nowy model
2. Testuje pary zdań o PODOBNYM znaczeniu (powinny mieć niski dystans)
3. Testuje pary zdań o RÓŻNYM znaczeniu (powinny mieć wysoki dystans)
4. Sugeruje optymalny próg na podstawie rozkładu dystansów

Uruchomienie: venv/bin/python3 semantic_density_audit.py
"""

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
OLD_THRESHOLD = 0.25  # ustawiony pod all-MiniLM-L6-v2

# ── Pary PODOBNE — powinny mieć NISKI dystans (wysoka similarity) ──
SIMILAR_PAIRS = [
    ("mam Crohna",                          "jelita mi dzisiaj siadają"),
    ("jestem zmęczony",                     "nie mam dzisiaj energii"),
    ("pracuję nad projektem LDI",           "buduję system wykrywania utraconego popytu"),
    ("boli mnie brzuch",                    "Crohn daje się we znaki"),
    ("biorę Stelarę",                       "jestem na leczeniu biologicznym"),
    ("buduję Astrę",                        "pracuję nad AI companion"),
    ("mam wizytę u lekarza jutro",          "jutro idę do kliniki"),
    ("nie śpię dobrze",                     "miałem bezsenną noc"),
    ("kończę leki",                         "wystarczy mi do końca miesiąca"),
    ("oglądam anime",                       "lecę Call of the Night"),
]

# ── Pary RÓŻNE — powinny mieć WYSOKI dystans (niska similarity) ──
DIFFERENT_PAIRS = [
    ("mam Crohna",                          "lubię kawę"),
    ("jestem zmęczony",                     "projekt idzie świetnie"),
    ("biorę Stelarę",                       "oglądam anime dzisiaj"),
    ("buduję Astrę",                        "boli mnie głowa"),
    ("wizyta u lekarza jutro",              "klocki hamulcowe do BMW"),
    ("nie śpię dobrze",                     "zrobiłem świetny commit"),
    ("kończę leki",                         "lubię pizzę"),
    ("pracuję nad RAGiem",                  "idę spać"),
]


def cosine_distance(v1, v2) -> float:
    """Dystans cosinusowy (0 = identyczne, 2 = przeciwne). ChromaDB używa tego."""
    sim = cosine_similarity([v1], [v2])[0][0]
    return round(1.0 - sim, 4)


def main():
    print("=" * 60)
    print(f"SEMANTIC DENSITY AUDIT")
    print(f"Model: {MODEL_NAME}")
    print(f"Stary próg HIGH_CONFIDENCE: {OLD_THRESHOLD}")
    print("=" * 60)

    print(f"\nŁadowanie modelu...")
    model = SentenceTransformer(MODEL_NAME)
    print("Model załadowany.\n")

    # ── Test par PODOBNYCH ──
    print("─" * 60)
    print("PARY PODOBNE (oczekujemy: niski dystans)")
    print("─" * 60)
    similar_distances = []
    for a, b in SIMILAR_PAIRS:
        va = model.encode(a)
        vb = model.encode(b)
        dist = cosine_distance(va, vb)
        similar_distances.append(dist)
        flag = "✅" if dist < OLD_THRESHOLD else "⚠️ "
        print(f"{flag} dist={dist:.4f} | '{a}' ↔ '{b}'")

    avg_similar = np.mean(similar_distances)
    max_similar = np.max(similar_distances)
    print(f"\nSredni dystans PODOBNYCH: {avg_similar:.4f}")
    print(f"Maksymalny dystans PODOBNYCH: {max_similar:.4f}")

    # ── Test par RÓŻNYCH ──
    print("\n" + "─" * 60)
    print("PARY RÓŻNE (oczekujemy: wysoki dystans)")
    print("─" * 60)
    different_distances = []
    for a, b in DIFFERENT_PAIRS:
        va = model.encode(a)
        vb = model.encode(b)
        dist = cosine_distance(va, vb)
        different_distances.append(dist)
        flag = "✅" if dist > OLD_THRESHOLD else "⚠️ "
        print(f"{flag} dist={dist:.4f} | '{a}' ↔ '{b}'")

    avg_different = np.mean(different_distances)
    min_different = np.min(different_distances)
    print(f"\nSredni dystans RÓŻNYCH: {avg_different:.4f}")
    print(f"Minimalny dystans RÓŻNYCH: {min_different:.4f}")

    # ── Kalibracja progu ──
    print("\n" + "=" * 60)
    print("REKOMENDACJA PROGU")
    print("=" * 60)

    # Optymalny próg: w połowie między max(similar) a min(different)
    suggested = round((max_similar + min_different) / 2, 3)
    gap = round(min_different - max_similar, 4)

    print(f"\nStary próg (all-MiniLM-L6-v2):     HIGH_CONFIDENCE = {OLD_THRESHOLD}")
    print(f"Sugerowany próg (multilingual-L12): HIGH_CONFIDENCE = {suggested}")
    print(f"Gap między podobnymi a różnymi:     {gap:.4f}")

    if gap < 0.05:
        print("\n⚠️  UWAGA: Gap bardzo mały — model słabo rozróżnia podobne od różnych.")
        print("   Rozważ dodanie kontekstu do zdań testowych lub zmianę modelu.")
    elif gap > 0.15:
        print("\n✅ Dobry gap — model dobrze odróżnia podobne od różnych.")
    else:
        print("\n✅ Akceptowalny gap.")

    print(f"\n>>> Zaktualizuj w strict_grounding.py:")
    print(f"    HIGH_CONFIDENCE_THRESHOLD = {suggested}")

    # ── Ocena starego progu ──
    print("\n" + "─" * 60)
    if OLD_THRESHOLD > max_similar:
        print(f"✅ Stary próg {OLD_THRESHOLD} nadal poprawny dla par podobnych.")
    else:
        print(f"⚠️  Stary próg {OLD_THRESHOLD} ZA CIASNY — {sum(1 for d in similar_distances if d >= OLD_THRESHOLD)} par podobnych")
        print(f"   trafia w LOW_CONFIDENCE zamiast GROUNDED.")

    print("=" * 60)


if __name__ == "__main__":
    main()
