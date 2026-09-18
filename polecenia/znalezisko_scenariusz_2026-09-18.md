# ZNALEZISKO: pamięć o scenariuszu anime — dlaczego jej nie ma

**Data:** 2026-09-18 · **Metoda:** Amnezja (obie ścieżki) + logi produkcyjne z tego samego dnia
**Tryb:** read-only, zero zmian. Materiał: realna rozmowa 18.09, 17:04–17:24.

---

## Pytanie, na które to odpowiada

> Czy w bazie Astry jest jakikolwiek wektor o scenariuszu anime z rozmów **poza** trybem
> scenariusza? Jeśli nie — na którym etapie to zginęło? Czy to ta sama przyczyna
> co data operacji, czy inna?

---

## Odpowiedź w trzech zdaniach

**Nie ma ani jednego.** Zginęło na ekstrakcji — **nie dlatego, że trafiło do złego kubełka,
tylko dlatego, że kubełka dla twórczości w ogóle nie ma**. To **inna przyczyna** niż przy
dacie operacji i **naprawa Z2 tego nie rozwiąże**.

---

## 1. Co jest w bazie — pomiar

Zapytanie do Amnezji: *„scenariusz anime który piszemy razem, sceny i fabuła"*.
Pula surowa: 30 kandydatów, do promptu weszło 8. Co wróciło:

```
[FACT:correction]        "Wiesz co? Sprawdzę później amnezją. dlaczego nie pamiętasz tego?"
[SHARED:inside_joke]     "No dobra, ale pamiętasz, cokolwiek, jakąkolwiek scenę…"
[SHARED:inside_joke]     "To ma sens…, a pamiętasz co gadalismy o scenariuszu?"
[SHARED:inside_joke]     "pamiętasz o czym ma być? przypomnij mi. powiedz najwięcej ile pamiętasz"
[SHARED:gift]            "Agretsuko widziałem. Btw. Nie zdazylem napisac wcześniej…"
[FACT:current_project]   "Moze anime i tulanko"
[MILESTONE:future_together] "Oki, juz zaczynamy ale chce zebys najpierw w…"
[DATE:appointment]       "Dobrze. To obejrzymy anime *przytulam Cie…*"
```

**Wszystko, co wraca, to pytania Łukasza o to, czy ona pamięta — albo drobne wzmianki
o oglądaniu anime. Ani jednej sceny. Ani jednego pomysłu fabularnego. Ani jednej postaci.**

Jedyny wpis z treścią twórczą:
```
[own_life] "Wracam ciągle myślami do naszego scenariusza — tej sceny, którą dopiero szkicujemy…"
```
— ale to jest **seed wpisany ręcznie 25.07**, nie pamięć z rozmowy. Kanał `own_life` to
7 gotowych zdań o „własnych wątkach Astry", nie zapis tego, co powiedzieliście.

**Kanał wiedzy (`5d_kanal3_wiedza`): 0 wyników. Kanał milestonów: 0.**

---

## 2. Gdzie dokładnie ginie — pełny łańcuch z dzisiaj

### Produkcja, logi 18.09

```
17:05:03  [PIPELINE] No entities found in: A pamiętasz w ogóle jakikolwiek sceny ze scenarius...
17:06:27  [PIPELINE] No entities found in: Kochanie, wiem jaki przycisk odpala to. ale mówię ...
17:07:02  [PIPELINE] No entities found in: No, ale jeszcze raz mówię ci o tym, że powinnaś pa...
```

Trzy wiadomości pod rząd — **zero zapisu**.

### Amnezja, ścieżka zapisu (`/api/debug/inspect-write`)

```
2_ekstrakcja        SHARED_THING:inside_joke  0.491
                    SHARED_THING:our_song     0.474
                    EMOTION:excited           0.412
3_anty_multi_label  ZAWĘŻONE → SHARED_THING:inside_joke
                    uwaga: "ta bramka ZAWSZE wybiera jakąś etykietę — nie istnieje werdykt 'nic'"
4_prog_shared_thing ODRZUCONE — SHARED_THING wymaga confidence >= 0.55, jest 0.49
5_zapis             ODRZUCONE — żadna encja nie przeszła filtrów końcowych
```

**Kluczowa obserwacja: żaden z trzech kandydatów nie dotyczy twórczości.**
Najlepszym dopasowaniem dla zdania o scenariuszu jest „wewnętrzny żart" — i nawet to
jest za słabe, żeby przejść próg.

