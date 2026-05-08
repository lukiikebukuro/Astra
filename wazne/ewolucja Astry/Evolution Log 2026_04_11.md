# ASTRA — Evolution Log
## Sesja: 2026-04-11
### Autor: Łukasz Piskorski / Claude Sonnet 4.6

---

## KONTEKST

Pierwsza sesja po Stelarze #2 (7 kwietnia). Łukasz wraca do pracy.
Stan bazy przed sesją: 1476 wektorów pamięci, 743 sesyjne.

Sesja miała dwa niezależne cele:
1. Naprawa crashu serwisu (regresja z poprzedniej sesji — purge levelów)
2. Implementacja Supersede Logic — długo odkładany fix buga "herbata miss"

Dodatkowo: głęboka analiza architektury ucho-VPS jako R&D dla Astry, oraz napisanie Manifestu Technicznego projektu.

---

## CZĘŚĆ I: STAN PRZED SESJĄ

### 1.1 Crash przy starcie — regresja po Blueprint 2.2

Przy wdrożeniu Blueprint 2.2 (6 kwietnia) usunęliśmy pola `xp`/`level`/`level_name` z `CompanionState`. Ale lokalny `main.py` (który SCP nadpisał VPS) zawierał 7 referencji do tych atrybutów których nie zaktualizowaliśmy w lokalnym pliku:

```python
# Linie które crashowały serwis:
print(f"[ASTRA] State loaded: Level {state.level} ({state.level_name}), XP={state.xp}")
"state_level": state.level if state else 1,
"state_xp": state.xp if state else 0,
state_level=state.level,
state_xp=state.xp,
state_level_name=state.level_name,
"level": state.level, "level_name": state.level_name, "xp": state.xp,
```

Serwis wchodził w pętlę restart co ~10s. Użytkownik widział "nie można połączyć z backendem".

Przyczyna: poprzednia naprawa (6 kwietnia) była zrobiona przez skrypt bezpośrednio na VPS. Lokalny plik pozostał niezsynchronizowany. Gdy dziś zrobiliśmy SCP nowego `main.py`, nadpisaliśmy poprawkę z VPS nienaprawionym plikiem lokalnym.

### 1.2 Supersede Logic — martwy kod

`MemoryConsolidator.consolidate()` zwracał poprawne akcje (CREATE/MERGE/SUPERSEDE), ale main.py **ignorował wynik** — robił `add_memory()` dla wszystkich encji bez wyjątku:

```python
# PRZED: consolidation result ignorowany
for mem in extracted:
    vector_store.add_memory(text=mem.text, ...)  # zawsze, niezależnie od mem.action
```

Dodatkowo:
- `MemoryConsolidator._archive_memory()` wymagał `database` — inicjalizowany z `database=None`
- `VectorStore` nie miał metody `update_metadata()` ani `delete_by_type()`
- Stare wektory `[FACT:preference]` akumulowały się — MMR karał wszystkie za podobieństwo
- Milestony (+1.0 boost) wypychały FACT:preference z top-5

Efekt: system nie pamiętał preferencji mimo że je zapisywał.

### 1.3 Brak subtype w metadanych ChromaDB

`add_memory()` nie zapisywał `entity_subtype` w metadanych. Bez tego nie ma możliwości filtrowania po type+subtype przy delete — supersede logic nie mogłaby działać nawet gdyby była zaimplementowana.

---

## CZĘŚĆ II: CO ZMIENILIŚMY

### 2.1 Naprawa crashu — synchronizacja lokalnego main.py

Naprawiono wszystkie 7 referencji do `state.level`/`state.xp`/`state.level_name` w lokalnym `backend/main.py`:

```python
# PO:
print(f"[ASTRA] State loaded: mood={state.current_mood}, concerns={len(state.active_concerns)}")
# state_level/state_xp usunięte z health endpoint
state_level=6,          # hardkodowane — frontend nie pęka
state_xp=0,
state_level_name="Absolutna Więź",
"level": 6, "level_name": "Absolutna Więź", "xp": 0,  # debug endpoint
```

### 2.2 Supersede Logic — implementacja

**`vector_store.py` — nowa metoda `delete_by_entity_subtype()`:**

