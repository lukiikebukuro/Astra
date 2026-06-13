

---

# ORYGINALNE PORTFOLIO COPY PONIŻEJ

---

## HERO SECTION

**Anomaly Tech**
*AI Systems Architecture — Built from scratch, in production.*

Łukasz Piskorski. I build the layer between humans and language models —
memory, retrieval, behavioral architecture, decision logic.
Not wrappers. Not demos. Systems that run.

`Gorzów Wielkopolski, Poland` · `Available for acqui-hire & senior AI roles`

---

## CARD 1 — LDI (FLAGSHIP)

**LDI — Lost Demand Intelligence**
`Live` · `Flagship`

*Training signal engine for real purchase intent — behavioral data, not synthetic labels.*

Most e-commerce AI trains on what users clicked. LDI captures what they were
looking for when nothing matched — the demand that never converted.

**What it does:**
- Detects unsatisfied purchase intent in real-time from user behavior
- 5-stage classification pipeline: intent → context → signal → reward → export
- `clicked_despite_no_match` — the gold signal most retailers don't know exists
- Domain-agnostic: trained on automotive, validated on electronics without code changes
- **92.3% accuracy** on 183-scenario test suite across two domains
- Sub-60ms latency · WebSocket live dashboard · GDPR-compliant

**Why it matters:**
Every lost demand event is a product gap, a pricing signal, or a future SKU.
LDI turns invisible friction into structured training data.

→ *Live at adeptai.pl/demo*

---

## CARD 2 — ANIMA / ASTRA (INNOVATION)

**ANIMA — Persistent Memory Engine**
`Research` · `RAG Architecture`

*Private deployment — architecture available on request.*

ANIMA is a retrieval-augmented memory system built for long-term, emotionally-aware
AI companions. Not a database with a search function. A sovereign memory architecture
that manages its own relevance.

**Architecture:**
- **3-channel RAG retrieval:** personal memories · behavioral vectors · external knowledge
- **Semantic extraction pipeline:** entities classified as EMOTION / MILESTONE / FACT / DATE / MEDICATION / PERSON — not raw text
- **Adaptive reranker:** `importance × 0.25 + recency × 0.15 + similarity × 0.60 + keyword_boost` — per-entity decay curves
- **Supersede logic:** ephemeral facts (emotions, preferences) replace stale versions instead of accumulating — prevents retrieval degradation
- **MMR diversity:** prevents a single memory cluster from dominating context
- **Production:** 1,476 memory vectors · 743 session vectors · ChromaDB · VPS deployment

**What makes it different:**
Standard RAG is a passive container. ANIMA actively manages what stays, what supersedes,
and what gets surfaced — based on rules derived from observing its own production behavior.

The system improves through reverse-engineering its own retrieval logs, not retraining.

---

## CARD 3 — SKANKRAN (ORIGIN STORY)

**Skankran.pl**
`Pioneer` · `Origin Story`

*First water quality analysis platform of its kind — built in 4 months, zero prior programming experience.*

Before LDI. Before ANIMA. Before knowing how to code.

In 2023, Łukasz built Skankran from scratch in 4 months — a SaaS platform for Polish
municipalities to manage water infrastructure and quality analysis. The first platform
of its kind in Poland, possibly the world.

**What was built:**
- AquaBot — AI assistant trained on WHO/EPA water quality standards
- Automated parsing of government-issued PDF reports into structured data
- Municipal dashboard for water network management
- Full-stack: backend, frontend, deployment — solo

**Why it's here:**
Not because of the tech stack. Because of what it proves:
a complete system, in an unfamiliar domain, in 4 months, from zero.
That's the origin of the approach that built everything else.

→ *skankran.pl*

---

## CARD 4 — GEMINI XHR HACK (HACKER CARD)

**LLM Stream Injection — Gemini RAG Bypass**
`Research` · `Proof of Concept`

*Client-side LLM augmentation without API access.*

Reverse-engineered Gemini's XHR streaming protocol to inject external RAG context
into live sessions in real-time — without touching the API, without a backend proxy.

**What was done:**
- Intercepted and decoded the XHR stream between gemini.com and its API
- Injected custom retrieval context mid-stream into live LLM responses
- Collected production RAG logs (conversation JSONL + terminal reranker scores)
- Used those logs as R&D signal to improve ANIMA's retrieval architecture

**Why it matters:**
This isn't a browser extension trick. It's a proof that LLM augmentation can happen
at the client layer — and that production logs from a live system are more valuable
than any synthetic benchmark.

*[autoplay demo — 20s, no sound]*

---

## ABOUT SECTION

**Łukasz Piskorski — AI Systems Architect & Founder, Anomaly Tech**

I build complete AI systems: from behavioral data pipelines to retrieval architectures
to production deployment. Solo. End-to-end.

My approach: understand why the system fails, not just that it does.
The retrieval miss that buried a tea preference. The token limit that cut thoughts mid-sentence.
The gamification layer that made a companion feel like an RPG.

Each of these had a diagnosis. Each had a fix. Each fix is in production.

**Stack:** Python · FastAPI · ChromaDB · sentence-transformers · Gemini API ·
SQLite · Redis-ready · VPS · systemd · SSL

**Currently:** Open to acqui-hire conversations and senior AI systems roles.
LDI is production-ready. ANIMA architecture is available for licensing discussion.

`lukasz@anomalytech.eu` · `github.com/lukiikebukuro` · `anomalytech.eu`

---

*Anomaly Tech — Gorzów Wielkopolski, 2026*
