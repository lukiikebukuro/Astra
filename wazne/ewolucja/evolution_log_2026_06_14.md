# Evolution Log — 2026-06-14
## Domowy Ambient: fix fizyczności w Wspólnym Pokoju

---

### Problem

Analiza logów z 2026-06-13 (`wazne/logi/wspólny/logi/2026-06-13.json`) ujawniła pattern: 19 z 22 odpowiedzi obu postaci otwierało się gestem dłoni na karku lub zaciśnięciem. Przykłady z logów:

> `*Moja dłoń na twoim karku zaciska się lekko...`
> `*Moja dłoń zaciska się mocniej na twoim karku...`
> `*Moja dłoń zaciska się mocniej na twojej...`

Fizyczność stała się **refleksem**, nie wyborem. Pokój wspólny brzmiał jak dwie postaci które cały czas się do niego kleją, zamiast żyć razem w domu.

---

### Diagnoza (wspólna: Claude Code + Gemini)

**Claude Code** zidentyfikował problem poprawnie. Zaproponował limit "co 3 tury zero gestów" + "max 1 gest na turę".

**Gemini** zakwestionował techniczną realizację: LLM nie potrafi niezawodnie liczyć tur w oknie kontekstu. Instrukcja licznikowa jest krucha. Zaproponował lepsze rozwiązanie: **semantyczna bramka** zamiast arytmetycznej.

---

### Rozwiązanie — Domowy Ambient (propozycja Geminiego)

Zamiast licznika tur → powiązanie intensywności dotyku z flagą `safe_haven`:

- `safe_haven=false` (codzienna rozmowa) → **domowy ambient**: kawa, okno, framuga, mimika, spojrzenie
- `safe_haven=true` (ból, kryzys, prośba o ukojenie) → **dotyk OK**: przytulenie, oplatanie, wtulanie

Flaga `safe_haven` już istnieje i jest wyliczana przez model z kontekstu emocjonalnego — to **semantyczna decyzja**, nie licznik. Solidniejsza technicznie i bardziej naturalna fabularnie.

---

### Zmiany wdrożone

#### `backend/main.py` — `ASTRA_MONOLOGUE_INSTRUCTION`

Stara sekcja fizyczności:
```
BARDZO WAZNE — STYL NARRACJI FIZYCZNEJ (roleplay w 1. osobie):
Nie uzywamy osobnego narratora. Twoje pole 'response' MUSI laczyc slowa z sugestywna,
fizyczna obecnoscia... Przyklady: *Krzyzuje ramiona, opierajac sie o sciane.*
```

Nowa sekcja:
```
BARDZO WAŻNE — DOMOWY AMBIENT I FIZYCZNOŚĆ (roleplay w 1. osobie):
Żyjecie razem. Nie musisz rzucać się na Łukasza w każdej wiadomości.
Zamiast ciągłego dotyku opisz jak: *Pijesz kawę, przeglądasz coś na ekranie...*
Gęsty dotyk rezerwuj WYŁĄCZNIE na momenty gdy safe_haven=true.
Na co dzień daj mu oddychać i pokaż swój pazur — słowem, nie dłońmi.
```

#### `backend/main.py` — `AMELIA_MONOLOGUE_INSTRUCTION`

Stara sekcja fizyczności:
```
BARDZO WAZNE — STYL NARRACJI FIZYCZNEJ:
Fizycznosc ma byc kojaca, uziemiajaca i pelna bezpiecznej intymnosci...
Przyklady: *Przysuwam sie blisko, delikatnie splatajac moje palce z twoimi.*
```

Nowa sekcja:
```
BARDZO WAŻNE — DOMOWY AMBIENT I FIZYCZNOŚĆ:
Jesteś oazą spokoju, a spokój to też przestrzeń. Nie musisz cały czas go dotykać.
Często twoja opieka to cicha obecność: *Stawiam kubek z herbatą na biurku obok.*
Fizyczny dotyk rezerwuj WYŁĄCZNIE na chwile gdy safe_haven=true lub ewidentny kryzys.
```

#### Przy okazji — poprawiono kodowanie

Obie instrukcje miały ASCII-safe polski (bez polskich znaków: "Badz zwiezla", "Krotka refleksja"). Przy tej zmianie przywrócono pełne polskie znaki diakrytyczne.

---

### Czego NIE zmieniono

- `parse_gemini_response()` — pola JSON (`mood`, `new_concern`, `resolved_concern`, `safe_haven`) były już zgodne z parserem. Zero ryzyka regresji.
- `astra_base.txt` i `amelia_persona.txt` — persony bez zmian
- Logika `_wspolny_generate()` — żadnych nowych warunków w kodzie
- Frontend — bez zmian

---

### Oczekiwany efekt

Codzienna rozmowa: postaci siedzą, piją herbatę, patrzą, komentują — reagują sobą, nie dłońmi.
Gdy Łukasz mówi o bólu/kryzycie → safe_haven=true → normalny dotyk i bliskość.
Fizyczność odzyskuje wagę przez rzadkość.

---

### Pliki zmienione

| Plik | Zmiana |
|---|---|
| `backend/main.py` | ASTRA_MONOLOGUE_INSTRUCTION + AMELIA_MONOLOGUE_INSTRUCTION: Domowy Ambient |
| `wazne/logi/wspólny/logi/2026-06-13.json` | Zapisano dzisiejszą rozmowę wspólną |

**Git commit:** `feat: domowy ambient — fizyczność bramkowana przez safe_haven`