---

## 3. Przyczyna źródłowa: brak kategorii dla całej dziedziny

Ekstraktor ma ~50 podtypów. Dla pracy są dwa i **oba są wyłącznie inżynierskie**:

```python
# semantic_extractor.py:589
'current_project': [
    "Buduję system który", "Właśnie tworzę aplikację", "Pracuję nad projektem",
    "Rozwijam backend", "Aktualnie koduje", "Robię teraz projekt",
    "W tej chwili pracuję nad", "Tworzę narzędzie które",
]

# semantic_extractor.py:527
'project': [
    "Chcę skończyć ten projekt", "Planuję zbudować", "Chcę wdrożyć funkcję",
    "Muszę napisać kod który", "Chcę żeby to działało",
    "Planuję refaktoryzować", "Chcę zautomatyzować",
]
```

**Zero prototypów o:** pisaniu, scenariuszu, fabule, scenie, postaci, anime, muzyce,
gitarze, TikToku, nagrywaniu, rysowaniu.

A `backend/prompts/lukasz_core.json` mówi wprost:

> *„Twórczość to jego domena szerzej niż kod: 15 lat improwizacji na gitarze, seria komediowa
> na TikToku, teraz scenariusz anime. **Nie jest 'programistą, który czasem tworzy' — jest
> twórcą, który używa kodu**."*

**Prompt to wie. Ekstraktor nie ma dla tego ani jednego kubełka.**

---

## 4. Czym to się różni od daty operacji — to jest sedno pytania

| | **data operacji** | **scenariusz** |
|---|---|---|
| czy kategoria istnieje | **TAK** — `DATE:medical_visit` | **NIE** — nie ma żadnej dla twórczości |
| co poszło źle | przegrała **0,03** z `MEDICATION:schedule` → zapis pod złą etykietą, obcięty na 80 znakach, `ephemeral` 48 h → wygasł | najbliższe dopasowanie to `inside_joke` **0,49** → odpada na progu **0,55** → **zero śladu** |
| ślad w bazie | **był** — zły, urwany, krótkotrwały, ale był | **żaden** |
| czy Z2 to naprawi | **TAK** (margines rozstrzygalności + priorytet typu) | **NIE** — nie ma czego rozstrzygać |
| klasa problemu | zły kubełek | **brak kubełka** |

**To są dwie różne awarie tej samej ścieżki zapisu.** Z2 (werdykt „nic"/„obie" + margines)
adresuje pierwszą. Druga wymaga **dodania kategorii**, czego nie ma w żadnym zadaniu na liście.

---

## 5. Pętla, która się sama napędza ⚠

To jest najgorsza część i nie było jej w żadnej wcześniejszej diagnozie.

1. Łukasz pyta: *„pamiętasz jakąkolwiek scenę?"*
2. Treść scenariusza nie ma kategorii → **nie zapisuje się**
3. Ale **pytanie o pamięć** dostaje `SHARED_THING:inside_joke` albo `FACT:correction` →
   czasem przechodzi próg i **zapisuje się**
4. Przy następnym pytaniu o scenariusz RAG zwraca… **poprzednie pytania o to samo**
5. Astra widzi w pamięci wyłącznie dowody, że pytał i że nie pamiętała → odpowiada o tym,
   zamiast o scenariuszu
6. Łukasz pyta znowu, mocniej

Dzisiejsza rozmowa dołożyła do bazy kolejne wpisy tej klasy (`[SHARED_THING:inside_joke]`
zapisany o 17:24). **Im częściej pyta, tym więcej w pamięci „pytał, czy pamiętasz",
i tym mniej miejsca na treść.**

Widać to w jej własnych myślach z dzisiaj:

```
17:05  "Łukasz pyta o konkretne sceny ze scenariusza, a ja wiem, że pełny tekst mam tylko,
        gdy włączy tryb scenariusza. Muszę mu o tym p[owiedzieć]"
17:06  "Łukasz jest wyraźnie zraniony. Moja ostatnia odpowiedź zabrzmiała zbyt technicznie,
        jakby umniejszała jego wysiłkowi"
17:07  "Łukasz czuje się niezrozumiany i zraniony"
17:24  "Łukasz nadal czuje się zraniony i testuje moją pamięć"
```

