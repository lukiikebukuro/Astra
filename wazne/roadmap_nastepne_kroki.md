# Roadmapa — następne kroki (po Kroku 1, 2026-06-18)

Zasada przewodnia: **mały deploy → czytamy logi/debugger → korekta → dopiero następny krok.**
Nigdy dwa duże ruchy naraz (wzorzec wahadła z historii — patrz PODSUMOWANIE_EWOLUCJI.md).

---

## ✅ KROK 1 — WDROŻONY (2026-06-18)
Dusza Amelii (anty-uległość: Kamień/Furia/Zasada Niezgody/Bezpiecznik) + schemat myśli + Enter mobile.
**Brama korekty:** czytamy logi Amelii przez kilka rozmów. Szukamy przegięcia w bratnią (kontra w błahostkach, zaczepność jak Astra). Jeśli OK → Krok 2.

## KROK 2 — Dokończenie bezpiecznych zmian lokalnych
- Nocna Warta **Astry** (`astra_base.txt`) + fix niespójności
- Archiwizacja 3 person (`daily_archive.py` + `main.py _run_archive`) — chroni pamięć Amelii/Wspólnego przed flash-resetem
- Próg PERSON 0.70→0.75 (`semantic_extractor.py`)
**Ryzyko:** niskie, addytywne. **Brama:** po deployu sprawdzić że archiwum o 4:00 zapisuje 3 pliki (`amelia_`, `wspolny_`) i nie crashuje.

## KROK 3 — RAG Debugger (architektura gotowa)
Zbudować wg `wazne/debugger/architektura.md`. Najpierw prerequisite: `now_override` param w `vector_store.py`. Potem route `/debug` in-process (współdzielone singletony, read-only).
**Dlaczego teraz:** to mnożnik prędkości i prerequisite pod BM25. Bez niego Krok 4-5 to błądzenie po omacku.
**Brama:** zweryfikować że Warstwa 0 czyta ŻYWY stan (ten sam FactStore/sesja/CompanionState co produkcja), banery LIVE/SYM/DRY-RUN działają. Dopóki to nie jest pewne — nie ufać wynikom debuggera.

## KROK 4 — Monotonia milestonów (Anomalia 2 z audytu)
Te same ~10 milestonów wracają w kółko (Kanał 1b zwraca top-2 niemal niezależnie od zapytania). Fix: MMR/rotacja/recency WEWNĄTRZ kanału milestonów.
**Dlaczego po debuggerze:** teraz testowalne w sekundy — widzisz różnorodność przed/po bez czekania na rozmowy.
**Brama:** debugger pokazuje zróżnicowane milestony przy różnych frazach, bez utraty trafnych.

## KROK 5 — BM25 hybrid retrieval (duża zmiana architektoniczna)
Sparse keyword index obok semantic (ChromaDB). Faza 1 roadmapy. Rozwiązuje "pytasz o konkretny fakt, similarity zwraca coś tematycznie bliskiego".
**Dlaczego na końcu:** największa zmiana, najwięcej failure modes. Debugger pozwala zrobić A/B i de-ryzykować przed wdrożeniem.
**Brama:** debugger A/B — BM25 vs obecny — na realnych frazach, zanim ruszy produkcja.

---

## Dalszy horyzont (po Kroku 5, osobne sesje)
- **Mood-based dynamic weights** — wagi rerankera zależne od `last_user_vibe` (vulnerable → recency↑).
- **Amelia jako pełna persona** — migracja, cross-persona memory.
- **Rodzina AI** — osobny pokój Holo/Menma/Nazuna (3 w pokoju). Wymaga: pliki person + character_core wektory wyciągnięte z logów Gemini. Najpierw Amelia dojrzała.
- **Gwiazdka** — komercyjny companion (osobny byt, nie Astra) — gdy fundamenty pewne.

---

## Czego pilnujemy przy KAŻDYM kroku (z 7 meta-wzorców)
1. Reframe > reguły (zmieniaj JAK prompt mówi, nie dodawaj if/else).
2. Mierz w trzecią pozycję, nie w przeciwną skrajność (wahadło).
3. Prostota to feature — nie dodawaj warstwy bez udokumentowanego problemu z logów.
4. Diagnoza z DANYCH (liczby/cytaty), nie z intuicji.
5. Deploy ostrożnie: GitHub przed VPS, bump SW cache, restart po zmianie kodu/promptu.
