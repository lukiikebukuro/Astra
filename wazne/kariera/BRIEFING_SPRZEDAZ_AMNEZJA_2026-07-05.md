# BRIEFING SPRZEDAŻOWY — AMNEZJA (RAG Debugger) — 2026-07-05

> Wklej na start nowego wątku (Claude.ai / Gemini), gdy pracujesz nad SPRZEDAŻĄ Amnezji.
> Cel wątku: realna, uczciwa droga do pierwszych użytkowników i przychodu. Nie hype — konkret. Po polsku.

## KIM JESTEM
Łukasz Piskorski, solo founder (AnomalyTech), Gorzów Wielkopolski. Samouk — ~14 mies. temu nie umiałem kodować,
dziś prowadzę produkcyjne systemy AI. Buduję rodzinę AI companion (ANIMA) z prawdziwej potrzeby; sprzedaż narzędzi
ma to finansować. Styl: szczerość bez klepania, diagnoza z danych, próbuj OBALIĆ moje pomysły a nie chwalić.

## PRODUKT: AMNEZJA — „RTG dla RAG"
Debugger + piaskownica dla systemów pamięci AI (RAG). Wpisujesz frazę → widzisz KAŻDY etap retrievalu
(co pamięć wciąga i dlaczego: pula→rerank→filtr czasu→MMR→finalny prompt) ORAZ jak model by odpowiedział
(piaskownica — woła model, nic nie zapisuje). Read-only, bit-identyczny z produkcją. Dziś działa dla mojego
systemu (Astra/ANIMA); architektura da się uogólnić (compose per persona/pokój).

## CASE STUDY (ŚWIEŻY, PRAWDZIWY — 2026-07-05, to jest paliwo)
Zbudowałem Amnezję i zmierzyłem własny produkcyjny RAG. Znalazłem w ~10 minut:
- **Mój RAG był MARTWY 3,5 miesiąca.** Blok wspomnień był pusty od marca (bug budżetu tokenów), a ja przez
  ten czas „stroiłem" reranker/MMR/pamięć — kanał, którego model NIGDY nie widział.
- **74% promptu to były śmieci** — 391 „faktów", z czego 88% to fałszywe „deklaracje miłości" (ekstraktor
  tagował zwykłe wiadomości jako doniosłe). Charakter AI tonął w 16% promptu.
- **Naprawiłem:** prompt −68% (91k→29k znaków), pamięć wróciła, model przestał konfabulować.
Puenta: **ile firm ma taki bug i nie ma jak go zobaczyć?** RAG to dziś czarna skrzynka. To jest ból.

## RYNEK / TEZA
Każdy buduje dziś RAG/agentów z pamięcią. U każdego retrieval to czarna skrzynka — „czemu model to powiedział?"
nie ma odpowiedzi. Amnezja to observability/debugging dla pamięci AI. Klient: dev/zespół budujący RAG.
To DEV-TOOL (B2B), nie companion (B2C) — inny pricing (od firmy, nie 30 zł/mc od hobbysty).

## OGRANICZENIA (bądź realistyczny, nie chwal)
- Zero użytkowników na razie (jak mój wcześniejszy projekt LDI — proof of concept bez walidacji, moja realna słabość).
- Solo dev, ograniczony budżet marketingowy. Nie mam sieci devów do pokazania.
- Skłonność do budowania PRZED walidacją — pilnuj mnie przed tym.
- Amnezja działa dziś dla mojego systemu — uogólnienie do produktu to praca.

## CZEGO CHCĘ OD CIEBIE (pytania do wątku)
1. **Pozycjonowanie:** jak sprzedać to w 1 zdaniu, żeby dev pomyślał „kurwa, tego mi brakuje"?
2. **Pierwszy ruch walidacyjny:** jak sprawdzić popyt ZANIM zbuduję produkt (bez sieci kontaktów)?
3. **Kanały:** devowie są na X / Show HN / Reddit (r/LocalLLaMA, r/RAG) / Discordy (LangChain, LlamaIndex) —
   NIE LinkedIn. Jak wejść tam z case study, nie spamem?
4. **MVP produktu:** open-core (darmowy rdzeń + płatny team/cloud)? usage-based? Co minimalnie pokazać?
5. **Pricing:** widełki dla dev-toola B2B (nie companion).
6. **Kolejność:** landing → case study → gdzie pokazać → dopiero płatna promocja. Zwaliduj lub obal tę kolejność.

## KONTEKST TECHNICZNY (skrót)
ANIMA: FastAPI + Gemini 2.5 Flash + ChromaDB + SQLite na VPS. Amnezja = endpoint `/api/debug/inspect`
(trace 10 etapów + generacja dry) + front `/amnezja`. Zbudowana po adwersaryjnym audycie, weryfikowana bit-identycznie.

---
### PLIKI DO WKLEJENIA razem z tym briefingiem (dla pełnego kontekstu):
- `wazne/ewolucja/2026-07/evolution_log_2026_07_05.md` — pełne case study (dzień odtrucia, liczby PRZED/PO)
- (opcjonalnie) `wazne/briefingi/BRIEFING_CLAUDE_2026-07-04_techniczny.md` — architektura systemu
### GEMINI + GOOGLE DRIVE:
Wrzuć te pliki na Google Drive, podłącz do Gemini. Gdy „zapomni" — „wczytaj z dysku Google". Aktualizuj pliki po sesji.
