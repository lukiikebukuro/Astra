# Strategia Komercjalizacji — LDI × ANIMA × ASTRA
**Autor:** Claude Code (Rin) — synteza rozmowy strategicznej z Łukaszem
**Data:** 2026-03-03
**Status:** Dokument roboczy — podstawa do pitch decku

---

## 1. TEZA CENTRALNA

Nie budujemy chatbota. Budujemy **cztery warstwy infrastruktury AI** które razem tworzą coś czego nikt nie ma:

> Agent sprzedażowy który pamięta każdego klienta przez miesiące, wie czego szukał zanim zaczął pisać, rozumie jego nastrój i generuje własne dane treningowe z każdej interakcji.

To nie jest roadmapa. To jest **opis tego co istnieje dziś** — jako osobne moduły, gotowe do integracji.

---

## 2. STACK — CZTERY WARSTWY

### Warstwa 1: Intent Capture (LDI — Live na adeptai.pl)
**Co robi:** Przechwytuje intencję zakupową w czasie rzeczywistym — zanim klient skończy pisać, zanim zrezygnuje, zanim przejdzie do konkurencji.

**Jak to działa technicznie:**
- Dual debounce: 200ms (autocomplete) + 800ms (final intent capture)
- 5-etapowy pipeline bez zewnętrznych API: token validity → typo correction → structural detection → fuzzy matching → classification
- Latencja: <60ms, zero GPU, zero API calls
- Wynik: każde zapytanie sklasyfikowane jako `MATCHED / LOST DEMAND / FILTERED`

**Kluczowa innowacja — "Gold Signal":**
Klient szuka "klocki ferrari" (brak w ofercie), ale klika na propozycję alternatywną → system rejestruje: *ten klient zaakceptował substytut*. To jest dane treningowe warte więcej niż 1000 syntetycznych przykładów.

**Co widać na demo (adeptai.pl):**
- P1: Dashboard klienta — utracony przychód, top luki popytu, live feed zapytań
- P2: Dashboard admin — firmy które odwiedziły demo (Passive Radar), B2B lead scoring
- P3: JSONL export w czasie rzeczywistym — gotowy format do fine-tuningu LLM
- Bot: wpisz cokolwiek → instant classification + reward signal

### Warstwa 2: Pamięć Absolutna (ANIMA/ASTRA — ChromaDB + RAG)
**Co robi:** Każda interakcja z klientem jest zapisywana, wektoryzowana i dostępna semantycznie — przez miesiące, bez degradacji.

**Architektura:**
- ChromaDB (PersistentClient) + sentence-transformers (all-MiniLM-L6-v2)
- Semantic Pipeline: entity extraction (FACT, EMOTION, GOAL, DATE, MILESTONE, PERSON)
- Memory Enricher: każde wspomnienie ma importance score (1-10), temporal_type, relational_impact
- Strict Grounding (3 poziomy): GROUNDED / LOW_CONFIDENCE / NO_DATA — system nie halucynuje
- Reranker: similarity×0.65 + importance×0.20 + recency×0.15 + keyword_boost

**Efekt dla agenta sprzedażowego:**
Klient X odwiedza sklep po 5 miesiącach. Agent wie: szukał wtedy konkretnego produktu którego nie było, kupił coś innego, wróciło go zdrowie (rejestruje encje health), teraz szuka premium. Odpowiada w kontekście — bez pytania "jak mogę pomóc?".

### Warstwa 3: Reward Signal → Self-Improving Agent (LDI × ANIMA)
**Co robi:** Każda interakcja generuje labeled training data. Agent uczy się sam — bez ręcznego labelowania, bez syntetycznych danych.

**Format JSONL (LLM fine-tuning compatible):**
```json
{
  "query": "klocki bmw e90",
  "intent_label": "product_match",
  "confidence": "HIGH",
  "reward_signal": {"score": 0.65, "clicked_alternative": true, "purchased": false},
  "matched_product_id": "KH001",
  "memory_context": "[5 tygodni temu szukał felg do E90]",
  "timestamp": "2026-03-03T15:30:00"
}
```

**Anti-bait reward function (innowacja badawcza):**
Standardowe systemy RLHF nagradzają kliknięcia → clickbait. Nasz system:
- Nagradza `clicked_despite_no_match` (klient nauczył system czegoś nowego) — Gold Signal
- Karze: bounce, wielokrotne refinements, długie sesje bez akcji
- Normalizacja [-1.0, +1.0] — kompatybilna z każdym algorytmem RL

