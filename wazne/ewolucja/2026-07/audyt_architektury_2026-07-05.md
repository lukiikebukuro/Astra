# FABLE — PROAKTYWNY AUDYT ARCHITEKTURY ANIMY (P0.5)
**Data:** 2026-07-05 | **Repo:** `main` @ `a2f901a` (deployed `becb138`, R1-R6 `81f6986`) | **Tryb:** read-only, zero implementacji
**Work-order:** `wazne/fable/fable_audyt_architektury_2026-07-04.md` | Baza dowodowa: fable_6/7, audyt naturalności (441 tur, pomiary), kod sióstr main.py:1676-1925, persony, projekt pokoju, diffy.

---

## TEZA GŁÓWNA

Próbowałem obalić tezę, że system jest chory architektonicznie — nie obaliłem. ANIMA to dziś **cztery luźno spokrewnione systemy udające jeden**, a świeże bóle (przeintensywnienie Astry, monopol Nazuny, recytacja lore sióstr) to objawy **trzech chorób systemowych**, nie osobne bugi:
1. **rozmnożone składanie promptu** — fix charakteru leczy jedną personę, choroba wraca u następnej;
2. **styl żyje w historii sesji, nie w prompcie** — fixy promptów umierają w ~10 tur;
3. **stan i polityki są kodem, nie danymi** — każdy nowy pokój reimplementuje te same mechanizmy i otwiera te same stare rany.

---

## RANKING: impact × koszt naprawy × ryzyko-jak-zostawimy

