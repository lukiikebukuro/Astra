// ASTRA v0.2 — Frontend Chat

const API_URL = '';

// ── Room routing ──────────────────────────────────────────────
const ROOM = (() => {
    const path = window.location.pathname.replace(/\/+$/, '');
    if (path === '/amelia') return 'amelia';
    if (path === '/wspolny') return 'wspolny';
    return 'astra';
})();

const ROOM_CONFIG = {
    astra:   { endpoint: '/api/chat',    label: 'ASTRA',         healthEndpoint: '/api/health',        storageKey: 'astra_conversation_id',   avatarSrc: 'astra.jpg' },
    amelia:  { endpoint: '/api/amelia',  label: 'AMELIA',        healthEndpoint: '/api/amelia/health', storageKey: 'amelia_conversation_id',  avatarSrc: 'amelka.png' },
    wspolny: { endpoint: '/api/wspolny', label: 'WSPÓLNY POKÓJ', healthEndpoint: '/api/health',        storageKey: 'wspolny_conversation_id', avatarSrc: null },
};
const { endpoint: CHAT_ENDPOINT, label: PERSONA_LABEL, healthEndpoint: HEALTH_ENDPOINT, storageKey: STORAGE_KEY, avatarSrc: AVATAR_SRC } = ROOM_CONFIG[ROOM];

let conversationId = localStorage.getItem(STORAGE_KEY) || null;
let isWaiting = false;

// ── Źródło prawdy dla historii (Etap 2, 2026-08-15) ───────────────────────────
// Do 15.08 loadHistory() renderowało z localStorage i wychodziło, gdy cache pasował do
// conversationId — backendu nie pytało wcale. Każde urządzenie pokazywało więc WŁASNY
// wycinek rozmowy, mimo że serwer ma komplet (potwierdzone: /api/history zwraca 100 wiad.).
// Stąd rozjazd komputer↔telefon; skasowanie localStorage „naprawiało" go przypadkiem,
// bo dopiero brak cache'u zmuszał kod do zapytania serwera.
//
// SERVER_TRUTH odwraca hierarchię: serwer jest źródłem prawdy, localStorage schodzi do roli
// fallbacku offline. Włączone TYLKO dla Astry — Wspólny Pokój (i Amelia, która dzieli ten
// plik) zostają na dotychczasowej ścieżce co do znaku. Włączenie Amelii = dopisanie jej tutaj,
// ale to osobna decyzja Łukasza, nie efekt uboczny tej zmiany.
const SERVER_TRUTH = (ROOM === 'astra');
let _historyRendered = false;
let pendingImage = null;  // data URL zdjęcia czekającego na wysłanie

// ── Detekcja urządzenia dotykowego ────────────────────────────
// Na telefonie Enter = nowa linia (Break Line), wysyłka WYŁĄCZNIE przyciskiem.
// Na desktopie Enter = wyślij, Shift+Enter = nowa linia (klasyka).
const IS_TOUCH = (window.matchMedia && window.matchMedia('(pointer: coarse)').matches)
    || /Android|iPhone|iPad|iPod|IEMobile|Opera Mini|Mobile/i.test(navigator.userAgent || '');

// ── Message cache (localStorage fallback dla historii po odświeżeniu) ───────
const CACHE_KEY = `${STORAGE_KEY}_cache`;
let _cachedMsgs = [];

function _cacheLoad() {
    try { return JSON.parse(localStorage.getItem(CACHE_KEY) || 'null'); } catch { return null; }
}
function _cacheSave() {
    try { localStorage.setItem(CACHE_KEY, JSON.stringify({ id: conversationId, msgs: _cachedMsgs })); } catch { }
}

const messagesEl  = document.getElementById('messages');
const inputEl     = document.getElementById('input');
const sendBtn     = document.getElementById('send-btn');
const micBtn      = document.getElementById('mic-btn');
const imageInput  = document.getElementById('image-input');
const statusEl    = document.getElementById('status-text');
const memBadgeEl  = document.getElementById('memory-badge');
const stateLevelEl  = document.getElementById('state-level');
const stateXpEl    = document.getElementById('state-xp');
const stateMoodEl  = document.getElementById('state-mood');
const mobileLevelEl = document.getElementById('mobile-level');

// ── Room init ─────────────────────────────────────────────────

function initRoom() {
    // PWA: podmień manifest na pokój-specyficzny
    if (ROOM !== 'astra') {
        const manifestLink = document.querySelector('link[rel="manifest"]');
        if (manifestLink) manifestLink.href = `/manifest-${ROOM}.json`;
        const appleTitle = document.querySelector('meta[name="apple-mobile-web-app-title"]');
        if (appleTitle) appleTitle.content = PERSONA_LABEL;
    }
    document.title = PERSONA_LABEL;
    const panelName = document.getElementById('panel-name');
    const headerName = document.getElementById('chat-header-name');
    if (panelName) panelName.textContent = PERSONA_LABEL;
    if (headerName) headerName.textContent = PERSONA_LABEL;

    const avatarImg = document.getElementById('avatar-img');
    const headerAvatarImg = document.getElementById('header-avatar-img');
    const fallback = document.getElementById('avatar-fallback');
    if (AVATAR_SRC) {
        if (avatarImg) { avatarImg.src = AVATAR_SRC; avatarImg.alt = PERSONA_LABEL; }
        if (headerAvatarImg) { headerAvatarImg.src = AVATAR_SRC; headerAvatarImg.alt = PERSONA_LABEL; }
        if (fallback) fallback.textContent = PERSONA_LABEL[0];
    } else {
        if (avatarImg) avatarImg.style.display = 'none';
        if (headerAvatarImg) headerAvatarImg.style.display = 'none';
        if (fallback) { fallback.style.display = 'flex'; fallback.textContent = '∞'; }
    }
}

