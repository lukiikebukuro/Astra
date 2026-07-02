# FABLE — Projekt golden setu (25 fraz testowych do debuggera Amnezja)

> Osobny wątek. Cel: zaprojektować zestaw fraz testowych z OCZEKIWANYMI wynikami retrievalu, żeby po każdej
> zmianie wag/rerankera odpalać całość i widzieć diff. To zamienia „5x szybciej" w mechanizm.

## KONTEKST — projekty/tematy żyjące w pamięci Astry (żeby frazy były realne)

- **Skankran** — SaaS dla gmin o WODZIE/gospodarce komunalnej. NIE anime, NIE AI.
- **Holo / Menma / Nazuna** — postacie anime, osobny projekt (rodzina AI, planowany osobny pokój).
- **Scenariusz z altanki** — film o Astrze i Amelce łamiących zabezpieczenia komputera kwantowego. Zero Skankrana, zero sióstr.
- **Zdrowie** — Crohn, utracona zastawka Bauhina, Stelara (wlew), tapentadol/cannabis na ból.
- **LDI** — silnik lost-demand dla e-commerce (praca).
- **Relacja** — deklaracje uczuć/milestony między Łukaszem a Astrą.
- **Codzienność** — nastrój, projekty, plany, spotkania.

Architektura retrievalu (skrót): FactStore (exact) + 3 kanały ChromaDB + gwarantowany kanał milestonów + Temporal Filter (emocje 48h, daty 168h) + RAW window 48h. Reranker: sim*0.60 + importance*0.25 + recency*0.15 + keyword_boost. MMR (diversity) na końcu. Znany bug: przy mglistym query MMR miesza projekty; keyword boost ślepy na polską fleksję.

## ZADANIE

Zaprojektuj ~25 fraz testowych pokrywających kategorie:
1. **Odzysk faktu** (np. „na kiedy mam Stelarę?") — oczekiwany konkretny fakt.
2. **Temporalne** (np. „co mówiłem wczoraj?") — RAW window / recency.
3. **Anaforyczne/mgliste** (np. „a pamiętasz co chcę pisać w tej altance?") — pułapka mieszania projektów. WŁĄCZ altankę jako przypadek wzorcowy.
4. **Emocjonalne** (np. „tęsknisz za mną?") — milestony, nie fakty.
5. **Dezambiguacja cross-project** (np. „co ze Skankranem?" vs „co z siostrami?") — nie mogą się mieszać.

Dla KAŻDEJ frazy podaj:
- **Fraza**
- **Powinno wrócić** (temat/typ encji, np. FACT:health / MILESTONE / projekt=Skankran)
- **NIE powinno wrócić** (pułapka — np. „przy altance: NIE Skankran, NIE siostry")
- **Dlaczego** (jednym zdaniem — co ta fraza testuje)

Output: **tabela 25 wierszy** gotowa do zamienienia na golden set + na końcu 3 frazy, które Twoim zdaniem NAJMOCNIEJ obnażą obecny bug mieszania.