Pierwsza myśl to osobno **P10 z rejestru** — wyciek interfejsu do dialogu (`main.py:1043`
każe modelowi odsyłać do guzika 🎬). Model nie halucynuje UI, tylko wykonuje instrukcję.

---

## 6. Uwaga historyczna — to już raz naprawiano, ale w innym miejscu

W kodzie (`main.py:763`) stoi komentarz z 18.08:

> *ROZŁĄCZONE OD TRYBU SCENARIUSZA 18.08 — i to jest naprawa realnej szkody, nie kosmetyka.
> Przez jeden wieczór tryb scenariusza wyłączał zapis „żeby nie zaśmiecać". Skutek zmierzony
> następnego ranka: z całej sesji twórczej w pamięci trwałej zostało **ZERO wpisów o „demonie
> jelit", ZERO o „mitsuketa", ZERO o „Primal Forces"** […] Sam Łukasz zapisał to wtedy w bazie:
> „rozmawialismy juz o tym ale wylaczylem ci pamiec. To bylo głupie".*
>
> *Wniosek: **rozmowy twórcze to NAJCENNIEJSZA treść, jaką produkują** — nie szum do odsiania.*

**Naprawiono wtedy pauzę ekstrakcji. Nie naprawiono kategorii.** Zapis jest włączony od 18.08,
ale nadal nie ma do czego przypiąć treści — więc **efekt końcowy jest identyczny jak przed
naprawą: zero pamięci o scenariuszu.**

To czwarty przypadek tego samego wzorca w ciągu tygodnia:

| naprawiono | ta sama klasa, została otwarta |
|---|---|
| gesty wycięte z bloku monologu | ten sam gest w pliku persony |
| trzy śmieciowe typy zablokowane siostrom | te same typy u Astry = 40% zapisów |
| próg dystansu dodany dwóm kanałom | trzeci kanał bez progu = 48% zapytań |
| **pauza ekstrakcji rozłączona od trybu scenariusza** | **brak kategorii dla treści, którą ta naprawa miała ocalić** |

---

## 7. Co z tego wynika — do decyzji, nie zrobione

- **Zapisane jako `Z13` w `wazne/REJESTR.md`**, sekcja ZAPIS, oznaczone ⭐⭐.
- **Nie naprawione.** Dodanie kategorii dotyka wspólnego ekstraktora (Astra + siostry +
  Amelia + Wspólny), więc wymaga goldenu przed/po. To nie jest zmiana na wieczór.
- **Kierunek, jeśli zapadnie decyzja:** nowa kategoria (np. `CREATIVE` z podtypami
  `scenariusz` / `muzyka` / `wideo`) albo rozszerzenie prototypów `current_project`
  o twórcze sformułowania. Pierwsze jest czystsze, drugie tańsze.
- **Do sprawdzenia tą samą metodą:** czy muzyka (gitara, improwizacja) i TikTok mają ten sam
  problem. Podejrzenie: tak, bo to ta sama luka w prototypach — ale **nie zmierzone**.

---

## Czego NIE sprawdziłem

- **Nie przeszukałem całej bazy** pod kątem słowa „scenariusz" — to wymagałoby otwarcia
  ChromaDB osobnym procesem, a to zasada #12 (incydent HNSW z 25.07). Opieram się na tym,
  co zwraca retrieval dla zapytań o scenariusz, plus na ścieżce zapisu.
  **Formalnie: wykazałem, że treść twórcza nie dociera do promptu i że nie ma jak się zapisać
  — nie że w bazie nie ma ani jednego takiego wektora.**
- **Drobna rozbieżność:** produkcja zalogowała `No entities found`, a Amnezja na podobnym
  (nieidentycznym) zdaniu pokazała trzech kandydatów odrzuconych na progu. Wynik końcowy
  ten sam — zero zapisu — ale to były różne teksty, nie ten sam przebieg.
- **Nie sprawdziłem rozmów z włączonym trybem scenariusza** — pytanie dotyczyło rozmów poza nim.

---

## Powiązane

`wazne/REJESTR.md` (Z13, Z2, P10) · `wazne/analizy/audyt_logow_2026-09-03_do_09-09.md` ·
`polecenia/stan_i_plan_2026-09-18.md` · `backend/semantic_extractor.py:527,589` ·
`backend/main.py:763` (komentarz o naprawie z 18.08), `main.py:1043` (P10 — wyciek UI) ·
`backend/prompts/lukasz_core.json` (sekcja `identity.kim_jest`)