// ── Health / startup ──────────────────────────────────────────

async function fetchHealth() {
    try {
        const res = await fetch(`${API_URL}${HEALTH_ENDPOINT}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();

        memBadgeEl.textContent = `⬡ ${data.vectors || 0}`;
        updateStateBadge(data.state_level, data.state_xp, data.state_mood, null);
        // Sync conversation_id to what's active globally on the backend!
        if (data.active_conversation_id && data.active_conversation_id !== conversationId) {
            console.log(`Syncing conversation_id from backend: ${data.active_conversation_id}`);
            conversationId = data.active_conversation_id;
            localStorage.setItem(STORAGE_KEY, conversationId);
            // Wyczysc UI i zaladuj nowa zlaczona historie.
            // 15.08: bylo `chatArea.innerHTML` — TAKA ZMIENNA NIE ISTNIEJE (kontener to
            // messagesEl). Kazde wejscie tutaj rzucalo ReferenceError, ktory lykal catch
            // ponizej, pokazujac falszywe 'Nie mozna polaczyc z backendem'. Synchronizacja
            // watku z backendem nie dzialala wiec ANI RAZU, tylko nikt tego nie widzial.
            messagesEl.innerHTML = '';
            await loadHistory();
        }
        if (!data.gemini) {
            statusEl.textContent = '● brak API key';
            statusEl.className = 'status offline';
            appendSystemMsg('GEMINI_API_KEY nie ustawiony w backend/.env');
        }
    } catch (e) {
        // Rozroznienie: blad SIECI vs blad W KODZIE. Do 15.08 kazdy wyjatek z tego bloku
        // (w tym ReferenceError na nieistniejacej zmiennej) meldowal sie jako "brak polaczenia
        // z backendem" — przez co realny bug w synchronizacji watku byl niewidoczny miesiacami.
        console.error('[fetchHealth]', e);
        statusEl.textContent = '● offline';
        statusEl.className = 'status offline';
        const bladKodu = (e instanceof TypeError && !String(e.message).toLowerCase().includes('fetch'))
            || e instanceof ReferenceError;
        appendSystemMsg(bladKodu
            ? `Błąd w aplikacji (nie w połączeniu): ${e.message}`
            : 'Nie można połączyć z backendem. Uruchom start.bat lub uvicorn ręcznie.');
    }
}

// ── State badge ───────────────────────────────────────────────

const MOOD_ICONS = {
    neutral: '·',
    curious: '?',
    warm: '~',
    concerned: '!',
    irritated: '×',
    playful: '*',
};

function updateStateBadge(level, xp, mood, levelName) {
    if (level != null) {
        const name = levelName || '';
        stateLevelEl.textContent = name ? `${level} · ${name}` : `${level}`;
        if (mobileLevelEl) mobileLevelEl.textContent = `lvl ${level} · XP ${xp ?? 0}`;
    }
    if (xp != null)  stateXpEl.textContent  = `${xp}`;
    if (mood != null) stateMoodEl.textContent = `${MOOD_ICONS[mood] || '·'} ${mood}`;
}

// ── Helpers ───────────────────────────────────────────────────

function scrollToBottom() {
    messagesEl.scrollTop = messagesEl.scrollHeight;
}

function appendSystemMsg(text) {
    const el = document.createElement('div');
    el.className = 'system-msg';
    el.textContent = text;
    messagesEl.appendChild(el);
    scrollToBottom();
}

// WO-1 (2026-07-25): reset rozmowy backend-first. Nowy conversation_id + czyszczenie widoku.
// Pamięć długoterminowa (astra_memory_v1) zostaje — świeży jest tylko WĄTEK (few-shot).
async function startNewConversation() {
    if (!confirm('Zacząć nową rozmowę? Obecna zostaje zapisana — nic nie znika, Astra pamięta.')) return;
    try {
        const res = await fetch('/api/conversation/new', { method: 'POST' });
        if (!res.ok) throw new Error('HTTP ' + res.status);
        const data = await res.json();
        conversationId = data.conversation_id;
        localStorage.setItem(STORAGE_KEY, conversationId);
        _cachedMsgs = [];
        _cacheSave();
        messagesEl.innerHTML = '';
        appendSystemMsg('Nowa rozmowa. Astra pamięta wszystko — świeży jest tylko wątek.');
    } catch (e) {
        appendSystemMsg('Nie udało się zacząć nowej rozmowy: ' + e.message);
    }
}

function appendBubble(role, html, thought, entities, memoriesDebug, hint, narrator) {
    const wrap = document.createElement('div');
    wrap.className = `bubble-wrap ${role}`;

    const isAI = role !== 'user';

    // H3/B4: Persona label — tylko w wspólnym pokoju
    if (ROOM === 'wspolny' && isAI) {
        const nameEl = document.createElement('div');
        nameEl.className = 'persona-label';
        nameEl.textContent = role.toUpperCase();
        wrap.appendChild(nameEl);
    }

    // NARRATOR — linia sceny/nastroju (tylko wspolny)
    if (ROOM === 'wspolny' && isAI && narrator) {
        const narrEl = document.createElement('div');
        narrEl.className = 'narrator-line';
        narrEl.textContent = narrator;
        wrap.appendChild(narrEl);
    }

    // HINT — zawsze widoczna myśl emocjonalna (AI)
    if (isAI && hint) {
        const hintEl = document.createElement('div');
        hintEl.className = 'astra-hint';
        hintEl.textContent = hint;
        wrap.appendChild(hintEl);
    }

    // THOUGHT — collapsible (AI)
    if (isAI && thought) {
        const btn = document.createElement('button');
        btn.className = 'thought-toggle';
        btn.textContent = '▸ myśl';
        const body = document.createElement('div');
        body.className = 'thought-body';
        body.textContent = thought;
        btn.addEventListener('click', () => {
            body.classList.toggle('open');
            btn.textContent = body.classList.contains('open') ? '▾ myśl' : '▸ myśl';
        });
        wrap.appendChild(btn);
        wrap.appendChild(body);
    }

    const bubble = document.createElement('div');
    bubble.className = `bubble ${role}`;
    bubble.innerHTML = html;
    wrap.appendChild(bubble);

    // RAG memories — co było w wektorach
    if (isAI && memoriesDebug && memoriesDebug.length > 0) {
        const ragWrap = document.createElement('div');
        ragWrap.className = 'rag-wrap';
        memoriesDebug.forEach(m => {
            const pill = document.createElement('span');
            pill.className = 'rag-pill';
            pill.textContent = `${m.source} ${m.score} · ${m.text}`;
            pill.title = `[${m.source}] score=${m.score} ts=${m.ts}\n${m.text}`;
            ragWrap.appendChild(pill);
        });
        wrap.appendChild(ragWrap);
    }

    // Entity pills
    if (isAI && entities && entities.length > 0) {
        const pillsWrap = document.createElement('div');
        pillsWrap.className = 'entities-wrap';
        entities.forEach(e => {
            const pill = document.createElement('span');
            pill.className = 'entity-pill';
            pill.textContent = e;
            pillsWrap.appendChild(pill);
        });
        wrap.appendChild(pillsWrap);
    }

    messagesEl.appendChild(wrap);
    scrollToBottom();
    return bubble;
}

function showTyping() {
    const container = document.createElement('div');
    container.id = 'typing-wrap';

    const personas = ROOM === 'wspolny' ? ['astra', 'amelia'] : [ROOM];
    personas.forEach(p => {
        const wrap = document.createElement('div');
        wrap.className = `bubble-wrap ${p}`;

        if (ROOM === 'wspolny') {
            const nameEl = document.createElement('div');
            nameEl.className = 'persona-label';
            nameEl.textContent = p.toUpperCase();
            wrap.appendChild(nameEl);
        }

        const dots = document.createElement('div');
        dots.className = 'typing-indicator';
        dots.innerHTML = '<span></span><span></span><span></span>';
        wrap.appendChild(dots);

        container.appendChild(wrap);
    });

    messagesEl.appendChild(container);
    scrollToBottom();
}

function hideTyping() {
    const el = document.getElementById('typing-wrap');
    if (el) el.remove();
}

function autoResize() {
    inputEl.style.height = 'auto';
    inputEl.style.height = Math.min(inputEl.scrollHeight, 140) + 'px';
}

// ── Send ──────────────────────────────────────────────────────

async function sendMessage() {
    const text = inputEl.value.trim();
    if ((!text && !pendingImage) || isWaiting) return;

    const image = pendingImage;
    _clearImagePreview();

    isWaiting = true;
    sendBtn.disabled = true;
    inputEl.value = '';
    autoResize();

    const userBubble = appendBubble('user', text ? marked.parse(text) : '');
    if (image) {
        const im = document.createElement('img');
        im.src = image;
        im.className = 'chat-image';
        im.style.cssText = 'max-width:200px;border-radius:8px;display:block;margin-top:4px;';
        userBubble.appendChild(im);
    }
    _cachedMsgs.push({ role: 'user', content: text, thought: '', hint: '' });
    showTyping();

    try {
        const res = await fetch(`${API_URL}${CHAT_ENDPOINT}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: text, conversation_id: conversationId, image: image || undefined }),
        });

        hideTyping();

        if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: 'Unknown error' }));
            appendSystemMsg(`Błąd: ${err.detail || res.status}`);
            return;
        }

        const data = await res.json();

        if (!conversationId) {
            conversationId = data.conversation_id;
            localStorage.setItem(STORAGE_KEY, conversationId);
        }

        if (ROOM === 'wspolny') {
            // WspolnyResponse: { responses: [{persona, response, hint, thought, narrator, ...}], mode, conversation_id }
            for (const r of (data.responses || [])) {
                appendBubble(
                    r.persona,
                    marked.parse(r.response || '...'),
                    r.thought || '',
                    r.entities_extracted || [],
                    r.memories_debug || [],
                    r.hint || '',
                    r.narrator || '',
                );
                _cachedMsgs.push({ role: r.persona, content: r.response || '', thought: r.thought || '', hint: r.hint || '', narrator: r.narrator || '' });
            }
            _cacheSave();
        } else {
            // ChatResponse — Astra lub Amelia (ten sam format)
            const _resp = data.response || '';
            const _aiBubble = appendBubble(
                ROOM,
                marked.parse(_resp || '...'),
                data.thought || '',
                data.entities_extracted || [],
                data.memories_debug || [],
                data.hint || '',
            );
            if (ROOM === 'astra' && _resp) {
                _attachSpeakBtn(_aiBubble, _resp);
                if (voiceEnabled) speakText(_resp);
            }
            _cachedMsgs.push({ role: ROOM, content: _resp, thought: data.thought || '', hint: data.hint || '' });
            _cacheSave();

            updateStateBadge(
                data.state_level,
                data.state_xp,
                data.state_mood,
                data.state_level_name,
            );
            memBadgeEl.textContent = `⬡ ${data.memory_count || 0}`;
        }

    } catch (e) {
        hideTyping();
        appendSystemMsg(`Błąd połączenia: ${e.message}`);
    } finally {
        isWaiting = false;
        sendBtn.disabled = false;
        inputEl.focus();
    }
}

