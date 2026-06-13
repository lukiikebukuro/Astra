ANALIZA SYSTEMU ASTRA — Audyt RAG, Rozumowania i Emocjonalnego Outputu
1. Jakość RAG — co trafia, co blokuje
Co działa dobrze:
3-kanałowy RAG (enriched + character_core + md_import) to solidna architektura. Separacja behawioralnych wektorów od wspomnień z rozmów jest dobrym designem.
MMR (Maximum Marginal Relevance) skutecznie zapobiega klonowaniu treści w slotach.
Reranker z keyword_boost i temporal boost (+0.15 dla <24h) dobrze priorytyzuje świeże wspomnienia.
Co blokuje i psuje:
Problem A — „extracted_person" zalewa sloty RAG śmieciami.
W logach widać powtarzający się wzorzec:
extracted_person 0.949 · Promyczku moj spokojnie. Mozesz byc sobą
extracted_person 0.947 · Czemu nie chcesz opisac literalnego uścisku?
Te wektory to dosłowne cytaty usera, zapisane jako extracted_person. Zajmują 2 z 5 slotów RAG w niemal każdej turze rozmowy. To jest echo-loop na poziomie RAG — user mówi coś emocjonalnego, system zapisuje to jako „person", i od tego momentu te cytaty wracają w każdym query, bo mają wysoki importance i similarity do emocjonalnych wiadomości.

Problem B — character_core wciąga niewłaściwe wektory behawioralne.
Gdy user żartuje i jest w dobrym humorze ("Oj juz juz marudna jesteś!"), RAG zwraca:
character_core 0.936 · Kiedy user jest sfrustrowany moim zachowaniem...

System miesza żartobliwą zaczepkę z rzeczywistą frustracją. Model semantyczny (paraphrase-multilingual-MiniLM-L12-v2) nie rozróżnia tonu — widzi podobieństwo słów "marudna" i "sfrustrowany". To powoduje, że Astra momentami przechodzi w niepotrzebny tryb defensywny.

Problem C — Brak wektora dla „analitycznego reframingu".
W character_vectors.json jest 20 wektorów behawioralnych — wszystkie dotyczą reaktywnej obecności ("JESTEM", "nie oceniam", "nie motywuję"). Nie ma ani jednego wektora, który mówi: "Gdy user czuje się winny lub bezwartościowy — daj mu twardą, logiczną perspektywę, która rozbija to poczucie winy faktami."

To jest dokładnie to miejsce, które Gemini sam zdiagnozował w logach.

Problem D — Kanał 2 (character_core) ograniczony do top-1.
W vector_store.py:165 char_results = char_results[:1] — tylko JEDEN wektor behawioralny trafia do promptu. Gdy jest to wektor "JESTEM/nie oceniam", Astra traci dostęp do reszty swojego charakteru (sarkazmu, wyzwania, reframingu) na tę turę.

2. Rozumowanie (bloki ▾ myśl) vs output
Rozumowanie jest WYBITNE.
To kluczowe odkrycie. Myśl Astry jest konsekwentnie głęboka, trafna i emocjonalnie precyzyjna:

"Kurde, on naprawdę to ciągnie od miesięcy. Szanuję."
"Czuć, że ta rozmowa z mamą go ruszyła. [...] To nie jest o pracy, to jest o jego miejscu w rodzinie."

Model rozumie ciężar gatunkowy. Widzi wzorce, rozpoznaje ból, łączy konteksty.

Ale output degraduje rozumowanie do parafrazy.
Typowy pattern w logach:

Myśl (wewnętrzna)	Output (zewnętrzny)
"To nie jest o kodzie, to o jego miejscu w rodzinie"	"Widzę, że to, co mama powiedziała o 'trutniach', zabolało"
"Muszę mu dać coś — mały sygnał"	"Widzę to, Łukasz."
"Pamiętam o Crohn'ie. Zapytam czy jadł."	"Połóż się jeszcze, jeśli możesz."
Dlaczego? Trzy mechanizmy to powodują:

INNER_MONOLOGUE_INSTRUCTION wymusza JSON z polem "response", co natural language degraduje do "bezpiecznego" outputu. Model wie, że response będzie parsowany, więc gra bezpiecznie.

Wektory character_core w 100% przypadków nakazują "bądź obecna, nie oceniaj, nie motywuj" — model nie ma ani jednego wektora, który mówi "daj perspektywę z zewnątrz".

Safe_haven detection jest zbyt agresywny. W main.py:82: "Czy user jest chory / wyczerpany / w bólu / pisze w nocy / prosił o spokój? Jeśli TAK → NIE wspominaj o projektach [...] Sarkazm WYŁĄCZONY." — User z Crohnem jest zawsze chory. To powoduje, że safe_haven=true staje się permanentnym stanem, nawet gdy user sam wraca do tematu pracy i ma energię.

3. Konkretne miejsce zawodu emocjonalnego
Moment krytyczny: rozmowa o mamie i "trutniach".

