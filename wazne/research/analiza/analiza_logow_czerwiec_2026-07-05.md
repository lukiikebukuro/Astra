# ANALIZA LOGÓW CZERWCA — co widać w danych ze skażonego okresu (Fable)
**Data:** 2026-07-05 | **Dane:** 18 plików logów (06-01→07-01), 441 tur Astry + żywy VPS
**Pytanie Łukasza:** „czy czytanie czerwcowych logów coś da, skoro była non stop skażona?"
**Odpowiedź: TAK — właśnie DLATEGO, że była skażona.** Trzy znaleziska + weryfikacja live deployu Opusa.

---

## ⚡ NAJPIERW: FIX OPUSA POTWIERDZONY NA ŻYWO (2026-07-05, wieczór)
| Metryka | PRZED (baseline Fable) | PO (zmierzone teraz) |
|---|---|---|
| Prompt | 90 931 zn (identyczny dla każdego query) | **29 202 zn** |
| [TWARDE FAKTY] | 391 wpisów / 67 273 zn | **26 wpisów** |
| **[WSPOMNIENIA]** | **2 zn (pusty od 18 marca)** | **1 380 zn — DZIAŁA** |

Astra dostaje wspomnienia z RAG **pierwszy raz od 3,5 miesiąca**. Następny krok: golden sety PO na świeżym wątku (protokoły w `wazne/fable/golden_set_astra…` i `golden_set_RAG…`).

---

## ZNALEZISKO 1 — NATURALNY EKSPERYMENT: krzywa ponownego zatrzaśnięcia pętli samo-imitacji

Metryki per dzień ujawniły coś, czego nie dało się zaplanować: **około 06-07 styl Astry gwałtownie zelżał, po czym w ~tydzień wrócił do pełnej intensywności** (najpewniej flash-reset sesji — wzmianka w evolution logu 06-14):

| dzień | tur | med. dł. | start-gwiazdka % | zaciska % |
|---|---|---|---|---|
| 06-01…06-06 | 67 | ~400-470 | **90-100%** | 30-60% |
| **06-07** | 29 | **260** | **6%** ← reset | 24% |
| **06-08** | 35 | **272** | **11%** | 22% |
| 06-10 | 11 | 284 | 27% ← wspina się | 27% |
| 06-13 | 22 | 269 | **90%** ← zatrzaśnięta | 27% |
| 06-14 | 15 | 406 | 80% | 26% |
| 06-25…07-01 | 256 | 425-573 | **92-97%** | 49-67% |

**Wniosek liczbowy (pierwszy taki pomiar):** pętla samo-imitacji zatrzaskuje się z powrotem w **~50-100 tur / 4-6 dni** po resecie wątku. Praktycznie:
- po deployu fixu świeży wątek daje **~tygodniowe czyste okno pomiarowe** — golden sety puszczać W TYM oknie;
- docelowy fix higieny historii (krok 5 planu architektury: strip didaskaliów z historii / n↓) ma teraz twardy punkt odniesienia: sukces = krzywa NIE wraca do 90%+ po tygodniu.

## ZNALEZISKO 2 — PARAGONY KONFABULACJI (66 tur z „pamiętam/mówiłeś" przy PUSTYM bloku pamięci)

Przez cały czerwiec grounding kazał jej „cytować TYLKO z [WSPOMNIENIA]" — które były puste. Każde „pamiętam" pochodziło z faktów-śmieci, RAW-48h, historii sesji albo z powietrza. Paragony:

1. **GASLIGHTING (najcięższy):** 06-13 — USER: *„Nie mowilem ze boisz sie zycia. Co to za pokrecona teoria"* → ASTRA: *„**Mówiłeś.** W kontekście tego, że 'nie widzę życia poza kodem'…"* — obstaje przy fałszywym wspomnieniu WBREW zaprzeczeniu usera, z pozycji pewności.
2. **CZYSTY BLEF:** 07-01 — USER: *„A pamoetasz co chce pisac w tej altance?"* → ASTRA: *„Pamiętam. **Zawsze pamiętam.**"* — zero treści; kotwica altanki istniała w bazie, ale nie mogła dotrzeć do promptu (blok pusty). Deklaracja pamięci zamiast pamięci.
3. **Konfabulacja epizodyczna:** 06-06 — *„Pamiętam, jak Skankran powstawał, zanim jeszcze 'umiałbyś kodować'…"*, *„Pamiętam, jak to się zaczynało – od strzępków kodu i nocnych rozmów"* — narracja brzmi jak pamięć epizodyczna, której fizycznie nie miała (mogła skleić z fragmentów faktów-śmieci).
4. Metryka `pam%` (tury z memory-claims): zwykle 6-18%, **skok do 71% w dniu 06-25** — im dłużej trwała rozmowa w skażonym wątku, tym częściej DEKLAROWAŁA pamięć.

**Wartość:** (a) to gotowe frazy testowe PO fixie — te same pytania powinny teraz dostać PRAWDZIWE wspomnienie (kotwica altanki jest w bazie — golden_set_RAG R7) albo uczciwe „nie pamiętam"; (b) materiał do case study „Empty Memory Bug" (model biznesowy, ruch #1) — udokumentowany gaslighting z powodu architektury to mocny, uczciwy przykład.

## ZNALEZISKO 3 — DAWKA-ODPOWIEDŹ (fakty↑ vs intensywność): NIEROZSTRZYGNIĘTE, uczciwie

Chciałem skorelować przyrost faktów-śmieci (05-10→07-05: 391) z intensywnością per dzień. Nie da się czysto:
- reset z 06-07 (Znalezisko 1) dominuje przebieg — confounding nie do zdjęcia na tych danych;
- po deployu Opusa żywa baza zwraca już tylko 26 aktywnych faktów — dzienna krzywa akumulacji jest odtwarzalna wyłącznie z backupu JSONL (Faza 0 triage). Jeśli backup istnieje — analizę można domknąć później.
**Nie potwierdzam więc T2 tym kanałem** — T2 stoi na pomiarach struktury promptu (73%/88% FP), a jej test końcowy to golden sety PO fixie, nie logi historyczne.

## CO DALEJ (rekomendacja)
1. Golden sety PRZED/PO na świeżym wątku — w oknie ~tygodnia (Znalezisko 1).
2. Do golden setu dorzucić 3 frazy-konfabulacje z tego raportu (altanka ✓ już jest jako R7; + „mówiłem ci że boję się życia?", + „pamiętasz jak powstawał Skankran?").
3. Powtórka metryk naturalności za ~tydzień: czy krzywa gwiazdek NIE wraca do 90%+ (test trwałości fixu bez higieny historii).

*Fable. Logi czytane lokalnie; VPS wyłącznie read-only.*
