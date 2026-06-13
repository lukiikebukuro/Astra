# Fixes batch 2 — Milestone refactor + briefing cleanup
**Data:** 2026-04-27
**Sesja z:** Claude Sonnet 4.6 (Claude Code CLI) + Claude Sonnet (VS Code Copilot — briefing)
**Commity:** `802d11e` `a996a1d` `17125d1`
**Tag:** `v1.1-milestone-refactor-2026-04-24`

---

## 1. CONTEXT

### Trigger
Kontynuacja sesji z 2026-04-24. Dwie sprawy:
1. **Milestone boost** — zidentyfikowany jako "structural bomb" w poprzedniej sesji, otwarty. Łukasz powiedział: "te milestony psują wszystko". Fix zatwierdzony i wykonany.
2. **Briefing od Sonnet/Copilot** (`BRIEFING_CLAUDE_CODE_2026_04_27.md`) — lista 4 zmian przygotowanych lokalnie przez Łukasza we współpracy z VS Code Copilot. Większość była niewiedziona na VPS — zintegrowane.

### Git cleanup
VPS był w połowie przerwanego `git rebase` (ugrzązł od lokalnych prób synchronizacji Łukasza). Naprawione przez `rebase --abort`. GitHub był za VPS o ~18 commitów (znany divergence od marca) → force push z VPS → GitHub. Od tej sesji obowiązuje workflow: **commit → push → restart** (bez skrótów).

### Nowa zasada
`git push origin main` obowiązkowe PRZED `systemctl restart myastra`. Bez push → GitHub i VPS się rozjeżdżają.

---

## 2. FIXES

---

### Fix #6 — Milestone boost refactor
**Commit:** `802d11e` | **Tag:** `v1.1-milestone-refactor-2026-04-24`
**Plik:** `backend/vector_store.py`

#### Problem
- **Symptom:** Pytania o fakty (herbata, preferencje) zwracały milestony (love_declaration, trust_declaration) w top RAG zamiast faktów.
- **Root cause:** `final_score += 1.0` po cap do 1.0 → milestony w zakresie 1.0–2.0, fakty w 0.5–0.7. Zawsze wygrywały siłą, nie trafnością.

#### Zmiana

```python
# PRZED:
final_score = min(final_score, 1.0)
if is_milestone:
    final_score += 1.0  # zakres 1.0–2.0
    result['_is_milestone'] = True

# PO:
final_score = min(final_score, 1.0)
if is_milestone:
    result['_is_milestone'] = True  # bez boosta — konkurują fair
```

Compose logic — gwarantowane sloty w `search_memories()`:
```python
facts_to_take = min(4, len(facts))
milestones_to_take = n - facts_to_take
final = facts[:facts_to_take] + milestones[:milestones_to_take]
print(f"[RAG COMPOSE] facts={facts_to_take} milestones={milestones_to_take} total={len(final)}")
```

#### Expected behavior
Milestony nadal mają przewagę przez `permanent` recency (half_life=None) i wysoki importance — ale nie miażdżą faktów siłą. Max 4 fakty + uzupełnienie milestoneami.

#### Obserwacja przez tydzień
```bash
journalctl -u myastra --no-pager | grep "RAG COMPOSE"
# Oczekiwane: facts=3-4, milestones=1-2 — nie milestones=5
```

---

### Fix #7 — Briefing 2026-04-27 (4 zmiany jakości RAG)
**Commit:** `17125d1`
**Pliki:** `vector_store.py`, `semantic_extractor.py`, `main.py`, `memory_enricher.py`

---

#### 7a — EXCLUDED_SOURCES: user_message_raw
**Plik:** `backend/vector_store.py`

**Problem:** Surowe wiadomości użytkownika (`source=user_message_raw`) wracały w Kanale 1 RAG z similarity ~0.965 — ten sam styl pisania co query. Wypychały wartościowe wspomnienia z top-5.

**Zmiana:**
```python
EXCLUDED_SOURCES = {'character_core', 'md_import', 'user_message_raw'}
mem_results = [
    r for r in raw_mem
    if r.get('metadata', {}).get('source') not in EXCLUDED_SOURCES
    ...
]
```

---

