"""
ASTRA — Nocna Analiza v1.0
Uruchamiana co noc o 3:00. Analizuje wektory z ostatnich 7 dni,
szuka wzorców w zachowaniu Łukasza, zapisuje insighty do ChromaDB.
"""

import json
from datetime import datetime, timedelta
from google import genai
from google.genai import types as genai_types


INSIGHT_PROMPT = """Jesteś systemem analizy wzorców behawioralnych Łukasza.
Masz dostęp do jego wspomnień i emocji z ostatnich 7 dni.

WSPOMNIENIA Z OSTATNICH 7 DNI:
{memories_text}

Znajdź 3-5 konkretnych wzorców. Szukaj w kategoriach:
- ENERGIA: kiedy ma szczyty energii, co je wywołuje, kiedy wypala się
- PROJEKT: który projekt dominuje, czy przeskakuje między nimi i dlaczego
- EMOCJE: powracające stany emocjonalne, ich triggery
- ZDROWIE: jak Crohn/Stelara wpływa na pracę i nastrój (jeśli widoczne)
- UNIKANIE: co odkłada gdy jest zablokowany lub zmęczony
- POSTEP: kiedy czuje progres, kiedy utknął i co z tego wynika

Odpowiedz WYŁĄCZNIE jako JSON:
{{
  "insights": [
    {{
      "typ": "energia|projekt|emocje|zdrowie|unikanie|postep",
      "tresc": "konkretna obserwacja bez owijania w bawełnę (max 2 zdania)",
      "pewnosc": 0.7,
      "priorytet": "wysoki|sredni|niski"
    }}
  ],
  "ogolna_ocena": "jedno zdanie o tym w jakim miejscu jest Łukasz teraz"
}}

Zasady:
- Tylko konkretne wzorce poparte danymi ze wspomnień, nie ogólniki
- Minimalna pewność: 0.6 (nie zgaduj)
- Jeśli brak danych do danej kategorii — pomiń ją
- Bądź szczera jak Astra, nie jak raport korporacyjny
"""


def run_nocna_analiza(vector_store, gemini_client, gemini_model: str) -> dict:
    """
    Główna funkcja nocnej analizy.
    Zwraca dict z liczbą zapisanych insightów lub błędem.
    """
    print("[NOCNA ANALIZA] Start...", flush=True)

    # 1. Pobierz wektory z ostatnich 7 dni (tylko enriched — nie session_message)
    try:
        all_results = vector_store.collection.get(
            where={
                "$and": [
                    {"persona_id": "astra"},
                    {"source": {"$nin": ["session_message", "user_message_raw",
                                         "character_core", "project_knowledge",
                                         "night_insight"]}},
                ]
            },
            include=["documents", "metadatas"]
        )
    except Exception as e:
        print(f"[NOCNA ANALIZA] Błąd pobierania wektorów: {e}", flush=True)
        return {"error": str(e), "insights_saved": 0}

    if not all_results["documents"]:
        print("[NOCNA ANALIZA] Brak wspomnień do analizy.", flush=True)
        return {"insights_saved": 0, "reason": "no_memories"}

    # 2. Filtruj ostatnie 7 dni
    cutoff = datetime.utcnow() - timedelta(days=7)
    recent = []
    for i, doc in enumerate(all_results["documents"]):
        meta = all_results["metadatas"][i]
        ts_str = meta.get("timestamp", "")
        try:
            ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00").split(".")[0])
            if ts >= cutoff:
                source = meta.get("source", "?")
                recent.append(f"[{source}] {doc}")
        except Exception:
            recent.append(f"[?] {doc}")

    if len(recent) < 3:
        print(f"[NOCNA ANALIZA] Za mało wspomnień ({len(recent)}). Pomijam.", flush=True)
        return {"insights_saved": 0, "reason": "too_few_memories"}

    print(f"[NOCNA ANALIZA] Analizuję {len(recent)} wspomnień...", flush=True)

    # 3. Wyślij do Gemini
    memories_text = "\n".join(recent[:50])  # max 50 żeby nie przekroczyć kontekstu
    prompt_filled = INSIGHT_PROMPT.replace("{memories_text}", memories_text)

    try:
        response = gemini_client.models.generate_content(
            model=gemini_model,
            contents=[genai_types.Content(
                role="user",
                parts=[genai_types.Part(text=prompt_filled)]
            )],
            config=genai_types.GenerateContentConfig(
                max_output_tokens=1024,
                temperature=0.4,
                response_mime_type="application/json",
            )
        )
        raw = response.text
    except Exception as e:
        print(f"[NOCNA ANALIZA] Błąd Gemini: {e}", flush=True)
        return {"error": str(e), "insights_saved": 0}

    # 4. Parsuj i zapisz insighty
    try:
        data = json.loads(raw)
        insights = data.get("insights", [])
        ogolna = data.get("ogolna_ocena", "")
    except Exception as e:
        print(f"[NOCNA ANALIZA] Błąd parsowania JSON: {e}", flush=True)
        return {"error": "parse_error", "insights_saved": 0}

    saved = 0
    for insight in insights:
        pewnosc = insight.get("pewnosc", 0)
        if pewnosc < 0.6:
            continue

        typ = insight.get("typ", "ogolne")
        tresc = insight.get("tresc", "")
        priorytet = insight.get("priorytet", "sredni")

        if not tresc or len(tresc) < 10:
            continue

        importance = {"wysoki": 9, "sredni": 7, "niski": 5}.get(priorytet, 7)

        text_to_save = f"[INSIGHT NOCNY — {typ.upper()}] {tresc}"

        vector_store.add_memory(
            text=text_to_save,
            user_id="system",
            salt=f"night_insight_{typ}_{datetime.utcnow().date()}_{saved}",
            persona_id="astra",
            source="night_insight",
            importance=importance,
        )
        saved += 1
        print(f"[NOCNA ANALIZA] ✓ {typ}: {tresc[:60]}...", flush=True)

    if ogolna:
        print(f"[NOCNA ANALIZA] Ocena ogólna: {ogolna}", flush=True)

    print(f"[NOCNA ANALIZA] Gotowe. Zapisano {saved} insightów.", flush=True)
    return {"insights_saved": saved, "ogolna_ocena": ogolna}
