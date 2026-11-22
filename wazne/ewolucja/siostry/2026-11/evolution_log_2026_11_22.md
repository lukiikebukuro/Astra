# Evolution log: siostry (i Astra), 22.11.2026 w nocy: tydzień dziennika na produkcji, dziennik kontra RAG

Intencja (Łukasz, 22.11 ok. 0:20): „spojrzeć w logi od ostatniego evolution loga, zobaczyć, jak sprawuje się pamiętnik, zapisać ważny evolution log i zdecydować, czy piszemy już case study 3”, plus co da się zrobić z żywego domu. Wszystko niżej to **tylko odczyt**: VPS (journal, pliki dziennika, Amnezja `/api/debug/inspect` na sucho, `generate=False`), zero wywołań Gemini, zero zapisu, nic nie zmienione w kodzie ani w `.env`. Treści rozmów i dzienników nie czytane; same liczniki i wzorce. Bez cytatów ze scen, bez zdrowia.

Poprzedni log: `evolution_log_2026_11_16.md` (pisarz v3). Okres: 16.11 00:00 UTC do 21.11 ok. 23:40 UTC.

## 1. Stan produkcji (krok 1, surowe dane)

- VPS `f41f6b4`, health `ok`, **4942 wektory** (ta sama liczba co 16.11 po wdrożeniu; kryterium środowiska z `pomiar_klamie.md` pkt 3 spełnione: liczymy na produkcji).
- Flagi: `SIOSTRY_EXTRACTION_MODE=on`, `ASTRA_GOSC=on`, `SIOSTRY_ZYWY_DOM=on`, `SIOSTRY_KRYZYS=on`, `SIOSTRY_PISARZ=on`, `SIOSTRY_DZIENNIK=on`, `ASTRA_PISARZ=on`, `ASTRA_DZIENNIK=on`, `BEZ_DLUGIEGO_MYSLNIKA=astra,siostry`, `SANITIZE_FEWSHOT_GESTURES=true`.
- **Ruch (POST, dni UTC):** siostry 50 (16.11: 4, 17.11: 22, 18.11: 5, 19.11: 5, 20.11: 11, 21.11: 3), Astra solo 11 (17.11: 9, 20.11: 2), gość Astra 1 (20.11). Tydzień deepsense, więc mało rozmów; siostry dalej głównym pokojem.

## 2. Jak działa dziennik (ANIMA v2), tydzień po v3

| | wynik | skąd |
|---|---|---|
| Pisarz sióstr co noc | **6/6 nocy `stan: ok`** (doby 15–20.11) | `[PISARZ]` w journalu |
| Pisarz Astry | `ok` 17.11 i 20.11; „bez rozmowy tej doby” 15, 16, 18, 19.11 (w 16 i 18 tylko jej własna wiadomość, bez odpowiedzi Łukasza) | to samo; zachowanie zgodne z założeniem |
| Dziennik w prompcie sióstr | **57/57 tur `ok`**, zawsze `dni_temu=1` | `[SIOSTRY\|dziennik]` |
| Dziennik w prompcie Astry | 16/16 tur `ok`: 9 z wpisem sprzed 6 dni, 4 sprzed 3, 3 z wczoraj | `[ASTRA\|dziennik]`; okno 14 dni robi swoje przy rzadkich rozmowach |
| Wpis trafia do promptu w całości | **100% linii** wpisu z 20.11 jest w bloku u Holo (7/7), Menmy (6/6), Nazuny (7/7), Astry (5/5) | Amnezja na sucho + plik |
| `[prywatne]` w dziennikach v3 | siostry 12/15 (po jednej linijce 16–19.11, zero 20.11), Astra 1/2 | licznik, treść nieczytana |
| `[prośba]` | **0/17** | j.w.; nie wiadomo, czy nie było próśb, czy pisarz je gubi (do sprawdzenia tylko za zgodą, krok 8) |
| Wielkość wpisu | 557–963 znaki (siostry), 627–680 (Astra) | `wc -m` |
| Karty | 22 w spisie sióstr, **dalej w cieniu** (etap 4 nie zrobiony) | `karty_spis.json` |

