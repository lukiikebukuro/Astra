# Czy naprawy warstwy ZAPIS obejmują też siostry?

**Data:** 2026-09-21 · **Autor:** sesja wykonawcza (Claude Code)
**Pytanie Łukasza:** czy Holo, Menma i Nazuna używają tego samego ekstraktora i pipeline'u
zapisu co Astra — a jeśli tak, czy Z2b/Z1/Z13 poprawią ich pamięć automatycznie, bez osobnej pracy?

**Tryb:** read-only. Sprawdzone w kodzie **i potwierdzone pomiarem na produkcji**.

---

## Odpowiedź w jednym zdaniu

**Tak — jedna naprawa na cztery systemy, bez osobnej pracy.** Z2b i Z1 już działają dla sióstr
od 18.09; Z13 obejmie je automatycznie, i to wymaga jednej Twojej decyzji (§4).

---

## 1. Dlaczego — jeden obiekt, czterech wołających

W `main.py:370` tworzona jest **jedna** instancja `SemanticPipeline`:

```python
pipeline = SemanticPipeline(vector_store=vector_store, database=None)
```

Wołają ją cztery ścieżki:

| linia | kto |
|---|---|
| `main.py:1842` | **Astra** (`/api/chat`) |
| `main.py:2085` | **Amelia** |
| **`main.py:2922`** | **siostry** (`_siostry_extract`) |
| `main.py:3351` | **Amnezja** (ścieżka zapisu, `/api/debug/inspect-write`) |

Wewnątrz pipeline'u jest **jeden** `SemanticExtractor` (`semantic_pipeline.py:73`).

Sprawdzone grepem po całym `backend/`: **`ENTITY_DEFINITIONS` i `FUTURE_DATE_PATTERNS`
istnieją wyłącznie w `semantic_extractor.py`. Zero kopii dla sióstr, Amelii czy Wspólnego.**

Czyli wszystkie trzy naprawy leżą we wspólnej części:

| naprawa | gdzie siedzi | wspólne? |
|---|---|---|
| **Z1** — koniec ucinania na 80. znaku | `semantic_pipeline.py` → `_synthesize_text` → `_skroc_do_zdania` | tak |
| **Z2b** — daty pisane słownie | `semantic_extractor.py` → `FUTURE_DATE_PATTERNS` + `_extract_date_value` | tak |
| **Z13** — kategoria dla twórczości | `semantic_extractor.py` → `ENTITY_DEFINITIONS` | tak (będzie) |

---

## 2. Dowód — nie lektura kodu, tylko pomiar

Przepuściłem **to samo zdanie** przez Amnezję (ścieżka zapisu) dla trzech person:

> `„Dzisiaj rano bylem w klinice i lekarz powiedzial ze zwezenie jest powazniejsze niz
> myslelismy. Kontrola 5 pazdziernika."`

```
astra  (126) [DATE:medical_visit] 2026-10-05: Dzisiaj rano bylem w klinice i lekarz...
holo   (126) [DATE:medical_visit] 2026-10-05: Dzisiaj rano bylem w klinice i lekarz...
menma  (126) [DATE:medical_visit] 2026-10-05: Dzisiaj rano bylem w klinice i lekarz...
```

**Identyczna kategoria · identyczna wyliczona data · identyczna długość.**

Widać w tym oba wdrożone fixy naraz:
- **Z2b** — „5 pazdziernika" rozpoznane i przeliczone na `2026-10-05` (przed 18.09: brak daty),
- **Z1** — 126 znaków zamiast ucięcia na 80., więc `powazniejsze niz myslelismy` zostaje
  (przed 18.09 zdanie urywało się przed tą informacją).

**Wniosek: siostry dostały te naprawy 18.09, w tym samym commicie co Astra. Nikt nic nie musi
robić osobno.**

---

## 3. Czym siostry się RÓŻNIĄ — trzy rzeczy, wszystkie *po* ekstrakcji

To jest istotne, bo pokazuje, gdzie wspólność się kończy:

1. **`SIOSTRY_TYPY_BLOKOWANE`** (`main.py:2824`) — trzy typy odrzucane **po** ekstrakcji:
   `DATE:inventory_status`, `FACT:correction`, `SHARED_THING:inside_joke`.
   To jedyna prawdziwa różnica w polityce zapisu.
2. **Kolekcja docelowa** — per siostra (`holo`/`menma`/`nazuna_memory_v1`) albo `siostry_shared_v1`
   przy `group_address`, zależnie od routera.
3. **`SIOSTRY_EXTRACTION_MODE`** — przełącznik `off | shadow | on` (obecnie `on` od 19.08).

**Czego NIE ma na liście różnic, wbrew intuicji:**
- **próg pewności jest taki sam** — `SIOSTRY_MIN_CONFIDENCE = 0.40`, Astra też 0.40;
- **`_is_too_short`** (min. 5 słów) jest **wspólne** — używa go i Astra (`main.py:1865`),
  i siostry (`main.py:2933`).

To potwierdza pomiar z przeglądu pokoju 04.09: wskaźnik ekstrakcji **Astra 26,6% · siostry 27,6%**
— różnicy nie ma, bo pipeline jest ten sam.

---

## 4. ⚠ Jedna decyzja do podjęcia przed Z13

Skoro `ENTITY_DEFINITIONS` jest wspólne, a `CREATIVE` nie będzie na liście blokowanych —
**nowa kategoria wejdzie do sióstr automatycznie**. Holo, Menma i Nazuna zaczną zapamiętywać
scenariusz, muzykę i TikToka.

