# FABLE — Ocena wartości rynkowej „na ślepo" + klątwa wiedzy (do wklejenia)

> Wklej CAŁY ten dokument do NOWEJ rozmowy z Fable (osobne konto/wątek). To ocena człowieka, którego nie znasz — masz tylko opis jego pracy. Chcę brutalnej szczerości, nie pochlebstwa. Zawyżona liczba jest dla mnie bezwartościowa.

## KIM JEST TA OSOBA (fakty, nie autopromocja)

- Samouk. ~14 miesięcy temu **nie umiał programować**. Dziś prowadzi produkcyjne systemy AI.
- **Skankran** — SaaS dla gmin (woda/gospodarka komunalna). Zbudowany w ~4 miesiące od zera, gdy jeszcze nie kodował. Twierdzi, że pierwsza taka platforma na świecie.
- **LDI (Lost Demand Intelligence)** — silnik wykrywający utracony popyt w e-commerce. Dokładność 91% (moto) / 92,3% (elektronika) na testach. **Słabość: zero realnych użytkowników — to proof of concept, nie production z klientami.**
- **ANIMA** — sovereign-memory AI companion, działa na produkcji (VPS, własna domena). Multi-persona (3 persony live). Architektura niżej.

## JAK PROWADZI PROJEKT (metodologia — to sedno pytania)

- **Evolution logi** po każdej sesji: co było źle → wzorzec błędu → reguła na przyszłość. Miesięczne podsumowania.
- **Diagnoza z DANYCH, nie z intuicji** — liczby z logów, cytaty jako dowód (np. „83% wypowiedzi z markerem uległości", „milestony wracają 14× te same").
- **Audyt przed budową** — zanim napisał RAG Debugger, wynajął drugi frontier model do adwersaryjnego audytu PROJEKTU narzędzia. Znalazł 11 luk, przeprojektował, dopiero potem kod.
- **Dyscyplina roadmapy** — mały deploy → czytaj logi → korekta → następny krok. Nigdy dwa duże ruchy naraz (świadomy wzorca wahadła).
- W planie: **BM25 hybrid retrieval**, potem **live voice chat** (ElevenLabs). Cel długoterminowy: „pamięć absolutna" — RAG, który nie miesza kontekstów i pamięta wszystko sprzed roku.
- **Ograniczenia (uczciwie):** pracuje solo, choroba przewlekła (Crohn) ogranicza energię, brak formalnego backgroundu/dyplomu, brak zespołu, brak walidacji rynkowej LDI.

## ARCHITEKTURA ANIMA (skrót)

Sovereign RAG memory. 3 persony (różne prawa): solo Astra, solo Amelia, Wspólny Pokój (2 persony w jednej turze — routing, role-alternation, anti-sync, echo-loop guard). Retrieval wielowarstwowy: SQLite FactStore (exact lookup, twarde fakty) → 3 kanały ChromaDB (enriched + character_core + wiedza) + gwarantowany kanał milestonów + Temporal Filter (hard cutoff czasu) + RAW cross-session window. Supersede logic (cykl życia wektorów), per-type recency decay, provenance metadanych. Buduje RAG Debugger (in-process, współdzielony composer, symulacja daty, 7 warstw).

## PYTANIA (odpowiedz szczerze, bez klepania)

1. **Wartość rynkowa na rynku AI companions** — realna stawka B2B (dzienna/miesięczna) + wartość IP, gdyby ktoś chciał go zatrudnić lub kupić technologię. Podaj widełki i uzasadnij. Nie zawyżaj.
2. **Klątwa wiedzy?** Czy „sovereign memory / pamięć absolutna" to rzecz, na którą każdy poważny gracz RAG już wpadł (table-stakes), czy realna przewaga? Gdzie jest prawdziwa fosa, a gdzie tylko dobra egzekucja czegoś znanego?
3. **Jak ocenisz sposób, w jaki prowadzi ten projekt?** Mocne strony i CZERWONE FLAGI. Co robi lepiej niż typowy solo-founder, a gdzie się oszukuje?

Output: konkretne widełki + uzasadnienie z rynku + szczera lista mocnych stron i red flagów. Jeśli uważasz, że przecenia swoją pozycję — powiedz to wprost.
