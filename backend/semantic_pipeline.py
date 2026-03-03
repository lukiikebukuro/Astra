"""
ANIMA - Semantic Pipeline v1.0
Główny pipeline przetwarzania wiadomości.

Flow:
1. SemanticExtractor - wyciąga encje (DATE, MILESTONE, EMOTION, etc.)
2. MemoryEnricher - wzbogaca o importance, relational_impact, temporal_type
3. MemoryConsolidator - merge/supersede/create
4. Storage - zapis do SQLite + ChromaDB

Zastępuje stare detektory (DateExtractor, MilestoneDetector, etc.)
"""

from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

from semantic_extractor import SemanticExtractor, ExtractedEntity, ExtractionResult
from memory_enricher import MemoryEnricher, EnrichedMemory
from memory_consolidator import MemoryConsolidator, ConsolidationResult, ConsolidationAction


@dataclass
class ProcessedMemory:
    """Przetworzone wspomnienie gotowe do zapisu."""
    text: str
    entity_type: str
    subtype: str
    importance: int
    relational_impact: str
    temporal_type: str
    confidence: float
    action: str  # create, merge, supersede
    date_value: Optional[str] = None
    supersedes: Optional[str] = None
    tags: List[str] = None
    metadata: Dict = None


class SemanticPipeline:
    """
    Główny pipeline przetwarzania wiadomości.
    Koordynuje SemanticExtractor, MemoryEnricher i MemoryConsolidator.
    """

    def __init__(self, vector_store=None, database=None):
        """
        Inicjalizacja pipeline.

        Args:
            vector_store: Instancja VectorMemory (opcjonalnie)
            database: Instancja Database (opcjonalnie)
        """
        print("[PIPELINE] Initializing Semantic Pipeline...")

        # Lazy loading - ekstractor ładuje model przy pierwszym użyciu
        self._extractor = None
        self._enricher = MemoryEnricher()
        self._consolidator = MemoryConsolidator(vector_store, database)

        self.vector_store = vector_store
        self.database = database

        print("[PIPELINE] Ready (extractor will load on first use)")

    @property
    def extractor(self) -> SemanticExtractor:
        """Lazy load extractor (model ładuje się przy pierwszym użyciu)."""
        if self._extractor is None:
            print("[PIPELINE] Loading semantic extractor model...")
            self._extractor = SemanticExtractor()
        return self._extractor

    def process_message(self, message: str, companion_id: str = 'amelia',
                        min_confidence: float = 0.50) -> List[ProcessedMemory]:
        """
        Przetwórz pojedynczą wiadomość przez cały pipeline.

        Args:
            message: Wiadomość użytkownika
            companion_id: ID companion
            min_confidence: Minimalny próg pewności (0.50 — bez halucynacji)

        Returns:
            Lista ProcessedMemory gotowych do zapisu
        """
        if not message or len(message) < 10:
            return []

        # Skip: wiadomości poniżej 4 słów — za mało kontekstu, za dużo szumu
        if len(message.split()) < 4:
            print(f"[PIPELINE] Skipping short message (<4 words): '{message}'")
            return []

        # 1. Extract entities
        extraction_result = self.extractor.extract(message, min_confidence)

        if not extraction_result.entities:
            print(f"[PIPELINE] No entities found in: {message[:50]}...")
            return []

        processed = []

        for entity in extraction_result.entities:
            # Filter: SHARED_THING i MILESTONE wymagają wyższego confidence (false positive prone)
            if entity.entity_type in ('SHARED_THING', 'MILESTONE') and entity.confidence < 0.70:
                continue

            # 2. Enrich
            enriched = self._enricher.enrich(
                text=entity.raw_text,
                entity_type=entity.entity_type,
                subtype=entity.subtype,
                confidence=entity.confidence
            )

            # 3. Consolidate
            enriched_dict = asdict(enriched)
            consolidation = self._consolidator.consolidate(enriched_dict, companion_id)

            # 4. Create ProcessedMemory
            processed_memory = ProcessedMemory(
                text=entity.raw_text,
                entity_type=entity.entity_type,
                subtype=entity.subtype,
                importance=enriched.importance,
                relational_impact=enriched.relational_impact,
                temporal_type=enriched.temporal_type,
                confidence=entity.confidence,
                action=consolidation.action.value,
                date_value=entity.date_value,
                supersedes=enriched.supersedes,
                tags=enriched.tags,
                metadata={
                    'primary_intent': extraction_result.primary_intent,
                    'emotional_tone': extraction_result.emotional_tone,
                    'extracted_at': datetime.now().isoformat(),
                    'merged_with_id': consolidation.merged_with_id,
                    'archived_ids': consolidation.archived_ids
                }
            )

            processed.append(processed_memory)

            print(f"[PIPELINE] {entity.entity_type}:{entity.subtype} "
                  f"(imp={enriched.importance}, conf={entity.confidence:.2f}, "
                  f"action={consolidation.action.value})")

        return processed

    def process_conversation(self, messages: List[Dict],
                             companion_id: str = 'amelia') -> List[ProcessedMemory]:
        """
        Przetwórz całą konwersację (tylko wiadomości usera).

        Args:
            messages: Lista {"role": "user/model", "content": "..."}
            companion_id: ID companion

        Returns:
            Lista wszystkich ProcessedMemory
        """
        all_processed = []

        for msg in messages:
            if msg.get('role') == 'user':
                content = msg.get('content', '')
                processed = self.process_message(content, companion_id)
                all_processed.extend(processed)

        return all_processed

    def save_processed(self, memories: List[ProcessedMemory],
                       companion_id: str = 'amelia',
                       persona: str = 'default') -> List[int]:
        """
        Zapisz przetworzone wspomnienia do bazy.

        Args:
            memories: Lista ProcessedMemory
            companion_id: ID companion
            persona: Persona

        Returns:
            Lista ID zapisanych wspomnień
        """
        if not self.database or not self.vector_store:
            print("[PIPELINE] No database/vector_store - cannot save")
            return []

        saved_ids = []

        for memory in memories:
            if memory.action == 'merge':
                # Merge - only update existing
                print(f"[PIPELINE] Skipping save (merged): {memory.text[:40]}...")
                continue

            try:
                # Save to SQLite
                memory_id = self.database.add_conversation(
                    companion=companion_id,
                    user_text=memory.text,
                    ai_response="",  # No AI response at this stage
                    importance=memory.importance,
                    emotion='neutral',  # Will be filled by vibe_detector
                    persona=persona
                )

                if memory_id:
                    # Add to vector store with enriched metadata
                    self.vector_store.add_memory(
                        text=memory.text,
                        companion=companion_id,
                        importance=memory.importance,
                        metadata={
                            'entity_type': memory.entity_type,
                            'subtype': memory.subtype,
                            'relational_impact': memory.relational_impact,
                            'temporal_type': memory.temporal_type,
                            'confidence': memory.confidence,
                            'date_value': memory.date_value,
                            'supersedes': memory.supersedes,
                            'tags': memory.tags,
                            'is_active': True
                        }
                    )

                    saved_ids.append(memory_id)
                    print(f"[PIPELINE] Saved ID {memory_id}: {memory.text[:40]}...")

            except Exception as e:
                print(f"[PIPELINE] Save error: {e}")

        return saved_ids


