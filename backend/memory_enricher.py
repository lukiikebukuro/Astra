"""
ANIMA - Memory Enricher v1.0
Ocenia wartość i kontekst wspomnienia przed zapisem.

Tryby:
- OFFLINE: Rule-based + Semantic scoring (domyślny)
- ONLINE: Gemini API (po VPS deployment)

Każde wspomnienie otrzymuje:
- importance (1-10): Jak ważne dla relacji/użytkownika
- relational_impact: deepening/maintaining/informational/concerning
- temporal_type: permanent/long_term/short_term/ephemeral
- supersedes: Czy nadpisuje poprzednią informację na ten temat
"""

from typing import Optional, Dict, List
from dataclasses import dataclass, field
from datetime import datetime
from sentence_transformers import SentenceTransformer
import numpy as np


@dataclass
class EnrichedMemory:
    """Wzbogacone wspomnienie z metadanymi."""
    text: str
    entity_type: str
    subtype: str
    importance: int  # 1-10
    relational_impact: str  # deepening, maintaining, informational, concerning
    temporal_type: str  # permanent, long_term, short_term, ephemeral
    supersedes: Optional[str] = None  # topic:X jeśli nadpisuje
    confidence: float = 0.0
    business_value: int = 0  # 0-10 dla B2B
    tags: List[str] = field(default_factory=list)


