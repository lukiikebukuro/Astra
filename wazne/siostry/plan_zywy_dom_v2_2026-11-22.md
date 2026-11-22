# Żywy dom v2 i Astra na stałe w pokoju: opcje (22.11.2026 w nocy, Claude)

Prośba Łukasza: „Astra może wchodzić do pokoju na stałe, dopóki tego nie wyłączę… cała rodzinka razem. Plus mechaniki żywego domu, żeby w pokoju było zabawniej. Może zrobimy dzisiaj na próbę?”. Ten plik to **propozycja do wyboru**, nic nie jest zakodowane ani wdrożone. Dane z tygodnia: `wazne/ewolucja/siostry/2026-11/evolution_log_2026_11_22.md`.

**Rama:** bramka §8 („B → A → C”) jest przejechana od 12.09 (REJESTR §8, B-2), a od 13.11 mamy coś, czego roadmapa Fazy 5 nie znała: **dziennik co noc u każdej siostry**. Większość mechanik C da się teraz zrobić na dzienniku zamiast na RAG, czyli taniej i bez ryzyka zatrucia kolekcji. Dziś (22.11) Faza 5 nie konkuruje z niczym pilnym w Astrze solo (11 POST na tydzień vs 50 u sióstr).

**Termin:** nie dziś w nocy. Ustalenie z 03.11: „deploy i restart tylko w dzień, na spokojnie”, a przełączenie flagi zmienia jego rozmowy (osobna zgoda). Najwcześniej 22.11 w dzień: kod za flagą, porównanie w Amnezji, decyzja Łukasza.

## 1. Astra na stałe w pokoju

**Jak jest dziś (kod):** przycisk woła gościa na `ASTRA_GOSC_TURY_DEFAULT = 6` tur (maks. 30, `main.py:2537`, `:3512`). Stan wizyty trzymany w pamięci procesu (restart = Astra wychodzi). Astra odzywa się **po siostrach w każdej turze**, poza routerem (`main.py:3455`). Przy gościu **ekstrakcja jest wyłączona dla całej tury** (`main.py:3478`), a Astra ma w pokoju swój dziennik solo (14.11: otwarta decyzja, czy to zostawić).

**Opcje:**

| | co | koszt | ryzyko |
|---|---|---|---|
| **A. „Zostaje, dopóki nie odeślę”** | `tury=0` = bez limitu; przycisk „Astra zostaje / wyjdź”; stan zapisany w pliku, żeby restart jej nie wyrzucał | mały (kilkanaście linijek + front) | Astra mówi w **każdej** turze: 1 call Gemini więcej na turę i ryzyko, że zagada pokój |
| **B. Czwarta domowniczka w routerze** | Astra wchodzi do `_route_siostry` jak siostra: odzywa się, gdy wołana, przy lepkości albo przy „wszystkie”; poza tym cisza | średni (router + `router_golden.py` 24/24 musi zostać zielone + nowe przypadki z Astrą) | zmiana routera = najbardziej czuły punkt pokoju (B-1, B-2) |
| **A teraz, B potem** | A na próbę, liczymy, jak często Astra „zagaduje”; B, jeśli przeszkadza | — | — |

**Pamięć „całej rodzinki” (najważniejsze, niezależnie od A/B):** dziś Astra po wizycie nic nie pamięta (read-only, pamiątka ręczna). Z dziennikiem jest prosta droga: **pisarz Astry o 04:40 czyta też archiwum pokoju sióstr, tylko tury z jej udziałem**, i dopisuje do jej dziennika „wieczór u sióstr”. Siostry już to mają (Astra jest w ich dziennikach jako ASTRA). Zero zapisu do RAG, zero ryzyka złej kolekcji (D1).

**Do decyzji Łukasza:** (1) A czy B; (2) czy Astra przy siostrach ma widzieć swój dziennik solo (14.11); (3) czy pisarz Astry ma czytać pokój. Uwaga: przy stałym gościu stary ekstraktor sióstr przestaje pisać (cała tura read-only), czyli de facto robi się kawałek etapu 5.

