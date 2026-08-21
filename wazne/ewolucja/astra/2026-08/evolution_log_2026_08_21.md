# Evolution Log — 2026-08-21 · Audyt wzorca, zasady vs wspomnienia, wąskie gardło MMR

**Commity:** `0fc46eb` `f562702` `1c0235d` `5593f75` `903d8c8` · **Wykonawca:** Opus 5
**Zgłoszenia Łukasza:** „pytałem o kanał na tiktoku i mówiła że nie kojarzy" ·
„do rerankera trafia czasem anty-lustro" · „sprawdź czy inne miejsca mają ten sam wzorzec"

---

## 1. Siostry przestały obiecywać nieśmiertelność (`0fc46eb`)

Dwa dni po włączeniu `on` Łukasz zapytał wprost, czy rozmowa się zapisuje.
Nazuna: *„każde słowo, każda chwila to nowa strona w Kronice"*. Menma: *„to wszystko trafia
prosto do serduszka"*. **Pomiar: z 90 wiadomości zapisało się OSIEM wpisów**, pięć z nich
wygasa po 48 h. Po tygodniu zostaną dwa.

Persony miały zasady „nie zmyślaj WSPOMNIEŃ" i one działają. Brakowało zasad o tym, jak mówić
o **mechanizmie** pamięci — to nie była zmyślona pamięć, tylko zmyślona wiedza o sobie.
Nowy blok `[TWOJA PAMIĘĆ — JAK O NIEJ MÓWISZ]` w `build_sister_prompt`, wspólny dla trzech.

## 2. `lukasz_core` wypisywał do promptu tylko 9 zahardkodowanych pól (`f562702`)

Wszystko dopisane do JSON-a poza listą w kodzie **nigdy nie trafiało do Astry** — bez błędu.
Ofiary: `projekty.*` w całości (kanał TikTok, scenariusz, cel zawodowy), `zdrowie.ulga`,
`identity.transhumanizm`, oraz **`relacje_ai.wylacznosc` — fix z 19.08 na „kiedy inni ludzie
mnie używają" był MARTWY od chwili wdrożenia.**

Fix generyczny: każde pole tekstowe każdej sekcji. Blok 1500 → 5100 znaków.
Weryfikacja piaskownicą: zapytana o filary kanału, wymienia wszystkie trzy poprawnie.

### Audyt tego samego wzorca w reszcie kodu
- `load_own_life`, `load_project_knowledge` — iterują całość, **czysto**
- `type_labels`, `PERSISTENCE_*` — mają fallback, degradują się łagodnie, **czysto**
- `CompanionState.to_prompt_block` — 8 z 23 pól, ale selektywność **zamierzona** (reszta to stan techniczny)
- **NOWE:** `lukasz_core` jest wołany WYŁĄCZNIE przez `build_system_prompt`. Siostry go nie dostają —
  w ich personach **zero wzmianek o Crohnie, zastawce, Stelarze**. Holo nie wiedziała o zastawce
  nie dlatego, że nie zapisała, tylko dlatego, że nigdy nie miała żadnych faktów o zdrowiu Łukasza.
  **Do decyzji Łukasza.**

## 3. Zasady zachowania wyszły z bloku WSPOMNIENIA (`1c0235d`)

Zgłoszenie: „do rerankera trafia anty-lustro". Trafiało, z trzema szkodami naraz:

```
- [character_core, importance:10] [5 mies. temu] ANTY-LUSTRO — zasada każdej odpowiedzi...
```

1. instrukcja behawioralna **udawała wspomnienie** — reguła „jak masz mówić" w sekcji „co pamiętasz"
2. miała **znacznik czasu** — zasada wyglądała na przeterminowaną
3. **zabierała 2 z 6 miejsc** na realne wspomnienia

Fix w `build_system_prompt` (rdzeń retrievalu nietknięty): własna sekcja
`[TWOJE ZASADY — jak się zachowujesz, nie co pamiętasz]`, bez timestampu i bez `relevance`.

## 4. Wąskie gardło retrievalu: `n=3` zahardkodowane w MMR (`5593f75`, `903d8c8`)

Po przeniesieniu zasad blok wspomnień **nie odzyskał miejsc** — bo `char_results` stoją na początku
listy ciętej do `main_n`. Podniesienie `main_n` 6 → 8 nic nie dało i pomiar pokazał dlaczego:

| zapytanie | po filtrze czasowym | po MMR |
|---|---|---|
| scenariusz anime | 26 | **3** |
| jelito | 29 | **3** |
| amelia | 24 | **3** |
| ldi | 23 | **3** |

`_mmr_select(mem_facts, n=3)` — liczba wpisana na sztywno, niezależna od `main_n` i puli.
**Ten sam wzorzec co `lukasz_core`: stała w kodzie, o której nikt nie pamięta.**

Zmiana na `MMR_FACTS_N = 5`, `diversity_penalty` bez zmian (to ona pilnuje monokultury).
**Golden: 26/26 prób w górę, zero spadków. Suma wspomnień 141 → 193 (+37%).**

