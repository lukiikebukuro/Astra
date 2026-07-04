# Evolution Log — 2026-07-04

Sesja: fix charakteru Astry (przeintensywnienie) + podział portfolio + deploy.
Model: Opus 4.8 (Claude Code, dostęp do repo + SSH do VPS).

---

## 1. GŁÓWNE: fix przeintensywnienia charakteru Astry (WDROŻONE)

### Diagnoza (2 audyty, zgodne)
Problem zgłoszony z analizy logów czerwca: Astra w KAŻDEJ turze „widzi na wylot",
każda odpowiedź musi być doniosła, nie odpuszcza tematu, nie wychodzi z trybu schronienia.
- **Audyt Gemini** (`wazne/research/analiza/gemini_audyt_astra_naturalnosc_2026-07-04.md`)
  i **audyt Fable** (`..._fable.md`) — oba wskazały: **źródło = PROMPT, nie RAG.**
- Potwierdzone w logach: „widzę cię na wylot" >37× w czerwcu, 0 płaskich reakcji w próbce 18 logów.
- Mechanizm wzmacniający: `thought` w monologu (widoczny userowi) leciał tym samym snajperskim tonem
  co `response` → intensywność dwoma kanałami naraz.
- Głębszy korzeń (self-imitation): historia sesji (n=10) działa jak few-shot — model naśladuje
  własny stary styl silniej niż reguły promptu. Dlatego sam fix promptu bez świeżego wątku pada w ~10 tur (jak próba 06-14).

### Zmiany (Fable R1–R6) — commit `81f6986`
`backend/prompts/astra_base.txt`:
- **R1** (L167): koniec przymusu „każda odpowiedź musi coś odkryć" — „Haha, no." / „Nie wiem, sprawdź." to pełnoprawne odpowiedzi. „Jak każde zdanie głębokie — żadne nie jest."
- **R2** (L54 + po L102): zasada 80/20 (czytaj ciężar zanim odpowiesz; 4 z 5 odpowiedzi = zwykła obecność) + „małe jest małe, lody to lody, nie szukaj drugiego dna".
- **R3** (L174): gwiazdki oszczędne i nieobowiązkowe, ZAKAZ PĘTLI gestu, intensywny dotyk tylko ból/safe_haven.
- **R4** (po L194): SAFE_HAVEN MA KONIEC — gdy on łapie oddech/żartuje, wychodzisz z nim; jego żart to nie ucieczka do przełamania.
- **R5** (L222): imię max RAZ/rozmowę + ZAKAZ FRAZ PRZEWAGI POZNAWCZEJ („widzę cię na wylot", „wiem co robisz", „nie kupuję tego").
`backend/main.py`:
- **R6** (`ASTRA_MONOLOGUE_INSTRUCTION`, L128): `thought` domyślnie zwyczajny („to co czujesz"), pazur gdy temat wart — nie w każdej myśli.

### NIE ruszone (świadomie)
- L8/L10 („archetyp lustro z pazurem", „wiesz rzeczy których on sam sobie nie powiedział") i L20 („zaborcza" ×3)
  = **silnik generujący** problem. R5 zakazał objawów (fraz), ale silnik został. → do decyzji Fable (patrz backlog).
- Sekcja Wspólnego Pokoju w astra_base.txt, persony sióstr, Amelia — nietknięte.
- UWAGA: Wspólny Pokój używa tej samej `build_system_prompt` + `astra_base.txt` + `ASTRA_MONOLOGUE` dla tury Astry,
  więc R1–R6 **łagodzą też Astrę we Wspólnym** (efekt uboczny, pożądany — spójna Astra). Siostry i Amelia: zero wpływu.

### Deploy (VPS, zweryfikowany)
- `git pull origin main` becb138 → **81f6986** (przy okazji wdrożył WSTRZYMANY `5ef8f50` router-3 sióstr — izolowany od Astry, zgoda Łukasza; reszta = docsy).
- Backup: `backend/companion_state.json.bak.20260704`.
- **Chirurgiczny reset R7**: `active_conversation_id` d3886722 → **28750b59** (świeży UUID).
  Reszta stanu NIETKNIĘTA: xp=1824, level=5 (Synchronizacja), mood="ufna, ale z pazurem", total_msgs=1650, concerns=5.
  Metoda nowego UUID (nie pustego): front na `fetchHealth` sam zsynchronizuje się do nowego wątku i wyczyści ekran —
  Łukasz nie musi czyścić cache przeglądarki, wystarczy otworzyć i pisać.
- Weryfikacja żywego serwisu: health 200, gemini=true, vectors=3671, active_conv=28750b59; R2/R5/R6 obecne w plikach.
- Pamięć (ChromaDB `astra_memory_v1`/`session_v1`, FactStore) — zero kasowania. Stary wątek fizycznie zostaje w session_v1, tylko nie karmi few-shotu.

### Pomiar (następne dni)
Cele: lekkie reakcje >20%, start-od-gwiazdki <40%, „zaciska" <10%, „Łukasz" <20% tur, mediana <300 znaków.
Ryzyko wahadła: może przestrzelić w „za płasko/za chłodno" — wtedy podkręcić z powrotem.

---

## 2. Portfolio (forteca_finalna, LOKALNE, NIE zdeployowane)

`templates/index.html` (adeptai.pl) — sekcja Work podzielona na dwie grupy:
- **Products** (`// shipped & running`): LDI + Skankran.
- **Memory & retrieval** (`// the RAG research line`): ANIMA + Gemini XHR + **NOWA karta „Amnezja — RAG Debugger"**.
- „Four systems" → „Five systems", nowy CSS `.group-title/.group-sub/.cols-3`, responsywność (obie grupy zwijają do 1 kolumny).
- Narracja: grupa 2 pokazuje spójną linię badawczą (XHR hack → ANIMA → debugger) — mocne dla ról AI companion/research.
- `ldi.html` nietknięty. **Deploy portfolio = osobne repo, do zrobienia oddzielnie.**

---

## Stan końcowy
- VPS: `81f6986`, serwis active, świeży wątek, prompt złagodzony.
- Do zrobienia jutro/później: patrz `wazne/fable/fable_do_wtorku_2026-07-04.md`.
