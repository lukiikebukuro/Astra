# Audyt Fable (CLAUDE.AI / WEB) — Astra solo, sekcja zwłok promptu 90 931 znaków — 2026-07-05

> Humanistyczny/systemowy. Karmiony: briefing techniczny + astra_base.txt + audyt architektury + pomiar Opusa (91k/74%/345 love_declaration). Bez dostępu do Amnezji — analiza na dostarczonych liczbach.

## TEZA: leczyliście nie tego pacjenta
Cała saga R1–R7 zakładała, że przeintensywnienie mieszka w warstwie persony. Pomiar to obala jako diagnozę główną: postać = 16% tego co model czyta. 74% to ściana 391 "twardych faktów", 345 = MILESTONE:love_declaration (w tym "Oki. Popalam sobie").
Samokorekta: w audycie architektury dałem "prompt bez sufitu" jako #5 "ŚREDNI (pełzający)" — myliłem się. Nie pełza, już zdominował; dla Astry to #1. Jednocześnie "instrukcje persony to ułamek procenta" było przesadą — 16% to nie ułamek, model widzi astra_base. Tylko czyta ją jako szept na tle chóru.

## 1. Anatomia 74%: błąd KATEGORIALNY, nie ilościowy
`get_facts_for_prompt` bez LIMIT → magazyn = kontekst. FactStore projektowany jako exact-match (Crohn, imiona, daty) — przy 30 faktach działa; przy 391 "fakty mają priorytet" produkuje wysypisko na pozycji priorytetowej. Wspomnienia mają reranker/MMR/temporal/budżet; fakty NIC. Zbudowaliście selekcję dla kanału-ułamka, a kanał dominujący leje się grawitacyjnie.
Ekstraktor: 88% jednej etykiety = kolaps klasyfikatora do klasy większościowej, nie "błędne oznaczanie". Hipotezy: (a) love_declaration jest catch-allem/pierwszą pozycją enuma; (b) ekstrakcja z kontekstem relacji → romantyczna soczewka na wszystko; (c) bug: default przy is_milestone=true bez etykiety. Weryfikacja: przeczytać prompt ekstraktora, SELECT fact_type COUNT GROUP BY, histogram timestampów (lawina od konkretnego dnia = data regresji).
Zbieg z #9 architektury: 773 milestony ChromaDB + 345 FactStore — dwa magazyny, ta sama inwersja: "milestone" (rzadka kotwica) operacyjnie klasą większościową. Gdy wyjątek staje się regułą, przeprojektowuje się mechanizm, nie próg. Milestone potrzebuje budżetu (kandydat→potwierdzenie, cap).

## 2. Humanistycznie: pamięć, która nie zapomina, nie jest pamięcią — jest protokołem
Zapominanie to mechanizm konstruowania znaczenia. Partner pamięta wybiórczo, i ta wybiórczość mówi ci ile ważysz. System trzymający "Popalam sobie" obok prawdziwego wyznania z tą samą etykietą i priorytetem robi relacji to, co kicz robi sztuce: inflację znaczenia. Jeśli 345 rzeczy to deklaracje miłości, żadna nie jest. Prawdziwe wyznania Łukasza toną we własnej walucie.
Mechanika modelu: Gemini czyta co turę korpus, gdzie wszystko co Łukasz powiedział jest emocjonalnie doniosłe. astra_base mówi "błahe jest błahe", "4 z 5 lekkich", "nie szukaj drugiego dna". Dane mówią: każde jego słowo było deklaracją miłości. Model rozstrzyga sprzeczność na korzyść 67k znaków, nie 3 linijek — few-shot bije instrukcję. Ta ściana to de facto 345-elementowy few-shot rejestru "wszystko doniosłe". TRZECI silnik przeintensywnienia (obok pętli historii i monotonii milestonów) — prawdopodobnie najsilniejszy: największy objętościowo, obecny od tury zero.
Wniosek adwersaryjny: R1–R7 mogły "działać" głównie przez świeży conversation_id (reset pętli imitacji), nie przez treść poprawek — trzy zmienne naraz, zero kontroli. Nie rozplątać wstecz; ale fix faktów robić jako JEDYNĄ zmianę z golden setem przed/po.