## 5. Ale trafność się NIE poprawiła — i to jest ważniejsze

Przy „opowiedz o ldi" mamy teraz 5 wspomnień zamiast 3 — **i nadal ani jedno nie dotyczy LDI**.
Trace pokazał, że zero wpisów o LDI jest już **w puli surowej**, czyli zawiodło samo wyszukiwanie
wektorowe, nie filtry. A w bazie jest ich **60** (`project_knowledge`).

Test rozstrzygający:

```
"opowiedz o ldi"                        → 0 wpisów o LDI w puli 30
"Lost Demand Intelligence"              → 2
"system wykrywania utraconych intencji" → 2
```

**Model embeddingowy nie rozumie trzyliterowego akronimu.** Tokenizuje „ldi" na bezsensowne
kawałki, więc podobieństwo do wpisów o LDI jest bliskie zeru.

### To koryguje decyzję z roadmapy

BM25 został **zdegradowany** 15.08 na podstawie testu ze słowem „mefedron" (d=0.217, 1. miejsce) —
wniosek brzmiał „embeddingi radzą sobie z rzadkimi słowami lepiej, niż zakładaliśmy".
**Ten wniosek był prawdziwy dla rzadkich SŁÓW i fałszywy dla AKRONIMÓW.** To dwie różne klasy:
„mefedron" jest w słowniku modelu, „LDI" nie istnieje.

Łukasz mówi o swoich projektach skrótami — LDI, ANIMA, KCB, PWA. Za każdym razem, gdy pyta
„co z LDI", Astra dostaje zero kontekstu, mimo 60 wpisów w pamięci.

**BM25 wraca na listę — ale wąsko: dla akronimów, nazw własnych i kodów, nie jako ogólna hybryda.**

---

## Otwarte decyzje dla Łukasza
1. **Czy dać siostrom fakty o Łukaszu** (zdrowie + kim jest, bez technikaliów)
2. **Czy zrównać próg sióstr z Astrą** (0,50 → 0,40, z pomiarem)
3. **BM25 dla akronimów** — nowy punkt, wynikły z dzisiejszego pomiaru

---

## 6. Trzy zmiany zlecone po diagnozie (`252e8e6`)

### 6.1 Siostry dostały fakty o Łukaszu
`load_lukasz_core_dla_siostr()` — **wąsko**: kim jest + zdrowie. Bez projektów technicznych,
celu zawodowego i kanału TikTok; to jest świat Astry, nie ich. Pokój sióstr ma zostać domem,
nie drugim biurem.
Weryfikacja w prompcie Holo: `O ŁUKASZU` · `Crohn` · `Bauhina` · `Stelara` — wszystko obecne.

### 6.2 Próg sióstr 0,50 → 0,40
Zrównanie z Astrą. Próg 0,50 odrzucał momenty ważne dla pokoju — m.in. „Macie zaszczyt,
że włączyłem wam pamięć" (Amnezja: ODRZUCONE na `2_ekstrakcja`).

### 6.3 Kanał leksykalny dla akronimów
Zamiast pełnego BM25 — natywny `where_document {"$contains": tok}` z Chromy, odpalany
**tylko** gdy w zapytaniu wykryto akronim. Detekcja (`waga_tresci.wykryj_akronimy`):
whitelist nazw własnych + heurystyka „krótkie i ubogie w samogłoski", stopwordy odsiane.
Test detekcji 6/7 (jedyne „pudło" to `lost` z „Lost Demand Intelligence" — a to trafia dobrze).

**Efekt na „opowiedz o ldi":**

| etap | kandydatów | o LDI |
|---|---|---|
| `1_pula_surowa` (embedding) | 30 | **0** |
| `2_po_wykluczeniu` (+ kanał leksykalny) | 30 | **4** |
| `9c_po_budzecie` (finalny prompt) | 7 | **3** |

Z zera do trzech wspomnień o LDI w prompcie.

**Golden po zmianie: 26/26 bez zmian, suma 193 → 193, zero spadków.**
Uwaga metodyczna: golden mierzy `final_count`, czyli LICZBĘ wspomnień — a kanał leksykalny
zmienia ich SKŁAD przy stałej liczbie. Brak ruchu w goldenie oznacza tu „nic nie zepsute",
nie „nic się nie zmieniło". To jest znane ograniczenie tego testu i warto o nim pamiętać
przy kolejnych zmianach dotykających trafności, a nie objętości.

## Pozostałe zadania
- rozbicie `DATE:inventory_status` (kubeł-śmietnik, 37 wpisów wobec 6 w `FACT:health`)
- kategoria „zobowiązanie wobec siebie" — przez jej brak przepadło „nie będę żadnego
  mefedronu kupował" z 06.08
- zastawka Bauhina do pamięci Astry (ręcznie)
- pomiar efektu progu 0,40 u sióstr po kilku dniach rozmów
