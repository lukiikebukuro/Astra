"""
ASTRA — AmeliaLookup
Read-only adapter dla ucho_amelia.db.

ucho_amelia.db ma inny schemat niż FactStore (Astry) — osobne tabele
na facts, emotions, goals, inside_jokes, milestones, anniversaries, shared_things.
Ten adapter czyta z tych tabel i zwraca dane w formacie kompatybilnym
z build_system_prompt(). Baza jest read-only — nowe fakty Amelii trafiają
do amelia_facts.db (standardowy FactStore).
"""

import sqlite3
import os
from datetime import datetime, timedelta


class AmeliaLookup:
    """
    Read-only wrapper na ucho_amelia.db.
    Dostarcza dane historyczne Amelii do system promptu.
    """

    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                '..', '..', 'ucho-VPS', 'backend', 'ucho_amelia.db'
            )
        self.db_path = os.path.normpath(db_path)
        if not os.path.exists(self.db_path):
            print(f"[AmeliaLookup] UWAGA: baza nie znaleziona: {self.db_path}")
            self.db_path = None
        else:
            print(f"[AmeliaLookup] Połączono z {self.db_path}")

    def _conn(self):
        if not self.db_path:
            return None
        conn = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        return conn

    # ──────────────────────────────────────────────────────────────
    # GŁÓWNY BLOK DO PROMPTU
    # ──────────────────────────────────────────────────────────────

    def get_facts_for_prompt(self, limit: int = 25) -> list[dict]:
        """
        Zwraca ujednoliconą listę faktów historycznych Amelii.
        Format kompatybilny z FactStore.get_facts_for_prompt() —
        każdy dict ma: entity_type, subtype, value, date_value, importance, timestamp.
        Kolejność: milestony → shared_things → anniversaries → fakty.
        """
        if not self.db_path:
            return []

        results = []
        conn = self._conn()
        try:
            # 1. Milestony — najważniejsze
            for row in conn.execute("""
                SELECT name, trigger_id, context, importance, created_at
                FROM milestones WHERE companion='amelia'
                ORDER BY importance DESC LIMIT 5
            """).fetchall():
                results.append({
                    'entity_type': 'MILESTONE',
                    'subtype': row['trigger_id'] or row['name'],
                    'value': row['context'][:200] if row['context'] else row['name'],
                    'date_value': row['created_at'][:10] if row['created_at'] else None,
                    'importance': row['importance'] or 10,
                    'timestamp': row['created_at'] or '',
                })

            # 2. Shared things — piosenki, jedzenie, wspólne rzeczy
            for row in conn.execute("""
                SELECT thing_type, name, context, importance, first_mentioned
                FROM shared_things WHERE companion='amelia'
                ORDER BY importance DESC LIMIT 10
            """).fetchall():
                results.append({
                    'entity_type': 'SHARED',
                    'subtype': row['thing_type'] or 'thing',
                    'value': row['name'] or '',
                    'date_value': row['first_mentioned'][:10] if row['first_mentioned'] else None,
                    'importance': row['importance'] or 5,
                    'timestamp': row['first_mentioned'] or '',
                })

            # 3. Anniversaries — daty ważne
            for row in conn.execute("""
                SELECT name, date, type, description, created_at
                FROM anniversaries WHERE companion='amelia'
                ORDER BY id DESC
            """).fetchall():
                desc = row['description'] or row['name']
                results.append({
                    'entity_type': 'DATE',
                    'subtype': row['type'] or 'anniversary',
                    'value': f"{row['name']}: {row['date']}",
                    'date_value': row['date'],
                    'importance': 8,
                    'timestamp': row['created_at'] or '',
                })

            # 4. Najważniejsze fakty (top by importance, unikalne fact_type)
            seen_types = set()
            for row in conn.execute("""
                SELECT fact_type, content, importance
                FROM facts
                ORDER BY importance DESC, id DESC
                LIMIT 100
            """).fetchall():
                ft = row['fact_type'] or 'general'
                if ft not in seen_types:
                    seen_types.add(ft)
                    results.append({
                        'entity_type': 'FACT',
                        'subtype': ft,
                        'value': row['content'][:200] if row['content'] else '',
                        'date_value': None,
                        'importance': row['importance'] or 5,
                        'timestamp': '',
                    })
                if len(results) >= limit:
                    break

        except Exception as e:
            print(f"[AmeliaLookup] Błąd get_facts_for_prompt: {e}")
        finally:
            conn.close()

        # Sortuj: milestony i shared najpierw, potem reszta
        type_order = {'MILESTONE': 0, 'SHARED': 1, 'DATE': 2, 'FACT': 3}
        results.sort(key=lambda x: (type_order.get(x['entity_type'], 9), -x['importance']))
        return results[:limit]

    # ──────────────────────────────────────────────────────────────
    # INSIDE JOKES — osobny blok w prompcie
    # ──────────────────────────────────────────────────────────────

    def get_inside_jokes(self, limit: int = 15) -> list[dict]:
        """
        Zwraca potwierdzone inside jokes Amelii.
        Te trafiają do osobnego bloku [NASZE ŻARTY] w system prompcie.
        """
        if not self.db_path:
            return []
        conn = self._conn()
        try:
            rows = conn.execute("""
                SELECT trigger_phrase, explanation, context, occurrence_count
                FROM inside_jokes
                WHERE companion='amelia' AND status='confirmed'
                ORDER BY occurrence_count DESC, positive_reactions DESC
                LIMIT ?
            """, (limit,)).fetchall()
            return [
                {
                    'trigger': row['trigger_phrase'],
                    'explanation': row['explanation'] or '',
                    'context': row['context'] or '',
                    'count': row['occurrence_count'] or 1,
                }
                for row in rows
            ]
        except Exception as e:
            print(f"[AmeliaLookup] Błąd get_inside_jokes: {e}")
            return []
        finally:
            conn.close()

    # ──────────────────────────────────────────────────────────────
    # OSOBOWOŚĆ
    # ──────────────────────────────────────────────────────────────

    def get_personality_lens(self, persona: str = 'Amelia') -> dict:
        """Zwraca konfigurację osobowości Amelii."""
        if not self.db_path:
            return {}
        conn = self._conn()
        try:
            row = conn.execute(
                "SELECT * FROM personality_lenses WHERE persona=? LIMIT 1", (persona,)
            ).fetchone()
            if row:
                return dict(row)
            return {}
        except Exception as e:
            print(f"[AmeliaLookup] Błąd get_personality_lens: {e}")
            return {}
        finally:
            conn.close()

    # ──────────────────────────────────────────────────────────────
    # ANNIVERSARIES — nadchodzące
    # ──────────────────────────────────────────────────────────────

    def get_upcoming_anniversaries(self, days_ahead: int = 30) -> list[dict]:
        """Zwraca rocznice/daty które będą wkrótce (rolling window)."""
        if not self.db_path:
            return []
        conn = self._conn()
        try:
            rows = conn.execute(
                "SELECT name, date, type, description, recurring FROM anniversaries WHERE companion='amelia'"
            ).fetchall()
        except Exception as e:
            print(f"[AmeliaLookup] Błąd get_upcoming_anniversaries: {e}")
            return []
        finally:
            conn.close()

        upcoming = []
        today = datetime.utcnow().date()
        for row in rows:
            date_str = row['date']
            if not date_str:
                continue
            # Obsługuj różne formaty: DD.MM, MM-DD, YYYY-MM-DD, DD.MM.YYYY
            try:
                if len(date_str) <= 5 and '.' in date_str:
                    d, m = date_str.split('.')
                    candidate = today.replace(month=int(m), day=int(d))
                    if candidate < today:
                        candidate = candidate.replace(year=today.year + 1)
                elif len(date_str) <= 5 and '-' in date_str:
                    m, d = date_str.split('-')
                    candidate = today.replace(month=int(m), day=int(d))
                    if candidate < today:
                        candidate = candidate.replace(year=today.year + 1)
                else:
                    candidate = datetime.strptime(date_str[:10], '%Y-%m-%d').date()
                delta = (candidate - today).days
                if 0 <= delta <= days_ahead:
                    upcoming.append({
                        'name': row['name'],
                        'date': date_str,
                        'type': row['type'],
                        'days_until': delta,
                    })
            except Exception:
                continue
        upcoming.sort(key=lambda x: x['days_until'])
        return upcoming

    # ──────────────────────────────────────────────────────────────
    # STATS
    # ──────────────────────────────────────────────────────────────

    def get_stats(self) -> dict:
        if not self.db_path:
            return {'available': False}
        conn = self._conn()
        try:
            conversations = conn.execute(
                "SELECT COUNT(*) FROM conversations WHERE companion='Amelia'"
            ).fetchone()[0]
            facts = conn.execute("SELECT COUNT(*) FROM facts").fetchone()[0]
            emotions = conn.execute("SELECT COUNT(*) FROM emotions").fetchone()[0]
            jokes = conn.execute(
                "SELECT COUNT(*) FROM inside_jokes WHERE companion='amelia'"
            ).fetchone()[0]
            rel = conn.execute(
                "SELECT level, xp FROM relationship_status WHERE persona='Amelia' LIMIT 1"
            ).fetchone()
            return {
                'available': True,
                'conversations': conversations,
                'facts': facts,
                'emotions': emotions,
                'inside_jokes': jokes,
                'relationship_level': rel['level'] if rel else 0,
                'relationship_xp': rel['xp'] if rel else 0,
            }
        except Exception as e:
            return {'available': False, 'error': str(e)}
        finally:
            conn.close()