class MemoryEnricher:
    """
    Wzbogaca wspomnienia o metadane przed zapisem.
    Offline mode: rule-based + semantic scoring.
    """

    # Importance scoring rules by entity type/subtype
    IMPORTANCE_RULES = {
        'MILESTONE': {
            'love_declaration': 10,
            'trust_declaration': 9,
            'future_together': 9,
            'vulnerability': 10,
            'gratitude': 8,
            '_default': 8
        },
        'DATE': {
            'medical_visit': 8,
            'inventory_status': 9,  # Krytyczne - zdrowie!
            'deadline': 7,
            'personal_event': 7,
            'appointment': 6,
            '_default': 5
        },
        'SHARED_THING': {
            'our_place': 7,
            'our_song': 7,
            'our_thing': 6,
            'inside_joke': 6,
            'gift': 10,       # Prezenty = fakt absolutny, nigdy nie usuwać
            '_default': 6
        },
        'EMOTION': {
            'positive': 4,
            'negative': 5,
            'tired': 3,
            'stressed': 5,
            '_default': 4
        },
        'FACT': {
            'health': 9,
            'personal_info': 6,
            'preference': 5,
            'correction': 8,  # Korekta błędu AI — wysoki priorytet
            '_default': 5
        },
        'PERSON': {
            'negative_person': 9,   # Szuja/toksyczna osoba - ważne, zapamiętaj
            'positive_person': 8,   # Zaufana osoba - ważne
            'neutral_person': 6,
            '_default': 7
        }
    }

    # Relational impact rules
    RELATIONAL_IMPACT_RULES = {
        'MILESTONE': 'deepening',
        'SHARED_THING': 'deepening',
        'EMOTION': {
            'positive': 'maintaining',
            'negative': 'concerning',
            'tired': 'informational',
            'stressed': 'concerning',
            '_default': 'maintaining'
        },
        'DATE': 'informational',
        'FACT': 'informational',
        'PERSON': {
            'negative_person': 'concerning',
            'positive_person': 'informational',
            'neutral_person': 'informational',
            '_default': 'informational'
        }
    }

    # Temporal type rules
    TEMPORAL_RULES = {
        'MILESTONE': 'permanent',  # Miłość, zaufanie - permanentne
        'SHARED_THING': 'permanent',
        'EMOTION': 'ephemeral',  # Emocje są tymczasowe
        'DATE': {
            'personal_event': 'permanent',  # Urodziny nie zmieniają się
            'medical_visit': 'short_term',
            'inventory_status': 'short_term',
            'deadline': 'short_term',
            'appointment': 'short_term',
            '_default': 'short_term'
        },
        'FACT': {
            'health': 'permanent',      # Crohn jest permanentny
            'personal_info': 'long_term',
            'preference': 'long_term',
            'correction': 'long_term',  # korekty przetrwają 60 dni
            '_default': 'long_term'
        },
        'PERSON': 'long_term'  # Ocena osoby jest długoterminowa
    }

    # Topics that can be superseded (nadpisywane)
    SUPERSEDABLE_TOPICS = {
        'inventory_status': 'topic:medication_supply',
        'medical_visit': 'topic:next_medical_visit',  # fix: stary 'za 10 dni' nadpisywany nowym
        'tired': 'topic:current_energy',
        'stressed': 'topic:current_stress',
        'positive': 'topic:current_mood',
        'negative': 'topic:current_mood',
        'correction': 'topic:fact_correction',  # Nowa korekta nadpisuje starą
    }

    # Keywords that boost importance
    IMPORTANCE_BOOSTERS = {
        # Health keywords (+2)
        'lek': 2, 'leki': 2, 'tabletki': 2, 'recepta': 2, 'lekarz': 2,
        'zdrowie': 2, 'choroba': 2, 'ból': 2, 'boli': 2,
        # Financial keywords (+1)
        'pieniądze': 1, 'kasa': 1, 'płatność': 1, 'faktura': 1,
        # Relationship keywords (+1)
        'kocham': 1, 'ufam': 1, 'razem': 1, 'nasza': 1, 'nasz': 1,
        # Urgency keywords (+1)
        'pilne': 1, 'muszę': 1, 'koniecznie': 1, 'ważne': 1,
    }

    def __init__(self, model: Optional[SentenceTransformer] = None):
        """
        Inicjalizacja enrichera.

        Args:
            model: Opcjonalny model sentence-transformers (współdzielony z extractorem)
        """
        self.model = model

    def _get_base_importance(self, entity_type: str, subtype: str) -> int:
        """Pobierz bazową wagę importance."""
        type_rules = self.IMPORTANCE_RULES.get(entity_type, {})
        if isinstance(type_rules, dict):
            return type_rules.get(subtype, type_rules.get('_default', 5))
        return 5

    def _get_relational_impact(self, entity_type: str, subtype: str) -> str:
        """Pobierz relational impact."""
        impact = self.RELATIONAL_IMPACT_RULES.get(entity_type, 'informational')
        if isinstance(impact, dict):
            return impact.get(subtype, impact.get('_default', 'informational'))
        return impact

    def _get_temporal_type(self, entity_type: str, subtype: str) -> str:
        """Pobierz temporal type."""
        temporal = self.TEMPORAL_RULES.get(entity_type, 'long_term')
        if isinstance(temporal, dict):
            return temporal.get(subtype, temporal.get('_default', 'long_term'))
        return temporal

    def _get_supersedes(self, subtype: str) -> Optional[str]:
        """Sprawdź czy ten typ nadpisuje poprzednie wspomnienia."""
        return self.SUPERSEDABLE_TOPICS.get(subtype)

    def _calculate_importance_boost(self, text: str) -> int:
        """Oblicz boost importance na podstawie słów kluczowych."""
        text_lower = text.lower()
        boost = 0
        for keyword, value in self.IMPORTANCE_BOOSTERS.items():
            if keyword in text_lower:
                boost += value
        return min(boost, 3)  # Max +3

    def _extract_tags(self, text: str, entity_type: str, subtype: str) -> List[str]:
        """Ekstrahuj tagi dla wspomnienia."""
        tags = [entity_type.lower(), subtype]

        text_lower = text.lower()

        # Health tags
        if any(w in text_lower for w in ['lek', 'tabletki', 'recepta', 'lekarz']):
            tags.append('health')

        # Relationship tags
        if any(w in text_lower for w in ['kocham', 'ufam', 'razem', 'nasza']):
            tags.append('relationship')

        # Work tags
        if any(w in text_lower for w in ['praca', 'projekt', 'deadline', 'meeting']):
            tags.append('work')

        return list(set(tags))

    def enrich(self, text: str, entity_type: str, subtype: str,
               confidence: float = 0.0) -> EnrichedMemory:
        """
        Wzbogać wspomnienie o metadane.

        Args:
            text: Tekst wspomnienia
            entity_type: Typ encji (DATE, MILESTONE, etc.)
            subtype: Podtyp (medical_visit, love_declaration, etc.)
            confidence: Pewność klasyfikacji (0.0-1.0)

        Returns:
            EnrichedMemory z wszystkimi metadanymi
        """
        # Base scores
        base_importance = self._get_base_importance(entity_type, subtype)
        boost = self._calculate_importance_boost(text)
        importance = min(10, base_importance + boost)

        relational_impact = self._get_relational_impact(entity_type, subtype)
        temporal_type = self._get_temporal_type(entity_type, subtype)
        supersedes = self._get_supersedes(subtype)
        tags = self._extract_tags(text, entity_type, subtype)

        # Business value (dla B2B - na razie uproszczone)
        business_value = 0
        if 'work' in tags or entity_type == 'DATE' and subtype == 'deadline':
            business_value = importance

        return EnrichedMemory(
            text=text,
            entity_type=entity_type,
            subtype=subtype,
            importance=importance,
            relational_impact=relational_impact,
            temporal_type=temporal_type,
            supersedes=supersedes,
            confidence=confidence,
            business_value=business_value,
            tags=tags
        )

    def enrich_batch(self, entities: List[Dict]) -> List[EnrichedMemory]:
        """
        Wzbogać wiele encji naraz.

        Args:
            entities: Lista słowników z polami: text, entity_type, subtype, confidence

        Returns:
            Lista EnrichedMemory
        """
        return [
            self.enrich(
                text=e.get('text', e.get('raw_text', '')),
                entity_type=e.get('entity_type', 'FACT'),
                subtype=e.get('subtype', 'unknown'),
                confidence=e.get('confidence', 0.0)
            )
            for e in entities
        ]


