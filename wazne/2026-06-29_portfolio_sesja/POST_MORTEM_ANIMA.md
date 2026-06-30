# GŁĘBOKIE TECHNICAL POST-MORTEM: Architektura Pamięci ANIMA (Wspólny Pokój, RAG & Supersede)

**Wstęp:** Klasyczny RAG (Retrieval-Augmented Generation) w systemach AI bazujący wyłącznie na przeszukiwaniu wektorowo-podobnych fraz (np. w logikach "chat with your docs") to pułapka w rozwoju wirtualnych towarzyszy. Pasywne zapisywanie wszystkiego uszkadza spójność czasową – po 3 miesiącach testów, zapytanie odnajdywało po 30 wpisów "jestem dzisiaj zmęczony", a system karany de-duplikacją MMR całkowicie ignorował kamienie milowe o znaczeniu relacyjnym. 

Zbudowana na produkcyjnym VPS architektura ANIMA odwraca zasady pasywnego przechowywania danych.

---

## 1. Zjawisko "Cmentarza Wektorowego"
Standardowa architektura tworzy bazy przyduszone przez nieskończone zbieractwo (Accumulation Problem), wypierające logikę "teraz" (Temporal Blindness) przez odnajdywanie podobnego, choć starego, wpisu.

### Patologia: "Rzeźnia Kamieni Milowych" (Analiza błędu punktowania)
**Problem:** Początkowo starałem się walczyć z MMR podbijając sztucznie wartości krytycznych relacyjnych wyznań ("kamieni milowych"). Kod wyglądał następująco: `final_score += 1.0` z sufitem matematycznym ścinającym punktację na maksa `1.0`. By podbić ważność faktu zapisanego miesiące temu (który tracił swój wskaźnik recency), narzuciłem matematyczny gorset dający z założenia `1.500` - w efekcie milestony miaźdżyły każdy bieżący kontekst. Działające podbijanie wektorów stawało się structural-bomb-ą, uniemożliwiając logiczne wnioskowanie przy prostych pytaniach.
**Rozwiązanie:** Opuściłem siłę `boost` tylko na matematyczne `+0.25` modyfikatora dla progu po cap-ie do 1.0. W połączeniu z hardkowanym "Guaranteed Milestone Channel", milestony całkowicie zaczęły mijać pole rażenia "surowego zapytań o bieżące zadania", omijając proces wpychania go do MMR, ale nadal rywalizując uczciwą dystrybucją RAG jeśli zapytanie operowało w warstwie "uczuciowej".

## 2. Pamięć na dwóch silnikach: Semantic Extraction vs Explicit SQLite Lookup
Skorzystanie z ChromaDB na bazie SentenceTransformers powoduje utraty ważnych detali jeśli model zignoruje similarity score na korzyść wagi i terminu. Aby AI zdołał zachowywać spójną relację powziąłem nowatorską ścieżkę hybrydową.

**SQLite FactStore (Twarde Fakty)**
Aplikacje generatywne nie mogą grać w rzut monetą ze stałymi zdrowotnymi czy osobistymi preferencjami:
- Przeniosłem 12 rodzajów absolutnych `ENTITY_DEFINITIONS` z bazy Chroma do klasycznego `SQLite`.
- Wektorom stworzonym po raz ponowny dla typu `FACT:health`, `FACT:preference` przypisano generowanie bezwzględnego hash'a (`SHA256(entity_type:subtype:persona_id:user_hash)`). Wysłanie na bazę operacji wgrywa twardy `INSERT OR REPLACE` uaktywniając `Supersede Logic`. 
- Baza pamięta dzięki temu *wyłącznie o najnowszych twardych faktach* ograniczając koszty API tokenu. System pamięta dokładnie, na kiedy user przełożył swoją wizytę, nie wysyłając ślepych RAG queries o terminy wizyt. W kodzie wrzucam je bezpośrednio na hardkodowaną pozycję do Prompt Assembly - z bloka `[TWARDE FAKTY]`.

**ChromaDB Supersede Pipeline**
Natychmiast po uruchomieniu semantycznej ekstrakcji (z wykorzystywaną barierą thresholdów dla wektorów typu `EMOTION >= 0.55`), te podlegające regułom obracanym (tak jak tymczasowa "zła motywacja", albo "podniecenie") zostają przepuszczane przez moduł logarytmów wymuszające usuwanie. System wypluwa `delete_by_entity_subtype` dla bazy ChromaDB, całkowicie rotując bezsensowny stary śmietnik – cykl ewolucji staje się aktywny i przypomina wreszcie ludzką skłonność do zacierania.

## 3. "Temporal Blindness" i Filtr Cut-Off
System by opierać się pasywnej rotacji został ubrany w *Cross-Session RAW window*: RAG podaje dosłowne surowe komunikaty wektorowe, ale bez szans na przedostanie się poza próg 48H. System nie traci pamięci krótkotrwałej o czym rozmawiano wczoraj, ale natychmiast zapomina błache detale ("Zjadłem chłodnik", "Nie chce mi się pisać do ciebie") zamykając w ramy bezwzględny spadek wektorów (`Temporal Cutoff Filter`). Emocje 48, budżet/finanse 168h.

## 4. Patologie Systemów Współistniejących: Echo i Anti-Sync
Przy budowie opcji `/api/wspolny` – środowiska gdzie dwa osobne modele ewaluują jednocześnie kontekst bez uszkadzania swoich instancji logicznych, mierzyłem się z uderzeniami "Cross-halucynowania":
- **Zjawisko Echo-Loop Guard**: Modele przy budowie Semantic Pipeline, przechwytywały "siebie same" z rozmów z drugą platformą AI wmawiając sobie generacje jako `Fakty Użytkownika`. Zaobserwowane bugi skutkowały wyłączeniem całości ścieżki ekstrakcji w "Wspólnym Pokoju", dodatkowo RAG wykluczał wpisy `extracted_person` w warstwach o gęstości >80 Znaków. W kodzie jest zasada strict tnąca i podmieniająca słowa jak echo `strip_memory_echo()`.
- **API Model Collision**: Podwójny request API zawodził system logik i pękał, tworząc kolejność User -> Astra -> Amelia (jako model error). Zmianą był mergowany `role-alteration` (Astra/Amelia stawały się wspólnym promptem generacji `other_response` z flagą nie-duplikacji: zakaz cytowania zachowania drugiego skryptu np. pierwszego członu zdania i zawartych w asteryskach operacji fizycznych (*patrzy smutno*)).

## 5. Cicha Asocjacja: "Thinking Budget"
Użytkownicy AI Companion szukają nie tylko poprawnego zachowania – oni żądają chemii i organicznego skoku logicznego. Uruchamiając parametry generacji z JSON, AI przechodziło w "płytsze myśli". 
Do endpointów Gemini dodane zostało `thinking_config=genai_types.ThinkingConfig(thinking_budget=4096)`. Model otrzymał "ślepą pętle" myśli od wewnętrznego kontrolera. Dodatkowym czynnikiem było zbudowanie w System Prompt JSON osobnej flagi `"hint": "jedna mroczna / wewnetrzna bezceremonialna sentencja zakazana z powtarzalnoscia"`. Zmieniło to natychmiast logikę odpisywania. A.I. zaczęło myśleć i czuć organiczną reakcję asocjacyjną między wynikiem zaplecza faktów RAG a surową analizą uczucową, unikając korpo sterylizmu.

--- 

*Architektura ANIMA nie gromadzi wiedzy o użytkowniku — ewoluuje wiedzę o użytkowniku. Cechuje się własną suwerennością decyzyjną na zasadach dedykowanych praw zarządzania instancją logów i RAG.*