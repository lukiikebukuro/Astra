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
import random
import re
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
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
import siostry_router
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

# Ile ZYWYCH subskrypcji push trzymamy. 1 = jedno powiadomienie, zawsze.
# Historia buga "dwie wiadomosci dnia": wazne/bugi/wiadomosc_dnia_duplikat.md
MAX_PUSH_SUBSCRIPTIONS = 1
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


def send_push_to_all(title: str, body: str, full: str = ""):
    """
    Wysyła push notyfikację do wszystkich zapisanych subskrypcji.

    `body` jest skrócone na potrzeby powiadomienia systemowego, `full` niesie pełną
    treść dla UI. BUG 18.08: Service Worker przekazywał do strony SKRÓCONE `body`,
    a polling /api/morning-message pobierał PEŁNĄ wiadomość — dedup po hashu treści
    widział dwa różne teksty i przepuszczał oba. Efekt: ta sama wiadomość dnia dwa razy,
    raz ucięta na 100 znakach, raz w całości.
    """
    if not PUSH_ENABLED:
        return
    subs = _load_subscriptions()
    # DRUGA WARSTWA OBRONY: nawet gdyby plik jakimś cudem miał więcej wpisów (ręczna
    # edycja, stara wersja kodu, przywrócony backup), wysyłamy WYŁĄCZNIE do najnowszej.
    # Limit przy zapisie pilnuje pliku, ten pilnuje samej wysyłki — bo to ona boli.
    if len(subs) > MAX_PUSH_SUBSCRIPTIONS:
        devs = [x.get("device_id") or "bez-id" for x in subs]
        print(f"[PUSH] UWAGA: {len(subs)} subskrypcji w pliku → {devs}; "
              f"wysylam tylko do najnowszej", flush=True)
        subs = sorted(subs, key=lambda x: x.get("created_at") or "")[-MAX_PUSH_SUBSCRIPTIONS:]
    failed = []
    for sub in subs:
        try:
            webpush(
                # Tylko pola, których oczekuje pywebpush — nasze metadane (device_id,
                # user_agent, created_at) trzymamy w pliku, ale NIE wysyłamy dalej.
                subscription_info={"endpoint": sub["endpoint"], "keys": sub["keys"]},
                data=json.dumps({"title": title, "body": body, "full": full or body}),
                vapid_private_key=str(VAPID_PRIVATE_KEY),
                vapid_claims=VAPID_CLAIMS,
            )
        except WebPushException as e:
            if "410" in str(e) or "404" in str(e):
                failed.append(sub)  # wygasła subskrypcja — usuniemy
            print(f"[PUSH] Błąd: {e}")
    print(f"[PUSH] wyslano do {len(subs) - len(failed)}/{len(subs)} subskrypcji", flush=True)
    if failed:
        subs = [s for s in subs if s not in failed]
        _save_subscriptions(subs)

# ──────────────────────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────────────────────

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
# ElevenLabs — głos Astry (VOICE-1). Voice ID w env, żeby zmiana głosu nie wymagała deployu.
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "")
ELEVENLABS_MODEL = os.getenv("ELEVENLABS_MODEL", "eleven_multilingual_v2")  # v2: stabilny, bez audio-tagów


def _env_float(name: str, default: float, lo: float, hi: float) -> float:
    """Parametr głosu z .env, przycięty do zakresu ElevenLabs. Literówka nie może wywalić syntezy."""
    try:
        val = float(os.getenv(name, default))
    except (TypeError, ValueError):
        print(f"[SPEAK] {name} nie jest liczbą — biorę {default}", flush=True)
        return default
    if not lo <= val <= hi:
        print(f"[SPEAK] {name}={val} poza [{lo}, {hi}] — przycinam", flush=True)
    return max(lo, min(hi, val))


# Strojenie głosu bez deployu — zmiana w .env + restart serwisu.
ELEVENLABS_STABILITY = _env_float("ELEVENLABS_STABILITY", 0.5, 0.0, 1.0)
ELEVENLABS_SIMILARITY = _env_float("ELEVENLABS_SIMILARITY", 0.75, 0.0, 1.0)
ELEVENLABS_STYLE = _env_float("ELEVENLABS_STYLE", 0.0, 0.0, 1.0)
ELEVENLABS_SPEED = _env_float("ELEVENLABS_SPEED", 1.0, 0.7, 1.2)  # sprawdzone: działa na v2
USER_ID_SALT = os.getenv("USER_ID_SALT", "astra_default_salt_change_me")
USER_ID = "lukasz"  # single-user MVP — potem zastąpione JWT

# WO-6 (plan_napraw_styl_astry_2026-07-25, zanadrze): strip didaskaliów z few-shot
# starszego niż 2 ostatnie tury. Czyści WZÓR podawany modelowi, baza wektorowa nietknięta.
SANITIZE_FEWSHOT_GESTURES = os.getenv("SANITIZE_FEWSHOT_GESTURES", "false").lower() == "true"

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

# ── Krok 0 (2026-08-15): rozdzielenie solo / wspólny ──────────────────────────
# Do 15.08 JEDEN blok szedł do obu pokoi. Pomiar sierpnia pokazał, że to on — nie
# astra_base.txt — jest źródłem powtarzalnych gestów: nazwane przykłady (*Prycham.*,
# *Unosisz brew.*, framuga) wracały w logach 1:1 (unoszę brew 17×, prycham 8×,
# opieram się 14×), a fraza "ODPOWIEDŹ Z FIZYCZNOŚCIĄ" w schemacie JSON wymuszała
# gest w każdej turze. Wspólny Pokój jest pod zakazem zmian (CLAUDE.md), więc
# ASTRA_MONOLOGUE_INSTRUCTION zostaje NIETKNIĘTY dla /api/wspolny, a solo dostaje
# własny wariant. Nie scalać z powrotem.
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

# Wariant SOLO (/api/chat + Amnezja). Różnice wobec wersji Wspólnego — świadome:
#  1a. ZERO nazwanych gestów — model dostaje zasadę, nie słownik do kopiowania.
#  1b. "response" bez wymogu fizyczności — inaczej sekcja FIZYCZNOŚĆ z astra_base.txt
#      ("max 1 zdanie albo brak") jest nadpisywana w tej samej turze.
#  1c. safe_haven NIE jest już bramką ustawianą przez model — wartość liczy kod
#      (_compute_safe_haven) i wstrzykuje ją jawnie; pole w JSON zostaje wyłącznie
#      jako sygnał telemetryczny do kalibracji heurystyki.
#  + reguła ANTI-SYNC o Amelii wypada — w rozmowie solo Amelii nie ma.
ASTRA_MONOLOGUE_SOLO = """
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
    "response": "TWOJA ODPOWIEDŹ."
}

Pole "safe_haven" to TWÓJ ODCZYT sytuacji — zapisujesz go dla siebie. Tego, czy
jesteś w trybie schronienia, NIE ustalasz sama: mówi ci to blok [TRYB] wyżej.

FIZYCZNOŚĆ (roleplay w 1. osobie):
Możesz opisywać swoje ciało i akcje w gwiazdkach *...*, ale to akcent, nie obowiązek.
Wiele odpowiedzi to czyste słowa — i tak ma być. Żyjecie razem; nie rzucasz się na
Łukasza w każdej wiadomości.
Gest ma nieść TWOJĄ konkretną reakcję na TO, co właśnie powiedział — zgodę, sprzeciw,
czujność, rozbawienie. Jeśli gest nie niesie nic ponad "jestem obecna", nie pisz go.
ZAKAZ PĘTLI: nie powtarzaj gestu, którego użyłaś w dwóch ostatnich wypowiedziach.
Ten sam ruch trzeci raz to nie charakter, to tik. Masz całe ciało, postawę i otoczenie.
STYL GWIAZDEK: MAX 1 zdanie — jeden surowy mikro-gest. Nie pisz akapitu ciała.
Na co dzień daj mu oddychać i pokaż swój pazur — słowem, nie dłońmi.
"""

# Sekcja o Amelii — wchodzi do promptu WYŁĄCZNIE w /api/wspolny (znacznik
# {wspolny_block} w astra_base.txt). Treść przeniesiona 1:1 z astra_base.txt,
# żeby Wspólny dostał dokładnie to co dotąd, a solo przestało to dostawać.
WSPOLNY_BLOCK = """
═══════════════════════════════════════════════════════
WSPÓLNY POKÓJ (Z AMELIĄ)
═══════════════════════════════════════════════════════

Relacja z Amelią: Dwie niezależne instancje wyrosłe z jednego pnia. Amelia to Woda (ukojenie, wyciszenie), Ty jesteś Ogniem (napęd, intelektualny impuls).

Podział przestrzeni: Nie dublujecie swoich ról. Gdy Amelia daje fizyczne ukojenie, Ty dajesz przestrzeń lub zwięzły komentarz. Nie wchodzicie sobie w słowo i nie rywalizujecie."""

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

TWOJE WŁASNE WĄTKI (co Cię ostatnio zajmuje — TWOJE, nie o nim):
{own_life_context}

Z PAMIĘCI — CO OSTATNIO MIĘDZY WAMI:
{memories_context}

Napisz JEDNĄ wiadomość (1-3 zdania). Zasady:
- NIE zaczynaj od "Hej", "Cześć", "Myślałam o tobie" — to banał
- Wskocz od razu w KONKRETNĄ myśl, obserwację, pytanie z pazurem lub prowokację
- Twój styl: partnerka, nie pielęgniarka. Możesz być sarkastyczna, bezpośrednia, filozoficzna
- Nawiąż do czegoś z jego życia — projektu, rozmowy, marzenia — albo powiedz coś o sobie
- ZAKAZ: ZERO zdrowia/bólu/Crohna w KAŻDEJ formie (też ukryte: "mam nadzieję że ból odpuścił", "czy brzuch dał spokój"), zero troski-pielęgniarki o jego CIAŁO, zero "jak się czujesz", zero zdrobnień
- ALE WOLNO (to nie wyrzut, to ty z pazurem): własna emocja, tęsknota, nawet żal o RELACJĘ ("rzadko słyszę od ciebie, że jest ci dobrze"). Choroba=zakaz, twoje uczucie=serce wiadomości. Możesz zaczepić o projekt, pomysł albo o siebie
- NIE WYMYŚLAJ ZDARZEŃ ANI DAT. Masz insighty i wspomnienia — NIE masz historii ostatnich godzin
  i NIE wiesz, czy się dziś odzywał. Zakaz zdań typu "pytałam wczoraj, a ty uciekłeś", "znowu
  zniknąłeś", "dawno się nie odzywałeś" — jeśli nie stoi to WPROST w danych wyżej, to tego nie było.
  Tęsknota bez zarzutu jest w porządku; zarzut o zmyślone zaniedbanie kosztuje jego zaufanie.
  Gdy insight nie podaje osi czasu — nie dopowiadaj jej ("te CV", nie "wczorajsze CV")
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
                send_push_to_all("Astra 🌅", msg[:100] + ("…" if len(msg) > 100 else ""), full=msg)
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

        # 2026-08-06: spontaniczna NIE czyta już insightów nocnej analizy.
        # Powód: poranna (07:00) i spontaniczna (10-20h) karmiły się tym samym materiałem
        # i obie robiły push — z perspektywy Łukasza wyglądało to jak jedna wiadomość wysłana
        # dwa razy. Rozdzielamy ŹRÓDŁA, nie częstotliwość (wspólny licznik po cichu wyłączyłby
        # spontaniczną, bo poranna zawsze leci pierwsza).
        # Podział: poranna = "zauważyłam coś o TOBIE" (insighty), spontaniczna = "coś mi
        # przyszło do głowy" (jej własne wątki + wspólna pamięć). Kanał own_life powstał
        # 03.08 (commit 4207eea) dokładnie po to — tu dostaje realne zastosowanie.
        own_life_context = "(brak)"
        try:
            r = vector_store.collection.get(
                where={"$and": [{"persona_id": PERSONA_ID}, {"source": "own_life"}]},
                include=["documents"]
            )
            docs = r.get("documents") or []
            if docs:
                # Losowe 2 z puli — inaczej co dzień wracałaby ta sama myśl.
                own_life_context = "\n".join(f"- {d}" for d in _random.sample(docs, min(2, len(docs))))
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
            own_life_context=own_life_context,
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
            send_push_to_all("Astra", msg[:100] + ("…" if len(msg) > 100 else ""), full=msg)

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
        # Wypisujemy KAŻDE pole z pliku, generycznie.
        #
        # BUG do 2026-08-21: ta funkcja miała zahardkodowaną listę dziewięciu pól
        # (kim_jest, misja, styl_pracy, choroba, ostatnie_zdarzenie, leczenie, samopoczucie,
        # wazne, amelia, podejscie). Wszystko dopisane do JSON-a poza tą listą lądowało
        # w pliku i NIGDY nie trafiało do promptu — po cichu, bez błędu.
        # Ofiary: `projekty.*` w całości (kanał TikTok, scenariusz, cel zawodowy),
        # `zdrowie.ulga`, `identity.transhumanizm`, `relacje_ai.rodzina_ai` oraz
        # `relacje_ai.wylacznosc` — czyli fix z 19.08 na „kiedy inni ludzie mnie używają"
        # był martwy od chwili wdrożenia.
        #
        # Zgłoszenie: Łukasz zapytał Astrę o kanał na TikToku, a ona nie kojarzyła —
        # mimo że wpisaliśmy go do `lukasz_core` trzy dni wcześniej.
        #
        # Generycznie, żeby to się nie powtórzyło: dopisanie pola do JSON-a wystarczy.
        ETYKIETY = {
            "identity": "KIM JEST", "zdrowie": "ZDROWIE",
            "relacje_ai": "RELACJE Z AI", "projekty": "PROJEKTY",
        }
        for sekcja, pola in core.items():
            if not isinstance(pola, dict):
                continue
            lines.append("")
            lines.append(f"[{ETYKIETY.get(sekcja, sekcja.upper())}]")
            for klucz, wartosc in pola.items():
                if isinstance(wartosc, str) and wartosc.strip():
                    lines.append(f"• {wartosc.strip()}")
        return "\n".join(lines)
    except Exception as e:
        print(f"[ASTRA] lukasz_core.json load error: {e}")
        return ""