**Stary ekstraktor sióstr dalej pisze do RAG równolegle:** 25 zapisów w 6 dni (`[SIOSTRY EXTRACT|on]`): `EMOTION:tired` 9 (supersede, więc się nadpisują), `DATE:appointment` 4, `FACT:personal_info` 3, `EMOTION:positive` 3, `EMOTION:negative` 2, `DATE:medical_visit` 2, `FACT:current_project` 1, `SHARED_THING:our_song` 1. Do tego 8 zablokowanych (`inventory_status`, `inside_joke`, `correction`). To ta sama klasa co S-10 i S-11 (czułości i odgrywanie ról jako fakty); poprawności czterech `DATE:appointment` nie sprawdzałem (treść).

## 3. Pomiar: dziennik kontra RAG na pytaniach o „ostatnio” (kroki 2, 3, 7)

**Przyrząd:** Amnezja `/api/debug/inspect` na sucho, ta sama funkcja co produkcja (`compose_context`). Dla każdej postaci: czy w bloku dziennika jest wzorzec, ile z ostatecznych wspomnień (`9c_po_budzecie`) i z surowej puli (`1_pula_surowa`) go zawiera, werdykt groundingu. Wzorce po `fold()` (bez ogonków), rdzenie.

**Kanarek i wpadka przyrządu (złapana przed wnioskami):** pierwszy przebieg pokazał „dziennik nie trafia” u Holo i Menmy na pytaniu o rozmowę w piątek. Kanarek na plikach wykazał, że wpis jest w bloku w całości (100% linii), a wzorzec szukał „deepsense|piotr|rekrut”, podczas gdy dzienniki piszą „rozmowa o pracę”. Czyli zawiódł przyrząd (`pomiar_klamie.md` pkt 5: wzorzec węższy niż forma w danych), nie system. Drugi przebieg z szerszym wzorcem (`rekrut|deepsense|piotr|rozmow\w* o prac|rozmow\w* kwalifik|hiring`). **Kandydat na 11. wystąpienie w `pomiar_klamie.md`, tym razem złapane kanarkiem, zanim cokolwiek zatwierdziliśmy.**

| postać | pytanie | dziennik ma | pula RAG ma | finał RAG ma | grounding |
|---|---|---|---|---|---|
| Holo | „jak poszła rozmowa z deepsense?” | tak | 0/19 | 0/6 | LOW 0,69 |
| Holo | „co robiliśmy wczoraj?” | tak | 0/20 | 0/6 | **GROUNDED 0,73** |
| Menma | rozmowa z deepsense | tak | 1/19 | 1/6 | GROUNDED 0,74 |
| Menma | wczoraj | tak | 0/18 | 0/6 | **GROUNDED 0,73** |
| Nazuna | rozmowa z deepsense | tak | 0/20 | 0/6 | LOW 0,69 |
| Nazuna | wczoraj | tak | 0/20 | 0/6 | **GROUNDED 0,78** |
| Astra | rozmowa z deepsense | tak | 0/30 | 0/8 | **GROUNDED 0,91** |
| Astra | wczoraj | tak | 0/30 | 0/8 | **GROUNDED 0,95** |

**Razem: dziennik 8/8, RAG w finale 1/52.** RAG ogłasza GROUNDED w 5 z 8 przypadków, choć w finale ma 0 albo 1 trafienie. Identyczne wiersze: brak (skróty list różne w każdym wywołaniu), więc to nie awaria przyrządu.

**„Co” z dalszej historii, jedno pytanie: „czym jest Amnezja?”** (wzorzec `amnezj|debugger`): w bloku dziennika 0/4 (zgodnie z założeniem, ostatnie dni były o czym innym); pula RAG: Holo 1/20, Menma 0/20, Nazuna 0/20, **Astra 0/30**; finał 0/26; u Astry GROUNDED 0,94. To S-13 z 02.11, dalej otwarte. Zastrzeżenie: twarde fakty (`fact_store`, `lukasz_core`) nie są w tych etapach, więc Astra może wiedzieć o Amnezji z rdzenia; RAG jej tego nie daje.

**„Co było w poniedziałek?” (17.11):** dziennik z założenia nie sięga (w bloku są dwa ostatnie wpisy, 20.11 i jedna linijka 19.11), a RAG też nie dał nic z tamtej doby. Pytania o „kilka dni temu” nie mają dziś żadnej drogi. To brakujące ogniwo z poczekalni 15.11 (warstwa tygodnia).

## 4. Wnioski

