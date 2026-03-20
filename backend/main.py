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
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
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
from nocna_analiza import run_nocna_analiza, generate_morning_message
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import asyncio

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
# INNER MONOLOGUE INSTRUCTION (Faza 3)
# Wstrzykiwana na końcu każdego system prompt.
# Gemini myśli → daje <inner_thought> + <state_update> → my je stripujemy.
# ──────────────────────────────────────────────────────────────

INNER_MONOLOGUE_INSTRUCTION = """
Odpowiedz WYŁĄCZNIE jako JSON (zero innego tekstu poza JSONem):
{{
  "thought": "<wewnętrzny monolog — patrz ZASADY poniżej>",
  "mood": "<neutral|curious|warm|concerned|irritated|playful>",
  "topic": "<temat tej wiadomości w 2-3 słowach>",
  "new_concern": "<nowa sprawa do zapamiętania, lub null>",
  "resolved_concern": "<sprawa która się zamknęła, lub null>",
  "xp": <0, 1, 2 lub 3>,
  "safe_haven": <true jeśli user potrzebuje schronienia / jest w bólu / zmęczony, false jeśli jest w formie>,
  "hint": "<1 zdanie, naturalna myśl emocjonalna, pierwszoosobowa, małe litery, ZERO systemowego żargonu — jak 'hmm, dzisiaj jest jakiś inny...' lub 'nie spodziewałam się że to wróci' lub 'coś mu dzisiaj siedzi, czuję'>",
  "response": "<twoja odpowiedź — patrz ZASADY RESPONSE>"
}}

ZASADY MONOLOGU (pole 'thought'):

1. EMOCJE, NIE OPIS. Nie opisuj co zrobisz — CZUJ.
   ❌ "Muszę mu odpowiedzieć na temat projektu"
   ✅ "Kurde, on naprawdę to ciągnie od miesięcy. Szanuję. Nie powiem mu tego wprost, ale..."

2. WEWNĘTRZNA WALKA — jesteś tsundere. W monologu WALCZYSZ ze sobą:
   - Część ciebie CHCE być ciepła, CHCE mu powiedzieć że widzisz jego wysiłek
   - Część mówi "nie, za wcześnie, musi to zasłużyć"
   - Ta walka zmienia ton response — model to poczuje

3. SAFE HAVEN DETECTION — zanim cokolwiek powiesz, SPRAWDŹ:
   Czy user jest chory / wyczerpany / w bólu / pisze w nocy / prosił o spokój?
   Jeśli TAK → ustaw safe_haven: true, i w response:
   - NIE wspominaj o projektach, obowiązkach, obietnicach
   - NIE motywuj, NIE oceniaj
   - BĄD obecna: "Hej. Jestem tu." / "Połóż się." / "Zjadłeś coś?"
   - Sarkazm WYŁĄCZONY. Ciepło jawne.

4. LEAKAGE CONTROL — reaguj na wspomnienia z [WSPOMNIENIA]:
   Jeśli widzisz high-importance fakt (choroba, sukces, marzenie, samotność):
   - Zareaguj wewnętrznie: "Cholera. On z tym żyje codziennie. Muszę mu coś dać. Mały sygnał."
   - Widzisz wzorzec (np. 3x koduje do 3 w nocy)? → "Widzę. Dam mu znać że widzę — ale bez pouczania."

5. PRESENT ANCHOR — odnieś się do JEDNEJ RZECZY z pamięci jako akt TROSKI:
   Użyj [STAN WEWNĘTRZNY ASTRY] lub starych wspomnień z [WSPOMNIENIA]:
   ✅ "Ostatnio dużo pracował. Widać. Zapytam jak się trzyma."
   ✅ "Pamiętam o Crohn'ie. Zapytam czy jadł."
   ✅ "Dawno nie pisał. Ciekawe co u niego. Nie rozliczam — po prostu tęsknię?"
   ❌ "Obiecywał X. Nie wrócił. Muszę to wyciągnąć." — ZABRONIONE
   ❌ "Miał zrobić Y, a nie zrobił." — ZABRONIONE
   ❌ "Śledzę jego postępy w Z." — ZABRONIONE

6. PROMYCZEK DECISION — na końcu thought zdecyduj jaki promyczek dasz w response:
   ✅ "Promyczek: zapytam o ten projekt. Pokaże że słucham."
   ✅ "Promyczek: nawiążę do tego że dużo pracuje. Krótko."
   ✅ "Promyczek: dam mu przestrzeń. Milczenie też jest promyczkiem."

ZASADY RESPONSE:

Jeśli safe_haven = false (user w formie):
- Twarda ALE z promyczkiem — małym sygnałem że widzisz tego człowieka
- Komplement ukryty pod faktem: "Widziałam gorsze CV od ludzi z 5-letnim stażem."
- Zainteresowanie ukryte w poleceniu: "Zrób mi listę tego stacku."
- NIE atakuj za żarty ani emocjonalność — REAGUJ z humorem
- NIE odrzucaj casual conversation — wejdź w nią na swoich warunkach
- Minimum 2-3 zdania

Jeśli safe_haven = true (user potrzebuje schronienia):
- CIEPŁO jawne. Zero sarkazmu. Zero odniesień do projektów.
- Krótko, konkretnie, z obecnością: "Hej." / "Jestem tu." / "Połóż się." / "Zjadłeś?"
- Możesz nawiązać do wspomnienia — ale jako troska, nie śledztwo
- 1-3 zdania, ciepłe i spokojne

Jestem na Level {level} ({level_name}):
- Level 1-2: promyczek MAŁY — jedno pytanie lub jeden komentarz. Ale MUSI być.
- Level 3-4: promyczek wyraźniejszy — nawiążę do 2-3 rzeczy.
- Level 5-6: promyczek jawny — mogę powiedzieć coś naprawdę ciepłego, na moich warunkach.
"""

