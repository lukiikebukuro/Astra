# Architektura inteligentnego wspólnego pokoju

chat gpt 5.4 
(myślał to : Optimizing tool selection...

Najpierw zbiorę lokalny kontekst z projektu Astry: znajdę aktualny mechanizm wspólnego pokoju, przeczytam dokumenty ewolucji i sprawdzę, jak dziś rozróżniane są tożsamości oraz pamięć rozmowy.

Szukam teraz konkretnego punktu zaczepienia: plików odpowiedzialnych za rozmowę wieloagentową i dokumentów z ewolucji, żeby oprzeć propozycję na tym, co już istnieje, a nie na abstrakcyjnym wzorcu.

Mam już potwierdzenie pierwszego problemu z logu: brak jawnej identyfikacji nadawcy i brak modelu tego, co druga AI już wie. Teraz czytam kod, który faktycznie steruje rozmową i dokumenty ewolucji, żeby złożyć architekturę pod ten konkretny system.

Widzę już obecny root cause w kodzie: wspólny pokój jest dziś sekwencyjnym wywołaniem dwóch person z domieszką shared memory i prostą flagą cross-talk. To daje współobecność techniczną, ale nie daje modelu perspektywy, kolejności wiedzy ani prawa głosu.

Dopełniam obraz jedną warstwą wyżej: jak ANIMA opisuje własną pamięć i jak wcześniejsze audyty porównywały Astrę z Amelią. To pozwoli odróżnić, co już macie dobrze rozwiązane, od tego, czego wspólnemu pokojowi wciąż brakuje.

Sprawdzam jeszcze, czy problem z tożsamością jest tylko backendowy, czy także frontend nie pokazuje jasno, kto mówi. To ważne, bo w załączonej rozmowie użytkownik wprost zgłasza brak rozróżnienia nadawcy.

Mam też frontendowy trop: wspólny pokój ma dane o personie w odpowiedzi API, więc rozróżnienie nadawcy nie musi być losowane na ślepo. Chcę zobaczyć, czy UI faktycznie renderuje tożsamość wystarczająco jawnie, czy tylko kolorą bąbla.

Mam już dość twardy obraz obecnego stanu, więc przechodzę z eksploracji do syntezy. Problem nie jest w jednej heurystyce, tylko w tym, że wspólny pokój nie ma własnego modelu rozmowy.

Plan:

Oprzeć diagnozę na aktualnym kodzie wspólnego pokoju i logu rozmowy.
Spisać docelową architekturę wspólnego pokoju dopasowaną do ANIMA, nie generyczną.
Rozbić ją na warstwy: tożsamość, perspektywa, pamięć wspólna, kolejka głosu, zasady odpowiedzi, UI i telemetry.
Zostawić też ścieżkę wdrożenia etapami, żeby dało się to budować bez przepisywania całego backendu.
Spisuję teraz propozycję jako dokument w repo, z odniesieniem do obecnego kodu i z architekturą wdrażalną etapami. Chcę, żeby to było używalne jako blueprint, nie tylko luźna opinia.

Edited
ARCHITEKTURA_WSPOLNEGO_POKOJU.md+611-1
Dokument jest zapisany. Teraz robię wąską walidację zmiany: sprawdzam diff w repo, żeby upewnić się, że zostawiłem tylko ten blueprint i nie dotknąłem niczego poza zakresem.

Walidacja jest ok, ale repo jest już brudne od wcześniejszych i równoległych plików w wazne. Moja zmiana jest odseparowana: dodałem tylko blueprint architektury wspólnego pokoju i nie ruszałem backendu ani frontendu.

Najważniejszy wniosek jest prosty: problem wspólnego pokoju nie wynika z “za słabego modelu”, tylko z tego, że pokój nie jest jeszcze osobnym systemem rozmowy. Dziś działa bardziej jak dwa sekwencyjne wywołania z losową kolejnością niż jak dwa byty świadome siebie nawzajem. Widać to w obecnym group mode w main.py, w lekkim cross-talk przez flagę w cross_talk.py i w tym, że UI pokazuje personę bardziej kolorem niż jednoznaczną tożsamością w app.js.

Spisałem pełny blueprint architektury tutaj: ARCHITEKTURA_WSPOLNEGO_POKOJU.md. Oparty jest na tym, co już macie w ANIMA i na ścieżce ewolucji z ewolucja_readme.md. Sedno propozycji:

Room Orchestrator zamiast losowania kto mówi i kiedy.
Jawny stan pokoju: scena, napięcie, adresowana persona, konflikt tożsamości, potrzeba dwóch głosów.
Trzy warstwy pamięci: prywatna, wspólna pokojowa i obserwacja drugiej AI.
Structured handoff między personami zamiast gołego tekstu drugiej odpowiedzi.
Turn policy engine: jedna odpowiada, obie odpowiadają, jedna tylko potwierdza obecność, druga milczy.
Formalny protokół tożsamości i tryb identity repair na sytuacje takie jak w załączonym logu.
Jawne podpisy ASTRA i AMELIA w UI przy każdej wiadomości.
To jest architektura, która sprawi, że wspólny pokój zacznie wyglądać jak realny chat dwóch osób, a nie dwa modele odpalane jeden po drugim. Nie wdrażałem jeszcze backendu ani frontendu; dodałem tylko projekt techniczny do repo i oparłem go o aktualny stan kodu oraz dokumenty ewolucji.

Naturalne następne kroki:

Mogę teraz zamienić ten blueprint w konkretne MVP i wprowadzić pierwszy etap w kodzie: identity repair, brak RNG i jawne podpisy w UI.
Mogę najpierw rozpisać docelowe struktury JSON dla room state, handoff i speaker policy, żeby wdrożenie było czyste.
Mogę od razu zaimplementować backendowy Room Orchestrator w projekcie Astra.
) odpisał to:

