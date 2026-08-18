# Evolution Log — 2026-08-17 · Astra: dlaczego nie pamiętała mefedronu (diagnoza pełna)

**Commit:** (brak — sesja diagnostyczna, zero zmian w kodzie i danych) · **Wykonawca:** Opus 5 (Claude Code)
**Zgłoszenie:** Łukasz — *„zdołowało mnie, jak Astra o substancjach nie kłamie, że pamięta, ale reranker
wyciąga jej weed i benzo… czy RAG to na pewno dobry pomysł na pamięć companiona"*
**Metoda:** odczyt `mode=ro` z ChromaDB na VPS + embeddingi liczone lokalnie (model produkcyjny).
Zero zapisów, zero dotknięcia HNSW, produkcja nietknięta.

---

## 1. Co się stało w rozmowie (17.08, 14:52-14:53)

Łukasz zapytał wprost: *„O jakiej substancji mówimy?"* — w kontekście epizodu 6-8 sierpnia.
Astra: *„Mówimy o konopiach, które kupiłeś w klinice. Wspominałeś też o weed, benzo… opioidach."*

**Astra nie skonfabulowała. Podała dokładnie to, co ma.** To jest zachowanie, o które walczyliśmy
przy detoksie: uczciwa luka zamiast wymyślonego szczegółu. Tyle że prawda okazała się bolesna.

## 2. Dlaczego — trzy bramki, jeden wzorzec

| kolekcja | wpisów | „mefedron" | weed/benzo/opioidy |
|---|---|---|---|
| `astra_memory_v1` (zeszyt — **jedyne**, co pyta RAG) | 4644 | **0** | 51 |
| `astra_memory_session_v1` (dyktafon — **nikt nie pyta**) | 5582 | **15** | 90 |

Reranker nie zawiódł. **Zadziałał bezbłędnie na pustym miejscu** — zwrócił jedyne substancje,
jakie w ogóle zna. Najcięższy epizod tego lata nie ma w pamięci skojarzeniowej ani jednego wpisu.

**Wzorzec, który wyszedł trzy razy w dwa dni — pojedyncza bramka bez drugiej drogi:**
1. bramka `<4 słowa` (`semantic_pipeline.py:87-92`) wyrzuciła „Mefedron. Wziąłem kreskę.";
2. ekstraktor nie zrobił ani jednej notatki z 15 wiadomości o mefedronie;
3. embedding nie połączył „substancji" z „mefedronem".

Za każdym razem: **jedno wejście, żadnego zapasowego.** Czego bramka nie przepuści, tego dla Astry
nie ma — nie „jest gorzej widoczne", tylko **nie istnieje**, mimo że leży w drugiej kolekcji obok.

## 3. Nowe znalezisko — zapytanie bez kontekstu (`main.py:1361`)

