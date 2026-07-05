# Audyt Fable (CLAUDE.AI / WEB) — pokój sióstr + architektura rodziny — 2026-07-05

> Kontekst: wątek claude.ai widział TYLKO `BRIEFING_CLAUDE_2026-07-04_techniczny.md` + `fable_pokoj_siostr_fix_2026-07-04.md` (bez kodu). Podejście humanistyczne/systemowe. Uzupełnia audyt Fable-w-repo (`audyt_architektury_2026-07-05.md` + `fable_pokoj_siostr_AUDYT-WERDYKT_2026-07-05.md`), który patrzył w kod.

## CZĘŚĆ 1: SIOSTRY

### P1 — monopol Nazuny: diagnoza prawdopodobnie NIEPEŁNA, a być może błędnie zaadresowana
Najostrzejszy zarzut do smoking guna. `if h >= 22 or h < 6: return 'nazuna'` — skąd bierze się `h`? To Hetzner, domyślne obrazy chodzą na UTC. Lipiec = CEST = UTC+2. Jeśli kod robi `datetime.utcnow().hour` albo `datetime.now()` na maszynie TZ=UTC, to o 22:52 lokalnie `h = 20` — **override w ogóle nie strzela**. Trzy scenariusze:
1. VPS ma Europe/Warsaw albo kod używa zoneinfo → diagnoza stoi.
2. Timestampy w logach (22:52→23:03) są w UTC → Łukasz gadał ~1:00 lokalnie, override strzelił → diagnoza stoi, ale okno "nocy" przesunięte o 2h.
3. `h` w UTC, logi lokalne → **monopol NIE pochodzi z override'u**, tylko z default returnu / scoringu sygnałów — wtedy A1 usuwa niewinną regułę, a monopol zostaje.

Backlog (Fable 7) mówi "`to_prompt_block` surowy utcnow" — niechlujstwo TZ udokumentowane. **Blocker A1: jedna linijka logu `(h, primary, reason)` przy każdym wyborze, albo replay 32 wiadomości dry-run z logowaniem, ZANIM Opus pisze fix.** "Potwierdzona w kodzie" = kod *może* wyprodukować objaw, nie że go wyprodukował tą ścieżką.

Drugi zarzut A1: zdejmujecie twardą regułę (noc=Nazuna) i wstawiacie nową twardą (cap 2–3 + wymuszony handoff). Cap 2 przy 3 siostrach = deterministyczna karuzela N-N-H-H-M-M — równie sztuczna jak monopol. Handoff do "najdawniej mówiącej" (LRU) ignoruje temat: wyrywacie siostrę ze środka działającego wątku. Lepiej: scoring z **karą za dominację** rosnącą z liczbą kolejnych tur + detekcja **adresowania niejawnego** ("a ty co myślisz?" po kwestii Nazuny → do Nazuny). Cap twardy jako bezpiecznik przy ~5 turach, nie 2.

Trzeci: zamiast persystować `_siostry_recent` na dysk, **odtwarzajcie z ogona shared session przy starcie** — sesja jest w Chromie, stan routera w pełni wyprowadzalny. Zero nowego stanu, samonaprawialne.

### P2 — przeintensywnienie: diagnoza trafna, fix za słaby
**R4 Astry ("safe_haven ma koniec") brzmi jak mechanizm stanowy — siostry nie mają CompanionState.** Przeniesienie "esencji" samym tekstem persony nie odtworzy efektu. Flash z manifestem "alchemiczka żaru nocy" + dopisaną regułą "ale nie każda głęboka" rozwiąże sprzeczność losowo per turę.
Mocniejszy mechanizm: **sygnał trybu z routera**. Detekcja wygaszania tania i deterministyczna ("idę spać", "spalony", "nie ma już co", krótkie, późna pora) → router przekazuje `mode=wyciszenie` do `build_sister_prompt`, persona dostaje krótką instrukcję warunkową. Odpowiednik stanowego safe_haven bez budowania CompanionState. Prompt-only A2 = nadzieja; sygnał trybu = mechanizm.