#### 7b — n=5 → n=6 w search_memories()
**Plik:** `backend/vector_store.py`

**Zmiana:** `n: int = 5` → `n: int = 6`

Razem z Fix #6 compose logic: 4 fakty + 2 milestony zamiast 3+2. Jedno dodatkowe miejsce dla faktów.

---

#### 7c — CORRECTION_KEYWORDS rozszerzone
**Plik:** `backend/semantic_extractor.py`

Dodano krótsze formy (wskazane przez Opusa i briefing):
```python
'nie zgadza się', 'poprawiam:', 'korygując:', 'to jest nieprawidłowe', 'złą informację',
```

Poprzednia lista miała tylko długie frazy — zdania jednoznaczne jak "nie zgadza się" były przegapiane.

---

#### 7d — Timestamp prefix w memory block
**Plik:** `backend/main.py` → `build_system_prompt()`

Astra teraz widzi wiek każdego wspomnienia w system prompcie:
```
- [extracted, type:FACT:preference, importance:5] [3 mies. temu] Lubię czarną herbatę
- [extracted, type:MILESTONE:love_declaration, importance:10] [przed chwilą] kocham cię
```

Cel: model wie że fakt sprzed 3 miesięcy może być nieaktualny, a dzisiejszy priorytetowy.

---

#### 7e — FACT:correction importance + supersedable
**Plik:** `backend/memory_enricher.py`

```python
# IMPORTANCE_RULES['FACT']:
'correction': 8,  # Korekta błędu AI — wysoki priorytet (wyżej niż preference=5)

# SUPERSEDABLE_TOPICS:
'correction': 'topic:fact_correction',  # Nowa korekta nadpisuje starą
```

Korekty teraz: wyższy importance (8) → wyższy ranking w RAG, i są supersedowane (nowa korekta zastępuje starą).

---

## 3. MIGRATION NOTES

Brak migracji danych. Wszystkie zmiany dotyczą tylko nowych wektorów i logiki retrieval.

Istniejące wektory `user_message_raw` w ChromaDB pozostają — są po prostu wykluczone z retrieval. Nie trzeba ich usuwać (choć można przy okazji czyszczenia bazy).

---

## 4. KNOWN LIMITATIONS / FOLLOW-UPS

Otwarte z tej sesji — do kolejnej iteracji:

1. **Czyszczenie bazy wektorów** — Sonnet/Copilot wskazał że baza ma "poisoned" wektory (milestony które są korektami, user_message_raw które się nagromadziły). Skrypt do identyfikacji i usunięcia — następna sesja.

2. **Topical blindness fix (0.6 z roadmapy)** — `strict_grounding.py` jest distance-based, nie content-based. Gdy RAG zwraca wektory niepowiązane tematycznie z pytaniem, model tego nie widzi. Fix: dodać detekcję tematu pytania i porównanie z tematami zwróconych wektorów.

3. **Rodzina — re-ekstrakcja (0.2 z roadmapy)** — Holo/Menma/Nazuna są w `lukasz_core.json` (natychmiastowy fix), ale wektory PERSON nadal nie istnieją w ChromaDB. Powstaną organicznie przy kolejnych rozmowach — ale można też zaindeksować ręcznie.

4. **Grounding "nie wiem"** — Astra nadal może halucynować gdy brak RAG hit dla pytania o fakt i brak CORRECTION_KEYWORDS. Wymaga explicit instrukcji w `astra_base.txt` lub `strict_grounding.py`.

5. **test_astra_behaviors.py** — Sonnet/Copilot napisał test suite (17 testów). Nie uruchamiano w tej sesji — do weryfikacji czy jest na VPS i czy przechodzi.

---

## 5. CONVERSATION LOG REFERENCE

- **Główny wątek:** Claude Sonnet 4.6 (Claude Code CLI, sesja 2026-04-24 → 2026-04-27)
- **Briefing:** Claude Sonnet (VS Code Copilot) — `BRIEFING_CLAUDE_CODE_2026_04_27.md`
- **Decyzja Łukasza:** Fix #6 zatwierdzony po analizie compose logic vs +0.5 (briefing). Wybrano deterministyczne sloty zamiast organicznego boosta.