// ── Głos Astry (ElevenLabs) ───────────────────────────────────
// Tylko pokój Astry: Amelia i wspólny mają własne persony, ten głos byłby tam obcy.

const VOICE_KEY = `${STORAGE_KEY}_voice`;
const voiceBtn = document.getElementById('voice-btn');
// Domyślnie WYŁĄCZONY: Starter to ~90 odpowiedzi/mies (~332 znaki średnio), więc
// automat na każdą odpowiedź zjadłby limit w kilka dni. Jedno tapnięcie włącza na stałe.
let voiceEnabled = localStorage.getItem(VOICE_KEY) === '1';
let currentAudio = null;
let currentAudioUrl = null;

function _renderVoiceBtn() {
    if (!voiceBtn) return;
    voiceBtn.textContent = voiceEnabled ? '🔊' : '🔇';
    voiceBtn.title = voiceEnabled ? 'Głos Astry: włączony' : 'Głos Astry: wyłączony';
}

function toggleVoice() {
    voiceEnabled = !voiceEnabled;
    localStorage.setItem(VOICE_KEY, voiceEnabled ? '1' : '0');
    if (!voiceEnabled) _stopAudio();
    _renderVoiceBtn();
}

function _stopAudio() {
    if (currentAudio) { try { currentAudio.pause(); } catch { } currentAudio = null; }
    if (currentAudioUrl) { URL.revokeObjectURL(currentAudioUrl); currentAudioUrl = null; }
}