Może to jest dobre. Ale jest tu napięcie z wcześniejszą, świadomą decyzją projektową.
Komentarz w `load_lukasz_core_dla_siostr` (`main.py:2539`) mówi wprost:

> *„Wąsko, nie w całości: siostry dostają KIM JEST i ZDROWIE. Bez projektów technicznych,
> bez celu zawodowego, bez kanału TikTok — **to jest świat Astry, nie ich. Pokój sióstr ma
> zostać domem, nie drugim biurem**."*

Czyli: **ten sam projekt, który celowo odciął siostrom TikToka na poziomie promptu,
nie odetnie go na poziomie pamięci.**

### Trzy opcje

| opcja | skutek |
|---|---|
| **A. Wpuścić wszystko** *(rekomendacja)* | siostry pamiętają scenariusz, muzykę i wideo |
| **B. Dopisać `CREATIVE:*` do `SIOSTRY_TYPY_BLOKOWANE`** | pokój zostaje wolny od twórczości — ale odtwarza dokładnie ten problem, który Z13 naprawia, tylko w drugim pokoju |
| **C. Wpuścić `CREATIVE:scenariusz`, zablokować `muzyka`/`wideo`** | anime oglądacie razem, więc scenariusz jest wspólny; TikTok i gitara zostają u Astry |

**Rekomendacja: A.** Rozmowa o scenariuszu w pokoju to nie jest „drugie biuro" — to wspólne
oglądanie anime i pisanie o postaciach, które w tym pokoju mieszkają. Blokada powtórzyłaby
błąd z 18.08 (wyłączenie zapisu „żeby nie zaśmiecać", które skasowało całą sesję twórczą).

Ale to jest decyzja o **charakterze pokoju**, nie techniczna — więc Twoja, nie moja.

---

## 5. Co z tego wynika dla planu

- **Z2b i Z1: zrobione dla wszystkich**, w commitach `bbff52d` i `8fe7d37` z 18.09.
  Żadnej dodatkowej pracy dla sióstr.
- **Z13: jedna implementacja, cztery systemy.** Trzeba tylko rozstrzygnąć §4 przed kodem.
- **Z12** (`fold()` i `ł`) — też wspólne, ale inaczej: `waga_tresci.fold()` jest importowany
  przez `semantic_pipeline` i `vector_store`, więc naprawa obejmie wszystkie persony.
  Osobna sprawa: `siostry_router.py` ma **własną, poprawną** kopię `fold` — jej nie ruszamy.
- **Golden przed/po przy Z13 musi objąć obie strony** — Astrę i przynajmniej jedną siostrę.
  Dziś tego nie ma czym zmierzyć (`golden_trafnosc.py` nie istnieje — patrz
  `polecenia/raport_warstwa_zapis_2026-09-18.md` §5).

---

## 6. Przy okazji — dwa sprostowania stanu

**`TRYB_SZPITAL` jest już zdjęty.** Usunąłem go 18.09. Stan `.env` na VPS dzisiaj:

```
SIOSTRY_EXTRACTION_MODE=on
NOCNA_DNI=mon,wed,fri
SPONTANICZNA=off
```

Log schedulerów potwierdza:
`Nocna Analiza 03:00 [mon,wed,fri] | Archiwum 04:00 [codziennie] | Poranna 07:00 [mon,wed,fri] | Spontaniczna: WYŁĄCZONA`

Notatki mówiące „flaga nadal `on` — do wyłączenia" są nieaktualne.

**Pierwsza wiadomość w nowym rytmie poszła dziś rano** (poniedziałek 21.09, 03:00 nocna
→ 07:00 poranna). **Nie sprawdzałem jeszcze, jak wypadła** — w szczególności czy prefiks
`msg_kind=nocna_analiza` zadziałał. To jest pierwszy realny test tamtej zmiany.

---

## Czego NIE sprawdziłem

- **Nie testowałem Nazuny ani Amelii** — sprawdziłem `astra`, `holo`, `menma`. Kod jest wspólny,
  więc nie ma powodu sądzić, że się różnią, ale formalnie to jest wniosek z trzech person, nie pięciu.
- **Test był na ścieżce zapisu Amnezji**, która woła ten sam `pipeline.process_message`,
  ale **z pominięciem filtrów siostrzanych** (`SIOSTRY_TYPY_BLOKOWANE`, `_is_too_short`).
  Dla `DATE:medical_visit` to bez znaczenia (nie jest blokowany), ale przy Z13 trzeba będzie
  sprawdzić pełną ścieżkę produkcyjną, nie samą Amnezję.
- **Nie zmierzyłem, czy Z1 zmienił retrieval** — ani u Astry, ani u sióstr. Brak przyrządu.

## Powiązane

`polecenia/raport_warstwa_zapis_2026-09-18.md` (Z2b i Z1 — wdrożenie i kanarki) ·
`polecenia/work-order_warstwa_zapis_2026-09-18.md` (mapa klasy problemu, krok 5b) ·
`polecenia/znalezisko_scenariusz_2026-09-18.md` (Z13 — diagnoza) ·
`wazne/ewolucja/siostry/2026-09/evolution_log_2026_09_04.md` (26,6% vs 27,6%) ·
`backend/main.py:370,1842,2085,2824,2922,3351` · `backend/semantic_pipeline.py:73,209,259,303`