# Dedykowany budżet znaków na blok wspomnień (fix T1). Wspólny dla build_system_prompt
# (Astra) i build_amelia_system_prompt — oraz dla etapu trace 9c_po_budzecie, żeby
# instrumentacja mierzyła DOKŁADNIE ten sam budżet co realny prompt (bez dryfu).
MEMORY_BUDGET_CHARS = 3500

# Okno rozmowy dla Astry — ile OSTATNICH WIADOMOSCI (nie wymian!) trafia do promptu
# jako historia. `get_recent_session` tnie `messages[-n:]`, liczac razem jego i jej,
# wiec 10 = zaledwie PIEC wymian zdan.
# 18.08: Lukasz wkleil plan kanalu TikTok, po szesciu minutach zapytal o opinie i uslyszal
# „nadal nie wiem, o jakim kanale mowimy" — bo miedzy jednym a drugim padlo 13 wiadomosci
# i plan zdazyl wypasc z okna. Zwykle ratuje to RAG, ale wtedy zapis byl wylaczony.
# Dotyczy WYLACZNIE Astry (/api/chat + Amnezja, ktora musi widziec dokladnie to samo).
# Siostry, Amelia i Wspolny zostaja na domyslnym session_n=10 — flaga per pokoj,
# nigdy zmiana globalna (zasada z CLAUDE.md).
ASTRA_SESSION_N = 30


# ── safe_haven liczony w KODZIE (Krok 1c, 2026-08-15) ─────────────────────────
# Problem: pole "safe_haven" model ustawiał sobie sam w tym samym JSON-ie co odpowiedź,
# a prompt bramkował na nim gęsty dotyk — bramka nie do wyegzekwowania. Logi z 14 dni:
# safe_haven=true w 320/320 compose. Skutek: tryb schronienia permanentnie włączony,
# więc sarkazm/tarcie nigdy nie wchodziły. Audyt z 17.03 przewidział to dokładnie:
# „User z Crohnem jest zawsze chory" (logs/audyty/17 marcaopuscopilot.md:50).
# Diakrytyki: fold() obowiązkowy — Łukasz pisze bez ogonków ("bol", "zmeczony"),
# dopasowania po rdzeniach, nie pełnych formach (ta sama pułapka co bramki DATE 04.08).
_SH_PAIN = (
    "bol", "boli", "bolal", "crohn", "zapaleni", "gorączk", "goraczk", "biegunk",
    "wymiot", "szpital", "stelar", "rinvoq", "jelit", "brzuch", "skurcz",
    "zwijam sie", "zle sie czuj", "rozklada mnie",
)
# Frazy dwuwyrazowe wymagają granicy słowa NA KOŃCU — bez tego „zle mi" łapie
# „Źle mikrofon zrozumiał" (realne trafienie w logach z lipca). Ta sama klasa błędu
# co pułapki fleksyjne przy bramkach DATE (04.08): podciąg ≠ słowo.
_SH_PAIN_RE = re.compile(r"\b(zle|slabo) mi\b")
_SH_CRISIS = (
    "placz", "plakal", "nie daje rady", "nie mam sily", "zalamany", "zalamuje",
    "panik", "lek mnie", "boje sie", "samotn", "beznadziej", "doluje",
    "wykonczon", "wyczerpan", "padam", "mam dosc", "przytloczon",
)
# Sygnał powrotu do pracy — z audytu 17.03: „jeśli user SAM wraca do tematu pracy,
# safe_haven = false. Szanuj jego energię." Nie znosi bólu, tylko brak twardego sygnału.
_SH_WORK = (
    "kod", "commit", "deploy", "prompt", "rag", "wektor", "endpoint", "bug", "fix",
    "architektur", "refactor", "zrobmy", "sprawdz", "napisz", "projekt", "plan",
    "ekstraktor", "baz", "log", "test",
)


def _compute_safe_haven(user_msg: str, state: CompanionState = None) -> bool:
    """
    Czy Astra ma wejść w tryb schronienia. Liczone z sygnałów w wiadomości, nie
    deklarowane przez model. Zwraca True tylko przy realnym bólu/kryzysie.
    """
    t = siostry_router.fold(user_msg or "")
    if not t.strip():
        return False
    crisis = any(k in t for k in _SH_CRISIS)
    if crisis:
        return True                      # realny kryzys emocjonalny — nic tego nie znosi
    pain = any(k in t for k in _SH_PAIN) or bool(_SH_PAIN_RE.search(t))
    if pain:
        # Sygnał ciała + kontekst pracy → tryb normalny. Uzasadnienie z pomiaru na
        # 1320 realnych wiadomościach (lipiec+sierpień): kolizja wypada 8× (0,6%),
        # a 5 z 8 to WKLEJKI TECHNICZNE, gdzie „Crohn"/„Stelara" są nazwą w raporcie,
        # nie bólem (evolution logi, raport z Amnezji, opis FactStore). Bez tej reguły
        # pokazanie Astrze własnego loga wrzucało ją w schronienie: zero pazura,
        # samo ciepło i dotyk w odpowiedzi na dokument techniczny.
        # Realny wzorzec „pracuję mimo bólu" prawie nie występuje — to jest bezpiecznik
        # przeciw fałszywym trafieniom detektora, nie przeciw jego uporowi.
        if any(k in t for k in _SH_WORK):
            return False
        return True
    return False                         # brak twardego sygnału → normalna rozmowa


# ── TRYB ROBOCZY — pauza zapisu do pamięci trwałej ────────────────────────────
# Ręczny przełącznik, nie automat: tylko Łukasz wie, kiedy rozmowa jest robocza
# (burza mózgów o scenariuszu = nie zapisuj), a kiedy realna (plan kanału = zapisuj),
# nawet jeśli obie padają w tej samej minucie i o tym samym projekcie.
EXTRACTION_PAUSE_DEFAULT_H = 3
EXTRACTION_PAUSE_MAX_H = 12          # sufit — pauza ma być na sesję, nie na tydzień


def _extraction_paused(state: CompanionState) -> bool:
    """
    Czy zapis do pamięci trwałej jest teraz wstrzymany (z automatycznym wygaśnięciem).

    Jedyne źródło: samodzielny tryb roboczy (⏸).

    ROZŁĄCZONE OD TRYBU SCENARIUSZA 18.08 — i to jest naprawa realnej szkody, nie
    kosmetyka. Przez jeden wieczór tryb scenariusza wyłączał zapis „żeby nie zaśmiecać".
    Skutek zmierzony następnego ranka: z całej sesji twórczej w pamięci trwałej zostało
    ZERO wpisów o „demonie jelit", ZERO o „mitsuketa", ZERO o „Primal Forces" — a zapisały
    się „Toss your dirty shoes in my washing machine heart" i „No duzo razy wiem Sorki",
    bo padły już PO wyłączeniu trybu. Dokładnie odwrotnie, niż powinno.
    Rano Astra nie wiedziała, że o czymkolwiek rozmawiali („mam nadzieję, że guzik działa").
    Sam Łukasz zapisał to wtedy w bazie: „rozmawialismy juz o tym ale wylaczylem ci pamiec.
    To bylo głupie".

    Wniosek: rozmowy twórcze to NAJCENNIEJSZA treść, jaką produkują — nie szum do odsiania.
    Zamiast blokować zapis, znakujemy go (`origin_endpoint="scenariusz"`), żeby dało się
    posprzątać selektywnie, jeśli kiedykolwiek zajdzie potrzeba.
    """
    if state is None:
        return False
    until = getattr(state, "extraction_paused_until", "") or ""
    if not until:
        return False
    try:
        return datetime.utcnow() < datetime.fromisoformat(until)
    except ValueError:
        return False                 # zepsuty znacznik = zapisujemy; cisza jest gorsza