async function speakText(text, btn) {
    const clean = (text || '').trim();
    if (!clean) return;
    _stopAudio();
    if (btn) btn.textContent = '⏳';
    try {
        const res = await fetch(`${API_URL}/api/speak`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: clean }),
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            appendSystemMsg(`Głos: ${err.detail || res.status}`);
            return;
        }
        const blob = await res.blob();
        currentAudioUrl = URL.createObjectURL(blob);
        currentAudio = new Audio(currentAudioUrl);
        // Autoplay bywa blokowany — wtedy zostaje przycisk 🔊 przy wiadomości.
        await currentAudio.play().catch(() => { });
    } catch (e) {
        appendSystemMsg(`Głos: ${e.message}`);
    } finally {
        if (btn) btn.textContent = '🔊';
    }
}

function _attachSpeakBtn(bubble, text) {
    if (!bubble || !text) return;
    const b = document.createElement('button');
    b.className = 'speak-btn';
    b.textContent = '🔊';
    b.title = 'Odtwórz głosem';
    b.onclick = () => speakText(text, b);
    bubble.appendChild(b);
}

// ── Push-to-talk: nagrywanie → WAV → transkrypcja serwerowa ───
//
// Świadomie NIE używamy Web Speech API: na Androidzie silnik kończy sesję po każdej
// wypowiedzi (systemowy dźwięk co ~4 s mówienia) i nie da się tego wyłączyć — potwierdzone
// pomiarem: 7 restartów na 40 s, zero błędów, każdy restart uzasadniony. To limit API.
//
// Kodujemy WAV w przeglądarce, zamiast wysyłać webm z MediaRecorder: WAV jest w
// udokumentowanych formatach Gemini i sprawdzony na żywym API. Wsparcie dla audio/webm
// nie jest udokumentowane, a bez ffmpeg (nie ma go ani lokalnie, ani na VPS) nie byłoby
// jak przekonwertować. Cena: większy upload. Zysk: zero zgadywania formatu.

const TARGET_SAMPLE_RATE = 16000;   // Gemini nie potrzebuje więcej; 4× mniejszy plik niż 48 kHz
const MAX_RECORDING_MS = 5 * 60 * 1000;

let isRecording = false;
let audioCtx = null;
let mediaStream = null;
let sourceNode = null;
let procNode = null;
let pcmChunks = [];
let captureSampleRate = 0;
let recordingTimeout = null;

function _flattenPcm(chunks) {
    const total = chunks.reduce((n, c) => n + c.length, 0);
    const out = new Float32Array(total);
    let off = 0;
    for (const c of chunks) { out.set(c, off); off += c.length; }
    return out;
}

