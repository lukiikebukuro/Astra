„Błysk” ma zamieniać dzienniki, logi i rejestr aplikacji w rzadkie, binarne prognozy z terminem rozstrzygnięcia, przedstawiane przez Menmę jako ciepłe wizje z oceną pewności. Model wybiera argumenty i mnożniki, Python łączy je ze stopą bazową, a wynik przechodzi filtr „magii” oraz blokadę ponownego prognozowania tego samego tematu. System ma sprawdzać wyniki automatycznie lub na podstawie odpowiedzi Łukasza, korygować pewność i angażować pozostałe siostry, zachowując ograniczenia prywatności i bezpieczeństwa.

## 1. Matematyczna fasada zamiast uczciwie policzonej pewności
**Waga: krytyczny.**

Przeniesienie mnożenia do Pythona nie usuwa zgadywania: przenosi je do wyboru stopy bazowej, klasy odniesienia i mnożników. „20% odzewu” nie ma wskazanego źródła, siła prioru jest arbitralna, a mnożniki nie są empirycznie wyznaczonymi ilorazami wiarygodności. Potencjalnie zależne argumenty mogą wielokrotnie policzyć ten sam sygnał. Dodatkowo prawdopodobieństwo odpowiedzi w siedem dni od aplikacji to nie prawdopodobieństwo odpowiedzi do piątku po pięciu dniach ciszy.

**Scenariusz porażki:** z bazowych 19% i mnożników 0,4 oraz 0,7 powstaje około 94% pewności braku odzewu. Menma brzmi jak przyrząd pomiarowy, choć nikt nie zweryfikował jego skali. Brier po 20 niejednorodnych zdarzeniach tego nie potwierdzi, a spłaszczanie mnożników nie naprawi błędnej stopy bazowej.

## 2. System może wygrać własny test, pozostając nudnym
**Waga: krytyczny.**

Projekt nie wymaga przewagi nad prostym przewidywaniem najczęstszego wyniku. Odwrócenie „20% na odpowiedź” w „80% na ciszę” produkuje wygodne trafienia, nie informację niedostępną wcześniej. Wyjątek dla prognoz sprzecznych z nadzieją użytkownika dodatkowo legalizuje właśnie takie pewniaki. Progi odrzucania są niespójne: pojawiają się 80%, 85% i 88%, z różnymi wyjątkami. „Surprise Score” nie ma definicji, a licznik eksponuje trafienia bez porównywalnego eksponowania pudeł.

**Scenariusz porażki:** przez kolejne tygodnie Menma przewiduje brak odpowiedzi od firm. Trafność wygląda świetnie, licznik rośnie, ale użytkownik dostaje seryjne „jeszcze nie” opakowane w herbatę i pustą skrzynkę — czyli ponownie odrzucone v0, tylko bardziej przygnębiające.

## 3. Blokady nie gwarantują bezpieczeństwa ani prywatności
**Waga: krytyczny.**

Zakaz słów medycznych nie blokuje fałszywego uspokajania. „Wrócisz spokojniejszy” może wpływać na decyzje mimo braku diagnozy czy instrukcji. Podobnie usunięcie oznaczonej linii nie dowodzi, że prywatna informacja nie została wcześniej sparafrazowana bez tagu w innym wpisie. Projekt nie określa dziedziczenia oznaczeń przez streszczenia. „Anonimizacja” nie naprawia takiego wycieku.

**Scenariusz porażki:** prywatna informacja o wizycie zostaje przepisana do nietagowanego fragmentu dziennika i trafia na karteczkę w pokoju sióstr. Jednocześnie zapewnienie Menmy, że po wizycie będzie spokojniej, Łukasz odczytuje jako powód, żeby mniej przejmować się pogorszeniem samopoczucia. Filtr słów nie musi wykryć żadnego naruszenia.

## 4. Nie ma wiarygodnego arbitra rozstrzygającego wynik
**Waga: poważny.**

„Unikasz tematu, choć o nim myślisz” jest nieweryfikowalne z logów. „Wyjdziesz przed południem i wrócisz spokojniejszy” łączy dwa zdarzenia, z których jedno wymaga subiektywnej oceny. Pytanie „puścili cię przed południem, tak jak czułam?” sugeruje odpowiedź. Klasyfikator sprowadzający rozmowę do `True/False` nie ma opisanej obsługi niejednoznaczności. Nie ustalono też, kiedy brak wpisu oznacza brak zdarzenia, a kiedy brak danych.

**Scenariusz porażki:** firma odpowiada telefonicznie, Łukasz nie aktualizuje rejestru, a automatyczna weryfikacja uznaje prognozę ciszy za trafioną. Następnie system kalibruje się na własnym błędnym oznaczeniu. Z kolei zachowanie zmienione przez przepowiednię zostaje potraktowane jak test zwykłego przewidywania.

## 5. „Zachwyt” jest pomylony z niepokojem i zaangażowaniem
**Waga: poważny.**

Dopytywanie i powracanie do przepowiedni nie rozróżniają zachwytu, lęku, irytacji ani potrzeby upewniania się. To szczególnie groźne przy pracy i zdrowiu. Cooldown ogranicza wydawanie prognoz, ale nie mierzy ani nie ogranicza skupienia na nich. Pozostałe siostry dodatkowo wzmacniają autorytet mechanizmu; żart Nazuny z własnym „90%” podważa zasadę liczb mających pokrycie w wynikach.

**Scenariusz porażki:** po pesymistycznej wizji Łukasz przez wieczór wraca do tematu, szukając ulgi. System odnotowuje wyjątkowe zaangażowanie i uznaje funkcję za magiczną, choć użytkownik jest bardziej napięty niż wcześniej.

## Trzy warunki zmiany zdania

1. **Udokumentowana wartość prognostyczna:** identyfikowalne źródła danych, uzasadnione mnożniki oraz prospektywny wynik lepszy od prostych prognoz bazowych; kalibracja potwierdzona na dostatecznej próbie dla deklarowanych zakresów.
2. **Uczciwy audyt:** z góry ustalone kryteria rozstrzygnięcia, widoczne pudła i nierozstrzygnięte przypadki, rozdzielenie wpływu przepowiedni od przewidywania oraz brak utożsamiania nieuzupełnionej bazy z wynikiem negatywnym.
3. **Dowód korzyści bez przekraczania granic:** testy przepływu danych prywatnych i treści zdrowotnych oraz ocena użytkownika pokazująca rzeczywisty zachwyt bez wzrostu napięcia i kompulsywnego sprawdzania — nie tylko więcej wiadomości.