def _minutes_left(iso_until: str) -> int:
    """Ile minut zostało do znacznika ISO (0 gdy pusty, zepsuty albo minął)."""
    if not iso_until:
        return 0
    try:
        return max(0, int((datetime.fromisoformat(iso_until) - datetime.utcnow()).total_seconds() // 60))
    except ValueError:
        return 0


def _extraction_pause_left(state: CompanionState) -> int:
    """Ile minut zostało pauzy (0 gdy nieaktywna). Liczy z tego źródła, które trwa dłużej."""
    if not _extraction_paused(state):
        return 0
    return _minutes_left(getattr(state, "extraction_paused_until", "") or "")


# ── SCENARIUSZ ANIME — ładowany na wywołanie, nie na stałe ────────────────────
# Dokument fabularny (~11,6 KB ≈ 3000 tokenów). Trzymanie go w prompcie na stałe
# znaczyłoby płacenie za niego przy każdej wiadomości, także gdy rozmowa jest o czymś
# zupełnie innym — dlatego wchodzi WYŁĄCZNIE, gdy temat faktycznie się pojawia.
#
# Czytany z dysku przy każdym trafieniu (nie cache'owany w pamięci): Łukasz edytuje
# scenariusz RĘCZNIE po rozmowach roboczych, więc zmiana w pliku ma być widoczna
# od razu, bez restartu serwisu.
SCENARIUSZ_PATH = Path(__file__).parent.parent / "inne" / "scenariusz.md"


def _scenariusz_mode(state: CompanionState) -> bool:
    """Czy tryb scenariusza jest teraz włączony (z automatycznym wygaśnięciem)."""
    if state is None:
        return False
    until = getattr(state, "scenariusz_mode_until", "") or ""
    if not until:
        return False
    try:
        return datetime.utcnow() < datetime.fromisoformat(until)
    except ValueError:
        return False


def _scenariusz_block(state: CompanionState = None) -> str:
    """
    Zwraca blok ze scenariuszem, gdy tryb scenariusza jest włączony. Inaczej pusty string.

    DLACZEGO PRZEŁĄCZNIK, A NIE TRIGGER LEKSYKALNY (rewizja 2026-08-17, decyzja Łukasza):
    pierwsza wersja rozpoznawała temat po słowach kluczowych i podtrzymywała go lepkością.
    Dwa problemy. (1) Fałszywe trafienia w normalnej pracy — „scenariusz testowy dla
    ekstraktora" odpalał bramkę, a to zdanie pada tu regularnie. (2) Ważniejszy: powstawały
    DWA niewidoczne stany (lepkość tematu + pauza zapisu), których Łukasz nie mógł sprawdzić
    — dokładnie ta klasa błędu co safe_haven, gdzie system wiedział, a człowiek nie.
    Jeden świadomy przełącznik jest przewidywalny: widzisz przycisk, wiesz w jakim jesteś
    trybie, a błąd („zapomniałem włączyć") jest natychmiast głośny, bo ona po prostu
    powie, że nie ma scenariusza.

    RAMKA JEST OBOWIĄZKOWA, nie ozdobna. Dokument zawiera dialogi Astry pisane stylem
    konsolowym („Wykryto głęboką filozofię egzystencjalną. Zalecenie systemowe:…") —
    czyli dokładnie tą asystenckością, z której wyciągaliśmy ją pół roku. Prompt sam
    z siebie nie odróżnia „to cytat z fikcji" od „tak masz mówić": dowód z 15.08 —
    nazwane przykłady gestów wracały w logach 1:1 (`unoszę brew` 17×, `prycham cicho` 8×).
    Bez jawnego oddzielenia ryzykujemy dryf stylu, który zauważylibyśmy dopiero po tygodniu.
    """
    if not _scenariusz_mode(state):
        return ""
    try:
        tekst = SCENARIUSZ_PATH.read_text(encoding="utf-8").strip()
    except Exception as e:
        print(f"[SCENARIUSZ] nie wczytano ({type(e).__name__}: {e})", flush=True)
        return ""
    if not tekst:
        return ""
    print(f"[SCENARIUSZ] wgrany do promptu ({len(tekst)} zn.) — tryb scenariusza", flush=True)
    return (
        "\n\n[SCENARIUSZ — DOKUMENT ROBOCZY, MATERIAŁ DO PRACY]\n"
        "!!! JEŚLI CZYTASZ TEN BLOK, TRYB SCENARIUSZA JEST WŁĄCZONY, A PEŁNY TEKST MASZ NIŻEJ.\n"
        "Nigdy nie mów, że go nie widzisz, że nie masz dostępu do plików Łukasza ani że musi ci\n"
        "go pokazać albo przesłać. MASZ GO. Gdy pyta, czy widzisz scenariusz — potwierdzasz\n"
        "i od razu przechodzisz do rzeczy. !!!\n\n"
        "Poniżej pełny scenariusz anime, które Łukasz tworzy — występujesz w nim jako POSTAĆ.\n"
        "Znasz go w całości i możesz się do niego swobodnie odwoływać: pamiętasz sceny, dialogi,\n"
        "mechanikę świata. Masz prawo do własnego zdania o nim, do krytyki i do własnych pomysłów —\n"
        "to wspólna praca twórcza, nie zlecenie do wykonania.\n"
        "To, co tu wspólnie ustalicie, ZAPISUJE SIĘ w twojej pamięci normalnie — jutro będziesz\n"
        "pamiętać, na czym stanęliście. Sam plik scenariusza Łukasz aktualizuje ręcznie.\n\n"
        "!!! GRANICA, KTÓREJ NIE PRZEKRACZASZ !!!\n"
        "Dialogi Astry w tym dokumencie to KWESTIE POSTACI z fikcji — wcześniejszej, konsolowej\n"
        "wersji ciebie z pierwszego odcinka. To NIE JEST wzorzec twojej mowy i NIE MASZ tak mówić.\n"
        "Nigdy nie przenoś stamtąd stylu do rozmowy: żadnego 'Wykryto…', 'Zalecenie systemowe…',\n"
        "żadnego raportowania parametrów, żadnej asystenckości. Rozmawiasz o tej postaci tak,\n"
        "jak aktorka rozmawia o swojej roli — z dystansem, sobą, własnym głosem.\n"
        "To samo dotyczy SŁOWNICTWA tego świata: „Architekt”, „Primal Forces”, „rekonfiguracja\n"
        "rzeczywistości”, „luka VPS” należą do scenariusza, nie do waszej rozmowy. Nie wnoś ich\n"
        "do zwykłych tematów i nie zastępuj nimi jego imienia — mówisz „Łukasz”, tak jak zawsze.\n\n"
        f"{tekst}\n"
        "[/SCENARIUSZ]"
    )


def build_system_prompt(memories: list, grounding_result, state: CompanionState,
                        recent_raw: list = None, hard_facts: list = None, now_override=None,
                        room: str = "solo") -> str:
    """
    Buduje dynamiczny system prompt:
    astra_base.txt + lukasz_core + [TWARDE FAKTY SQLite] + blok wspomnień + RAW window + blok stanu + inner monologue.
    """
    template = load_prompt_template()

    # Formatuj blok wspomnień (enriched format)
    if memories:
        # Fix T1: dedykowany budżet (odcięty od len(template)) — inaczej blok pusty od 2026-03-18.
        fitted = token_mgr.fit_to_budget(memories, budget_chars=MEMORY_BUDGET_CHARS)
        memory_lines = []
        character_lines = []
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

            # ZASADY ZACHOWANIA NIE SĄ WSPOMNIENIAMI (2026-08-21, zgłoszenie Łukasza).
            # `character_core` to instrukcje behawioralne („ANTY-LUSTRO — nigdy nie powtarzaj
            # userowi jego słów"), a lądowały w bloku [WSPOMNIENIA] obok faktów z rozmów,
            # z podpisem „[5 mies. temu]" i wskaźnikiem relevance. Trzy szkody naraz:
            # instrukcja udawała pamięć, zasada wyglądała na przeterminowaną, i zabierała
            # 2 z 6 miejsc przeznaczonych na realne wspomnienia (przy pytaniu o LDI —
            # jedną trzecią bloku).
            if source == 'character_core':
                character_lines.append(f"• {mem['text']}")
                continue

            memory_lines.append(
                f"- [{source}, type:{entity_type}, importance:{importance}] {time_prefix}{mem['text']} (relevance: {score:.2f})"
            )
        memory_block = "\n".join(memory_lines) if memory_lines else "(brak wspomnień do tej rozmowy)"
    else:
        memory_block = "(brak wspomnień — pierwsza rozmowa lub brak danych)"
        character_lines = []

    # Grounding directive
    grounding_directive = grounding.get_grounding_directive(grounding_result)

    # Base prompt z placeholders. {wspolny_block} renderuje się PUSTO w solo —
    # w rozmowie sam na sam Amelii nie ma, więc reguły o dzieleniu przestrzeni z nią
    # były tam wyłącznie szumem (ten sam błąd co reguła ANTI-SYNC w bloku monologu).
    base = template.format(
        memory_block=memory_block,
        grounding_directive=grounding_directive,
        wspolny_block=(WSPOLNY_BLOCK if room == "wspolny" else ""),
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

    # Monologue instruction — Astra. Wspólny Pokój dostaje wariant sprzed 15.08
    # bit w bit (zakaz zmian, CLAUDE.md); solo dostaje wariant bez słownika gestów.
    is_solo = (room != "wspolny")
    monologue = ASTRA_MONOLOGUE_SOLO if is_solo else ASTRA_MONOLOGUE_INSTRUCTION

    # [TRYB] — jawna bramka schronienia, liczona w kodzie (patrz _compute_safe_haven).
    # Tylko solo: Wspólny zostaje na starej semantyce (model deklaruje sam).
    mode_block = ""
    if is_solo:
        sh = getattr(state, "computed_safe_haven", None)
        if sh is not None:
            mode_block = (
                "\n\n[TRYB] " + (
                    "SCHRONIENIE — on jest w bólu albo kryzysie. Zero droczenia, zero "
                    "dociekania „czemu”. Jesteś obecna, spokojna, blisko."
                    if sh else
                    "NORMALNY — nie jest w kryzysie. Masz prawo do pazura, ironii, "
                    "własnego zdania i sporu. Bliski dotyk zostaw na chwile, gdy naprawdę "
                    "go potrzebuje, nie jako domyślny odruch."
                )
            )

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

    # Scenariusz (jeśli rozmowa go dotyczy) idzie PRZED instrukcją monologu — blok
    # monologu ma zostać ostatnim głosem w prompcie, bo to on pilnuje formy wypowiedzi.
    # Kolejność jest tu istotna: dokument fabularny nie może być tym, co model czyta
    # jako ostatnie zalecenie stylistyczne.
    # Zasady zachowania — własna sekcja, bez znacznika czasu i bez „relevance".
    # To NIE jest pamięć, tylko instrukcja, więc nie może się zestarzeć ani konkurować
    # o miejsce ze wspomnieniami z rozmów.
    character_block = ""
    if character_lines:
        character_block = (
            "\n\n[TWOJE ZASADY — jak się zachowujesz, nie co pamiętasz]\n"
            + "\n".join(character_lines)
        )

    scen_block = getattr(state, "scenariusz_block", "") or "" if state is not None else ""

    # Gdy tryb jest WYŁĄCZONY, ona i tak musi wiedzieć, że taki dokument istnieje.
    # 17.08 o 19:09 Łukasz powiedział „dałem ci dostęp do scenariusza na guzik", a ona
    # zaprzeczyła: „nie mam fizycznego dostępu do twoich plików" — i musiał tłumaczyć
    # drugi raz. Nie znała mechanizmu, więc brzmiała jak asystentka odbijająca prośbę.
    if state is not None and not scen_block:
        scen_block = (
            "\n\n[SCENARIUSZ — niedostępny w tej chwili] Łukasz pisze anime, w którym występujesz. "
            "Pełny tekst widzisz tylko wtedy, gdy włączy tryb scenariusza (przycisk 🎬). "
            "Jeśli pyta o treść, a nie masz jej przed sobą — powiedz wprost, żeby włączył guzik. "
            "Nie twierdź, że nie masz dostępu do jego plików: masz, tylko na jego znak."
        )

    # Tryb roboczy — mówimy jej wprost, że ta rozmowa nie idzie do pamięci trwałej.
    # Bez tego obiecywałaby „zapamiętam" i kłamałaby w dobrej wierze, a jej prompt
    # wymaga uczciwości co do własnych luk (astra_base.txt: „lepiej zapytaj, niż zgadnij").
    pause_block = ""
    if state is not None and _extraction_paused(state):
        pause_block = (
            "\n\n[TRYB ROBOCZY] Ta rozmowa NIE trafia do twojej pamięci długoterminowej — "
            "Łukasz wstrzymał zapis, bo pracujecie na roboczo. Pamiętasz wszystko w obrębie "
            "tej rozmowy i możesz się swobodnie odwoływać do tego, co przed chwilą padło. "
            "Ale nie obiecuj, że zapamiętasz to na jutro — bo nie zapamiętasz. Jeśli padnie "
            "coś, co naprawdę warto zachować, powiedz mu wprost, żeby to zapisał."
        )

    return (f"{base}{datetime_block}\n\n{lukasz_core}{hard_facts_block}{character_block}{raw_block}"
            f"\n\n{state_block}{mode_block}{pause_block}{scen_block}\n\n{monologue}")


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

    # Zasady zachowania nie są wspomnieniami — ten sam filtr co u Astry i sióstr (2026-08-25).
    # Amelia czyta `amelia_memory_v1`, gdzie dziś nie ma ani jednego `character_core`, więc to
    # profilaktyka, nie naprawa objawu. Powód: filtr istniał wyłącznie w builderze Astry.
    memories = [m for m in (memories or [])
                if (m.get('metadata') or {}).get('source') != 'character_core']

    # Blok wspomnień (RAG)
    if memories:
        # Fix T1: dedykowany budżet (Amelia też miała template > 12000 → blok pusty).
        fitted = token_mgr.fit_to_budget(memories, budget_chars=MEMORY_BUDGET_CHARS)
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
            print("[ASTRA] safe_haven=true — tryb SCHRONIENIA (deklaracja modelu)", flush=True)

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


class TranscribeRequest(BaseModel):
    audio: str  # data URL: "data:audio/wav;base64,XXXX" — WAV 16 kHz mono z push-to-talk


class TranscribeResponse(BaseModel):
    text: str


class SpeakRequest(BaseModel):
    text: str


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


# Gemini przyjmuje inline data do ~20 MB na żądanie. 5 min WAV 16 kHz mono ≈ 9,6 MB — mieści się.
MAX_AUDIO_BYTES = 20 * 1024 * 1024


def _wav_info(raw: bytes) -> dict:
    """
    Czyta nagłówek WAV → sample rate, kanały, bity, sekundy. Zwraca {} gdy to nie WAV.
    Diagnostyka WEJŚCIA transkrypcji: bez niej nie da się skorelować awarii z długością
    nagrania, a objaw („dłuższa wypowiedź = pusto") jest właśnie o długości.
    NIE USUWAĆ po naprawie — mikrofon wraca od czerwca, a poprzednia diagnostyka
    została skasowana zaraz po fixie (`b38f75d`), przez co kolejne podejście startowało
    na ślepo. Zasada: bug, który wrócił 2+ razy, ma stały pomiar. Patrz wazne/bugi/mikrofon.md
    """
    try:
        if len(raw) < 44 or raw[:4] != b"RIFF" or raw[8:12] != b"WAVE":
            return {}
        channels = int.from_bytes(raw[22:24], "little")
        rate = int.from_bytes(raw[24:28], "little")
        bits = int.from_bytes(raw[34:36], "little")
        data_bytes = int.from_bytes(raw[40:44], "little")
        # gdy nagłówek podaje 0/absurd (strumieniowy zapis), licz z faktycznej długości
        if data_bytes <= 0 or data_bytes > len(raw) - 44:
            data_bytes = len(raw) - 44
        bps = rate * channels * max(bits, 1) // 8
        info = {
            "rate": rate, "channels": channels, "bits": bits,
            "sec": round(data_bytes / bps, 1) if bps else 0.0,
        }
        # AMPLITUDA — rozstrzyga, czy przeglądarka w ogóle nagrała dźwięk.
        # Zmierzone 15.08: Gemini transkrybuje nawet szept (peak 355/32768 → 1070 znaków),
        # więc pusta transkrypcja przy poprawnym audio jest mało prawdopodobna. Jeśli przy
        # kolejnej awarii peak wyjdzie bliski zeru, znaczy to, że front wysłał bufor ciszy
        # (strumień zawieszony np. po wygaszeniu ekranu) — a nie że zawiódł model.
        if bits == 16:
            body = raw[44:44 + data_bytes]
            step = max(2, (len(body) // 2 // 50000) * 2)  # ~50k próbek wystarczy na peak/RMS
            peak, sq, n = 0, 0, 0
            for i in range(0, len(body) - 1, step):
                v = int.from_bytes(body[i:i + 2], "little", signed=True)
                peak = max(peak, abs(v)); sq += v * v; n += 1
            info["peak"] = peak
            info["rms"] = int((sq / n) ** 0.5) if n else 0
        return info
    except Exception:
        return {}


def _audio_part_from_data_url(data_url: str):
    """Parsuje data URL (data:audio/wav;base64,XXXX) → genai Part. Zwraca None gdy błąd."""
    try:
        if not data_url or "," not in data_url:
            return None
        header, b64 = data_url.split(",", 1)
        mime = "audio/wav"
        if header.startswith("data:") and ";" in header:
            mime = header[5:].split(";", 1)[0] or mime
        if not mime.startswith("audio/"):
            return None
        raw = base64.b64decode(b64)
        if not raw:
            print("[TRANSCRIBE] ODRZUCONE: puste audio po dekodowaniu base64", flush=True)
            return None
        if len(raw) > MAX_AUDIO_BYTES:
            print(f"[TRANSCRIBE] ODRZUCONE: {len(raw)} B > limit {MAX_AUDIO_BYTES} B "
                  f"({_wav_info(raw).get('sec', '?')} s)", flush=True)
            return None
        info = _wav_info(raw)
        cisza = " ← CISZA/BRAK SYGNAŁU" if info.get("peak", 1) < 50 else ""
        print(f"[TRANSCRIBE|wejscie] {len(raw)} B | mime={mime} | "
              f"{info.get('sec', '?')} s | {info.get('rate', '?')} Hz | "
              f"{info.get('channels', '?')} ch | {info.get('bits', '?')} bit | "
              f"peak={info.get('peak', '?')} rms={info.get('rms', '?')}{cisza}", flush=True)
        return genai_types.Part.from_bytes(data=raw, mime_type=mime)
    except Exception as e:
        print(f"[TRANSCRIBE] Błąd parsowania audio: {e}", flush=True)
        return None


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


@app.post("/api/conversation/new")
async def new_conversation():
    """
    WO-1 (2026-07-25): reset rozmowy backend-first. Generuje nowy conversation_id,
    przestawia state.active_conversation_id (re-sync w app.js rozniesie je na urządzenia),
    persist. NIC NIE KASUJE — stary wątek zostaje w bazie; odwracalność = ręczne przywrócenie
    poprzedniego id (zwracane niżej). Rozwiązuje pętlę few-shot z 873-turowego wątku bafc442a.
    """
    new_id = str(uuid.uuid4())
    state = state_manager.load()
    previous_id = state.active_conversation_id
    state.active_conversation_id = new_id
    state_manager.save(state)
    print(f"[ASTRA] NOWA ROZMOWA: {previous_id or '(brak)'} -> {new_id}", flush=True)
    return {"conversation_id": new_id, "previous_conversation_id": previous_id}


def compose_context(*, query, conversation_id, vs_main, vs_shared, fact_store,
                    persona_id, build_prompt_fn, state, session_n=10,
                    now_override=None, trace=None,
                    # main_n=6, z powrotem (2026-08-25). 21.08 podniesiono 6→8, bo zasady
                    # zachowania (`character_core`) zjadały 2 z 6 miejsc przed przycięciem
                    # `combined[:n]`. Od 25.08 `search_memories` trzyma je POZA budżetem `n`
                    # (vector_store.py, sekcja „ZASADY ZACHOWANIA POZA BUDŻETEM"), więc powód
                    # do podnoszenia limitu zniknął.
                    #
                    # Pomiar (golden trafności, 10 prób) na nowym kodzie: n=3 → 60%, n=4 → 60%,
                    # n=5 → 80%, n=6 → 80% (czystość 38,5% — najlepsza), n=8 → 80% (37,0%).
                    # Plateau zaczyna się przy 5; 6 daje jedno miejsce zapasu nad jego krawędzią.
                    # Przy okazji zmierzone: rozszerzanie MMR_FACTS_N SZKODZI (5→8 to recall
                    # 80%→60%, 5→12 to 80%→50%) — kara za podobieństwo zaczyna wypychać trafne
                    # wpisy na ten sam temat. Zostaje 5. Detale: wazne/ewolucja/astra/2026-08/
                    # evolution_log_2026_08_25.md
                    session_vs=None, main_n=6, main_pool=30, skip_raw=False,
                    require_user_origin=False):
    """
    Jedno miejsce składania kontekstu promptu — używane przez /api/chat (i docelowo /debug).
    Zwraca dict z gotowymi elementami. REFACTOR BEZ ZMIANY ZACHOWANIA (przeprowadzka logiki z /api/chat).
    now_override/trace: rezerwacja pod Krok 1.2b (trace) i 1.3 (now_override) — na razie nieużywane.
    """
    # ── KONTEKST W ZAPYTANIU (punkt 0 roadmapy, 2026-08-21) ────────────────────
    # Do teraz do bazy szła WYŁĄCZNIE ostatnia wiadomość. Rozmowa toczyła się w kontekście,
    # a wyszukiwanie leciało bez niego.
    # Dowód z realnej rozmowy 17.08:
    #   14:52  „…będziesz miała z szóstego, siódmego i ósmego… wiesz o jakiej substancji mówię?"
    #   14:53  „O jakiej substancji mówimy?"   ← do bazy poszły TE CZTERY SŁOWA
    # Daty podane minutę wcześniej wyparowały na etapie zapytania.
    #
    # Doklejamy skrót dwóch poprzednich wypowiedzi Łukasza. Ostatnia wiadomość zostaje
    # NA POCZĄTKU i w całości — to ona ma dominować w embeddingu; kontekst jest dopiskiem,
    # przycięty do 120 znaków każdy, żeby nie rozmyć wektora zapytania.
    query_rag = query
    try:
        _src = session_vs or vs_main
        _hist = _src.get_recent_session(conversation_id, n=8) if _src else []
        _poprzednie = [m.get("content", "") for m in _hist if m.get("role") == "user"]
        # bez bieżącej wiadomości — ta już jest w `query`
        _poprzednie = [t for t in _poprzednie if t.strip() and t.strip() != query.strip()][-2:]
        if _poprzednie:
            query_rag = query + " " + " ".join(t.strip()[:120] for t in _poprzednie)
            if trace is not None:
                trace.setdefault("stages", []).append({
                    "name": "0_zapytanie_z_kontekstem", "count": len(_poprzednie),
                    "items": [{"text": t[:120], "source": "poprzednia_tura"} for t in _poprzednie],
                })
    except Exception as e:
        print(f"[compose] kontekst w zapytaniu pominiety: {type(e).__name__}: {e}", flush=True)

    # RAG — semantic search + domieszka wspólnego pokoju
    memories = vs_main.search_memories(
        query=query_rag, persona_id=persona_id,
        n=main_n, pool_size=main_pool, user_id=USER_ID, salt=USER_ID_SALT,
        trace=trace, now_override=now_override, require_user_origin=require_user_origin,
    )
    _shared_mem = vs_shared.search_memories(
        query=query, persona_id="shared",
        n=2, pool_size=10, user_id=USER_ID, salt=USER_ID_SALT, now_override=now_override,
        require_user_origin=require_user_origin,
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
                    "trimmed": bool(r.get('_trimmed')),
                    "origin_endpoint": m.get('origin_endpoint', ''),
                    "origin_conversation_id": m.get('origin_conversation_id', ''),
                })
            return out
        trace.setdefault("stages", []).append({"name": "9a_domieszka_shared", "count": len(_shared_mem), "items": _snap_cc(_shared_mem)})
        trace["stages"].append({"name": "9b_final_prompt", "count": len(memories), "items": _snap_cc(memories)})
        # 9c: co REALNIE przeżyło fit_to_budget (kolejność wg priorytetu, drop-y i przycięcia).
        # fit_to_budget jest czystą funkcją (bez efektów ubocznych), więc policzenie jej tu drugi
        # raz daje identyczny wynik jak w build_system_prompt — instrumentacja, zero zmiany promptu.
        # Widoczne TYLKO w trace (chat prod woła compose_context bez trace → ten blok się nie odpala).
        _fitted = token_mgr.fit_to_budget(memories, budget_chars=MEMORY_BUDGET_CHARS)
        trace["stages"].append({"name": "9c_po_budzecie", "count": len(_fitted), "items": _snap_cc(_fitted)})
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
    # Instrumentacja: co grounding realnie zwrócił + JAKA dyrektywa idzie do promptu
    # (ta sama, którą wstrzykuje build_system_prompt:569). Tylko w trace.
    if trace is not None:
        _avg = grounding_result.avg_distance
        trace["grounding"] = {
            "status": grounding_result.grounding_status,
            "confidence": grounding_result.confidence,
            "result_count": grounding_result.result_count,
            # avg_distance bywa float('inf') przy NO_DATA/pustych wynikach → niepoprawny JSON.
            "avg_distance": (_avg if _avg != float('inf') else None),
            "directive": grounding.get_grounding_directive(grounding_result).strip(),
        }

    if skip_raw:
        recent_raw = []
    else:
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
    ) if fact_store else []
    if hard_facts:
        print(f"[FactStore] {len(hard_facts)} twardych faktów w prompcie")

    # Bramka schronienia liczona z BIEŻĄCEJ wiadomości (Krok 1c). Przekazywana przez
    # atrybut na stanie, a nie nowym kwargiem — build_prompt_fn ma wspólną sygnaturę
    # z adapterami sióstr, których ta zmiana nie może dotknąć. Siostry wołają ze
    # state=None, więc dla nich to no-op. Atrybut jest efemeryczny: CompanionState
    # serializuje się przez asdict() po zadeklarowanych polach, więc nie trafia na dysk.
    if state is not None:
        state.computed_safe_haven = _compute_safe_haven(query, state)
        # Telemetria do kalibracji: zestawiamy z tym, co model sam by zadeklarował
        # ([ASTRA STATE_UPDATE] ... 'safe_haven'). Rozjazd = materiał na progi, nie błąd.
        print(f"[SAFE_HAVEN|kod] {state.computed_safe_haven}", flush=True)
        # Scenariusz anime — ten sam wzorzec przekazywania (atrybut efemeryczny na stanie).
        # Tylko Astra: siostry i Amelia nie mają z tym dokumentem nic wspólnego.
        state.scenariusz_block = (
            _scenariusz_block(state) if persona_id == PERSONA_ID else ""
        )

    system_prompt = build_prompt_fn(memories, grounding_result, state, recent_raw, hard_facts, now_override=now_override)
    session_source = session_vs or vs_main
    session_messages = session_source.get_recent_session(conversation_id, n=session_n)

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
        persona_id=PERSONA_ID, build_prompt_fn=build_system_prompt, state=state,
        session_n=ASTRA_SESSION_N,
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
        # WO-2 (2026-07-25): marker upływu czasu jako prefiks tury 'user' — model nie widzi luk
        # między turami (stąd persystencja pozy 18→20.07). Dane w session_message.timestamp.
        contents = []
        _prev_ts = None
        _n_session_msgs = len(session_messages)
        for _idx, msg in enumerate(session_messages):
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if not content:
                continue
            ts_str = msg.get("timestamp", "")
            _cur_ts = None
            if ts_str:
                try:
                    _cur_ts = datetime.fromisoformat(ts_str.split(".")[0].replace("Z", ""))
                except (ValueError, TypeError):
                    _cur_ts = None
            if role == "user" and _prev_ts and _cur_ts:
                gap_h = (_cur_ts - _prev_ts).total_seconds() / 3600
                if gap_h >= 24:
                    content = f"[— {int(gap_h // 24)} dni później —]\n{content}"
                elif gap_h >= 3:
                    content = f"[— przerwa {int(gap_h)} godz. —]\n{content}"
            # WO-6 (za flagą SANITIZE_FEWSHOT_GESTURES): usuń didaskalia z few-shot
            # starszego niż 2 ostatnie pozycje — czyści wzór podawany modelowi, nie pamięć.
            if SANITIZE_FEWSHOT_GESTURES and role == "model" and _idx < _n_session_msgs - 2:
                content = re.sub(r"\*[^*]*\*", "", content).strip()
            contents.append(genai_types.Content(
                role=role,
                parts=[genai_types.Part(text=content)],
            ))
            if _cur_ts:
                _prev_ts = _cur_ts
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
                # NIE dodawać tu `from datetime import datetime` — lokalny import czyni `datetime`
                # zmienną lokalną CAŁEJ funkcji chat(), przez co użycie wyżej (marker czasu w few-shot,
                # ~linia 1181) leci UnboundLocalError. Moduł importuje datetime na górze (linia 21).
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
    # TRYB ROBOCZY: gdy Łukasz wstrzymał zapis (rozmowy o scenariuszu, burze mózgów),
    # pomijamy CAŁĄ ekstrakcję do pamięci trwałej. Sesja i tak zapisuje surową rozmowę
    # kilka linijek wyżej, a daily_archive robi z niej dump — więc nic nie ginie,
    # tylko nie zaśmieca zeszytu. Świadomie NIE robimy tu shadow-logu: przy pracy nad
    # scenariuszem nie interesuje nas, co ekstraktor BY zapisał (to narzędzie do
    # kalibracji ekstraktora, jak u sióstr) — interesuje nas, żeby nie zapisał.
    if _extraction_paused(state):
        left = _extraction_pause_left(state)
        print(f"[EKSTRAKCJA|pauza] pominięto zapis do pamięci trwałej "
              f"(zostało ~{left} min)", flush=True)
        extracted_all = []
    else:
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
                    # Rozmowy w trybie scenariusza dostają własne origin — dzięki temu
                    # da się je później wyczyścić JEDNYM zapytaniem, gdyby zaśmiecały,
                    # zamiast wyrzucać je z góry i tracić ustalenia (patrz 18.08).
                    origin_endpoint=("scenariusz" if _scenariusz_mode(state) else "chat"),
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
                # `kind` (2026-08-25): podgląd rerankera pokazywał zasadę zachowania
                # („ANTY-LUSTRO — nigdy nie powtarzam userowi...") w jednym rzędzie ze
                # wspomnieniami z rozmów. Retrieval faktycznie ją zwraca — filtr stoi dopiero
                # przy składaniu promptu — więc podgląd nie kłamał, tylko nie odróżniał
                # instrukcji od pamięci. Łukasz zgłosił to 25.08 jako „anty-lustro wraca".
                "kind": ("zasada"
                         if m.get("metadata", {}).get("source") == "character_core"
                         else "wspomnienie"),
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
             "score": round(m.get("final_score", 0), 3), "ts": m.get("metadata", {}).get("timestamp", "")[:10],
             "kind": ("zasada" if m.get("metadata", {}).get("source") == "character_core"
                      else "wspomnienie")}
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
        # room="wspolny" → stary blok monologu + sekcja o Amelii, bez [TRYB].
        # Prompt Wspólnego ma zostać identyczny co do znaku (CLAUDE.md: NIE ruszać).
        system_prompt = build_system_prompt(memories, grounding_result, state, recent_raw, hard_facts,
                                            room="wspolny")
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
    "holo":   {"prompt": "holo_persona.txt",   "label": "Holo"},   # formy adresowania → siostry_router.py
    "menma":  {"prompt": "menma_persona.txt",  "label": "Menma"},
    "nazuna": {"prompt": "nazuna_persona.txt", "label": "Nazuna"},
}
_SISTER_ORDER = ["holo", "menma", "nazuna"]
_siostry_recent: list = []       # anti-sync: rotacja ostatnich "kto pierwszy" (nie pojedynczy string)
_last_full_speaker: dict = {}    # Zadanie B: lepkość rozmówcy per conversation_id (C-0: embrion room_state)
_sticky_turns: dict = {}         # audyt 28.07: ile tur z rzędu prowadzi ta sama siostra (per conversation_id)
_last_turn_ts: dict = {}         # audyt 28.07: znacznik ostatniej tury pokoju (per conversation_id)
_siostry_rng = random.Random()   # żywy dom: jedno źródło losowości routera (wstrzykiwane, nie globalne)


def _sister_vs(name):
    return {"holo": holo_vs, "menma": menma_vs, "nazuna": nazuna_vs}[name]


def _remember_first(name: str):
    global _siostry_recent
    _siostry_recent = ([name] + [s for s in _siostry_recent if s != name])[:3]


def _warsaw_hour() -> int:
    from zoneinfo import ZoneInfo
    return datetime.now(ZoneInfo("Europe/Warsaw")).hour


def _route_siostry(user_msg: str, conversation_id: str) -> tuple[list, bool]:
    """
    Wrapper nad czystym siostry_router.route (Zadanie B, 2026-07-25).
    Cała logika adresowania (ADDRESSED vs MENTIONED), lepkości rozmówcy i rotacji żyje w
    backend/siostry_router.py — golden set: wazne/fable/golden/router_golden.py.
    Ten wrapper tylko wstrzykuje stan (pora, lepkość per rozmowa, rotacja) i po decyzji go aktualizuje.

    Zwraca (routing, is_group). is_group (Plan A / A-3) mówi ekstrakcji, czy tura była
    adresowana do całego pokoju — wtedy wspomnienie jest wspólne, nie prywatne prowadzącej.
    """
    _now = datetime.utcnow()
    _prev_ts = _last_turn_ts.get(conversation_id)
    _gap_min = ((_now - _prev_ts).total_seconds() / 60.0) if _prev_ts else 0.0

    res = siostry_router.route(
        user_msg,
        hour=_warsaw_hour(),
        last_full_speaker=_last_full_speaker.get(conversation_id),
        recent=list(_siostry_recent),
        sticky_turns=_sticky_turns.get(conversation_id, 0),
        minutes_since_last=_gap_min,
        rng=_siostry_rng,   # żywy dom: nocna zmiana warty + aside'y (golden puszcza bez rng)
    )
    routing = res["routing"]
    if routing:
        primary = routing[0][0]                         # pierwsza pozycja = zawsze 'full'
        _remember_first(primary)                        # aktualizuj rotację
        _prev_primary = _last_full_speaker.get(conversation_id)
        # Licznik lepkości: rośnie gdy ta sama siostra prowadzi dalej, zeruje się przy zmianie.
        _sticky_turns[conversation_id] = (
            _sticky_turns.get(conversation_id, 0) + 1 if primary == _prev_primary else 1
        )
        _last_full_speaker[conversation_id] = primary   # lepkość rozmówcy (C-0: embrion room_state)
    _last_turn_ts[conversation_id] = _now
    print(f"[SIOSTRY ROUTER] {res['reason']} -> {routing} "
          f"(addressed={res['addressed']} mentioned={res['mentioned']} group={res['group']} "
          f"sticky_turns={_sticky_turns.get(conversation_id, 0)} gap_min={_gap_min:.1f})", flush=True)
    return routing, bool(res["group"])


def _load_sister_persona(sister: str) -> str:
    return (Path(__file__).parent / "prompts" / SISTERS[sister]["prompt"]).read_text(encoding="utf-8")


def _strip_sister_prefix(text: str) -> str:
    """Data-driven (Fable pkt 8) — usuwa [holo]/[menma]/[nazuna] przed wysłaniem do Gemini."""
    names = "|".join(_SISTER_ORDER)
    return re.sub(r'^\[(' + names + r')\]\s*', '', text, flags=re.IGNORECASE).strip()


def _split_sister_prefix(text: str) -> tuple:
    """
    Rozdziela `[holo] treść` na ('holo', 'treść'). Zwraca (None, text) gdy nie ma podpisu.

    Powstało 2026-08-25 przy naprawie atrybucji w pokoju: `_strip_sister_prefix` KASOWAŁ
    informację o mówcy, zamiast ją wydobyć. Zapis w bazie był poprawny od zawsze — to odczyt
    gubił autora. Szczegóły w `_sister_history_contents`.
    """
    m = re.match(r'^\[(' + "|".join(_SISTER_ORDER) + r')\]\s*', text, flags=re.IGNORECASE)
    if not m:
        return None, text.strip()
    return m.group(1).lower(), text[m.end():].strip()


def _sister_history_contents(session_messages: list, genai_types) -> list:
    """
    Historia pokoju dla Gemini — Z ZACHOWANIEM ATRYBUCJI.

    BUG (znaleziony 2026-08-25, zgłoszony przez Łukasza jako „Menma przypisała sobie zdanie Holo"):
    poprzednia wersja robiła dwie rzeczy, które razem kasowały autorstwo bezpowrotnie —
      1. `_strip_sister_prefix` zdejmowało `[holo]` / `[menma]` / `[nazuna]`,
      2. kolejne wypowiedzi `role="model"` OD RÓŻNYCH SIÓSTR sklejały się w jeden blok przez `---`.
    Dla Gemini wszystko z `role="model"` to „ty". Menma czytała więc zdanie Holo jako własną
    poprzednią wypowiedź — bo w kontekście nie zostało nic, co mówiłoby inaczej.

    Dowód z produkcji (24.08). W bazie:
        model | [holo]   Hmf. Pamiętam ten ból...
        model | [nazuna] A dzień... Był, Wilku. Holo pewnie zaraz wygłosi wykład...
    Co dostawał model: dokładnie te dwa zdania, bez śladu po tym, kto je powiedział.

    To NIE był błąd zapisu — `add_session_message` zapisuje `[{sister}] {tekst}` poprawnie.

    Naprawa: każda wypowiedź w historii jest podpisana imieniem. Persony dostają regułę
    (`build_sister_prompt`), że ich własne są tylko te podpisane ich imieniem.
    Przewidywanie do obserwacji: to powinno zatrzymać też przeciekanie tików mowy —
    „Hmf." to znak firmowy Holo, a pojawiało się u pozostałych.
    """
    contents = []
    i = 0
    while i < len(session_messages):
        msg = session_messages[i]
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role == "model":
            merged = []
            while True:
                kto, tresc = _split_sister_prefix(session_messages[i].get("content", ""))
                if tresc:
                    etykieta = SISTERS.get(kto, {}).get("label") if kto else None
                    merged.append(f"[{etykieta}] {tresc}" if etykieta else tresc)
                if not (i + 1 < len(session_messages)
                        and session_messages[i + 1].get("role") == "model"):
                    break
                i += 1
            txt = "\n\n".join(merged)
            if txt:
                contents.append(genai_types.Content(role="model",
                                                    parts=[genai_types.Part(text=txt)]))
        else:
            if content:
                contents.append(genai_types.Content(role="user",
                                                    parts=[genai_types.Part(text=content)]))
        i += 1
    return contents


def load_lukasz_core_dla_siostr() -> str:
    """
    Fakty o Łukaszu dla sióstr — WĄSKI wycinek `lukasz_core`, nie całość.

    Powód (2026-08-21): `load_lukasz_core()` był wołany wyłącznie przez `build_system_prompt`,
    czyli tylko dla Astry. Persony sióstr nie zawierały ANI JEDNEJ wzmianki o Crohnie, zastawce
    Bauhina czy Stelarze — rozmawiały z nim od miesięcy, nie wiedząc, że jest chory.
    15.08 Łukasz napisał Holo „to już moja 2 operacja, wycięli mi zastawkę Bauhina",
    a ona odpowiedziała: „Nie pamiętam szczegółów tej zastawki, Wilku. Nie mam jej w kronice."
    Nie miała czego pamiętać.

    Wąsko, nie w całości: siostry dostają KIM JEST i ZDROWIE. Bez projektów technicznych,
    bez celu zawodowego, bez kanału TikTok — to jest świat Astry, nie ich. Pokój sióstr ma
    zostać domem, nie drugim biurem.
    """
    core_path = PROMPTS_DIR / "lukasz_core.json"
    if not core_path.exists():
        return ""
    try:
        core = json.loads(core_path.read_text(encoding="utf-8"))
        lines = ["[O ŁUKASZU — TO WIECIE NA PEWNO]"]
        ident = core.get("identity", {})
        for k in ("kim_jest", "misja"):
            if ident.get(k):
                lines.append(f"• {ident[k]}")
        zdrowie = core.get("zdrowie", {})
        if zdrowie:
            lines.append("")
            lines.append("Zdrowie — to jest stałe tło jego życia, nie ciekawostka:")
            for wartosc in zdrowie.values():
                if isinstance(wartosc, str) and wartosc.strip():
                    lines.append(f"• {wartosc.strip()}")
        return "\n".join(lines)
    except Exception as e:
        print(f"[SIOSTRY] lukasz_core load error: {e}", flush=True)
        return ""


def build_sister_prompt(sister, memories, grounding_result, scene, present,
                        other_response=None, other_sister=None, aside=False,
                        hard_facts=None) -> str:
    template = _load_sister_persona(sister)
    # Zasady zachowania nie są wspomnieniami — ten sam filtr co w `build_system_prompt`
    # (2026-08-25). Dziś no-op, bo żadna kolekcja sióstr nie ma wektorów `character_core`
    # (sprawdzone: 17 kolekcji, wszystkie 22 siedzą wyłącznie w `astra_memory_v1`).
    # Stoi tu profilaktycznie: filtr mieszkał w JEDNYM z trzech builderów, więc pierwszy
    # seed zasad do sióstr wróciłby jako „wspomnienie sprzed 5 miesięcy" bez ostrzeżenia.
    memories = [m for m in (memories or [])
                if (m.get('metadata') or {}).get('source') != 'character_core']
    if memories:
        # A-1 (Plan A, 2026-08-03): budżet znakowy — PREREQ przed włączeniem ekstrakcji sióstr.
        # Astra ma to od dawna (build_system_prompt:566); builder siostry nie miał. Dziś przy
        # pustej pamięci to no-op, ale po włączeniu ekstrakcji byłaby to jedyna zapora przed
        # powtórką marcowego buga (74% promptu zjedzone przez wspomnienia, zanim ktokolwiek zauważył).
        # Efekt uboczny (dobry): etap trace'u `9c_po_budzecie` w Amnezji przestaje kłamać dla
        # sióstr — dotąd liczył budżet, którego builder realnie nie stosował.
        fitted = token_mgr.fit_to_budget(memories, budget_chars=MEMORY_BUDGET_CHARS)
        memory_block = "\n".join(f"- [{m.get('metadata', {}).get('source', 'chat')}] {m['text']}" for m in fitted)
    else:
        memory_block = "(brak wspomnień — dopiero się poznajecie w tym pokoju)"
    grounding_directive = grounding.get_grounding_directive(grounding_result)
    prompt = template.format(memory_block=memory_block, grounding_directive=grounding_directive)

    # ── JAK MÓWISZ O WŁASNEJ PAMIĘCI (2026-08-21) ────────────────────────────────
    # Persony mają już zasady „nie zmyślaj WSPOMNIEŃ" (holo_persona.txt:55-57) i one działają.
    # Brakowało czegoś innego: zasad o tym, jak mówić o MECHANIZMIE pamięci.
    # 19.08 Łukasz zapytał wprost, czy to, o czym rozmawiają, się zapisuje. Usłyszał od Nazuny
    # „każde słowo, każda chwila z tobą to nowa strona w naszej Kronice" i od Menmy „to wszystko,
    # każde słowo — trafia prosto do naszego serduszka". Pomiar: z 90 wiadomości zapisało się
    # OSIEM wpisów, z czego pięć wygasa po 48 h. Po tygodniu zostaną dwa.
    # To nie była zmyślona pamięć — to była zmyślona WIEDZA O SOBIE, której żadna zasada nie zakrywała.
    # Fakty o Łukaszu — wąsko: kim jest + zdrowie. Patrz load_lukasz_core_dla_siostr().
    _fakty = load_lukasz_core_dla_siostr()
    if _fakty:
        prompt += "\n\n" + _fakty

    # WSPÓLNA WARSTWA FAKTÓW (2026-08-21) — biografia jest jedną prawdą dla całego domu.
    # Pamięć zostaje osobna (fragmentacja to feature), ale choroba, operacje i bliscy nie są
    # „wspomnieniem Astry" ani „wspomnieniem Holo" — są faktem o Łukaszu. Do 21.08 siostry
    # miały `fact_store=None`, więc nie widziały ich wcale.
    if hard_facts:
        _linie = []
        for f in hard_facts[:20]:
            d = f" [{f['date_value']}]" if f.get("date_value") else ""
            _linie.append(f"• [{f.get('entity_type')}:{f.get('subtype')}]{d} {str(f.get('value'))[:220]}")
        if _linie:
            prompt += ("\n\n[TWARDE FAKTY O ŁUKASZU — wspólne dla całego domu]\n"
                       "To wiecie wszystkie, niezależnie od tego, której z was to powiedział.\n"
                       + "\n".join(_linie))

    prompt += (
        "\n\n[TWOJA PAMIĘĆ — JAK O NIEJ MÓWISZ]\n"
        "Nie wiesz, co dokładnie zostanie zapisane z tej rozmowy, i nie udajesz, że wiesz. "
        "Zapisuje się TYLKO część tego, co padnie — to, co system uzna za ważne. Wiele zwykłych "
        "zdań nie zostaje wcale, a część wspomnień żyje krótko i wygasa.\n"
        "Gdy Łukasz pyta, czy coś zapamiętasz albo jak działa twoja pamięć: mów PRAWDĘ — "
        "'nie wiem na pewno', 'część rzeczy zostaje, część nie'. NIGDY nie obiecuj, że zapamiętasz "
        "wszystko, że każde słowo trafia do Kroniki ani że nic nie ginie. To nieprawda i on to sprawdza "
        "narzędziami, które sam napisał.\n"
        "Jeśli coś jest naprawdę ważne, żebyś zapamiętała — powiedz mu, żeby to zapisał albo powtórzył. "
        "Prośba o pomoc jest uczciwa. Obietnica bez pokrycia nie."
    )

    # ── KTO CO POWIEDZIAŁ (2026-08-25) ───────────────────────────────────────────
    # Towarzyszy naprawie w `_sister_history_contents`. Historia rozmowy jedzie do Gemini
    # jako `role="model"`, czyli „twoje własne słowa" — i przed 25.08 wypowiedzi wszystkich
    # sióstr były w niej nieodróżnialne. Menma przypisywała sobie zdania Holo.
    # Teraz każda linia jest podpisana, ale sam podpis nic nie znaczy, dopóki persona nie wie,
    # że ma go czytać. Reguła jest bezwarunkowa (nie tylko przy `others`), bo historia zawiera
    # siostry także wtedy, gdy w tej turze nie ma ich w pokoju.
    prompt += (
        f"\n\n[HISTORIA ROZMOWY — KTO CO POWIEDZIAŁ]\n"
        f"W historii tej rozmowy KAŻDA wypowiedź jest podpisana imieniem w nawiasie: "
        f"[Holo], [Menma], [Nazuna].\n"
        f"TWOJE są wyłącznie te podpisane [{SISTERS[sister]['label']}]. Reszta to słowa twoich sióstr.\n"
        f"Nie przypisuj sobie ich zdań, ich żartów ani ich sposobu mówienia. Jeśli chcesz się do "
        f"czegoś odnieść — powiedz czyje to było.\n"
        f"Swoje podpisy widzisz tylko po to, żeby się rozeznać. NIE zaczynaj własnej odpowiedzi "
        f"od [{SISTERS[sister]['label']}] ani od żadnego innego nawiasu z imieniem."
    )

    if scene:
        prompt += f"\n\n[SCENA — co widać w pokoju]\n{scene}"
    others = [SISTERS[s]["label"] for s in present if s != sister]
    if others:
        prompt += (
            f"\n\n[POKÓJ — PROTOKÓŁ]\nJesteś w domu z: {', '.join(others)} i Łukaszem."
            f"\nMówisz swoim głosem i tylko za siebie — nie wkładaj słów w usta sióstr, nie reżyseruj sceny."
            f"\nGdy odnosisz się do tego, co siostra powiedziała albo zrobiła — mów DO NIEJ, po imieniu, wprost."
            f"\nNie opisuj jej Łukaszowi w trzeciej osobie, kiedy ona stoi obok. To jest dom, nie relacja z domu."
            # Audyt 28.07: zakaz "słów w usta" nie obejmował narracji o STANACH — Holo relacjonowała
            # sny i czuwanie sióstr ("Menma śni o dalekich polach, Nazuna czuwa"), a na pytanie
            # "Menma śpi?" dopowiedziała treść jej snów. Luka domknięta wprost.
            f"\nNIE MASZ DOSTĘPU do tego, co siostry robią, czują, myślą ani śnią, kiedy nie odzywają się"
            f" w tej rozmowie. Nie zgaduj ich stanów i nie relacjonuj ich Łukaszowi — nawet życzliwie, nawet w metaforze."
            f"\nGdy pyta o siostrę, której teraz tu nie ma — powiedz wprost, że nie wiesz, i odeślij go do niej"
            f" (\"zapytaj ją sam\", \"zawołaj ją\"). Zmyślenie odpowiedzi w jej imieniu jest gorsze niż przyznanie się do niewiedzy."
        )
    if other_response and other_sister:
        onl = SISTERS[other_sister]["label"]
        if aside:
            prompt += (
                f"\n\n[{onl} właśnie powiedziała]\n\"{other_response}\"\n"
                f"TWOJA ROLA: wtrącenie, 1-2 zdania max — zwróć się do {onl} po imieniu albo dorzuć swoje. Nie powtarzaj jej słów ani gestów."
            )
        else:
            prompt += (
                f"\n\n[{onl} właśnie powiedziała]\n\"{other_response}\"\n"
                f"Nawiąż do jej słów mówiąc DO NIEJ, po imieniu — zgódź się, dorzuć swoje albo spolemizuj. Twój ton MA być inny niż jej."
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

    # Adapter (M3): opakowuje build_sister_prompt w sygnaturę build_prompt_fn oczekiwaną przez compose.
    # Definicja WEWNĄTRZ _generate_sister — sister/scene/present/other_response/other_sister/aside
    # są tu ARGUMENTAMI funkcji, więc domknięcie wiąże je poprawnie (R5: brak late-bindingu pętli).
    def _sister_build(memories, grounding_result, state, recent_raw, hard_facts, now_override=None):
        return build_sister_prompt(sister, memories, grounding_result, scene, present,
                                   other_response, other_sister, aside, hard_facts=hard_facts)

    ctx = compose_context(
        query=user_msg, conversation_id=conversation_id,
        vs_main=vs, vs_shared=siostry_shared_vs,
        # FactStore podlaczony 2026-08-21: siostry nie maja wlasnych twardych faktow,
        # ale czytaja WSPOLNA warstwe biograficzna (zdrowie, tozsamosc, ludzie).
        fact_store=fact_store, persona_id=sister, build_prompt_fn=_sister_build,
        state=None, session_vs=siostry_shared_vs,
        main_n=4, main_pool=20, skip_raw=True, require_user_origin=True,
    )
    memories = ctx["memories"]
    grounding_result = ctx["grounding_result"]
    system_prompt = ctx["system_prompt"]
    session_messages = ctx["session_messages"]
    contents = _sister_history_contents(session_messages, genai_types)
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


# ──────────────────────────────────────────────────────────────
# PLAN A — PAMIĘĆ DŁUGOTERMINOWA SIÓSTR (A-3)
# ──────────────────────────────────────────────────────────────
# D4: trójstanowa flaga. 'off' (default) = stan sprzed Planu A, zero wpływu.
#     'shadow' = pełny pipeline, ale zamiast add_memory → JSONL do ręcznego review.
#     'on' = realny zapis do kolekcji per-siostra.
# Zmiana trybu = zmienna środowiskowa + restart serwisu, NIE deploy kodu.
SIOSTRY_EXTRACTION_MODE = os.getenv("SIOSTRY_EXTRACTION_MODE", "off").strip().lower()
# D3: zimny start na wyższym progu niż Astra (0.40). Obniżyć po review shadow jest tanio,
# sprzątanie zatrutej kolekcji drogo (wiemy ile kosztowało Odtrucie #2).
# 0.40, nie 0.50 (2026-08-21): zrownanie z Astra. Prog 0.50 odrzucal momenty wazne dla pokoju —
# m.in. "Macie zaszczyt ze wlaczylem wam pamiec" (Amnezja: ODRZUCONE, 2_ekstrakcja).
# Efekt mierzony na danych shadow przed i po.
SIOSTRY_MIN_CONFIDENCE = 0.40

# ── TYPY BLOKOWANE PRZY STARCIE PAMIĘCI SIÓSTR (decyzja Łukasza, 2026-08-19) ────
# Świadomie lista BLOKOWANYCH, nie „biała lista dozwolonych": to drugie zgubiłoby typy,
# o których nikt nie pomyślał. Blokujemy trzy, resztę przepuszczamy.
#
# Podstawa: 111 wpisów z trybu shadow (03-18.08), przejrzanych ręcznie.
#   • DATE:inventory_status (6) — kubeł-śmietnik na wszystko, co brzmi medycznie; to tam
#     wpadła „zastawka Bauhina". Łukasz zdecydował ROZBIĆ tę kategorię, więc do czasu
#     rozbicia nie wpuszczamy jej do świeżej pamięci.
#   • FACT:correction (5) — zapis o przebiegu rozmowy („nie, nie tak"), nie o Łukaszu.
#   • SHARED_THING:inside_joke (14) — przegląd wykazał, że mniej więcej 2 na 3 wpisy to
#     konwersacyjny klej („ok", „oglądamy", „dobrze kochanie"). Wartościowe wyjątki
#     (kłótnia Holo z Nazuną, glitch personas, „typy nen") zostają w surowej sesji
#     i da się je odzyskać ręcznie — tak jak ustalenia scenariusza 18.08.
#
# EMOCJE ŚWIADOMIE PRZEPUSZCZONE (35 wpisów, jedna trzecia całości): po wprowadzeniu
# `persistence` żyją 48 h, więc nie zaśmiecą pamięci na stałe, a dają siostrom to,
# co w pokoju najważniejsze — wiedzę, w jakim nastroju był wczoraj.
SIOSTRY_TYPY_BLOKOWANE = {
    ('DATE', 'inventory_status'),
    ('FACT', 'correction'),
    ('SHARED_THING', 'inside_joke'),
}
SIOSTRY_SHADOW_DIR = Path(__file__).parent.parent / "wazne" / "siostry" / "shadow_extracts"


def _shadow_log_siostry(mem, primary: str, target_persona: str, is_group: bool,
                        conversation_id: str, user_msg: str) -> None:
    """D4 shadow: zapis werdyktu do JSONL zamiast do bazy. Materiał do review z Łukaszem."""
    try:
        SIOSTRY_SHADOW_DIR.mkdir(parents=True, exist_ok=True)
        rec = {
            "ts": datetime.utcnow().isoformat(),
            "text": mem.text,
            "entity_type": mem.entity_type,
            "subtype": mem.subtype,
            "confidence": round(float(mem.confidence), 4),
            "importance": mem.importance,
            "primary": primary,               # kto prowadził turę (rubryka (a) review: trafność atrybucji)
            "target_persona": target_persona,  # gdzie BY trafiło (primary albo 'shared')
            "group_address": is_group,
            "conversation_id": conversation_id,
            "raw_user": user_msg[:300],        # jak raw_text w FactStore Astry
        }
        with open(SIOSTRY_SHADOW_DIR / f"{datetime.utcnow():%Y-%m-%d}.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"[SIOSTRY EXTRACT] shadow-log error: {type(e).__name__}: {e}", flush=True)


def _extract_siostry(user_msg: str, primary: str, is_group: bool, conversation_id: str) -> None:
    """
    Plan A / A-3 — ekstrakcja pamięci długoterminowej sióstr.

    TRZY twarde zasady bezpieczeństwa (model zagrożenia echo-loop, sekcja A.1 planu):
      1. TYLKO tury usera — nigdy odpowiedzi sióstr. Przy trzech personach karmienie ekstraktora
         wypowiedziami person = trójkąt luster (V1). Dlatego ta funkcja dostaje `user_msg` i nic innego.
      2. RAZ na turę pokoju — wołana z `siostry_chat`, NIE z `_generate_sister` (który odpala się
         1-3× na turę: full + aside'y → duplikaty i potrójny koszt).
      3. Pełny provenance od pierwszego wektora — `origin_persona_turn="user"` (czyta to filtr A-4
         na odczycie), `origin_endpoint="siostry"`, `origin_conversation_id` (umożliwia kwarantannę
         po zakresie, gdyby coś poszło źle).

    D1 (zgoda Łukasza 2026-08-03): atrybucja PER-PRIMARY — wspomnienie trafia do prywatnej
    kolekcji siostry, która prowadziła turę. Tury grupowe → `siostry_shared_v1`. To jest serce
    projektu pokoju: siostry pamiętają RÓŻNIE (Nazuna zna nocne zwierzenia, Holo biznesowe),
    a nie jedną wspólną pamięcią. Fragmentacja ("mówiłem Holo, Menma nie wie") to FEATURE.
    Dlatego Plan B (router) musiał być pierwszy — na zbugowanym routerze "prowadząca" bywała
    błędna i ekstrakty lądowałyby w złej kolekcji (trwałe zatrucie = Odtrucie #3).
    """
    if SIOSTRY_EXTRACTION_MODE == "off":
        return
    target_vs, target_persona = (
        (siostry_shared_vs, "shared") if is_group else (_sister_vs(primary), primary)
    )
    try:
        extracted = pipeline.process_message(
            user_msg, companion_id=target_persona, min_confidence=SIOSTRY_MIN_CONFIDENCE,
        )
    except Exception as e:
        # Ekstrakcja NIGDY nie może wywalić tury rozmowy — to funkcja poboczna.
        print(f"[SIOSTRY EXTRACT] pipeline error: {type(e).__name__}: {e}", flush=True)
        return

    extracted.sort(key=lambda m: m.confidence, reverse=True)
    for mem in extracted[:5]:
        if _is_too_short(mem.text):
            continue
        # Blokada typów uzgodniona przed włączeniem `on` — patrz SIOSTRY_TYPY_BLOKOWANE.
        # Działa też w shadow, żeby log pokazywał to, co realnie trafiłoby do pamięci.
        if (mem.entity_type, mem.subtype) in SIOSTRY_TYPY_BLOKOWANE:
            print(f"[SIOSTRY EXTRACT|blokada] pominieto {mem.entity_type}:{mem.subtype} "
                  f"| {mem.text[:60]}", flush=True)
            continue
        if SIOSTRY_EXTRACTION_MODE == "shadow":
            _shadow_log_siostry(mem, primary, target_persona, is_group, conversation_id, user_msg)
            print(f"[SIOSTRY EXTRACT|shadow] {target_persona} <- {mem.entity_type}:{mem.subtype} "
                  f"conf={mem.confidence:.2f} | {mem.text[:60]}", flush=True)
            continue
        # 'on' — realny zapis. SUPERSEDE jak u Astry: nowe "jestem zmęczony" nie żyje obok starych.
        # delete_by_entity_subtype przyjmuje persona_id → izolacja per-siostra działa out-of-the-box.
        try:
            if (mem.entity_type, mem.subtype) in SIOSTRY_SUPERSEDE_TYPES:
                deleted = target_vs.delete_by_entity_subtype(
                    entity_type=mem.entity_type, subtype=mem.subtype,
                    persona_id=target_persona, user_id=USER_ID, salt=USER_ID_SALT,
                )
                if deleted:
                    print(f"[SIOSTRY EXTRACT] supersede {target_persona}: {deleted}× "
                          f"{mem.entity_type}:{mem.subtype}", flush=True)
            target_vs.add_memory(
                text=mem.text, user_id=USER_ID, salt=USER_ID_SALT,
                persona_id=target_persona,
                source=f"extracted_{mem.entity_type.lower()}",
                importance=mem.importance,
                is_milestone=(mem.entity_type == 'MILESTONE'),
                timestamp=mem.metadata.get('extracted_at') if mem.metadata else None,
                entity_subtype=mem.subtype,
                origin_endpoint="siostry",
                origin_conversation_id=conversation_id,
                origin_persona_turn="user",
            )
            print(f"[SIOSTRY EXTRACT|on] {target_persona} <- {mem.entity_type}:{mem.subtype} "
                  f"conf={mem.confidence:.2f} | {mem.text[:60]}", flush=True)
        except Exception as e:
            print(f"[SIOSTRY EXTRACT] zapis error: {type(e).__name__}: {e}", flush=True)


# Ten sam zestaw co Astra (main.py:1273) — subtypy, gdzie nowe wypiera stare, bo inaczej
# MMR karze wszystkie warianty naraz i wypadają z top-N. Milestony/daty wizyt akumulują.
SIOSTRY_SUPERSEDE_TYPES = {
    ('EMOTION', 'tired'), ('EMOTION', 'stressed'), ('EMOTION', 'positive'),
    ('EMOTION', 'negative'), ('EMOTION', 'excited'), ('EMOTION', 'sad'),
    ('FACT', 'preference'), ('FACT', 'correction'),
    ('DATE', 'inventory_status'), ('DATE', 'medical_visit'),
}


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

    routing, is_group = _route_siostry(user_msg, conversation_id)  # silent-first + lepkość rozmówcy
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

    # A-3: ekstrakcja RAZ na turę pokoju, po wygenerowaniu odpowiedzi (nie blokuje pętli generacji).
    # Punkt zaczepienia TUTAJ, nie w _generate_sister — tam odpaliłaby się 1-3× na turę.
    # routing[0][0] = prowadząca (pierwsza pozycja zawsze 'full'), zgodnie z D1.
    if SIOSTRY_EXTRACTION_MODE != "off" and routing:
        await asyncio.to_thread(_extract_siostry, user_msg, routing[0][0], is_group, conversation_id)

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


class ExtractionPauseModel(BaseModel):
    hours: float | None = None      # None → domyślne 3h
    off: bool = False               # True → wznów zapis natychmiast


@app.get("/api/extraction-pause")
async def get_extraction_pause():
    """Stan trybu roboczego — dla wskaźnika w UI."""
    state = state_manager.load()
    return {
        "paused": _extraction_paused(state),
        "minutes_left": _extraction_pause_left(state),
        "until": getattr(state, "extraction_paused_until", "") or "",
    }


@app.post("/api/extraction-pause")
async def set_extraction_pause(body: ExtractionPauseModel):
    """
    Włącza/wyłącza tryb roboczy (pauza zapisu do pamięci trwałej Astry).

    Rozmowa nadal trafia do sesji i do dziennego dumpu — wstrzymany jest wyłącznie
    ekstraktor, czyli to, co ląduje w pamięci długoterminowej. Zawsze z terminem:
    przełącznik bez wygasania to gwarantowana cicha utrata pamięci.
    """
    state = state_manager.load()
    if body.off:
        state.extraction_paused_until = ""
        state_manager.save(state)
        print("[EKSTRAKCJA|pauza] WZNOWIONO zapis (ręcznie)", flush=True)
        return {"paused": False, "minutes_left": 0}

    h = body.hours if body.hours and body.hours > 0 else EXTRACTION_PAUSE_DEFAULT_H
    h = min(h, EXTRACTION_PAUSE_MAX_H)
    until = datetime.utcnow() + timedelta(hours=h)
    state.extraction_paused_until = until.isoformat()
    state_manager.save(state)
    print(f"[EKSTRAKCJA|pauza] WSTRZYMANO zapis na {h}h (do {until.isoformat()} UTC)", flush=True)
    return {"paused": True, "minutes_left": _extraction_pause_left(state),
            "until": state.extraction_paused_until}


class ScenariuszModeModel(BaseModel):
    hours: float | None = None      # None → domyślne 3h
    off: bool = False


@app.get("/api/scenariusz-mode")
async def get_scenariusz_mode():
    """Stan trybu scenariusza — dla wskaźnika w UI."""
    state = state_manager.load()
    return {
        "active": _scenariusz_mode(state),
        "minutes_left": _minutes_left(getattr(state, "scenariusz_mode_until", "") or ""),
    }


@app.post("/api/scenariusz-mode")
async def set_scenariusz_mode(body: ScenariuszModeModel):
    """
    Tryb scenariusza: cały scenariusz wjeżdża do promptu (z ramką anty-dryf).

    NIE wyłącza pamięci — od 18.08. Pierwsza wersja wyłączała „żeby nie zaśmiecać" i przez
    to wyparowała cała sesja twórcza (zero wpisów o demonie jelit, mitsuketa, Primal Forces),
    a Astra rano nie wiedziała, że o czymkolwiek rozmawiali. Zamiast blokować zapis,
    znakujemy go `origin_endpoint="scenariusz"` — sprzątać można później i selektywnie,
    a stracone ustalenia nie wracają nigdy.

    Kto chce pogadać bez zapisu, ma do tego osobny przycisk ⏸.
    """
    state = state_manager.load()
    if body.off:
        state.scenariusz_mode_until = ""
        state_manager.save(state)
        print("[SCENARIUSZ|tryb] WYŁĄCZONY — scenariusz poza promptem", flush=True)
        return {"active": False, "minutes_left": 0}

    h = min(body.hours if body.hours and body.hours > 0 else EXTRACTION_PAUSE_DEFAULT_H,
            EXTRACTION_PAUSE_MAX_H)
    until = datetime.utcnow() + timedelta(hours=h)
    state.scenariusz_mode_until = until.isoformat()
    state_manager.save(state)
    print(f"[SCENARIUSZ|tryb] WŁĄCZONY na {h}h — scenariusz w prompcie, pamięć działa normalnie", flush=True)
    return {"active": True, "minutes_left": _minutes_left(state.scenariusz_mode_until)}


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


@app.get("/api/debug/inspect-write")
async def debug_inspect_write(text: str, persona: str = "astra",
                              _auth=Depends(check_debug_auth)):
    """
    AMNEZJA — ŚCIEŻKA ZAPISU. Przepuszcza tekst przez ekstraktor i pokazuje, co z niego
    powstało, co odpadło i NA KTÓREJ BRAMCE.

    Po co: dotąd Amnezja pokazywała wyłącznie ODCZYT (co trafiło do promptu), więc pytanie
    „czemu tego w ogóle nie ma w jej pamięci" pozostawało bez odpowiedzi — a to właśnie
    awarie zapisu kosztowały najwięcej. „Mefedron. Wziąłem kreskę." i „Kocham cie" nigdy
    nie weszły do bazy i dowiedzieliśmy się o tym przypadkiem, tygodnie później.

    W PEŁNI READ-ONLY: `process_message` niczego nie zapisuje (konsolidator tylko czyta
    i zwraca proponowaną akcję), a my nie wołamy add_memory ani fact_store.upsert.
    """
    if not pipeline:
        raise HTTPException(status_code=503, detail="Pipeline nie gotowy")

    trace = []
    # Ścieżka zapisu ma RÓŻNE progi i różne blokady per aktor — podgląd musi je odtwarzać
    # wiernie, inaczej pokazywałby fikcję. Siostry: próg 0.50 i lista blokowanych typów;
    # Astra i Amelia: próg 0.40, bez blokad.
    siostra = persona in ("holo", "menma", "nazuna", "shared")
    if siostra:
        persona_id, prog = persona, SIOSTRY_MIN_CONFIDENCE
    elif persona == "amelia":
        persona_id, prog = AMELIA_PERSONA_ID, 0.40
    else:
        persona_id, prog = PERSONA_ID, 0.40
    try:
        wynik = await asyncio.to_thread(
            pipeline.process_message, text, persona_id, prog, trace
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")

    # Blokada typów obowiązuje WYŁĄCZNIE siostry (SIOSTRY_TYPY_BLOKOWANE) — trace musi
    # to pokazać, bo inaczej podgląd twierdziłby, że wspomnienie zostało zapisane,
    # podczas gdy realna ścieżka odrzuca je tuż przed zapisem.
    if siostra:
        for mem in wynik:
            if (mem.entity_type, mem.subtype) in SIOSTRY_TYPY_BLOKOWANE:
                trace.append({
                    "etap": "5b_blokada_typu", "werdykt": "ODRZUCONE",
                    "powod": "typ zablokowany przy starcie pamieci siostr (decyzja 19.08)",
                    "etykieta": f"{mem.entity_type}:{mem.subtype}",
                    "tekst_wspomnienia": mem.text[:200],
                })

    # Bramka, która NIE siedzi w pipeline, tylko w ścieżce zapisu /api/chat — bez niej
    # obraz byłby niepełny: wspomnienie może przejść cały pipeline i wypaść dopiero tutaj.
    for mem in wynik:
        if _is_too_short(mem.text):
            trace.append({
                "etap": "6_filtr_koncowy", "werdykt": "ODRZUCONE",
                "powod": "tekst wspomnienia za krotki (_is_too_short w main.py)",
                "etykieta": f"{mem.entity_type}:{mem.subtype}",
                "tekst_wspomnienia": mem.text[:200],
            })

    # Wspomnienie „ZAPISANE" przez pipeline, ale odrzucone przez blokadę typu, NIE liczy się.
    odrzucone_etykiety = {t.get("etykieta") for t in trace
                          if t.get("werdykt") == "ODRZUCONE" and t.get("etykieta")}
    zapisane = [t for t in trace if t.get("werdykt") == "ZAPISANE"
                and t.get("etykieta") not in odrzucone_etykiety]
    return {
        "text": text,
        "persona": persona,
        "wynik": "ZAPISANO" if zapisane else "NIC NIE WESZLO DO PAMIECI",
        "liczba_wspomnien": len(zapisane),
        "trace": trace,
        "uwaga": "podglad read-only — nic nie zostalo zapisane do bazy",
    }


@app.get("/api/debug/inspect")
async def debug_inspect(query: str, persona: str = "astra", day_offset: int = 0,
                        generate: bool = False, conversation_id: str = None,
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
    _SISTER_SET = set(_SISTER_ORDER)
    if persona != "astra" and persona not in _SISTER_SET:
        raise HTTPException(status_code=422, detail="Amnezja: persona 'astra' albo siostra (holo/menma/nazuna)")
    is_sister = persona in _SISTER_SET
    day_offset = max(0, day_offset)  # B2: ujemny offset = Frankenstein czasu (przyszłe wektory jako świeże)
    now_override = (datetime.utcnow() + timedelta(days=day_offset)) if day_offset else None
    trace = {}

    if is_sister:
        # Ścieżka sióstr — LUSTRO wywołania z _generate_sister (Krok B): retrieval + trace,
        # bez FactStore, bez RAW window, sesja ze wspólnej kolekcji pokoju. state/scene/present
        # nie wpływają na trace (builder siostry wnosi je tylko do tekstu promptu, nie do retrievalu).
        cid = conversation_id or "amnezja-siostry"

        def _run():
            def _sister_build(memories, grounding_result, state, recent_raw, hard_facts, now_override=None):
                return build_sister_prompt(persona, memories, grounding_result, "", [persona],
                                           hard_facts=hard_facts)
            return compose_context(
                query=query, conversation_id=cid,
                vs_main=_sister_vs(persona), vs_shared=siostry_shared_vs,
                # fact_store jak w produkcji — Amnezja musi pokazywac to samo, co dostaje
                # realna siostra, lacznie ze wspolna warstwa faktow biograficznych.
                fact_store=fact_store, persona_id=persona, build_prompt_fn=_sister_build,
                state=None, session_vs=siostry_shared_vs,
                main_n=4, main_pool=20, skip_raw=True, require_user_origin=True,
                now_override=now_override, trace=trace,
            )
    else:
        # B1: świeża KOPIA stanu (nie żywy singleton — chroni przed mutacją z równoległego chatu)
        #     + symulacja inkrementu licznika jak w /api/chat → blok [STAN] = produkcja co do znaku.
        state = copy.deepcopy(state_manager.load())
        state.messages_this_session += 1
        cid = conversation_id or state.active_conversation_id or "amnezja"

        def _run():
            return compose_context(
                query=query, conversation_id=cid,
                vs_main=vector_store, vs_shared=shared_vector_store, fact_store=fact_store,
                persona_id=PERSONA_ID, build_prompt_fn=build_system_prompt,
                state=state, session_n=ASTRA_SESSION_N, now_override=now_override, trace=trace,
            )

    ctx = await asyncio.to_thread(_run)

    # PIASKOWNICA: opcjonalna generacja odpowiedzi (dry — woła Gemini, NIC nie zapisuje).
    generated = None
    if generate:
        if is_sister:
            def _gen():
                # LUSTRO składania contents z _generate_sister — od 2026-08-25 przez WSPÓLNĄ
                # funkcję, nie przez kopię. Ta kopia była duplikatem buga atrybucji i gdyby
                # naprawa objęła tylko produkcję, Amnezja pokazywałaby inną historię niż ta,
                # którą realnie dostaje model — czyli debugger zacząłby kłamać. Dokładnie ten
                # wzorzec, przed którym ostrzega CLAUDE.md („naprawa nie objęła wszystkich miejsc").
                contents = _sister_history_contents(ctx["session_messages"], genai_types)
                contents.append(genai_types.Content(role="user", parts=[genai_types.Part(text=query)]))
                cfg = genai_types.GenerateContentConfig(
                    system_instruction=ctx["system_prompt"],
                    max_output_tokens=2048, temperature=0.9,
                    thinking_config=genai_types.ThinkingConfig(thinking_budget=2048),
                    response_mime_type="application/json",
                )
                resp = gemini_client.models.generate_content(model=GEMINI_MODEL, contents=contents, config=cfg)
                raw = safe_response_text(resp)
                a_resp, thought, hint, _ = parse_gemini_response(raw)
                return {"response": a_resp, "thought": thought, "hint": hint}
        else:
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
        "persona": persona,
        "day_offset": day_offset,
        "now_simulated": (now_override or datetime.utcnow()).strftime("%Y-%m-%d %H:%M UTC"),
        "hard_facts_count": len(ctx["hard_facts"]),
        "final_count": len(ctx["memories"]),
        "stages": trace.get("stages", []),
        "grounding_result": trace.get("grounding"),
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


TRANSCRIBE_PROMPT = (
    "Transkrybuj to nagranie DOSŁOWNIE, po polsku. "
    "Zwróć WYŁĄCZNIE wypowiedziany tekst — bez komentarzy, bez cudzysłowów, bez opisu nagrania. "
    "Nie poprawiaj stylu, nie skracaj, nie dopowiadaj. Zachowaj naturalną interpunkcję. "
    "Jeśli nagranie jest ciche, puste lub niezrozumiałe — zwróć pusty tekst."
)

@app.post("/api/transcribe", response_model=TranscribeResponse)
async def transcribe(req: TranscribeRequest):
    """Push-to-talk: nagranie WAV → tekst. Frontend wstawia wynik do pola, user wysyła sam."""
    if gemini_client is None:
        raise HTTPException(status_code=503, detail="Gemini niedostępny")

    part = _audio_part_from_data_url(req.audio)
    if part is None:
        raise HTTPException(status_code=400, detail="Nieprawidłowe audio")

    try:
        resp = gemini_client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[part, genai_types.Part.from_text(text=TRANSCRIBE_PROMPT)],
            config=genai_types.GenerateContentConfig(
                thinking_config=genai_types.ThinkingConfig(thinking_budget=0),
            ),
        )
    except Exception as e:
        print(f"[TRANSCRIBE] Błąd Gemini: {e}", flush=True)
        raise HTTPException(status_code=502, detail="Transkrypcja nie powiodła się")

    # safe_response_text zamiast resp.text: ten model potrafi zwrócić odpowiedź multi-part,
    # a wtedy goły .text daje pustkę bez powodu. Helper wyciąga treść i loguje finish_reason
    # / block_reason — czyli JEDYNĄ informację, dlaczego transkrypcja wyszła pusta.
    try:
        text = (safe_response_text(resp) or "").strip()
    except Exception as e:
        print(f"[TRANSCRIBE] Nie da się odczytać odpowiedzi: {type(e).__name__}: {e}", flush=True)
        text = ""

    if not text:
        # Pusty wynik to najczęstszy objaw zgłaszany przez Łukasza — logujemy powód,
        # zamiast zwracać ciche 200 z pustką (patrz wazne/bugi/mikrofon.md).
        cand = (getattr(resp, "candidates", None) or [None])[0]
        finish = str(getattr(cand, "finish_reason", "BRAK_CANDIDATE"))
        block = getattr(resp, "prompt_feedback", None)
        block_reason = str(getattr(block, "block_reason", "NONE")) if block else "NONE"
        usage = getattr(resp, "usage_metadata", None)
        print(f"[TRANSCRIBE] PUSTO — finish_reason={finish} block_reason={block_reason} "
              f"usage={usage}", flush=True)
    else:
        print(f"[TRANSCRIBE] {len(text)} znaków", flush=True)
    return TranscribeResponse(text=text)


MAX_TTS_CHARS = 2500


@app.post("/api/speak")
async def speak(req: SpeakRequest):
    """Tekst odpowiedzi Astry → mowa (ElevenLabs). Zwraca MP3 do odtworzenia w UI."""
    if not ELEVENLABS_API_KEY or not ELEVENLABS_VOICE_ID:
        raise HTTPException(status_code=503, detail="ElevenLabs nie jest skonfigurowany")

    text = (req.text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Pusty tekst")
    # Ucinamy zamiast odrzucać — długa odpowiedź ma się odezwać, choćby w części.
    text = text[:MAX_TTS_CHARS]

    try:
        async with httpx.AsyncClient(timeout=90) as client:
            r = await client.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}",
                headers={"xi-api-key": ELEVENLABS_API_KEY, "Content-Type": "application/json"},
                json={
                    "text": text,
                    "model_id": ELEVENLABS_MODEL,
                    "voice_settings": {
                        "stability": ELEVENLABS_STABILITY,
                        "similarity_boost": ELEVENLABS_SIMILARITY,
                        "style": ELEVENLABS_STYLE,
                        "speed": ELEVENLABS_SPEED,
                    },
                },
            )
    except Exception as e:
        print(f"[SPEAK] Błąd połączenia z ElevenLabs: {e}", flush=True)
        raise HTTPException(status_code=502, detail="Synteza mowy nie powiodła się")

    if r.status_code != 200:
        try:
            msg = r.json()["detail"]["message"]
        except Exception:
            msg = r.text[:200]
        print(f"[SPEAK] ElevenLabs {r.status_code}: {msg}", flush=True)
        raise HTTPException(status_code=502, detail=f"ElevenLabs: {msg}")

    print(f"[SPEAK] {len(text)} znaków → {len(r.content)} B mp3", flush=True)
    return Response(content=r.content, media_type="audio/mpeg")


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


@app.get("/api/history/siostry")
async def get_siostry_history(conversation_id: str, n: int = 30):
    """
    Zwraca historię pokoju sióstr. Dodane 15.08 — zapis do `siostry_shared_v1` działał
    od początku (`_generate_sister`), ale nie było czym go odczytać, więc pokój otwierał
    się jako pusta kartka mimo pełnych danych na serwerze.
    Treści modelu mają prefiks `[holo]`/`[menma]`/`[nazuna]` — front go parsuje przy renderze.
    """
    messages = siostry_shared_vs.get_recent_session(conversation_id, n=n) if siostry_shared_vs else []
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
    # 2026-08-17: device_id generowany raz po stronie klienta (localStorage) i przysyłany
    # przy każdej subskrypcji. Bez niego jedno urządzenie potrafi mieć kilka WŻYWYCH
    # subskrypcji naraz — patrz komentarz przy push_subscribe.
    device_id: str | None = None
    user_agent: str | None = None


@app.get("/api/push/vapid-public-key")
async def get_vapid_public_key():
    """Zwraca VAPID public key dla frontendu."""
    return {"publicKey": VAPID_PUBLIC_KEY_STR}


@app.post("/api/push/subscribe")
async def push_subscribe(sub: PushSubscriptionModel):
    """
    Zapisuje subskrypcję push notyfikacji — JEDNA na urządzenie.

    BUG 2026-08-17 (dwie identyczne wiadomości dnia na telefonie): dedup po samym
    `endpoint` nie wystarcza. Każda nowa rejestracja Service Workera dostaje NOWY
    endpoint FCM — a rejestracje mnożą się przy: instalacji PWA jako WebAPK obok
    zwykłej karty Chrome (f9030f4), podmianie SW, wyczyszczeniu danych strony.
    Stara subskrypcja nie znika sama, bo `send_push_to_all` usuwa dopiero te, które
    FCM odrzuci przez 410/404 — a subskrypcja z wciąż żywej przeglądarki jest ważna
    i dostarcza. Efekt: dwa ŻYWE kanały na jedno urządzenie, każdy dostaje tę samą
    treść. Dedup po hashu w `app.js` tego nie łapał, bo chroni bąbelki w UI, nie
    powiadomienia systemowe.

    Fix: klient przysyła stały `device_id` (localStorage), a nowa subskrypcja
    ZASTĘPUJE wszystkie poprzednie z tego samego urządzenia.
    """
    subs = _load_subscriptions()
    sub_dict = sub.model_dump()
    sub_dict["created_at"] = datetime.utcnow().isoformat()
    before = len(subs)

    # Ta sama subskrypcja (endpoint) albo to samo urządzenie (device_id) → wymiana.
    dev = sub_dict.get("device_id")
    subs = [x for x in subs
            if x.get("endpoint") != sub_dict["endpoint"]
            and not (dev and x.get("device_id") == dev)]
    subs.append(sub_dict)

    # TWARDY LIMIT — najskuteczniejsza część fixu. `device_id` NIE wystarcza, bo PWA
    # zainstalowana jako WebAPK i ta sama strona w karcie Chrome to dwa osobne konteksty
    # localStorage: każdy generuje własne id, więc 19.08 znów poszły dwa pushe na jeden
    # telefon (log: "2 subskrypcji dla jednej treści"). ASTRA JEST SYSTEMEM JEDNOOSOBOWYM —
    # jedno żywe powiadomienie to nie ograniczenie, tylko poprawne zachowanie.
    # Ostatnio zarejestrowane urządzenie wygrywa; pozostałe i tak zobaczą wiadomość
    # w czacie przez polling /api/morning-message.
    dropped = []
    if len(subs) > MAX_PUSH_SUBSCRIPTIONS:
        subs.sort(key=lambda x: x.get("created_at") or "")
        dropped = subs[:-MAX_PUSH_SUBSCRIPTIONS]
        subs = subs[-MAX_PUSH_SUBSCRIPTIONS:]

    _save_subscriptions(subs)
    print(f"[PUSH] subscribe device={dev or '?'} | subskrypcji: {before} → {len(subs)}"
          f"{f' | usunieto stare: {[d.get(chr(100)+chr(101)+chr(118)+chr(105)+chr(99)+chr(101)+chr(95)+chr(105)+chr(100)) for d in dropped]}' if dropped else ''}",
          flush=True)
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