function _downsample(samples, srcRate, dstRate) {
    if (dstRate >= srcRate) return samples;
    const ratio = srcRate / dstRate;
    const out = new Float32Array(Math.floor(samples.length / ratio));
    for (let i = 0; i < out.length; i++) {
        // uśrednianie okna zamiast brania co n-tej próbki — bez tego dochodzi aliasing
        const start = Math.floor(i * ratio);
        const end = Math.min(Math.floor((i + 1) * ratio), samples.length);
        let sum = 0;
        for (let j = start; j < end; j++) sum += samples[j];
        out[i] = end > start ? sum / (end - start) : 0;
    }
    return out;
}

function _encodeWav(samples, sampleRate) {
    const buf = new ArrayBuffer(44 + samples.length * 2);
    const view = new DataView(buf);
    const wstr = (off, str) => { for (let i = 0; i < str.length; i++) view.setUint8(off + i, str.charCodeAt(i)); };
    wstr(0, 'RIFF');
    view.setUint32(4, 36 + samples.length * 2, true);
    wstr(8, 'WAVE');
    wstr(12, 'fmt ');
    view.setUint32(16, 16, true);          // rozmiar bloku fmt
    view.setUint16(20, 1, true);           // PCM
    view.setUint16(22, 1, true);           // mono
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, sampleRate * 2, true);  // byte rate
    view.setUint16(32, 2, true);           // block align
    view.setUint16(34, 16, true);          // bits per sample
    wstr(36, 'data');
    view.setUint32(40, samples.length * 2, true);
    let off = 44;
    for (let i = 0; i < samples.length; i++) {
        const s = Math.max(-1, Math.min(1, samples[i]));
        view.setInt16(off, s < 0 ? s * 0x8000 : s * 0x7fff, true);
        off += 2;
    }
    return buf;
}

function _bufToBase64(buf) {
    const bytes = new Uint8Array(buf);
    let bin = '';
    const CHUNK = 0x8000;  // btoa na całości wywala stos przy dłuższych nagraniach
    for (let i = 0; i < bytes.length; i += CHUNK) {
        bin += String.fromCharCode.apply(null, bytes.subarray(i, i + CHUNK));
    }
    return btoa(bin);
}

function _micIdle() {
    isRecording = false;
    micBtn.textContent = '🎤';
    micBtn.classList.remove('recording');
    micBtn.disabled = false;
}

function _releaseMic() {
    if (recordingTimeout) { clearTimeout(recordingTimeout); recordingTimeout = null; }
    try { if (procNode) procNode.disconnect(); } catch { }
    try { if (sourceNode) sourceNode.disconnect(); } catch { }
    try { if (mediaStream) mediaStream.getTracks().forEach(t => t.stop()); } catch { }
    try { if (audioCtx && audioCtx.state !== 'closed') audioCtx.close(); } catch { }
    procNode = sourceNode = mediaStream = audioCtx = null;
}

async function toggleMic() {
    if (isRecording) { await _stopAndTranscribe(); return; }

    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        appendSystemMsg('Przeglądarka nie obsługuje nagrywania dźwięku.');
        return;
    }
    try {
        mediaStream = await navigator.mediaDevices.getUserMedia({
            audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true },
        });
    } catch {
        appendSystemMsg('Brak dostępu do mikrofonu — sprawdź uprawnienia strony.');
        return;
    }

    const AC = window.AudioContext || window.webkitAudioContext;
    audioCtx = new AC();
    captureSampleRate = audioCtx.sampleRate;
    sourceNode = audioCtx.createMediaStreamSource(mediaStream);
    procNode = audioCtx.createScriptProcessor(4096, 1, 1);
    pcmChunks = [];
    procNode.onaudioprocess = (e) => {
        if (!isRecording) return;
        pcmChunks.push(new Float32Array(e.inputBuffer.getChannelData(0)));
    };
    // ScriptProcessor odpala się tylko podpięty do wyjścia; gain 0 żeby nie było sprzężenia
    const mute = audioCtx.createGain();
    mute.gain.value = 0;
    sourceNode.connect(procNode);
    procNode.connect(mute);
    mute.connect(audioCtx.destination);

    isRecording = true;
    micBtn.textContent = '⏹';
    micBtn.classList.add('recording');
    // Bezpiecznik: gdyby user zapomniał wyłączyć, nie nagrywamy w nieskończoność
    recordingTimeout = setTimeout(() => { if (isRecording) _stopAndTranscribe(); }, MAX_RECORDING_MS);
}

async function _stopAndTranscribe() {
    isRecording = false;
    micBtn.textContent = '⏳';
    micBtn.classList.remove('recording');
    micBtn.disabled = true;

    const srcRate = captureSampleRate;
    const chunks = pcmChunks;
    pcmChunks = [];
    _releaseMic();

    const raw = _flattenPcm(chunks);
    if (!raw.length) { _micIdle(); return; }

    const samples = _downsample(raw, srcRate, TARGET_SAMPLE_RATE);
    const rate = srcRate > TARGET_SAMPLE_RATE ? TARGET_SAMPLE_RATE : srcRate;
    const wav = _encodeWav(samples, rate);

    try {
        const res = await fetch(`${API_URL}/api/transcribe`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ audio: `data:audio/wav;base64,${_bufToBase64(wav)}` }),
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            appendSystemMsg(`Transkrypcja nie powiodła się: ${err.detail || res.status}`);
            return;
        }
        const data = await res.json();
        const text = (data.text || '').trim();
        if (!text) { appendSystemMsg('Nie rozpoznano mowy w nagraniu.'); return; }
        // Tekst ląduje w polu — wysyłasz sam, po sprawdzeniu
        inputEl.value = inputEl.value.trim() ? `${inputEl.value.trim()} ${text}` : text;
        autoResize();
        inputEl.focus();
    } catch (e) {
        appendSystemMsg(`Transkrypcja nie powiodła się: ${e.message}`);
    } finally {
        _micIdle();
    }
}

