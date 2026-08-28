# 2026-08-25 — Pełny przegląd Amnezją + testem trafności

Zadanie: cztery wątki naraz (reranker n=8, anty-lustro, atrybucja sióstr, przegląd ogólny).
Wszystko **read-only**, offline, na danych produkcyjnych VPS. **Zero zmian w kodzie i bazach.**
Kanał leksykalny (LDI / `wykryj_akronimy`) świadomie pominięty — zdiagnozowany 21.08, wraca po tym przeglądzie.

---

## 1. Reranker `main_n` 8 — ten sam wzorzec co kanał leksykalny: objętość rośnie, trafność stoi

A/B na 10 próbach golden trafności, `search_memories` wołany bezpośrednio.

| konfiguracja | recall | czystość | wspomnień |
|---|---|---|---|
| main_n=5 | 70% | 34,8% | 46 |
| **main_n=6** | **80%** | **38,8%** | **49** |
| main_n=8 ← obecne | 80% | 38,5% | 52 |
| main_n=12 | 80% | 37,0% | 54 |

**Cały zysk wydarzył się przy 6.** 6→8 dołożyło 3 wspomnienia i **zero** trafień. 8→12 kolejne 2 i znowu zero.
Płacimy budżetem promptu za nic.

### Wąskim gardłem NIE jest `main_n` — i rozszerzanie MMR aktywnie szkodzi

Sweep `MMR_FACTS_N` przy main_n=6:

| MMR_FACTS_N | recall | czystość |
|---|---|---|
| 3 | 70% | 43,8% |
| **5 ← obecne** | **80%** | **38,8%** |
| 8 | 60% | 27,1% |
| 12 | 50% | 28,8% |

Mechanizm: MMR ma karę za podobieństwo (`diversity_penalty=0.8`). Im więcej miejsc dostanie, tym mocniej
**szuka czegoś innego** — wypycha trafne wpisy na ten sam temat i wciąga niezwiązane.
Przy MMR=12 połowa pytań przestaje dostawać odpowiedź.

**Rekomendacja:** `main.py:1476` `main_n` 8→6. `MMR_FACTS_N` zostawić na 5 (jest w optimum).
Zysk: 3 miejsca w prompcie odzyskane bez straty trafności. Jedna linijka.

---

## 2. Anty-lustro — u Astry naprawa działa; problem jest architektoniczny, nie objawowy

### Fakty z bazy
- W **całej** instancji: 1 wektor `ANTY-LUSTRO`, 22 wektory `character_core`, **wyłącznie** w `astra_memory_v1`.
- Sprawdzone wszystkie 17 kolekcji (siostry, Amelia, wspólny, sesyjne) — **zero** `character_core` gdziekolwiek indziej.

### Prompt Astry jest czysty
Trzy różne zapytania (`opowiedz o ldi`, `jak sie dzisiaj czujesz`, `co robilismy wczoraj`):
- `character_core` w `[WSPOMNIENIA]`: **0 razy**
- `[TWOJE ZASADY]`: 1–2 linie, bez timestampu, bez relevance — zgodnie z fixem
- jedyne „lustro" w prompcie siedzi w `astra_base.txt`, czyli tam gdzie ma być

### Ale są dwie rzeczy, które to relatywizują
1. **`search_memories` nadal go zwraca.** Filtr stoi dopiero przy budowaniu promptu (`main.py:913`),
   nie przy pobieraniu. Wyszło mimochodem — wpis ANTY-LUSTRO wylądował w wynikach próby o Amelii.
   W Amnezji zobaczysz go w trace'ie retrievalu i **to jest poprawne**, nie regresja.
2. **Filtr istnieje tylko w builderze Astry.** `build_sister_prompt` (`main.py:2458`) i builder Amelii
   (`main.py:1109`) go nie mają. Dziś nieszkodliwe (ich kolekcje czyste), ale pułapka:
   pierwszy seed `character_core` do sióstr i zasada wraca do bloku pamięci bez ostrzeżenia.