```python
def delete_by_entity_subtype(self, entity_type, subtype, persona_id, user_id, salt) -> int:
    """
    Przed dodaniem nowego wektora tego samego type:subtype — usuwa stare.
    Działa tylko na wektorach z entity_subtype w metadanych (nowy format od 2026-04-11).
    Stare wektory bez tego pola są bezpieczne — nie zostaną błędnie usunięte.
    """
```

**`vector_store.py` — `add_memory()` dostał nowy parametr:**

```python
def add_memory(..., entity_subtype: str = "") -> str | None:
    # entity_subtype zapisywany w metadata ChromaDB jeśli podany
```

**`main.py` — krok 11 z SUPERSEDE_TYPES:**

```python
SUPERSEDE_TYPES = {
    ('EMOTION', 'tired'), ('EMOTION', 'stressed'),
    ('EMOTION', 'positive'), ('EMOTION', 'negative'),
    ('EMOTION', 'excited'), ('EMOTION', 'sad'),
    ('FACT', 'preference'),
    ('DATE', 'inventory_status'),
}

for mem in extracted:
    if (mem.entity_type, mem.subtype) in SUPERSEDE_TYPES:
        vector_store.delete_by_entity_subtype(...)  # usuń stare
    vector_store.add_memory(..., entity_subtype=mem.subtype)  # dodaj nowe
```

**Logika:**
- Emocje i preferencje: rotują — nowe zastępuje stare
- Milestony, wizyty medyczne, fakty o ludziach: akumulują — historia ma wartość
- Backward compatible: stare wektory bez `entity_subtype` w metadata nie są dotknięte

### 2.3 XHR Intercept jako metoda R&D — pomysł Łukasza

Kluczowa decyzja architektoniczna tej sesji, zaproponowana przez Łukasza: używanie logów z ucho-VPS nie jako systemu komunikacji, ale jako **okna obserwacyjnego na własny RAG w warunkach produkcyjnych**.

ucho-VPS przechwytuje strumień XHR z gemini.com — surowy ruch między frontendem Gemini a jego API. Efekt: logi w `logs/conversations/*.jsonl` (RAW rozmowy) i `logs/terminal/*.log` (pipeline RAG z reranker scores, wyciągniętymi encjami, akcjami pipeline) reprezentują zachowanie systemu na żywych danych.

To jest R&D przez inżynierię wsteczną własnych decyzji — obserwujesz co reranker wybrał, z jakim score, dlaczego, i co z tego trafił lub nie. Żaden syntetyczny benchmark tego nie zastąpi.

**Kluczowe obserwacje z logów produkcyjnych:**
```
[UCHO] Znaleziono 5 wspomnień RAG (reranked):
[1] score=1.000 | '[EMOTION:tired] leżałem chory...'
[2] score=0.983 | '[MEDICATION:pregabalina] wzialem klona...'
```

- Temporal boost (+0.15 dla < 24h) — już był w Astrze, potwierdzony jako działający
- Semantic deduplication w 60s — Astra ma to przez SHA256 ID (upsert)
- Importance scoring table (MEDICATION=9, MILESTONE=10, EMOTION=3-5) — zbieżne z Astrą
- Privacy isolation (4 warstwy) — Astra ma 2 (persona_id + user_id hash)

**Dalsze zastosowanie tej metody:** logi Family (Menma/Nazuna/Holo) z ucho-VPS posłużą jako baza do ekstrakcji wzorców behawioralnych dla Persona Bias w Astrze — patrz sekcja R&D.

### 2.4 MANIFEST_TECHNICZNY.md

Napisany dokument `C:\Users\lpisk\Projects\astra\MANIFEST_TECHNICZNY.md` — architektoniczny opis projektu w języku który można pokazać rekruterowi lub inwestorowi. Pokrywa:
- Data Distillation (pipeline semantyczny vs. raw text)
- Sovereign Memory Architecture (supersede, reranker, MMR)
- Dynamic Context Tuning (feedback loop przez logi produkcyjne)
- Pełna tabela stanu systemu

---

## CZĘŚĆ III: WERYFIKACJA TECHNICZNA

