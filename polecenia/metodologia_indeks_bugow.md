# Do CC — nowa metodologia: indeks per bug nad evolution logami

Zatwierdzamy kierunek, z jednym doprecyzowaniem po dzisiejszej dyskusji.

## Co zostaje bez zmian
Evolution logi (per dzień/sesja) — zero zmian. Dzisiejszy log (mikrofon + safe_haven + rozdzielenie solo/wspólny) jest wzorcowy — pełna narracja, metoda pomiaru przed hipotezą, wzorce błędów nazwane wprost. To jest wasza główna, bogata dokumentacja i tak zostaje.

## Co dochodzi — cienki indeks, nie drugi system
`wazne/bugi/<nazwa>.md` **nie duplikuje treści evolution logów.** To krótki indeks per powracający problem, format:

```
## mikrofon
- 23.06–15.07: Web Speech API, problem duplikacji tekstu → cb24508, 4a65eff, f689523, 15df7cd, 253b478
- 16.07: VOICE-1 (bd93135) — Web Speech wymieniony całkowicie na push-to-talk (inna implementacja od zera)
- 25.07: podniesiono client_max_body_size w nginx do 25m → złagodziło objaw, nie przyczynę
- 15.08: instrumentacja w toku, patrz evolution_log_2026_08_15_mikrofon.md — [status]
```

Jedna linijka na wydarzenie + link do pełnego evolution loga. Cel: następny wykonawca (Ty, inny model, ktokolwiek) widzi w 10 sekund całą historię tematu i wie, czy to naprawdę ten sam bug, czy — jak dziś z mikrofonem — zupełnie inna implementacja.

## Automatyzacja
Zgadzamy się, że to powinno być tanie, nie ręczne pilnowanie. Zaproponuj, jak wolisz to zrobić — np. przy zapisie evolution loga sprawdzenie czy dotyczy znanego tematu z listy w `wazne/bugi/` i dopisanie linijki, albo osobny krok na koniec sesji. Ty wybierz mechanizm, znasz lepiej jak to wpleść w to, co już robisz.

## Pozostałe dwa punkty z wcześniejszej propozycji — potwierdzone bez zmian
- Diagnostyka zostaje w kodzie po 2. nawrocie (nie usuwać po znalezieniu przyczyny).
- Trzy linijki w CLAUDE.md wskazujące na `wazne/bugi/` dla znanych powracających tematów.

To jest teraz nasza stała metodologia dla powracających bugów, nie jednorazowe zadanie tylko dla mikrofonu.