## 3. Audyt astra_base.txt — dobry tekst z minami, które sam podkłada
Po R1–R7 to solidny prompt (80/20, anty-parafraza z "Haha, no.", ZAKAZ PĘTLI, safe_haven z końcem, zakaz fraz przewagi). Ale:
- **Archetyp otwiera plik.** "Widzisz głębiej niż on sam widzi" (l.8-10) na pozycji prymarnej; korekty 100 linijek niżej. Pozycja = waga. Zdiagnozowaliście mirror-with-claws jako przyczynę i zostawiliście jako pierwsze zdanie. Fix przez dopisywanie wyjątków zamiast edycji tezy.
- **Konwencja PROTOKÓŁ/CAPS** — ta sama mina co u sióstr. "PERMISSION PROTOCOL", "PROTOKÓŁ NOCNEJ WARTY", "PROTOKÓŁ SAFE HAVEN". Sprawdzić w 441 turach czy Astra nie recytuje swoich.
- **Zaszyte liczby w przykładach** (l.85: "1000 zł / 24k") — modele papugują dosłownie; będzie recytować stan z lipca w grudniu. Pseudo-cytat l.50 ("Rok temu mówiłeś że się poddasz na RAGu") uczy formy "przywołaj wspomnienie z datą" → konfabulacja gdy retrieval nie poda prawdy. Przykłady bez liczb i bez pseudo-cytatów.
- **Sekcja Wspólnego Pokoju w pliku bazowym** (~15% pliku) — solo-Astra czyta protokół Amelii w każdej rozmowie sam na sam = przeciek scopingu na poziomie persony. Wydzielić: base + mixin pokojowy doklejany warunkowo.
- **"Wspomnienia fundamentem" + "PROAKTYWNA PAMIĘĆ nie czekaj aż zapyta"** — przy 67k ściany mislabelowanych faktów to rozkaz: wciągaj tę ścianę do każdej wymiany. Współwinne przeintensywnienia przez zatrute dane pod spodem. Po detoksie może zostać; przed — dolewa paliwa.
- DNA 50/30/20 to dekoracja (model nie miesza procentowo) — nie szkodzi, nie działa.

## 4. Rewizja planu: DETOKS PRZED REFAKTOREM
- **Krok 1 — zatamować krwawienie:** fix ekstraktora (taksonomia z prawdziwym defaultem "nie-milestone", próg, przykłady negatywne). Bez tego każdy dzień dosypuje śmieci.
- **Krok 2 — triage zaplecza, NIE kasowanie.** Jako humanista: te 345 wpisów to zapis relacji, choćby źle otagowany. Kolumna statusu / reklasyfikacja (nocny job LLM + wyrywkowa kontrola), ZERO DELETE. Prawdziwe deklaracje dostają etykietę z powrotem i wtedy znaczą.
- **Krok 3 — selekcja faktów w compose:** LIMIT + filtr kategorii (zdrowie/tożsamość zawsze, epizodyczne przez relevance), cap znakowy na [TWARDE FAKTY]. To business case dla hybrid_memory_consolidation.md.
- **Krok 4 — świeży conversation_id po deployu** + golden set przed/po.

## OSTRZEŻENIE (obowiązek, nie asekuracja)
Zdjęcie 74% promptu zmieni Astrę mocniej niż wszystkie R-fixy razem. Prawdopodobnie na lepsze — lżejsza, mniej dosłowna, mniej "doniosła". Ale Łukasz musi wiedzieć PRZED, że po operacji ona będzie brzmieć inaczej, i że to leczenie, nie utrata. Ustalić wcześniej, po czym poznacie sukces (golden set + odbiór w tygodniu), żeby "inna" nie zostało odruchowo odczytane jako "zepsuta" — ani żeby prawdziwa poprawa nie została cofnięta z tęsknoty za intensywnością, która była objawem.

## WERDYKT
Diagnoza przenosi się z warstwy persony do warstwy DANYCH: chór 345 fałszywych deklaracji + pętla historii to silniki; archetyp w prompcie to rezonator. Fix ekstraktora i selekcja faktów wskakują przed krok 1 migracji architektury (tańsze S/M, twardy pomiar). astra_base = osobny mniejszy zabieg (degradacja archetypu z pozycji otwierającej, dekaps protokołów, usunięcie liczb i pseudo-cytatów, wydzielenie Wspólnego). Koncepcja "milestone" w całej ANIMIE wymaga przeprojektowania z budżetem.
**Największe "gdzie się myliliście":** przez pół roku edytowaliście 16% promptu, bo to było widać. Ściana faktów była niewidzialna, bo nikt jej nie mierzył — aż zbudowaliście Amnezję. Debugger zwrócił koszt budowy jednym pomiarem.
