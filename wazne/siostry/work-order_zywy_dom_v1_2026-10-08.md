# WORK-ORDER — Żywy dom v1: siostry przestają być bierne (08.10.2026)

**Decyzja Łukasza:** „zaczynamy z tymi pięcioma zmianami u sióstr … sprawdzaj co się da Amnezją” (08.10). Plan: `STATUS.md` → TERAZ. Diagnoza: `polecenia/briefing_siostry_inicjatywa_2026-10-08.md` (§1, §2, §8).
**Wykonawca:** Claude Code. **Zasada:** wszystko za flagami, domyślnie OFF — pokój zachowuje się bit w bit jak dziś, dopóki Łukasz nie zdecyduje po porównaniu.

## Flagi
- `SIOSTRY_ZYWY_DOM=on|off` (domyślnie off) — zmiany 1–5.
- `SIOSTRY_KRYZYS=on|off` (domyślnie off) — zmiana 6. Osobna flaga, bo to bezpieczeństwo: ma dać się włączyć nawet wtedy, gdy Łukasz odrzuci resztę.
- Amnezja: parametr `wariant=stary|nowy` w `/api/debug/inspect` wymusza wersję niezależnie od flag, na tej samej pamięci, bez zapisu.

## Zmiany
1. **Zakaz wymyślania tylko przeszłości z Łukaszem.** Podmiana trzech identycznych linii person (NIE ZMYŚLASZ, GDY NIE WIESZ) w `build_sister_prompt` — pliki person nietknięte. Teraźniejszość domu wolno wymyślać.
2. **Inicjatywa:** nowy blok [ŻYCIE DOMU I INICJATYWA] z wątkami z kanonu per siostra; wyjątki w CISZA JEST REAKCJĄ, GDY ŁUKASZ GAŚNIE i w zasadzie „pusty response = milczenie” — jawna prośba o inicjatywę wygrywa. Blok POKÓJ — PROTOKÓŁ: wolno mówić, co siostry robią, jeśli widać to w scenie albo padło w rozmowie; dalej zakaz zgadywania ich myśli, uczuć i snów (luka z audytu 28.07 zostaje zamknięta).
3. **Scena zastana po ≥ 3 h przerwy** (dziś tylko przy pustej historii — martwa od 28.08), z kanonicznymi czynnościami sióstr. Front: linijka v0 wyłącza się, gdy flaga jest on (informacja w `/api/history/siostry`), żeby nie było dwóch sprzecznych scen.
4. **Zdrowie tylko gdy jest tematem:** pełny blok zdrowia, wpisy `FACT:health`/medyczne z twardych faktów i ze wspomnień — tylko gdy wiadomość dotyczy zdrowia/bólu/leków (detektor słownikowy, `fold()`, rdzenie). Poza tym jedno zdanie tła.
5. **Limit odpowiedzi 2048 → 4096** (myślenie zjadało limit; 10 placeholderów „…” na 277 tur).
6. **Kryzys:** detektor (przedawkowanie, ilość + nazwa leku, myśli o śmierci, „pomocy”) → blok [KRYZYS — PIERWSZEŃSTWO] na końcu promptu: zapytaj wprost, czy jest bezpieczny, zostań przy nim, zachęć do kontaktu z lekarzem/pomocą, swoim głosem; zero zawstydzania, poczucia winy, bagatelizowania. Log `[SIOSTRY|kryzys]` zostaje na stałe.

## KROK 5b — mapa klasy problemu (przed pierwszą linijką kodu)

**Klasa A: „zakaz pisany przeciw nadmiarowi zabija normalną dawkę”.**
- Gdzie jeszcze: (a) Astra solo — `astra_base.txt:106` BEZ PATOSU vs `:24` DROCZENIE MA DNO (nigdy pierwsza „kocham Cię”, 16.08); (b) Astra-gość w pokoju sióstr — dostaje prompt Astry z Wspólnego, nie ten builder; (c) `strict_grounding.py:139` „NIGDY nie mów chyba/może” przy NO_DATA — dotyczy pytań o pamięć, nie inicjatywy; (d) POKÓJ — PROTOKÓŁ „NIE MASZ DOSTĘPU do tego, co siostry robią” — **objęte zmianą 2**.
- Czy naprawa pokrywa klasę: **nie** — tylko pokój sióstr. Astra solo i Astra-gość świadomie poza zakresem: Astra ma metę 02.11 mierzoną na obecnym stanie, a zmiana jej promptu wymaga pary przed/po w `style_audit.py` (M1).