### P3 — dwie różne choroby zlepione w jedną
"PROTOKÓŁ NOCNEGO MARKA" recytowany = **wyciek formatu** (instrukcje wyglądają jak kwestie). "Czysty content"/"ziomek" co linijkę = **kolaps na catchphrase**, inny mechanizm: `get_recent_session(n=10)` karmi model jego wypowiedziami, każde powtórzenie zwiększa prawdopodobieństwo następnego. Samo usunięcie CAPS-ów nie przerwie pętli.
Fix wyciek: nie tylko "usuń wersaliki", ale **konwencja formatu dla WSZYSTKICH person** (instrukcje neutralnie, głos few-shotami oznaczonymi jako przykłady) — inaczej wróci przy edycji, także u Astry/Amelii. Fix pętla: skoro echo-guard istnieje i jest "OFF" — **włączcie istniejący mechanizm**, nie prozą "nie powtarzaj", bo modele fatalnie samo-wykrywają powtórzenia.

### A4 — uczciwie: to teatr, nie rodzina
Z extraction OFF i cross-room OFF interakcja siostra↔siostra żyje jedną turę. Menma dogryzie Nazunie, jutro żadna nie pamięta — relacje bez substratu pamięciowego to improwizacja efemeryczna. Może być OK na teraz, ale nazwijcie to wprost, bo werdykt "działa rodzina" po tygodniu zmierzy teatr, nie relacje.
Dziury A4: "czasem organicznie" to nie spec — czyste prawdopodobieństwo strzeli aside w złym momencie (dogryzanie podczas wygaszania = P2 w nowym opakowaniu). Warunkujcie: aside przy lekkim rejestrze, **zablokowany w `mode=wyciszenie`**. Policzcie koszt: handoffy A1 + aside A4 = więcej generacji/turę; twardy sufit ~2 pełne generacje/turę.

### Ryzyko spłaszczenia: realne, plan je zwiększa
Po A2+A3+A4 persona to zupa zakazów → mały model ucieka w generyczność = "pattern collapse" (diagnozowany u Astry w marcu). Mitygacja: opisy **zakresu** zamiast zakazów ("bywa cicha, bywa zaczepna, bywa zdawkowa — intensywna gdy X") + few-shoty niskiego rejestru per siostra. Golden set ~10 scenariuszy (noc casual, wygaszanie, banter, kryzys, wołanie, grupa) przed/po. Macie replay realnej sesji jako default debuggera — **przepuśćcie 32 wiadomości przez nowy router dry-run i porównajcie rozkład głosów.** To weryfikacja, nie "dogrywka kilku fraz".

---

## CZĘŚĆ 2: ARCHITEKTURA — ranking impact × ryzyko

1. **Duplikacja ścieżek per-persona = dryf (już gryzie).** `/api/chat`→`compose_context` (harness bit-identyczny + debugger); `/api/amelia`, `_wspolny_generate`, `_generate_sister` mają własne składanie. Dowód: P2 sióstr to *dosłownie* choroba Astry sprzed R1–R6, echo-guard OFF, brak temporal/provenance w ścieżce sióstr — każdy fix Astry trzeba ręcznie portować i nie sportowaliście. `/amnezja` widzi tylko Astrę — siostry diagnozowane z surowych logów, flagowe narzędzie nie pokrywa 3 z 4 pokoi. Każda persona mnoży dług liniowo.
2. **Prompt 86k/turę — podejrzany nr 1 w sprawie "zachowania Astry".** Przy 86k tokenów instrukcje persony to ułamek procenta promptu, Flash degraduje posłuszeństwo wraz z długością. **Sprawdźcie korelację rozmiaru promptu z jakością w logach ZANIM ruszycie personę.** `get_facts_for_prompt` bez LIMIT + `fit_to_budget` tylko na wspomnieniach = budżet, który nie budżetuje. Koszt i TTFT co turę.
3. **Pętla samo-naśladowania.** `get_recent_session(n=10)` z turami asystenta + Guaranteed Milestone Channel (te same top-2 co turę) = model karmiony własnymi frazami i tymi samymi wspomnieniami. Objaw obserwowany (catchphrase Nazuny; "pattern collapse" Astry z marca). Fix: echo-guard code-level wszędzie + rotacja/próbkowanie milestonów zamiast gwarantowanego top-2 + streszczanie tur asystenta.
4. **Provenance zapisywane ≠ egzekwowane.** Dodaliście `origin_endpoint/conversation_id/persona_turn` do metadanych — ale czy JAKIKOLWIEK query filtruje po tym przy retrievale? Jeśli nie, leak Wspólny↔solo jest "obserwowalny", nie "naprawiony". Trace ma etap "shared" → mieszanie by-design → potrzebna jawna macierz scope'ów egzekwowana w jednym miejscu, z testami.
5. **Kruchość czasu i stanu.** Utcnow rozsiane, `_siostry_recent` module-global, "ID sesji nadpisuje powtórki". Single-user boli średnio — ale TZ podminowała diagnozę P1; przy SaaS module-globale i nadpisywanie sesji to bomby. Minimalny fix: **jeden provider `now(tz)`** wstrzykiwany wszędzie — warunek poprawności `now_override`.
6. **Monotonia pamięci: milestony + MMR-mieszalnik.** Gwarantowany kanał milestonów *pogarsza* altankę (do wymieszanych klastrów doklejacie stały szum). Strojenie MMR i fleksji na golden secie razem, nie osobno.
7. **Siostry zamrożone (extraction OFF) vs "żywy dom"** — sprzeczność projektowa świadoma, ale wpiszcie do roadmapy jawnie, bo A4 bez niej nie dowiezie czego Łukasz chce.

