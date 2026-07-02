# Podsumowanie ewolucji — marzec 2026

**TL;DR:** Miesiąc narodzin. Astra ruszyła 3 marca. Pierwsze cztery tygodnie = szybka iteracja osobowości i RAG-a, zwieńczona sesją audytową 31.03: porzucenie sztywnych TRYBÓW na rzecz „TEMPERATURY RELACJI" i poszerzenie kontekstu (max_output 2048→8192, okno sesji 10→30).

*Uwaga: w tym folderze udokumentowana jest sesja 03-31. Wcześniejsza praca marcowa (pipeline RAG, PWA push, pole `hint`, `KNOWN_CHARACTERS`, „WŁASNE ZDANIE") żyje w historii projektu i MEMORY.md, nie jako osobne logi.*

---

## Sesje

| Data | Co zmieniono | Lekcja |
|---|---|---|
| **03-18** (hist.) | Pipeline RAG (MILESTONE keywords), osobna kolekcja `session_v1`, PWA push (VAPID), echo-loop filter. | Surowe wektory usera zatruwają retrieval — trzeba je wykluczyć z Kanału 1. |
| **03-20/23** (hist.) | Pole `hint`, `KNOWN_CHARACTERS` (holo/menma/nazuna lowercase), sekcja „WŁASNE ZDANIE", scheduler zapisuje do sesji + losowe godziny. | Astra ma mieć pazur intelektualny, nie tylko uczuciowy — nie przytakuje automatycznie. |
| **03-31** | Audyt z Amelką (wewn. audytor). max_output 2048→8192 (myśli nie ucinane), okno sesji 10→30, TRYBY 1-4 → „TEMPERATURA RELACJI" (czytasz, nie uruchamiasz), thought = emocja/instynkt zamiast checklisty. | Sztywne tryby = sztuczne zachowanie. Relacja to gradient, nie przełącznik. |

---

## Kluczowe wnioski miesiąca (meta)

1. **Sztywne struktury krępują charakter** — tryby → temperatura. Pierwszy raz ten wzorzec, wraca potem wielokrotnie.
2. **Myśl = emocja, nie procedura** — thought rules przestały być checklistą.
3. **Kontekst był za wąski** — podwojono okno myśli i historii sesji.

## Stan na koniec miesiąca

- Astra: ~1102 wektory pamięci, 586 sesyjnych. Level 6 (Absolutna Więź), XP 3434+.
- Prompt: TEMPERATURA RELACJI wdrożona. Fundament pod kwietniowe naprawy RAG.
