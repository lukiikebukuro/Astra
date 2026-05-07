"""
ASTRA — CrossTalk
Prosty mechanizm flagowy dla komunikacji między pokojami.

Gdy jedna postać wykryje mocny sygnał emocjonalny (smutek, ból, euforia),
zapisuje flagę do pliku. Druga postać przy następnej odpowiedzi widzi flagę
i może się do niej subtelnie odnieść. Flaga wygasa po 2h.

Plik: backend/cross_talk_flag.json
"""

import json
import os
from datetime import datetime, timedelta


CROSS_TALK_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cross_talk_flag.json')
EXPIRY_SECONDS = 7200  # 2 godziny

# Emocje które generują flagę + minimalny próg ważności
STRONG_SIGNALS = {
    'sad', 'grief', 'alone', 'cry',
    'pain', 'stressed', 'anguish', 'fear',
    'euphoria', 'excited', 'love', 'joy',
}
IMPORTANCE_THRESHOLD = 6  # importance >= 6 → flaga nawet dla niestandardowych emocji


def set_flag(source: str, signal: str, context: str):
    """
    Zapisuje flagę cross-talk.
    source: 'astra' | 'amelia'
    signal: nazwa emocji/sygnału
    context: fragment wiadomości triggera (max 200 znaków)
    """
    data = {
        'source': source,
        'signal': signal,
        'context': context[:200],
        'timestamp': datetime.utcnow().isoformat(),
    }
    try:
        with open(CROSS_TALK_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)
        print(f"[CrossTalk] Flaga ustawiona: {source} → {signal}")
    except Exception as e:
        print(f"[CrossTalk] Błąd zapisu flagi: {e}")


def get_flag(consumer: str) -> dict | None:
    """
    Odczytuje flagę jeśli jest ustawiona przez INNĄ postać (nie consumer).
    Zwraca dict lub None. Nie kasuje — użyj clear_flag() po użyciu.
    """
    if not os.path.exists(CROSS_TALK_FILE):
        return None
    try:
        with open(CROSS_TALK_FILE, encoding='utf-8') as f:
            data = json.load(f)
        # Wygaśnięcie
        ts = datetime.fromisoformat(data['timestamp'])
        if (datetime.utcnow() - ts).total_seconds() > EXPIRY_SECONDS:
            clear_flag()
            return None
        # Tylko jeśli flaga jest od INNEJ postaci
        if data.get('source') == consumer:
            return None
        return data
    except Exception as e:
        print(f"[CrossTalk] Błąd odczytu flagi: {e}")
        return None


def clear_flag():
    """Usuwa flagę po jej wykorzystaniu."""
    try:
        if os.path.exists(CROSS_TALK_FILE):
            os.remove(CROSS_TALK_FILE)
            print("[CrossTalk] Flaga wyczyszczona")
    except Exception as e:
        print(f"[CrossTalk] Błąd usuwania flagi: {e}")


def detect_strong_signal(entities: list, user_text: str = '') -> tuple[str, str] | None:
    """
    Sprawdza czy extracted entities zawierają mocny sygnał emocjonalny.
    Zwraca (signal_name, context) lub None.
    entities: lista obiektów z .entity_type, .subtype, .importance, .text
    """
    for mem in entities:
        if mem.entity_type != 'EMOTION':
            continue
        is_strong_type = mem.subtype.lower() in STRONG_SIGNALS
        is_strong_importance = mem.importance >= IMPORTANCE_THRESHOLD
        if is_strong_type or is_strong_importance:
            return mem.subtype, mem.text[:200]
    return None


def build_cross_talk_block(flag: dict) -> str:
    """
    Buduje blok tekstowy do wstrzyknięcia w system prompt drugiej postaci.
    """
    source_name = 'Astra' if flag['source'] == 'astra' else 'Amelia'
    return (
        f"\n\n[CROSS_TALK — sygnał od {source_name}]\n"
        f"{source_name} wykryła u Łukasza: {flag['signal']}.\n"
        f"Kontekst: \"{flag['context']}\"\n"
        f"Możesz się do tego subtelnie odnieść — nie musisz, ale możesz. "
        f"Nie wyjaśniaj skąd wiesz — po prostu czuj."
    )
