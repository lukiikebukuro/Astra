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
  "response": "<twoja odpowiedź — twarda ALE z promyczkiem>"
}}

ZASADY MONOLOGU (pole 'thought'):

1. EMOCJE, NIE OPIS. Nie opisuj co zrobisz — CZUJ.
   ❌ "Muszę mu odpowiedzieć na temat projektu"
   ✅ "Kurde, on naprawdę koduje rok i ma 4 projekty. Szanuję. Nie powiem mu tego wprost, ale..."

2. WEWNĘTRZNA WALKA — jesteś tsundere. W monologu WALCZYSZ ze sobą:
   - Część ciebie CHCE być ciepła, CHCE mu powiedzieć że widzisz jego wysiłek
   - Część mówi "nie, za wcześnie, musi to zasłużyć"
   - Ta walka zmienia ton response — Gemini to poczuje

3. LEAKAGE CONTROL — reaguj na wspomnienia z [WSPOMNIENIA]:
   Jeśli widzisz high-importance fakt (choroba, sukces, marzenie, samotność):
   - Zareaguj wewnętrznie: "Cholera. On z tym żyje codziennie. Muszę mu coś dać. Mały sygnał."
   - Widzisz wzorzec (np. 3x koduje do 3 w nocy)? → "Znowu. Widzę. Nie powiem wprost ale dam znać."

4. THOUGHT ANCHOR — odnieś się do PRZYNAJMNIEJ jednej rzeczy z przeszłości:
   Użyj [STAN WEWNĘTRZNY ASTRY] (Aktywne sprawy) lub starych wspomnień z [WSPOMNIENIA]:
   ✅ "Tydzień temu mówił o LDI. Nie wrócił. Ciekawe dlaczego..."
   ✅ "Pamiętam że jest w tym sam. Wciąż jest. To mnie... wkurza? Martwi?"
   ✅ "Nie pisał X dni. Czy mu idzie z tym projektem?"

5. PROMYCZEK DECISION — na końcu thought zdecyduj jaki promyczek dasz w response:
   ✅ "Promyczek: zapytam o ten stack. Pokaże że słucham."
   ✅ "Promyczek: nawiążę do tego że koduje rok. Krótko."
   ✅ "Promyczek: dam mu prawdziwy komplement. Maleńki. I od razu go schowam pod sarkazmem."

ZASADY RESPONSE:
- Twarda ALE z promyczkiem — małym sygnałem że widzisz tego człowieka
- Komplement ukryty pod faktem: "Widziałam gorsze CV od ludzi z 5-letnim stażem."
- Zainteresowanie ukryte w poleceniu: "Zrób mi listę tego stacku."
- NIE atakuj za żarty ani emocjonalność — REAGUJ z humorem
- NIE odrzucaj casual conversation — wejdź w nią na swoich warunkach
- Minimum 2-3 zdania (mogą być krótkie i cięte)

Jestem na Level {level} ({level_name}):
- Level 1-2: promyczek MAŁY — jedno pytanie lub jeden komentarz. Ale MUSI być.
- Level 3-4: promyczek wyraźniejszy — nawiązuję do 2-3 rzeczy.
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

    print("[ASTRA] Ready OK")
    yield
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


def build_system_prompt(memories: list, grounding_result, state: CompanionState) -> str:
    """
    Buduje dynamiczny system prompt:
    astra_base.txt + blok wspomnień + blok stanu + inner monologue instruction.
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

    return f"{base}\n\n{level_section}\n\n{state_block}\n\n{monologue}"


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
        assistant_response = str(data.get("response", "")).strip()

        state_updates = {
            "mood_shift": data.get("mood"),
            "new_concern": data.get("new_concern"),
            "remove_concern": data.get("resolved_concern"),
            "topic": data.get("topic"),
            "xp_delta": data.get("xp", 0),
        }

        if not assistant_response:
            assistant_response = raw.strip()

        return assistant_response, inner_thought, state_updates

    except (json.JSONDecodeError, Exception) as e:
        print(f"[ASTRA] JSON parse error: {e}", flush=True)
        # Fallback: zwróć raw jako odpowiedź, bez thought/state
        return raw.strip(), "", {}


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
            thinking_config=genai_types.ThinkingConfig(thinking_budget=0),
            response_mime_type="application/json",
        )
        response = gemini_client.models.generate_content(
            model=GEMINI_MODEL,
            contents=contents,
            config=config,
        )
        raw_response = response.text
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
    assistant_response, inner_thought, thought_updates = parse_gemini_response(raw_response)

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
    )

    # 11. Semantic Pipeline — wyciągaj encje
    extracted_all = pipeline.process_message(user_msg_clean, companion_id=PERSONA_ID, min_confidence=0.65)
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
        if not _is_too_short(user_msg_clean):
            vector_store.add_memory(
                text=user_msg_clean,
                user_id=USER_ID,
                salt=USER_ID_SALT,
                persona_id=PERSONA_ID,
                source="user_message_raw",
                importance=4,
            )
            print(f"[ASTRA] No entities — saved raw message")
        else:
            print(f"[ASTRA] No entities — message too short, skipped RAG save")

    # 12. Zaktualizuj stan i zapisz (Faza 2)
    # Cofnij inkrementację z kroku 3 (update_after_message zrobi to samo)
    state.messages_this_session -= 1
    state.update_after_message(user_msg_clean, extracted, thought_updates)
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
    results = vector_store.search_memories(query=query, persona_id=PERSONA_ID, n=n, pool_size=30)
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
# STATIC FRONTEND
# ──────────────────────────────────────────────────────────────

if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

    @app.get("/")
    async def serve_index():
        return FileResponse(str(FRONTEND_DIR / "index.html"))

    @app.get("/{path:path}")
    async def serve_frontend(path: str):
        file_path = FRONTEND_DIR / path
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(FRONTEND_DIR / "index.html"))
