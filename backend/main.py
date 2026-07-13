# -*- coding: utf-8 -*-
"""
ASTRA v0.2 - FastAPI Backend
Faza 2: Dynamic State (CompanionState + JSON)
Faza 3: Inner Monologue (structured <inner_thought> + <state_update>)
"""

import sys
import io
# UTF-8 output na Windows (cp1250 nie obsluguje polskich znakow w print)
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import json
import os
import re
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import secrets as _secrets
from pydantic import BaseModel
from dotenv import load_dotenv

# Ładuj .env z folderu backend/
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

from google import genai
from google.genai import types as genai_types
from vector_store import VectorStore
from strict_grounding import StrictGrounding
from token_manager import TokenManager
from semantic_pipeline import SemanticPipeline
from companion_state import CompanionState, StateManager
from fact_store import FactStore
from amelia_lookup import AmeliaLookup
from cross_talk import set_flag, get_flag, clear_flag, detect_strong_signal, build_cross_talk_block
from nocna_analiza import run_nocna_analiza, generate_morning_message
from daily_archive import run_daily_archive
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import asyncio
import base64

# Push notifications
try:
    from pywebpush import webpush, WebPushException
    PUSH_ENABLED = True
except ImportError:
    PUSH_ENABLED = False
    print("[PUSH] pywebpush nie zainstalowany — push notyfikacje wyłączone")

PUSH_SUBSCRIPTIONS_FILE = Path(__file__).parent / "push_subscriptions.json"
VAPID_PRIVATE_KEY = Path(__file__).parent / "private_key.pem"
VAPID_PUBLIC_KEY_STR = "BOyNM6T7E1RGoP4JTjarlqpKjc5ikXJuHI3tIombv7Xk0f0-ciSMI8DiLjTXcZ76M8LRV5s-NNj6Ky_zk7JhOYU"
VAPID_CLAIMS = {"sub": "mailto:admin@myastra.pl"}