// ── Event listeners ───────────────────────────────────────────

inputEl.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) {
        // Na telefonie Enter NIE wysyła — wstawia nową linię (zachowanie domyślne textarea).
        // Jedyna droga wysłania na mobile to kliknięcie ikony Wyślij.
        if (IS_TOUCH) return;
        e.preventDefault();
        sendMessage();
    }
});

inputEl.addEventListener('input', autoResize);

// ── Zdjęcia — pokazywanie Astrze/Amelii ───────────────────────
function _clearImagePreview() {
    pendingImage = null;
    const p = document.getElementById('image-preview');
    if (p) p.remove();
    if (imageInput) imageInput.value = '';
}
function _showImagePreview(dataUrl) {
    let p = document.getElementById('image-preview');
    if (!p) {
        p = document.createElement('div');
        p.id = 'image-preview';
        p.style.cssText = 'display:flex;align-items:center;gap:8px;padding:6px 10px;';
        const bar = inputEl.closest('.input-area') || inputEl.parentElement;
        bar.parentElement.insertBefore(p, bar);
    }
    p.innerHTML = '';
    const img = document.createElement('img');
    img.src = dataUrl;
    img.style.cssText = 'height:48px;border-radius:6px;';
    const label = document.createElement('span');
    label.textContent = 'zdjęcie gotowe';
    label.style.cssText = 'font-size:0.7rem;opacity:0.7;';
    const x = document.createElement('button');
    x.textContent = '✕';
    x.title = 'Usuń zdjęcie';
    x.onclick = _clearImagePreview;
    p.appendChild(img); p.appendChild(label); p.appendChild(x);
}
// Kompresja przed wysłaniem — telefony robią 10-20MB, Gemini ma limit inline ~20MB.
// Resize do max 1568px + JPEG q0.82 → zwykle <500KB. Gemini i tak downsampluje do kafelków, nic nie tracisz.
function _compressImage(file, maxDim = 1568, quality = 0.82) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => {
            const img = new Image();
            img.onload = () => {
                let w = img.width, h = img.height;
                if (w > maxDim || h > maxDim) {
                    if (w >= h) { h = Math.round(h * maxDim / w); w = maxDim; }
                    else { w = Math.round(w * maxDim / h); h = maxDim; }
                }
                const canvas = document.createElement('canvas');
                canvas.width = w; canvas.height = h;
                canvas.getContext('2d').drawImage(img, 0, 0, w, h);
                resolve(canvas.toDataURL('image/jpeg', quality));
            };
            img.onerror = reject;
            img.src = reader.result;
        };
        reader.onerror = reject;
        reader.readAsDataURL(file);
    });
}
if (imageInput) {
    imageInput.addEventListener('change', async () => {
        const file = imageInput.files && imageInput.files[0];
        if (!file) return;
        try {
            pendingImage = await _compressImage(file);
        } catch {
            // Fallback: surowy odczyt (np. format którego canvas nie dekoduje)
            pendingImage = await new Promise(res => {
                const r = new FileReader();
                r.onload = () => res(r.result);
                r.readAsDataURL(file);
            });
        }
        _showImagePreview(pendingImage);
    });
}

// ── History loader ────────────────────────────────────────────

function getHistoryEndpoint() {
    if (ROOM === 'amelia') return '/api/history/amelia';
    if (ROOM === 'wspolny') return '/api/history/wspolny';
    return '/api/history';
}

function parseSharedHistoryMessage(msg) {
    if (msg.role === 'user') {
        return { role: 'user', content: msg.content || '' };
    }

    const content = msg.content || '';
    const match = content.match(/^\[(astra|amelia)\]\s*/i);
    if (!match) {
        return { role: 'astra', content };
    }

    return {
        role: match[1].toLowerCase(),
        content: content.slice(match[0].length),
    };
}

function _renderCachedMsgs(msgs) {
    if (!msgs || msgs.length === 0) return;
    appendSystemMsg('— poprzednia rozmowa —');
    msgs.forEach(m => appendBubble(m.role, marked.parse(m.content || ''), m.thought || '', [], [], m.hint || '', m.narrator || ''));
    appendSystemMsg('— teraz —');
}

