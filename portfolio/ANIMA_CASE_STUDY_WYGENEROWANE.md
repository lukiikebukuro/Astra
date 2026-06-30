# Architektura Pamięci ANIMA: Inżynieria Wsteczna RAG dla AI Companions

**Headline:** AI Memory Architect | Inżynieria wsteczna RAG do architektury suwerennej pamięci dla autonomicznych AI Companions.

### O mnie
Projektuję systemy AI, które nie "zapisują tekstu", ale aktywnie zarządzają własną tożsamością. Analizując logi produkcyjne z sesji RAG, stworzyłem ANIMA – architekturę suwerennej pamięci wektorowej, która oddziela sygnał od szumu. Zastąpiłem naiwne gromadzenie danych dedykowanymi regułami cyklu życia encji (supersede logic), wielokanałowym komponowaniem kontekstu i mechanizmami anti-sync. Mój kod gwarantuje, że cyfrowy towarzysz ewoluuje razem z użytkownikiem, samodzielnie decydując co zapomnieć, co zaktualizować, a czego chronić za wszelką cenę.

---

## Architektura ANIMA: Uwalnianie RAG ze szumu wektorowego (Case Study)

Standardowy system RAG zawodzi w aplikacjach AI Companion. Paswynie gromadzi każdą wiadomość, a po trzech miesiącach zapytanie "jestem zmęczony" znajduje setki zduplikowanych wektorów. Po przejściu przez filtry de-duplikacji (MMR), baza głodzi okno kontekstowe z krytycznych informacji relacyjnych (kamieni milowych). Baza danych staje się "cmentarzem".

ANIMA, działająca na produkcji (myastra.pl) od marca 2026, to architektoniczny framework zbudowany na filozofii **Pamięci Suwerennej**: system, który automatycznie zarządza swoim kontekstem poprzez inżynierię analizującą logowania własnych trafień.

### 1. Data Distillation i Ekstrakcja Semantyczna
Zamiast wrzucać do bazy surowe wypowiedzi, każda wiadomość klienta przechodzi przez *SemanticExtractor*. Używając modeli typu `sentence-transformers` (klasyfikacja zero-shot), intencje dzielone są na kilkadziesiąt wspieranych subtypów bazujących na encjach typu: `EMOTION`, `FACT`, `MILESTONE`, `DATE`. `MemoryEnricher` ocenia wagę (1-10/10) i przypisuje tagi czasu. System zapisuje więc *tylko* syntetyzowaną z wiedzy abstrakcję twardych faktów bez bezużytecznego szumu po upływie terminu de-duplikacji. 

### 2. Suwerenność i Cykl Życia Wspomnień
Zamiast budować na stałej bazie wektorowej budującej amnezję przez nieskończony rozrost:
*   **Supersede Logic i Per-Type Decay**: Emocje i ulotne preferencje są nietrwałe i zdefiniowane logiką nadpisywania. Silnik wywołuje `delete_by_entity_subtype` przed wgraniem nowego faktu dla np. `['EMOTION', 'tired']`.
*   **Hybrydowy FactStore (Exact Lookup vs Similarity)**: Użycie samego ChromaDB nie gwarantuje wydobycia precyzyjnych i konkretnych faktów. Anima wdraża dual-layer: dla dedykowanych faktów/dat o miodach relacyjnych zaimplementowano SQLite FactStore z zapytaniami exact-match oraz hashami dla unikalnych ID (SHA256 z type:subtype) w celu nadpisywania logiki update/upsert (gwarancja priorytetu bez udziału ślepego similarity scoring).

### 3. Komponowanie 3-kanałowe bez kolizji wag
Zamiast prostej logiki zapytań o najwyższym kosinusie, kontekst montowany jest z potrójnej warstwy architektonicznej nie wchodzącej w wzajemne kolizje punktacji (hybrid adaptive ranker + boost multipliers): 
1.  **Guaranteed Milestone Channel**: Kluczowe dla tożsamości zdarzenia o randze 10 ("kamienie milowe") ignorują karę Jaccard MMR podczas de-duplikacji punktacji similarity, wymuszając w sposób stały iniekcję krytycznych relacyjnych wyczerpywań gwarantowanego progu minimum ≥1.0. W ten sposób AI zawsze wie "kim jesteśmy" nawet jeżeli nie wyszuka tego na etapie analizowania bazy wektorów zapytań.
2.  **Temporal Window Filter (RAW Frame)**: Cross-sesyjne surowe wiadomości (bufor z ostatnich 48h i stały Twardy Cut-Off) zakotwiczają AI w teraźniejszości operacyjnej.
3.  **Adaptive Similarity Reranker Score**: Wynik RAG ewoluuje jako wielomian z wagami dostrajanymi dla natury encji pod typ query, oparty na analizie testowej: `final_score = 0.25*importance + 0.15*recency + 0.60*similarity_score + keyword_boost`. 

### 4. Dynamic Context Tuning i Multi-Persona (Echo-Loop Guard)
System dostarczono i rozwinięto we frameworku natywnym dla wielu modeli wirtualnego współistnienia i interakcji z jedną instancją czatu:
*   **Multi-Persona Anti-Sync (Wspólny Pokój / Etap 0-2)**: Zapobiegłem załamywaniu się Gemini API (podwójnym turo "model") i homogenizowaniu ról wielu person rozwiązaniem Signal-based ordering, zakazem "do-not-repeat", twardym strip-persona w logikach injectów i flagowaniu CrossTalk pomiędzy odpowiedziami dwukierunkowej instancji.
*   **Echo-Loop Guard**: Implementacja zasady zapobiegającej odczytaniu przez mechanizm RAG "rozmowy AI między sobą" lub "jej o użytkowniku" jako wygenerowanych faktów pochodzących od użytkownika per test logów testów R&D zapobiega zatruciom RAG-a sememantycznego echa błędnie klasyfikowanego odczytu.

*Technical Stack: ChromaDB, Python (Vector & Semantic Core), Sentence Transformers, SQLite Exact Lookup, Gemini 2.5 AI, systemd / VPS Deployment Pipeline.*