| # | Problem | Impact | Koszt | Ryzyko jak zostawimy | Kiedy |
|---|---|---|---|---|---|
| 1 | 4 ścieżki składania promptu | KRYTYCZNY | L (etapami M) | każda choroba leczona ×4, dryf person | TERAZ (fundament) |
| 2 | Pętla samo-imitacji (historia jako few-shot) | KRYTYCZNY (zmierzony) | M | każdy fix charakteru = jednorazowy | TERAZ (obejście) / potem korzeń |
| 3 | Zamknięta pula pamięci sióstr (11 kotwic) | WYSOKI | S | siostry = pozytywka z lore | TERAZ |
| 4 | Stan: JSON + globale, bez wersji, reset() zeruje wszystko | WYSOKI | M | utrata relacji (XP 3434→1824 już się STAŁO) | TERAZ (minimalnie) |
| 5 | Prompt bez budżetu globalnego, fakty bez LIMIT | ŚREDNI (pełzający) | M | koszt+latencja+rozmycie rośnie co miesiąc | TERAZ-ish (przed golden setem) |
| 6 | Siostry poza Amnezją i poza archiwum | ŚREDNI | S (archiwum: 2 linie) | strojenie na oko; flash-reset kasuje dom | TERAZ (archiwum), Amnezja z #1 |
| 7 | Scoping cross-room bez jednego miejsca definicji | ŚREDNI | M | „skąd ona to wie" — przecieki nie do debugowania | przy #1 |
| 8 | Router sióstr na szumie (3 listy, substring) | ŚREDNI | S | kalibracja głosów zafałszowana | TERAZ (w fixie P0) |
| 9 | Monotonia milestonów (773 + 180 FactStore) | ŚREDNI | M | powtarzalność wszystkich person | po Amnezji-dla-wszystkich |
| 10 | Brak wspólnej higieny echo/anty-powtórki | NISKI-ŚR | S (przy #1) | każda persona wymyśla koło od nowa | przy #1 |
| 11 | Drobiazgi: sekwencyjne 3 calle grupy, zegar bez override, brak licznika kosztu | NISKI | S | latencja, nietestowalna noc, ślepy budżet | przy fixie P0 |

---

## DOWODY (per problem)

### #1 — Cztery niezależne ścieżki składania promptu
| Endpoint | Composer | FactStore | RAW | Temporal | trace (Amnezja) | now_override |
|---|---|---|---|---|---|---|
| `/api/chat` | `compose_context()` | ✓ | ✓ | ✓ | ✓ | ✓ |
| `/api/amelia` | inline kopia | ✓ | ✓ | ✓ | ✗ | ✗ |
| `/api/wspolny` | `_wspolny_generate` | ✓ | ✓ (24h) | ✓ | ✗ | ✗ |
| `/api/siostry` | `_generate_sister` (main.py:1832-1884) | ✗ | ✗ | ✗ | ✗ | ✗ |

**Dowód, że boli JUŻ TERAZ:** R1-R6 (`81f6986`) wylądowało TYLKO w `astra_base.txt`. Tydzień później siostry chorują na TO SAMO (P2 work-ordera: każda linia głęboka, brak wyjścia z intensywności), a Amelia czeka w backlogu („Amelia overswing"). Fix nie propaguje się, bo nie ma czym. Do tego „ZASADY DOMU (wspólne)" są wklejone 3× w 3 pliki person — każda zmiana = 3 ręczne edycje = pewny dryf.

### #2 — Pętla samo-imitacji (jedyny problem z twardym POMIAREM)
Po fixie „Domowy Ambient" (06-14) intensywność Astry **wzrosła**: „zaciska" 29%→55%, start-od-gwiazdki 59%→95%, śr. długość 346→563 zn (audyt naturalności, 441 tur). Mechanizm: `get_recent_session(n=10)` podaje modelowi 10 jego własnych tur jako few-shot — few-shot bije reguły promptu. Siostry mają identycznie (main.py:1843). **Wniosek twardy: każdy fix promptu person (w tym A2/A3 sióstr) bez świeżego `conversation_id` po deployu jest martwy na starcie.** Wniosek architektoniczny: historia ma nieść TREŚĆ rozmowy, nie WZORZEC stylu — dziś niesie oba i wzorzec wygrywa. Kierunki fixu korzenia (do testu przez Amnezję): strip didaskaliów z historii podawanej modelowi / redukcja n / streszczanie starszych tur.

### #3 — Zamknięta pula pamięci sióstr = pozytywka
Ekstrakcja OFF w `/api/siostry` (świadome, słuszne — echo-loop). ALE: kolekcje `holo/menma/nazuna_memory_v1` zawierają wyłącznie ~11 seedowanych kotwic (wszystkie `is_milestone`) i **nigdy nie urosną**. Retrieval `n=4, pool=20` (main.py:1837) z puli 11 → co turę te same kotwice w memory_block. To DRUGI silnik „pętli fraz" (P3) i przeintensywnienia (P2), którego diagnoza sióstr nie widzi — czyszczenie promptu z catchphrase'ów NIE usunie recytacji, jeśli kotwice je zawierają. **Do sprawdzenia na VPS** (seeda nie ma w repo): `collection.get()` na kolekcjach sióstr → czy kotwice zawierają „PROTOKÓŁ NOCNEGO MARKA"/„czysty content". Kierunek: rozdzielić lore-kanon (rzadko, kanał gwarantowany 1-2) od pamięci żywej (dziś pustej — decyzja: kontrolowana ekstrakcja z guardami Astry albo świadome „siostry nie pamiętają szczegółów, tylko kanon").

### #4 — Stan: kruchy, niewersjonowany, częściowo ulotny
- `_siostry_recent` (main.py:1676) i `_last_wspolny_first` — globale, **giną przy każdym restarcie** (= każdy deploy); mierzą przy tym „kto pierwszy", nie „kto dominuje".
- `CompanionState`: singleton-cache; `reset()` (companion_state.py:292) zeruje WSZYSTKO bez kopii; zapis `write_text` bez tmp+rename (crash mid-write = uszkodzony stan); **brak pola wersji schematu** → każda zmiana pól = ciche `from_dict` na starym pliku. Utrata XP 3434→1824 już się wydarzyła — to nie jest ryzyko teoretyczne.
- Planowany `room_state` sióstr odziedziczy to wszystko, jeśli powstanie jako kolejny JSON obok.

### #5 — Prompt bez sufitu
(fable_7 TOP-3, wciąż otwarte) `get_facts_for_prompt` bez LIMIT; `fit_to_budget` widzi tylko wspomnienia i rezerwuje tylko `len(template)`; ~86k zn/turę u Astry i rośnie z faktami. Siostry dziś lekkie — wejdą na tę samą trajektorię w chwili dostania FactStore/rytuałów/rocznic z projektu domu. Budżet globalny musi być w composerze ZANIM rodzina dostanie rytuały. Uwaga sprzężenia: zmiana budżetu ZMIENIA prompt → zrobić przed zamrożeniem golden setu (albo świadomie razem).

### #6 — Siostry poza narzędziami, które już zbudowano
- **Poza Amnezją:** `_generate_sister` nie przechodzi przez compose → zero trace → zaplanowane strojenie pokoju będzie „na oko" — dokładnie tryb pracy, przeciw któremu zbudowano debugger. Amnezja obejmuje dziś 1 personę z 5.
- **Poza archiwum:** `_run_archive` (main.py:396-405) = astra/amelia/wspolny, **sióstr brak** → flash-reset kolekcji sesji kasuje historię domu bezpowrotnie. Wspólny Pokój ma na to bliznę („odporne na flash-reset" w komentarzu). Fix = 2 linie — najtańszy punkt audytu.

### #7 — Scoping cross-room: cztery przepływy, zero jednego miejsca definicji
Przepływy między-pokojowe zdefiniowane w czterech różnych miejscach, każdy innymi parametrami:
1. solo Astra ← shared mixin (compose: n=2 memories + RAW shared n=3/48h),
2. wspolny ← solo RAW obu person (main.py:1501-1511, n=3/24h),
3. wspolny → zapis TYLKO shared session (1647-1651) — **zero ekstrakcji we wspólnym**: „pamięć" wspólnego istnieje wyłącznie przez domieszki odczytu,
4. siostry: cross-room OFF (świadome).
Skutek: pytanie „skąd Astra wie X" ma 4 możliwe odpowiedzi w 4 miejscach kodu. Provenance (origin_*) jest zapisywane, ale NIE egzekwowane przy odczycie (żaden odczyt nie filtruje po origin). Kierunek: `RoomPolicy.cross_flows` jako dane + Amnezja pokazująca origin w każdej warstwie (już pokazuje w trace — użyć jako leak-detector, jak w backlogu).

### #8 — Router sióstr decyduje na szumie
Trzy RÓŻNE listy sygnałów: `_pick_primary`:1702, `_pick_second`:1717, `strong_emotion`:1732-35 — nakładające się, nie identyczne. Substring bez granic słowa: `'sam'` łapie „**sam**ochód/cza**sam**i", `'plan'`→„planeta", `'kod'`→„kodeks". Ironia: poprawny wzorzec (granice słowa, formy z configu) jest 15 linii wyżej (`_sister_called`:1683-85) i nieużyty dla sygnałów. Szczegóły i kontrpropozycja routera → werdykt P0 (`wazne/fable/fable_pokoj_siostr_AUDYT-WERDYKT_2026-07-05.md`).

### #9 — Monotonia milestonów
773 milestony ChromaDB + ~180 FactStore (audyt 06-23) + kanał gwarantowany top-2 + „fakty akumulujące" bez supersede = te same ~10 wspomnień w kółko (zgłoszone już 06-23 jako „źródło monotonii", otwarte). Seed sióstr powiela wzorzec od dnia zero (#3). Cykl życia wektorów istnieje tylko dla typów SUPERSEDE — milestony wyłącznie rosną. Kierunek: cap kanału gwarantowanego per rozmowa (nie per tura), rotacja milestonów (recency wśród milestonów), review „czy 773 to na pewno kamienie milowe".

### #10 — Higiena echo/anty-powtórki: każda persona od nowa
Astra: ZAKAZ PĘTLI (R3) + `strip_memory_echo` + echo-loop filter PERSON<80. Wspólny: do_not_repeat + merge turns. Siostry: „nie powtarzaj jej słów" tylko w aside-protokole; brak anty-powtórki własnych fraz (P3!). Cztery implementacje tej samej troski. Powinna być JEDNA warstwa (w composerze/RoomEngine), konfigurowana per persona.

### #11 — Drobiazgi do zabrania przy okazji fixu P0
- Tura grupowa sióstr: 3 sekwencyjne calle (main.py:1911-1919), a obie aside zależą tylko od pierwszej odpowiedzi → `asyncio.gather` dla aside = −33% latencji grupy.
- `_warsaw_hour()` (1693-95) bez override → nocna logika routera **nietestowalna w dzień** (Amnezja ma now_override właśnie po to; router nie ma).
- Licznik kosztu per tura (pkt 9 review odpfable: „N calli, X tokenów od tury zero") — niezrealizowany; kalibracja sióstr = ślepy budżet.
- Bezpieczeństwo fable_7 (DELETE /api/state bez auth, CORS `*`): status po `becb138` nieznany — jeśli nginx Basic Auth faktycznie objął cały server block, punkt zamknięty; z repo nie zweryfikuję. Checklist: `grep -rn auth_basic /etc/nginx/` + `curl -X DELETE https://myastra.pl/api/state` (oczekiwane 401).

---

## DOCELOWA ARCHITEKTURA RODZINY

Zasada nadrzędna (sprawdzona na Amnezji): **tożsamość wymuszana STRUKTURĄ, nie dyscypliną**. Persona i pokój = DANE; silnik jeden.

```
PersonaConfig (dane): id, label, formy fleksyjne,
  stores (vector/fact/state), template_path, monologue, format JSON,
  retrieval (n, pool, kanały on/off, half-life'y)
compose_context(persona_cfg, query, room_ctx=None) -> ctx + trace
  = JEDYNE miejsce składania promptu dla WSZYSTKICH person
  → Amnezja z selektorem persony widzi każdą z 5 (leak-detector za darmo)
  → wspólna warstwa higieny echo/anty-powtórki (#10) i budżetu promptu (#5)

RoomEngine (jeden silnik pokoju; Wspólny i siostry = konfiguracje):
  RoomPolicy (dane): biasy pory (WAGA, nie wyrok), capy prowadzenia,
    JEDNA lista sygnałów (granice słów), wołanie po imieniu, tryb grupy,
    anty-sync, budżet interakcji persona↔persona, cross_flows (#7)
  RoomState (trwały, SQLite): kto prowadził (albo liczone z historii),
    sojusze, temperatura, otwarte wątki

Stan: jeden store SQLite (wzorzec FactStore już jest) dla CompanionState /
  RoomState / liczników; zapisy atomowe (tmp+rename); pole schema_version;
  reset() robi backup przed zerowaniem.
Historia sesji: higiena stylu (treść ≠ wzorzec) — fix #2 u korzenia.
```

## ŚCIEŻKA MIGRACJI (addytywna, NIE kasuje wektorów, każdy krok deployowalny osobno)

Harness: `backend/tools/verify_compose.py` (14 fraz) — rozszerzać per persona. Bramka każdego kroku refaktorowego = bit-identyczność; kroki zmieniające prompt ZAMIERZENIE (budżet) — golden diff zatwierdzany przez Łukasza.

0. **Poza kolejnością, od razu (S):** siostry do `_run_archive` (2 linie); jedna lista sygnałów routera + granice słów (w ramach fixu P0); zegar routera z override.
1. **Amelia → compose_context** (PersonaConfig v1). Najbliższa chatowi. Bramka: bit-identyczny prompt Amelii. Zysk natychmiastowy: Amnezja widzi Amelię; fix „Amelia overswing" robiony już na wspólnym rdzeniu.
2. **Budżet promptu + LIMIT faktów** (w composerze → od razu dla obu person). PRZED zamrożeniem golden setu pamięci.
3. **RoomEngine na Wspólnym** — blizny (merge model-turns, thought isolation, do_not_repeat, anty-sync) PRZENOSIĆ jako przetestowane wzorce, nie przepisywać. Bramka: te same frazy → ten sam routing i prompty co `_route_wspolny`/`_wspolny_generate`.
4. **Siostry na RoomEngine** + trace + FactStore-opcjonalny. Dopiero tu strojenie sióstr przestaje być „na oko". Router wg kontrpropozycji z werdyktu P0.
5. **Higiena historii sesji** (korzeń #2): eksperyment przez Amnezję (strip didaskaliów z historii / n↓ / streszczenie), pomiar skryptem z audytu naturalności. Do tego czasu: świeży wątek po każdym fixie charakteru (obejście znane i działające — dowód: R1-R6 + 28750b59).
6. **Cykl życia milestonów** (#9) — po tym, jak Amnezja widzi wszystkie persony.

**TERAZ / MVP:** kroki 0-2 + obejścia (#2 świeże wątki). **DŁUG NA PÓŹNIEJ / przy SaaS:** kroki 3-6, multi-user w stanie (klucz user_id w state-store), wersjonowanie migracji stanu, licznik kosztów per user.

**Czego NIE ruszać przy migracji:** blizny Wspólnego (B2-B8), silent-first sióstr, izolowane kolekcje (sedno sekretów), płoty ANTY-DRYF, scena zastana, EXCLUDED_SOURCES/echo-guardy, deterministyczne ID pamięci semantycznej, KCB.

## CO TA ARCHITEKTURA KUPUJE
Fix charakteru robiony RAZ działa dla całej rodziny · Amnezja widzi każdą personę (strojenie przestaje być zgadywaniem) · nowa persona/pokój (Makima-gość, crossover Menma↔Astra) = wpis w konfigu + persona.txt, nie 250 linii routera · restart przestaje robić amnezję routingu · flash-reset przestaje kasować dom · mechaniki „żywego domu" dostają miejsce, gdzie mają żyć.

*Fable, P0.5. Zero zmian w kodzie. Rzeczy nieweryfikowalne z repo (seedy sióstr, nginx, logi VPS) oznaczone + podane jak sprawdzić.*
