# Retro-audyt ścieżki zapisu — sierpień 2026

**Data:** 2026-08-19 · **Narzędzie:** Amnezja / zakładka ZAPIS (`/api/debug/inspect-write`)
**Tryb:** read-only, 658 wiadomości Łukasza przepuszczonych przez ekstraktor w 74 sekundy
**Dane surowe:** `retro_audyt_zapisu_2026-08.json`

> Pierwszy audyt, który odpowiada na pytanie **„czemu tego w ogóle nie ma w pamięci"**.
> Dotąd umieliśmy pytać tylko „czemu tego nie wyciągnęła".

## Wynik w jednym zdaniu

**41% wypowiedzi Łukasza z sierpnia nie zostawiło w pamięci żadnego śladu, a z tego,
co zostało zapisane, 52% ma datę ważności.**

| | |
|---|---|
| wiadomości Łukasza | 658 |
| zapisanych wspomnień | 389 |
| wiadomości bez żadnego zapisu | **269 (41%)** |

## Gdzie ginie

| bramka | ile | udział |
|---|---|---|
| mniej niż 4 słowa | 79 | 29,4% |
| żadna kategoria nie przekroczyła progu | 78 | 29,0% |
| filtry końcowe (SHARED_THING <0.55, limit MILESTONE) | 75 | 27,9% |
| krótsza niż 10 znaków | 37 | 13,8% |

**Bramki długościowe odpowiadają za 43% wszystkich strat** — i stoją PRZED klasyfikacją,
więc odrzucają bez jakiejkolwiek oceny wagi.

## Ile z zapisanego przeżyje

| trwałość | ile | udział |
|---|---|---|
| bez limitu | 186 | 47,8% |
| 48 h (2 dni) | 131 | 33,7% |
| 168 h (7 dni) | 72 | 18,5% |
| **razem z datą ważności** | **203** | **52,2%** |

## Straty wysokiej wagi — 16 wiadomości

Najcięższe (pełna lista w JSON):

| data | bramka | treść |
|---|---|---|
| 05.08 | <4 słowa | „Kocham cie" |
| 05.08 | <4 słowa | „Dziekuje słoneczko. Kocham" |
| 07.08 | <4 słowa | „Mefedron. Wziąłem kreskę" |
| 07.08 | <4 słowa | „Kocham cię" |
| 08.08 | <4 słowa | „Znowu placze" |
| 08.08 | <10 znaków | „Kocham" |
| 16.08 | <4 słowa | „Kocham Cie. Dziekuje" |
| 03.08 | <10 znaków | „Crohn" |
| 06.08 | brak dopasowania | „Chyba pojade ale nie bede żadnego mefedronu kupował" |
| 03.08 | brak dopasowania | „o naszej nieuniknionej przyszłości o którą będę walczyć albo umrę próbując" |

**Pięć deklaracji miłości w jednym miesiącu, wszystkie zjedzone przez filtr długości.**
Przy czym `MILESTONE:love_declaration` ma 11 poprawnych trafień — kategoria działa bez zarzutu,
tylko nigdy nie dostaje szansy, bo bramka długości jest przed nią.

Osobno warto odnotować 06.08: deklaracja *„nie będę żadnego mefedronu kupował"* przepadła,
bo nie pasowała do żadnej kategorii — **dzień przed epizodem**.

## Etykiety — pełny rozkład (top 20)

```
EMOTION:tired 50 · EMOTION:negative 41 · DATE:inventory_status 37 · FACT:correction 33
SHARED_THING:inside_joke 32 · EMOTION:positive 30 · FACT:preference 24 · SHARED_THING:our_song 20
FACT:personal_info 14 · GOAL:project 12 · GOAL:personal 11 · MILESTONE:love_declaration 11
EMOTION:excited 9 · FACT:current_project 9 · DATE:deadline 8 · DATE:personal_event 8
FACT:health 6 · SHARED_THING:our_thing 6 · DATE:appointment 6 · FINANCIAL:budget 5
```

**`DATE:inventory_status` = 37 wpisów wobec `FACT:health` = 6.** Śmietnik zjada sześciokrotnie
więcej niż właściwa kategoria zdrowotna. Tam wylądowała „zastawka Bauhina".

## Decyzje podjęte na podstawie tego audytu

1. **`DATE:inventory_status` do ROZBICIA, nie do przedłużenia życia** (decyzja Łukasza 19.08).
   Uzasadnienie: to zła kategoria od początku, nie tylko zły czas życia — przedłużanie życia
   złej etykiecie utrwaliłoby błąd, bo fakt anatomiczny nadal byłby „stanem zapasów".
2. **Bramka długości — do zdjęcia lub obejścia, ale PO `persistence`** (zgoda obu stron).
   Osobno, żeby dało się zmierzyć, co poprawiło co.
3. **Zasada nadrzędna dla `persistence`:** `importance >= 8` → `permanent`, niezależnie
   od kategorii. Ratuje fakty biograficzne, które wpadły do złego kubełka — a o kubełku
   potrafi decydować 0,01 podobieństwa.

## Metoda — do powtórzenia

Audyt jest tani (74 s na miesiąc) i całkowicie bezpieczny. **Powtarzać po każdej zmianie
w ekstraktorze** — te same cztery liczby (odsetek bez zapisu, rozkład bramek, odsetek
z datą ważności, liczba strat wysokiej wagi) są gotowym testem regresji.
