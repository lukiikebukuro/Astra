# STAN AMNEZJI — dokument żywy

> **To NIE jest log.** Log mówi „co się stało 28.08" i jest prawdziwy na zawsze.
> Ten dokument mówi **„co Amnezja widzi DZISIAJ"** i jest prawdziwy tylko dopóki go aktualizujemy.
>
> **ZASADA: zmieniasz cokolwiek w Amnezji — aktualizujesz ten plik W TYM SAMYM COMMICIE.**
> Nieaktualny dokument stanu jest gorszy od jego braku, bo kłamie z pewną miną.

**Ostatnia aktualizacja:** 2026-08-28 · **Commit:** `5459981` + naprawy z audytu

---

## Czym Amnezja jest

Read-only debugger RAG-a. Dwie zakładki:
- **ODCZYT** (`/api/debug/inspect`) — 16-etapowy ślad drogi wspomnienia do promptu
- **ZAPIS** (`/api/debug/inspect-write`) — przewód decyzyjny ekstraktora, dry-run

Kluczowa właściwość: **`compose_context` jest WSPÓLNA** dla produkcji i debuggera.
Amnezja nie symuluje produkcji — używa tego samego kodu.

---

## Co Amnezja widzi (macierz pokrycia)

| ścieżka | lustro | uwagi |
|---|---|---|
| `chat` — Astra | ✅ pełne | wspólna `compose_context` **i** wspólna `_astra_history_contents` (od 28.08) |
| `_generate_sister` — siostry | ✅ pełne | wspólna `_sister_history_contents` (od 25.08) |
| `amelia_chat` | ❌ brak | — |
| `_wspolny_generate` | ❌ brak | — |
| `_scene_as_found` — narrator sceny | ❌ brak | — |
| `nocna_analiza.py` — nocna + poranna | ❌ brak | **najboleśniejsza luka**, patrz niżej |

**Dwie z sześciu ścieżek generacyjnych.** Trzynaście miejsc w kodzie składa `contents` ręcznie —
każde z nich to potencjalny rozjazd lustra.

---

## Niezmienniki, które trzymają (stan zweryfikowany)

Sprawdzane przez `backend/tools/audyt_amnezji.py` na 5 zapytaniach. **Wszystkie przechodzą.**

- **I1** — żaden wpis w `8_final` nie pojawia się znikąd; każdy ma źródło we wcześniejszym etapie
- **I2** — `9c_po_budzecie` ⊆ `9b_final_prompt`; budżet nie wymyśla wpisów
- **I3** — każdy wpis z `9c` realnie ląduje w prompcie
- **I4** — liczba linii w prompcie zgadza się z `9c` **co do jednej**

Znaczenie: **od momentu, w którym wpis wejdzie do trace'u, Amnezja prowadzi go uczciwie do końca.**
Historycznie dziura była wyłącznie na wejściu — patrz następna sekcja.

## Etapy trace'u (16)

```
0_zapytanie_z_kontekstem · 1_pula_surowa · 2_po_wykluczeniu · 2b_po_kanale_leksykalnym
3_po_reranku · 4_po_temporal · 5_milestony · 6_po_mmr_facts · 7_kanal1_final
5b_own_life · 5c_kanal2_zasady · 5d_kanal3_wiedza
8_final · 9a_domieszka_shared · 9b_final_prompt · 9c_po_budzecie
```

**Dodając nowy kanał do `search_memories` — dodaj `_rec(...)` ORAZ dopisz nazwę do
`ETAPY_ZRODLOWE` w `tools/audyt_amnezji.py`.** Bez tego audyt zgłosi naruszenie, którego nie ma.

---

## Znane luki — stan otwarty

### L1. Ścieżki proaktywne bez wglądu (priorytet najwyższy)
Poranna, nocna analiza i popołudniowa nie mają lustra. To **tam** gryzły zmyślone daty
(„wczorajsze CV" o zdarzeniu sprzed trzech dni) i znikająca wiadomość dnia — czyli bugi,
które kosztowały najwięcej sesji. Dwa wywołania Gemini w `nocna_analiza.py`, poza `main.py`.

### L2. Amelia i Wspólny Pokój bez lustra
Amelia ma dokładnie te same mechanizmy co Astra i zero wglądu. Wspólny — świadomie nie ruszany.

### L3. `entity_type` nie istnieje w metadanych
Na 4729 wektorach Astry: `entity_subtype` obecny na 3732, `entity_type` na **zerze**.
`vector_store.py` przekazuje go do `compute_persistence`, ale nie zapisuje.
`main.py` ma cichy fallback na `source`, przez co każda linia promptu powtarza to samo słowo
dwa razy (`[extracted_fact, type:extracted_fact, ...]`). Skutki: filtrowanie po typie
w metadanych jest niemożliwe, plus marnowane tokeny w każdej turze.
**Naprawa addytywna, bez migracji starych wektorów.**

### L4. Przewód ZAPISU nie jest pokazany w UI
Endpoint zwraca komplet: wszystkich kandydatów z confidence, zwycięzcę, odrzuconych,
importance, trwałość. **„Dlaczego ta etykieta" jest już zbudowane — brakuje tylko widoku.**
Zakładka sama się denuncjuje: `"ta bramka ZAWSZE wybiera jakas etykiete - nie istnieje werdykt 'nic'"`.

### L5. Amnezja nie widzi trendu
Brak wymiaru czasu: nie da się zobaczyć, czy pamięć poprawia się z tygodnia na tydzień.

---

## Historia napraw (skrót — szczegóły w audytach i logach)

| data | co | dlaczego to było groźne |
|---|---|---|
| 2026-08-25 | wspólna `_sister_history_contents` | piaskownica miała kopię buga atrybucji |
| 2026-08-28 | etapy `5c_kanal2_zasady`, `5d_kanal3_wiedza` | ~25% promptu bez rodowodu |
| 2026-08-28 | rozdzielone `2_po_wykluczeniu` / `2b_po_kanale_leksykalnym` | etap „po wykluczeniu" potrafił rosnąć |
| 2026-08-28 | wspólna `_astra_history_contents` | piaskownica generowała z innego promptu niż produkcja |

**Wzorzec, który wrócił dwa razy:** lustro debuggera jako osobna kopia kodu.
Za każdym razem naprawa produkcji nie objęła kopii albo odwrotnie.
**Reguła: lustro NIGDY nie jest osobnym kodem — zawsze wspólna funkcja.**

---

## Narzędzia

- `backend/tools/audyt_amnezji.py` — niezmienniki I1–I4, read-only, kod wyjścia 0/1/2
- `wazne/fable/golden/golden_trafnosc.py` — trafność retrievalu; **stoi na Amnezji**,
  więc jej wiarygodność jest warunkiem wstępnym dla wszystkich pomiarów trafności
- `wazne/bugi/pomiar_klamie.md` — czytać PRZED każdym pomiarem

## Powiązane dokumenty
- `wazne/debugger/audyt_amnezji_2026-08-28.md` — pełny raport z pierwszego audytu (metody A–E)
- `wazne/ewolucja/astra/2026-08/evolution_log_2026_08_25.md` — tabele A/B rerankera i MMR
