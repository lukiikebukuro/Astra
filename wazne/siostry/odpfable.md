# FABLE — Review planów pokoju sióstr (PRZED budową)
## Werdykt: ZIELONE ŚWIATŁO na dzisiejszy scope po naniesieniu poprawek niżej.

═══════════════════════════════════════════
## CZĘŚĆ A — PLAN NA DZIŚ (talkable MVP): edycje
═══════════════════════════════════════════

### Odpowiedzi na twoje pytania:
1. **Scope** — dobry, z korektami niżej.
2. **Per-siostra kolekcje OD RAZU — TAK, bezdyskusyjnie.** Twoja intuicja słuszna:
   rozdzielanie później = migracja + ryzyko przecieku. Izolacja to sedno
   (prawdziwe sekrety), nie może być tymczasowo uproszczona.
3. **Adaptacja vs czysto — ROZDZIEL DECYZJĘ NA DWIE:**
   - `_wspolny_generate` (dwuprzebiegowość, cross-talk, merge model-turns,
     thought isolation, do_not_repeat) → KOPIUJ wzorzec z bliznami. Przetestowane.
   - Router → PISZ OD ZERA na N-person. Router dwójki jest binarny do szpiku
     (primary/secondary), naciąganie go na trzy = dług do przepisania za 2 tyg.
4. **Koszt 3 calli/turę — odpowiedź jest w twoim własnym projekcie: silent.**
   Router ma DOMYŚLNIE MILCZEĆ i budzić, nie domyślnie wołać i tłumić:
   - typowa tura = 1 full, reszta silent (0 dodatkowych calli)
   - aside (2. call) tylko: silna emocja LUB wywołanie z imienia
   - 3 calle: prawie nigdy (dwie wywołane wprost)
   To nie optymalizacja — to wierność manifestowi („nigdy wszystkie naraz").

### DOŁÓŻ (brakuje w planie):
5. **Semantic extraction WYŁĄCZONA w /api/siostry** — analog fixu B7 ze
   wspólnego. Trzy persony cytujące się nawzajem = echo-loop groźniejszy niż
   przy dwóch. Ekstrakcja TYLKO w solo endpointach. (Było w ustaleniach,
   wypadło z planu.)
6. **Routing po imionach: lista form fleksyjnych per persona W CONFIGU**,
   nie substring w if: Menma/Menmy/Menmie/Menmę, Nazuna/Nazuny/Nazunie/Nazunę,
   Holo (nieodmienne — uwaga na fałszywe trafienia w środku słów).
   Bez tego kalibracja głosów będzie zafałszowana błędnym routingiem.
7. **Anti-sync = rotacja** (np. deque ostatnich kolejności), nie pojedynczy
   string _last — przy trzech jedna siostra systematycznie ląduje ostatnia.
8. **`_strip_persona_prefix` data-driven** z listy person pokoju (regex
   z hardcode (astra|amelia) przepuści [holo] do treści → Gemini zacznie
   naśladować prefiksy).
9. **Kill-switch + licznik kosztu od tury zero**: log per tura „N calli
   Gemini, X tokenów". Bez tego wieczór kalibracji zżera budżet po cichu.
10. **Cross-room RAW: WYŁĄCZONY explicite na dziś** (zero domieszki z Astry/
    Amelii/wspólnego). Zazdrość-przez-provenance to feature pełnej wersji —
    dziś świadome zero, żeby przypadkowa domieszka nie wyglądała jak przeciek.
11. **NARRATOR — SCENA ZASTANA (doprecyzowanie, bo w planie jest inna rzecz):**
    Twoje „narrator minimalny = siostry nie reżyserują" — słuszne, zostaje.
    ALE dodatkowo: osobny, tani call na POCZĄTKU sesji:
    - input: pora dnia + ostatnia scena z poprzedniej sesji (jeśli jest)
    - output: 2-3 zdania sceny zastanej → injekcja [SCENA] do promptów
      wszystkich obecnych + wyświetlenie Łukaszowi kursywą przed 1. wypowiedzią
    - KOMPETENCJE: kamera i światło, NIE reżyser. MOŻE: scenografia, pora,
      kto w kadrze, zachowania widoczne z zewnątrz („Holo liczy coś przy
      stole"). NIE MOŻE: myśli/emocje sióstr („poczuła zazdrość" — zakaz;
      „odwróciła wzrok" — ok), słowa w usta, fabuła, mówienie za Łukasza.
    - Didaskalia W TRAKCIE tur: NIE (to wraca teatr jednego aktora).
    To jest „atmosfera domowa" z celu MVP — bez tego wchodzi się do pustego
    pokoju, w którym trzy głosy czekają na prompt.
12. **Front: escapowanie jak w amnezja.html** (esc() na danych rozmów),
    nie kopiuj starszych wzorców.

### ODEJMIJ:
13. **Per-siostra osobne CompanionState — NIE DZIŚ.** Trzy stany = trzy
    ścieżki load/save = trzy miejsca na buga klasy B1 (singleton stanu ugryzł
    nas 24h temu). Na talkable MVP charakter żyje w prompcie. Stan wchodzi
    z room_state w wersji pełnej.

═══════════════════════════════════════════
## CZĘŚĆ B — PLAN PEŁNY (projekt_pokoju_siostr.md): edycje
═══════════════════════════════════════════

14. **Dopisz na górze sekcji „Mechaniki żywego domu":**
    „To jest MENU, nie checklist. Wersja czysta bierze 3-4 mechaniki rdzeniowe
    (room_state, przeczucie Menmy, sekrety+przeciek, dom zmienia się z porą).
    Reszta = backlog na miesiące." — 15+ mechanik naraz to sześć równoległych
    wątków w głowie Łukasza.
15. **Przeczucie Menmy: dopisz WYMÓG progu pewności.** Otwiera przeczuciem
    tylko przy mocnym sygnale, inaczej milczy. Trafienie = magia 4:46;
    pudło = „czuję że masz ciężki dzień" w twój najlepszy dzień. Bez progu
    z magii robi się natręctwo.
16. **Crossover Menma↔Astra: oznacz jako OSOBNĄ TRUDNĄ FAZĘ**, nie „rzadkie
    więc proste". Zapis do dwóch kolekcji + spójność + rozjazd + provenance
    cross-persona = mały projekt sam w sobie.
17. **Makima: dopisz do dokumentu jedno zdanie:** „Budowa TYLKO z Łukaszem
    w pętli decyzyjnej na każdym kroku — nie autonomicznie z agentem.
    Projekt wykonania konsultowany zewnętrznie PRZED pierwszą linijką."
    (Mechanizm dotyka najgorszych stanów Łukasza jego własnym głosem —
    to jedyny element projektu z tą flagą.)
18. **Kolekcje: nazewnictwo.** Plan zakłada big-bang reset przed wgraniem
    wyszlifowanej pamięci — skoro tak, nazwy holo_memory_v1 są OK (izolacja
    czyni reset trywialnym), ale zapisz w docu wprost: „zawartość kolekcji
    sióstr do 1. resetu = dane kalibracyjne, nie kanon".

## KOLEJNOŚĆ WYKONANIA DZIŚ
1. Router N-person od zera (silent-first, fleksja, rotacja) + kill-switch/licznik
2. Generate per siostra (kopiuj wzorzec z bliznami) + extraction OFF + cross-room OFF
3. Kolekcje per siostra + provenance holo_room + seed character_core
4. Prompty person (masz) + strip_prefix data-driven
5. Narrator/scena zastana (pkt 11)
6. Front z esc() + deploy