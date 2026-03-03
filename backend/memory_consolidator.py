"""
ANIMA - Memory Consolidator v1.0
Łączy, nadpisuje i archiwizuje wspomnienia zamiast tworzenia duplikatów.

Funkcje:
- MERGE: Łączy podobne wspomnienia (zwiększa mention_count)
- SUPERSEDE: Archiwizuje stare, zapisuje nowe (ten sam topic)
- CREATE: Tworzy nowe wspomnienie

Zapobiega:
- 50x "jestem zmęczony" jako osobne wpisy
- Sprzeczne informacje o tym samym temacie
- Vector store bloat
"""

from typing import Optional, List, Tuple
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class ConsolidationAction(Enum):
    """Typ akcji konsolidacji."""
    CREATE = "create"      # Nowe wspomnienie
    MERGE = "merge"        # Połącz z istniejącym
    SUPERSEDE = "supersede"  # Nadpisz stare


@dataclass
class ConsolidationResult:
    """Wynik konsolidacji wspomnienia."""
    action: ConsolidationAction
    memory: dict  # Wspomnienie do zapisania
    archived_ids: List[int] = None  # ID zarchiwizowanych wspomnień
    merged_with_id: Optional[int] = None  # ID wspomnienia z którym połączono
    reason: str = ""


class MemoryConsolidator:
    """
    Konsoliduje wspomnienia przed zapisem do bazy.
    Wymaga dostępu do vector_store i database.
    """

    # Similarity thresholds
    MERGE_THRESHOLD = 0.85  # Bardzo podobne = merge
    RELATED_THRESHOLD = 0.70  # Powiązane = potential supersede

    def __init__(self, vector_store=None, database=None):
        """
        Inicjalizacja konsolidatora.

        Args:
            vector_store: Instancja VectorMemory
            database: Instancja Database
        """
        self.vector_store = vector_store
        self.database = database

    def consolidate(self, memory: dict, companion_id: str = 'amelia') -> ConsolidationResult:
        """
        Skonsoliduj wspomnienie z istniejącymi.

        Args:
            memory: Wzbogacone wspomnienie (EnrichedMemory jako dict)
            companion_id: ID companion

        Returns:
            ConsolidationResult z akcją do wykonania
        """
        if not self.vector_store:
            # No vector store = just create
            return ConsolidationResult(
                action=ConsolidationAction.CREATE,
                memory=memory,
                reason="No vector store available"
            )

        text = memory.get('text', '')
        supersedes = memory.get('supersedes')

        # 1. Check for superseding (topic-based)
        if supersedes:
            return self._handle_supersede(memory, supersedes, companion_id)

        # 2. Check for merge (similarity-based)
        similar = self._find_similar(text, companion_id, threshold=self.MERGE_THRESHOLD)
        if similar:
            return self._handle_merge(memory, similar[0], companion_id)

        # 3. Create new
        return ConsolidationResult(
            action=ConsolidationAction.CREATE,
            memory=memory,
            reason="No similar memories found"
        )

    def _find_similar(self, text: str, companion_id: str,
                      threshold: float = 0.70, n_results: int = 5) -> List[dict]:
        """
        Znajdź podobne wspomnienia w vector store.

        Returns:
            Lista podobnych wspomnień z distance < (1 - threshold)
        """
        try:
            results = self.vector_store.search(
                query=text,
                companion_filter=companion_id,
                n_results=n_results
            )

            # Filter by similarity (distance is 1 - similarity for cosine)
            similar = []
            for r in results:
                distance = r.get('distance', 1.0)
                similarity = 1.0 - distance
                if similarity >= threshold:
                    r['similarity'] = similarity
                    similar.append(r)

            return similar
        except Exception as e:
            print(f"[CONSOLIDATOR] Search error: {e}")
            return []

    def _handle_supersede(self, memory: dict, topic: str,
                          companion_id: str) -> ConsolidationResult:
        """
        Obsłuż nadpisywanie starego wspomnienia na ten sam temat.
        """
        # Find memories with same topic to archive
        archived_ids = []

        if self.database:
            try:
                # Search by topic tag in existing memories
                # This would require extending database to search by metadata
                # For now, use vector similarity
                similar = self._find_similar(
                    memory['text'],
                    companion_id,
                    threshold=self.RELATED_THRESHOLD
                )

                for old_memory in similar:
                    old_supersedes = old_memory.get('metadata', {}).get('supersedes')
                    if old_supersedes == topic:
                        # Same topic - archive it
                        old_id = old_memory.get('id')
                        if old_id:
                            self._archive_memory(old_id)
                            archived_ids.append(old_id)

            except Exception as e:
                print(f"[CONSOLIDATOR] Supersede error: {e}")

        return ConsolidationResult(
            action=ConsolidationAction.SUPERSEDE,
            memory=memory,
            archived_ids=archived_ids,
            reason=f"Supersedes topic: {topic}"
        )

    def _handle_merge(self, new_memory: dict, existing: dict,
                      companion_id: str) -> ConsolidationResult:
        """
        Obsłuż łączenie z istniejącym wspomnieniem.
        """
        existing_id = existing.get('id')
        similarity = existing.get('similarity', 0)

        # Merge strategy:
        # - Keep higher importance
        # - Increment mention_count
        # - Update last_mentioned timestamp
        # - Keep more recent temporal data

        merged = {
            **existing,
            'importance': max(
                new_memory.get('importance', 5),
                existing.get('metadata', {}).get('importance', 5)
            ),
            'mention_count': existing.get('metadata', {}).get('mention_count', 1) + 1,
            'last_mentioned': datetime.now().isoformat(),
            'merged_texts': existing.get('metadata', {}).get('merged_texts', []) + [new_memory['text'][:100]]
        }

        # Update in database if available
        if self.database and existing_id:
            try:
                self._update_memory_metadata(existing_id, {
                    'mention_count': merged['mention_count'],
                    'importance': merged['importance'],
                    'last_mentioned': merged['last_mentioned']
                })
            except Exception as e:
                print(f"[CONSOLIDATOR] Merge update error: {e}")

        return ConsolidationResult(
            action=ConsolidationAction.MERGE,
            memory=merged,
            merged_with_id=existing_id,
            reason=f"Merged with existing (similarity: {similarity:.2f})"
        )

    def _archive_memory(self, memory_id: int):
        """
        Zarchiwizuj stare wspomnienie (soft delete).
        """
        if not self.database:
            return

        try:
            # Mark as archived in SQLite
            conn = self.database.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE conversations
                SET metadata = json_set(COALESCE(metadata, '{}'), '$.archived', 1),
                    updated_at = ?
                WHERE id = ?
            ''', (datetime.now().isoformat(), memory_id))
            conn.commit()
            conn.close()

            # Mark as inactive in ChromaDB (via metadata update)
            if self.vector_store:
                self.vector_store.update_metadata(
                    memory_id,
                    {'is_active': False, 'archived_at': datetime.now().isoformat()}
                )

            print(f"[CONSOLIDATOR] Archived memory ID: {memory_id}")

        except Exception as e:
            print(f"[CONSOLIDATOR] Archive error: {e}")

    def _update_memory_metadata(self, memory_id: int, updates: dict):
        """
        Zaktualizuj metadane wspomnienia.
        """
        if not self.database:
            return

        try:
            conn = self.database.get_connection()
            cursor = conn.cursor()

            # Build JSON set operations
            json_sets = []
            params = []
            for key, value in updates.items():
                json_sets.append(f"'$.{key}', ?")
                params.append(value if not isinstance(value, (dict, list)) else str(value))

            if json_sets:
                sql = f'''
                    UPDATE conversations
                    SET metadata = json_set(COALESCE(metadata, '{{}}'), {', '.join(json_sets)}),
                        updated_at = ?
                    WHERE id = ?
                '''
                params.extend([datetime.now().isoformat(), memory_id])
                cursor.execute(sql, params)
                conn.commit()

            conn.close()

        except Exception as e:
            print(f"[CONSOLIDATOR] Update metadata error: {e}")

    def get_consolidation_stats(self, companion_id: str = 'amelia') -> dict:
        """
        Pobierz statystyki konsolidacji.
        """
        stats = {
            'total_memories': 0,
            'active_memories': 0,
            'archived_memories': 0,
            'unique_topics': 0,
            'avg_mention_count': 0
        }

        if not self.database:
            return stats

        try:
            conn = self.database.get_connection()
            cursor = conn.cursor()

            # Total
            cursor.execute('SELECT COUNT(*) FROM conversations WHERE companion = ?',
                           (companion_id,))
            stats['total_memories'] = cursor.fetchone()[0]

            # Active (not archived)
            cursor.execute('''
                SELECT COUNT(*) FROM conversations
                WHERE companion = ?
                AND (metadata IS NULL OR json_extract(metadata, '$.archived') IS NULL)
            ''', (companion_id,))
            stats['active_memories'] = cursor.fetchone()[0]

            stats['archived_memories'] = stats['total_memories'] - stats['active_memories']

            conn.close()

        except Exception as e:
            print(f"[CONSOLIDATOR] Stats error: {e}")

        return stats


# === Singleton instance ===
_consolidator_instance: Optional[MemoryConsolidator] = None


def get_consolidator(vector_store=None, database=None) -> MemoryConsolidator:
    """Get or create singleton consolidator instance."""
    global _consolidator_instance
    if _consolidator_instance is None or (vector_store and database):
        _consolidator_instance = MemoryConsolidator(vector_store, database)
    return _consolidator_instance


# === Test ===
if __name__ == '__main__':
    print("=" * 60)
    print("MEMORY CONSOLIDATOR v1.0 TEST")
    print("=" * 60)

    # Test without actual stores (dry run)
    consolidator = MemoryConsolidator()

    test_memories = [
        {
            'text': "Jestem zmęczony po pracy",
            'entity_type': 'EMOTION',
            'subtype': 'tired',
            'importance': 3,
            'supersedes': 'topic:current_energy'
        },
        {
            'text': "Kocham cię bardzo",
            'entity_type': 'MILESTONE',
            'subtype': 'love_declaration',
            'importance': 10,
            'supersedes': None
        },
        {
            'text': "Zapas leku wystarczy do 15 marca",
            'entity_type': 'DATE',
            'subtype': 'inventory_status',
            'importance': 9,
            'supersedes': 'topic:medication_supply'
        }
    ]

    print("\nTest consolidation (dry run - no vector store):")
    print("-" * 60)

    for memory in test_memories:
        result = consolidator.consolidate(memory)
        print(f"\nMemory: {memory['text'][:40]}...")
        print(f"  Action: {result.action.value}")
        print(f"  Reason: {result.reason}")

    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)
