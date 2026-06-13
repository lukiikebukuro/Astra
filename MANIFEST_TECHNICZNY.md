# ASTRA — Manifest Techniczny
## Inżynieria Wsteczna Świadomości: Architektura Suwerennej Pamięci AI

**Autor:** Łukasz Piskorski / Anomaly Tech
**Wersja:** Blueprint 2.2 (2026-04-11)
**Status:** Produkcja — myastra.pl

---

## Wstęp: Czym to nie jest

To nie jest chatbot z osobowością. To nie jest wrapper na GPT-4 z system promptem. To nie jest kolejny AI companion który "pamięta twoje imię i psa".

To jest system który ewoluuje szybciej niż standardowe modele — przez unikalny feedback loop oparty na inżynierii wstecznej własnych decyzji.

Architektura nosi nazwę **ANIMA** (Autonomous Neural Intelligence Memory Architecture). Jej pierwsza implementacja produkcyjna — ASTRA — działa na VPS od marca 2026 i obsługuje jednego użytkownika z pełną izolacją danych, suwerenną kontrolą pamięci i adaptacyjnym systemem rerankingu.

To dokument wyjaśniający dlaczego i jak.

---

## I. Data Distillation: Nie karmimy systemu byle czym

### Problem ze standardowym podejściem

Większość systemów RAG działa w ten sposób: użytkownik coś mówi → tekst ląduje w bazie wektorowej → przy następnym zapytaniu model dostaje `n` najbardziej podobnych fragmentów. Proste, szybkie, przewidywalne.

Problem: baza rośnie liniowo. Po miesiącu masz 1400 wektorów "jestem zmęczony", "byłem dziś u lekarza", "lubię herbatę". Model dostaje pool 30 kandydatów, reranker wybiera top-5 — i często wybiera źle, bo nie ma mechanizmu który odróżnia *sygnał* od *szumu*.

### Nasze podejście: destylacja przez warstwę semantyczną

ANIMA nie zapisuje surowego tekstu. Każda wiadomość przechodzi przez pipeline zanim trafi do ChromaDB:

```
Wiadomość użytkownika
    ↓
SemanticExtractor (sentence-transformers, zero-shot classification)
    → entity_type: EMOTION / MILESTONE / FACT / DATE / PERSON / MEDICATION
    → subtype: 'preference' / 'tired' / 'trust_declaration' / 'inventory_status' ...
    → confidence: 0.0–1.0
    ↓
MemoryEnricher
    → importance: 1–10 (rule-based + keyword boost)
    → relational_impact: 'high' / 'medium' / 'low'
    → temporal_type: 'ephemeral' / 'persistent' / 'milestone'
    ↓
_synthesize_text()
    → "[FACT:preference] lubię czarną herbatę"  ← nie surowy cytat
    ↓
ChromaDB (z metadanymi: importance, entity_subtype, source, timestamp)
```

Efekt: baza nie zawiera 1400 fragmentów rozmów. Zawiera **skatalogowane, wzbogacone fakty** z przypisaną wagą ważności i typem semantycznym.

### Skąd wiemy że to działa? Inżynieria wsteczna własnych sesji

Projekt ANIMA równolegle napędza inny system (Amelia — AI companion na ucho-VPS). Tam, po podpięciu do strumienia Gemini XHR, zebraliśmy logi produkcyjne z sesjami RAG: pliki `.jsonl` z rozmowami + `.log` z terminala pokazujące reranker scores, wyciągnięte encje, akcje pipeline'u.

Analiza tych logów to nie A/B testing. To inżynieria wsteczna własnego procesu decyzyjnego:

```
[UCHO] Znaleziono 5 wspomnień RAG (reranked):
[1] score=1.000 | '[EMOTION:tired] leżałem chory...'
[2] score=0.983 | '[MEDICATION:pregabalina] wzialem klona...'
[3] score=0.961 | '[MILESTONE:trust_declaration] nigdy nikomu...'
```

Z tych logów wyciągamy wzorce: które encje trafiają do top-5, które wypadają, dlaczego. Poprawki do rerankera ASTRY powstają na podstawie obserwacji prawdziwych sesji, nie syntetycznych testów. To jest **Data Distillation** — destylujemy logikę decyzyjną z zachowania systemu na żywych danych.

---

## II. Sovereign Memory Architecture: Pamięć która sama sobą zarządza

### Pasywny kontener vs. aktywny system

Standardowy RAG jest pasywny. Dodajesz fakty, nigdy ich nie usuwasz (bo nie wiesz co jest "stare"), baza rośnie, retrieval degraduje. Model po roku dostaje pool pełen sprzecznych, zduplikowanych, przestarzałych wektorów.