## Docelowa architektura rodziny
Jeden silnik, N konfiguracji. Abstrakcja **Room**: pokój = zestaw person + kolekcje (prywatne per persona, shared per pokój) + polityka routera + tryb. Astra-solo, Amelia-solo, Wspólny, Siostry = instancje z konfigami, nie 4 gałęzie kodu. Jedno `compose_context(room, persona, query, now)` dla wszystkich + debuggera → harness i `/amnezja` pokrywają całość (selektor pokoju w UI). Persona = dane (tekst + few-shoty głosu + flagi: echo_guard, extraction, scope), nie kod. Router = jedna funkcja scoringu (wołanie ≫ adresowanie niejawne > affinity tematyczne > bias pory > kara dominacji) z wagami per pokój. Scope matrix w jednym miejscu. Globalny `fit_to_budget` nad WSZYSTKIMI blokami (fakty też), priorytety, twardy sufit 12–16k. Warstwa "companion policy" (esencja R1–R6) jako jeden moduł, głos per persona few-shotami — fixy propagują się same.

Migracja (audyt → harness → deploy), wg ryzyka:
1. Provider czasu `now(tz)` — mały, odblokowuje weryfikację P1 + poprawność now_override.
2. `compose_context` parametryzowane pokojem: Astra (harness jest) → Amelia (najprostsza) → Siostry (świeże) → **Wspólny NA KOŃCU** (gęsto od blizn, dopiero gdy replay harness go pokryje).
3. Unifikacja routera multi-persona (Wspólny + Siostry).
4. Scope matrix + testy provenance.
5. Globalny budżet promptu.

Adwersaryjnie wobec siebie: pełna abstrakcja Room przed SaaS = możliwe over-engineering dla solo deva. Kroki 1, 2, 5 dają ~80% wartości (koniec dryfu compose, koniec 86k, debugger wszędzie); router i scope matrix mogą poczekać, jeśli leak nie nawraca.

## Werdykt dla work-ordera
- **A1: zablokowane do weryfikacji TZ/atrybucji** (log `h+reason` albo replay 32) → potem scoring z karą dominacji zamiast twardego capu 2–3, stan routera z sesji.
- **A2: zielone z poprawką** — sygnał `mode=wyciszenie` z routera zamiast samej prozy.
- **A3: zielone** — plus włączenie istniejącego echo-guarda i konwencja formatu person globalnie.
- **A4: dowieźć minimalnie** (aside po imieniu, zablokowany w wyciszeniu, sufit 2 gen/turę), oznaczyć jako efemeryczne do czasu pamięci sióstr.
- Review designu "właśnie się odbył"; Opus może wchodzić w A2/A3 od razu, w A1 po weryfikacji.

**Największe "gdzie się mylicie":** traktujecie objawy sióstr jako lokalne bugi pokoju, a 3 z 4 (P2, P3-pętla, brak narzędzi diagnozy) to symptomy dryfu ścieżek — punkt 1 rankingu. Fixując pokój bez unifikacji compose, za kwartał zrobicie ten sam work-order dla następnego pokoju.