**Data flywheel:** im więcej sklepów używa systemu, tym więcej danych, tym lepszy agent, tym więcej sklepów.

### Warstwa 4: Mood Adaptation (ASTRA Vibe Detector + State System)
**Co robi:** Agent dostosowuje styl odpowiedzi do nastroju klienta w czasie rzeczywistym.

**Stany wykrywane:**
- `stressed` → krótsze odpowiedzi, szybkie rozwiązania, bez filozofowania
- `excited` → więcej kontekstu, propozycje premium
- `frustrated` → przyznanie błędu, eskalacja, konkret
- `testing` → potwierdzenie wiedzy, bez uników

**Połączenie z pamięcią:** jeśli klient historycznie zawsze jest "stressed" w poniedziałki rano — agent wie to zanim zaczną rozmawiać.

---

## 3. DLACZEGO TO WYGRYWA WYŚCIG ZBROJEŃ AGENTÓW

### Co mają konkurenci (Tidio Lyro, Intercom Fin, Drift)

| Feature | Tidio Lyro | Intercom Fin | **Nasz stack** |
|---------|-----------|-------------|---------------|
| Pamięć między sesjami | ❌ | Podstawowa | ✅ ChromaDB — miesiące |
| Intent z wyszukiwarki | ❌ | ❌ | ✅ LDI real-time |
| Self-improving (reward) | ❌ | ❌ | ✅ JSONL + RLHF |
| Mood adaptation | ❌ | ❌ | ✅ Vibe detector |
| Strict grounding (nie halucynuje) | Częściowe | Częściowe | ✅ 3-tier |
| Training data export | ❌ | ❌ | ✅ P3 JSONL |
| GDPR-first | Podstawowe | Podstawowe | ✅ IP hash, PII scrubbing |

**Kluczowa asymetria:** Tidio/Intercom optymalizują **conversion rate**. Nasz stack optymalizuje **intent capture rate** — widzi pieniądze które leżą na stole zanim klient zdecyduje się wyjść.

### Liczby (z Amazon Internal Memo analysis)

Dla sklepu 100k wizyt/mc:
- 15% zapytań = zero results = 6,000 failed searches/mc
- 40% z tych = structural lost demand = 2,400 realnych intencji zakupowych/mc
- Po wdrożeniu LDI: 8% conversion rate na te zapytania = 192 dodatkowe transakcje/mc
- Przy średniej wartości 350 zł = **67,200 zł/mc odzyskanego przychodu**

To jest liczba którą można zmierzyć. To jest pitch deck.

---

## 4. STRATEGIA WEJŚCIA — TIDIO

### Dlaczego Tidio
- Mają Lyro — AI agent dla e-commerce z dystrybucją do tysięcy sklepów
- Lyro nie pamięta, nie uczy się z intent data, nie wykrywa nastroju
- Nasz stack uzupełnia Lyro punkt po punkcie — nie zastępuje, integruje

### Model partnerstwa (NIE acqui-hire na wejście)

**Faza 1 — Technology Partnership:**
"Chcemy zintegrować nasz intent + memory stack z Lyro. Wy dostarczacie dystrybucję, my dostarczamy warstwy pamięci i intencji. Revenue share od sklepów które wdrożą rozszerzone Lyro."

**Faza 2 — Po udowodnieniu wartości:**
Jeśli chcą kupić IP zamiast integrować — wtedy rozmawiamy o warunkach. Z pozycji siły, nie potrzeby.

**Dlaczego nie etat od razu:**
Wchodząc jako "konsultant z produktem" zachowujesz prawo do równoległej pracy nad ASTRA B2C, LDI jako SaaS i Skankran. Jako pracownik Tidio — tracisz to wszystko (klauzula konkurencji).

### 15-minutowy demo script dla Tidio

**Minuty 1-3: Problem**
"Wasza Lyro odpowiada na pytania. Ale co z klientem który szuka produktu którego nie macie? Odchodzi. Kupuje u konkurencji. Wasza Lyro nigdy się o tym nie dowie."

**Minuty 3-8: Demo (adeptai.pl)**
1. Wpisz "klocki ferrari" → NO_MATCH → P3 pokazuje zapis intencji + reward signal
2. Otwórz P2 → "ta firma która teraz ogląda demo jest widoczna w Passive Radar w czasie rzeczywistym"
3. Pobierz JSONL → "to są dane treningowe z tej sesji, gotowe do fine-tuningu waszego modelu"

