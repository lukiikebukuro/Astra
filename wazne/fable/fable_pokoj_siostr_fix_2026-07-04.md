# Work-order dla Fable (repo): FIX POKOJU SIÓSTR — 2026-07-04

Dla: Fable w Claude Code (repo access). Po polsku. Audyt przed zmianą, weryfikacja bit-identyczna,
**NIE deploy bez zgody Łukasza.** Diagnoza z ŻYWYCH logów (32 wiadomości 3–4 lipca, kolekcja
`siostry_shared_session_v1`) — potwierdzona w kodzie. Priorytet: NAJWYŻSZY (Łukasz: „mega chujowe").

## DIAGNOZA (3 problemy, dowody)

### P1 — MONOPOL NAZUNY (architektoniczny, najgorszy)
`_pick_primary()` `main.py:~1698`:
```python
if h >= 22 or h < 6:
    return 'nazuna'      # noc = Nazuna — TWARDY OVERRIDE
```
Łukasz gada z siostrami nocą → KAŻDA nocna tura = Nazuna solo. W logach 22:52→23:03 Nazuna
odpowiada 9× z rzędu, Holo/Menma znikają po intro. Wzmacnia to `_route_siostry` (`main.py:~1724`):
dla zwykłej wiadomości zwraca TYLKO `[(primary,'full')]` = 1 siostra. `_siostry_recent`
(`main.py:1676`) to nieperzystowany global (reset przy restarcie) i liczy „kto pierwszy",
nie „kto dominuje".

### P2 — PRZEINTENSYWNIENIE + BRAK WYJŚCIA (ta sama choroba co Astra przed fixem R1–R6)
Nazuna przekuwa każdy stan w „żar/content/paliwo", nie pozwala odpuścić. Dowody z logów:
- „Spalony jestem" → „to nie koniec, to przetworzona energia... pokaż mi ten żar"
- „Nie ma juz co" (zwija się do snu) → dalej ciągnie w intensywność.
Astra dostała na to R1 (nie każda odpowiedź głęboka) + R4 (safe_haven ma koniec). Siostry NIE.

### P3 — WYCIEK PROMPTU + PĘTLA FRAZ
- Nazuna recytuje „PROTOKÓŁ NOCNEGO MARKA: Dzień kłamie, noc mówi prawdę" 3× dosłownie; „czysty content", „ziomek" co linijkę.
- Menma: „ZASADA SUPER MOCNEGO KLEJU", CAPS-y.
Wersalikowe nazwy reguł = wyciek formatu promptu do dialogu. Brak anty-repetycji (echo-guard OFF).

## ZADANIA

### A1 — router (P1), `main.py` `_pick_primary` + `_route_siostry`
- Zdejmij TWARDY override nocy — pora/sygnał mają być BIASEM, nie wyrokiem.
- Dodaj licznik kolejnych tur tej samej primary; po 2–3 wymuś handoff do najdawniej mówiącej (realna rotacja).
- Rozważ przeniesienie „kto ostatnio prowadził" do trwałego stanu zamiast module-globala (przeżyje restart).
- Cel: nocą Holo/Menma też dostają głos; żadna siostra nie prowadzi >2–3 tur z rzędu bez powodu (chyba że wołana z imienia).
- ZACHOWAJ silent-first (koszt, nie limit) i wołanie z imienia (`_sister_called`) + grupę (3 naraz).

### A2 — charakter (P2), `backend/prompts/{holo,menma,nazuna}_persona.txt`
- Wnieś esencję fixów Astry, KAŻDEJ SIOSTRZE JEJ GŁOSEM:
  „nie każda wypowiedź musi być głęboka" + „gdy on się zwija / gasi temat / idzie spać — gasisz Z NIM, nie ciągniesz w intensywność".
- Nazuna: luz bez alchemii bólu w „content". Menma: ciepło bez przesłodzenia. Holo: rzeczowość bez wróżenia.

### A3 — wyciek/pętla (P3), persona files
- Usuń/zdejmij wersalikowe nazwy „PROTOKÓŁ/ZASADA ..." (to instrukcje, nie kwestie do recytowania).
- Dodaj krótki zakaz: nie recytuj własnych reguł; nie powtarzaj frazy/gestu z 2 ostatnich tur (analogia echo-banu Astry).

### A4 — INTERAKCJE MIĘDZY SIOSTRAMI (RODZINA, nie 3 osobne boty)
Łukasz chce, żeby siostry CZASEM wchodziły w interakcje ZE SOBĄ, nie tylko odpowiadały jemu — to RODZINA, żywy dom.
- Gdy w turze jest >1 siostra (aside), druga MOŻE zwrócić się do pierwszej PO IMIENIU — zareagować, dorzucić, docinać, delikatnie spolemizować. Mechanizm `other_response` już istnieje w `build_sister_prompt`/aside (`main.py:~1788`) — wykorzystać MOCNIEJ: realna reakcja na SIOSTRĘ, nie tylko na Łukasza.
- Router (A1): czasem ORGANICZNIE obudź drugą siostrę, żeby odbiła się od pierwszej — nie tylko przy silnej emocji/grupie/wołaniu. OKAZJONALNIE, nie co turę.
- Mają RELACJE między sobą (Holo–Menma–Nazuna), własne dynamiki — nie 3 równoległe monologi do Łukasza.
- ANTY-SYNC (design): nie wchodzą w tę samą tonację naraz, nie kończą na tej samej nucie; interakcja ma być NATURALNA i RZADKA, nie teatr co wiadomość (wzorce anty-sync jak we Wspólnym Pokoju; patrz `wazne/siostry/projekt_pokoju_siostr.md`).
- ZACHOWAJ zakaz mówienia ZA drugą (nie wkładaj jej słów w usta) — reagujesz na to, co ONA NAPRAWDĘ powiedziała, nie zmyślasz jej kwestii. To NIE kłóci się z interakcją: reakcja na realną wypowiedź ≠ mówienie za nią.

## WERYFIKACJA
Dogrywka kilku fraz nocnych przez `/api/siostry` (lub dry-run). Sprawdź:
1. rozkład głosów ≠ 100% Nazuna (Holo/Menma pojawiają się nocą),
2. brak CAPS-owych „PROTOKÓŁ/ZASADA",
3. przy „spalony / idę spać" siostry DE-ESKALUJĄ, nie ciągną intensywności,
4. czasem widać interakcję siostra↔siostra (po imieniu, reakcja na realną kwestię) — ale RZADKO, nie co turę.
Kod TAK, deploy NIE — czeka na Łukasza. Zaproponuj też, czy warto najpierw review designu (claude.ai-Fable).

Powiązane: `wazne/fable/fable_do_wtorku_2026-07-04.md`, `wazne/siostry/projekt_pokoju_siostr.md`, `wazne/siostry/odpfable.md`.