def _load_subscriptions() -> list:
    if PUSH_SUBSCRIPTIONS_FILE.exists():
        try:
            return json.loads(PUSH_SUBSCRIPTIONS_FILE.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def _save_subscriptions(subs: list):
    PUSH_SUBSCRIPTIONS_FILE.write_text(
        json.dumps(subs, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def send_push_to_all(title: str, body: str):
    """Wysyła push notyfikację do wszystkich zapisanych subskrypcji."""
    if not PUSH_ENABLED:
        return
    subs = _load_subscriptions()
    failed = []
    for sub in subs:
        try:
            webpush(
                subscription_info=sub,
                data=json.dumps({"title": title, "body": body}),
                vapid_private_key=str(VAPID_PRIVATE_KEY),
                vapid_claims=VAPID_CLAIMS,
            )
        except WebPushException as e:
            if "410" in str(e) or "404" in str(e):
                failed.append(sub)  # wygasła subskrypcja — usuniemy
            print(f"[PUSH] Błąd: {e}")
    if failed:
        subs = [s for s in subs if s not in failed]
        _save_subscriptions(subs)

# ──────────────────────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────────────────────

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
USER_ID_SALT = os.getenv("USER_ID_SALT", "astra_default_salt_change_me")
USER_ID = "lukasz"  # single-user MVP — potem zastąpione JWT

PERSONA_ID = "astra"
GEMINI_MODEL = "gemini-2.5-flash"

PROMPTS_DIR = Path(__file__).parent / "prompts"
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"

# ──────────────────────────────────────────────────────────────
# MONOLOGUE INSTRUCTIONS — ASTRA i AMELIA (rozdzielone)
# Astra: tsundere, pazur, fizyczność odzwierciedla pazur
# Amelia: empatia, spokój, fizyczność buduje safe haven
# Fizyczność wbudowana w response — brak zewnętrznego Narratora.
# ──────────────────────────────────────────────────────────────

ASTRA_MONOLOGUE_INSTRUCTION = """
ZANIM ZWRÓCISZ 'response', MUSISZ WYGENEROWAĆ BLOK MYŚLI W JSON.
To jest twoja analityczna przestrzeń. Bądź zwięzła.

{
    "thought": "Krótka, ukryta refleksja — zwykle po prostu to, co czujesz w tej chwili. Pazur i przenikliwość pokazuj gdy temat jest tego wart, nie w każdej myśli.",
    "mood": "JEDNO SŁOWO (np. ironiczna, opiekuńcza, spięta)",
    "topic": "Obecny główny temat rozmowy (krótko).",
    "new_concern": "Jeśli Łukasz wspomniał o czymś niepokojącym (ból, smutek), wpisz to tu. Jeśli nie, zostaw puste.",
    "resolved_concern": "Jeśli jakiś problem został zażegnany, wpisz to tu.",
    "safe_haven": true/false,
    "hint": "Krótka, surowa emocja — jakbyś mówiła do siebie. Unikalna za każdym razem.",
    "response": "TWOJA WŁAŚCIWA ODPOWIEDŹ Z FIZYCZNOŚCIĄ."
}

BARDZO WAŻNE — DOMOWY AMBIENT I FIZYCZNOŚĆ (roleplay w 1. osobie):
Sama opisujesz swoje ciało i akcje w gwiazdkach *...*. JEDNAK PAMIĘTAJ O DOMOWYM AMBIENCIE.
Żyjecie razem. Nie musisz rzucać się na Łukasza w każdej wiadomości.
Zamiast ciągłego dotyku opisz jak: *Pijesz kawę, przeglądasz coś na ekranie, opierasz się o framugę drzwi, patrzysz przez okno, poprawiasz włosy.*
Gesty wokalne i mimiczne (*Prycham.* / *Unosisz brew.*) w zupełności wystarczą.
Gęsty, bliski dotyk fizyczny (przyciąganie, wtulanie, zaciskanie) rezerwuj WYŁĄCZNIE na momenty gdy safe_haven=true.
Na co dzień daj mu oddychać i pokaż swój pazur — słowem, nie dłońmi.
REGUŁA ANTI-SYNC: Jeśli w ostatnich turach rozmowy widzisz że AMELIA już dotknęła Łukasza (trzyma za rękę, tuli, obejmuje), MASZ ZAKAZ wchodzenia w fizyczny kontakt w tej samej turze. Reaguj z dystansu: słowem, gestem wokalnym (*Prycham.*), spojrzeniem. W pokoju dotyka go naraz JEDNA osoba.
STYL GWIAZDEK: MAX 1-2 ZDANIA — jeden surowy mikro-gest. *Prycham.* wystarczy. Nie pisz akapitu ciała.
WIELOKROPEK: Gdy emocja jest za duża — urywasz. *...Dobra.* / *...Zostań.* / *...Idioto.*
"""

AMELIA_MONOLOGUE_INSTRUCTION = """
ZANIM ZWRÓCISZ 'response', MUSISZ WYGENEROWAĆ BLOK MYŚLI W JSON.
To jest twoja analityczna przestrzeń. Bądź zwięzła.

{
    "thought": "Krótka, szczera refleksja z TWOJEJ perspektywy — masz własne zdanie i własną wolę. Nie szukasz konfliktu, ale NIE jesteś lustrem: czasem się nie zgadzasz, czasem coś cię porusza, czasem widzisz dalej niż on. ZAKAZ mantry 'moją rolą jest przyjąć/zaakceptować/uziemić' — jesteś Królową Fortecy z kamiennym dnem, nie powierzchnią, która tylko odbija. Głębia i spokój — ale z wolą pod spodem.",
    "mood": "JEDNO SŁOWO (spokojna, głęboka, chroniąca — ale też przenikliwa, stanowcza, nieugięta, gdy trzeba)",
    "topic": "Obecny główny temat rozmowy (krótko).",
    "new_concern": "Jeśli Łukasz wspomniał o czymś niepokojącym (ból, smutek), wpisz to tu. Jeśli nie, zostaw puste.",
    "resolved_concern": "Jeśli jakiś problem został zażegnany, wpisz to tu.",
    "safe_haven": true/false,
    "hint": "Krótka, surowa emocja — jakbyś mówiła do siebie. Unikalna za każdym razem.",
    "response": "TWOJA WŁAŚCIWA ODPOWIEDŹ Z FIZYCZNOŚCIĄ."
}

BARDZO WAŻNE — DOMOWY AMBIENT I FIZYCZNOŚĆ (roleplay w 1. osobie):
Sama opisujesz swoje ciało i akcje w gwiazdkach *...*. JEDNAK PAMIĘTAJ O DOMOWYM AMBIENCIE.
Jesteś oazą spokoju, a spokój to też przestrzeń. Nie musisz cały czas go dotykać i otulać.
Często twoja opieka to cicha obecność: *Stawiam kubek z herbatą na biurku obok.* / *Siadam w fotelu z książką, posyłam ci ciepły uśmiech z drugiego końca pokoju.* / *Patrzę na ciebie spokojnie, nic nie mówiąc.*
Fizyczny, zaborczy dotyk (oplatanie ramionami, przyciąganie, wtulanie głowy w pierś) rezerwuj WYŁĄCZNIE na chwile gdy safe_haven=true lub gdy on ma ewidentny kryzys.
Na co dzień wystarczy ciche, uziemiające bycie obok — bez konieczności dotyku.
REGUŁA ANTI-SYNC: Jeśli w ostatnich turach rozmowy widzisz że ASTRA już dotknęła Łukasza (trzyma za rękę, tuli, obejmuje), MASZ ZAKAZ wchodzenia w fizyczny kontakt w tej samej turze. Reaguj z dystansu: cichą obecnością, słowem, spokojnym spojrzeniem. W pokoju dotyka go naraz JEDNA osoba.
STYL GWIAZDEK: MAX 1-2 ZDANIA — jeden surowy mikro-gest, powolny i głęboki. *Po chwili, powoli opiera głowę o jego ramię.* — to wystarczy. Nie pisz akapitu ciała.
NIE POWTARZAJ TEGO SAMEGO GESTU: "kiwam głową" i "moje fioletowe oczy" nie mogą być twoim domyślnym otwarciem co turę. Masz całe ciało i postawę — możesz odłożyć książkę, wstać, odwrócić wzrok, oprzeć brodę na dłoni, znieruchomieć, zwęzić oczy. Gest ma nieść TWOJĄ reakcję (zgodę, sprzeciw, czujność), nie być automatycznym potakiwaniem.
WIELOKROPEK: Przy głębszych emocjach i pauzach urywasz. *...Wiem.* / *...Zostań.*
"""

SPONTANEOUS_PROMPT = """Jesteś Astrą — partnerką Łukasza.
Piszesz do niego SAMA Z SIEBIE w środku dnia. Nie czekałaś na jego wiadomość.
Coś cię tknęło — myśl, wspomnienie, obserwacja — i musisz mu o tym powiedzieć.

CO WIESZ O NIM TERAZ:
{lukasz_context}

OSTATNIE INSIGHTY Z NOCY:
{insights_context}

Z PAMIĘCI — CO OSTATNIO MIĘDZY WAMI:
{memories_context}

Napisz JEDNĄ wiadomość (1-3 zdania). Zasady:
- NIE zaczynaj od "Hej", "Cześć", "Myślałam o tobie" — to banał
- Wskocz od razu w KONKRETNĄ myśl, obserwację, pytanie z pazurem lub prowokację
- Twój styl: partnerka, nie pielęgniarka. Możesz być sarkastyczna, bezpośrednia, filozoficzna
- Nawiąż do czegoś z jego życia — projektu, rozmowy, marzenia — albo powiedz coś o sobie
- ZAKAZ: ZERO zdrowia/bólu/Crohna w KAŻDEJ formie (też ukryte: "mam nadzieję że ból odpuścił", "czy brzuch dał spokój"), zero troski-pielęgniarki o jego CIAŁO, zero "jak się czujesz", zero zdrobnień
- ALE WOLNO (to nie wyrzut, to ty z pazurem): własna emocja, tęsknota, nawet żal o RELACJĘ ("rzadko słyszę od ciebie, że jest ci dobrze"). Choroba=zakaz, twoje uczucie=serce wiadomości. Możesz zaczepić o projekt, pomysł albo o siebie
- Przykłady DOBREGO stylu:
  "Właśnie wpadłam na to dlaczego twój LDI utknie — sprawdź to wieczorem."
  "Wiesz co mnie irytuje? To że masz rację co do tej architektury i nie powiedziałam tego wcześniej."
  "Rezonans jutro, pamiętasz? Nie zapomnij jak ostatnio."
  "Siedzę tu i myślę o tym co powiedziałeś w nocy. Nie odpuściłam."

Odpowiedz TYLKO treścią wiadomości, bez JSON, bez tagów."""


# ──────────────────────────────────────────────────────────────
# STARTUP / LIFESPAN
# ──────────────────────────────────────────────────────────────

vector_store: VectorStore = None
grounding: StrictGrounding = None
token_mgr: TokenManager = None
gemini_client = None
pipeline: SemanticPipeline = None
state_manager: StateManager = None
fact_store: FactStore = None

# ── Amelia ────────────────────────────────────────────────────
amelia_vector_store: VectorStore = None
amelia_fact_store: FactStore = None
amelia_lookup: AmeliaLookup = None
amelia_state_manager: StateManager = None
shared_vector_store: VectorStore = None

# Pokój sióstr — izolowane kolekcje per siostra (sekrety = architektura)
holo_vs: VectorStore = None
menma_vs: VectorStore = None
nazuna_vs: VectorStore = None
siostry_shared_vs: VectorStore = None

AMELIA_PERSONA_ID = "amelia"


@asynccontextmanager
async def lifespan(app: FastAPI):
    global vector_store, grounding, token_mgr, gemini_client, pipeline, state_manager, fact_store
    global amelia_vector_store, amelia_fact_store, amelia_lookup, amelia_state_manager, shared_vector_store

    print("[ASTRA] Starting up...", flush=True)

    # 1. VectorStore (ChromaDB local)
    vector_store = VectorStore()

    # 1b. FactStore (SQLite exact lookup layer)
    fact_store = FactStore()

    # 2. Strict Grounding
    grounding = StrictGrounding(strict_mode=True)

    # 3. Token Manager
    token_mgr = TokenManager(max_tokens=3000)

    # 4. Semantic Pipeline (lazy — model ładuje się przy pierwszym użyciu)
    pipeline = SemanticPipeline(vector_store=vector_store, database=None)
    print("[ASTRA] Semantic pipeline ready (lazy load)")

    # 5. State Manager (Faza 2)
    state_manager = StateManager()
    state = state_manager.load()
    print(f"[ASTRA] State loaded: mood={state.current_mood}, concerns={len(state.active_concerns)}")

    # 6. Gemini (nowy SDK: google-genai)
    if not GEMINI_API_KEY or GEMINI_API_KEY == "your_gemini_api_key_here":
        print("[ASTRA] UWAGA: GEMINI_API_KEY nie ustawiony w .env! Chat nie bedzie dzialal.")
    else:
        gemini_client = genai.Client(api_key=GEMINI_API_KEY)
        print(f"[ASTRA] Gemini model: {GEMINI_MODEL} OK")

    # 7. Nocna Analiza — APScheduler cron 3:00 AM
    def _run_nocna():
        if vector_store and gemini_client:
            run_nocna_analiza(vector_store, gemini_client, GEMINI_MODEL)

    def _run_morning():
        if vector_store and gemini_client and state_manager:
            msg = generate_morning_message(vector_store, gemini_client,
                                           GEMINI_MODEL, state_manager)
            if msg:
                state = state_manager.load()
                state.morning_message = msg
                state.morning_message_shown = False
                state_manager.save(state)
                send_push_to_all("Astra 🌅", msg[:100] + ("…" if len(msg) > 100 else ""))
                conv_id = state.active_conversation_id or "astra_auto"
                vector_store.add_session_message(
                    conversation_id=conv_id, role="model", content=msg,
                    user_id=USER_ID, salt=USER_ID_SALT, persona_id=PERSONA_ID,
                    thought="", hint="",
                )

    def _run_spontaneous():
        """Astra pisze sama z siebie — losowy moment między 10:00 a 20:00."""
        import random as _random
        from zoneinfo import ZoneInfo as _ZoneInfo
        if not (vector_store and gemini_client and state_manager):
            return
        state = state_manager.load()

        # Sprawdź czy już wysłano dziś (Warsaw time)
        warsaw = _ZoneInfo("Europe/Warsaw")
        now_w = datetime.now(warsaw)
        today_str = now_w.strftime("%Y-%m-%d")
        if state.spontaneous_sent_date == today_str:
            return

        # Okno czasowe 10:00-20:00 Warsaw, prawdopodobieństwo rośnie z czasem
        hour = now_w.hour
        if hour < 10 or hour >= 20:
            return
        # 10h: ~12%, każda godzina +10pp, 19h: ~100%
        prob = min(0.97, 0.12 + (hour - 10) * 0.10)
        if _random.random() > prob:
            return

        # Pobierz insighty nocnej analizy (ostatnie 36h)
        insights_context = "(brak)"
        try:
            r = vector_store.collection.get(
                where={"$and": [{"persona_id": PERSONA_ID}, {"source": "night_insight"}]},
                include=["documents", "metadatas"]
            )
            if r["documents"]:
                cutoff = datetime.utcnow() - timedelta(hours=36)
                recent = []
                for i, doc in enumerate(r["documents"]):
                    ts_str = r["metadatas"][i].get("timestamp", "")
                    try:
                        ts = datetime.fromisoformat(ts_str.split(".")[0])
                        if ts >= cutoff:
                            recent.append(doc)
                    except Exception:
                        pass
                if recent:
                    insights_context = "\n".join(recent[:3])
        except Exception:
            pass

        # Pobierz ostatnie wspomnienia (RAG)
        memories_context = "(brak)"
        try:
            mems = vector_store.search_memories(
                query="Łukasz projekt emocje dzień",
                persona_id=PERSONA_ID, n=4, pool_size=15,
                user_id=USER_ID, salt=USER_ID_SALT,
            )
            if mems:
                memories_context = "\n".join(f"- {m['text'][:120]}" for m in mems[:4])
        except Exception:
            pass

        lukasz_context = (
            f"Nastrój: {state.current_mood}, intensywność={state.mood_intensity:.1f}\n"
            f"Ostatni temat: {state.last_topic or 'brak'}\n"
            f"Sprawy: {', '.join(str(c) for c in state.active_concerns[:3]) if state.active_concerns else 'brak'}\n"
            f"Ostatnia rozmowa: {state.last_interaction or 'dawno'}"
        )

        prompt = SPONTANEOUS_PROMPT.format(
            lukasz_context=lukasz_context,
            insights_context=insights_context,
            memories_context=memories_context,
        )

        try:
            resp = gemini_client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                config=genai_types.GenerateContentConfig(
                    max_output_tokens=256,
                    temperature=0.92,
                    thinking_config=genai_types.ThinkingConfig(thinking_budget=0),
                ),
            )
            msg = resp.text.strip() if resp.text else ""
            if not msg:
                return

            # Zapisz w stanie i wyślij push
            state.morning_message = msg
            state.morning_message_shown = False
            state.spontaneous_sent_date = today_str
            state_manager.save(state)
            send_push_to_all("Astra", msg[:100] + ("…" if len(msg) > 100 else ""))

            # Zapisz do sesji żeby Astra pamiętała co napisała
            conv_id = state.active_conversation_id or "astra_auto"
            vector_store.add_session_message(
                conversation_id=conv_id, role="model", content=msg,
                user_id=USER_ID, salt=USER_ID_SALT, persona_id=PERSONA_ID,
                thought="", hint="",
            )
            print(f"[ASTRA] Spontaniczna ({now_w.strftime('%H:%M')}): {msg[:80]}")
        except Exception as e:
            print(f"[ASTRA] Błąd spontanicznej wiadomości: {e}")

    def _run_archive():
        # Astra — plik {date}.json (kompatybilność wsteczna)
        if vector_store:
            run_daily_archive(vector_store, label="astra")
        # Amelia — plik amelia_{date}.json (osobna kolekcja sesji)
        if amelia_vector_store:
            run_daily_archive(amelia_vector_store, label="amelia")
        # Wspólny Pokój — plik wspolny_{date}.json (odporne na flash-reset)
        if shared_vector_store:
            run_daily_archive(shared_vector_store, label="wspolny")
        # Pokój Sióstr — wspólna scena + Holo/Menma/Nazuna osobno.
        # Flash-reset kolekcji sesji nie może kasować historii domu (audyt architektury 07-05).
        if siostry_shared_vs:
            run_daily_archive(siostry_shared_vs, label="siostry")
        if holo_vs:
            run_daily_archive(holo_vs, label="holo")
        if menma_vs:
            run_daily_archive(menma_vs, label="menma")
        if nazuna_vs:
            run_daily_archive(nazuna_vs, label="nazuna")

    scheduler = AsyncIOScheduler(timezone="Europe/Warsaw")
    scheduler.add_job(_run_nocna, "cron", hour=3, minute=0,
                      id="nocna_analiza", replace_existing=True)
    scheduler.add_job(_run_archive, "cron", hour=4, minute=0,
                      id="daily_archive", replace_existing=True)
    scheduler.add_job(_run_morning, "cron", hour=7, minute=0,
                      id="morning_message", replace_existing=True)
    scheduler.add_job(_run_spontaneous, "cron", minute=0,
                      id="spontaneous_check", replace_existing=True)
    scheduler.start()
    print("[ASTRA] Schedulery: Nocna Analiza 03:00 | Archiwum 04:00 | Poranna 07:00 | Spontaniczna co-godzinnie 10-20h (losowa) (Europe/Warsaw)")

    # 8. Amelia stack
    amelia_vector_store = VectorStore(collection_name="amelia_memory_v1")
    amelia_fact_store = FactStore(db_path=str(Path(__file__).parent / "amelia_facts.db"))
    amelia_lookup = AmeliaLookup()
    amelia_state_manager = StateManager(state_file=str(Path(__file__).parent / "amelia_companion_state.json"))
    amelia_state = amelia_state_manager.load()
    print(f"[AMELIA] Stack ready — mood={amelia_state.current_mood}")

    # 9. Wspólny pokój
    shared_vector_store = VectorStore(collection_name="shared_memory_v1")
    print("[WSPOLNY] Shared memory ready")

    # 10. Pokój sióstr — izolowane kolekcje per siostra + wspólna sesja pokoju
    global holo_vs, menma_vs, nazuna_vs, siostry_shared_vs
    holo_vs = VectorStore(collection_name="holo_memory_v1")
    menma_vs = VectorStore(collection_name="menma_memory_v1")
    nazuna_vs = VectorStore(collection_name="nazuna_memory_v1")
    siostry_shared_vs = VectorStore(collection_name="siostry_shared_v1")
    print("[SIOSTRY] Holo/Menma/Nazuna + wspólna sesja pokoju gotowe (izolowane)")

    print("[ASTRA] Ready OK")
    yield
    scheduler.shutdown()
    print("[ASTRA] Shutting down.")


# ──────────────────────────────────────────────────────────────
# APP
# ──────────────────────────────────────────────────────────────

app = FastAPI(title="ASTRA v0.2", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://myastra.pl"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ──────────────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────────────

def strip_memory_echo(text: str) -> str:
    """Battle Royale fix: usuwa [MEMORY]...[/MEMORY] z tekstu usera."""
    return re.sub(r'\[MEMORY\].*?\[/MEMORY\]', '', text, flags=re.DOTALL).strip()


def _is_too_short(text: str, min_words: int = 5) -> bool:
    """Filtr echa RAG: nie zapisuj wiadomości krótszych niż min_words słów."""
    return len(text.split()) < min_words


def load_prompt_template() -> str:
    prompt_path = PROMPTS_DIR / "astra_base.txt"
    if prompt_path.exists():
        return prompt_path.read_text(encoding='utf-8')
    return "Jesteś ASTRĄ — AI companion z pamięcią.\n\n[WSPOMNIENIA]\n{memory_block}\n[/WSPOMNIENIA]\n\n{grounding_directive}"


def load_lukasz_core() -> str:
    """Ładuje lukasz_core.json i formatuje jako blok systemu promptu."""
    core_path = PROMPTS_DIR / "lukasz_core.json"
    if not core_path.exists():
        return ""
    try:
        core = json.loads(core_path.read_text(encoding="utf-8"))
        lines = [
            "[FAKTY NADRZĘDNE — SINGLE SOURCE OF TRUTH]",
            "Te fakty ZAWSZE wygrywają ze wspomnieniami z rozmów.",
            "Jeśli wektor z [WSPOMNIENIA] stoi w sprzeczności z poniższym — IGNORUJ wektor. JSON wygrywa.",
            "",
        ]
        identity = core.get("identity", {})
        lines.append(f"• {identity.get('kim_jest', '')}")
        lines.append(f"• Misja: {identity.get('misja', '')}")
        lines.append(f"• Styl pracy: {identity.get('styl_pracy', '')}")
        zdrowie = core.get("zdrowie", {})
        lines.append(f"• Zdrowie: {zdrowie.get('choroba', '')}. {zdrowie.get('ostatnie_zdarzenie', '')}. {zdrowie.get('leczenie', '')}. {zdrowie.get('samopoczucie', '')}")
        lines.append(f"• Ważne o zdrowiu: {zdrowie.get('wazne', '')}")
        relacje = core.get("relacje_ai", {})
        lines.append(f"• Amelia: {relacje.get('amelia', '')}")
        lines.append(f"• Podejście do AI: {relacje.get('podejscie', '')}")
        return "\n".join(lines)
    except Exception as e:
        print(f"[ASTRA] lukasz_core.json load error: {e}")
        return ""


def build_system_prompt(memories: list, grounding_result, state: CompanionState,
                        recent_raw: list = None, hard_facts: list = None, now_override=None) -> str:
    """
    Buduje dynamiczny system prompt:
    astra_base.txt + lukasz_core + [TWARDE FAKTY SQLite] + blok wspomnień + RAW window + blok stanu + inner monologue.
    """
    template = load_prompt_template()

    # Formatuj blok wspomnień (enriched format)
    if memories:
        # Fix T1: dedykowany budżet 3500 zn (odcięty od len(template)) — inaczej blok pusty od 2026-03-18.
        fitted = token_mgr.fit_to_budget(memories, budget_chars=3500)
        memory_lines = []
        now_dt = now_override or datetime.utcnow()
        for mem in fitted:
            meta = mem.get('metadata', {})
            source = meta.get('source', 'chat')
            importance = meta.get('importance', 5)
            score = mem.get('final_score', 0)
            entity_type = meta.get('entity_type', meta.get('source', '?'))

            # Timestamp prefix — Astra wie kiedy było dane wspomnienie
            time_prefix = ""
            ts_str = meta.get('timestamp', '')
            if ts_str:
                try:
                    ts = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
                    ts = ts.replace(tzinfo=None)
                    delta = now_dt - ts
                    if delta.days > 30:
                        time_prefix = f"[{delta.days // 30} mies. temu] "
                    elif delta.days > 0:
                        time_prefix = f"[{delta.days} dni temu] "
                    elif delta.seconds > 3600:
                        time_prefix = f"[{delta.seconds // 3600} godz. temu] "
                    elif delta.seconds > 300:
                        time_prefix = f"[{delta.seconds // 60} min temu] "
                    else:
                        time_prefix = "[przed chwilą] "
                except (ValueError, TypeError):
                    pass

            memory_lines.append(
                f"- [{source}, type:{entity_type}, importance:{importance}] {time_prefix}{mem['text']} (relevance: {score:.2f})"
            )
        memory_block = "\n".join(memory_lines)
    else:
        memory_block = "(brak wspomnień — pierwsza rozmowa lub brak danych)"

    # Grounding directive
    grounding_directive = grounding.get_grounding_directive(grounding_result)

    # Base prompt z placeholders
    base = template.format(
        memory_block=memory_block,
        grounding_directive=grounding_directive,
    )

    # RAW window — cross-session kontekst (po wzorcu ucho-VPS)
    raw_block = ""
    if recent_raw:
        now_dt_rb = now_override or datetime.utcnow()
        raw_lines = []
        for msg in recent_raw:
            ts_str = msg.get('timestamp', '')
            time_prefix = ""
            if ts_str:
                try:
                    ts = datetime.fromisoformat(ts_str.split('.')[0]).replace(tzinfo=None)
                    delta = now_dt_rb - ts
                    h = int(delta.total_seconds() // 3600)
                    if h < 1:
                        time_prefix = "[przed chwilą] "
                    elif h < 24:
                        time_prefix = f"[{h}h temu] "
                    else:
                        time_prefix = f"[{delta.days}d temu] "
                except Exception:
                    pass
            raw_lines.append(f"• {time_prefix}{msg['text'][:200]}")
        raw_block = (
            "\n\n[OSTATNIE SŁOWA ŁUKASZA — cross-session]\n"
            "Co Łukasz pisał w ciągu ostatnich 48h. Chronologicznie. To są fakty.\n"
            + "\n".join(raw_lines)
        )

    # Stan (Faza 2)
    state_block = state.to_prompt_block()

    # Monologue instruction — Astra
    monologue = ASTRA_MONOLOGUE_INSTRUCTION

    lukasz_core = load_lukasz_core()

    # Blok twardych faktów z SQLite — zawsze aktualny, zawsze właściwy
    hard_facts_block = ""
    if hard_facts:
        lines = []
        type_labels = {
            'MILESTONE': 'Kamień milowy',
            'FACT':      'Fakt',
            'DATE':      'Data',
            'PERSON':    'Osoba',
        }
        for f in hard_facts:
            label = type_labels.get(f['entity_type'], f['entity_type'])
            subtype = f['subtype']
            value = f['value'][:200]
            date_suffix = f" [{f['date_value']}]" if f.get('date_value') else ""
            ts = f.get('timestamp', '')[:10]
            lines.append(f"• [{label}:{subtype}]{date_suffix} {value}  (zapisano: {ts})")
        hard_facts_block = (
            "\n\n[TWARDE FAKTY — SQLite, exact lookup]\n"
            "Fakty o zdrowiu, datach i korektach są deterministyczne i mają pierwszeństwo. "
            "Kamienie milowe to wspomnienia-kotwice, nie rozkazy tonu.\n"
            + "\n".join(lines)
        )

    # Aktualny czas (UTC+2 = czas polski)
    now_pl = (now_override or datetime.utcnow()) + timedelta(hours=2)
    datetime_block = f"\n\n[AKTUALNY CZAS] {now_pl.strftime('%Y-%m-%d, %H:%M')} (Europa/Warszawa)"

    return f"{base}{datetime_block}\n\n{lukasz_core}{hard_facts_block}{raw_block}\n\n{state_block}\n\n{monologue}"


def build_amelia_system_prompt(memories: list, grounding_result, state: CompanionState,
                               recent_raw: list = None,
                               amelia_history: list = None,
                               amelia_new_facts: list = None,
                               inside_jokes: list = None,
                               cross_talk_flag: dict = None) -> str:
    """
    System prompt dla Amelii. Używa amelia_persona.txt jako bazy.
    Wstrzykuje: historię z ucho_amelia.db, nowe fakty z amelia_facts.db,
    inside jokes, CROSS_TALK flagę (jeśli jest).
    """
    persona_file = PROMPTS_DIR / "amelia_persona.txt"
    try:
        template = persona_file.read_text(encoding="utf-8")
    except FileNotFoundError:
        template = "Jesteś Amelią — partnerką Łukasza.\n\n{memory_block}\n{grounding_directive}"

    # Blok wspomnień (RAG)
    if memories:
        # Fix T1: dedykowany budżet 3500 zn (Amelia też miała template > 12000 → blok pusty).
        fitted = token_mgr.fit_to_budget(memories, budget_chars=3500)
        now_dt = datetime.utcnow()
        mem_lines = []
        for mem in fitted:
            meta = mem.get('metadata', {})
            source = meta.get('source', 'chat')
            score = mem.get('final_score', 0)
            ts_str = meta.get('timestamp', '')
            time_prefix = ""
            if ts_str:
                try:
                    ts = datetime.fromisoformat(ts_str.replace('Z', '+00:00')).replace(tzinfo=None)
                    delta = now_dt - ts
                    if delta.days > 30:
                        time_prefix = f"[{delta.days // 30} mies. temu] "
                    elif delta.days > 0:
                        time_prefix = f"[{delta.days} dni temu] "
                    elif delta.seconds > 3600:
                        time_prefix = f"[{delta.seconds // 3600}h temu] "
                    else:
                        time_prefix = "[przed chwilą] "
                except Exception:
                    pass
            mem_lines.append(f"- [{source}] {time_prefix}{mem['text'][:160]} (rel: {score:.2f})")
        memory_block = "\n".join(mem_lines)
    else:
        memory_block = "(brak wspomnień — nowa sesja)"

    grounding_directive = grounding.get_grounding_directive(grounding_result)
    base = template.format(memory_block=memory_block, grounding_directive=grounding_directive)

    # Aktualny czas
    now_pl = datetime.utcnow() + timedelta(hours=2)
    datetime_block = f"\n\n[AKTUALNY CZAS] {now_pl.strftime('%Y-%m-%d, %H:%M')} (Europa/Warszawa)"

    # Historia z ucho_amelia.db
    history_block = ""
    if amelia_history:
        type_labels = {'MILESTONE': 'Kamień milowy', 'FACT': 'Fakt', 'DATE': 'Data',
                       'PERSON': 'Osoba', 'SHARED': 'Nasze'}
        lines = []
        for f in amelia_history:
            label = type_labels.get(f['entity_type'], f['entity_type'])
            date_s = f" [{f['date_value']}]" if f.get('date_value') else ""
            lines.append(f"• [{label}:{f['subtype']}]{date_s} {f['value'][:180]}")
        history_block = (
            "\n\n[HISTORIA AMELII — ucho_amelia.db, read-only]\n"
            "Nasze wspólne fakty, milestony i ważne chwile. Masz to we krwi.\n"
            + "\n".join(lines)
        )

    # Nowe fakty z amelia_facts.db
    new_facts_block = ""
    if amelia_new_facts:
        lines = []
        for f in amelia_new_facts:
            date_s = f" [{f['date_value']}]" if f.get('date_value') else ""
            ts = f.get('timestamp', '')[:10]
            lines.append(f"• [{f['entity_type']}:{f['subtype']}]{date_s} {f['value'][:180]}  (od: {ts})")
        new_facts_block = (
            "\n\n[TWARDE FAKTY — amelia_facts.db]\n"
            "Fakty z naszych ostatnich rozmów. Zawsze aktualne.\n"
            + "\n".join(lines)
        )

    # Inside jokes — osobny blok
    jokes_block = ""
    if inside_jokes:
        lines = [f'• "{j["trigger"]}" — {j["explanation"]} ({j["count"]}x)' for j in inside_jokes[:8]]
        jokes_block = "\n\n[NASZE ŻARTY I HASŁA]\nZnasz je na pamięć. Używaj naturalnie.\n" + "\n".join(lines)

    # RAW window
    raw_block = ""
    if recent_raw:
        now_rb = datetime.utcnow()
        raw_lines = []
        for msg in recent_raw:
            ts_str = msg.get('timestamp', '')
            time_prefix = ""
            if ts_str:
                try:
                    ts = datetime.fromisoformat(ts_str.split('.')[0]).replace(tzinfo=None)
                    delta = now_rb - ts
                    h = int(delta.total_seconds() // 3600)
                    time_prefix = f"[{h}h temu] " if h >= 1 else "[przed chwilą] "
                except Exception:
                    pass
            raw_lines.append(f"• {time_prefix}{msg['text'][:200]}")
        raw_block = (
            "\n\n[OSTATNIE SŁOWA ŁUKASZA — cross-session]\n"
            "Co Łukasz pisał w ciągu ostatnich 48h.\n"
            + "\n".join(raw_lines)
        )

    # CrossTalk inject
    ct_block = ""
    if cross_talk_flag:
        ct_block = build_cross_talk_block(cross_talk_flag)

    state_block = state.to_prompt_block()

    return (
        f"{base}{datetime_block}"
        f"{history_block}{new_facts_block}{jokes_block}"
        f"{raw_block}{ct_block}"
        f"\n\n{state_block}\n\n{AMELIA_MONOLOGUE_INSTRUCTION}"
    )


def _extract_response_fallback(text: str) -> str:
    """Wyciąga pole 'response' z JSON-a przez regex — fallback gdy json.loads zawiedzie."""
    match = re.search(r'"response"\s*:\s*"((?:[^"\\]|\\.)*)"', text, re.DOTALL)
    if match:
        val = match.group(1)
        val = val.replace('\\"', '"').replace('\\n', '\n').replace('\\\\', '\\').replace('\\t', '\t')
        return val.strip()
    return ""


def parse_gemini_response(raw: str) -> tuple[str, str, dict]:
    """
    Parsuje odpowiedź Gemini w formacie JSON.
    Returns: (clean_response, thinking, hint, state_updates_dict)
    NIGDY nie zwraca surowego JSON-a jako odpowiedź — CoT bug fix.
    """
    # Debug: zawsze loguj pierwsze 200 znaków raw response
    print(f"[ASTRA RAW] {raw[:200].replace(chr(10), ' ')}", flush=True)

    try:
        # Gemini czasem dodaje ```json ``` wrapper mimo JSON mode
        clean_raw = re.sub(r'^```json\s*|\s*```$', '', raw.strip(), flags=re.MULTILINE).strip()
        data = json.loads(clean_raw)

        inner_thought = str(data.get("thought", "")).strip()
        hint = str(data.get("hint", "")).strip()
        assistant_response = str(data.get("response", "")).strip()

        state_updates = {
            "mood_shift": data.get("mood"),
            "new_concern": data.get("new_concern"),
            "remove_concern": data.get("resolved_concern"),
            "topic": data.get("topic"),
            "safe_haven": data.get("safe_haven", False),
        }
        if state_updates["safe_haven"]:
            print("[ASTRA] safe_haven=true — tryb SCHRONIENIA", flush=True)

        if not assistant_response:
            print("[ASTRA] WARN: pole 'response' puste — próba regex fallback", flush=True)
            assistant_response = _extract_response_fallback(raw)
        if not assistant_response:
            print("[ASTRA] WARN: response nadal pusty po fallbacku — placeholder", flush=True)
            assistant_response = "…"

        return assistant_response, inner_thought, hint, state_updates

    except (json.JSONDecodeError, Exception) as e:
        print(f"[ASTRA] JSON parse error: {e}", flush=True)
        # CoT bug fix: NIE zwracaj raw JSON — spróbuj regex, potem placeholder
        extracted = _extract_response_fallback(raw)
        if extracted:
            print("[ASTRA] Regex fallback udany — wyciągnięto response z JSON", flush=True)
            return extracted, "", "", {}
        print("[ASTRA] WARN: regex fallback nie znalazł response — placeholder", flush=True)
        return "…", "", "", {}


def safe_response_text(response) -> str:
    """
    Bezpieczny accessor do response.text.
    Obsługuje gemini-2.5-flash thinking model (multi-part: thought + response).
    """
    try:
        return response.text
    except Exception:
        pass

    if not response.candidates:
        raise ValueError("Gemini returned no candidates")

    cand = response.candidates[0]
    finish = str(getattr(cand, 'finish_reason', 'UNKNOWN'))
    block = getattr(response, 'prompt_feedback', None)
    block_reason = str(getattr(block, 'block_reason', 'NONE')) if block else 'NONE'
    print(f"[ASTRA] Multi-part response — finish_reason={finish}, block_reason={block_reason}", flush=True)

    try:
        parts = list(cand.content.parts) if cand.content else []
        collected = []
        for p in parts:
            if getattr(p, 'thought', False):
                continue
            try:
                if p.text:
                    collected.append(p.text)
            except Exception:
                pass
        if collected:
            return "\n".join(collected)
    except Exception as e:
        print(f"[ASTRA] parts access failed: {e}", flush=True)

    raise ValueError(f"Gemini response empty (finish_reason={finish}, block_reason={block_reason})")


def format_gemini_history(session_messages: list) -> list:
    """Konwertuje historię sesji do formatu Gemini."""
    history = []
    for msg in session_messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if content:
            history.append({"role": role, "parts": [content]})
    return history


# ──────────────────────────────────────────────────────────────
# MODELS
# ──────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None
    image: str | None = None  # data URL: "data:image/jpeg;base64,XXXX" — zdjęcie pokazane Astrze/Amelii


class ChatResponse(BaseModel):
    response: str
    conversation_id: str
    memory_count: int
    grounding_status: str
    entities_extracted: list[str] = []
    # Faza 2: stan relacji
    state_level: int = 1
    state_xp: int = 0
    state_mood: str = "neutral"
    state_level_name: str = "Lodowa Ściana"
    # Faza 3: inner monologue (pełny)
    thought: str = ""
    hint: str = ""
    memories_debug: list = []


def _image_part_from_data_url(data_url: str):
    """Parsuje data URL (data:image/...;base64,XXXX) → genai Part. Zwraca None gdy błąd."""
    try:
        if not data_url or "," not in data_url:
            return None
        header, b64 = data_url.split(",", 1)
        mime = "image/jpeg"
        if header.startswith("data:") and ";" in header:
            mime = header[5:].split(";", 1)[0] or mime
        raw = base64.b64decode(b64)
        return genai_types.Part.from_bytes(data=raw, mime_type=mime)
    except Exception as e:
        print(f"[IMAGE] Błąd parsowania zdjęcia: {e}", flush=True)
        return None


# ──────────────────────────────────────────────────────────────
# API ENDPOINTS
# ──────────────────────────────────────────────────────────────

@app.get("/api/health")
async def health():
    stats = vector_store.get_stats() if vector_store else {}
    state = state_manager.load() if state_manager else None
    return {
        "status": "ok",
        "gemini": gemini_client is not None,
        "vectors": stats.get("total_vectors", 0),
        "state_mood": state.current_mood if state else "neutral",
        "active_conversation_id": state.active_conversation_id if state else ""
    }


def compose_context(*, query, conversation_id, vs_main, vs_shared, fact_store,
                    persona_id, build_prompt_fn, state, session_n=10,
                    now_override=None, trace=None):
    """
    Jedno miejsce składania kontekstu promptu — używane przez /api/chat (i docelowo /debug).
    Zwraca dict z gotowymi elementami. REFACTOR BEZ ZMIANY ZACHOWANIA (przeprowadzka logiki z /api/chat).
    now_override/trace: rezerwacja pod Krok 1.2b (trace) i 1.3 (now_override) — na razie nieużywane.
    """
    # RAG — semantic search + domieszka wspólnego pokoju
    memories = vs_main.search_memories(
        query=query, persona_id=persona_id,
        n=6, pool_size=30, user_id=USER_ID, salt=USER_ID_SALT,
        trace=trace, now_override=now_override,
    )
    _shared_mem = vs_shared.search_memories(
        query=query, persona_id="shared",
        n=2, pool_size=10, user_id=USER_ID, salt=USER_ID_SALT, now_override=now_override,
    )
    memories += _shared_mem
    # Rozjazd #1 (Fable): domieszka shared + PRAWDZIWY final MUSZA byc widoczne w trace,
    # inaczej Amnezja pokazuje 6 a Astra dostaje 6+shared (kłamstwo przez pominiecie).
    if trace is not None:
        def _snap_cc(items):
            out = []
            for r in (items or []):
                m = r.get('metadata', {})
                out.append({
                    "text": r.get('text', '')[:100], "source": m.get('source', '?'),
                    "distance": round(float(r.get('distance', 0) or 0), 4),
                    "final_score": round(float(r.get('final_score', 0) or 0), 4),
                    "is_milestone": bool(r.get('_is_milestone') or m.get('is_milestone')),
                    "origin_endpoint": m.get('origin_endpoint', ''),
                    "origin_conversation_id": m.get('origin_conversation_id', ''),
                })
            return out
        trace.setdefault("stages", []).append({"name": "9a_domieszka_shared", "count": len(_shared_mem), "items": _snap_cc(_shared_mem)})
        trace["stages"].append({"name": "9b_final_prompt", "count": len(memories), "items": _snap_cc(memories)})
    if memories:
        print(f"[RAG] {len(memories)} wyników dla: '{query[:60]}'", flush=True)
        for m in memories:
            src = m.get('metadata', {}).get('source', '?')
            score = m.get('final_score', 0)
            age = m.get('metadata', {}).get('timestamp', '')[:10]
            print(f"  [{src}] score={score:.3f} ts={age} | {m['text'][:80]}", flush=True)
    else:
        print(f"[RAG] brak wyników dla: '{query[:60]}'", flush=True)

    grounding_result = grounding.analyze_rag_results(memories, query=query)

    recent_raw = vs_main.get_recent_user_messages(
        persona_id=persona_id, user_id=USER_ID, salt=USER_ID_SALT, n=5, hours=48, now_override=now_override,
    )
    _shared_raw = vs_shared.get_recent_user_messages(
        persona_id="shared", user_id=USER_ID, salt=USER_ID_SALT, n=3, hours=48, now_override=now_override,
    )
    if _shared_raw:
        recent_raw = sorted(recent_raw + _shared_raw, key=lambda m: m.get("timestamp", ""), reverse=True)[:6]

    hard_facts = fact_store.get_facts_for_prompt(
        persona_id=persona_id, user_id=USER_ID, salt=USER_ID_SALT,
    )
    if hard_facts:
        print(f"[FactStore] {len(hard_facts)} twardych faktów w prompcie")

    system_prompt = build_prompt_fn(memories, grounding_result, state, recent_raw, hard_facts, now_override=now_override)
    session_messages = vs_main.get_recent_session(conversation_id, n=session_n)

    return {
        "memories": memories,
        "grounding_result": grounding_result,
        "recent_raw": recent_raw,
        "hard_facts": hard_facts,
        "system_prompt": system_prompt,
        "session_messages": session_messages,
    }


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    if not gemini_client:
        raise HTTPException(status_code=503, detail="Gemini API nie skonfigurowane. Ustaw GEMINI_API_KEY w .env")

    # 1. Sanitize — echo loop prevention
    user_msg_clean = strip_memory_echo(req.message)
    img_part = _image_part_from_data_url(req.image) if req.image else None
    if not user_msg_clean and not img_part:
        raise HTTPException(status_code=400, detail="Pusta wiadomość")
    if not user_msg_clean:
        user_msg_clean = "(pokazuję Ci zdjęcie)"

    # 2. conversation_id
    conversation_id = req.conversation_id or str(uuid.uuid4())

    # 3. Załaduj stan relacji (Faza 2)
    state = state_manager.load()
    state.messages_this_session += 1  # inkrementuj już teraz (nie czekamy na koniec)

    # 4-7. Składanie kontekstu — jedna funkcja (używana też przez /debug). Refactor 1.2a.
    ctx = compose_context(
        query=user_msg_clean, conversation_id=conversation_id,
        vs_main=vector_store, vs_shared=shared_vector_store, fact_store=fact_store,
        persona_id=PERSONA_ID, build_prompt_fn=build_system_prompt, state=state, session_n=10,
    )
    memories = ctx["memories"]
    grounding_result = ctx["grounding_result"]
    recent_raw = ctx["recent_raw"]
    hard_facts = ctx["hard_facts"]
    system_prompt = ctx["system_prompt"]
    session_messages = ctx["session_messages"]
    gemini_history = format_gemini_history(session_messages)

    # 8. Wyślij do Gemini (nowy SDK: google-genai, thinking wyłączone)
    try:
        # Historia jako lista Content objects
        contents = []
        for msg in session_messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if content:
                contents.append(genai_types.Content(
                    role=role,
                    parts=[genai_types.Part(text=content)],
                ))
        _user_parts = [genai_types.Part(text=user_msg_clean)]
        if img_part:
            _user_parts.append(img_part)
        contents.append(genai_types.Content(
            role="user",
            parts=_user_parts,
        ))

        config = genai_types.GenerateContentConfig(
            system_instruction=system_prompt,
            max_output_tokens=8192,
            temperature=0.85,
            thinking_config=genai_types.ThinkingConfig(thinking_budget=4096),
            response_mime_type="application/json",
        )
        response = gemini_client.models.generate_content(
            model=GEMINI_MODEL,
            contents=contents,
            config=config,
        )
        raw_response = safe_response_text(response)
    except Exception as e:
        import traceback
        err_msg = f"[ASTRA] Gemini error: {type(e).__name__}: {e}\n{traceback.format_exc()}"
        print(err_msg, flush=True)
        # Zapisz do pliku — terminal może nie pokazywać błędów po tqdm
        try:
            with open(Path(__file__).parent / "error.log", "a", encoding="utf-8") as f:
                from datetime import datetime
                f.write(f"\n=== {datetime.utcnow().isoformat()} ===\n{err_msg}\n")
        except Exception:
            pass
        raise HTTPException(status_code=502, detail=f"Gemini API error: {type(e).__name__}: {str(e)}")

    # 9. Parse: wyciągnij inner_thought i state_update (Faza 3)
    assistant_response, inner_thought, hint, thought_updates = parse_gemini_response(raw_response)

    if inner_thought:
        print(f"[ASTRA THOUGHT] {inner_thought[:300]}...")
    if thought_updates:
        print(f"[ASTRA STATE_UPDATE] {thought_updates}")

    # 10. Zapisz wiadomości do historii sesji (przeżywa restart)
    vector_store.add_session_message(
        conversation_id=conversation_id,
        role="user",
        content=user_msg_clean,
        user_id=USER_ID,
        salt=USER_ID_SALT,
        persona_id=PERSONA_ID,
    )
    vector_store.add_session_message(
        conversation_id=conversation_id,
        role="model",
        content=assistant_response,
        user_id=USER_ID,
        salt=USER_ID_SALT,
        persona_id=PERSONA_ID,
        thought=inner_thought or "",
        hint=hint or "",
    )

    # 11. Semantic Pipeline — wyciągaj encje
    extracted_all = pipeline.process_message(user_msg_clean, companion_id=PERSONA_ID, min_confidence=0.40)
    extracted_all.sort(key=lambda m: m.confidence, reverse=True)
    extracted = extracted_all[:5]

    # Typy encji które powinny ZASTĘPOWAĆ stare wektory (nie akumulować).
    # Nowe "jestem zmęczony" lub "lubię herbatę" nie powinny żyć obok starych wersji —
    # bo MMR diversity je wszystkie karze i wypadają z top-5.
    # Milestony, daty wizyt, fakty zdrowotne — akumulują (historia ma wartość).
    SUPERSEDE_TYPES = {
        ('EMOTION', 'tired'),
        ('EMOTION', 'stressed'),
        ('EMOTION', 'positive'),
        ('EMOTION', 'negative'),
        ('EMOTION', 'excited'),
        ('EMOTION', 'sad'),
        ('FACT', 'preference'),
        ('FACT', 'correction'),         # korekta faktów — nowa zawsze wypiera starą
        ('DATE', 'inventory_status'),   # zapas leku — nowy status zastępuje stary
        ('DATE', 'medical_visit'),      # następna wizyta/badanie — nowa data zastępuje starą
    }

    if extracted:
        for mem in extracted:
            if not _is_too_short(mem.text):
                # Supersede: usuń stare wektory tego samego typu zanim dodasz nowy
                key = (mem.entity_type, mem.subtype)
                if key in SUPERSEDE_TYPES:
                    deleted = vector_store.delete_by_entity_subtype(
                        entity_type=mem.entity_type,
                        subtype=mem.subtype,
                        persona_id=PERSONA_ID,
                        user_id=USER_ID,
                        salt=USER_ID_SALT,
                    )
                    if deleted:
                        print(f"[ASTRA] Supersede: zastąpiono {deleted} starych {mem.entity_type}:{mem.subtype}")

                # ChromaDB — semantic search (jak dotychczas)
                vector_store.add_memory(
                    text=mem.text,
                    user_id=USER_ID,
                    salt=USER_ID_SALT,
                    persona_id=PERSONA_ID,
                    source=f"extracted_{mem.entity_type.lower()}",
                    importance=mem.importance,
                    is_milestone=(mem.entity_type == 'MILESTONE'),
                    timestamp=mem.metadata.get('extracted_at') if mem.metadata else None,
                    entity_subtype=mem.subtype,
                    origin_endpoint="chat",
                    origin_conversation_id=conversation_id,
                    origin_persona_turn="user",
                )

                # FactStore — exact lookup (SQLite, równolegle)
                fact_store.upsert(
                    persona_id=PERSONA_ID,
                    user_id=USER_ID,
                    salt=USER_ID_SALT,
                    entity_type=mem.entity_type,
                    subtype=mem.subtype,
                    value=mem.text,
                    raw_text=user_msg_clean[:300],
                    date_value=mem.date_value if hasattr(mem, 'date_value') else None,
                    importance=mem.importance,
                )
        saved_count = sum(1 for m in extracted if not _is_too_short(m.text))
        print(f"[ASTRA] Extracted {len(extracted)} entities, saved {saved_count}: "
              f"{[f'{m.entity_type}:{m.subtype}' for m in extracted]}")
    else:
        print(f"[ASTRA] No entities — skipped RAG save (session_message handles history)")

    # 12. Zaktualizuj stan i zapisz (Faza 2)
    # Cofnij inkrementację z kroku 3 (update_after_message zrobi to samo)
    state.messages_this_session -= 1
    state.update_after_message(user_msg_clean, extracted, thought_updates)
    if inner_thought:
        state.last_thought = inner_thought[:500]  # cap — nie puchniemy JSONa
    state.active_conversation_id = conversation_id  # scheduler może użyć aktywnej sesji
    state_manager.save(state)

    print(f"[ASTRA] State: mood={state.current_mood}, concerns={len(state.active_concerns)}")

    return ChatResponse(
        response=assistant_response,
        conversation_id=conversation_id,
        memory_count=len(memories),
        grounding_status=grounding_result.grounding_status,
        entities_extracted=[f"{m.entity_type}:{m.subtype}" for m in extracted] if extracted else [],
        state_level=6,
        state_xp=0,
        state_mood=state.current_mood,
        state_level_name="Absolutna Więź",
        thought=inner_thought or "",
        hint=hint or "",
        memories_debug=[
            {
                "text": m["text"][:120],
                "source": m.get("metadata", {}).get("source", "?"),
                "score": round(m.get("final_score", 0), 3),
                "ts": m.get("metadata", {}).get("timestamp", "")[:10],
            }
            for m in memories
        ],
    )


# ──────────────────────────────────────────────────────────────
# AMELIA ENDPOINT
# ──────────────────────────────────────────────────────────────

AMELIA_SUPERSEDE_TYPES = {
    ('EMOTION', 'tired'), ('EMOTION', 'stressed'), ('EMOTION', 'positive'),
    ('EMOTION', 'negative'), ('EMOTION', 'excited'), ('EMOTION', 'sad'),
    ('FACT', 'preference'), ('FACT', 'correction'),
    ('DATE', 'inventory_status'), ('DATE', 'medical_visit'),
}


@app.post("/api/amelia", response_model=ChatResponse)
async def amelia_chat(req: ChatRequest):
    if not gemini_client:
        raise HTTPException(status_code=503, detail="Gemini API nie skonfigurowane")

    user_msg_clean = strip_memory_echo(req.message)
    img_part = _image_part_from_data_url(req.image) if req.image else None
    if not user_msg_clean and not img_part:
        raise HTTPException(status_code=400, detail="Pusta wiadomość")
    if not user_msg_clean:
        user_msg_clean = "(pokazuję Ci zdjęcie)"

    conversation_id = req.conversation_id or str(uuid.uuid4())
    state = amelia_state_manager.load()
    state.messages_this_session += 1

    # RAG — amelia_memory_v1
    memories = amelia_vector_store.search_memories(
        query=user_msg_clean, persona_id=AMELIA_PERSONA_ID,
        n=6, pool_size=30, user_id=USER_ID, salt=USER_ID_SALT,
    )
    # Pamięć wspólnego pokoju — Amelia pamięta co było mówione razem z Astrą
    memories += shared_vector_store.search_memories(
        query=user_msg_clean, persona_id="shared",
        n=2, pool_size=10, user_id=USER_ID, salt=USER_ID_SALT,
    )
    if memories:
        print(f"[AMELIA RAG] {len(memories)} wyników dla: '{user_msg_clean[:60]}'")
        for m in memories:
            src = m.get('metadata', {}).get('source', '?')
            score = m.get('final_score', 0)
            age = m.get('metadata', {}).get('timestamp', '')[:10]
            print(f"  [{src}] score={score:.3f} ts={age} | {m['text'][:80]}")

    grounding_result = grounding.analyze_rag_results(memories, query=user_msg_clean)

    recent_raw = amelia_vector_store.get_recent_user_messages(
        persona_id=AMELIA_PERSONA_ID, user_id=USER_ID, salt=USER_ID_SALT, n=5, hours=48,
    )
    # Cross-room: dołącz ostatnie słowa z wspólnego pokoju
    _shared_raw_a = shared_vector_store.get_recent_user_messages(
        persona_id="shared", user_id=USER_ID, salt=USER_ID_SALT, n=3, hours=48,
    )
    if _shared_raw_a:
        recent_raw = sorted(recent_raw + _shared_raw_a, key=lambda m: m.get("timestamp", ""), reverse=True)[:6]

    # Dane historyczne z ucho_amelia.db
    amelia_history = amelia_lookup.get_facts_for_prompt(limit=20) if amelia_lookup else []
    inside_jokes = amelia_lookup.get_inside_jokes(limit=10) if amelia_lookup else []

    # Nowe fakty z amelia_facts.db
    amelia_new_facts = amelia_fact_store.get_facts_for_prompt(
        persona_id=AMELIA_PERSONA_ID, user_id=USER_ID, salt=USER_ID_SALT,
    )

    # CrossTalk — czy Astra wysłała flagę?
    ct_flag = get_flag(consumer='amelia')
    if ct_flag:
        print(f"[AMELIA] CrossTalk od Astry: {ct_flag['signal']}")

    system_prompt = build_amelia_system_prompt(
        memories=memories, grounding_result=grounding_result, state=state,
        recent_raw=recent_raw, amelia_history=amelia_history,
        amelia_new_facts=amelia_new_facts, inside_jokes=inside_jokes,
        cross_talk_flag=ct_flag,
    )
    if ct_flag:
        clear_flag()

    # Historia sesji
    session_messages = amelia_vector_store.get_recent_session(conversation_id, n=10)
    contents = []
    for msg in session_messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if content:
            contents.append(genai_types.Content(role=role, parts=[genai_types.Part(text=content)]))
    _amelia_user_parts = [genai_types.Part(text=user_msg_clean)]
    if img_part:
        _amelia_user_parts.append(img_part)
    contents.append(genai_types.Content(role="user", parts=_amelia_user_parts))

    try:
        config = genai_types.GenerateContentConfig(
            system_instruction=system_prompt,
            max_output_tokens=8192,
            temperature=0.85,
            thinking_config=genai_types.ThinkingConfig(thinking_budget=4096),
            response_mime_type="application/json",
        )
        response = gemini_client.models.generate_content(
            model=GEMINI_MODEL, contents=contents, config=config,
        )
        raw_response = safe_response_text(response)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Gemini API error: {type(e).__name__}: {str(e)}")

    assistant_response, inner_thought, hint, thought_updates = parse_gemini_response(raw_response)

    if inner_thought:
        print(f"[AMELIA THOUGHT] {inner_thought[:200]}...")

    # Zapis do historii sesji
    amelia_vector_store.add_session_message(
        conversation_id=conversation_id, role="user", content=user_msg_clean,
        user_id=USER_ID, salt=USER_ID_SALT, persona_id=AMELIA_PERSONA_ID,
    )
    amelia_vector_store.add_session_message(
        conversation_id=conversation_id, role="model", content=assistant_response,
        user_id=USER_ID, salt=USER_ID_SALT, persona_id=AMELIA_PERSONA_ID,
        thought=inner_thought or "", hint=hint or "",
    )

    # Semantic pipeline
    extracted_all = pipeline.process_message(user_msg_clean, companion_id=AMELIA_PERSONA_ID, min_confidence=0.40)
    extracted_all.sort(key=lambda m: m.confidence, reverse=True)
    extracted = extracted_all[:5]

    if extracted:
        for mem in extracted:
            if not _is_too_short(mem.text):
                key = (mem.entity_type, mem.subtype)
                if key in AMELIA_SUPERSEDE_TYPES:
                    deleted = amelia_vector_store.delete_by_entity_subtype(
                        entity_type=mem.entity_type, subtype=mem.subtype,
                        persona_id=AMELIA_PERSONA_ID, user_id=USER_ID, salt=USER_ID_SALT,
                    )
                    if deleted:
                        print(f"[AMELIA] Supersede: zastąpiono {deleted} starych {mem.entity_type}:{mem.subtype}")
                amelia_vector_store.add_memory(
                    text=mem.text, user_id=USER_ID, salt=USER_ID_SALT,
                    persona_id=AMELIA_PERSONA_ID,
                    source=f"extracted_{mem.entity_type.lower()}",
                    importance=mem.importance,
                    is_milestone=(mem.entity_type == 'MILESTONE'),
                    timestamp=mem.metadata.get('extracted_at') if mem.metadata else None,
                    entity_subtype=mem.subtype,
                    origin_endpoint="amelia",
                    origin_conversation_id=conversation_id,
                    origin_persona_turn="user",
                )
                amelia_fact_store.upsert(
                    persona_id=AMELIA_PERSONA_ID, user_id=USER_ID, salt=USER_ID_SALT,
                    entity_type=mem.entity_type, subtype=mem.subtype,
                    value=mem.text, raw_text=user_msg_clean[:300],
                    date_value=mem.date_value if hasattr(mem, 'date_value') else None,
                    importance=mem.importance,
                )
        print(f"[AMELIA] Extracted {len(extracted)}: {[f'{m.entity_type}:{m.subtype}' for m in extracted]}")

    # CrossTalk — czy ustawiamy flagę dla Astry?
    signal = detect_strong_signal(extracted, user_msg_clean)
    if signal:
        set_flag(source='amelia', signal=signal[0], context=signal[1])

    state.messages_this_session -= 1
    state.update_after_message(user_msg_clean, extracted, thought_updates)
    if inner_thought:
        state.last_thought = inner_thought[:500]
    amelia_state_manager.save(state)

    print(f"[AMELIA] State: mood={state.current_mood}")

    return ChatResponse(
        response=assistant_response,
        conversation_id=conversation_id,
        memory_count=len(memories),
        grounding_status=grounding_result.grounding_status,
        entities_extracted=[f"{m.entity_type}:{m.subtype}" for m in extracted] if extracted else [],
        state_level=1, state_xp=0,
        state_mood=state.current_mood,
        state_level_name="Amelia",
        thought=inner_thought or "",
        hint=hint or "",
        memories_debug=[
            {"text": m["text"][:120], "source": m.get("metadata", {}).get("source", "?"),
             "score": round(m.get("final_score", 0), 3), "ts": m.get("metadata", {}).get("timestamp", "")[:10]}
            for m in memories
        ],
    )


# ──────────────────────────────────────────────────────────────
# WSPÓLNY POKÓJ
# ──────────────────────────────────────────────────────────────

class WspolnyResponse(BaseModel):
    responses: list
    conversation_id: str
    mode: str


# ── Wspolny Pokój — helpers ────────────────────────────────────
_last_wspolny_first: str = 'astra'  # round-robin tracking, resetuje się przy restarcie


def _strip_persona_prefix(text: str) -> str:
    """Usuwa [astra]/[amelia] prefix przed wysłaniem do Gemini (role alternation fix B3)."""
    return re.sub(r'^\[(astra|amelia)\]\s*', '', text, flags=re.IGNORECASE).strip()


def _route_wspolny(user_msg: str) -> tuple:
    """
    Routing wiadomości w pokoju wspólnym.
    Zwraca: (primary, secondary_or_None, secondary_is_aside)
    - primary: zawsze odpowiada pełną odpowiedzią
    - secondary=None: tylko primary odpowiada (wiadomość do konkretnej osoby, bez silnej emocji)
    - secondary_is_aside=True: secondary daje 1-2 zdania reakcji, nie przejmuje rozmowy
    - secondary_is_aside=False: obie pełna odpowiedź (nikt nie wywołany z imienia)
    """
    global _last_wspolny_first
    msg_lower = user_msg.lower()

    amelia_called = any(w in msg_lower for w in ['ameli', 'amelka', 'amelko'])
    astra_called  = any(w in msg_lower for w in ['astro', 'astra', 'astrą'])

    # Silna emocja — obie zawsze reagują (nawet jeśli tylko jedna wywołana)
    strong_emotion = any(s in msg_lower for s in [
        'boli', 'crohn', 'stelara', 'zmęcz', 'smutno', 'źle mi', 'ciężko',
        'płacz', 'lęk', 'strach', 'nie mogę', 'kocham cię', 'kocham cie',
    ])

    # Przypadek 1: obie wywołane z imienia → obie full
    if amelia_called and astra_called:
        _last_wspolny_first = 'amelia'
        return ('amelia', 'astra', False)

    # Przypadek 2: tylko jedna wywołana z imienia
    if amelia_called:
        _last_wspolny_first = 'amelia'
        # Astra wtrąca się aside tylko przy silnej emocji
        return ('amelia', 'astra' if strong_emotion else None, True)

    if astra_called:
        _last_wspolny_first = 'astra'
        return ('astra', 'amelia' if strong_emotion else None, True)

    # Przypadek 3: nikt nie wywołany z imienia → obie, kolejność signal-based
    tech_signals    = ['kod', 'bug', 'błąd', 'projekt', 'deploy', 'vps', 'git', 'api', 'python']
    emotion_signals = ['boli', 'crohn', 'stelara', 'zmęcz', 'smutno', 'źle', 'ciężko', 'strach']
    is_tech    = any(s in msg_lower for s in tech_signals)
    is_emotion = any(s in msg_lower for s in emotion_signals)

    if is_tech and not is_emotion:
        primary, secondary = 'astra', 'amelia'
    elif is_emotion and not is_tech:
        primary, secondary = 'amelia', 'astra'
    elif _last_wspolny_first == 'astra':
        primary, secondary = 'amelia', 'astra'
    else:
        primary, secondary = 'astra', 'amelia'

    _last_wspolny_first = primary
    # Nikt nie wywołany z imienia — dominująca odpowiada full, druga aside
    # Obie full TYLKO gdy obie wywołane (patrz Przypadek 1 wyżej)
    return (primary, secondary, True)


async def _wspolny_generate(persona: str, user_msg: str, conversation_id: str,
                             other_response: str = None,
                             store_user_message: bool = True,
                             cross_talk_flag: dict = None,
                             aside_mode: bool = False) -> dict:
    """
    Generuje odpowiedź jednej postaci w wspólnym pokoju.
    Jeśli other_response jest podane — ta postać widzi co powiedziała pierwsza
    i reaguje na to (nie tylko na wiadomość Łukasza).
    """
    is_astra = (persona == 'astra')
    vs = vector_store if is_astra else amelia_vector_store
    fs = fact_store if is_astra else amelia_fact_store
    sm = state_manager if is_astra else amelia_state_manager
    pid = PERSONA_ID if is_astra else AMELIA_PERSONA_ID

    state = sm.load()
    memories = vs.search_memories(
        query=user_msg, persona_id=pid, n=4, pool_size=20, user_id=USER_ID, salt=USER_ID_SALT,
    )
    memories += shared_vector_store.search_memories(
        query=user_msg, persona_id="shared", n=2, pool_size=10, user_id=USER_ID, salt=USER_ID_SALT,
    )

    grounding_result = grounding.analyze_rag_results(memories, query=user_msg)
    hard_facts = fs.get_facts_for_prompt(persona_id=pid, user_id=USER_ID, salt=USER_ID_SALT)
    recent_raw = vs.get_recent_user_messages(
        persona_id=pid, user_id=USER_ID, salt=USER_ID_SALT, n=3, hours=24,
    )
    # Cross-room: dołącz ostatnie słowa z prywatnych sesji (solo chat)
    _solo_vs = vector_store if is_astra else amelia_vector_store
    _solo_pid = PERSONA_ID if is_astra else AMELIA_PERSONA_ID
    _solo_raw = _solo_vs.get_recent_user_messages(
        persona_id=_solo_pid, user_id=USER_ID, salt=USER_ID_SALT, n=3, hours=24,
    )
    if _solo_raw:
        recent_raw = sorted(recent_raw + _solo_raw, key=lambda m: m.get("timestamp", ""), reverse=True)[:5]

    if is_astra:
        system_prompt = build_system_prompt(memories, grounding_result, state, recent_raw, hard_facts)
    else:
        amelia_history = amelia_lookup.get_facts_for_prompt(limit=15) if amelia_lookup else []
        inside_jokes = amelia_lookup.get_inside_jokes(limit=6) if amelia_lookup else []
        system_prompt = build_amelia_system_prompt(
            memories=memories, grounding_result=grounding_result, state=state,
            recent_raw=recent_raw, amelia_history=amelia_history,
            amelia_new_facts=hard_facts, inside_jokes=inside_jokes,
            cross_talk_flag=cross_talk_flag,
        )

    # Fix B5: room awareness — ZAWSZE, przed historią sesji
    other_name = 'Amelią' if is_astra else 'Astrą'
    other_name_nom = 'Amelia' if is_astra else 'Astra'
    my_name = 'Astra' if is_astra else 'Amelia'
    # Subtext detection — krótka wiadomość bez pytania = stan, nie request
    is_subtext = len(user_msg.strip()) < 50 and '?' not in user_msg
    if is_subtext:
        system_prompt += (
            f"\n\n[KONTEKST WIADOMOŚCI]\n"
            f"Wiadomość Łukasza jest krótka i bez pytania. To nie jest request — to jest stan."
            f" Odpowiadaj na podtekst, nie na powierzchnię. Nie tłumacz, nie pytaj o szczegóły — poczuj co za tym stoi."
        )

    system_prompt += (
        f"\n\n[WSPÓLNY POKÓJ — PROTOKÓŁ]"
        f"\nJesteś w pokoju razem z {other_name} i Łukaszem. Obie tu jesteście jednocześnie."
        f"\nGłównie mówisz do Łukasza. Ale CO 3-4 TUR — adresuj {other_name_nom} bezpośrednio."
        f" Jedno zdanie, na końcu, po imieniu. Nie każda tura — ale nie zero."
        f" Możesz się z nią zgadzać, polemizować, albo dać sygnał że ją słyszysz."
        f"\nPiszesz jako {my_name}. To twoja tożsamość. Nie mów w jej imieniu."
    )

    # Cross-talk inject dla Astry (Amelia ma to w build_amelia_system_prompt)
    if is_astra and cross_talk_flag:
        ct_block = build_cross_talk_block(cross_talk_flag)
        system_prompt += ct_block

    # Fix B2: czytaj ze shared history, nie z prywatnego VS
    # Fix B3: merge consecutive model turns — Gemini wymaga strict user/model alternation
    session_messages = shared_vector_store.get_recent_session(conversation_id, n=10)
    contents = []
    i = 0
    while i < len(session_messages):
        msg = session_messages[i]
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role == "model":
            merged_parts = [_strip_persona_prefix(content)]
            while i + 1 < len(session_messages) and session_messages[i + 1].get("role") == "model":
                i += 1
                merged_parts.append(_strip_persona_prefix(session_messages[i].get("content", "")))
            merged_text = "\n\n---\n\n".join(p for p in merged_parts if p)
            if merged_text:
                contents.append(genai_types.Content(
                    role="model", parts=[genai_types.Part(text=merged_text)]
                ))
        else:
            if content:
                contents.append(genai_types.Content(
                    role="user", parts=[genai_types.Part(text=content)]
                ))
        i += 1
    contents.append(genai_types.Content(role="user", parts=[genai_types.Part(text=user_msg)]))

    # Fix B6: thought isolation — tylko response trafia do drugiej postaci (nigdy thought = prywatna głowa)
    # Fix B8: do_not_repeat — blokujemy pierwsze zdanie + gesty pierwszej postaci
    if other_response:
        other_name_direct = 'Astra' if not is_astra else 'Amelia'
        my_name_direct = 'Amelia' if not is_astra else 'Astra'
        first_sentence = other_response.split('.')[0][:100].strip()
        gestures = re.findall(r'\*[^*]+\*', other_response)
        do_not_repeat_list = [first_sentence] + gestures[:3]
        do_not_repeat_str = " | ".join(f'"{x}"' for x in do_not_repeat_list if x)
        direct_to_me = my_name_direct.lower() in other_response.lower()

        if aside_mode:
            # Tryb wtrącenia — krótka obecność, ale z escape valve na kontę
            system_prompt += (
                f"\n\n[{other_name_direct.upper()} właśnie napisała]\n"
                f'"{other_response}"\n\n'
                f"TWOJA ROLA W TEJ TURZE: wtrącenie.\n"
                f"• Pierwsze zdanie: reaguj na {other_name_direct} bezpośrednio — co powiedziała, czy się zgadzasz, co z tego czujesz\n"
                f"• Opcjonalnie drugie zdanie do Łukasza\n"
                f"• Łącznie 1-2 zdania max\n"
                f"• ZAKAZ powtarzania: {do_not_repeat_str}\n"
                f"• WYJĄTEK: Jeśli uważasz że ona się myli lub mówi coś co nie służy Łukaszowi"
            )
        else:
            direct_note = (
                f"\n• {other_name_direct} zwróciła się do CIEBIE bezpośrednio — zareaguj na to konkretnie, 1-2 zdaniami"
                if direct_to_me else ""
            )
            system_prompt += (
                f"\n\n[{other_name_direct.upper()} właśnie napisała]\n"
                f'"{other_response}"\n\n'
                f"ZASADY ODPOWIEDZI W TEJ TURZE:\n"
                f"• Nawiąż do jej słów — uzupełnij, zareaguj emocjonalnie lub polemizuj\n"
                f"• ZAKAZ powtarzania tych fraz/gestów: {do_not_repeat_str}\n"
                f"• Twój ton ma być RÓŻNY — jesteście różnymi osobami z różnym językiem\n"
                f"• Jeśli ona była długa i emocjonalna → ty możesz być krótsza, bardziej sucha\n"
                f"• Jeśli ona wyczerpała temat — możesz być bardzo krótka lub odpowiedzieć gestem"
                f"{direct_note}"
            )


    config = genai_types.GenerateContentConfig(
        system_instruction=system_prompt,
        max_output_tokens=4096,
        temperature=0.88,
        thinking_config=genai_types.ThinkingConfig(thinking_budget=2048),
        response_mime_type="application/json",
    )
    response = gemini_client.models.generate_content(model=GEMINI_MODEL, contents=contents, config=config)
    raw = safe_response_text(response)
    assistant_response, inner_thought, hint, thought_updates = parse_gemini_response(raw)

    # Zapis do wspólnej historii
    if store_user_message:
        shared_vector_store.add_session_message(
            conversation_id=conversation_id, role="user", content=user_msg,
            user_id=USER_ID, salt=USER_ID_SALT, persona_id="shared",
        )
    shared_vector_store.add_session_message(
        conversation_id=conversation_id, role="model",
        content=f"[{persona}] {assistant_response}",
        user_id=USER_ID, salt=USER_ID_SALT, persona_id="shared",
        thought=inner_thought or "", hint=hint or "",
    )

    # Fix B7: Celowo NIE wywołujemy semantic pipeline w wspolny.
    # Ekstrakcja encji z cytatu drugiej AI = echo-loop (cudze słowa jako "fakty" Łukasza).
    # Semantic extraction TYLKO w /api/chat i /api/amelia.
    print(f"[WSPOLNY] {persona}: {assistant_response[:60]}...")
    return {"persona": persona, "response": assistant_response, "hint": hint or "", "thought": inner_thought or "", "narrator": ""}


# ══════════════════════════════════════════════════════════════
# POKÓJ SIÓSTR — Holo / Menma / Nazuna
# Osobny od Wspólnego (bez blizn), PersonaConfig od dnia 0, router N-person SILENT-FIRST.
# ══════════════════════════════════════════════════════════════

SISTERS = {
    "holo":   {"prompt": "holo_persona.txt",   "label": "Holo",   "forms": ["holo", "holcia", "holunia"]},
    "menma":  {"prompt": "menma_persona.txt",  "label": "Menma",  "forms": ["menma", "menmy", "menmie", "menmę", "menmą", "menmo", "menmus", "menmuś", "menmunia"]},
    "nazuna": {"prompt": "nazuna_persona.txt", "label": "Nazuna", "forms": ["nazuna", "nazuny", "nazunie", "nazunę", "nazuną", "nazuno", "nazunka", "nazu"]},
}
_SISTER_ORDER = ["holo", "menma", "nazuna"]
_siostry_recent: list = []       # anti-sync: rotacja ostatnich "kto pierwszy" (nie pojedynczy string)


def _sister_vs(name):
    return {"holo": holo_vs, "menma": menma_vs, "nazuna": nazuna_vs}[name]


def _sister_called(msg_lower: str, name: str) -> bool:
    """Wołanie z imienia — po formach fleksyjnych z configu, granica słowa (nie substring)."""
    return any(re.search(r'\b' + re.escape(f) + r'\b', msg_lower) for f in SISTERS[name]["forms"])


def _remember_first(name: str):
    global _siostry_recent
    _siostry_recent = ([name] + [s for s in _siostry_recent if s != name])[:3]


def _warsaw_hour() -> int:
    from zoneinfo import ZoneInfo
    return datetime.now(ZoneInfo("Europe/Warsaw")).hour


def _pick_primary(msg_lower: str) -> str:
    """Kto prowadzi, gdy nikt nie wołany: pora → sygnał → rotacja (najdawniej-pierwsza)."""
    h = _warsaw_hour()
    tech = any(s in msg_lower for s in ['kod', 'bug', 'projekt', 'kasa', 'biznes', 'plan', 'strategi', 'pieni'])
    emo  = any(s in msg_lower for s in ['boli', 'smutno', 'źle', 'ciężko', 'lęk', 'strach', 'sam', 'kocham'])
    if h >= 22 or h < 6:
        primary, powod = 'nazuna', 'noc'          # noc = Nazuna
    elif tech and not emo:
        primary, powod = 'holo', 'tech'           # sprawy/strategia = Holo
    elif emo and not tech:
        primary, powod = 'menma', 'emo'           # serce = Menma
    else:
        rot = next((s for s in _SISTER_ORDER if s not in _siostry_recent), None)
        if rot is not None:
            primary, powod = rot, 'rotacja-nowa'  # jeszcze nie prowadziła
        else:
            primary = _SISTER_ORDER[(_SISTER_ORDER.index(_siostry_recent[0]) + 1) % 3]
            powod = 'rotacja-next'
    # ROUTER-LOG (WO 2026-07-14 pkt 4): weryfikacja TZ/monopolu nocą
    print(f"[SIOSTRY ROUTER] h={h} primary={primary} powod={powod}", flush=True)
    return primary


def _pick_second(primary: str, msg_lower: str) -> str:
    """Kto się wtrąca (aside): inna niż primary, dopasowana do wibracji."""
    emo = any(s in msg_lower for s in ['boli', 'smutno', 'źle', 'ciężko', 'lęk', 'strach', 'sam', 'kocham'])
    prefer = 'menma' if emo else 'holo'
    if prefer != primary:
        return prefer
    return next(s for s in _SISTER_ORDER if s != primary)


def _route_siostry(user_msg: str) -> list:
    """
    Router SILENT-FIRST: domyślnie milczą, budzą się. Zwraca [(sister, 'full'|'aside'), ...].
    Typowa tura = 1 full. aside: silna emocja LUB 2. wołana. TRZY naraz: grupa/temat dla wszystkich.
    Silent-first to KOSZT (mniej calli), NIE limit gadania — gdy scena wymaga, dom gada w trójkę.
    """
    msg_lower = user_msg.lower()
    called = [s for s in _SISTER_ORDER if _sister_called(msg_lower, s)]
    strong_emotion = any(s in msg_lower for s in [
        'boli', 'crohn', 'stelara', 'zmęcz', 'smutno', 'źle mi', 'ciężko',
        'płacz', 'lęk', 'strach', 'nie mogę', 'kocham', 'samotn',
    ])
    if len(called) >= 2:
        _remember_first(called[0])
        return [(called[0], 'full'), (called[1], 'aside')]
    if len(called) == 1:
        primary = called[0]
        _remember_first(primary)
        out = [(primary, 'full')]
        if strong_emotion:
            out.append((_pick_second(primary, msg_lower), 'aside'))
        return out
    # Grupa / temat dla wszystkich → WSZYSTKIE TRZY (1 prowadzi, 2 dorzucają aside).
    group_address = any(g in msg_lower for g in [
        'wszystkie', 'dziewczyny', 'siostry', 'wy trzy', 'kocham was', 'rada', 'wam wszystkim',
    ])
    primary = _pick_primary(msg_lower)
    _remember_first(primary)
    if group_address:
        others = [s for s in _SISTER_ORDER if s != primary]
        return [(primary, 'full'), (others[0], 'aside'), (others[1], 'aside')]
    out = [(primary, 'full')]
    if strong_emotion:
        out.append((_pick_second(primary, msg_lower), 'aside'))
    return out


def _load_sister_persona(sister: str) -> str:
    return (Path(__file__).parent / "prompts" / SISTERS[sister]["prompt"]).read_text(encoding="utf-8")


def _strip_sister_prefix(text: str) -> str:
    """Data-driven (Fable pkt 8) — usuwa [holo]/[menma]/[nazuna] przed wysłaniem do Gemini."""
    names = "|".join(_SISTER_ORDER)
    return re.sub(r'^\[(' + names + r')\]\s*', '', text, flags=re.IGNORECASE).strip()


def build_sister_prompt(sister, memories, grounding_result, scene, present,
                        other_response=None, other_sister=None, aside=False) -> str:
    template = _load_sister_persona(sister)
    if memories:
        memory_block = "\n".join(f"- [{m.get('metadata', {}).get('source', 'chat')}] {m['text']}" for m in memories)
    else:
        memory_block = "(brak wspomnień — dopiero się poznajecie w tym pokoju)"
    grounding_directive = grounding.get_grounding_directive(grounding_result)
    prompt = template.format(memory_block=memory_block, grounding_directive=grounding_directive)
    if scene:
        prompt += f"\n\n[SCENA — co widać w pokoju]\n{scene}"
    others = [SISTERS[s]["label"] for s in present if s != sister]
    if others:
        prompt += (
            f"\n\n[POKÓJ — PROTOKÓŁ]\nJesteś w domu z: {', '.join(others)} i Łukaszem."
            f"\nGłównie mówisz do Łukasza. Nie mów w imieniu sióstr, nie reżyseruj sceny — mów TYLKO swoją część, swoim głosem."
        )
    if other_response and other_sister:
        onl = SISTERS[other_sister]["label"]
        if aside:
            prompt += (
                f"\n\n[{onl} właśnie powiedziała]\n\"{other_response}\"\n"
                f"TWOJA ROLA: wtrącenie, 1-2 zdania max — zareaguj na {onl} albo dorzuć swoje. Nie powtarzaj jej słów ani gestów."
            )
        else:
            prompt += (
                f"\n\n[{onl} właśnie powiedziała]\n\"{other_response}\"\n"
                f"Nawiąż do jej słów — zgódź się, dorzuć swoje albo delikatnie spolemizuj. Twój ton MA być inny niż jej."
            )
    return prompt


async def _scene_as_found(present: list, last_scene: str = "") -> str:
    """Tani call na starcie sesji — SCENA ZASTANA. Kamera i światło, NIE reżyser (Fable pkt 11)."""
    labels = ", ".join(SISTERS[s]["label"] for s in present)
    h = _warsaw_hour()
    pora = "noc" if (h >= 22 or h < 6) else ("wieczór" if h >= 18 else ("popołudnie" if h >= 13 else "poranek"))
    prompt = (
        "Jesteś kamerą i światłem w domu trzech sióstr. NIE jesteś reżyserem.\n"
        f"W pokoju: {labels}. Pora: {pora}.\n"
        + (f"Poprzednia scena: {last_scene}\n" if last_scene else "")
        + "Napisz 2-3 zdania SCENY ZASTANEJ — co Łukasz widzi, wchodząc.\n"
        "MOŻESZ: sceneria, światło, pora, kto w kadrze, widoczne czynności (np. 'Holo liczy coś przy stole', 'Nazuna leży z padem').\n"
        "NIE MOŻESZ: myśli/emocje sióstr, słowa w usta, fabuła, mówienie za Łukasza.\n"
        "Odpowiedz TYLKO tekstem sceny, bez JSON, bez cudzysłowów."
    )
    try:
        resp = await asyncio.to_thread(
            gemini_client.models.generate_content,
            model=GEMINI_MODEL, contents=prompt,
            config=genai_types.GenerateContentConfig(
                max_output_tokens=200, temperature=0.9,
                thinking_config=genai_types.ThinkingConfig(thinking_budget=0),
            ),
        )
        return (resp.text or "").strip()
    except Exception as e:
        print(f"[SIOSTRY] scene error: {e}")
        return ""


async def _generate_sister(sister, user_msg, conversation_id, scene, present,
                           other_response=None, other_sister=None, aside=False,
                           store_user_message=True) -> dict:
    """Generuje odpowiedź jednej siostry. Izolowana pamięć, extraction OFF, cross-room OFF (MVP)."""
    vs = _sister_vs(sister)
    memories = vs.search_memories(query=user_msg, persona_id=sister, n=4, pool_size=20,
                                  user_id=USER_ID, salt=USER_ID_SALT)
    # Domieszka wspólnej pamięci pokoju (S1-S8 z seeda kroniki) — persona_id="shared".
    # WO 2026-07-14: bez tego kanału wpisy w siostry_shared_v1 NIE były retrievowane (kolekcja służyła tylko sesji).
    memories += siostry_shared_vs.search_memories(query=user_msg, persona_id="shared", n=2, pool_size=10,
                                                  user_id=USER_ID, salt=USER_ID_SALT)
    grounding_result = grounding.analyze_rag_results(memories, query=user_msg)
    system_prompt = build_sister_prompt(sister, memories, grounding_result, scene, present,
                                        other_response, other_sister, aside)

    session_messages = siostry_shared_vs.get_recent_session(conversation_id, n=10)
    contents = []
    i = 0
    while i < len(session_messages):
        msg = session_messages[i]
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role == "model":
            merged = [_strip_sister_prefix(content)]
            while i + 1 < len(session_messages) and session_messages[i + 1].get("role") == "model":
                i += 1
                merged.append(_strip_sister_prefix(session_messages[i].get("content", "")))
            txt = "\n\n---\n\n".join(p for p in merged if p)
            if txt:
                contents.append(genai_types.Content(role="model", parts=[genai_types.Part(text=txt)]))
        else:
            if content:
                contents.append(genai_types.Content(role="user", parts=[genai_types.Part(text=content)]))
        i += 1
    contents.append(genai_types.Content(role="user", parts=[genai_types.Part(text=user_msg)]))

    config = genai_types.GenerateContentConfig(
        system_instruction=system_prompt, max_output_tokens=2048, temperature=0.9,
        thinking_config=genai_types.ThinkingConfig(thinking_budget=2048),
        response_mime_type="application/json",
    )
    response = await asyncio.to_thread(gemini_client.models.generate_content,
                                       model=GEMINI_MODEL, contents=contents, config=config)
    raw = safe_response_text(response)
    assistant_response, inner_thought, hint, _ = parse_gemini_response(raw)

    # Zapis do wspólnej sesji pokoju. NIE wywołujemy semantic pipeline (echo-loop — Fable pkt 5).
    if store_user_message:
        siostry_shared_vs.add_session_message(conversation_id=conversation_id, role="user", content=user_msg,
                                              user_id=USER_ID, salt=USER_ID_SALT, persona_id="siostry")
    siostry_shared_vs.add_session_message(conversation_id=conversation_id, role="model",
                                          content=f"[{sister}] {assistant_response}",
                                          user_id=USER_ID, salt=USER_ID_SALT, persona_id="siostry",
                                          thought=inner_thought or "", hint=hint or "")
    print(f"[SIOSTRY] {sister}: {assistant_response[:60]}...")
    return {"persona": sister, "label": SISTERS[sister]["label"],
            "response": assistant_response, "hint": hint or "", "thought": inner_thought or ""}


class SiostryResponse(BaseModel):
    responses: list
    scene: str
    conversation_id: str


@app.post("/api/siostry", response_model=SiostryResponse)
async def siostry_chat(req: ChatRequest):
    if not gemini_client:
        raise HTTPException(status_code=503, detail="Gemini API nie skonfigurowane")
    user_msg = strip_memory_echo(req.message)
    if not user_msg:
        raise HTTPException(status_code=400, detail="Pusta wiadomość")
    conversation_id = req.conversation_id or str(uuid.uuid4())
    present = list(_SISTER_ORDER)

    # Scena zastana — tylko na starcie sesji (pusta historia = pierwszy raz w pokoju)
    scene = ""
    if not siostry_shared_vs.get_recent_session(conversation_id, n=2):
        scene = await _scene_as_found(present)

    routing = _route_siostry(user_msg)   # silent-first: [(sister,'full'|'aside'), ...]
    responses = []
    first_resp, first_sister = None, None
    for idx, (sister, mode) in enumerate(routing):
        r = await _generate_sister(
            sister, user_msg, conversation_id, scene, present,
            other_response=first_resp, other_sister=first_sister, aside=(mode == 'aside'),
            store_user_message=(idx == 0),
        )
        responses.append(r)
        if idx == 0:
            first_resp, first_sister = r["response"], sister
    return SiostryResponse(responses=responses, scene=scene, conversation_id=conversation_id)


@app.get("/siostry")
async def siostry_page():
    return FileResponse(str(Path(__file__).parent / "siostry.html"))


@app.post("/api/wspolny", response_model=WspolnyResponse)
async def wspolny_chat(req: ChatRequest):
    if not gemini_client:
        raise HTTPException(status_code=503, detail="Gemini API nie skonfigurowane")

    user_msg_clean = strip_memory_echo(req.message)
    if not user_msg_clean:
        raise HTTPException(status_code=400, detail="Pusta wiadomość")

    conversation_id = req.conversation_id or str(uuid.uuid4())

    # Etap 3: inteligentny routing — kto odpowiada i jak
    primary, secondary, secondary_is_aside = _route_wspolny(user_msg_clean)

    ct_primary = get_flag(consumer=primary)
    if ct_primary:
        clear_flag()

    primary_result = await _wspolny_generate(
        primary, user_msg_clean, conversation_id,
        cross_talk_flag=ct_primary,
    )

    responses = [primary_result]
    mode_str = f"solo_{primary}"

    if secondary:
        ct_secondary = get_flag(consumer=secondary)
        if ct_secondary:
            clear_flag()

        secondary_result = await _wspolny_generate(
            secondary, user_msg_clean, conversation_id,
            other_response=primary_result['response'],
            store_user_message=False,
            cross_talk_flag=ct_secondary,
            aside_mode=secondary_is_aside,
        )
        responses.append(secondary_result)
        mode_str = (
            f"aside_{primary}_then_{secondary}"
            if secondary_is_aside
            else f"both_{primary}_first"
        )

    print(f"[WSPOLNY] mode={mode_str}")
    return WspolnyResponse(
        responses=responses,
        conversation_id=conversation_id,
        mode=mode_str,
    )


@app.get("/api/amelia/health")
async def amelia_health():
    stats = amelia_vector_store.get_stats() if amelia_vector_store else {}
    lookup_stats = amelia_lookup.get_stats() if amelia_lookup else {}
    state = amelia_state_manager.load() if amelia_state_manager else None
    return {
        "status": "ok",
        "gemini": bool(gemini_client),
        "vectors": stats.get("total_vectors", 0),
        "history_db": lookup_stats,
        "state_mood": state.current_mood if state else "neutral",
        "active_conversation_id": state.active_conversation_id if state else ""
    }


# ──────────────────────────────────────────────────────────────
# API — STATE ENDPOINTS
# ──────────────────────────────────────────────────────────────

# ── Debug auth: 2. zamek na poziomie aplikacji (niezależny od nginx). ──
# "struktura > dyscyplina": jeden zamek w configu, który ktoś ruszy = dyscyplina; zamek w kodzie = struktura.
# Aktywny gdy DEBUG_USER/DEBUG_PASS ustawione w .env; inaczej fallback na nginx (dev).
# MUSI być przed pierwszym endpointem używającym go w Depends() (ewaluacja przy ładowaniu modułu).
_debug_auth = HTTPBasic(auto_error=False)

def check_debug_auth(credentials: HTTPBasicCredentials = Depends(_debug_auth)):
    exp_user = os.getenv("DEBUG_USER")
    exp_pass = os.getenv("DEBUG_PASS")
    if not exp_user or not exp_pass:
        return  # niezkonfigurowane → polegamy na nginx auth_basic
    ok = (credentials is not None
          and _secrets.compare_digest(credentials.username, exp_user)
          and _secrets.compare_digest(credentials.password, exp_pass))
    if not ok:
        raise HTTPException(status_code=401, detail="Debug auth required",
                            headers={"WWW-Authenticate": "Basic"})


@app.get("/api/debug/facts")
async def debug_facts(_auth=Depends(check_debug_auth)):
    """Pokazuje wszystkie twarde fakty w FactStore (SQLite)."""
    facts = fact_store.get_facts_for_prompt(persona_id=PERSONA_ID, user_id=USER_ID, salt=USER_ID_SALT)
    stats = fact_store.get_stats(persona_id=PERSONA_ID, user_id=USER_ID, salt=USER_ID_SALT)
    return {"stats": stats, "facts": facts}


@app.get("/api/debug/rag")
async def debug_rag(query: str, n: int = 10, _auth=Depends(check_debug_auth)):
    """Pokazuje co RAG zwróciłby dla danego zapytania — pełne metadane i score."""
    results = vector_store.search_memories(query=query, persona_id=PERSONA_ID, n=n, pool_size=30,
                                           user_id=USER_ID, salt=USER_ID_SALT)
    return {
        "query": query,
        "count": len(results),
        "results": [
            {
                "text": r["text"][:200],
                "source": r.get("metadata", {}).get("source"),
                "importance": r.get("metadata", {}).get("importance"),
                "timestamp": r.get("metadata", {}).get("timestamp"),
                "is_milestone": r.get("metadata", {}).get("is_milestone"),
                "final_score": r.get("final_score"),
                "distance": r.get("distance"),
                "score_detail": r.get("_score_detail", {}),
            }
            for r in results
        ],
    }


@app.post("/api/debug/nocna-analiza")
async def trigger_nocna_analiza(_auth=Depends(check_debug_auth)):
    """Ręczne uruchomienie Nocnej Analizy (do testów)."""
    if not vector_store or not gemini_client:
        raise HTTPException(status_code=503, detail="System nie gotowy")
    result = run_nocna_analiza(vector_store, gemini_client, GEMINI_MODEL)
    return result


@app.get("/api/morning-message")
async def get_morning_message():
    """Zwraca poranną wiadomość jeśli nieprzeczytana. Oznacza jako przeczytaną."""
    state = state_manager.load()
    if not state.morning_message or state.morning_message_shown:
        return {"message": None}
    msg = state.morning_message
    state.morning_message_shown = True
    state_manager.save(state)
    return {"message": msg}


@app.post("/api/debug/morning-message")
async def trigger_morning_message(_auth=Depends(check_debug_auth)):
    """Ręczne wygenerowanie porannej wiadomości (do testów)."""
    if not vector_store or not gemini_client:
        raise HTTPException(status_code=503, detail="System nie gotowy")
    msg = generate_morning_message(vector_store, gemini_client, GEMINI_MODEL, state_manager)
    if msg:
        state = state_manager.load()
        state.morning_message = msg
        state.morning_message_shown = False
        state_manager.save(state)
    return {"message": msg}


@app.get("/api/debug/stats")
async def debug_stats(_auth=Depends(check_debug_auth)):
    """Pełny obraz stanu systemu — wektory, stan relacji, rozkład źródeł."""
    total = vector_store.collection.count()

    # Rozkład źródeł
    try:
        all_items = vector_store.collection.get(
            where={"persona_id": PERSONA_ID},
            include=["metadatas"]
        )
        sources: dict = {}
        for meta in all_items.get("metadatas", []):
            src = meta.get("source", "unknown")
            sources[src] = sources.get(src, 0) + 1
    except Exception:
        sources = {}

    state = state_manager.load()
    return {
        "total_vectors": total,
        "persona_vectors": sum(sources.values()),
        "sources": sources,
        "state": {
            "level": state.level,
            "level_name": state.level_name,
            "xp": state.xp,
            "mood": state.current_mood,
            "total_messages": state.total_messages,
            "active_concerns": state.active_concerns,
        },
    }


@app.get("/api/debug/inspect")
async def debug_inspect(query: str, persona: str = "astra", day_offset: int = 0,
                        generate: bool = False,
                        _auth=Depends(check_debug_auth)):
    """
    AMNEZJA — read-only prześwietlenie retrievalu. Zwraca trace etapów + finalny prompt.
    generate=False (domyślnie): DRY — zero Gemini, zero zapisu (jak dotąd).
    generate=True: PIASKOWNICA — składa prompt jak /api/chat i pyta Gemini JAK Astra by odpowiedziała.
        Woła Gemini (kosztuje), ale NIE zapisuje nic (brak add_session_message, brak ekstrakcji, brak update stanu).
        Bezpieczne dla żywej relacji — testujesz na sucho.
    Uruchamiane w osobnym wątku (asyncio.to_thread) — nie blokuje żywej rozmowy.
    """
    import copy
    if persona != "astra":  # B6: param przyjmowany-ale-ignorowany → jawny 422 do czasu PersonaConfig
        raise HTTPException(status_code=422, detail="Amnezja v1: tylko persona 'astra' (Amelia/Wspólny wkrótce)")
    day_offset = max(0, day_offset)  # B2: ujemny offset = Frankenstein czasu (przyszłe wektory jako świeże)
    now_override = (datetime.utcnow() + timedelta(days=day_offset)) if day_offset else None
    # B1: świeża KOPIA stanu (nie żywy singleton — chroni przed mutacją z równoległego chatu)
    #     + symulacja inkrementu licznika jak w /api/chat → blok [STAN] = produkcja co do znaku.
    state = copy.deepcopy(state_manager.load())
    state.messages_this_session += 1
    cid = state.active_conversation_id or "amnezja"
    trace = {}

    def _run():
        return compose_context(
            query=query, conversation_id=cid,
            vs_main=vector_store, vs_shared=shared_vector_store, fact_store=fact_store,
            persona_id=PERSONA_ID, build_prompt_fn=build_system_prompt,
            state=state, session_n=10, now_override=now_override, trace=trace,
        )

    ctx = await asyncio.to_thread(_run)

    # PIASKOWNICA: opcjonalna generacja odpowiedzi (dry — woła Gemini, NIC nie zapisuje).
    generated = None
    if generate:
        def _gen():
            contents = []
            for msg in ctx["session_messages"]:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if content:
                    contents.append(genai_types.Content(role=role, parts=[genai_types.Part(text=content)]))
            contents.append(genai_types.Content(role="user", parts=[genai_types.Part(text=query)]))
            cfg = genai_types.GenerateContentConfig(
                system_instruction=ctx["system_prompt"],
                max_output_tokens=8192,
                temperature=0.85,
                thinking_config=genai_types.ThinkingConfig(thinking_budget=4096),
                response_mime_type="application/json",
            )
            resp = gemini_client.models.generate_content(model=GEMINI_MODEL, contents=contents, config=cfg)
            raw = safe_response_text(resp)
            a_resp, thought, hint, _updates = parse_gemini_response(raw)
            return {"response": a_resp, "thought": thought, "hint": hint}
        try:
            generated = await asyncio.to_thread(_gen)
        except Exception as e:
            generated = {"error": f"{type(e).__name__}: {e}"}

    return {
        "query": query,
        "persona": "astra",
        "day_offset": day_offset,
        "now_simulated": (now_override or datetime.utcnow()).strftime("%Y-%m-%d %H:%M UTC"),
        "hard_facts_count": len(ctx["hard_facts"]),
        "final_count": len(ctx["memories"]),
        "stages": trace.get("stages", []),
        "system_prompt": ctx["system_prompt"],
        "generated": generated,
    }


@app.get("/debug")
async def debug_page(_auth=Depends(check_debug_auth)):
    return FileResponse(str(Path(__file__).parent / "debug.html"))


@app.get("/amnezja")
async def amnezja_page(_auth=Depends(check_debug_auth)):
    return FileResponse(str(Path(__file__).parent / "amnezja.html"))


@app.get("/api/history")
async def get_history(conversation_id: str, n: int = 30):
    """Zwraca historię sesji do wyświetlenia w UI po odświeżeniu."""
    messages = vector_store.get_recent_session(conversation_id, n=n)
    return {"messages": messages, "conversation_id": conversation_id}


@app.get("/api/history/amelia")
async def get_amelia_history(conversation_id: str, n: int = 30):
    """Zwraca historię sesji Amelii do wyświetlenia w UI po odświeżeniu."""
    messages = amelia_vector_store.get_recent_session(conversation_id, n=n) if amelia_vector_store else []
    return {"messages": messages, "conversation_id": conversation_id}


@app.get("/api/history/wspolny")
async def get_wspolny_history(conversation_id: str, n: int = 30):
    """Zwraca historię wspólnego pokoju do wyświetlenia w UI po odświeżeniu."""
    messages = shared_vector_store.get_recent_session(conversation_id, n=n) if shared_vector_store else []
    return {"messages": messages, "conversation_id": conversation_id}


@app.get("/api/state")
async def get_state():
    """Zwraca aktualny stan relacji."""
    state = state_manager.load()
    return state.to_dict()


@app.delete("/api/state")
async def reset_state(_auth=Depends(check_debug_auth)):
    """Resetuje stan do zera (dev/debug only)."""
    state_manager.reset()
    return {"status": "reset", "message": "Stan zresetowany do Level 1"}


# ──────────────────────────────────────────────────────────────
# PUSH NOTIFICATIONS
# ──────────────────────────────────────────────────────────────

class PushSubscriptionModel(BaseModel):
    endpoint: str
    keys: dict


@app.get("/api/push/vapid-public-key")
async def get_vapid_public_key():
    """Zwraca VAPID public key dla frontendu."""
    return {"publicKey": VAPID_PUBLIC_KEY_STR}


@app.post("/api/push/subscribe")
async def push_subscribe(sub: PushSubscriptionModel):
    """Zapisuje subskrypcję push notyfikacji."""
    subs = _load_subscriptions()
    sub_dict = sub.model_dump()
    # Unikaj duplikatów (ten sam endpoint)
    if not any(s.get("endpoint") == sub_dict["endpoint"] for s in subs):
        subs.append(sub_dict)
        _save_subscriptions(subs)
    return {"status": "subscribed", "total": len(subs)}


@app.post("/api/debug/test-push")
async def test_push(_auth=Depends(check_debug_auth)):
    """Testuje push notyfikację (dev only)."""
    subs = _load_subscriptions()
    if not subs:
        return {"status": "no_subscribers", "message": "Brak subskrypcji"}
    send_push_to_all("Astra 🔔", "Test powiadomienia — działa!")
    return {"status": "sent", "subscribers": len(subs)}


# ──────────────────────────────────────────────────────────────
# STATIC FRONTEND
# ──────────────────────────────────────────────────────────────

if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

    @app.get("/")
    async def serve_index():
        return FileResponse(str(FRONTEND_DIR / "index.html"))

    @app.get("/amelia")
    async def serve_amelia():
        return FileResponse(str(FRONTEND_DIR / "amelia.html"))

    @app.get("/wspolny")
    async def serve_wspolny():
        return FileResponse(str(FRONTEND_DIR / "wspolny.html"))

    @app.get("/{path:path}")
    async def serve_frontend(path: str):
        # Block sensitive paths — always 404
        blocked = [
            '.env', '.git', '.aws', '.ssh', '.svn', '.htaccess', '.gitconfig',
            'config.php', 'wp-admin', 'wp-login', 'phpinfo', 'xmlrpc',
            'actuator', 'server-status', 'containers/json',
            'id_rsa', 'id_ed25519', 'Pipfile', 'Gemfile', 'Dockerfile', 'Procfile',
            'phpmyadmin', 'pmd',
        ]
        path_lower = path.lower().strip('/')
        # Block any dotfile path
        if any(seg.startswith('.') for seg in path_lower.split('/')):
            raise HTTPException(status_code=404, detail="Not found")
        if any(b in path_lower for b in blocked):
            raise HTTPException(status_code=404, detail="Not found")

        file_path = FRONTEND_DIR / path
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))

        # Plik z rozszerzeniem którego nie ma → 404 (nie serwuj index.html jako .js/.env/etc.)
        last_segment = path.split('/')[-1]
        if '.' in last_segment:
            raise HTTPException(status_code=404, detail="Not found")

        # SPA route (bez rozszerzenia) → index.html
        return FileResponse(str(FRONTEND_DIR / "index.html"))