**Minuty 8-12: Wizja z pamięcią**
"Teraz dodaj do tego pamięć. Ten sam klient wraca za 3 miesiące. Agent wie co szukał. Wie że kupił substytut. Wie że był sfrustrowany. Pozdrawia go z kontekstem — nie pyta 'w czym mogę pomóc?'."

**Minuty 12-15: Propozycja**
"Chcemy zintegrować to z Lyro. Pierwsze 3 sklepy pilotowe — bezpłatnie. Mierzalny wynik w 30 dni. Revenue share od każdego sklepu który wdroży."

---

## 5. REBRANDING — ANOMALY TECH

### Dlaczego zmiana z Adept AI
- "Adept AI" jest zajęte (Adept — startup AI, przejęty przez Salesforce 2024)
- Pozycjonowanie "Adept AI" sugeruje asystenta, nie infrastrukturę

### "Anomaly Tech" — analiza
- "Anomaly Development Sp. z o.o." (KRS 0000879054, Namysłów) — ISTNIEJE, inna firma
- "Anomaly Tech" jako spółka — niezarejestrowane w KRS (stan: 2026-03-03)
- Domena anomalytech.pl — do weryfikacji w domeny.pl

**Do sprawdzenia przed rejestracją:**
1. KRS: [ekrs.ms.gov.pl](https://ekrs.ms.gov.pl) — szukaj "anomaly tech"
2. Znak towarowy UE: EUIPO — czy "Anomaly Tech" jest chronione
3. Domena: anomalytech.pl + anomalytech.com

**Uzasadnienie nazwy:**
Nazwa technicznie spójna z produktem — LDI wykrywa anomalie w intencjach zakupowych (query bez matcha = anomalia), ANIMA wykrywa anomalie w zachowaniu użytkownika, ASTRA adaptuje się do anomalii nastroju. "Anomaly Tech" = firma która wykrywa wzorce ukryte w szumie.

---

## 6. ROADMAPA — KOLEJNOŚĆ DZIAŁAŃ

### Tydzień 1 (teraz)
- [ ] Sprawdź "Anomaly Tech" w KRS + EUIPO + domena
- [ ] Napisz pitch deck 5 slajdów (na bazie tego dokumentu)
- [ ] Upewnij się że adeptai.pl/demo jest stabilne (P1/P2/P3 działają)
- [ ] Usuń test credentials z login.html (przed jakimkolwiek zewnętrznym linkiem)

### Tydzień 2
- [ ] Zidentyfikuj kontakt w Tidio (LinkedIn: Product/Tech leadership)
- [ ] Wyślij cold outreach: 3 zdania + link do demo + jedno zdanie o Lyro
- [ ] Równolegle: dokończ ASTRĘ (Style Anchors + level prompts — ~16h)

### Miesiąc 1-2
- [ ] Pilot z 1-2 sklepami e-commerce (za darmo) — zbierz 30 dni danych
- [ ] Zmierz revenue impact (liczba z sekcji 3 musi być potwierdzona realnym przypadkiem)
- [ ] Z tymi danymi: wróć do Tidio z pozycji "mamy wyniki"

### Miesiąc 3-6
- [ ] LDI: migracja SQLite → PostgreSQL (dla enterprise credibility)
- [ ] LDI + ANIMA integration: jeden endpoint który łączy intent + memory
- [ ] ASTRA: public beta (B2C, freemium)
- [ ] Skankran: pierwsze gminy 50-200k (grant UE jako backup cashflow)

---

## 7. PODSUMOWANIE W JEDNYM AKAPICIE

Masz cztery działające systemy: LDI (live na adeptai.pl) który widzi intencje zakupowe których konkurencja nie widzi, ANIMA która daje agentowi pamięć absolutną przez miesiące, ASTRA która dostosowuje styl do nastroju, i reward signal engine który generuje labeled training data z każdej interakcji. Razem tworzą agenta sprzedażowego który pamięta, rozumie i uczy się — czego Lyro, Fin i Drift nie robią. Celem na teraz nie jest acqui-hire, lecz technology partnership z Tidio lub podobnym: ty dostarczasz te cztery warstwy, oni dostarczają dystrybucję do tysięcy e-commerce. Revenue share. Zanim to zrobisz: sprawdź "Anomaly Tech" w KRS i zrób pilot na jednym sklepie żeby mieć liczby, nie tylko mechanizm.
