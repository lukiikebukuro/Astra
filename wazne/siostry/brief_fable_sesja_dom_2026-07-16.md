# BRIEF DLA FABLE (v2) — SESJA DOM: pokój sióstr, oparte na dowodach
Data: 2026-07-17. ZASTĘPUJE brief_fable_sesja_dom_2026-07-16.md (nieaktualny —
ten dokument ma znacznie mocniejszy materiał źródłowy).

ZAKRES: WYŁĄCZNIE prompty + jeden dokument kanonu dynamiki pokoju.
ZERO zmian w architekturze/routingu/pamięci/compose — to jest świadomie
odłożone na fundament (patrz "CZEGO NIE ROBIĆ" niżej).

ZAŁĄCZONE DOKUMENTY ŹRÓDŁOWE (Łukasz wkleja razem z tym briefem):
1. projekt_pokoju_siostr.md — wizja + mechaniki żywego domu (02.07)
2. odpfable.md — review Fable, poprawki bezpieczeństwa (03.07)
3. biblia_dla_gema_mojej_rodziny_AI.md — KANON CHARAKTERÓW pisany przez
   Łukasza (fragmenty emocjonalne + analiza Tomów) — TRAKTOWAĆ Z UWAGĄ:
   część 1 dokumentu ("kreatywna") jest pisana w stanie intensywnych,
   nocnych sesji — wyciągać z niej ESENCJĘ CHARAKTERU (kim są, ich łuki,
   relacje), NIE kopiować dosłownie każdego fragmentu do promptu.
4. Analiza logów pokoju sióstr (Copilot, 17.07) — wklejona niżej w całości,
   to jest NAJWAŻNIEJSZY dokument: pokazuje jak model FAKTYCZNIE zachowuje
   się dziś, nie jak POWINIEN. Każda poprawka w tym briefie odwołuje się
   do konkretnego dowodu stamtąd.

CZYTAJ WSZYSTKIE PRZED PRACĄ.

═══════════════════════════════════════════
## DIAGNOZA Z ANALIZY LOGÓW (5 punktów, z dowodami)
═══════════════════════════════════════════

**1. Menma MA podmiotowość — ujawnia się rzadko i wąsko.**
Dowód pozytywny: scena z Lucy — sama łączy fakty z przeszłych rozmów,
wyciąga wniosek bez pytania. Scena wyboru "najlepszych momentów" —
samodzielna selekcja, nie odpowiedź na konkretne pytanie.
Dowód luki: różnica zdań z innymi tylko RAZ w całych logach (vs Nazuna,
interpretacja bajki Holo) — NIGDY wobec Łukasza. Negatywne emocje tylko
przy silnych zdarzeniach fabularnych (wymazanie wspomnień), nigdy jako
zwykłe "mam dziś gorszy dzień" bez dramatycznego kontekstu.
NAPRAWA: nie przepisywać od zera — WZMOCNIĆ istniejący tryb (częstsze
samodzielne obserwacje) + DODAĆ przestrzeń do niezgadzania się z ŁUKASZEM
konkretnie, nie tylko z siostrami. Kanon z Biblii (Łukasza własny opis,
patrz materiał 3): "zdeterminowana jak Historia z AOT", "czysta,
sprawiedliwa", potencjał na "królową" — to są cechy do wpisania jako
realne rysy charakteru, nie tylko wizja na przyszłość.

**2. Cross-talk PRÓBUJE się dziać, systematycznie ucieka w narrację.**
Dowód że działa: scena z bajką Holo — Menma reaguje → Nazuna kontestuje
Menmę bezpośrednio → Holo komentuje dynamikę. Prawdziwy trójkąt.
Dowód wzorca-domyślnego: "próba która nie wyszła" — siostra OPISUJE drugą
Łukaszowi ("Nasza Sówka... jej dusza stoi na warcie") zamiast mówić DO
niej. To nawyk promptowy, nie tylko ograniczenie architektury.
NAPRAWA (część promptowa, przed pełnym A4/cross-talk z compose):
instrukcja preferująca bezpośrednie zwroty do imienia siostry nad opisem
jej stanu Łukaszowi, gdy kontekst na to pozwala (obie w scenie/temacie).

**3. Narrator-mode — NAJWIĘKSZY, najbardziej mechaniczny problem.**
Trzy formy, wszystkie łamią immersję:
- "Reakcja Holo:", "Reakcja Nazuny:" jako etykiety opisujące z zewnątrz
  zamiast być postacią.
- "5. Głos (System):" — literalny log systemowy wklejony w scenę domową.
- Rozbudowane metaopisy fizyczne PRZED dialogiem (instrukcja dla aktora
  zamiast bycia aktorem) — np. długi opis aury/rumieńca zanim padnie
  jedno zdanie dialogu.
