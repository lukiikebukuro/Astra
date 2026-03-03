"""
ASTRA - Token-Aware Retrieval Manager
Inteligentne zarzadzanie tokenami z rozpoznawaniem gestosci semantycznej.

Typy tresci i strategie:
- CODE: Zachowaj wszystko lub nic (atomic) - kazdy znak ma znaczenie
- INSTRUCTION: Zachowaj rdzen, mozna skrocic przyklady
- FACT: Zachowaj fakt, mozna usunac kontekst
- EMOTIONAL: Mozna skrocic, usunac przymiotniki/powtorzenia
- GENERAL: Standardowe przycinanie od konca
"""

import re
from typing import List, Dict, Tuple

# Token estimation: ~4 chars per token (conservative for Polish)
CHARS_PER_TOKEN = 4


class TokenManager:
    """Manages token budgets with semantic-aware trimming."""

    # Content type identifiers
    CONTENT_TYPES = {
        'CODE': {
            'patterns': [
                r'```',                    # Code blocks
                r'def\s+\w+\s*\(',         # Python functions
                r'function\s+\w+\s*\(',    # JS functions
                r'class\s+\w+',            # Classes
                r'=>',                     # Arrow functions
                r'\{\s*\n',                # Object/block start
                r'import\s+\w+',           # Imports
                r'from\s+\w+\s+import',    # Python imports
                r'const\s+\w+\s*=',        # JS const
                r'let\s+\w+\s*=',          # JS let
            ],
            'trim_strategy': 'atomic',     # All or nothing
            'priority': 10,                # Highest priority (keep)
            'min_density': 1.0,            # Never trim
        },
        'INSTRUCTION': {
            'patterns': [
                r'musisz',                 # Must
                r'nie wolno',              # Not allowed
                r'zawsze',                 # Always
                r'nigdy',                  # Never
                r'pamietaj',               # Remember
                r'wazne:',                 # Important:
                r'uwaga:',                 # Warning:
                r'krok \d+',               # Step N
                r'najpierw',               # First
                r'nastepnie',              # Then
                r'zakaz',                  # Prohibition
            ],
            'trim_strategy': 'preserve_core',
            'priority': 9,
            'min_density': 0.8,
        },
        'FACT': {
            'patterns': [
                r'jest z',                 # Is from
                r'ma \d+',                 # Has N
                r'urodzon',                # Born
                r'mieszka',                # Lives
                r'pracuje',                # Works
                r'lubi\s',                 # Likes
                r'nie lubi',               # Doesn't like
                r'nazywa sie',             # Is called
                r'to jest',                # This is
            ],
            'trim_strategy': 'keep_subject_verb',
            'priority': 7,
            'min_density': 0.6,
        },
        'EMOTIONAL': {
            'patterns': [
                r'kocham',                 # Love
                r'nienawidze',             # Hate
                r'boje sie',               # Fear
                r'martwi',                 # Worry
                r'ciesze sie',             # Happy
                r'smutny',                 # Sad
                r'wsciekly',               # Angry
                r'bardzo',                 # Very (intensifier)
                r'niesamowit',             # Amazing
                r'cudown',                 # Wonderful
            ],
            'trim_strategy': 'remove_intensifiers',
            'priority': 5,
            'min_density': 0.4,
        },
        'GENERAL': {
            'patterns': [],
            'trim_strategy': 'truncate_end',
            'priority': 3,
            'min_density': 0.3,
        }
    }

    # Words that can be removed without losing meaning
    TRIMMABLE_WORDS = {
        'bardzo', 'naprawde', 'absolutnie', 'calkowicie', 'doskonale',
        'wspaniale', 'niesamowicie', 'niezwykle', 'szczegolnie',
        'oczywiscie', 'naturalnie', 'pewnie', 'chyba', 'moze',
        'jakby', 'troche', 'dosc', 'raczej', 'w zasadzie',
        'tak naprawde', 'w sumie', 'generalnie', 'zasadniczo'
    }

    def __init__(self, max_tokens=3000):
        """
        Initialize token manager.

        Args:
            max_tokens: Maximum token budget (default 3000 for ~12000 chars)
        """
        self.max_tokens = max_tokens
        self.max_chars = max_tokens * CHARS_PER_TOKEN

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for text."""
        if not text:
            return 0
        return len(text) // CHARS_PER_TOKEN + 1

    def classify_content(self, text: str) -> Tuple[str, float]:
        """
        Classify content type and calculate semantic density.

        Returns:
            (content_type, density_score)
        """
        text_lower = text.lower()

        for content_type, config in self.CONTENT_TYPES.items():
            if content_type == 'GENERAL':
                continue

            matches = 0
            for pattern in config['patterns']:
                if re.search(pattern, text_lower):
                    matches += 1

            if matches > 0:
                # Density based on matches and text length
                density = min(1.0, config['min_density'] + (matches * 0.1))
                return content_type, density

        return 'GENERAL', 0.3

    def trim_content(self, text: str, target_chars: int) -> str:
        """
        Trim content intelligently based on its type.

        Args:
            text: Original text
            target_chars: Target character count

        Returns:
            Trimmed text
        """
        if len(text) <= target_chars:
            return text

        content_type, density = self.classify_content(text)
        strategy = self.CONTENT_TYPES[content_type]['trim_strategy']

        if strategy == 'atomic':
            # Code: all or nothing
            if len(text) <= target_chars:
                return text
            return f"[CODE TRUNCATED - {self.estimate_tokens(text)} tokens]"

        elif strategy == 'preserve_core':
            # Instructions: keep first sentence, trim examples
            sentences = re.split(r'[.!?]\s+', text)
            result = sentences[0] + '.'
            for s in sentences[1:]:
                if len(result) + len(s) + 2 <= target_chars:
                    result += ' ' + s + '.'
                else:
                    break
            return result

        elif strategy == 'keep_subject_verb':
            # Facts: simplify but keep core
            # Remove parentheticals and extra details
            simplified = re.sub(r'\([^)]*\)', '', text)
            simplified = re.sub(r',\s*[^,]*,', ',', simplified)
            if len(simplified) <= target_chars:
                return simplified.strip()
            return simplified[:target_chars-3].strip() + '...'

        elif strategy == 'remove_intensifiers':
            # Emotional: remove fluff words
            result = text
            for word in self.TRIMMABLE_WORDS:
                result = re.sub(rf'\b{word}\b\s*', '', result, flags=re.IGNORECASE)
            result = re.sub(r'\s+', ' ', result).strip()
            if len(result) <= target_chars:
                return result
            return result[:target_chars-3].strip() + '...'

        else:
            # General: truncate from end
            return text[:target_chars-3].strip() + '...'

    def fit_to_budget(self, memories: List[Dict], reserved_chars: int = 0) -> List[Dict]:
        """
        Fit memories into token budget, trimming intelligently.

        Args:
            memories: List of memory dicts with 'text' and 'metadata'
            reserved_chars: Characters reserved for other content (passive knowledge etc)

        Returns:
            List of memories that fit in budget, possibly trimmed
        """
        available_chars = self.max_chars - reserved_chars
        result = []
        used_chars = 0

        # Sort by priority (based on content type and importance)
        scored_memories = []
        for mem in memories:
            content_type, density = self.classify_content(mem['text'])
            type_priority = self.CONTENT_TYPES[content_type]['priority']
            importance = mem.get('metadata', {}).get('importance', 5)
            final_score = mem.get('final_score', 0.5)

            # Combined priority: type priority + importance + reranker score
            priority = (type_priority * 0.4) + (importance * 0.3) + (final_score * 10 * 0.3)

            scored_memories.append({
                **mem,
                '_priority': priority,
                '_content_type': content_type,
                '_density': density
            })

        # Sort by priority descending
        scored_memories.sort(key=lambda x: x['_priority'], reverse=True)

        for mem in scored_memories:
            text = mem['text']
            text_len = len(text)

            if used_chars + text_len <= available_chars:
                # Fits completely
                result.append(mem)
                used_chars += text_len
            elif available_chars - used_chars >= 50:
                # Partial fit - try to trim
                remaining = available_chars - used_chars
                trimmed = self.trim_content(text, remaining)

                if len(trimmed) >= 30:  # Only include if meaningful
                    mem_copy = {**mem, 'text': trimmed, '_trimmed': True}
                    result.append(mem_copy)
                    used_chars += len(trimmed)

                # After trimming one, stop (don't keep trimming everything)
                break
            else:
                # No more space
                break

        return result

    def build_context(self, memories: List[Dict], passive_knowledge: str = '') -> Dict:
        """
        Build final context string with token accounting.

        Args:
            memories: List of memories (already reranked)
            passive_knowledge: Static knowledge to always include

        Returns:
            Dict with 'context', 'token_count', 'breakdown'
        """
        passive_chars = len(passive_knowledge)
        fitted = self.fit_to_budget(memories, reserved_chars=passive_chars)

        # Build context parts
        parts = []
        breakdown = {
            'passive_knowledge': self.estimate_tokens(passive_knowledge),
            'memories': [],
            'total_memories': len(fitted),
            'trimmed_count': 0
        }

        if passive_knowledge:
            parts.append(f"[CORE KNOWLEDGE]\n{passive_knowledge}")

        if fitted:
            parts.append("\n[ACTIVE MEMORIES]")
            for mem in fitted:
                content_type = mem.get('_content_type', 'GENERAL')
                is_trimmed = mem.get('_trimmed', False)
                text = mem['text']

                # Add type hint for very important content
                if content_type in ['CODE', 'INSTRUCTION']:
                    parts.append(f"[{content_type}] {text}")
                else:
                    parts.append(f"- {text}")

                breakdown['memories'].append({
                    'type': content_type,
                    'tokens': self.estimate_tokens(text),
                    'trimmed': is_trimmed
                })

                if is_trimmed:
                    breakdown['trimmed_count'] += 1

        context = '\n'.join(parts)
        total_tokens = self.estimate_tokens(context)

        return {
            'context': context,
            'token_count': total_tokens,
            'char_count': len(context),
            'within_budget': total_tokens <= self.max_tokens,
            'breakdown': breakdown
        }


# === Test ===
if __name__ == '__main__':
    print("=" * 60)
    print("TOKEN MANAGER TEST")
    print("=" * 60)

    tm = TokenManager(max_tokens=500)  # Small budget for testing

    test_texts = [
        "def calculate_score(x, y):\n    return x * 0.5 + y * 0.3",
        "Pamietaj: nigdy nie usuwaj waznych wspomnien bez potwierdzenia!",
        "Lukasz jest z Gorzowa i ma chorobe Crohna.",
        "Bardzo bardzo bardzo kocham te niesamowicie wspaniala pizze!",
        "Zwykly tekst bez specjalnego znaczenia, moze byc przyciety.",
    ]

    print("\nContent Classification:")
    print("-" * 60)
    for text in test_texts:
        ctype, density = tm.classify_content(text)
        print(f"[{ctype:12}] (density={density:.2f}) {text[:50]}...")

    print("\nTrimming Test (target 50 chars):")
    print("-" * 60)
    for text in test_texts:
        trimmed = tm.trim_content(text, 50)
        print(f"Original ({len(text):3}): {text[:60]}...")
        print(f"Trimmed  ({len(trimmed):3}): {trimmed}")
        print()

    print("\nBudget Fitting Test:")
    print("-" * 60)
    memories = [{'text': t, 'metadata': {'importance': 5}} for t in test_texts]
    fitted = tm.fit_to_budget(memories, reserved_chars=100)
    print(f"Input: {len(memories)} memories")
    print(f"Output: {len(fitted)} memories fit in budget")
    for mem in fitted:
        print(f"  [{mem.get('_content_type', '?'):12}] {mem['text'][:40]}...")