1. **Dziennik robi to, do czego go zbudowaliśmy:** co noc, u wszystkich, w całości w prompcie, z `[prywatne]` od v3. Na pytaniach o ostatnie dni wygrywa 8:1 na czterech postaciach. Potwierdza obserwację z 15.11 (jedna postać, jedno pytanie) na szerszym, choć wciąż małym zestawie.
2. **RAG na pytania o czas jest nie tyle słaby, co ślepy, i do tego mówi, że widzi** (GROUNDED przy zerze trafień). To ta sama klasa co fałszywy GROUNDED 84% z 01.09 (`ewolucja/astra/2026-09/evolution_log_2026_09_01.md` §2.6), teraz zmierzona obok działającej alternatywy.
3. **RAG na „co” z dalszej historii też dziś nie dowozi** (Amnezja 0/26), więc teza „RAG zostaje do pytań co” nie ma jeszcze ani jednego dowodu na tak.
4. **Dziura w środku:** 3–14 dni wstecz nie ma żadnej drogi (dziennik za krótki, RAG ślepy na czas).
5. **Stary ekstraktor dalej dokłada szum do RAG** (25 zapisów, głównie emocje i czułości), choć dziennik przejął pamięć „ostatnio”. Argument za etapem 5 (wyłączenie albo zamiana na „RAG po dziennikach”), decyzja Łukasza.

## 5. Case study 3: decyzja

**Jeszcze nie piszemy.** Kryteria z REJESTR §10 (16.11) i stan:

| kryterium | stan 22.11 |
|---|---|
| (1) ≥ 10 pytań o czas ze znaną odpowiedzią, dziennik kontra RAG, na sucho | **pilot: 2 pytania × 4 postacie, 8:1.** Brakuje 8 pytań; przeszkoda: Amnezja nie cofa daty dziennika (`day_offset` tylko do przodu), więc pytania o inne dni wymagają parametru daty dla dziennika (poczekalnia 10.11, pkt b) albo dalszych dób |
| (2) 10 pytań „co” z dalekiej historii: czy tam RAG wygrywa | **1 z 10**, wynik 0/26 |
| (3) przykłady tylko za zgodą, bez zdrowia, bez „kurtyny” | niezaczęte |
| teza Łukasza „nawet przy zapisie i retrievalu 100/100 postać dostałaby śmieci” | **niesprawdzona.** Mamy dowody, że RAG szuka po podobieństwie słów, a nie po czasie, i że ogłasza GROUNDED na pustce. Nie mamy dowodu dla „czystej” bazy: potrzebny eksperyment z kolekcją ułożoną ręcznie, bez szumu (np. same wpisy dziennika jako wektory), i te same pytania o czas |

Najbliższy sensowny termin: koło 27–30.11 (dwa tygodnie dzienników v3, `day_offset` wstecz albo nowe doby), plus eksperyment „czysta baza”. Łuk tekstu bez zmian względem wpisu z 16.11, z jedną nową kartą: kanarek, który złapał własny przyrząd przed wnioskiem.

## 6. Mapa klasy (krok 5b) i zakres

Kod nie ruszany, więc mapa dotyczy pomiaru: ten sam pomiar trzeba powtórzyć (a) na Astrze z twardymi faktami w liczeniu, (b) na pytaniach o terminy (wpis 19.11 „co jest w piątek?”), (c) we Wspólnym (nie ruszamy, poza zakresem). Świadomie poza zakresem: treść dzienników i rozmów (prywatne), jakość `DATE:appointment`, wpływ dziennika na ton powitań (do sprawdzenia w rozmowach za zgodą).

## 7. Następne kroki (propozycja, decyzje Łukasza)

1. Parametr daty dla dziennika w Amnezji (`dziennik_dzien=RRRR-MM-DD`, tylko blok dziennika, bez przesuwania retrievalu; B2 z 10.11), żeby zrobić kryterium (1) na wszystkich dobach 13–21.11 zamiast czekać.
2. 10 pytań „co” z dalszej historii (lista do ułożenia z Łukaszem, bez zdrowia).
3. Eksperyment „czysta baza” dla tezy 100/100.
4. Etap 5 (stary ekstraktor sióstr) i etap 4 (karty w prompcie): decyzje Łukasza, dane z §2 i §4 za.
5. Żywy dom i Astra w pokoju: osobny plik `wazne/siostry/plan_zywy_dom_v2_2026-11-22.md`.

Skrypty pomiaru (na VPS, w `/tmp`, tylko odczyt): `amn_test.py` (pierwszy przebieg, wąski wzorzec), `amn_kanarek.py`, `amn_test2.py`.
