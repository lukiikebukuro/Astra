---
name: anomalytech.eu — plan nowego portfolio
description: Dokładna specyfikacja nowego portfolio Anomaly Tech — co wchodzi, jak wygląda, co mówi
type: project
---

# anomalytech.eu — specyfikacja portfolio

**Why:** Rebranding z adeptai.pl na anomalytech.eu. Portfolio musi działać jako narzędzie acqui-hire outreach do Tidio/LiveChat/Gorgias/Algolia. Musi być po angielsku, ciemne/elektryczne, z 4 konkretnymi kartami projektów.

**How to apply:** Gdy Łukasz ma energię — siadamy i budujemy to od zera. Wszystkie decyzje poniżej są zatwierdzone przez Łukasza ("ta strona ma dokładnie tak wyglądać").

---

## Branding

- **Domena:** anomalytech.eu
- **Nazwa firmy:** Anomaly Tech
- **Język:** angielski (cały serwis)
- **Design:** ciemny/elektryczny (NIE jasny korporacyjny niebieski jak adeptai.pl)
- **Email kontakt:** do ustalenia (nie kontakt@adept-ai.pl)

---

## Struktura portfolio — 4 karty projektów

### 1. LDI — Lost Demand Intelligence (FLAGSHIP)
- **Nazwa produktu:** `LDI — Lost Demand Intelligence`
- **Tagline:** *Training signal engine for purchase intent — real behavioral data, not synthetic labels*
- **Co pokazać:**
  - Intent classification <50ms, 93% accuracy na prawdziwym ruchu
  - Reward signal z anti-bait mechaniką (novel, publishable)
  - Behavioral data flywheel — nie syntetyczne dane, prawdziwe kliknięcia/bouncy
  - Domain-agnostic proof: moto + elektro = dwie domeny
  - GDPR, WebSocket, live dashboard — produkcyjne, nie prototyp
  - Link: adeptai.pl/demo
- **Badge:** Flagship / Live

### 2. Astra / ANIMA (INNOVATION)
- **Nazwa:** `ANIMA — Persistent Memory Engine`
- **Tagline:** *Private deployment — architecture available on request*
- **Co pokazać:**
  - Diagram 3-kanałowego RAG (personal memories + character_core + project knowledge)
  - Fragment kodu ekstraktora encji (PERSON, MILESTONE, EMOTION, MEDICATION itd.)
  - Przykład jak wygląda wektor w ChromaDB
  - Reranker: importance + recency + similarity + keyword_boost
  - NIE linkować myastra.pl publicznie — prywatny deployment
  - Framing: "private AI companion with persistent RAG memory" = produkt badawczy, nie waifu
- **Badge:** Innovation / RAG Memory

### 3. Skankran (ORIGIN STORY)
- **Nazwa:** `Skankran.pl`
- **Tagline:** *First water quality analysis platform of its kind in Poland — built in 4 months, zero prior programming experience*
- **Co pokazać:**
  - Zbudowane w 4 miesiące od zera, Łukasz nie umiał programować
  - Pierwsza taka platforma w Polsce (możliwe że na świecie)
  - AquaBot trenowany na wiedzy WHO/EPA
  - Digitalizacja rządowych PDF-ów, własny parser danych
  - Link: skankran.pl
- **Badge:** Origin Story / Pioneer

### 4. Gemini XHR Hack (HACKER CARD)
- **Nazwa:** `LLM Stream Injection — Gemini RAG Bypass`
- **Tagline:** *Client-side LLM augmentation proof of concept*
- **Opis:** *Reverse-engineered Gemini's XHR stream to inject external RAG context in real-time — proof of concept for LLM augmentation without API access.*
- **Co pokazać:**
  - Krótki screen recording lub GIF (20-30 sekund), autoplay loop na stronie
  - Widać: normalny Gemini → Twój overlay → odpowiedź z wstrzykniętym kontekstem
  - Bez słów — samo wideo mówi wszystko, każdy tech sam rozumie
  - Framing: "research / proof of concept", NIE "złamałem regulamin"
- **Badge:** Research / Proof of Concept

---

## Co WYLATUJE z obecnego adeptai.pl
- Gmina-AI — do kosza
- Cały jasny/niebieski design
- Polska treść
- ADEPT AI branding

---

## Co zachowujemy z adeptai.pl
- Struktura HTML kart (dobra, do przepisania warstwy CSS + treści)
- Skankran karta (zaktualizowana)
- Demo link do LDI

---

## Tech stack nowego portfolio
- Statyczny HTML/CSS/JS (bez Flask — portfolio nie potrzebuje backendu)
- LUB Flask jeśli będzie contact form
- Ciemny motyw: tło #0a0a0f lub podobne, elektryczne akcenty (cyan/fiolet/zielony neon)
- Font: Inter lub podobny
- Animacje: scroll-based fadeIn (jak w obecnym)

---

## Kiedy budować
Gdy Łukasz będzie miał energię po Stelarze. Nie teraz.