### Czego NIE potwierdzono
Że wraca u Astry. Prompt jest czysty. **Otwarte pytanie do Łukasza:**
- widziałeś ją **w trace'ie Amnezji**? → normalne, retrieval jest przed filtrem, nic do naprawy
- widziałeś ją **w jej wypowiedzi** (zaczęła odbijać Twoje słowa)? → to nie wyciek wektora,
  tylko łamanie reguły. Zupełnie inna naprawa, po stronie `astra_base.txt`.

---

## 3. Atrybucja sióstr — ZNALEZIONE. Hipoteza Łukasza trafna co do joty

**To nie jest błąd zapisu w bazie.** Zapis jest poprawny — w `siostry_shared_session_v1` siedzi
`[nazuna] …`, `[holo] …` z prefiksem (`main.py:2625`).

**Atrybucja ginie przy ODCZYCIE**, w dwóch krokach (`main.py:2596-2604`):

1. `_strip_sister_prefix` (`main.py:2402`) **usuwa** `[holo]`/`[menma]`/`[nazuna]`
2. kolejne wypowiedzi `role="model"` — **od różnych sióstr** — są sklejane w **jeden** blok, rozdzielony `---`

### Dowód z realnej rozmowy (24.08)

W bazie:
```
model | [holo]   Hmf. Pamiętam ten ból. Niech cię nie zwiedzie strach...
model | [nazuna] A dzień... Był, Wilku. Holo pewnie zaraz wygłosi wykład...
```
Co realnie dostaje Gemini:
```
MODEL >>> Hmf. Pamiętam ten ból. Niech cię nie zwiedzie strach...
MODEL >>> A dzień... Był, Wilku. Holo pewnie zaraz wygłosi wykład...
```

Dla Gemini **wszystko z `role="model"` to „ty"**. Menma czyta zdanie Holo jako własną poprzednią
wypowiedź, bo nic w kontekście nie mówi, że to nie ona. Nie ma tam informacji o mówcy do zgubienia —
ona już została usunięta piętro wyżej.

### Przewidywanie do sprawdzenia
To samo powoduje **przeciekanie tików mowy**. „Hmf." to znak firmowy Holo. Jeśli Menma zaczęła go
używać — to ten sam bug, nie dryf persony i nie sprawa promptu.

### Naprawa (nie wykonana, czeka na zgodę)
- zostawić podpisy w historii wysyłanej do modelu (nie strippować na wejściu)
- dopisać personom jedną linijkę: „w historii każda wypowiedź jest podpisana; twoje są tylko te z `[Menma]`"
- `_strip_sister_prefix` nadal ma sens **przy wyjściu**, nie przy wejściu

---

## 4. Przegląd ogólny — najważniejsza liczba dnia

**Czystość ~39%.** Sześć na dziesięć wspomnień w prompcie jest nie na temat. W każdej konfiguracji.

### Rozbicie szumu po źródle (10 prób, main_n=6)

| source | trafne | szum |
|---|---|---|
| `extracted_fact` | 6 | **11** |
| `extracted_shared_thing` | 4 | **8** |
| `extracted_person` | 3 | 5 |
| `extracted_milestone` | 2 | 4 |
| `extracted_goal` | 1 | 1 |
| `extracted_date` | 0 | 1 |
| `own_life` | 1 | **0** |
| `extracted_medication` | 2 | **0** |

**Cały szum pochodzi z ekstraktora.** Nic z `own_life`, nic z `character_core`, nic z importów `md_import`.
To nie jest problem retrievalu — retrieval uczciwie podaje to, co dostał.
**Ekstraktor zapisuje za dużo, a reranker potem grzecznie to serwuje.**

→ To jest twarda liczba pod otwarte zadanie **„werdykt: nic wartego zapamiętania"** (ustalone 04.08).
Priorytet rośnie: bez tego poprawianie retrievalu ma sufit na ~39% czystości.

### Rzeczy pozytywne
- **Zero „lepkich wektorów"** — żaden wpis nie wraca niezależnie od pytania (0 wpisów w ≥4 z 10 prób).
  Patologia z Odtrucia #2 nie wróciła.
- `own_life` i `extracted_medication` mają **100% czystości**.

