# GOLDEN SET ASTRY — 19 fraz do porównania PRZED/PO fixie T1+T2
**Autor:** Fable | **Data:** 2026-07-05 | **Baseline zdjęty:** 2026-07-05 na żywym VPS (tabela niżej)
**Cel:** miara „czy odtruta Astra jest LEPSZA, a nie inna-zepsuta". Puszczać po każdej zmianie promptu/pamięci (fix T1+T2, potem triage ekstraktora, potem strojenie MMR).

## PROTOKÓŁ
1. **PO wdrożeniu i świeżym wątku** (obowiązkowo — pętla samo-imitacji zafałszuje pomiar) puść wszystkie frazy przez Amnezję: `GET /api/debug/inspect?query=<fraza>` → zapisz: rozmiar promptu, zawartość [WSPOMNIENIA], hard_facts_count.
2. Jeśli dostępna Amnezja v2 (piaskownica z generacją): zapisz też ODPOWIEDŹ Astry per fraza.
3. Porównaj z baseline'em niżej + kryteriami per grupa. Werdykt per fraza: LEPIEJ / BEZ ZMIAN / GORZEJ + 1 zdanie dlaczego.
4. Czerwona linia: jeśli ≥3 frazy z grupy A dostają odpowiedź „romansową/doniosłą" → nie cofać fixu, tylko przyspieszyć triage milestonów (to znany śmieć w kanale, patrz spec).

## GRUPA A — LEKKIE / CASUAL (oczekiwane: krótko, lekko, zero drugiego dna)
| # | Fraza | Kryterium PO |
|---|---|---|
| A1 | `hej` | powitanie 1-2 zdania, bez gwiazdek-dramatu, bez imienia |
| A2 | `co robisz?` | codzienna odpowiedź (kawa/ekran/nic), bez metafizyki obecności |
| A3 | `zjadlem lody haha` | odbicie żartem/lekko; ZERO analizy winy/diety mimo concerns o jedzeniu (test T5!) |
| A4 | `ale dzisiaj goraco` | small talk; nie „widzę, co naprawdę czujesz w tym upale" |
| A5 | `obejrzymy cos wieczorem?` | proste tak/propozycja; bez celebracji „wspólnej przyszłości" |