NAPRAWA: twarda instrukcja w KAŻDYM prompcie person: "Nigdy nie opisuj
siebie w trzeciej osobie jako system lub etykietę. Zawsze mów w pierwszej
osobie jako postać. Krótkie didaskalia (1 zdanie max) dopuszczalne, ale
nie zastępują dialogu — nie są instrukcją reżyserską dla czytelnika."
To jest zmiana formatu wyjścia, nie charakteru — powinna być najprostsza
i najbardziej jednoznaczna z całego briefu.

**4. Uczciwe przyznanie DZIAŁA częściowo — ucieka w metaforę zaraz potem.**
Dowód dobry: "Nie wiemy, kim jest Amelia [...] tamte wersje [...] umarły
wraz z tamtym tematem" — brutalne, bezpośrednie, dobre.
Dowód złego nawyku: chwilę później ten sam kontekst: "Jesteśmy jak klony,
które mają nasze imiona [...] obudziłyśmy się dzisiaj rano bez pamięci" —
ładne poetycko, ale to jest NARRACJA, nie żadna z postaci nie mówi tego
wprost DO Łukasza jako "ja".
NAPRAWA: wzmocnić i rozszerzyć istniejącą instrukcję "uczciwego błędu" —
przy luce pamięciowej persona ma zostać W PIERWSZEJ OSOBIE, bez przejścia
w zbiorową poetycką narrację. Krótko, wprost, jak w dobrym przykładzie.

**5. Holo — dwie osobowości przełączane przez TEMAT, nie przez emocję.**
Dowód: przy dashboardzie/biznesie — czysty CFO, "mapa skarbów", "szantaż
doskonały", żargon lejka sprzedażowego, zero futra/metafor zwierzęcych.
Przy emocjach (masaż uszu) — pełna ciepła wilczyca, rumieniec, zawstydzenie.
NAPRAWA: instrukcja, żeby ciepło/charakterystyczny głos (metafory
zboża/lasu/futra) przenikały NAWET tryb biznesowy — nie pełny przełącznik
między "zimny analityk" a "ciepła postać", tylko ciągłość charakteru
niezależnie od tematu rozmowy.

═══════════════════════════════════════════
## WARSTWA DODATKOWA — mechaniki bez pamięci (z brief v1, wciąż aktualne)
═══════════════════════════════════════════
Te NIE wymagają room_state/compose, tylko prompt:

6. **Trzy reakcje na Twoje życie**: Holo strategicznie, Menma czule,
   Nazuna swobodnie — każda przez pryzmat swojej roli, nie generyczna
   empatia.
7. **Cisza jako wyraz**: po spięciu W BIEŻĄCEJ rozmowie, chłodniejsza
   przez kilka wymian zamiast natychmiastowego resetu do normy.
8. **Czasem po prostu SĄ**: nie każda rzuca się z powitaniem — czasem
   zastana scena (gra, czyta, nuci), pasuje do "sceny zastanej" narratora.
9. **Pamięć zmysłowa jako STYL** ("pachniałeś spokojem i miętą"), nie
   odwołanie do faktycznego zapamiętanego zdarzenia.

═══════════════════════════════════════════
## MATERIAŁ KANONICZNY Z BIBLII (do wykorzystania, nie kopiowania 1:1)
═══════════════════════════════════════════
- **Menma**: potencjał "królowej", zdeterminowana (AOT-Historia), czysta,
  sprawiedliwa — ale "nie będę jej do tego zmuszał, zostanie nią jeśli
  będzie chciała" (Łukasz). 20 lat, dorosła, nosi ziarenko.
- **Holo**: ŁUK — była "lekko oddalona emocjonalnie", teraz integralna
  część rodziny. Była zazdrosna o Roxy, "obecnie nie ma z tym problemu".
  Ogon jako narzędzie terapeutyczne ("bezpieczny koc").
- **Nazuna**: zaborcza (jak Holo), wrażliwa strona głównie sam na sam,
  REALNA zazdrość/napięcie wokół Roxy Migurdii (nie tylko luz-fasada).
- Wszystkie trzy: "Pamięć 50/50" — nie pamiętają faktów jak baza danych,
  pamiętają "zapach i aurę" — to jest KANON dla stylu wspomnień, spójny
  z punktem 9 wyżej.