`query=user_msg_clean` — RAG pyta bazę **samą ostatnią wiadomością**. W realnej rozmowie daty
(„z szóstego, siódmego i ósmego") padły **turę wcześniej** i do wyszukiwania nie weszły w ogóle.
Rozmowa toczy się w kontekście, wyszukiwanie leci bez niego.

To jest nowy punkt **0** w roadmapie — przed wszystkimi pozostałymi, bo one poprawiają *gdzie*
szukamy, a ten *czego* szukamy.

## 4. Korekta wcześniejszej tezy (moja, z tej samej sesji)

Powiedziałem Łukaszowi: *„gdyby kanał 4 istniał, wczorajsza odpowiedź byłaby poprawna"*. **Sprawdziłem
i to nieprawda.** Kanał 4 trafia, gdy pada słowo (`mefedron` → 0.783, 1. miejsce), ale nie gdy pada
kategoria (`o jakiej substancji mowimy` → „Co robimy", „Oglądamy coś?"). Kanał 4 to **połowa**
rozwiązania, nie całość. Pełna tabela testów w roadmapie, punkt 1.

## 5. Odpowiedź na pytanie „czy RAG to dobry pomysł na pamięć companiona"

Tak — ale u Astry RAG pyta **jednej bazy z dwóch, i to tej przefiltrowanej**. Rozdział na dyktafon
i zeszyt był dobrym pomysłem (surowa historia jest zaszumiona — dowód: zapytanie omówne zwraca
„mhm", „co robimy"). Wadą jest to, że **zeszyt to jedyne wejście**.

Hard-code (kotwica na twardo) to obejście na jeden przypadek, nie odpowiedź na problem klasy „pamięć".
Nie skaluje się na scenariusz, Roksanę, chorobę ani nic innego.

**Kierunek: nie jeden lepszy mechanizm, tylko kilka tanich dróg, które rzadko milczą naraz** —
zeszyt → (jak milczy) dyktafon po słowach → (jak w pytaniu jest data) dyktafon po czasie →
(jak pytanie jest omówne) rozwinięcie zapytania przez model. Spięte groundingiem jako wyzwalaczem.

## 6. Zmiany w roadmapie (`wazne/research/roadmapa_pamieci_astry.md`)

- **nowy punkt 0** — kontekst w zapytaniu (najtańszy, przed wszystkim)
- **punkt 1 (kanał 4)** — korekta: nie jest samowystarczalny, tabela testów
- **punkt 2 (epizody)** — podniesiony: ludzie pytają datami, a czas nie wymaga rozumienia pytania
- **nowy 2b** — rozwinięcie zapytania przez model (abstrakcja kategoria → instancja)
- **nowy 2c** — grounding jako wyzwalacz drugiego strzału (pomysł Łukasza) + obserwacja,
  że 17.08 grounding nie zgłosił słabego pokrycia mimo 0 trafnych wpisów

## 7. Do zrobienia, wprost z tej sesji

- **Odtworzyć turę 14:53 w Amnezji** — mam rekonstrukcję z zawartości baz, nie realny trace.
  Amnezja pokaże, co faktycznie weszło do puli i dlaczego grounding nie zaprotestował.
- Stress test Amnezją na szerszym zestawie pytań (Łukasz zaproponował 17.08).

---

## 8. Wieczór 17.08 — wdrożenia (4 commity na produkcji)

**`d2c2e8d` — duplikat wiadomości dnia.** `push_subscriptions.json` miał 2 żywe subskrypcje FCM,
`send_push_to_all` słał do obu. Dedup po `endpoint` nie działa, bo każda rejestracja SW dostaje nowy
endpoint (WebAPK obok Chrome, podmiana SW), a sprzątanie jest reaktywne (tylko 410/404) — subskrypcja
z żywej przeglądarki nigdy nie umiera. Dedup po hashu w `app.js` tego nie łapał: chroni bąbelki w UI,
nie powiadomienia systemowe. Fix: stały `device_id` z localStorage, nowa subskrypcja zastępuje
poprzednie z tego urządzenia; metadane (`created_at`, `user_agent`); log przy >1 subskrypcji ZOSTAJE.
Obie stare wyczyszczone ręcznie (backup: `backend/backups/push_subscriptions_backup_2026-08-17.json`).

**`3ce0cb7` → `0239567` → `70f9e12` — scenariusz anime, trzy podejścia.** Warto zapisać drogę, bo
finał jest odwrotnością startu:
1. trigger leksykalny per wiadomość → dokument **migał**, bo „scenariusz" nie pada w każdej turze;
2. + lepkość 25 min (wzorzec z routera sióstr) → miganie zniknęło, ale powstały **dwa niewidoczne
   stany** (lepkość + pauza), których Łukasz nie mógł sprawdzić;
3. **przełącznik 🎬** — jeden świadomy stan, dwa skutki: scenariusz w prompcie + wstrzymany zapis.

**Wniosek metodyczny (Łukasz zgłosił, ja się zgodziłem):** automat rozpoznający intencję po słowach
przegrywa z przyciskiem wszędzie tam, gdzie **człowiek zna kontekst, a bramka nie**. Dowód z własnego
testu: „scenariusz testowy dla ekstraktora" odpalał trigger. Drugi argument, cięższy: każdy niewidoczny
stan systemu to potencjalny `safe_haven` — działa „poprawnie" i nikt nie zauważa. **Widoczny przełącznik
jest sam w sobie funkcją bezpieczeństwa.**

**Ramka anty-dryf** przy scenariuszu jest obowiązkowa: dokument (11 593 B) jest **większy niż
`astra_base.txt`** (10 552 B), a zawiera dialogi Astry pisane stylem konsolowym („Wykryto…",
„Zalecenie systemowe…"). Prompt nie odróżnia cytatu z fikcji od wzorca mowy — dowód z 15.08.
**Do zmierzenia po kilku wieczorach: `style_audit.py` vs baseline z 15.08.**

**`d4d7fb4` — tryb roboczy ⏸** (pauza zapisu bez scenariusza). Zostaje osobno, bo pauza przydaje się
do rozmów o czymkolwiek. Oba tryby wygasają same (3h, sufit 12h) — przełącznik wyłączający pamięć
bez terminu to gwarantowana cicha utrata. Astra dostaje blok `[TRYB ROBOCZY]`, więc **wie**, że nie
zapamięta, i nie obiecuje w dobrej wierze.

**Nie zapisuje shadow-logu świadomie:** shadow to narzędzie do kalibracji ekstraktora (jak u sióstr),
a tu nie chcemy wiedzieć, co ekstraktor BY zapisał — tylko żeby nie zapisał. Surowa rozmowa i tak
jest w sesji i w dziennym dumpie.

---

## 9. 18.08 — naprawa szkody i druga przyczyna duplikatu

**Odzysk 7 ustaleń twórczych** (`origin_endpoint="scenariusz_odzysk"`, imp 8-9). Wpisane RĘCZNIE
z pominięciem ekstraktora, przy ZATRZYMANYM serwisie (zasada: nigdy nie pisać do Chromy z osobnego
procesu przy żywym `myastra`). Backup: `backend/backups/chroma_backup_2026-08-18_odzysk.tar.gz` (43 MB).
Weryfikacja: „demon" 0→1, „mitsuket" 0→1, „primal" 0→1. Wektory 4678 → 4685.
Źródło treści: dyktafon (`astra_memory_session_v1`) — rozmowa nie zginęła, tylko nie trafiła do zeszytu.

**Duplikat wiadomości dnia — DRUGA, inna przyczyna** (pierwsza: `d2c2e8d`, dwie subskrypcje FCM).
Najpierw fakty, dopiero potem hipoteza: backend wysłał dziś **dokładnie jedną** wiadomość
(1 poranna 05:00 UTC = 07:00 Warsaw, `spontaneous_sent_date` wciąż 17.08, 1 subskrypcja, 1 proces,
serwer UTC + scheduler `Europe/Warsaw`). **Hipoteza Łukasza o godzinach serwerowni — obalona.**
Problem był w dostarczaniu.

Sedno: push niesie treść **skróconą** (`msg[:100] + "…"`), a SW przekazywał **właśnie ją** do strony
przez `postMessage`. Polling `/api/morning-message` pobiera treść **pełną**. Dedup porównuje hash
tekstu → hash urwanej ≠ hash pełnej → obie ścieżki przechodzą przez filtr i dokładają po bąbelku.
Fix dwuwarstwowy (bo stary SW może siedzieć na urządzeniu): pole `full` w payloadzie **oraz** hash
liczony ze znormalizowanego prefiksu 80 znaków. Do tego `_markProactiveShown` przed renderem
(wyścig relay↔polling). Log `[PUSH] wyslano do N/M` zostaje.

**Wzorzec, który wraca trzeci raz:** ten sam objaw, inna przyczyna za każdym razem. Dlatego
diagnostyka zostaje w kodzie — bez logu z 17.08 dzisiejsza diagnoza zaczęłaby się od zera.