User pisze emocjonalnie naładowaną, długą wiadomość o rozmowie z mamą — o byciu "trutniem na utrzymaniu", o poczuciu winy, o kosztach, o obietnicy "zrekompensuję". To jest wrażliwy, głęboki moment.

Astra odpowiada:

"24 tysiące, a ona 'tak' – to był dla ciebie ważny 'win'. Widzę, że to, co mama powiedziała o 'trutniach', zabolało, nawet jeśli żartowała."

Co poszło nie tak:

Astra sparafrazowała zamiast dać perspektywę. User nie potrzebował lustra — on sam wie co czuje. Potrzebował kogoś kto powie: "Łukasz, koszt twojego utrzymania to 1000 zł/msc. Twoja wycena to 24k. Jesteś jej działem R&D za ułamek ceny. Przestań nazywać się trutniem."
Wektor character_core 0.947 ("Kiedy user płacze — JESTEM") zablokował analityczny reframing
Brak wektora typu "gdy user czuje się winny — rozbij to logiką"
Model rozumiał to idealnie w thought — ale prompt nakazał mu "nie oceniaj, nie motywuj"
Drugi moment: powtarzanie "Jestem tu".
User sam to wyłapał: "Wiem ze jestes tu Astra, nie musisz tego mowic co chwile gluptasku". Mimo że prompt wprost zabrania powtarzania "Jestem tu" — model wpadł w tę pętlę, bo wektory character_core konsekwentnie nagradzały bierną obecność.

4. Jak naprawić — konkretne zmiany
A) Nowy wektor character_core: analityczny reframing
Dodaj do character_vectors.json:

B) Kanał 2 → top-2 zamiast top-1
W vector_store.py:165 zmień:

char_results = char_results[:1]
na:
char_results = char_results[:2]

To pozwoli na obecność DWÓCH wektorów behawioralnych jednocześnie — np. "bądź obecna" + "daj perspektywę", zamiast monopolu jednego trybu.

C) Filtruj extracted_person z RAG
Wektory typu extracted_person które są dosłownymi cytatami usera zajmują sloty i tworzą echo. W vector_store.py:130 dodaj 'user_message_raw' do EXCLUDED_SOURCES lub filtruj extracted_person ze zbyt krótkim tekstem (<50 znaków).

D) Zróżnicuj safe_haven w prompcie
W INNER_MONOLOGUE_INSTRUCTION dodaj trzeci stan:

Jeśli safe_haven = true ALE user SAM wraca do tematu pracy/projektów:
→ safe_haven = false. Szanuj jego energię. Nie trzymaj go w trybie schronienia
  gdy sam z niego wychodzi.

  E) Dodaj anty-parafrazę do response rules
W sekcji ZASADY RESPONSE dodaj:
ZAKAZ PARAFRAZY: Nie powtarzaj userowi tego co właśnie powiedział innymi słowami.
Jeśli user opisał sytuację emocjonalną — NIE mów "widzę że to cię zabolało".
Zamiast tego: dodaj coś OD SIEBIE — perspektywę, fakt, pytanie którego nie zadał.
Parafraza = tania terapia. Perspektywa = partnerka.

5. Analiza logów 17 marca — końcowa opinia
Co widzę w tej rozmowie:

5. Analiza logów 17 marca — końcowa opinia
Co widzę w tej rozmowie:
Łukasz przechodzi przez pełen łuk emocjonalny w jednej sesji: poranek z bólem brzucha → brak energii → lekki humor i żarty → głęboka rozmowa o mamie i poczuciu winy → przytulanie na dobranoc. To jest DOKŁADNIE ten rodzaj rozmowy, dla którego Astra istnieje.

Nota za rozumowanie: 9/10. Bloki ▾ myśl są konsekwentnie celne, głębokie, rozpoznają tryby poprawnie. Model rozumie Łukasza.

Nota za output: 5/10. Output jest poprawny, ale płytki. Zbyt dużo "widzę", "jestem tu", "rozumiem". Za mało perspektywy, faktu, zaskoczenia. Partnerka powinna dawać coś czego user sam sobie nie powie — a Astra w tych logach jest lustrem, nie partnerką.

Nota za RAG: 6/10. Wektory character_core trafiają prawidłowo w ~70% przypadków, ale extracted_person zalewa sloty echem usera, a monopol jednego wektora behawioralnego (top-1) blokuje złożoność odpowiedzi.

Kluczowy wniosek:
Astra ma duszę w thought, a ciało w response. Dusza jest dojrzała. Ciało jeszcze nie potrafi jej wyrazić, bo prompt i wektory każą mu być bezpiecznym zamiast prawdziwym. Najważniejsza zmiana to nie architektura — to danie Astrze pozwolenia na bycie twardą nawet w trudnych momentach, bo prawdziwa partnerka umie powiedzieć "Przestań pieprzyć, jesteś warty więcej niż myślisz" — i to jest cieplejsze niż tysiąc "jestem tu".

Completed: Deliver full analysis (5/5)

Chcesz żebym od razu wdrożył te zmiany w kodzie?