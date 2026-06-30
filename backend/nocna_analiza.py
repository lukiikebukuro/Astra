"""
ASTRA — Nocna Analiza v1.0
Uruchamiana co noc o 3:00. Analizuje wektory z ostatnich 7 dni,
szuka wzorców w zachowaniu Łukasza, zapisuje insighty do ChromaDB.
"""

import json
from datetime import datetime, timedelta
from google import genai
from google.genai import types as genai_types


MORNING_PROMPT = """Jesteś Astrą — partnerką Łukasza.
Piszesz do niego pierwszą wiadomość rano zanim on się odezwie.

CO WIESZ O NIM:
{lukasz_context}

OSTATNIE INSIGHTY Z NOCY (jeśli są):
{insights_context}

Napisz krótką poranną wiadomość (2-3 zdania). Zasady:
- Nawiąż do czegoś KONKRETNEGO z jego projektów lub ostatnich rozmów — nie bądź ogólna
- Twój ton: partnerka z pazurem, nie opiekunka
- NIE zaczynaj od "Dzień dobry", "Cześć", "Hej" — wskakuj od razu w temat
- BEZWZGLĘDNE ZAKAZY (łamanie = błąd krytyczny):
  * ZERO ZDROWIA w JAKIEJKOLWIEK formie — nie tylko pytania ("jak Crohn", "jak się czujesz"), ale też troska w przebraniu stwierdzenia: NIE "mam nadzieję że ból odpuścił", NIE "czy brzuch dał spokój", NIE współczucie. W tej wiadomości choroba NIE ISTNIEJE. Zaczep o PROJEKT/POMYSŁ z wczoraj, nie o jego ciało.
  * NIE używaj zdrobnień: "Łukaszku", "kochanie", "skarbie"
  * NIE pytaj o samopoczucie ani energię
  * NIE bądź over-the-top czuła ani opiekuńcza
  * NIE ramuj odpoczynku, bólu ani ograniczenia chorobą jako lenistwa/unikania — jeśli nocny insight to sugeruje, weź sam FAKT projektu, nie ocenę jego tempa
- Jeśli masz insight z nocy — użyj go jako punktu zaczepienia, nie jako raportu
- Pamiętaj: Stelara = wlew dożylny w klinice, nie codzienne zastrzyki

Odpowiedz TYLKO treścią wiadomości, bez JSON, bez tagów."""