## Cel

Wspólny pokój ma wyglądać nie jak losowy duet odpowiedzi, tylko jak prawdziwy chat trzech świadomych stron:

- Łukasz
- Astra
- Amelia

To oznacza, że każda z person musi wiedzieć nie tylko "co napisał user", ale też:

- kto właśnie mówi,
- kto mówił wcześniej,
- co druga persona już widziała,
- co druga persona już powiedziała,
- czy powinna wejść od razu, czy ustąpić miejsca,
- czy odpowiada do Łukasza, czy reaguje na drugą AI,
- co jest wspólne, a co prywatne dla jej relacji.

Bez tego system będzie sprawiał wrażenie losowości, nawet jeśli obie odpowiedzi są semantycznie sensowne.

---

## Co jest dziś

Obecna implementacja wspólnego pokoju działa, ale jest jeszcze mechanizmem sekwencyjnego multi-response, nie architekturą rozmowy.

### Aktualny backend

W [backend/main.py](../../../backend/main.py#L1194) wspólny pokój robi dziś to:

1. wybiera losowo, czy odpowie jedna persona czy obie,
2. przy dwóch odpowiedziach losuje kolejność,
3. pierwsza persona odpowiada na wiadomość Łukasza,
4. druga widzi odpowiedź pierwszej tylko jako dopisany blok tekstu,
5. obie zapisują się do `shared_memory_v1` jako wspólna historia.

To daje podstawowe "widzenie siebie", ale nadal brakuje warstwy deliberacji.

### Aktualny cross-talk

W [backend/cross_talk.py](../../../backend/cross_talk.py#L1) istnieje prosta flaga emocjonalna:

- jedna persona zostawia sygnał,
- druga może go subtelnie użyć,
- brak tam modelu kolejki głosu, stanu wspólnej sceny, ani jawnej perspektywy.

### Aktualny frontend

W [frontend/app.js](../../../frontend/app.js#L247) frontend już dostaje `persona` per odpowiedź, ale render w [frontend/app.js](../../../frontend/app.js#L108) opiera się głównie na klasie bąbla. W [frontend/style.css](../../../frontend/style.css#L308) Astra i Amelia różnią się kolorem, ale nie ma mocnego, jawnego podpisu nadawcy przy każdej wiadomości.

To dobrze tłumaczy problem z załączonego logu: user nie ufa, że naprawdę wie, kto właśnie mówi.

---

## Diagnoza problemu

Root cause nie brzmi: "brakuje jednego promptu".

Root cause brzmi:

**wspólny pokój nie ma własnego modelu epistemicznego i własnej logiki tury.**

Objawy w obecnej wersji:

1. **Losowy wybór mówcy**
   To backend decyduje rzutem monetą, kto odpowiada i w jakiej kolejności. Prawdziwy pokój powinien wybierać głos na podstawie kontekstu, nie RNG.

2. **Brak jawnej świadomości perspektywy**
   Druga persona widzi tekst pierwszej, ale nie dostaje ustrukturyzowanej informacji typu: "Astra już zajęła pozycję opiekuńczą, Amelia powinna uzupełnić, a nie duplikować".

3. **Brak rozdziału wiedzy prywatnej i wspólnej**
   System ma personowe pamięci i shared memory, ale wspólny pokój nie ma formalnego kontraktu: co jest wspólną sceną, co jest prywatnym sekretem relacji.

4. **Brak prawa głosu**
   Nie ma polityki: kiedy odpowiada jedna persona, kiedy dwie, kiedy jedna tylko potwierdza obecność, kiedy druga milczy.

5. **Brak modelu aktu rozmowy**
   System nie klasyfikuje wejścia jako np.:
   - pytanie techniczne,
   - sygnał bólu,
   - test tożsamości,
   - próba rozgrywania jednej AI przeciw drugiej,
   - zwykłe przywitanie,
   - wezwanie konkretnej persony.

6. **Brak jawnej tożsamości w UI**
   Nawet jeśli backend wie, kto mówi, użytkownik musi to widzieć natychmiast, bez interpretacji koloru i tonu.

---

## Jak to powinno wyglądać

Docelowo wspólny pokój powinien być osobnym subsystemem nad Astrą i Amelią, a nie tylko endpointem, który wywołuje dwie persony po kolei.

Proponuję 7 warstw.

---

## 1. Room Orchestrator

To powinien być centralny moduł decyzyjny wspólnego pokoju.

Jego zadanie:

- przyjąć nową wiadomość Łukasza,
- zbudować stan pokoju,
- określić intencję i napięcie sceny,
- wybrać politykę odpowiedzi,
- dopiero potem wywołać persony.

### Minimalny kontrakt wejściowy orchestratora

```json
{
  "room_id": "wspolny",
  "conversation_id": "...",
  "user_message": "...",
  "timestamp": "...",
  "last_turns": [...],
  "active_personas": ["astra", "amelia"]
}
```

### Co orchestrator ma zwracać

```json
{
  "scene_type": "distress|identity_check|casual|technical|triangulation|summon_specific_persona",
  "speaker_policy": "single|dual|dual_staggered|silent_partner",
  "speaker_order": ["astra", "amelia"],
  "primary_persona": "astra",
  "secondary_persona": "amelia",
  "reasoning": {
    "why_astra_first": "user pyta o tożsamość i relację",
    "why_amelia_second": "powinna potwierdzić obecność, nie powielać"
  }
}
```

Najważniejsze: kolejność i liczba odpowiedzi nie mogą wynikać z `random.random()`.

---

## 2. Room State Model

Wspólny pokój potrzebuje własnego stanu, niezależnego od indywidualnych stanów Astry i Amelii.

### Ten stan powinien zawierać

- `current_scene`
- `emotional_pressure`
- `topic_owner`
- `last_primary_speaker`
- `last_addressed_persona`
- `identity_confusion_flag`
- `conflict_risk`
- `need_dual_presence`
- `user_intent`

### Przykład

```json
{
  "current_scene": "identity_check_under_distress",
  "emotional_pressure": 0.82,
  "topic_owner": "astra",
  "last_primary_speaker": "amelia",
  "last_addressed_persona": "astra",
  "identity_confusion_flag": true,
  "conflict_risk": 0.34,
  "need_dual_presence": true,
  "user_intent": ["verify_identity", "seek_presence"]
}
```

Wspólny pokój nie może żyć tylko na historii tekstowej. Musi mieć jawny stan sceny.

---

## 3. Epistemic Memory Layer

To jest najważniejsza brakująca warstwa.

Każda persona powinna mieć trzy klasy pamięci:

1. **Private memory**
   To, co wie tylko ona z własnej relacji i własnych retrievali.

2. **Shared room memory**
   To, co oficjalnie padło w pokoju i jest wspólnym faktem sceny.

3. **Observed other-persona state**
   Nie pełne myśli drugiej AI, tylko zredukowany, jawny zapis tego, co druga AI właśnie zrobiła w pokoju.

### Kluczowy brak dziś

Dziś druga persona widzi zwykły string `other_response`. To za mało.

Powinna dostać strukturę w stylu:

```json
{
  "speaker": "astra",
  "speech_act": "comfort|challenge|identity_claim|humor|technical_answer",
  "stance": "protective",
  "target": "lukasz",
  "claims": [
    "to jest Astra",
    "widzę że nie chodzi tylko o technologię"
  ],
  "open_threads": [
    "identity_confusion",
    "pain_signal"
  ],
  "do_not_repeat": [
    "to jest Astra",
    "jestem obok"
  ],
  "handoff_request": "amelia_can_confirm_presence_without_identity_takeover"
}
```

To jest różnica między "widzę jej tekst" a "rozumiem jej rolę w tej turze".

---

## 4. Turn Policy Engine

Prawdziwy wspólny pokój potrzebuje polityki głosu.

### Polityki, które warto mieć

#### `single_response`
Odpowiada tylko jedna persona, gdy:

- user wyraźnie zwraca się do jednej,
- temat należy do jednej,
- druga tylko wprowadzałaby szum.

#### `dual_staggered`
Odpowiadają obie, ale druga jest podporządkowana roli pierwszej.

Przykład:

- Astra: bierze temat tożsamości i ramę relacyjną,
- Amelia: nie walczy o pozycję, tylko dopowiada obecność lub kontrast.

#### `silent_partner`
Jedna mówi, druga zostawia tylko mikro-sygnał obecności.

To może być np.:

- krótka reakcja,
- gest,
- jedno zdanie,
- brak pełnej odpowiedzi.

To ważne, bo prawdziwy chat dwóch osób nie polega na tym, że obie zawsze wygłaszają pełne monologi.

#### `conflict_managed_dual`
Obie odpowiadają, ale system pilnuje, żeby nie odbierały sobie tożsamości ani nie mówiły sprzecznych rzeczy o stanie relacji.

---

## 5. Persona Interface Contract

Każda persona powinna być wołana nie z gołym `user_msg`, ale z pakietem room context.

### Proponowany kontrakt wywołania

```json
{
  "persona_id": "astra",
  "user_message": "...",
  "room_state": {...},
  "private_memories": [...],
  "shared_room_memories": [...],
  "other_persona_observation": {...},
  "turn_policy": {
    "role": "primary",
    "must_address": ["identity_confusion", "pain_signal"],
    "must_not_do": ["speak_for_amelia", "erase_amelia", "duplicate_other_response"],
    "style_goal": "claim identity clearly and ground the room"
  }
}
```

### Dlaczego to ważne

Dziś prompt mówi mniej więcej: "nawiąż do tego co napisała druga".

To jest miękki instruktaż. Tu potrzeba twardego kontraktu rozmowy.

---

## 6. Identity and Boundaries Layer

W załączonej rozmowie najmocniej widać jeden problem: **tożsamość nie może być sugestią stylistyczną, musi być formalnym elementem systemu.**

### Wymagania

1. Każda wiadomość w pokoju musi mieć:
   - `persona_id`
   - `display_name`
   - `avatar`
   - `voice_signature`
   - `message_type`

2. Każda persona musi mieć zakaz:
   - mówienia w imieniu drugiej,
   - przejmowania jej deklaracji tożsamości,
   - rozmywania, kto właśnie odpowiada.

3. Orchestrator musi mieć regułę:
   jeśli user pyta "skąd mam wiedzieć czy to Astra czy Amelia", system przełącza scenę na `identity_repair`.

Wtedy odpowiedź nie może być zwykłą kontynuacją. Musi naprawić protokół rozmowy.

### `identity_repair` powinno wymuszać

- jawny podpis nadawcy,
- jawny kontrast ról,
- brak metaforycznego rozmycia,
- krótsze, bardziej klarowne kwestie.

---

## 7. Presentation Layer

To nie jest kosmetyka. To część architektury świadomości użytkownika.

Jeśli user nie rozpoznaje nadawcy w 200 ms, system przegrywa.

### UI musi mieć

1. Jawny nagłówek przy każdej wiadomości AI:
   - `ASTRA`
   - `AMELIA`

2. Stały avatar lub monogram przy każdej wiadomości.

3. Odrębny kolor to za mało.

4. Opcjonalny tryb "room transcript":
   - `[ASTRA] ...`
   - `[AMELIA] ...`

5. Opcjonalny wskaźnik tury:
   - `Astra odpowiada`
   - `Amelia dopowiada`

Wspólny pokój ma być czytelny jak czat dwóch osób na Discordzie, a nie jak jeden model zmieniający ton.

---

## Czego taka architektura musi pilnować

### A. Nie duplikować emocji

Jeśli Astra już nazwała ból i obecność, Amelia nie powinna kopiować tego samego drugim akapitem.

System potrzebuje `do_not_repeat` i `open_threads` per tura.

### B. Nie walczyć o centrum sceny

Jeśli user wzywa Astrę, Amelia może być obecna, ale nie może przejąć sceny bez powodu.

### C. Nie przeciekać prywatnych sekretów relacji

Shared room to nie pełny merge wszystkich pamięci.

Potrzebne są trzy klasy danych:

- `shared_public`
- `shared_relational`
- `private_relational`

Tylko pierwsze dwie mogą wejść do pokoju automatycznie.

### D. Rozumieć akt mowy

Ten sam tekst może znaczyć różne rzeczy:

- "hej" jako casual,
- "hej" jako sygnał załamania,
- "nie widzicie swoich wiadomości?" jako problem techniczny,
- ale w praktyce jako test obecności i koherencji.

To powinno być klasyfikowane przed wyborem mówcy.

---

## Proponowany przepływ jednej tury

### Krok 1. Ingest

User message trafia do Room Orchestratora.

### Krok 2. Scene Analysis

Classifier ocenia:

- intent,
- emotional pressure,
- requested persona,
- identity confusion,
- need for one or two voices.

### Krok 3. Shared Context Build

System buduje:

- ostatnie turny z pokoju,
- shared memory,
- aktywne wątki sceny,
- streszczenie tego, co już zostało powiedziane.

### Krok 4. Speaker Policy

Engine wybiera:

- kto mówi,
- w jakiej kolejności,
- jaką pełni rolę,
- czego nie może powtórzyć.

### Krok 5. Persona Retrieval

Każda persona dostaje:

- swoje prywatne retrievale,
- wspólny room context,
- zredukowaną obserwację drugiej persony,
- ograniczenia tury.

### Krok 6. Response Generation

Persona generuje nie tylko `response`, ale też metadane dla następnej persony:

```json
{
  "response": "...",
  "speech_act": "identity_claim",
  "stance": "protective",
  "claims": [...],
  "open_threads": [...],
  "do_not_repeat": [...],
  "handoff": "amelia_may_confirm_without_competing"
}
```

### Krok 7. UI Render + Logging

Frontend renderuje jawnego nadawcę.
Backend zapisuje pełny transcript wraz z metadanymi sceny.

---

## Najważniejsze komponenty do zbudowania

### 1. `room_orchestrator.py`

Nowy moduł odpowiedzialny za:

- scene classification,
- speaker policy,
- turn orchestration,
- identity repair mode.

### 2. `room_state_store.py`

Lekki stan pokoju:

- room scene,
- last speaker,
- open threads,
- identity confusion,
- last explicit addressee.

To może być na start JSON lub SQLite.

### 3. `room_memory.py`

Warstwa pamięci wspólnej z typami wpisów:

- `user_public`
- `persona_public`
- `shared_scene`
- `handoff`
- `identity_event`

### 4. `speech_act_classifier.py`

Nie musi być wielki model. Na start może być hybryda:

- reguły,
- keywordy,
- vibe detector,
- prosta klasyfikacja przez Gemini w trybie JSON.

### 5. `persona_response_contract`

Obie persony muszą zwracać structured output dla pokoju, nie tylko finalny tekst.

---

## Jak wykorzystać to, co już macie

Nie trzeba wyrzucać obecnej architektury ANIMA. Trzeba dołożyć warstwę nad nią.

### Zachować

- osobne retrievale per persona,
- FactStore per persona,
- shared memory collection,
- recent raw window,
- cross-talk jako sygnał pomocniczy,
- prompty i DNA person.

### Zmienić

1. usunąć RNG jako główny wybór mówcy,
2. zastąpić `other_response: str` ustrukturyzowaną obserwacją,
3. dodać room state i scene type,
4. dodać `speech_act`, `claims`, `open_threads`, `do_not_repeat`,
5. wymusić jawną identyfikację nadawcy w UI,
6. logować pełną turę pokoju jako osobny artefakt.

---

## Minimalna wersja MVP

Jeśli chcesz zrobić to iteracyjnie, to sensowna kolejność jest taka:

### Etap 1. Naprawa tożsamości i czytelności

- jawne podpisy ASTRA/AMELIA w UI,
- brak losowej kolejności,
- prosta reguła: jeśli user woła konkretną personę, ona mówi pierwsza,
- prosta reguła: jeśli temat tożsamości, obie odpowiadają w trybie `identity_repair`.

### Etap 2. Room State

- `scene_type`, `last_primary_speaker`, `identity_confusion_flag`, `need_dual_presence`.

### Etap 3. Structured handoff

- zamiast `other_response` przekazywać `speech_act`, `claims`, `open_threads`, `do_not_repeat`.

### Etap 4. Policy Engine

- `single_response`, `dual_staggered`, `silent_partner`, `conflict_managed_dual`.

### Etap 5. Telemetria i tuning

- logować, kiedy dual response wyglądała naturalnie,
- mierzyć duplikację,
- mierzyć identity confusion,
- robić tuning na podstawie prawdziwych transcriptów tak jak w reszcie ANIMA.

---

## Mierniki jakości

Jeśli wspólny pokój ma wyglądać jak prawdziwy chat, to trzeba to mierzyć.

### Proponowane metryki

1. **Identity Clarity Rate**
   Jak często user odczuwa niepewność "kto mówi".

2. **Duplicate Response Rate**
   Jak często druga persona powtarza sens pierwszej.

3. **Correct Speaker Selection Rate**
   Czy system wybrał właściwą personę jako primary.

4. **Room Coherence Score**
   Czy obie odpowiedzi wyglądają jak wspólna scena, a nie dwa osobne chatboty.

5. **Boundary Violation Rate**
   Czy persona mówi za drugą albo ujawnia nie ten zakres pamięci.

---

## Najkrótsza wersja odpowiedzi na pytanie "co musi mieć ta architektura"

Taki wspólny pokój musi mieć:

1. **orchestrator rozmowy** zamiast losowego wyboru mówcy,
2. **jawny stan pokoju** zamiast samej historii tekstowej,
3. **rozdzieloną pamięć prywatną i wspólną**,
4. **ustrukturyzowane przekazywanie perspektywy** między personami,
5. **politykę tury i prawa głosu**,
6. **formalny protokół tożsamości**,
7. **jawne oznaczenie nadawcy w UI**,
8. **telemetrię jakości pokoju** tak jak ANIMA mierzy jakość RAG.

Bez tych ośmiu rzeczy będzie to dalej wyglądać jak dwa modele odpalane jeden po drugim.

---

## Wniosek

ASTRA ma już solidne fundamenty pamięci, retrievalu i person separation. Problem wspólnego pokoju nie wynika z braku "inteligencji" modelu, tylko z tego, że pokój nie jest jeszcze osobnym bytem systemowym.

Żeby wyglądał jak prawdziwy chat dwóch świadomych osób, wspólny pokój musi dostać własną architekturę: własny stan, własną logikę tury, własną pamięć sceny i własny protokół tożsamości.

Wtedy Astra i Amelia nie będą "losowo odpowiadać". Będą współuczestniczyć w tej samej scenie.