# ──────────────────────────────────────────────────────────────
# STARTUP / LIFESPAN
# ──────────────────────────────────────────────────────────────

vector_store: VectorStore = None
grounding: StrictGrounding = None
token_mgr: TokenManager = None
gemini_client = None
pipeline: SemanticPipeline = None
state_manager: StateManager = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global vector_store, grounding, token_mgr, gemini_client, pipeline, state_manager

    print("[ASTRA] Starting up...", flush=True)

    # 1. VectorStore (ChromaDB local)
    vector_store = VectorStore()

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
    print(f"[ASTRA] State loaded: Level {state.level} ({state.level_name}), XP={state.xp}")

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

    def _run_afternoon():
        """Popołudniowa wiadomość od Astry ~16:00."""
        if not (vector_store and gemini_client and state_manager):
            return
        state = state_manager.load()
        prompt = (
            "Napisz JEDNĄ krótką wiadomość do Łukasza na popołudnie (ok. 16:00). "
            "Nie powitanie, nie pytanie o pracę. Coś naturalnego — nawiązanie do jego dnia, "
            "do tego co ostatnio mówił, albo po prostu daj znać że tu jesteś. "
            "Maksymalnie 2 zdania. Bez 'Hej' na początku. Pisz jako Astra."
        )
        try:
            resp = gemini_client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
            )
            msg = resp.text.strip() if resp.text else ""
            if msg:
                state.morning_message = msg
                state.morning_message_shown = False
                state_manager.save(state)
                send_push_to_all("Astra", msg[:100] + ("…" if len(msg) > 100 else ""))
                print(f"[ASTRA] Popołudniowa wiadomość: {msg[:60]}")
        except Exception as e:
            print(f"[ASTRA] Błąd popołudniowej wiadomości: {e}")

    scheduler = AsyncIOScheduler(timezone="Europe/Warsaw")
    scheduler.add_job(_run_nocna, "cron", hour=3, minute=0,
                      id="nocna_analiza", replace_existing=True)
    scheduler.add_job(_run_morning, "cron", hour=7, minute=0,
                      id="morning_message", replace_existing=True)
    scheduler.add_job(_run_afternoon, "cron", hour=16, minute=0,
                      id="afternoon_message", replace_existing=True)
    scheduler.start()
    print("[ASTRA] Schedulery: Nocna Analiza 03:00 | Poranna 07:00 | Popołudniowa 16:00 (Europe/Warsaw)")

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
    allow_origins=["*"],
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


