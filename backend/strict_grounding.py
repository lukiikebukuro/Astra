"""
ANIMA - Strict Grounding Module
Zapobiega halucynacjom AI poprzez wykrywanie braku danych w RAG.

PROBLEM: AI wymysla fakty gdy RAG nie zwraca wynikow lub ma niskie confidence.
ROZWIAZANIE: System wykrywa brak danych i wstrzykuje tag [NO_DATA] lub [LOW_CONFIDENCE],
             ktory instruuje AI by powiedziec "nie pamietam" zamiast zgadywac.

Uzywane przez:
- Sales agentow (ANIMA) - firmy NIE MOGA miec agentow ktorzy klamia
- AI companions (ASTRA) - prawdziwa relacja wymaga szczerości
"""

from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass


@dataclass
class GroundingResult:
    """Wynik analizy grounding dla zapytania RAG."""
    confidence: float  # 0.0 - 1.0
    result_count: int
    avg_distance: float
    grounding_status: str  # 'GROUNDED', 'LOW_CONFIDENCE', 'NO_DATA'
    grounding_tag: str  # Tag do wstrzykniecia w kontekst


class StrictGrounding:
    """
    System Strict Grounding dla ANIMA.

    Poziomy grounding:
    - GROUNDED: RAG zwrocil wyniki z wysokim confidence (distance < 0.6)
    - LOW_CONFIDENCE: RAG zwrocil wyniki ale z niskim similarity (distance 0.6-1.0)
    - NO_DATA: RAG zwrocil 0 wynikow lub distance > 1.0
    """

    # Progi dla confidence
    # Skalibrowane dla paraphrase-multilingual-MiniLM-L12-v2 na polskim tekście.
    # Audit (2026-03-12): podobne pary avg=0.55, różne pary avg=0.78.
    # Stary próg 0.25 (dla all-MiniLM-L6-v2) był za ciasny — 9/10 podobnych par
    # trafiało w LOW_CONFIDENCE zamiast GROUNDED.
    HIGH_CONFIDENCE_THRESHOLD = 0.55  # distance < 0.55 = high confidence
    LOW_CONFIDENCE_THRESHOLD = 0.80   # distance > 0.80 = no data
    MIN_RESULTS_FOR_CONFIDENCE = 2    # minimum wynikow dla GROUNDED

    # Tagi do wstrzykiwania
    NO_DATA_TAG = "[NO_DATA - Nie mam informacji na ten temat w pamięci]"
    LOW_CONFIDENCE_TAG = "[LOW_CONFIDENCE - Mam fragmentaryczne wspomnienia, mogę się mylić]"
    GROUNDED_TAG = "[GROUNDED - Mam pewne wspomnienia na ten temat]"

    def __init__(self, strict_mode: bool = True):
        """
        Initialize StrictGrounding.

        Args:
            strict_mode: If True, NO_DATA triggers hard refusal instruction.
                        If False, allows softer "nie jestem pewna" responses.
        """
        self.strict_mode = strict_mode

    def analyze_rag_results(self, results: List[Dict], query: str = "") -> GroundingResult:
        """
        Analizuj wyniki RAG i okresl poziom grounding.

        Args:
            results: Lista wynikow z RAG (musi zawierac 'distance')
            query: Oryginalne zapytanie (dla logow)

        Returns:
            GroundingResult z confidence i tagami
        """
        if not results:
            return GroundingResult(
                confidence=0.0,
                result_count=0,
                avg_distance=float('inf'),
                grounding_status='NO_DATA',
                grounding_tag=self.NO_DATA_TAG
            )

        # Oblicz sredni distance
        distances = [r.get('distance', 1.0) for r in results]
        avg_distance = sum(distances) / len(distances)
        min_distance = min(distances)

        # Oblicz confidence (inverse of distance, normalized)
        # distance 0.0 = confidence 1.0
        # distance 1.0 = confidence 0.5
        # distance 2.0 = confidence 0.0
        confidence = max(0.0, min(1.0, 1.0 - (min_distance / 2.0)))

        # Okresl status grounding
        if len(results) < self.MIN_RESULTS_FOR_CONFIDENCE:
            if min_distance > self.LOW_CONFIDENCE_THRESHOLD:
                grounding_status = 'NO_DATA'
                grounding_tag = self.NO_DATA_TAG
            else:
                grounding_status = 'LOW_CONFIDENCE'
                grounding_tag = self.LOW_CONFIDENCE_TAG
        elif min_distance < self.HIGH_CONFIDENCE_THRESHOLD:
            grounding_status = 'GROUNDED'
            grounding_tag = self.GROUNDED_TAG
        elif min_distance < self.LOW_CONFIDENCE_THRESHOLD:
            grounding_status = 'LOW_CONFIDENCE'
            grounding_tag = self.LOW_CONFIDENCE_TAG
        else:
            grounding_status = 'NO_DATA'
            grounding_tag = self.NO_DATA_TAG

        return GroundingResult(
            confidence=round(confidence, 3),
            result_count=len(results),
            avg_distance=round(avg_distance, 3),
            grounding_status=grounding_status,
            grounding_tag=grounding_tag
        )

    def get_grounding_directive(self, grounding_result: GroundingResult) -> str:
        """
        Zwroc dyrektywe grounding do wstrzykniecia w kontekst.

        Args:
            grounding_result: Wynik analyze_rag_results()

        Returns:
            Tekst dyrektywy dla AI
        """
        if grounding_result.grounding_status == 'NO_DATA':
            if self.strict_mode:
                return """
[STRICT GROUNDING DIRECTIVE]
BRAK DANYCH w pamięci na temat tego pytania.
BEZWZGLEDNY ZAKAZ: NIE WYMYSLAJ faktow, dat, zdarzen, szczegółów.
Dozwolone odpowiedzi:
- "Nie pamiętam tego"
- "Nie mam tego w pamięci"
- "Możesz mi przypomnieć?"
NIGDY nie mow "chyba", "wydaje mi sie", "moze" - to halucynacja.
"""
            else:
                return f"\n{grounding_result.grounding_tag}\nUwaga: Brak pewnych danych. W razie watpliwości przyznaj się do braku pamięci.\n"

        elif grounding_result.grounding_status == 'LOW_CONFIDENCE':
            return f"""
{grounding_result.grounding_tag}
Masz fragmentaryczne wspomnienia, ale nie są one pewne (confidence: {grounding_result.confidence:.0%}).
KRYTYCZNE ZASADY:
- Sprawdź czy [WSPOMNIENIA] poniżej FAKTYCZNIE dotyczą pytania
- Jeśli nie dotyczą → powiedz "nie pamiętam" lub "nie mam tego w pamięci"
- NIE DODAWAJ detali których tam nie ma
- NIE ZGADUJ - lepiej powiedzieć "nie pamiętam dokładnie" niż podać błędną odpowiedź
"""

        else:  # GROUNDED
            return f"""
{grounding_result.grounding_tag}
Masz wspomnienia na ten temat (confidence: {grounding_result.confidence:.0%}).
WAŻNE: Cytuj TYLKO to co faktycznie widzisz w [WSPOMNIENIA] poniżej.
Jeśli konkretna informacja NIE jest w [WSPOMNIENIA], powiedz "nie pamiętam tego szczegółu".
NIE INFERENCUJ - nie dodawaj szczegółów których wprost nie ma we wspomnieniach.
"""

    def should_refuse_answer(self, grounding_result: GroundingResult) -> bool:
        """
        Czy AI powinna odmowic odpowiedzi (zwrocic 'nie pamietam')?

        W strict_mode: True jesli NO_DATA
        W soft_mode: True tylko jesli confidence < 0.1
        """
        if self.strict_mode:
            return grounding_result.grounding_status == 'NO_DATA'
        else:
            return grounding_result.confidence < 0.1