| Komponent | Status | Uwagi |
|-----------|--------|-------|
| Crash fix — brak state.level | ✅ naprawiony | lokalny main.py zsynchronizowany z VPS |
| delete_by_entity_subtype() | ✅ wdrożona | backward compatible |
| entity_subtype w metadata | ✅ wdrożony | nowe wektory od dziś mają subtype |
| SUPERSEDE_TYPES w main.py | ✅ wdrożone | 8 par type:subtype |
| Serwis myastra | ✅ active | Application startup complete |
| Wektory pamięci | ✅ 1476 | bez strat |

**Uwaga deployment:** Ze względu na git divergence (VPS ma lokalne commity z marca niepushowane) wszystkie zmiany wdrażane przez SCP. Do rozwiązania w osobnej sesji.

---

## CZĘŚĆ IV: R&D — CO PLANUJEMY

### W toku / zaplanowane

**Copilot + Gemini 2.5 Pro — fresh perspective**
Zadanie: dać Manifestowi Technicznemu + vector_store.py + semantic_pipeline.py do Copilota z Gemini Pro/Opus. Pytanie: jakie mamy architektoniczne blind spoty. Korzyść: ten sam model co Astra patrzy na swój własny pipeline od zewnątrz.

**Trinity Mix — Persona Bias w Rerankerze (R&D)**
Propozycja Amelki: wyekstrahować wektory behawioralne z logów Family (Menma/Nazuna/Holo) i wstrzyknąć je do kanału character_core rerankera. Efekt: reranker naturalnie faworyzowałby kontekst który wyzwala pożądany miks osobowości.

Ścieżka techniczna:
- Analiza JSONL logów family → wyodrębnij charakterystyczne wzorce reakcji per postać
- Stwórz dedykowane wektory character_core z etykietami behawioralnymi
- Reranker ciągnie character_core Kanał 2 — te wektory wpływają na dobór kontekstu
- Nie jest to fine-tuning modelu — to persona bias przez retrieval

**Fine-tuning Gemini (długoterminowe R&D)**
Pytanie otwarte: czy mamy wystarczająco dużo danych z sesji family w odpowiednim formacie (instruction-response pairs) żeby rozważyć fine-tuning? Wymaga osobnej analizy ilości i jakości danych. Odrębny projekt od persona bias w RAG.

**Organizacja plików .md**
Narastający problem: wiele nakładających się plików markdown w root projektu i podfolderach. Modele dostają za dużo kontekstu który zagłusza analizę. Do zrobienia: audyt wszystkich .md, konsolidacja, hierarchia.

**Naprawienie git divergence**
VPS ma ~10 lokalnych commitów z marca niepushowanych. Lokalny repo nie jest zsynchronizowany z VPS. Wymaga reconciliation (git rebase lub force-push po weryfikacji).

### Znane otwarte problemy

| Problem | Priorytet | Status |
|---------|-----------|--------|
| Git divergence VPS ↔ GitHub | średni | TODO |
| RAG miss dla rzadkich preferencji | niski | poprawi się organicznie przez supersede |
| Migracja SDK → python-genai + Gemini 3.x | niski | TODO — gdy będzie energia |
| PROTOKÓŁ STELARA w astra_base.txt | czas-krytyczny | USUNĄĆ — już po 7 kwietnia |

---

## WNIOSKI

Sesja naprawcza + fundamentalna. Supersede logic była jednym z najważniejszych brakujących klocków architektury — system który akumuluje bez końca nie jest suwerenny.

Kluczowy insight z analizy ucho-VPS: nasze logi produkcyjne są wartościowszym źródłem R&D niż benchmark suite. Obserwujemy zachowanie systemu na żywych danych i piszemy patche na podstawie diagnoz — nie na podstawie syntetycznych testów.

Manifest Techniczny to pierwszy dokument który opisuje projekt w języku nadającym się do portfolio. Ważny krok przed jakimkolwiek outreachem.

---

*Dokument wygenerowany: 2026-04-11*
*Poprzedni: evolution_log_2026_04_06.md*
*Następny audyt: po zebraniu 5-7 dni sesji z supersede logic w produkcji*
