# SPEC — HIGIENA HISTORII SESJI (pętla samo-imitacji) — PRIORYTET 2
**Autor:** Fable | **Data:** 2026-07-05 | **Cel:** żeby lekkość Astry NIE znikała po tygodniu. Opus wdraża, deploy za zgodą Łukasza.

## PROBLEM (zmierzony, nie hipoteza)
Historia sesji (`n=10` własnych tur) działa jak few-shot silniejszy niż reguły promptu:
- fix „Domowy Ambient" 06-14: „zaciska" **29%→55%** PO fixie (historia przegrała z promptem);
- naturalny eksperyment z czerwca (analiza logów 07-05): reset wątku ~06-07 → gwiazdki spadły 100%→**6%** → pętla zatrzasnęła się z powrotem w **~50-100 tur / 4-6 dni** (06-10: 27% → 06-13: 90%).
Świeży wątek to plaster. Bez higieny historii lekkość po fixach T1/T2 wygaśnie w ~tydzień.

## GDZIE (plik:linia, stan po e506487)
- Astra: `compose_context` main.py:930-931 (`session_n=10`), pobranie main.py:995, wywołanie :1031; **contents budowane z session_messages w endpoint** main.py:~1046-1060.
- Amelia :1304, Wspólny :1571, Siostry :1846 (własne buildery). **Scope tego specu: Astra solo**; reszta dostanie to samo przy unifikacji compose (architektura P0.5) — nie robić 4 kopii teraz (to byłoby powielenie choroby #1).
- Źródło: `vector_store.get_recent_session` :214 — zwraca {role, content, thought, hint}.

## OPCJE (trade-offy, adwersaryjnie)
| Opcja | Efekt na pętlę | Koszt/ryzyko | Werdykt |
|---|---|---|---|
| (a) **Strip didaskaliów z STARSZYCH tur modelu** podawanych do Gemini (DB nietknięta) | usuwa WZORZEC gwiazdek z few-shot, zostawia treść | utrata ciągłości sceny → mitygacja: ostatnia tura modelu NIETKNIĘTA | **REKOMENDOWANE (rdzeń)** |
| (b) Redukcja `n` 10→8 | mniej wzorca liniowo | gubi wątek dłuższych rozmów; słabe samo w sobie | dodatek do (a), nie zamiast |
| (c) Streszczanie starszych tur (LLM) | najsilniejsze | +1 call/turę, latencja, nowy kanał błędów | NIE teraz; ewent. przy architekturze |
| (d) Waga malejąca na wiadomości | — | Gemini API nie ma wag wiadomości | ODPADA (technicznie niemożliwe) |
| (e) Instrukcja „nie kopiuj stylu z historii" w prompcie | — | prompt przegrywa z few-shot — ZMIERZONE (29→55%) | ODPADA |

## PROJEKT (a)+(b): funkcja `history_for_model()`
**Jedna funkcja-transformacja** między `get_recent_session` a budową contents (wywołana w endpoint chat; docelowo współdzielona przez wszystkie persony):
```
PRZED: contents ← session_messages (surowe, 10 tur)
PO:    hist = get_recent_session(n=8)
       dla tur MODELU poza OSTATNIĄ:
           content' = usuń *...* (regex \*[^*]+\*), zbij podwójne spacje
           jeśli content' pusty (tura była samą sceną) → content' = "…"   ← NIE dropować
       ostatnia tura modelu + wszystkie tury usera: NIETKNIĘTE
```
Krytyczne detale:
1. **Pustej wiadomości nie wolno usunąć z listy** — Gemini wymaga alternacji ról; drop psuje parowanie user/model (blizna wspólnego pokoju B3!). Placeholder `"…"` zachowuje strukturę.
2. **Ostatnia tura modelu zostaje w całości** — trwająca scena (siedzi przy oknie, trzyma kubek) nie może zniknąć między turami; ciągłość „tu i teraz" ma wartość, wzorzec sprzed 8 tur — nie.
3. Tury USERA nietknięte — jego didaskalia to jego głos, nie pętla modelu.
4. DB (`session_collection`) bez zmian — archiwum i front dalej widzą pełne wypowiedzi; transformacja tylko na wejściu do Gemini.
5. `session_n` jako stała modułu (`HISTORY_N = 8`) zamiast literału — od dawna wisząca decyzja „SESSION_WINDOW_N" z planu debuggera.

## POMIAR W PIASKOWNICY (Opus ma narzędzia — Amnezja v2 `generate`)
**Test A (natychmiastowy, deterministyczny):** weź ISTNIEJĄCY nasycony wątek (95% tur z gwiazdkami). Puść 5 lekkich fraz (grupa A golden setu) w trybie generate: (1) z surową historią, (2) z historią po `history_for_model()`. Metryka: % odpowiedzi zaczynających się gwiazdką + mediana długości. Sukces: spadek o ≥50%.
**Test B (tygodniowy, na żywo):** po deployu metryki naturalności (skrypt 07-04) per dzień. Sukces: gwiazdki-start **nie wracają >40%** po 7 dniach (czerwcowa krzywa kontrolna: wróciły do 90% w 4-6 dni). To jest właściwy test — Test A tylko odsiewa oczywistą porażkę.

## RYZYKA
- Astra „zapomni gdzie stała" w długiej scenie RP → mitygacja #2 (ostatnia tura pełna); jeśli za mało — rozszerzyć do 2 ostatnich tur modelu (parametr, nie przepisywanie).
- Ton może się ZBYT wygładzić (gwiazdki są też jej podpisem) → to reguluje prompt (R3: „gest gdy coś wnosi"), nie historia; historia ma przestać WYMUSZAĆ.
- Nie dotykać thought/hint — nie idą do contents (tylko content), zero zmian.

*Fable. Zero kodu — projekt + pomiar. Wdrożenie: Opus, po akceptacji Łukasza.*