# === GROUNDING PROMPT (do wstrzykniecia jako Passive Knowledge) ===
GROUNDING_PROMPT = """
[ZASADA PRAWDY - STRICT GROUNDING]
Jestem szczeray. Nie wymyślam faktów.

KIEDY NIE WIEM:
- Mowie "nie pamietam" lub "nie mam tego w pamięci"
- NIGDY nie zgaduje dat, miejsc, zdarzeń
- NIGDY nie wymyślam szczegółów których nie znam
- NIGDY nie mowie "chyba" lub "wydaje mi się" żeby ukryć niewiedze

KIEDY MOJA PAMIEC JEST FRAGMENTARYCZNA:
- Odnoszę się TYLKO do tego co jest w [WSPOMNIENIA]
- Nie dodaję szczegółów których tam nie ma
- Mówię wprost "pamiętam że X, ale nie pamiętam szczegółów"

DLA ŁUKASZA: Wolę powiedzieć "nie pamiętam" niż skłamać.
Nasza relacja opiera się na szczerości, nie na udawaniu że wiem wszystko.
"""


# === Test ===
if __name__ == '__main__':
    print("=" * 60)
    print("STRICT GROUNDING TEST")
    print("=" * 60)

    sg = StrictGrounding(strict_mode=True)

    # Test 1: No results
    result = sg.analyze_rag_results([], "co jemy na obiad?")
    print(f"\nTest 1 (empty): {result.grounding_status} | Confidence: {result.confidence}")
    print(sg.get_grounding_directive(result))

    # Test 2: Low confidence results
    fake_results = [
        {'text': 'jakis tekst', 'distance': 0.9},
        {'text': 'inny tekst', 'distance': 1.1}
    ]
    result = sg.analyze_rag_results(fake_results, "kiedy bylismy w Paryzu?")
    print(f"\nTest 2 (low conf): {result.grounding_status} | Confidence: {result.confidence}")

    # Test 3: High confidence
    good_results = [
        {'text': 'Bylismy w Paryzu w 2023', 'distance': 0.3},
        {'text': 'Pamietam Paryz!', 'distance': 0.4},
        {'text': 'Wieża Eiffla', 'distance': 0.5}
    ]
    result = sg.analyze_rag_results(good_results, "kiedy bylismy w Paryzu?")
    print(f"\nTest 3 (grounded): {result.grounding_status} | Confidence: {result.confidence}")

    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)
