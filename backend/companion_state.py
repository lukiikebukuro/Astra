"""
ASTRA - Companion State (Faza 2: Dynamic State)
Trzyma stan relacji user↔ASTRA: XP, level, mood, active_concerns.
Persystencja: JSON plik na dysku (MVP; Redis gdy multi-user).
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional, List
import json


# ──────────────────────────────────────────────────────────────
# LEVEL SYSTEM
# ──────────────────────────────────────────────────────────────

LEVEL_NAMES = {
    1: "Lodowa Ściana",
    2: "Odwilż",
    3: "Pewność",
    4: "Głębia",
    5: "Synchronizacja",
    6: "Absolutna Więź",
}

LEVEL_THRESHOLDS = {
    1: 0,
    2: 50,      # ~25 rozmów z dobrym engagement
    3: 150,     # ~75 rozmów
    4: 400,     # ~200 rozmów
    5: 1000,    # ~500 rozmów (miesiące)
    6: 2500,    # ~1250 rozmów (pół roku+)
}


# ──────────────────────────────────────────────────────────────
# COMPANION STATE
# ──────────────────────────────────────────────────────────────

@dataclass
class CompanionState:
    """Dynamiczny stan postaci — wstrzykiwany ZAWSZE do system prompt."""

    # ── RELACJA ──
    xp: int = 0
    level: int = 1
    level_name: str = "Lodowa Ściana"
    intimacy_score: float = 0.0     # 0.0 – 1000.0 (ciągła skala)
    trust_score: float = 0.0        # 0.0 – 100.0

    # ── NASTRÓJ ASTRY ──
    current_mood: str = "neutral"   # neutral/curious/irritated/warm/concerned/playful
    mood_intensity: float = 0.5     # 0.0 (ledwo) – 1.0 (intensywnie)
    mood_since: str = ""

    # ── KONTEKST SESJI ──
    last_user_vibe: str = "neutral"
    last_topic: str = ""
    last_event: str = ""
    messages_this_session: int = 0
    total_messages: int = 0

    # ── PAMIĘĆ OPERACYJNA ──
    active_concerns: List[str] = field(default_factory=list)  # max 5, FIFO

    user_name: str = ""
    last_interaction: str = ""

    # ──────────────────────────────────────────────────────────
    # PROMPT BLOCK — wstrzykiwany do system prompt
    # ──────────────────────────────────────────────────────────

    def to_prompt_block(self) -> str:
        """Serializuj stan do bloku wstrzykiwanego w system prompt."""
        concerns = (
            "\n".join(f"  - {c}" for c in self.active_concerns)
            if self.active_concerns
            else "  (brak)"
        )
        # Oblicz czas od ostatniej rozmowy (dla Thought Anchors)
        hours_since = ""
        if self.last_interaction:
            try:
                last = datetime.fromisoformat(self.last_interaction)
                hours = (datetime.utcnow() - last).total_seconds() / 3600
                if hours > 48:
                    hours_since = f"Ostatnia rozmowa: {int(hours/24)} dni temu"
                elif hours > 1:
                    hours_since = f"Ostatnia rozmowa: {int(hours)} godzin temu"
                else:
                    hours_since = "Ostatnia rozmowa: w tej sesji"
            except (ValueError, TypeError):
                hours_since = ""

        return (
            f"[STAN WEWNĘTRZNY ASTRY — DANE TWARDE, NIE INTERPRETACJA]\n"
            f"Level: {self.level} ({self.level_name})\n"
            f"XP: {self.xp} | Intimacy: {self.intimacy_score:.1f} | Trust: {self.trust_score:.1f}\n"
            f"Mój obecny mood: {self.current_mood} (intensywność: {self.mood_intensity:.1f})\n"
            f"Ostatni temat: {self.last_topic or '(brak)'}\n"
            f"Wiadomości w sesji: {self.messages_this_session} | Total: {self.total_messages}\n"
            + (f"{hours_since}\n" if hours_since else "")
            + f"Aktywne sprawy:\n{concerns}\n"
            f"[/STAN]"
        )

    # ──────────────────────────────────────────────────────────
    # STATE UPDATE — wywoływane po każdej wiadomości usera
    # ──────────────────────────────────────────────────────────

    def update_after_message(
        self,
        message: str,
        entities: list,
        thought_updates: dict = None,
    ):
        """
        Aktualizuje stan po wiadomości usera.
        thought_updates: sparsowany JSON z <state_update> inner monologue.
        """
        self.total_messages += 1
        self.messages_this_session += 1

        # XP (deterministyczny, bez random)
        xp_gained = self._calculate_xp(message, entities)
        self.xp += xp_gained

        self._check_level_up()

        # Vibe / topic z encji
        for entity in entities:
            if entity.entity_type == "EMOTION":
                self.last_user_vibe = entity.subtype
                break
        if entities:
            # Najważniejsza encja → temat
            top = entities[0]
            if top.entity_type in ("FACT", "GOAL", "DATE", "MILESTONE"):
                self.last_topic = f"{top.entity_type}:{top.subtype}"

        # Aktualizacje z inner monologue (structured JSON)
        if thought_updates:
            mood_shift = thought_updates.get("mood_shift")
            if mood_shift and mood_shift not in (None, "null"):
                self.current_mood = mood_shift
                self.mood_since = datetime.utcnow().isoformat()

            new_concern = thought_updates.get("new_concern")
            if new_concern and new_concern not in (None, "null"):
                if new_concern not in self.active_concerns:
                    self.active_concerns.append(new_concern)
                self.active_concerns = self.active_concerns[-5:]

            remove_concern = thought_updates.get("remove_concern")
            if remove_concern and remove_concern not in (None, "null"):
                self.active_concerns = [
                    c for c in self.active_concerns if c != remove_concern
                ]

            topic = thought_updates.get("topic")
            if topic and topic not in (None, "null"):
                self.last_topic = topic

            xp_delta = thought_updates.get("xp_delta", 0)
            if isinstance(xp_delta, (int, float)) and xp_delta > 0:
                self.xp += int(xp_delta)
                self._check_level_up()

        self.last_interaction = datetime.utcnow().isoformat()

    # ──────────────────────────────────────────────────────────
    # XP — deterministyczny
    # ──────────────────────────────────────────────────────────

    def _calculate_xp(self, message: str, entities: list) -> int:
        """Deterministyczny XP — żadnego random. Bazuje na jakości interakcji."""
        xp = 0
        words = message.split()

        if len(words) > 3:
            xp += 1
        if len(words) > 20:
            xp += 1
        if len(entities) >= 2:
            xp += 1

        # Returning bonus: wraca po przerwie >6h
        if self.last_interaction:
            try:
                last = datetime.fromisoformat(self.last_interaction)
                gap_hours = (datetime.utcnow() - last).total_seconds() / 3600
                if gap_hours > 6:
                    xp += 1
            except (ValueError, TypeError):
                pass

        return min(xp, 3)

    def _check_level_up(self):
        """Sprawdza i aktualizuje level na podstawie XP."""
        for lvl in range(6, 0, -1):
            if self.xp >= LEVEL_THRESHOLDS[lvl]:
                if self.level != lvl:
                    old = self.level
                    self.level = lvl
                    self.level_name = LEVEL_NAMES[lvl]
                    print(f"[ASTRA] LEVEL UP: {old} -> {self.level} ({self.level_name})")
                break

    # ──────────────────────────────────────────────────────────
    # SERIALIZATION
    # ──────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "CompanionState":
        """Tworzy instancję z dict, ignoruje nieznane klucze."""
        known = {f for f in cls.__dataclass_fields__}
        clean = {k: v for k, v in data.items() if k in known}
        return cls(**clean)


# ──────────────────────────────────────────────────────────────
# STATE MANAGER — JSON persistence
# ──────────────────────────────────────────────────────────────

class StateManager:
    """Zarządza persystencją stanu w pliku JSON."""

    def __init__(self, state_file: str = None):
        if state_file is None:
            state_file = str(Path(__file__).parent / "companion_state.json")
        self.state_file = Path(state_file)
        self._state: Optional[CompanionState] = None

    def load(self) -> CompanionState:
        """Ładuje stan z pliku (lub tworzy nowy)."""
        if self._state is not None:
            return self._state

        if self.state_file.exists():
            try:
                data = json.loads(self.state_file.read_text(encoding="utf-8"))
                self._state = CompanionState.from_dict(data)
                print(
                    f"[STATE] Loaded: Level {self._state.level} "
                    f"({self._state.level_name}), XP={self._state.xp}, "
                    f"mood={self._state.current_mood}"
                )
                return self._state
            except Exception as e:
                print(f"[STATE] Load error: {e} — starting fresh")

        print("[STATE] New companion state created")
        self._state = CompanionState()
        return self._state

    def save(self, state: CompanionState):
        """Zapisuje stan do pliku JSON."""
        self._state = state
        try:
            self.state_file.write_text(
                json.dumps(state.to_dict(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as e:
            print(f"[STATE] Save error: {e}")

    def reset(self):
        """Resetuje stan do fabrycznie nowego."""
        self._state = CompanionState()
        if self.state_file.exists():
            self.state_file.unlink()
        print("[STATE] Reset to fresh state")