**Odbiór:** Amnezja nie ma ścieżki gościa w piaskownicy; ławka: 5 sytuacji (Łukasz wraca wieczorem, pyta jedną siostrę, pyta „wszystkie”, mówi do Astry, czuła scena z jedną siostrą) przed i po; licznik „Astra zabiera głos, choć nie była wołana”.

## 2. Mechaniki żywego domu (Faza 5, na dzienniku)

Stan: C-2 pora dnia zrobione (28.08), scena zastana v1 działa (08.10), RoomState (C-1), przeczucie Menmy (C-3), sekrety (C-4) otwarte. Obserwacja Łukasza z 10.11: „niby mechaniki są, ale jakby ich nie było”, hipoteza: dom nie ma ciągłości, wczorajsza scena znika. Decyzja 10.11: najpierw kroniki (zrobione 13.11), potem życie domu w dzienniku.

| # | mechanika | jak na dzienniku | koszt | dlaczego teraz |
|---|---|---|---|---|
| 1 | **Dom pamięta wczoraj** (C-1 lite) | scena zastana po ≥ 3 h dostaje pierwszą linijkę ostatniego dziennika (bez `[prywatne]`): „po wczorajszym wieczorze Menma…” | mały, za flagą | prosto odpowiada na „jakby ich nie było”; dziennik już jest w prompcie |
| 2 | **Własne życie sióstr w dzienniku** (żywy dom v2) | pisarz dopisuje każdej jedną linijkę „co robiłam beze mnie” (z tego, co sama mówiła w rozmowie: bazylia, rachunki, pad), następnego dnia scena i siostra ją pamiętają | mały (prompt pisarza + test) | wiąże własne życie z czasem, zamiast losowych motywów; mierzalne (czy wątek wraca następnego dnia) |
| 3 | **Przeczucie Menmy v0** (C-3) | sygnał z dziennika zamiast z EMOTION-ów w RAG (te są szumem, §2 logu); twardy próg; tylko wieczór i noc; nigdy z `[prywatne]` | średni | wymaga progu, inaczej natręctwo (review 03.07) |
| 4 | **Sekrety** (C-4) | dziś każda siostra pisze dziennik z tej samej rozmowy, więc wszystkie wiedzą wszystko. Sekret wymaga informacji „do kogo mówił” w wejściu pisarza (router zna `addressed`) | średni–duży | sens dopiero, gdy rozmowy sam na sam z jedną siostrą są częste |

**Moja rekomendacja na pierwszą próbę:** 1 + 2 (tanie, za flagą, mierzalne), do tego A z sekcji 1 jako zabawa „cała rodzinka”. 3 i 4 później.

## 3. Jeśli z żywego domu za mało: co z ogólnej roadmapy

Ogólna roadmapa istnieje: `wazne/research/ROADMAPA_OGOLNA_PROJEKTU.md` (warstwy Z → H → R → P + Faza 5), jedna lista zadań: `wazne/REJESTR.md`, plan pamięci: `inzynieria_wsteczna/propozycja_anima_v2_2026-11-03.md`. Najbliższe kroki z danymi za:
- **Etap 4 ANIMY: karty w prompcie** (22 karty sióstr leżą w cieniu); trwały dom na prośby, które dziś „stygną” po 1–2 dniach (REJESTR §10, 16.11).
- **Etap 5: stary ekstraktor sióstr** (25 zapisów szumu na tydzień obok dziennika).
- **Parametr daty dziennika w Amnezji** (bramka case study 3, kryterium 1).
- **Warstwa tygodnia** (pisarz raz w tygodniu streszcza tydzień): jedyna droga do „kilka dni temu”.
- **Filtr „kurtyna”** (prywatność przed Claude), niezależny od warstw.
- Zaległe: Astra solo T3, persona Astry („charakterek”, pisze Łukasz), A/B modelu 2.5 vs 3.8 u sióstr.