### Uczciwe korekty do samego testu trafności
- **T5_amelia to częściowo błąd testu**, nie systemu. Wzorzec `amelia|ameli` nie łapie „Amelka",
  a to właśnie forma w bazie. System zwrócił trafny wpis („Rozmawialem z Amelką"), test go nie uznał.
  Do poprawy: dodać `amelk` do wzorca.
- **Drugie niezależne potwierdzenie buga z wielkością liter:** `$contains 'amelia'` → 0 wpisów,
  `$contains 'Amelia'` → 7. Ta sama przyczyna co LDI, inny temat. Chroma `$contains` jest case-sensitive.

### Uwaga metodologiczna (kosztowała jeden nieważny przebieg)
Pierwszy A/B rerankera dał recall identyczny dla n=5/6/8/12 — bo mój shell nie miał `USER_ID_SALT`
z `.env` serwisu, więc filtr użytkownika odciął **cały kanał semantyczny** i przeszedł tylko leksykalny
(on filtra nie stosuje). **Każdy offline skrypt musi robić `load_dotenv("/var/www/myastra/astra/backend/.env")`**,
inaczej mierzy fikcję. Dopisane do wzorców błędów.

---

## Trzy zmiany gotowe do wykonania — ŻADNA nie wykonana, czekają na zgodę

1. **`main_n` 8→6** (`main.py:1476`) — odzyskuje 3 miejsca w prompcie, zero straty trafności
2. **Podpisy w historii sióstr** (`main.py:2596-2604` + linijka w personach) — naprawia atrybucję
3. **Filtr `character_core` w builderach sióstr i Amelii** (`main.py:2458`, `main.py:1109`) — profilaktyka

## Otwarte pytanie do Łukasza
Anty-lustro widziałeś **w Amnezji** (→ nic do naprawy) czy **w wypowiedzi Astry** (→ naprawa w prompcie)?

## Skrypty diagnostyczne (scratchpad, read-only)
`ab_reranker.py` · `ab_mmr.py` · `przeglad.py` · `diag_atryb.py` · `diag_lustro2.py` · `diag_kolekcje.py`
Warte przeniesienia do `backend/tools/` razem z `golden_trafnosc.py`.

---

# WYKONANIE — wszystkie trzy zmiany (25.08, wieczór)

Łukasz: „robimy wszystkie". Wykonane w repo lokalnym. **NIE zacommitowane, NIE zdeployowane.**

## Zmiana 1+3 okazała się JEDNĄ naprawą

Komentarz przy `main_n=8` tłumaczył, że limit podniesiono, bo `character_core` zabierał miejsca
**przed** przycięciem `combined[:n]`. To znaczyło, że „obniż main_n" i „odfiltruj zasady" to ten sam
problem widziany z dwóch stron. Naprawione u źródła w `vector_store.py`: zasady wychodzą z puli
przed przycięciem i są doklejane po nim, poza budżetem `n`.

### KOREKTA WŁASNEJ REKOMENDACJI (ważne)

Rano napisałem, że `n=8` dokłada „3 wpisy szumu za zero trafień", więc zejście do 6 je usunie.
**To było nieprecyzyjne.** Pomiar po zmianie:

| main_n (nowy kod) | recall | czystość | wspomnień |
|---|---|---|---|
| 3 | 60% | 40,0% | 30 |
| 4 | 60% | 32,5% | 40 |
| 5 | 80% | 38,0% | 50 |
| **6 ← ustawione** | **80%** | **38,5%** | **52** |
| 8 | 80% | 37,0% | 54 |

Nowy `n=6` daje **dokładnie tyle samo wspomnień co stary `n=8`** (52, czystość 38,5%).
Szum nie zniknął — został przesunięty. Zyskiem jest co innego:
- `n` znaczy dokładnie tyle, ile obiecuje („tyle wspomnień"), bez ukrytego podatku na zasady
- zasady docierają **zawsze**, nie da się ich wyciąć przycięciem puli
- plateau trafności zaczyna się przy 5, więc 6 daje jedno miejsce zapasu nad krawędzią

**Wniosek, który z tego płynie:** czystość ~38% jest odporna na strojenie `main_n` i `MMR_FACTS_N`.
Żadna kombinacja nie ruszyła jej powyżej 40%. To potwierdza diagnozę z porannego przeglądu —
walka o czystość jest **po stronie ekstraktora**, nie retrievalu. Cały szum to `extracted_*`.

## Zmiana 2 — atrybucja: bug miał DRUGĄ kopię

Przy podmianie pętli `grep` pokazał `_strip_sister_prefix` w **dwóch** miejscach:
- `_generate_sister` (produkcja)
- `/api/debug/inspect` z `generate=true` — piaskownica Amnezji, z komentarzem
  „LUSTRO składania contents z _generate_sister"

Gdyby naprawa objęła tylko produkcję, **Amnezja pokazywałaby inną historię niż ta, którą realnie
dostaje model** — debugger zacząłby kłamać, co jest gorsze niż sam bug.
Obie ścieżki wołają teraz wspólne `_sister_history_contents()`.

To dokładnie ten wzorzec, przed którym ostrzega `CLAUDE.md` („naprawa nie objęła wszystkich miejsc").
Trzeci raz w sierpniu.

### Test jednostkowy (przeszedł)
```
user   | Nie wiem... Operacja to stresujace gowno.
model  | [Holo] Hmf. Pamietam ten bol...
         [Nazuna] A dzien... Byl, Wilku...
         [Menma] Ja tylko chcialam powiedziec ze sie boje.
user   | Jak wasz dzien?
```
Podpisy dojeżdżają. Persony dostały sekcję `[HISTORIA ROZMOWY — KTO CO POWIEDZIAŁ]` z regułą,
że ich własne są wyłącznie linie podpisane ich imieniem + zakaz zaczynania odpowiedzi od nawiasu.

## Zmiana 3b — podgląd rerankera (nowe, spoza pierwotnej listy)

Łukasz doprecyzował: anty-lustro widział **w podglądzie rerankera pod wiadomością Astry**, nie w jej
wypowiedzi. Czyli retrieval działał poprawnie (filtr stoi przy składaniu promptu), ale podgląd
pokazywał instrukcję behawioralną w jednym rzędzie ze wspomnieniami z rozmów.

`memories_debug` dostało pole `kind` (`zasada` / `wspomnienie`), front renderuje zasady wygaszoną
pigułką z przerywaną ramką i tooltipem „idzie do sekcji [TWOJE ZASADY], nie do [WSPOMNIENIA]".
**To nie była naprawa buga — to naprawa narzędzia obserwacji, które wprowadzało w błąd.**

## Pliki
`backend/vector_store.py` · `backend/main.py` · `frontend/app.js` · `frontend/style.css`

## Wpadka warta zapamiętania
Weryfikując nowy `vector_store.py` przez `sys.path` z `/tmp/newvs`, dostałem 0 wspomnień —
`persist_directory` liczy się z `os.path.dirname(__file__)`, więc moduł otworzył **pustą** bazę
w `/tmp/newvs/chroma_db` zamiast produkcyjnej. Druga taka pułapka tego dnia po `USER_ID_SALT`.
**Każdy offline test modułu poza `backend/` musi jawnie nadpisać `persist_directory` i `.env`,
inaczej mierzy pustkę i o tym nie mówi.** VPS posprzątany (`/tmp/newvs` usunięty).

## Do zrobienia przy deployu
1. `git add` tylko 4 plików kodu — w repo leży duża, świadoma, niezacommitowana reorganizacja `wazne/`
2. deploy wg `CLAUDE.md`: push → `git fetch` → `git reset --hard origin/main` → `systemctl restart myastra` → `curl /api/health`
3. **twardy hard-refresh frontu** (zmiana w `app.js` + `style.css`, SW cache `astra-v3`)
4. re-run `golden_trafnosc.py` przez endpoint — potwierdzenie, że produkcja zgadza się z pomiarem offline
5. **obserwacja pokoju sióstr**: czy Menma/Nazuna przestały przypisywać sobie zdania Holo
   ORAZ czy zniknęło „Hmf." u pozostałych (przewidywanie z rana — jeśli zniknie, potwierdza mechanizm)