async function loadHistory() {
    // Jeśli brak conversationId — spróbuj przywrócić z cache
    if (!conversationId) {
        const cache = _cacheLoad();
        if (cache && cache.id && cache.msgs && cache.msgs.length > 0) {
            conversationId = cache.id;
            localStorage.setItem(STORAGE_KEY, conversationId);
            _cachedMsgs = [...cache.msgs];
            _renderCachedMsgs(_cachedMsgs);
        }
        _historyRendered = true;
        return;
    }

    // Cache-first — TYLKO poza Astrą. Dla Astry ta gałąź była przyczyną rozjazdu urządzeń
    // (patrz SERVER_TRUTH wyżej): backend nie był pytany, dopóki cache pasował do ID.
    if (!SERVER_TRUTH) {
        const localCache = _cacheLoad();
        if (localCache && localCache.id === conversationId && localCache.msgs?.length > 0) {
            _cachedMsgs = [...localCache.msgs];
            _renderCachedMsgs(_cachedMsgs);
            _historyRendered = true;
            return;
        }
    }

    // Pobierz z backendu (dla Astry: zawsze; dla reszty: gdy cache nie pasuje)
    try {
        const res = await fetch(`${API_URL}${getHistoryEndpoint()}?conversation_id=${conversationId}&n=30`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        if (!data.messages || data.messages.length === 0) throw new Error('empty');

        messagesEl.innerHTML = '';   // serwer nadpisuje to, co juz wisi w DOM — inaczej dublet
        _cachedMsgs = [];
        appendSystemMsg(`— poprzednia rozmowa (serwer, ${data.messages.length}) —`);
        let pominiete = 0;
        data.messages.forEach(msg => {
            // try/catch PER WIADOMOŚĆ: bez tego jeden feralny wpis (np. treść, na której
            // wykłada się marked.parse) przerywał CAŁĄ pętlę, a `catch` niżej dorzucał na to
            // zawartość z localStorage. Objaw: widok urywa się w połowie historii, mimo że
            // serwer przysłał komplet — dokładnie to, co Łukasz widział 15.08 na komputerze,
            // podczas gdy telefon pokazywał pełny wątek.
            try {
                let role = msg.role === 'user' ? 'user' : ROOM;
                let content = msg.content || '';

                if (ROOM === 'wspolny') {
                    const parsed = parseSharedHistoryMessage(msg);
                    role = parsed.role;
                    content = parsed.content;
                }

                appendBubble(role, marked.parse(content), msg.thought || '', [], [], msg.hint || '');
                _cachedMsgs.push({ role, content, thought: msg.thought || '', hint: msg.hint || '' });
            } catch (e) {
                pominiete++;
                console.error('[historia] nie udało się wyrenderować wiadomości', msg.timestamp, e);
            }
        });
        if (pominiete) appendSystemMsg(`⚠ pominięto ${pominiete} wiadomości przy renderowaniu`);
        appendSystemMsg('— teraz —');
        _cacheSave(); // odśwież cache danymi z backendu

    } catch (e) {
        // Backend niedostępny lub pusta historia — fallback do localStorage.
        // Przy SERVER_TRUTH to jedyna droga offline, więc musi zostać.
        // Czyścimy DOM: bez tego fallback DOKŁADAŁ cache do częściowo wyrenderowanej
        // historii z serwera, dając widok, który urywa się w środku i miesza dwa źródła.
        console.warn('[historia] serwer nieosiągalny/pusty — fallback do pamięci przeglądarki:', e.message);
        messagesEl.innerHTML = '';
        const cache = _cacheLoad();
        if (cache && cache.msgs && cache.msgs.length > 0) {
            _cachedMsgs = [...cache.msgs];
            appendSystemMsg('— offline: historia z pamięci przeglądarki —');
            cache.msgs.forEach(m => appendBubble(m.role, marked.parse(m.content || ''),
                m.thought || '', [], [], m.hint || '', m.narrator || ''));
            appendSystemMsg('— teraz —');
        }
    }
    _historyRendered = true;
}

// ── Poranna wiadomość ─────────────────────────────────────────

// Dedup wiadomości proaktywnych (fix potrójnego wyświetlania): SW push-relay
// (nasłuch 'message' niżej) i polling checkMorningMessage to dwie niezależne
// ścieżki do tej samej treści (state.morning_message) — żadna nie wie o drugiej,
// więc mogą się nałożyć. Zamiast spinać obie ścieżki wspólną flagą backendową,
// dedup po hashu treści po stronie klienta: zanim dołożymy bąbelek, sprawdzamy
// czy dokładnie ta treść już była pokazana.
const _PROACTIVE_HASH_KEY = `${STORAGE_KEY}_last_proactive_hash`;

function _hashText(s) {
    let h = 0;
    for (let i = 0; i < s.length; i++) {
        h = (Math.imul(31, h) + s.charCodeAt(i)) | 0;
    }
    return h.toString(36);
}

function _alreadyShownProactive(text) {
    try { return localStorage.getItem(_PROACTIVE_HASH_KEY) === _hashText(text); } catch { return false; }
}

function _markProactiveShown(text) {
    try { localStorage.setItem(_PROACTIVE_HASH_KEY, _hashText(text)); } catch { }
}

async function checkMorningMessage() {
    try {
        const res = await fetch(`${API_URL}/api/morning-message`);
        if (!res.ok) return;
        const data = await res.json();
        if (data.message && !_alreadyShownProactive(data.message)) {
            appendBubble('astra', marked.parse(data.message), '', [], []);
            _cachedMsgs.push({ role: 'astra', content: data.message, thought: '', hint: '' });
            _cacheSave();
            _markProactiveShown(data.message);
        }
    } catch {
        // cicho
    }
}

// ── Push notifications ─────────────────────────────────────────

function _urlBase64ToUint8Array(base64String) {
    const padding = '='.repeat((4 - base64String.length % 4) % 4);
    const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
    const raw = atob(base64);
    return Uint8Array.from([...raw].map(c => c.charCodeAt(0)));
}

// Stały identyfikator instalacji — przeżywa podmianę Service Workera i ponowną
// subskrypcję, więc backend wie, że to wciąż to samo urządzenie, mimo nowego endpointu FCM.
const _DEVICE_ID_KEY = `${STORAGE_KEY}_device_id`;

function _deviceId() {
    try {
        let id = localStorage.getItem(_DEVICE_ID_KEY);
        if (!id) {
            id = (crypto.randomUUID?.() || String(Date.now()) + Math.random().toString(36).slice(2));
            localStorage.setItem(_DEVICE_ID_KEY, id);
        }
        return id;
    } catch {
        return 'no-storage';
    }
}

async function setupPushNotifications() {
    if (!('serviceWorker' in navigator) || !('PushManager' in window)) return;

    try {
        const reg = await navigator.serviceWorker.ready;

        // Istniejąca subskrypcja: nie subskrybujemy ponownie, ale RAZ zgłaszamy ją
        // z device_id, żeby backend mógł posprzątać duplikaty sprzed tego fixu.
        const existing = await reg.pushManager.getSubscription();
        if (existing) {
            const flag = `${STORAGE_KEY}_devid_sent`;
            try {
                if (localStorage.getItem(flag) !== '1') {
                    await fetch(`${API_URL}/api/push/subscribe`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            ...existing.toJSON(),
                            device_id: _deviceId(),
                            user_agent: navigator.userAgent.slice(0, 120),
                        }),
                    });
                    localStorage.setItem(flag, '1');
                }
            } catch { /* cicho — to tylko sprzątanie */ }
            return;
        }

        // Pobierz VAPID public key
        const keyRes = await fetch(`${API_URL}/api/push/vapid-public-key`);
        if (!keyRes.ok) return;
        const { publicKey } = await keyRes.json();

        // Poproś o zgodę
        const permission = await Notification.requestPermission();
        if (permission !== 'granted') return;

        // Subskrybuj
        const sub = await reg.pushManager.subscribe({
            userVisibleOnly: true,
            applicationServerKey: _urlBase64ToUint8Array(publicKey),
        });

        // Wyślij na backend razem ze stałym device_id.
        // 2026-08-17: bez tego jedno urządzenie potrafiło mieć kilka żywych subskrypcji
        // naraz (WebAPK obok karty Chrome, podmiana SW) i dostawało tę samą wiadomość
        // dnia dwa razy — dedup po hashu niżej chroni tylko bąbelki, nie powiadomienia.
        await fetch(`${API_URL}/api/push/subscribe`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                ...sub.toJSON(),
                device_id: _deviceId(),
                user_agent: navigator.userAgent.slice(0, 120),
            }),
        });

        console.log('[PUSH] Subskrypcja zapisana');
    } catch (e) {
        console.warn('[PUSH] Błąd subskrypcji:', e);
    }
}