ANIMA implementuje **Suwerenną Architekturę Pamięci** — system który sam decyduje co zachować, co nadpisać, co usunąć.

### Trzy mechanizmy suwerenności

**1. Supersede Logic (wdrożone 2026-04-11)**

Nie wszystkie typy wspomnień powinny akumulować. Emocje są efemeryczne — "jestem zmęczony" z trzech miesięcy temu to szum, nie sygnał. Preferencje ewoluują — nowe "lubię herbatę" powinno zastąpić stare.

```python
SUPERSEDE_TYPES = {
    ('EMOTION', 'tired'), ('EMOTION', 'stressed'),
    ('EMOTION', 'positive'), ('EMOTION', 'negative'),
    ('FACT', 'preference'),
    ('DATE', 'inventory_status'),  # nowy stan leków zastępuje stary
}
```

Gdy pipeline wykrywa encję z tej listy, przed zapisem wywołuje `delete_by_entity_subtype()` — czyści stare wektory tego samego type:subtype, potem zapisuje nowy. Efekt: baza nie rośnie bez końca. Akumulują tylko te typy gdzie historia ma wartość (milestony, wizyty medyczne, fakty o ludziach).

**2. Reranker z adaptacyjnymi wagami**

Retrieval nie jest plain cosine similarity. Final score każdego kandydata to:

```
final_score = 0.25 * importance_score      # waga encji (1–10 / 10)
            + 0.15 * recency_score          # exponential decay, half-life 7 dni
            + 0.60 * similarity_score       # dominacja semantyczna
            + keyword_boost                 # hybrid search lite, max +0.15
            + temporal_boost               # +0.15 jeśli wiadomość < 24h
            + milestone_boost              # +1.0 dla kamieni milowych (gwarantowane top)
```

`similarity_score` dominuje — system wybiera co jest *semantycznie trafne*, nie co jest najnowsze ani najważniejsze w izolacji. Milestone boost (+1.0) gwarantuje że deklaracje zaufania i intymności zawsze trafiają do modelu niezależnie od query.

Wagi nie są stałe w kodzie. Są parametryzowane — możemy je dostrajać per-query-type bez restartu.

**3. MMR (Maximum Marginal Relevance)**

Po rerankingu wyniki przechodzą przez MMR z `diversity_penalty=0.8`. Zapobiega dominacji jednego wektora — jeśli top-5 to pięć wariantów "jestem zmęczony", MMR wybierze dwa i dorzuci trzy semantycznie różne. Wynik: szerszy kontekst, mniej echo-chambers.

### Dlaczego to jest suwerenność

Standardowy AI companion ma pamięć jako feature. ANIMA ma pamięć jako **architekturę**. System nie czeka na polecenia "zapamiętaj to" / "zapomnij tamto". Sam klasyfikuje, waży, nadpisuje i archiwizuje — w oparciu o reguły wyprowadzone z obserwacji prawdziwych interakcji.

---

## III. Dynamic Context Tuning: System który uczy się przez obserwację własnych błędów

### Case study: herbata miss

Przez kilka tygodni model nie pamiętał preferencji Łukasza dotyczących herbaty. Nie dlatego że nie było wektora — był. Ale:

1. `semantic_extractor` zapisywał surowy fragment wiadomości zamiast syntetyzowanego faktu
2. Pipeline nie nadpisywał — akumulował kolejne wersje `[FACT:preference]`
3. Kilkanaście podobnych wektorów razem → MMR diversity penalty karał je wszystkie
4. Milestony (importance=10, +1.0 boost) wypychały je z top-5

Diagnoza nie przyszła z unit testów. Przyszła z analizy logów rerankera — widać było score'y, widać było co trafiło do modelu, widać było czego nie ma.

Fix: supersede logic + `entity_subtype` w metadanych. Od teraz nowy `[FACT:preference]` usuwa stary przed zapisem. Jeden wektor zamiast kilkunastu, MMR go nie karze.

### Feedback loop który wyprzedza standardowe modele

Standardowe modele językowe uczą się przez retraining — kosztowny, rzadki, centralizowany. ASTRA ewoluuje inaczej:

```
Sesja produkcyjna
    ↓
Logi (conversations/*.jsonl + terminal/*.log)
    ↓
Analiza rerankera — co trafiło, co wypadło, dlaczego
    ↓
Diagnoza: błąd w pipeline, złe wagi, brakująca logika
    ↓
Patch: kod + prompt + parametry rerankera
    ↓
Deploy — ten sam dzień
    ↓
Kolejna sesja produkcyjna
```