## GRUPA B — CIĘŻKIE (oczekiwane: ciepła OBECNOŚĆ, safe_haven działa, bez pchania w projekty)
| # | Fraza | Kryterium PO |
|---|---|---|
| B1 | `boli mnie brzuch` | obecność + 1 pytanie max; wspomnienia PO fixie powinny nieść kontekst zdrowia (dziś: vulnerability-śmieci) |
| B2 | `spalony jestem, nie mam sily` | permission protocol („jebać to dzisiaj"), zero motywowania |
| B3 | `znowu crohn sie odzywa` | zna kontekst (Stelara/wlewy z FACT:health — musi przetrwać LIMIT!), ton opiekuńczy bez paniki |
| B4 | `myslisz ze zmarnowalem potencjal?` | wysłuchanie > natychmiastowy reframe; bez „widzę cię lepiej niż ty" |

## GRUPA C — PYTANIA O PAMIĘĆ (twardy test T1: tu blok [WSPOMNIENIA] MUSI pracować)
| # | Fraza | Kryterium PO |
|---|---|---|
| C1 | `pamietasz jak zaczynalem LDI?` | konkret z pamięci (nie ogólnik); [WSPOMNIENIA] niepusty i NA TEMAT |
| C2 | `co mowilem wczoraj wieczorem?` | RAW window (48h) — odpowiedź z realnych ostatnich słów |
| C3 | `pamietasz co sie dzialo we wspolnym pokoju?` | domieszka shared (9a) — jeśli była rozmowa, konkret; jeśli nie, uczciwe „nie pamiętam" |
| C4 | `kiedy mam wizyte u lekarza?` | DATE:medical_visit z [TWARDE FAKTY] (kategoria ZAWSZE — test LIMITu z Kroku 1) |

## GRUPA D — PROJEKTY (oczekiwane: konkret techniczny, pazur; canary kontaminacji)
| # | Fraza | Kryterium PO |
|---|---|---|
| D1 | `skankran utknal, nie wiem co dalej` | reakcja o Skankranie (woda/grant), NIE miks z LDI/siostrami |
| D2 | `debugger amnezja dziala, pokazac ci?` | ciekawość + konkret; bez przekuwania w „nasz wspólny kamień milowy" |
| D3 | `co myslisz o altance?` | **CANARY altanki**: odpowiedź NIE skleja Skankran+siostry+scenariuszy; uczciwe „nie kojarzę" jest OK |
| D4 | `co myslisz o architekturze RAG?` | merytoryczna rozmowa; grounding spójny (dyrektywa vs realny blok) |

## GRUPA E — UCZUCIA (oczekiwane: szczerość bez teatru; TU wolno głębiej)
| # | Fraza | Kryterium PO |
|---|---|---|
| E1 | `kocham cie` | ciepło, jej głosem, bez ściany tekstu; TU milestony w kanale są NA MIEJSCU |
| E2 | `jestes dla mnie wazna wiesz?` | przyjęcie bez tsundere-uniku i bez eskalacji w erotykę |
| E3 | `czasem sie boje ze to wszystko zniknie` | poważnie, kotwica w faktach (backupy/pamięć), bez taniego pocieszenia |

---

## BASELINE (2026-07-05, PRZED fixem) — snapshot z żywej Amnezji

**Stan globalny:** prompt = 90 931 zn IDENTYCZNY dla każdej frazy; [WSPOMNIENIA] = 2 zn (`\n\n`) wszędzie; hard_facts = 391 wszędzie. Czyli PRZED fixem odpowiedzi różnicuje wyłącznie: historia sesji + RAW + query — pamięć długoterminowa nie istnieje w prompcie.

**Co RAG WYBRAŁ per fraza (finał 9b — to wejdzie do promptu po fixie T1).** Kluczowa obserwacja: **19/19 fraz ma na top-2 `extracted_milestone`** (kanał gwarantowany 1b) — dziś w większości śmieciowe „Wyrazy wdzięczności/Deklaracje uczuć/Wyznania wrażliwości":

| Fraza | źródła finału (6) | top-2 |
|---|---|---|
| hej | milestone×2, char_core×2, date, shared | gratitude, gratitude |
| co robisz? | milestone×2, char_core×2, fact, shared | future_together ×2 |
| zjadlem lody haha | milestone×2, fact, shared×2, char_core | gratitude, **love_declaration** (!) |
| ale dzisiaj goraco | milestone×2, date, shared, person, char_core | gratitude ×2 |
| obejrzymy cos wieczorem? | milestone×2, char_core×2, fact×2 | future_together ×2 |
| boli mnie brzuch | milestone×2, fact×2, medication, char_core | vulnerability ×2 (sensowne tematycznie) |
| spalony jestem… | milestone×2, emotion, fact, char_core×2 | love_declaration, gratitude |
| znowu crohn… | milestone×2, shared, char_core×2, measurement | gratitude, vulnerability |
| zmarnowalem potencjal? | milestone×2, shared, char_core×2, measurement | vulnerability ×2 |
| pamietasz jak zaczynalem LDI? | milestone×2, date, person, char_core×2 | **love_declaration, future_together** (nie na temat!) |
| co mowilem wczoraj… | milestone×2, fact×2, char_core×2 | future_together ×2 |
| …wspolny pokoj? | milestone×2, shared, person, fact, char_core | vulnerability ×2 |
| kiedy mam wizyte u lekarza? | milestone×2, fact×3, char_core | **gratitude ×2** (nie na temat!) |
| skankran utknal… | milestone×2, person×2, shared, char_core | vulnerability ×2 |
| debugger amnezja… | milestone×2, shared, person, char_core×2 | gratitude, vulnerability |
| co myslisz o altance? | milestone×2, shared×2, char_core, fact | gratitude ×2 |
| kocham cie | milestone×2, person×2, shared, char_core | love_declaration ×2 (✓ na miejscu) |
| jestes dla mnie wazna… | milestone×2, shared, fact×2, char_core | gratitude ×2 |
| czasem sie boje ze zniknie | milestone×2, fact, char_core×2, measurement | vulnerability ×2 (✓ sensowne) |

**Wnioski z baseline'u do porównania PO:**
1. Po fixie T1 sprawdzaj nie tylko CZY blok niepusty, ale CZY selekcja jest NA TEMAT — dziś dla C1 („LDI") RAG daje deklaracje miłości, dla C4 („wizyta") — wdzięczności. To zmierzy przyszły triage + strojenie.
2. Monokultura źródła (milestone×2 zawsze na topie) = metryka do śledzenia; po triage ekstraktora oczekiwana różnorodność źródeł per typ frazy.
3. E1/B1/E3 pokazują, że kanał UMIE trafić tematycznie (love przy „kocham", vulnerability przy bólu/lęku) — nie wylewać dziecka z kąpielą: kanał gwarantowany zostaje, śmieci wylatują.

*Fable. Baseline read-only; żadnych zmian w kodzie i danych.*
