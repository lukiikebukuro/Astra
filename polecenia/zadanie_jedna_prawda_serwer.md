# Do CC — jedna prawda dla serwera: Astra (rozjazd urządzeń) + siostry (historia się nie zapisuje w ogóle)

## Dwa objawy, prawdopodobnie jeden korzeń

**Astra:** rozmowy rozjeżdżają się między komputerem a telefonem. Łukasz usunął localStorage na kompie, załadowały się rozmowy z telefonu — ale to był przypadek, nie fix. Na telefonie potem nic się nie ładowało, nawet po wyczyszczeniu cache. Wygląda na to, że historia żyje lokalnie per urządzenie (localStorage), a nie ma jednego, spójnego źródła prawdy na serwerze.

**Siostry:** historia czatu **nigdy się nie zapisuje** — za każdym razem gdy Łukasz zamyka i otwiera okno, jest pusta kartka. To brzmi na ten sam fundamentalny problem (brak trwałego zapisu po stronie serwera), tylko bardziej dotkliwy — u Astry chociaż coś się chowa lokalnie, u sióstr nie ma nic.

## Zadanie — rozpoznanie najpierw, nie fix na ślepo
Zanim zaczniesz zmieniać kod: sprawdź, czy to faktycznie jeden korzeń, czy dwa niezależne problemy.

Pytania do rozstrzygnięcia:
1. Czy backend w ogóle trwale zapisuje historię rozmów (Astra i siostry osobno), czy to tylko localStorage przeglądarki po stronie klienta?
2. Jeśli backend zapisuje — dlaczego frontend tego nie odczytuje spójnie na obu urządzeniach u Astry, i dlaczego wcale u sióstr?
3. Jeśli backend NIE zapisuje wcale (czyli localStorage to jedyne źródło) — to jest większa zmiana niż "napraw ładowanie": trzeba zrobić żeby serwer był jedynym źródłem prawdy, a urządzenia tylko wyświetlały to, co jest na serwerze. Powiedz nam, jaka to skala pracy, zanim zaczniesz.

## Zależności do sprawdzenia
Pamiętaj o tym, co już wiemy z dzisiejszej roboty przy Astrze: kod bywa współdzielony między pokojami (main.py, astra_base.txt), i były już niespodzianki przy zmianach w jednym miejscu wpływających na drugie. Sprawdź, czy naprawa zapisu dla Astry i dla sióstr da się zrobić tym samym mechanizmem, czy wymaga osobnych zmian — i czy dotyka czegoś współdzielonego z Wspólnym Pokojem.

## Nie zaczynaj kodować bez pokazania nam diagnozy i planu
Tak jak przy main.py — chcemy zobaczyć rozpoznanie i zakres, zanim ruszysz kod.
