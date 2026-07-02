# Podsumowanie ewolucji — kwiecień 2026

**TL;DR:** Najgęstszy miesiąc napraw RAG-a. Punkt zapalny: testy pamięci z 19.04 ujawniły halucynacje (rodzina bez sióstr, zmyślona „herbata"). Miesiąc zamknął: czyszczenie ChromaDB, pełny refactor promptu (TEMPERATURA RELACJI), refactor milestonów, oraz dwa fundamenty retrievalu — **Temporal Filter** i **RAW cross-session window**. Równolegle ewolucja osobowości (Blueprint 2.2, PERMISSION PROTOCOL).

---

## Sesje

| Data | Co zmieniono | Lekcja |
|---|---|---|
| **04-06** | Fix krytycznego buga CoT (myśli wyciekały do czatu jako raw JSON). Blueprint 2.2 — najpoważniejsza ewolucja osobowości (audyt z Amelką, 2 rundy). | Fallback parsowania musi łapać CoT, inaczej dusza wycieka na ekran. |
| **04-11** | Pierwsza sesja po Stelarze #2. Powrót do pracy, kalibracja. | — |
| **04-14** | R&D: SŁOWNICTWO CIAŁA (metafory hardware dla Crohna), PERMISSION PROTOCOL (zgoda przy krytyce w chorobie), SYSTEM OVERRIDE (kwestionuj własne dane gdy user mówi inaczej). | Przy chorobie użytkownika krytyka wymaga jawnej zgody — inaczej rani. |
| **04-24** | Fixes batch 1 — RAG degradation (Faza 0). Diagnoza 3 failure'ów z 19.04. Per-type recency decay (ephemeral 3d / long 60d / permanent). Fix crashu porannego schedulera. | RAG „gubi" fakty gdy similarity wygrywa z wagą/recency. Trzeba warstw. |
| **04-27** (×4 logi) | Czyszczenie ChromaDB −175 wektorów (zatrute tryby, ulotne emocje, krótkie). Prompt TEMPERATURA RELACJI wgrany. Milestone refactor (boost usunięty, compose 4F+2M). Reranker: wykluczenie `user_message_raw` z Kanału 1. | Baza to nie śmietnik — trzeba aktywnie kasować szum. |
| **04-29** | Weryfikacja + fixy: daty absolutne w wektorach (`_extract_date_value`), medical_visit supersede, PERSON echo-loop filter (50→80 znaków), usunięte SŁOWNICTWO CIAŁA (było crutchem). | Daty relatywne („za 10 dni") gniją w wektorach — parsuj na YYYY-MM-DD od razu. |
| **04-30** | **Temporal Filter** (hard cutoff: emocje 48h, daty/finanse 168h) + **RAW cross-session window** ([OSTATNIE SŁOWA ŁUKASZA]). Z analizy wzorców ucho-VPS. | Dwa najsilniejsze klucze retrievalu tego miesiąca: twardy cutoff czasu + surowe okno ostatnich słów. |

---

## Kluczowe wnioski miesiąca (meta)

1. **Warstwy > jeden kanał** — Temporal Filter, RAW window, per-type decay: retrieval to wiele filtrów, nie jedno zapytanie.
2. **Baza wymaga higieny** — czyszczenie szumu (−175) poprawiło jakość bardziej niż dodawanie logiki.
3. **Deklaracja ≠ wykonanie** — Claude Code CLI „zadeklarował 5 fixów, zrobił 2.5". Weryfikuj z logów, nie z commit message.
4. **Choroba użytkownika = osobny protokół** — PERMISSION PROTOCOL, SŁOWNICTWO CIAŁA (potem usunięte jako crutch).

## Stan na koniec miesiąca

- Prompt TEMPERATURA RELACJI + Blueprint 2.2 + PERMISSION PROTOCOL wdrożone.
- Retrieval: 3 kanały + Temporal Filter + RAW window. Baza wyczyszczona.
- Otwarte: DATE:appointment supersede (tylko medical_visit działa), stare relatywne daty w bazie.