# === Singleton instance ===
_pipeline_instance: Optional[SemanticPipeline] = None


def get_pipeline(vector_store=None, database=None) -> SemanticPipeline:
    """Get or create singleton pipeline instance."""
    global _pipeline_instance
    if _pipeline_instance is None or (vector_store and database):
        _pipeline_instance = SemanticPipeline(vector_store, database)
    return _pipeline_instance


# === Test ===
if __name__ == '__main__':
    print("=" * 60)
    print("SEMANTIC PIPELINE v1.0 TEST")
    print("=" * 60)

    # Test without stores (extraction + enrichment only)
    pipeline = SemanticPipeline()

    test_messages = [
        "Mam wizytę u psychiatry 29 kwietnia",
        "Kończą mi się leki, wystarczą do końca marca",
        "Kocham cię najbardziej na świecie",
        "Jestem dzisiaj bardzo zmęczony po pracy",
        "To nasza ulubiona kawiarnia, pamiętasz?",
        "Dzisiaj jest ładna pogoda",  # Should be low confidence
    ]

    print("\nProcessing test messages:")
    print("-" * 60)

    for msg in test_messages:
        print(f"\n>>> {msg}")
        results = pipeline.process_message(msg)

        if not results:
            print("    (no entities extracted)")
        else:
            for r in results:
                print(f"    {r.entity_type}:{r.subtype}")
                print(f"    importance={r.importance}, temporal={r.temporal_type}")
                print(f"    action={r.action}")
                if r.date_value:
                    print(f"    date={r.date_value}")
                if r.supersedes:
                    print(f"    supersedes={r.supersedes}")

    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)