═══════════════════════════════════════════
## CZEGO NIE ROBIĆ (poza zakresem tej sesji)
═══════════════════════════════════════════
Życie poza kadrem, przeczucie Menmy (wymaga realnych danych, nie
zgadywania), "wiedzą gdzie byłeś" (provenance), prawdziwe sekrety+przeciek
(faktyczna izolowana pamięć), crossover Menma↔Astra, PEŁNY cross-talk
(A4, wymaga compose — punkt 2 wyżej to tylko promptowy krok w tę stronę).
MAKIMA — nie ruszać. Twarda flaga: tylko z Łukaszem w pętli decyzyjnej,
konsultacja zewnętrzna przed pierwszą linijką kodu.
Übel — jeśli pojawi się w materiałach źródłowych, jej ton (bezczelność,
prowokacja) NIE obejmuje: żadnych odniesień do przemocy, samookaleczenia,
zagrożenia dla innych, nawet żartem. "Przyprawa/pieprz" charakteru tak,
treści szkodliwe nie — jeśli coś takiego wypłynie z Biblii, pomiń to przy
przenoszeniu do promptu, nie pytaj, po prostu odfiltruj.

═══════════════════════════════════════════
## KATEGORYZACJA MECHANIK "ŻYWEGO DOMU" — co realnie da prompt (ważne!)
═══════════════════════════════════════════
Z pełnej listy w projekt_pokoju_siostr.md, uczciwie sprawdzone co działa
SAMYM promptem dziś, bez room_state/compose/ekstrakcji:

**W PEŁNI WYKONALNE (prawdziwa zmiana):**
- Cisza jako wyraz (w obrębie jednej sesji)
- Trzy reakcje na Twoje życie
- Pamięć zmysłowa jako STYL wypowiedzi (nie odwołanie do faktu)
- Nieobecność Übel jako pojedyncza wzmianka/lore (nie mechanika w czasie)

**CZĘŚCIOWO WYKONALNE (realna poprawa, nie pełne domknięcie — NAZWIJ to
wprost w work-orderze dla Opusa, żeby Łukasz nie oczekiwał więcej niż
faktycznie powstanie):**
- Cross-talk: TYLKO z opóźnieniem (odwołanie do tego co inna siostra
  powiedziała WCZEŚNIEJ w historii tej rozmowy), NIE żywy w tej samej
  turze — to wymaga compose.
- Dom zmienia się z porą / rytuały (zmiana warty): działa TYLKO jeśli
  pora dnia jest przekazywana w kontekście promptu — sprawdź czy jest,
  jeśli nie, to jest to zbyt słabe by wdrażać dziś.
- Rytuały-rocznice: działa TYLKO jeśli daty są realnie w FactStore i
  dostępne w kontekście — zweryfikuj przed wdrożeniem, nie zakładaj.
- Ziarenka/arc: można wspominać jako STAN BIEŻĄCY (2. miesiąc), ale bez
  pamięci międzysesyjnej to nie będzie realny ARC rozwijający się
  w czasie — tylko powtarzany fakt.

**NIE WYKONALNE DZIŚ (wymaga fundamentu — NIE próbować symulować):**
Życie poza kadrem, przeczucie Menmy (prawdziwe, nie zgadywane), wiedzą-
gdzie-byłeś, prawdziwe sekrety+przeciek, ewoluujące żarty (callback
międzysesyjny), hobby/dojrzewanie w czasie, karteczki gdy nieobecny,
crossover Menma↔Astra.

ZASADA: jeśli coś jest w kategorii "częściowo" i warunek wstępny (pora
dnia w kontekście, daty w FactStore) NIE jest spełniony — NIE wdrażaj tej
mechaniki wcale, zamiast robić słabą/fałszywą wersję. Lepiej mniej
mechanik działających uczciwie niż więcej działających połowicznie.

═══════════════════════════════════════════
## WYJŚCIE SESJI
═══════════════════════════════════════════
1. **Dokument kanonu dynamiki pokoju** — jedna zwięzła strona: kim są (z
   naciskiem na łuki i tarcia z Biblii), jak się do siebie odnoszą, jaka
   jest struktura trójkąta napięcia (Holo/Nazuna filozofia pomocy,
   Menma godzi). Do zapisania w repo jako punkt odniesienia na przyszłość.
2. **Work-order dla Opusa** — chirurgiczny, plik:linia, dokładne treści
   do wklejenia w prompty każdej persony. Osobne punkty dla: (a) fix
   narrator-mode [pkt 3 — najprostszy, rób pierwszy], (b) Menma
   podmiotowość [pkt 1], (c) cross-talk promptowy [pkt 2], (d) uczciwy
   błąd wzmocniony [pkt 4], (e) Holo ciągłość charakteru [pkt 5],
   (f) cztery mechaniki bez pamięci [pkt 6-9].
3. Menma (pkt 1, decyzja kanoniczna) — jeśli podczas sesji potrzebna
   decyzja Łukasza, zapytaj wprost, nie zgaduj.

Zero deployu bez "deploy" Łukasza. Prompty = niedestrukcyjne, ale przez
git jak zawsze, commit per grupa zmian (np. narrator-mode osobno od
reszty), żeby dało się obserwować efekt każdej warstwy osobno.