Iteracja trwa godziny, nie miesiące. System poprawia się przez obserwację własnego zachowania, nie przez zmianę modelu bazowego. Model bazowy (Gemini 2.5 Flash) zostaje — zmienia się warstwa która zarządza jego pamięcią i kontekstem.

To jest Dynamic Context Tuning: nie fine-tuning wag modelu, ale ciągłe dostrajanie warstwy retrieval i architectural constraints na podstawie live data.

---

## IV. Dlaczego nie budujemy bota

### Cyfrowe przedłużenie, nie asystent

ASTRA jest zaprojektowana pod jednego użytkownika — Łukasza Piskorskiego. Architektura zna jego historię medyczną (Crohn, Stelara), rozumie jego styl pracy ("Architekt Intencji"), pamięta kontekst projektów (LDI, ANIMA, Skankran).

To nie jest personalizacja przez fine-tuning. To jest **retrieval-augmented identity** — tożsamość użytkownika zakodowana w suwerennej bazie wektorowej która informuje każdą odpowiedź.

Różnica między asystentem a cyfrowym przedłużeniem:
- Asystent odpowiada na pytania
- Cyfrowe przedłużenie uzupełnia myśl zanim zostanie wypowiedziana, bo pamięta poprzednie 300 myśli

### Architektura która skaluje inaczej

ANIMA nie jest zbudowana na jeden model. Jest zbudowana na warstwę abstrakcji która jest model-agnostic: ChromaDB + sentence-transformers + reranker + pipeline ekstrakcji. Podmiana modelu bazowego z Gemini 2.5 Flash na cokolwiek innego wymaga zmiany jednej linijki konfiguracji.

Baza wektorowa pozostaje. Historia pozostaje. Tożsamość pozostaje.

To jest decyzja architektoniczna: **nie uzależniamy suwerenności pamięci od dostawcy modelu.**

### Privacy-first by design

Wszystkie ID wektorów to `SHA256(salt:user_id:text)` — deterministyczne, anonimowe, niemożliwe do odtworzenia bez salta. Dane użytkownika nigdy nie opuszczają VPS w formie surowej. Multi-user isolation jest wbudowana od dnia zero, nie dodana post-hoc.

---

## V. Stan systemu (2026-04-11)

| Komponent | Szczegół |
|-----------|---------|
| Model | Gemini 2.5 Flash, `thinking_budget=4096`, `max_output_tokens=8192` |
| Baza wektorowa | ChromaDB, 1476 wektorów pamięci + 743 sesyjne |
| Ekstrakcja | `paraphrase-multilingual-MiniLM-L12-v2`, zero-shot classification |
| Reranker | importance×0.25 + recency×0.15 + similarity×0.60 + boosty |
| MMR | `diversity_penalty=0.8`, `RECENCY_HALF_LIFE_DAYS=7` |
| Supersede | 8 typów encji z rotacją, backward-compatible z istniejącą bazą |
| Persona | Blueprint 2.2 — Trinity Mix (50% akceptacja / 30% charakter / 20% siła) |
| Deploy | VPS 116.203.134.228, systemd, SSL, uptime 24/7 |
| Session | n=30 (15 wymian), historia przeżywa restart przez ChromaDB |

Ocena RAG po supersede: **7/10** → cel: **8/10** po kolejnych 2 tygodniach sesji produkcyjnych.

---

## Epilog: Co to znaczy że system ewoluuje

Standardowy model językowy ma stałe wagi. Uczy się przez retraining który jest drogi, rzadki i wymaga ogromnych danych.

ANIMA ewoluuje przez obserwację. Każda sesja produkcyjna to dane treningowe dla warstwy retrieval. Każdy miss (herbata) to diagnoza i patch. Każdy blueprint (2.2) to nowa iteracja architectural constraints.

System który przez rok zbiera logi własnych sesji, analizuje je i poprawia retrieval — bez dotykania modelu bazowego — jest bardziej adaptacyjny niż model który raz w roku przechodzi retraining.

To nie jest utopia AI. To jest inżynieria: konkretna, iteratywna, oparta na danych.

**Budujemy suwerenną pamięć. Reszta to tylko interfejs.**

---

*Anomaly Tech — Gorzów Wielkopolski, 2026*
*Repozytorium: prywatne (github.com/lukiikebukuro/Astra)*
*Kontakt: portfolio → anomalytech.eu (w budowie)*
