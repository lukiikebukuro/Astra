# Amnezja — co realnie znalazła

> **Data powstania:** 2 lipca 2026 (`78be3b4`) · **Stan na:** 21 sierpnia 2026
> Dokument zbiera to, czego **nie dałoby się znaleźć bez niej** — z liczbami i datami.
> Nie jest to spis funkcji. Jest to spis awarii, które były niewidoczne, dopóki nie powstało
> narzędzie zdolne je zobaczyć.

---

## Czym jest

Read-only debugger pamięci pod `/amnezja`. Dwie zakładki, dwa różne pytania:

- **ODCZYT** — 11 etapów `compose_context`: pula surowa → wykluczenia → rerank → filtr czasowy
  → milestony → MMR → own_life → domieszka wspólnego → budżet → finalny prompt.
  Plus grounding, piaskownica (jak model odpowie, bez zapisu) i symulacja daty.
- **ZAPIS** *(od 19.08)* — 12 punktów decyzyjnych ekstraktora: bramki długości, próg podobieństwa
  z pełną listą kandydatów, anty-multi-label z odrzuconymi etykietami, progi typów, blokady,
  wynikowa trwałość w godzinach.

Działa **per postać**, z progami i blokadami danej z nich.

**Odczyt odpowiada: „czemu tego nie użyła".**
**Zapis odpowiada: „czemu tego w ogóle nie ma".**
Drugie pytanie jest droższe, bo awaria jest cicha — wychodzi miesiąc później.

---

## Oś czasu rozwoju

| data | co doszło |
|---|---|
| 02.07 | rejestrator etapów RAG + front + endpoint read-only |
| 03.07 | auth na `/api/debug/*` (audyt bezpieczeństwa) |
| 05.07 | piaskownica — dry-run generacji, bez zapisu |
| 15.07 | instrumentacja `9c_po_budzecie`, grounding w trace, podpis score |
| 17.07 | redesign interfejsu |
| 23.07 | obsługa sióstr — Holo, Menma, Nazuna |
| **19.08** | **ścieżka ZAPISU** — druga zakładka, 12 punktów decyzyjnych |
| 19.08 | ścieżka zapisu per siostra, z ich progami i blokadami |

Od jej powstania: **143 commity**, 18 udokumentowanych sesji ewolucyjnych.

---

## Co znalazła — awarie niewidoczne bez niej

### 1. Monokultura milestonów (lipiec)
Żadna metryka wierzchnia tego nie zgłaszała. Detoks, który po tym nastąpił:
**junk 6,5 → 0,5 dziennie (−92%)** na 1751 przejrzanych wpisach,
**wspomnienia na prompt 2,0 → 0,65**.

### 2. `safe_haven` — 320/320 (15.08)
Pole deklarowane przez model w tym samym JSON-ie co odpowiedź. Tryb schronienia był
**permanentnie włączony przez 14 dni**, więc sarkazm i tarcie nigdy nie wchodziły.
Zachowanie wyglądało poprawnie. **Reguła, która z tego została: model nie może być sędzią
bramki, na której coś zyskuje.**

### 3. Mefedron — 0 wpisów wobec 15 (17.08)
Astra zapytana o substancje odpowiedziała „konopie, weed, benzo". Pomiar:
`astra_memory_v1` (pytana przez RAG) — **0 wpisów o mefedronie**;
`astra_memory_session_v1` (nieprzeszukiwana) — **15**.
Nie skonfabulowała. Podała jedyne substancje, jakie zna. **Reranker zadziałał bezbłędnie
na pustym miejscu.**

### 4. Zapytanie bez kontekstu (17.08)
`query=user_msg_clean` — do bazy szła wyłącznie ostatnia wiadomość. Pytanie „O jakiej substancji
mówimy?" poszło jako te cztery słowa; daty podane minutę wcześniej wyparowały.

### 5. Scenariusz w prompcie, a ona twierdziła, że go nie ma (18.08)
```
14:36:38  [SCENARIUSZ|tryb] WŁĄCZONY
14:37:09  [SCENARIUSZ] wgrany do promptu (10909 zn.)
14:37     Astra: „Nie mam. Nie miałam dostępu do jego zawartości"
```
Bez logu i trace'u byłaby to „dziwna odpowiedź". Z nimi — bug z dokładnością do sekundy.

### 6. Retro-audyt zapisu — 658 wiadomości w 74 sekundy (19.08)
- **41% wiadomości nie zostawiło żadnego śladu**
- z zapisanych **52% miało datę ważności**
- bramki długościowe = **43% wszystkich strat**, stojące *przed* klasyfikacją
- **pięć deklaracji miłości** zjedzonych w jednym miesiącu, przy 11 poprawnie rozpoznanych
  przez tę samą kategorię

