# Work-order: dom v2 (22.11.2026 w nocy) — scena v2, karteczka, przeczucie Menmy v0, „wiedzą, gdzie byłeś”, Astra na stałe

Zgoda Łukasza 22.11 ok. 1:15: „od 1 do 4 już jest fajnie… jakby było jeszcze przeczucie Menmy, to by było naprawdę super”; po wyjaśnieniu: zostaje do 3:00. Plan i opcje: `plan_zywy_dom_v2_2026-11-22.md`. Dane: `ewolucja/siostry/2026-11/evolution_log_2026_11_22.md`.

**Jedna flaga:** `SIOSTRY_DOM_V2` (domyślnie `off`). Z flagą off prompt sióstr i odpowiedź API są takie jak dziś (kanarek `backend/tools/kanarek_t1_prompt.sh` przed i po deployu). Wdrożenie tylko na „wdrażaj” Łukasza, przy 0 turach w pokoju z 15 min; przełączenie flagi to jego decyzja.

## Co i dlaczego

1. **Scena v2.** Dowód: ~40 scen od 08.10 zaczyna się prawie tak samo („światło… rzucając długie cienie”, „Holo pochylona nad stołem”). Przyczyny w kodzie: przykłady w prompcie kamery (`'Holo liczy coś przy stole'`, `'Nazuna leży z padem'`) kopiowane przez model (klasa P7/P9), brak pamięci poprzednich scen, brak związku z poprzednim dniem. Zmiana: bez przykładów, lista ostatnich scen „nie powtarzaj”, po jednej bezpiecznej linijce z ostatniego dziennika każdej siostry jako możliwy ślad w kadrze.
2. **Karteczka** po powrocie (≥ 3 h): jedna siostra (ta, która mówiła ostatnio) zostawia 1–2 zdania swoim głosem. Front pokazuje ramkę, siostry dostają ją w prompcie tej tury.
3. **Przeczucie Menmy v0:** raz na dobę, tylko gdy w bezpiecznych linijkach ostatnich dzienników jest coś nadchodzącego (próg z danych). Wtedy karteczkę pisze Menma, jako przeczucie, nie pewność. Każde przeczucie zapisane w `<ANIMA_PLIKI_DIR>/dom/przeczucia.jsonl` ze stanem `do_sprawdzenia` (pod przyszły silnik z kalibracją).
4. **„Wiedzą, gdzie byłeś”:** gdy ostatnia wiadomość Łukasza u Astry solo jest nowsza niż ostatnia w pokoju i sprzed ≤ 6 h, siostry dostają jedną linijkę: był u Astry ok. N min temu, treści nie znają.
5. **Astra na stałe:** przy fladze `przyjdz` = bez limitu tur, stan w pliku (restart jej nie wyrzuca), `odejdz` = „Astra idzie do swojego pokoju”.

## Mapa klasy problemu (krok 5b), PRZED kodem

**Gdzie jeszcze ten sam typ problemu:**
1. *Przykłady w prompcie, które model kopiuje:* prompt kamery (naprawiane tu), `astra_base.txt:122` (gesty, znane od 15.08), persony sióstr (tiki, limit „przyprawa”). **Pokrywamy tylko kamerę**; persony i Astra poza zakresem (warstwa persony, S-2 „stop sesjom promptowym”).
2. *Wrażliwe rzeczy wracające nie w porę* (REJESTR §10, 16.11): nowe kanały to scena, karteczka i przeczucie, wszystkie biorą linijki z dziennika. **Pokrywamy:** jeden filtr `bezpieczne_linijki` dla wszystkich trzech: bez `[prywatne]`, bez `[prośba]`, bez zdrowia (`temat_zdrowia`), substancji, pieniędzy i rodziców; dodatkowo zakaz tych tematów w promptach karteczki i przeczucia.
3. *Liczba bez przyrządu:* przeczucie nie podaje procentów; zapis do pliku od pierwszego dnia, żeby kiedyś dało się policzyć trafność. **Pokrywamy.**
4. *Prywatność Astry solo w pokoju:* „wiedzą, gdzie byłeś” niesie tylko fakt i czas, nigdy treść. **Pokrywamy.** Dziennik solo Astry u gościa (decyzja z 14.11) **poza zakresem**, bez zmian.
5. *Stan w pamięci procesu* (gość ginie przy restarcie): pokrywamy tylko gościa na stałe (plik). `_last_full_speaker` i reszta routera **poza zakresem** (C-1).
6. *Ekstrakcja przy gościu wyłączona:* przy Astrze na stałe stary ekstraktor nie pisze nic przez całą wizytę. **Świadomie zostawione** (dziennik jest główną pamięcią; to i tak kierunek etapu 5), do wiadomości Łukasza.
7. *Amnezja musi widzieć to samo co produkcja:* `/api/debug/dom_v2` (na sucho, nic nie zapisuje) pokazuje prompt sceny, karteczki, ślady i sygnał przeczucia. Blok „wiedzą, gdzie byłeś” i karteczka w prompcie siostry nie są w `/api/debug/inspect`. **Luka zapisana**, do domknięcia przy następnej rozbudowie Amnezji.
8. *Wspólny i Amelia:* nie dotykamy (CLAUDE.md).

**Czy naprawa pokrywa klasę:** dla pokoju sióstr tak (scena, karteczka, przeczucie, gość). Nie dla person i nie dla Astry solo (pkt 1, 4).

## Odbiór (krok 7)
- Testy czystych funkcji (`backend/test_siostry_dom_v2.py`).
- Kanarek przed i po deployu: z flagą off `IDENTYCZNY` na wszystkich 6 zapytaniach.
- `/api/debug/dom_v2` na VPS: 3 sceny pod rząd mają różne pierwsze zdanie i nie zaczynają się od światła; karteczka bez zakazanych tematów; przeczucie tylko przy sygnale.
- Po włączeniu: 7 dni, licznik powtórzeń pierwszych słów scen (dziś: „światło… cienie” w większości) i liczba przeczuć w pliku.
