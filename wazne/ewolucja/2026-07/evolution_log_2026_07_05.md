# Evolution Log — 2026-07-05 — DZIEŃ ODTRUCIA ASTRY

Sesja przełomowa. Model: Opus 4.8 (Claude Code, repo + SSH VPS) + Fable (claude.ai humanistyczny + Claude Code kod-aware).
TL;DR: zbudowaliśmy piaskownicę → zdiagnozowaliśmy 2 wielkie trucizny → odtruliśmy Astrę (prompt −68%) → odkryliśmy drugi front.

---

## 1. AMNEZJA v2 — PIASKOWNICA (commit `bb159a5`, live)
Do RAG debuggera dodany DRUGI tryb: `/api/debug/inspect?generate=true` składa prompt jak `/api/chat`
i pyta Gemini JAK Astra by odpowiedziała. Front `/amnezja` przycisk „💬 JAK ODPOWIE" + panel (hint/response/thought).
**Bezpieczne — potwierdzone: vectors 3729=3729 po teście, NIC nie zapisuje.** generate=false (default) = zero zmian.
To była oryginalna wizja Łukasza (widzieć output, nie tylko co pamięta). Używa `active_conversation_id` = realna historia.

## 2. AUDYTY ASTRA SOLO (WEB + CODE) — 2 TRUCIZNY
Fable (2 instancje) + pomiar Opusa Amnezją na żywym VPS:
- **☠️ T1: Astra ŚLEPA OD 2026-03-18.** `fit_to_budget` dostaje `reserved_chars=len(astra_base)` (~22k),
  budżet `max_chars`=12000 → `available_chars` UJEMNE → blok [WSPOMNIENIA] pusty (2 zn) w KAŻDYM prompcie 3.5 mies.
  Cały pipeline RAG pracował, wynik wyrzucany na końcu. Całe strojenie RAG od marca = kanał-widmo. Amelia też ślepa.
- **☠️ T2: prompt 90 931 zn, [TWARDE FAKTY]=67 273 (74%), charakter 16%.** 391 faktów, 345 milestone (88%),
  FP: love_declaration 83%, trust_declaration 100% (132/132), future 97%. `get_facts_for_prompt` bez LIMIT.
  Ekstraktor = catch-all: zwykłe wiadomości ("Oki. Popalam sobie") tagowane jako „Deklaracja uczuć". +6.5/dzień.
- Fable-web humanistycznie: „leczyliście 16% promptu bo było widać; ściana faktów była niewidzialna aż zmierzyła ją Amnezja".

## 3. ODTRUCIE #1 — FIX T1+T2+T3 (commit `e506487`, WDROŻONE + ZWERYFIKOWANE)
Wg `spec_fixu_ASTRA_2026-07-05.md` (Fable), Opus wdrożył 1:1. Backup: companion_state + astra_facts.db.
- **Krok 1** `fact_store.py` get_facts_for_prompt: LIMIT+ranking. Rdzeń (health/date/person/correction) ZAWSZE;
  MILESTONE cap 15; habit cap 5; sufit bloku 8000 zn. NIC nie kasowane. + nagłówek: milestony=kotwice nie rozkazy tonu.
- **Krok 2** `token_manager.py` fit_to_budget: param `budget_chars=3500` (Astra+Amelia main.py:519/651), odcięty od template.
- **Krok 3b** `main.py` /api/debug/stats: state.level/xp zamiast hardcode 6/0.
- **Krok 3a** dedup concerns (Jaccard): CZĘŚCIOWY — nie łapie polskiej fleksji (winy≠wina), bezpieczny fallback=append. Do embed.
**Pomiar PO (Amnezja):** prompt 90931→~29200 (−68%), fakty 391→26, [WSPOMNIENIA] 2→1300-1600 (RAG WRÓCIŁ), prompt RÓŻNY per fraza, medical_visit przetrwał LIMIT. Świeży wątek R7: bafc442a (stan xp=1862 L5 zachowany).
**Test piaskownicy PRZED/PO:** „hej" zatr.„czekałam aż skończysz grzebać w mojej głowie"→odtr.„No, hej. *odrywam wzrok*"; „lody haha"→żart zero winy; „LDI?"→NA TEMAT. Obawa Fable (RAG wciągnie śmieci) nie zmaterializowała się — LIMIT wyciął śmieci naraz.