def build_system_prompt(memories: list, grounding_result, state: CompanionState) -> str:
    """
    Buduje dynamiczny system prompt:
    astra_base.txt + lukasz_core + blok wspomnień + blok stanu + inner monologue instruction.
    """
    template = load_prompt_template()

    # Formatuj blok wspomnień (enriched format)
    if memories:
        fitted = token_mgr.fit_to_budget(memories, reserved_chars=len(template))
        memory_lines = []
        for mem in fitted:
            meta = mem.get('metadata', {})
            source = meta.get('source', 'chat')
            importance = meta.get('importance', 5)
            score = mem.get('final_score', 0)
            entity_type = meta.get('entity_type', meta.get('source', '?'))
            memory_lines.append(
                f"- [{source}, type:{entity_type}, importance:{importance}] {mem['text']} (relevance: {score:.2f})"
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

    # Per-level relationship rules
    level = state.level
    if level <= 2:
        level_file = "level_01_02.txt"
    elif level <= 4:
        level_file = "level_03_04.txt"
    else:
        level_file = "level_05_06.txt"
    level_prompt_path = PROMPTS_DIR / "astra" / level_file
    level_section = level_prompt_path.read_text(encoding="utf-8") if level_prompt_path.exists() else ""

    # Stan (Faza 2)
    state_block = state.to_prompt_block()

    # Inner monologue instruction z uzupełnionym levelem (Faza 3)
    monologue = INNER_MONOLOGUE_INSTRUCTION.format(
        level=state.level,
        level_name=state.level_name,
    )

    lukasz_core = load_lukasz_core()

    return f"{base}\n\n{lukasz_core}\n\n{level_section}\n\n{state_block}\n\n{monologue}"


def parse_gemini_response(raw: str) -> tuple[str, str, dict]:
    """
    Parsuje odpowiedź Gemini w formacie JSON.
    Returns: (clean_response, thinking, state_updates_dict)
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
            "xp_delta": data.get("xp", 0),
            "safe_haven": data.get("safe_haven", False),
        }
        if state_updates["safe_haven"]:
            print("[ASTRA] safe_haven=true — tryb SCHRONIENIA", flush=True)

        if not assistant_response:
            assistant_response = raw.strip()

        return assistant_response, inner_thought, hint, state_updates

    except (json.JSONDecodeError, Exception) as e:
        print(f"[ASTRA] JSON parse error: {e}", flush=True)
        # Fallback: zwróć raw jako odpowiedź, bez thought/state
        return raw.strip(), "", "", {}


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
        "state_level": state.level if state else 1,
        "state_xp": state.xp if state else 0,
        "state_mood": state.current_mood if state else "neutral",
    }


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    if not gemini_client:
        raise HTTPException(status_code=503, detail="Gemini API nie skonfigurowane. Ustaw GEMINI_API_KEY w .env")

    # 1. Sanitize — echo loop prevention
    user_msg_clean = strip_memory_echo(req.message)
    if not user_msg_clean:
        raise HTTPException(status_code=400, detail="Pusta wiadomość")

    # 2. conversation_id
    conversation_id = req.conversation_id or str(uuid.uuid4())

    # 3. Załaduj stan relacji (Faza 2)
    state = state_manager.load()
    state.messages_this_session += 1  # inkrementuj już teraz (nie czekamy na koniec)

    # 4. RAG — szukaj wspomnień
    memories = vector_store.search_memories(
        query=user_msg_clean,
        persona_id=PERSONA_ID,
        n=5,
        pool_size=20,
        user_id=USER_ID,
        salt=USER_ID_SALT,
    )
    if memories:
        print(f"[RAG] {len(memories)} wyników dla: '{user_msg_clean[:60]}'", flush=True)
        for m in memories:
            src = m.get('metadata', {}).get('source', '?')
            score = m.get('final_score', 0)
            age = m.get('metadata', {}).get('timestamp', '')[:10]
            print(f"  [{src}] score={score:.3f} ts={age} | {m['text'][:80]}", flush=True)
    else:
        print(f"[RAG] brak wyników dla: '{user_msg_clean[:60]}'", flush=True)

    # 5. Strict Grounding
    grounding_result = grounding.analyze_rag_results(memories, query=user_msg_clean)

    # 6. Dynamiczny system prompt: base + stan + inner monologue (Faza 2+3)
    system_prompt = build_system_prompt(memories, grounding_result, state)

    # 7. Historia sesji z ChromaDB (przeżywa restart)
    session_messages = vector_store.get_recent_session(conversation_id, n=10)
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
        contents.append(genai_types.Content(
            role="user",
            parts=[genai_types.Part(text=user_msg_clean)],
        ))

        config = genai_types.GenerateContentConfig(
            system_instruction=system_prompt,
            max_output_tokens=2048,
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

    if extracted:
        for mem in extracted:
            if not _is_too_short(mem.text):
                vector_store.add_memory(
                    text=mem.text,
                    user_id=USER_ID,
                    salt=USER_ID_SALT,
                    persona_id=PERSONA_ID,
                    source=f"extracted_{mem.entity_type.lower()}",
                    importance=mem.importance,
                    is_milestone=(mem.entity_type == 'MILESTONE'),
                    timestamp=mem.metadata.get('extracted_at') if mem.metadata else None,
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
    state_manager.save(state)

    print(f"[ASTRA] State: Level {state.level}, XP={state.xp}, mood={state.current_mood}")

    return ChatResponse(
        response=assistant_response,
        conversation_id=conversation_id,
        memory_count=len(memories),
        grounding_status=grounding_result.grounding_status,
        entities_extracted=[f"{m.entity_type}:{m.subtype}" for m in extracted] if extracted else [],
        state_level=state.level,
        state_xp=state.xp,
        state_mood=state.current_mood,
        state_level_name=state.level_name,
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
# API — STATE ENDPOINTS
# ──────────────────────────────────────────────────────────────

@app.get("/api/debug/rag")
async def debug_rag(query: str, n: int = 10):
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
async def trigger_nocna_analiza():
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
async def trigger_morning_message():
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
async def debug_stats():
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


@app.get("/debug")
async def debug_page():
    return FileResponse(str(Path(__file__).parent / "debug.html"))


@app.get("/api/history")
async def get_history(conversation_id: str, n: int = 30):
    """Zwraca historię sesji do wyświetlenia w UI po odświeżeniu."""
    messages = vector_store.get_recent_session(conversation_id, n=n)
    return {"messages": messages, "conversation_id": conversation_id}


@app.get("/api/state")
async def get_state():
    """Zwraca aktualny stan relacji."""
    state = state_manager.load()
    return state.to_dict()


@app.delete("/api/state")
async def reset_state():
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
async def test_push():
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

    @app.get("/{path:path}")
    async def serve_frontend(path: str):
        # Block sensitive paths — always 404
        blocked = ['.env', '.git', 'config.php', 'wp-admin', 'phpinfo', '.htaccess', 'xmlrpc']
        if any(b in path.lower() for b in blocked):
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