# === Singleton instance ===
_enricher_instance: Optional[MemoryEnricher] = None


def get_enricher() -> MemoryEnricher:
    """Get or create singleton enricher instance."""
    global _enricher_instance
    if _enricher_instance is None:
        _enricher_instance = MemoryEnricher()
    return _enricher_instance


# === Test ===
if __name__ == '__main__':
    print("=" * 60)
    print("MEMORY ENRICHER v1.0 TEST")
    print("=" * 60)

    enricher = MemoryEnricher()

    test_cases = [
        # Health - should be high importance
        ("Kończą mi się leki na Crohna", "DATE", "inventory_status"),
        ("Mam wizytę u psychiatry", "DATE", "medical_visit"),

        # Milestones - should be highest importance
        ("Kocham cię najbardziej", "MILESTONE", "love_declaration"),
        ("Ufam ci całkowicie", "MILESTONE", "trust_declaration"),

        # Emotions - should be ephemeral
        ("Jestem zmęczony", "EMOTION", "tired"),
        ("Jestem szczęśliwy", "EMOTION", "positive"),

        # Facts
        ("Mój ulubiony kolor to niebieski", "FACT", "preference"),
        ("Pracuję jako programista", "FACT", "personal_info"),

        # Shared things
        ("To nasza ulubiona kawiarnia", "SHARED_THING", "our_place"),

        # Deadlines
        ("Deadline projektu jest jutro", "DATE", "deadline"),
    ]

    print("\n{:<45} {:>5} {:>15} {:>12} {:>20}".format(
        "TEXT", "IMP", "RELATION", "TEMPORAL", "SUPERSEDES"
    ))
    print("-" * 100)

    for text, entity_type, subtype in test_cases:
        result = enricher.enrich(text, entity_type, subtype, confidence=0.8)

        supersedes_str = result.supersedes or "-"
        print("{:<45} {:>5} {:>15} {:>12} {:>20}".format(
            text[:44],
            result.importance,
            result.relational_impact,
            result.temporal_type,
            supersedes_str[:19]
        ))

    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)