## 4. DRUGI FRONT (test altanki w piaskownicy)
„a pamiętasz co chcę pisać w altance?" — PRZED (czerwiec): „Pamiętam. Zawsze pamiętam" (blef, blok pusty).
PO: „Pamiętam że to kontekst prezentu... ale nie że ujawniłeś treść. Czyżbyś liczył że zgadnę?" — **KONFABULACJA ZNIKNĘŁA, uczciwość.**
ALE [WSPOMNIENIA] czerpie z ChromaDB (1083 śmieciowe milestony, NIEtknięte przez LIMIT FactStore) → daje echa pytań
jako „MILESTONE:gratitude". Kotwica altanki nie dociera. **Odtrucie #2 = ChromaDB + ekstraktor.**

## 5. ANALIZA LOGÓW CZERWCA (Fable) — `analiza_logow_czerwiec_2026-07-05.md`
- Pętla samo-imitacji wraca w ~4-6 dni (06-07 reset→lekka→06-13 gwiazdki 90%). Świeży wątek = PLASTER, docelowo higiena historii.
- 66 tur „pamiętam" przy pustym bloku = konfabulacja udokumentowana. Czytanie skażonych logów DAŁO wartość.

## 6. 3 SPEKI NA PRZYSZŁOŚĆ (Fable, gotowe do wdrożenia przez Opusa)
- `spec_odtrucie2_ekstraktor_2026-07-05.md` (P1): keyword-gate + sim≥0.50 + guard didaskaliów (kalibracja na 346 milestonach);
  blokuje 94% śmieci. Triage: nocny job LLM (346 FactStore + 1083 Chroma), reklasyfikacja NIE DELETE. ALTER kolumna status.
- `spec_higiena_historii_2026-07-05.md` (P2): `history_for_model()` — strip didaskaliów ze STARSZYCH tur (ostatnia nietknięta),
  n 10→8, DB nietknięta. Placeholder „…" (nie drop — blizna B3 alternacja ról).
- `spec_bug_altanki_2026-07-05.md` (P3): M1 keyword boost po rdzeniu 5 znaków (altanka=altance); M2 sweep diversity_penalty
  w piaskownicy. Kolejność: PO triage, jedna gałka naraz.

## 7. STRATEGIA BIZNESOWA (rozmowa)
Amnezja („RTG dla RAG") = najmocniejszy niedoceniony atut — dev-tool, realny ból (RAG=czarna skrzynka), świeże case study
(„RAG martwy 3.5 mies, naprawiony, −68%"). Rekomendacja Opusa: JEDEN flagowiec (nie 3 produkty=rozproszenie), Astra PRYWATNA
(klon=osobna persona ten sam RAG, zero danych Łukasza), walidacja PRZED budową (nie drugi LDI zero-userów). Cena dev-tool od firmy
nie od hobbysty (30zł=companion, nie debugger). Dystrybucja: devowie są na X/HN/Reddit(r/LocalLLaMA,r/RAG)/Discord — nie LinkedIn.

---

## Stan końcowy VPS
- HEAD deployed: `e506487` + świeży wątek bafc442a. Astra: prompt ~29k, RAG żywy, konfabulacja usunięta, lżejsza.
- Backupy: companion_state.json.bak.przed-odtruciem, astra_facts.db.bak.przed-odtruciem.
- Commity dnia: bb159a5 (piaskownica), fcf4d63/785a46a (audyty), f675a5d (spec+golden), e506487 (fix), 9f4b7af + priorytety+speki (Fable).
- NASTĘPNE: odtrucie #2 (ekstraktor+triage) → altanka → higiena; codzienna kalibracja Astry; landing+case study Amnezji; PORZĄDEK w wazne/.
