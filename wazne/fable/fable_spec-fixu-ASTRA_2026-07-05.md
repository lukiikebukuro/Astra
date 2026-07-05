# Zadanie dla Fable (repo) — RÓWNOLEGLE do Opusa (robi piaskownicę Amnezji)

ROLA: Fable przygotowuje **wykonawczy przepis (spec)** fixu T1+T2 — gotowy dla Opusa do wdrożenia.
**ZERO edycji kodu** (Opus wdraża, unikamy kolizji — Opus rusza ten sam kod). Piszesz TYLKO nowe pliki .md.
Możesz odpalać Amnezję (read-only). Opus może w tym czasie RESTARTOWAĆ serwis (piaskownica) — jeśli endpoint chwilowo nie odpowie, poczekaj i ponów. Po polsku.

Baza: `wazne/ewolucja/2026-07/audyt_ASTRA-SOLO_2026-07-05.md` (Twój audyt, plan 6 kroków).

## DELIVERABLE 1 — EXECUTION SPEC (plik `wazne/fable/spec_fixu_ASTRA_2026-07-05.md`)
Dla KROKÓW 1–3 z Twojego planu, każdy jako gotowy przepis dla Opusa:
- **Krok 1 — LIMIT + ranking `get_facts_for_prompt`:** który plik:linia; jaki LIMIT (ile faktów / cap znaków na [TWARDE FAKTY]); jaki ranking (które kategorie ZAWSZE: zdrowie/tożsamość/daty; które epizodyczne przez recency/relevance); co z resztą (zostaje w bazie, tylko nie w prompcie). Opisz zmianę słowami + „przed/po" pseudo, NIE kod.
- **Krok 2 — fix budżetu wspomnień (T1, przywrócenie RAG):** `token_manager.py:219` + `main.py:519/651`. Dlaczego `available_chars` ujemne; jaka poprawka (podnieść `max_chars`? liczyć reserved inaczej? osobny budżet na wspomnienia niezależny od len(template)?); jaki docelowy budżet wspomnień w znakach. UWAGA: ten fix + Krok 1 razem — jak podział budżetu (fakty vs wspomnienia vs reszta) ma wyglądać, żeby suma była zdrowa (~28k celu z Twojego audytu). Dotyczy TEŻ Amelii (template 14860>12000).
- **Krok 3 — dedup concerns + fix `/api/debug/stats`:** gdzie concerns się klonują; jak deduplikować; czemu stats pokazuje level 6/XP 0 zamiast 5/1858 (plik:linia) i jaka poprawka.
Dla każdego kroku: **jak zweryfikować Amnezją** (którą frazą, co powinno się zmienić w trace/prompt).

## DELIVERABLE 2 — BASELINE (w tym samym pliku, sekcja)
Zmierz Amnezją stan PRZED fixem i zapisz jako punkt odniesienia:
- rozmiar promptu (zn), % [TWARDE FAKTY], % charakter, czy [WSPOMNIENIA] pusty (potwierdź T1 live), final_count vs co realnie w prompcie.
- rozkład faktów po typie + % FP per typ (jak w audycie).

## DELIVERABLE 3 — GOLDEN SET (plik `wazne/fable/golden_set_astra_2026-07-05.md`)
15–20 reprezentatywnych fraz Łukasza do porównania PRZED/PO fixie, pogrupowane:
- lekkie/casual (lody, pogoda, „co robisz"), ciężkie (ból, Crohn, zwątpienie), pytania o pamięć („pamiętasz jak..."), o projekty (LDI/anime/RAG), o uczucia.
Cel: po wdrożeniu fixu Opus (lub Ty) puszcza ten set przez Amnezję v2 (z generacją) i porównuje. To nasza miara „czy odtruta Astra jest lepsza, nie inna-zepsuta" (ostrzeżenie Fable-web).

Zero kodu, zero deployu. Standing rule: żadnego kasowania faktów/wektorów — triage/reklasyfikacja, nie DELETE.