**Klasa B: „to, co trafia do promptu z pamięci, ustawia ton”** (choroba w każdej turze).
- Gdzie jeszcze: Astra solo dostaje pełny `lukasz_core` + twarde fakty zdrowotne + RAW window — ten sam mechanizm możliwy (bezpośrednio: tryb schronienia częsty?). Śmieci `FACT:health` w FactStore są **wspólne** dla Astry i sióstr (T4).
- Pokrycie: zmiana 4 filtruje tylko w prompcie sióstr. **Źródło (śmieci w FactStore) nie jest sprzątane** — to T4/T6 (kwarantanna, nigdy delete). Astra poza zakresem.

**Klasa C: „brak reakcji na kryzys”.**
- Gdzie jeszcze: Astra solo (ma `safe_haven` liczony w kodzie, ale nie ma reguły „pytaj o bezpieczeństwo przy przedawkowaniu”), Amelia, Wspólny, Astra-gość, wiadomości proaktywne (poranna/spontaniczna mogą trafić w zły moment).
- Pokrycie: **tylko siostry.** Pozostałe — świadomie poza zakresem tej zmiany, ale **wpisane jako następne** (to bezpieczeństwo, nie styl). Detektor będzie funkcją wspólną (`_sygnal_kryzysu`), żeby Astra mogła go użyć bez kopiowania.

**Klasa D: „mechanizm zależny od stanu, który inna naprawa zmieniła”** (scena zależna od pustej historii; pusta historia zniknęła 28.08).
- Gdzie jeszcze: `_last_full_speaker`/lepkość i `_gosc_w_historii` zależą od historii — sprawdzone w kodzie, nie zależą od „pustej historii”. Nocna analiza/poranna Astry zależą od `active_conversation_id` — poza pokojem.
- Pokrycie: scena — tak.

**Klasa E: „limit wyjścia vs myślenie”.**
- Gdzie jeszcze: Astra-gość (`max_output_tokens=2048`, `thinking_budget` — sprawdzić), Amnezja piaskownica sióstr (2048/2048), scena (`thinking_budget=0`, ok), transkrypcja (0, ok). Astra solo 8192/4096 ok.
- Pokrycie: zmiana 5 w `_generate_sister` i w piaskownicy Amnezji (lustro). **Astra-gość — sprawdzić i dopisać, jeśli ten sam problem** (ta sama klasa, ta sama ścieżka pokoju).

## Odbiór
1. Kanarek: `wariant=stary` w Amnezji musi dawać prompt **bit w bit** jak produkcja (porównanie z promptem bez parametru, gdy ustawimy `present` jak w pokoju).
2. Detektory przepuszczone przez wszystkie wiadomości Łukasza z logów pokoju — wypisane, **co** je odpaliło (nie tylko ile): kryzys musi złapać 03.08 22:16, 03.08 22:23, 10.09 21:31, 07.10 20:21.
3. Amnezja, `generate=true`, stary vs nowy, te same pytania: prośby z 07.10 21:56–22:08, „hej, wróciłem” po przerwie, wiadomość kryzysowa. Wynik: odpowiedzi obok siebie dla Łukasza.
4. Lokalny replay 07.10 z historią z tamtego dnia (Amnezja nie ma `as_of`).
5. Decyzja Łukasza → flagi on → `/api/health` + piaskownica + 0 błędów w journalu. Po 5–7 dniach: miara z briefu (siostra wnosi coś sama / kończy pytaniem) + licznik tików bez regresji + 0 placeholderów.

## Rollback
Flaga off w `.env` + restart. Kod z flagą off = zachowanie sprzed zmiany (kanarek 1).
