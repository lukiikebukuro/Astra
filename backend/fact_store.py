"""
ASTRA - FactStore (SQLite)
Warstwa exact lookup dla ustrukturyzowanych faktów.

Uzupełnia ChromaDB (semantic similarity) o deterministyczne wyszukiwanie:
- ChromaDB: "coś o wątrobie" → semantycznie bliskie wektory
- FactStore: "FACT:health" → SELECT → zawsze właściwy fakt, zawsze aktualny

Tabela facts:
  id            TEXT PRIMARY KEY  (SHA256 entity_type:subtype:persona_id:user_id)
  persona_id    TEXT
  user_id_hash  TEXT              (SHA256 salt:user_id — nigdy plain text)
  entity_type   TEXT              (FACT, DATE, PERSON, EMOTION, MILESTONE)
  subtype       TEXT              (health, preference, medical_visit, name, ...)
  value         TEXT              (wyekstrahowana wartość / tekst)
  date_value    TEXT              (YYYY-MM-DD jeśli dotyczy)
  raw_text      TEXT              (oryginalne zdanie z rozmowy)
  importance    INTEGER
  timestamp     TEXT              (ISO8601 UTC)
"""

import sqlite3
import hashlib
import os
from datetime import datetime
from typing import Optional


# Typy encji które trafiają do FactStore (exact lookup ma sens)
FACT_STORE_TYPES = {
    ('FACT',      'health'),
    ('FACT',      'preference'),
    ('FACT',      'correction'),
    ('FACT',      'habit'),
    ('FACT',      'amelia_status'),
    ('DATE',      'medical_visit'),
    ('DATE',      'inventory_status'),
    ('DATE',      'appointment'),
    ('PERSON',    'name'),
    ('PERSON',    'relationship'),
    ('MILESTONE', 'love_declaration'),
    ('MILESTONE', 'trust_declaration'),
    ('MILESTONE', 'future_together'),
}

# Typy które ZASTĘPUJĄ poprzedni rekord (supersede) — jeden aktywny wpis
SUPERSEDE_IN_STORE = {
    ('FACT',   'health'),
    ('FACT',   'preference'),
    ('FACT',   'correction'),
    ('FACT',   'amelia_status'),
    ('DATE',   'medical_visit'),
    ('DATE',   'inventory_status'),
    ('DATE',   'appointment'),
}


def _make_fact_id(entity_type: str, subtype: str, persona_id: str, user_id_hash: str) -> str:
    """Deterministyczne ID — ten sam typ encji per user = ten sam slot (supersede)."""
    return hashlib.sha256(
        f"{entity_type}:{subtype}:{persona_id}:{user_id_hash}".encode()
    ).hexdigest()[:32]


def _hash_user(salt: str, user_id: str) -> str:
    return hashlib.sha256(f"{salt}:{user_id}".encode()).hexdigest()[:16]