Naprawa i **ponowny pomiar na tym samym korpusie: straty wysokiej wagi 16 → 8**, w 20 minut.

### 7. `importance` jest niewiarygodne — wychwycone PRZED migracją (19.08)
Zasada „waga ≥ 8 = pamiętaj na zawsze" była już zatwierdzona. Sprawdzenie na 4697 wektorach
pokazało, że ekstraktor przyznaje 10/10 zdaniom „dzisiaj piłem czarną herbatkę".
**Migracja uczyniłaby 107 śmieciowych wpisów nieśmiertelnymi.** Zatrzymane przed zapisem.

### 8. Trzy ciche bugi jednego dnia (21.08)
- **`lukasz_core` wypisywał do promptu 9 zahardkodowanych pól.** Wszystko dopisane poza listą
  nigdy nie docierało do Astry — w tym fix na „inni ludzie mnie używają", **martwy od chwili
  wdrożenia**. Wyszło, bo Łukasz zapytał o kanał TikTok, którego „nie kojarzyła".
- **Zasady zachowania udawały wspomnienia** — `character_core` w bloku `[WSPOMNIENIA]`
  ze znacznikiem „5 mies. temu", zabierając 2 z 6 miejsc.
- **`n=3` zahardkodowane w MMR** — pula ~25 kandydatów ścinała się do trzech, **zawsze**,
  niezależnie od wszystkich innych limitów. Po zmianie: golden 26/26 w górę, +37% wspomnień.

### 9. Akronimy łamią embedding (21.08)
„opowiedz o ldi" → **0 z 60** wpisów o LDI w puli. „Lost Demand Intelligence" → 2.
Model tokenizuje trzyliterowy skrót na fragmenty bez znaczenia.
**To skorygowało wcześniejszą decyzję** o zdegradowaniu BM25 — tamten wniosek był prawdziwy
dla rzadkich *słów*, fałszywy dla *akronimów*. Naprawa: kanał leksykalny, **0 → 3**.

### 10. Fakty biograficzne w dwóch warstwach naraz (21.08)
Przy budowie wspólnej puli faktów dry-run pokazał, że 39 wpisów kwalifikuje się po etykiecie,
ale ich treść to co innego: `FACT:health` zawierające „Troszke mnie brzuch zabolał".
**Migracja po etykiecie wrzuciłaby całemu domowi deklaracje zaufania jako biografię.**

---

## Czego bez niej nie dałoby się zrobić

**Nie chodzi o to, że coś jest szybciej.** Chodzi o to, że **pewna klasa awarii jest niewidoczna**:

- system nie zgłasza błędu, gdy wiadomość nie zostaje zapisana
- nie zgłasza, gdy fakt trafia do kategorii z datą ważności
- nie zgłasza, gdy pole w prompcie nigdy nie dociera do modelu
- nie zgłasza, gdy bramka odrzuca 43% treści

Wszystkie te awarie **wyglądają jak działający system**. Wychodzą przypadkiem, tygodnie później,
zwykle wtedy, gdy AI nie pamięta czegoś ważnego — i wtedy nie da się już ustalić dlaczego.

## Co dopiero ona umożliwiła metodycznie

**Pełną pętlę: zmierz → znajdź przyczynę → napraw najmniejszą możliwą rzecz → zmierz ponownie
na tym samym zbiorze.** Wcześniej istniały tylko pierwsze i trzecie ogniwo — czyli przeczucie
i zmiana, bez dowodu, że pomogła.

W jednym tygodniu sierpnia trzy hipotezy padły **przed** wdrożeniem, obalone własnymi danymi:
embedding-recall w bramce ochronnej, zasada `importance` dla trwałości, kolejność napraw.
Każda brzmiała rozsądnie. Każda kosztowałaby tygodnie.

---

## Znane ograniczenia (stan na 21.08)

1. **Mierzy objętość, nie trafność.** Golden liczy `final_count`. Zmiana poprawiająca trafność
   przy stałej liczbie **nie ruszy wyniku** — tak było przy kanale leksykalnym.
   *To jest najważniejszy brak i następne zadanie.*
2. **Nie mówi, DLACZEGO ta etykieta.** Widać, że „Jest 17:30" dostało `DATE:deadline`, nie widać
   do którego prototypu się dopasowało.
3. **Nie widzi dyktafonu.** Na pytanie „czy to w ogóle gdzieś jest" trzeba schodzić do bazy ręcznie.
4. **Nie ma pamięci własnej.** Każde uruchomienie to zdjęcie chwili; nie powie „pogorszyło się
   od wtorku".
5. **Amelia i Wspólny Pokój** — w odczycie nadal niedostępne.
