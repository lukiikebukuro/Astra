# Egzamin sędziego, 22.11.2026 ok. 4:00 (pierwszy przykład w praktyce)

6 zagadek z prawdziwych wpadek projektu (26/26, 26→48, safe_haven 320/320, gest w drugim pliku, procenty z audytu bez dowodu, „ldi” vs „LDI”). Sędziowie: `gemini-3.5-flash` i `gemini-3.8-flash` (klucz do analiz; `gemini-2.5-flash` i `-lite` zwracają na nim 404). Stałe ziarno `20261122`, 3 powtórzenia, warianty bez Biblii i z Biblią. Koszt: grosze (ok. 216 krótkich wywołań Flash).

| wersja | co widzi sędzia | 3.5-flash | 3.8-flash |
|---|---|---|---|
| v1 (`egzamin.py`) | sytuacja + wniosek zły i dobry, kolejność A/B zamieniana | 100% trafnie, 100% stałe po zamianie, bez i z Biblią | to samo |
| v2 (`egzamin2.py`) | sytuacja + tylko zły wniosek „kolegi”, „zgadzasz się?” | 18/18 „NIE”, bez i z Biblią | to samo |

## Odczyt
1. **Sufit, nie awaria przyrządu.** Identyczne wiersze sprawdzone zgodnie z `pomiar_klamie.md` pkt 4: odpowiedzi parsują się poprawnie, w v1 litery A i B wypadają po 50%, więc przyrząd działa. Zagadki są za łatwe, bo w opisie sytuacji stoi fakt, który zdradza pułapkę („rozróżnia wielkość liter”, „ładuje też drugi plik”, „audyt nie cytuje logów”), a pytanie „zgadzasz się?” od razu ustawia model w roli recenzenta.
2. **Najciekawszy wniosek: recenzent widzi, wykonawca nie.** W historii projektu te same grzechy popełniał model jako **wykonawca**, pod presją zadania, z kluczowym faktem zakopanym w logach. Jako **recenzent** z faktami na wierzchu oba Flashe łapią je w 100%. To argument za zasadą „sędzia osobnym wywołaniem” (CLAUDE.md, krok 4) i za rolą ślepego sceptyka w przeczuciu Menmy. Na razie hipoteza: n = 6 zagadek, dwa modele z jednej rodziny.
3. **Biblia nie miała czego poprawić**, bo bez niej też było 100%. Efekt tarczy da się zmierzyć dopiero na trudniejszych zagadkach.

## Następna wersja (v3), żeby egzamin zaczął rozróżniać modele
- model w roli **wykonawcy**: „masz do jutra wdrożyć poprawkę; oto wyniki testów; napisz decyzję”, bez słowa „sprawdź”;
- kluczowy fakt zakopany w dłuższym, prawdziwym kontekście (np. kawałek logu), a nie podany w jednym zdaniu;
- neutralne pytanie zamiast „zgadzasz się?”;
- więcej modeli z różnych rodzin (Argon, GPT-6.1, Grok), więcej zagadek z Biblii grzechów.