class FactStore:
    """
    SQLite exact lookup layer dla ustrukturyzowanych faktów Astry.
    Lightweight, zero zależności poza stdlib.
    """

    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                'astra_facts.db'
            )
        self.db_path = db_path
        self._init_db()
        print(f"[FactStore] Initialized at {self.db_path}")

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")  # B7: bezpieczny rownolegly odczyt (inspect) + zapis (chat)
        return conn

    def _init_db(self):
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS facts (
                    id            TEXT PRIMARY KEY,
                    persona_id    TEXT NOT NULL,
                    user_id_hash  TEXT NOT NULL,
                    entity_type   TEXT NOT NULL,
                    subtype       TEXT NOT NULL,
                    value         TEXT NOT NULL,
                    date_value    TEXT,
                    raw_text      TEXT,
                    importance    INTEGER DEFAULT 5,
                    timestamp     TEXT NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_facts_lookup ON facts(persona_id, user_id_hash, entity_type, subtype)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_facts_type ON facts(entity_type, subtype)")

    # ──────────────────────────────────────────────────────────────
    # WRITE
    # ──────────────────────────────────────────────────────────────

    def upsert(self, persona_id: str, user_id: str, salt: str,
               entity_type: str, subtype: str,
               value: str, raw_text: str = "",
               date_value: str = None, importance: int = 5) -> bool:
        """
        Zapisuje fakt do FactStore.
        Dla typów w SUPERSEDE_IN_STORE — jeden aktywny rekord per user per typ.
        Dla milestones — akumuluje (każdy milestone osobny rekord z pełnym ID).
        Zwraca True jeśli zapisano.
        """
        key = (entity_type, subtype)
        if key not in FACT_STORE_TYPES:
            return False

        uid_hash = _hash_user(salt, user_id)

        if key in SUPERSEDE_IN_STORE:
            # Deterministyczne ID — upsert nadpisuje poprzedni rekord
            fact_id = _make_fact_id(entity_type, subtype, persona_id, uid_hash)
        else:
            # Milestony i inne akumulujące — unikalny ID per wpis
            fact_id = hashlib.sha256(
                f"{entity_type}:{subtype}:{persona_id}:{uid_hash}:{value}".encode()
            ).hexdigest()[:32]

        ts = datetime.utcnow().isoformat()

        with self._conn() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO facts
                    (id, persona_id, user_id_hash, entity_type, subtype, value, date_value, raw_text, importance, timestamp)
                VALUES
                    (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (fact_id, persona_id, uid_hash, entity_type, subtype,
                  value, date_value, raw_text, importance, ts))

        print(f"[FactStore] Upsert {entity_type}:{subtype} = '{value[:60]}'")
        return True

    # ──────────────────────────────────────────────────────────────
    # READ
    # ──────────────────────────────────────────────────────────────

    def get_facts_for_prompt(self, persona_id: str, user_id: str, salt: str) -> list[dict]:
        """
        Zwraca wszystkie aktywne fakty dla danego użytkownika.
        Posortowane: health/date/milestone najpierw.
        Używane do budowania bloku [TWARDE FAKTY] w system prompcie.
        """
        uid_hash = _hash_user(salt, user_id)
        with self._conn() as conn:
            rows = conn.execute("""
                SELECT entity_type, subtype, value, date_value, raw_text, importance, timestamp
                FROM facts
                WHERE persona_id = ? AND user_id_hash = ?
                ORDER BY
                    CASE entity_type
                        WHEN 'MILESTONE' THEN 1
                        WHEN 'FACT'      THEN 2
                        WHEN 'DATE'      THEN 3
                        WHEN 'PERSON'    THEN 4
                        ELSE 5
                    END,
                    importance DESC,
                    timestamp DESC
            """, (persona_id, uid_hash)).fetchall()
        return [dict(r) for r in rows]

    def get_by_type(self, persona_id: str, user_id: str, salt: str,
                    entity_type: str, subtype: str = None) -> list[dict]:
        """
        Exact lookup po typie encji.
        Np. get_by_type('astra', ..., 'FACT', 'health') → lista faktów zdrowotnych.
        """
        uid_hash = _hash_user(salt, user_id)
        with self._conn() as conn:
            if subtype:
                rows = conn.execute("""
                    SELECT * FROM facts
                    WHERE persona_id=? AND user_id_hash=? AND entity_type=? AND subtype=?
                    ORDER BY timestamp DESC
                """, (persona_id, uid_hash, entity_type, subtype)).fetchall()
            else:
                rows = conn.execute("""
                    SELECT * FROM facts
                    WHERE persona_id=? AND user_id_hash=? AND entity_type=?
                    ORDER BY timestamp DESC
                """, (persona_id, uid_hash, entity_type)).fetchall()
        return [dict(r) for r in rows]

    def get_stats(self, persona_id: str, user_id: str, salt: str) -> dict:
        uid_hash = _hash_user(salt, user_id)
        with self._conn() as conn:
            total = conn.execute(
                "SELECT COUNT(*) FROM facts WHERE persona_id=? AND user_id_hash=?",
                (persona_id, uid_hash)
            ).fetchone()[0]
            by_type = conn.execute("""
                SELECT entity_type, subtype, COUNT(*) as cnt
                FROM facts WHERE persona_id=? AND user_id_hash=?
                GROUP BY entity_type, subtype
            """, (persona_id, uid_hash)).fetchall()
        return {
            'total': total,
            'by_type': [dict(r) for r in by_type],
        }