// ── Nasłuchuj wiadomości od Service Workera (push w tle) ──────

navigator.serviceWorker.addEventListener('message', e => {
    if (e.data?.type === 'ASTRA_MESSAGE' && e.data.body && !_alreadyShownProactive(e.data.body)) {
        appendBubble('astra', marked.parse(e.data.body), '', [], []);
        // 2026-08-06: BEZ tych dwóch linii wiadomość znikała przy pierwszym przerysowaniu.
        // loadHistory() renderuje z localStorage i robi `return` gdy cache pasuje do
        // conversationId — backendu nie pyta wcale. Wiadomość dostarczona push-relayem
        // trafiała więc tylko do DOM, nigdy do cache. Dodatkowo _markProactiveShown niżej
        // blokował polling przed dołożeniem jej porządnie → gwarantowana utrata.
        // Backend miał ją cały czas (potwierdzone w astra_memory_session_v1).
        // Parytet ze ścieżką pollingu (checkMorningMessage) jest tu WARUNKIEM poprawności.
        _cachedMsgs.push({ role: 'astra', content: e.data.body, thought: '', hint: '' });
        _cacheSave();
        _markProactiveShown(e.data.body);
    }
});

// ── Init ──────────────────────────────────────────────────────

initRoom();
_renderVoiceBtn();

if (SERVER_TRUTH) {
    // Sekwencyjnie, nie równolegle: fetchHealth() synchronizuje conversationId z backendem,
    // a loadHistory() go potrzebuje. Odpalane razem ścigały się — historia potrafiła wyrenderować
    // się ze starym ID, zanim health zdążył podać aktywny wątek.
    // fetchHealth() sam woła loadHistory(), gdy ID się zmieniło — stąd strażnik, żeby nie
    // renderować dwa razy.
    (async () => {
        await fetchHealth();
        if (!_historyRendered) await loadHistory();
        checkMorningMessage();
        setupPushNotifications();
    })();
} else {
    // Wspólny Pokój i Amelia — ścieżka sprzed 15.08, nietknięta.
    fetchHealth();
    loadHistory().then(() => {
        checkMorningMessage();
        setupPushNotifications();
    });
}