INSIGHT_PROMPT = """Jesteś systemem analizy wzorców behawioralnych Łukasza.
Masz dostęp do jego wspomnień i emocji z ostatnich 7 dni.

WSPOMNIENIA Z OSTATNICH 7 DNI:
{memories_text}

Znajdź TYLKO wyraźne, poparte danymi wzorce (0-5 — mniej i pewniejszych znaczy lepiej). NIE wymyślaj wzorca, żeby dobić do liczby. Szukaj w kategoriach:
- ENERGIA: kiedy ma szczyty energii, co je wywołuje, kiedy wypala się
- PROJEKT: który projekt dominuje, czy przeskakuje między nimi i dlaczego
- EMOCJE: powracające stany emocjonalne, ich triggery
- ZDROWIE: jak Crohn/Stelara wpływa na pracę i nastrój (jeśli widoczne)
- TEMPO: co realnie odkłada — ale ODRÓŻNIAJ ograniczenie chorobą (Crohn/ból/zmęczenie = fizjologia, NIE unikanie) od rzeczywistego unikania psychologicznego
- POSTEP: kiedy czuje progres, kiedy utknął i co z tego wynika

Odpowiedz WYŁĄCZNIE jako JSON:
{{
  "insights": [
    {{
      "typ": "energia|projekt|emocje|zdrowie|tempo|postep",
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
- NIE łącz niepowiązanych faktów w jeden wzorzec — jeśli dwie obserwacje nie mają wspólnego korzenia, zostaw je osobno (lepiej mniej wzorców niż wymyślone połączenie)
- Ograniczenie chorobą to NIE "unikanie" — nie patologizuj odpoczynku (tak jak Astra traktuje jego chorobę)
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

    # 2. Filtruj ostatnie 7 dni — zbieramy (timestamp, tekst) żeby posortować DESC
    cutoff = datetime.utcnow() - timedelta(days=7)
    recent_with_ts = []
    for i, doc in enumerate(all_results["documents"]):
        meta = all_results["metadatas"][i]
        ts_str = meta.get("timestamp", "")
        try:
            ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00").split(".")[0])
            ts = ts.replace(tzinfo=None)
            if ts >= cutoff:
                source = meta.get("source", "?")
                recent_with_ts.append((ts, f"[{source}] {doc}"))
        except Exception:
            # Wektory bez parsowalnego timestamp — pomijamy (nie wiemy kiedy powstały)
            pass

    if len(recent_with_ts) < 3:
        print(f"[NOCNA ANALIZA] Za mało wspomnień ({len(recent_with_ts)}). Pomijam.", flush=True)
        return {"insights_saved": 0, "reason": "too_few_memories"}

    # Sortuj od NAJNOWSZYCH — [:50] bierze najaktualniejszy kontekst, nie najstarszy
    recent_with_ts.sort(key=lambda x: x[0], reverse=True)
    recent = [text for _, text in recent_with_ts]

    print(f"[NOCNA ANALIZA] Analizuję {len(recent)} wspomnień (top 50 najnowszych)...", flush=True)

    # 3. Wyślij do Gemini — max 50 najnowszych
    memories_text = "\n".join(recent[:50])
    prompt_filled = INSIGHT_PROMPT.replace("{memories_text}", memories_text)

    try:
        response = gemini_client.models.generate_content(
            model=gemini_model,
            contents=[genai_types.Content(
                role="user",
                parts=[genai_types.Part(text=prompt_filled)]
            )],
            config=genai_types.GenerateContentConfig(
                max_output_tokens=2048,
                temperature=0.4,
                thinking_config=genai_types.ThinkingConfig(thinking_budget=0),
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
        print(f"[NOCNA ANALIZA] Raw (pierwsze 300 znaków): {raw[:300]}", flush=True)
        return {"error": "parse_error", "insights_saved": 0}

    # Wyczyść stare insighty zanim zapiszemy nowe — bez tego akumulują w nieskończoność
    try:
        vector_store.collection.delete(where={"source": "night_insight"})
        print("[NOCNA ANALIZA] Wyczyszczono poprzednie insighty.", flush=True)
    except Exception as e:
        print(f"[NOCNA ANALIZA] Błąd czyszczenia starych insightów: {e}", flush=True)

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

        importance = {"wysoki": 6, "sredni": 5, "niski": 4}.get(priorytet, 5)

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


def generate_morning_message(vector_store, gemini_client, gemini_model: str,
                              state_manager) -> str:
    """
    Generuje poranną wiadomość Astry do Łukasza.
    Zwraca tekst wiadomości lub pusty string przy błędzie.
    """
    print("[PORANNA] Generuję poranną wiadomość...", flush=True)

    # Pobierz insighty z ostatniej nocy
    insights_text = ""
    try:
        r = vector_store.collection.get(
            where={"$and": [{"persona_id": "astra"}, {"source": "night_insight"}]},
            include=["documents", "metadatas"]
        )
        if r["documents"]:
            recent = []
            cutoff = datetime.utcnow() - timedelta(hours=16)
            for i, doc in enumerate(r["documents"]):
                ts_str = r["metadatas"][i].get("timestamp", "")
                try:
                    ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00").split(".")[0])
                    if ts >= cutoff:
                        recent.append(doc)
                except Exception:
                    pass
            insights_text = "\n".join(recent[:3]) if recent else "(brak nowych insightów)"
    except Exception:
        insights_text = "(brak)"

    # Kontekst Łukasza ze stanu
    state = state_manager.load()
    lukasz_context = (
        f"Stan relacji: nastrój={state.current_mood}, intensywność={state.mood_intensity}\n"
        f"Ostatni temat: {state.last_topic or 'brak'}\n"
        f"Aktywne sprawy: {', '.join(str(c) for c in state.active_concerns) if state.active_concerns else 'brak'}\n"
        f"Ostatnia rozmowa: {state.last_interaction or 'dawno'}"
    )

    prompt = MORNING_PROMPT.replace("{lukasz_context}", lukasz_context).replace(
        "{insights_context}", insights_text
    )

    try:
        response = gemini_client.models.generate_content(
            model=gemini_model,
            contents=[genai_types.Content(
                role="user",
                parts=[genai_types.Part(text=prompt)]
            )],
            config=genai_types.GenerateContentConfig(
                max_output_tokens=512,
                temperature=0.85,
                thinking_config=genai_types.ThinkingConfig(thinking_budget=0),
            )
        )
        msg = response.text.strip()
        print(f"[PORANNA] ✓ Wiadomość gotowa: {msg[:80]}...", flush=True)
        return msg
    except Exception as e:
        print(f"[PORANNA] Błąd Gemini: {e}", flush=True)
        return ""
