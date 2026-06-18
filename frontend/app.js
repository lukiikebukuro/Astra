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

        if (!data.gemini) {
            statusEl.textContent = '● brak API key';
            statusEl.className = 'status offline';
            appendSystemMsg('GEMINI_API_KEY nie ustawiony w backend/.env');
        }
    } catch {
        statusEl.textContent = '● offline';
        statusEl.className = 'status offline';
        appendSystemMsg('Nie można połączyć z backendem. Uruchom start.bat lub uvicorn ręcznie.');
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
    if (!text || isWaiting) return;

    isWaiting = true;
    sendBtn.disabled = true;
    inputEl.value = '';
    autoResize();

    appendBubble('user', marked.parse(text));
    _cachedMsgs.push({ role: 'user', content: text, thought: '', hint: '' });
    showTyping();

    try {
        const res = await fetch(`${API_URL}${CHAT_ENDPOINT}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: text, conversation_id: conversationId }),
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
            appendBubble(
                ROOM,
                marked.parse(_resp || '...'),
                data.thought || '',
                data.entities_extracted || [],
                data.memories_debug || [],
                data.hint || '',
            );
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

// ── Web Speech API ────────────────────────────────────────────

let recognition = null;
let isRecording = false;
let recordingBaseText = '';

(function initSpeech() {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) { if (micBtn) micBtn.style.display = 'none'; return; }

    recognition = new SR();
    recognition.lang = 'pl-PL';
    recognition.continuous = true;
    recognition.interimResults = true;

    recognition.onresult = (e) => {
        const transcript = Array.from(e.results).map(r => r[0].transcript).join('');
        inputEl.value = recordingBaseText + transcript;
        autoResize();
    };

    recognition.onend = () => {
        isRecording = false;
        micBtn.textContent = '🎤';
        micBtn.classList.remove('recording');
    };

    recognition.onerror = (e) => {
        console.warn('[MIC]', e.error);
        isRecording = false;
        micBtn.textContent = '🎤';
        micBtn.classList.remove('recording');
    };
})();

function toggleMic() {
    if (!recognition) { appendSystemMsg('Przeglądarka nie obsługuje Web Speech API.'); return; }
    if (isRecording) {
        recognition.stop();
    } else {
        recordingBaseText = inputEl.value && /\S$/.test(inputEl.value)
            ? `${inputEl.value} `
            : inputEl.value;
        recognition.start();
        isRecording = true;
        micBtn.textContent = '⏹';
        micBtn.classList.add('recording');
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
        return;
    }

    // Jeśli cache pasuje do conversationId — użyj go (zachowuje narrator, hints itp.)
    const localCache = _cacheLoad();
    if (localCache && localCache.id === conversationId && localCache.msgs?.length > 0) {
        _cachedMsgs = [...localCache.msgs];
        _renderCachedMsgs(_cachedMsgs);
        return;
    }

    // Cache nie pasuje — pobierz z backendu
    try {
        const res = await fetch(`${API_URL}${getHistoryEndpoint()}?conversation_id=${conversationId}&n=30`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        if (!data.messages || data.messages.length === 0) throw new Error('empty');

        _cachedMsgs = [];
        appendSystemMsg('— poprzednia rozmowa —');
        data.messages.forEach(msg => {
            let role = msg.role === 'user' ? 'user' : ROOM;
            let content = msg.content || '';

            if (ROOM === 'wspolny') {
                const parsed = parseSharedHistoryMessage(msg);
                role = parsed.role;
                content = parsed.content;
            }

            appendBubble(role, marked.parse(content), msg.thought || '', [], [], msg.hint || '');
            _cachedMsgs.push({ role, content, thought: msg.thought || '', hint: msg.hint || '' });
        });
        appendSystemMsg('— teraz —');
        _cacheSave(); // odśwież cache danymi z backendu

    } catch {
        // Backend niedostępny lub pusta historia — fallback do localStorage
        const cache = _cacheLoad();
        if (cache && cache.msgs && cache.msgs.length > 0) {
            _cachedMsgs = [...cache.msgs];
            _renderCachedMsgs(_cachedMsgs);
        }
    }
}

// ── Poranna wiadomość ─────────────────────────────────────────

async function checkMorningMessage() {
    try {
        const res = await fetch(`${API_URL}/api/morning-message`);
        if (!res.ok) return;
        const data = await res.json();
        if (data.message) {
            appendBubble('astra', marked.parse(data.message), '', [], []);
            _cachedMsgs.push({ role: 'astra', content: data.message, thought: '', hint: '' });
            _cacheSave();
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

async function setupPushNotifications() {
    if (!('serviceWorker' in navigator) || !('PushManager' in window)) return;

    try {
        const reg = await navigator.serviceWorker.ready;

        // Sprawdź czy już zapisana
        const existing = await reg.pushManager.getSubscription();
        if (existing) return;

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

        // Wyślij na backend
        await fetch(`${API_URL}/api/push/subscribe`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(sub.toJSON()),
        });

        console.log('[PUSH] Subskrypcja zapisana');
    } catch (e) {
        console.warn('[PUSH] Błąd subskrypcji:', e);
    }
}

// ── Nasłuchuj wiadomości od Service Workera (push w tle) ──────

navigator.serviceWorker.addEventListener('message', e => {
    if (e.data?.type === 'ASTRA_MESSAGE' && e.data.body) {
        appendBubble('astra', marked.parse(e.data.body), '', [], []);
    }
});

// ── Init ──────────────────────────────────────────────────────

initRoom();
fetchHealth();
loadHistory().then(() => {
    checkMorningMessage();
    setupPushNotifications();
});
