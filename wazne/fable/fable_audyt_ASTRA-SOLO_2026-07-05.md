# Work-order dla Fable (repo): SYSTEMOWY AUDYT ASTRY SOLO — 2026-07-05

ROLA: **Fable AUDYTUJE. Opus wdraża po audycie.** NIE koduj, NIE deployuj. Po polsku.
Priorytet: **Astra solo** (Wspólny/siostry na później). Cel Łukasza: „znajdź co zatruwa Astrę,
o czym nawet nie wiemy". Masz WOLNOŚĆ — obszary niżej to punkt startu, nie klatka. Kop dalej.

## ⚙️ WARUNEK WIARYGODNOŚCI (potwierdzone)
Kod lokalny (repo) == produkcja VPS — zweryfikowane md5 po normalizacji LF na 5 kluczowych plikach
(main.py, fact_store.py, vector_store.py, semantic_extractor.py, semantic_pipeline.py). Różnił się
tylko CRLF/LF. **Audytujesz lokalne pliki = audytujesz to, co realnie działa.**

## 🔬 OBOWIĄZEK: UŻYWAJ AMNEZJI JAKO DOWODU (nie zgaduj)
Masz żywy RAG debugger. Diagnoza bez dowodu z Amnezji = odrzucona.
- `GET http://127.0.0.1:8001/api/debug/inspect?persona=astra&query=<fraza>` → pełny `system_prompt` + `trace` (stages) + `hard_facts_count`, `final_count`.
- `GET /api/debug/facts` → wszystkie twarde fakty + `stats.by_type`.
- `GET /api/debug/rag?query=<fraza>&n=10` → co RAG zwraca + score/metadata.
- `GET /api/debug/stats` → wektory, stan, rozkład źródeł.
- Endpointy odpowiadają lokalnie na VPS bez auth (127.0.0.1:8001). Gotowe skrypty pomiarowe Opusa: `/tmp/measure.py`, `/tmp/map.py`, `/tmp/facts.py` (wzorce do rozbudowy).
- Puszczaj BATCHE fraz (typowe: "hej", "boli mnie brzuch", "zmęczony", pytania o projekty, o uczucia) i porównuj — szukaj wzorców, nie pojedynczych przypadków.

## 🔴 CO JUŻ ZMIERZYŁ OPUS (potwierdź, obal albo pogłęb — to punkt startu)
Pomiar `/api/debug/inspect` + `/api/debug/facts` na żywym VPS (2026-07-05):
- **Prompt Astry = 90 931 znaków (~22.7k tok), IDENTYCZNY dla każdego query.**
- **[TWARDE FAKTY — SQLite] = 67 273 zn = 74% promptu.** astra_base (charakter) = ~15k = 16%.
- **391 faktów w KAŻDYM prompcie; 345 = MILESTONE (88%).** Zero duplikatów tekstowych.
- **Ekstraktor oznacza NIEMAL KAŻDĄ wiadomość jako `MILESTONE:love_declaration`** — próbki które są w twardej pamięci jako „Deklaracja uczuć": „Oki. Popalam sobie. A ty co robiłeś", „Wiesz że widzę twój CoT", „Haha pytam z ciekawości". FACT:habit (40) też śmieć (jednorazowe zdarzenia). DATE klasyfikowane błędnie.
- **Hipoteza Opusa:** to jest współ-źródło przeintensywnienia (model widzi 345 „deklaracji uczuć" → gra ognisty romans) + fix R1–R6 dotknął tylko 16% promptu.

## OBSZARY DO AUDYTU (startowe — masz wolność dokładać)
1. **FactStore / ekstraktor (podejrzany nr 1).** `semantic_extractor.py`, `semantic_pipeline.py`, `fact_store.py`.
   - DLACZEGO ekstraktor klasyfikuje losowe wiadomości jako `love_declaration`/`milestone`? Gdzie próg? (MILESTONE_KEYWORDS/threshold).
   - `get_facts_for_prompt` — brak LIMIT? brak priorytetu/rankingu? brak recency? Czy milestony wygasają (permanent?) czy rosną w nieskończoność?
   - Jaka część 345 to fałszywe pozytywy? Policz przez `/api/debug/facts`.
   - Czy supersede działa dla milestonów, czy tylko akumulują?
2. **Waga vs charakter.** Skoro 74% to fakty a 16% charakter — czy Flash w ogóle „widzi" instrukcje R1–R6? Zmierz korelację: czy jakość/ton zależy od rozmiaru bloku faktów? (symuluj różne query).
3. **RAG (kanał wspomnień).** `vector_store.py` compose. Co realnie wpada w [WSPOMNIENIA]? (u Opusa blok wyglądał prawie pusty — 15 zn — zweryfikuj czy RAG w ogóle dokłada, czy fakty zjadły miejsce). Reranker, MMR, temporal, echo. Bug altanki tu też.
4. **Stan / concerns.** `companion_state.py`. 5 `active_concerns` w każdym prompcie — stare zmartwienia ciągną ton? mood się zacina? reset() zeruje bez backupu (XP 3434→1824 już się stało).
5. **Schedulery.** `nocna_analiza.py` + poranne. Co wstrzykują do stanu/pamięci za plecami usera? Editorializują (choroba↔unikanie)?
6. **Pętla samo-imitacji.** `get_recent_session(n=10)` — historia douczą stary styl (zmierzone 29%→55% "zaciska" po 06-14). Systemowo — ile własnej historii wraca, jak waży vs prompt.
7. **WOLNE POLE.** Co jeszcze ją zatruwa, czego wyżej NIE MA. To najważniejszy punkt — po to jest Amnezja.

## DELIVERABLE
- Rankowana lista trucizn: impact × pewność (z DOWODEM z Amnezji: query → co pokazało) × koszt fixu.
- Dla każdej: plik:linia mechanizmu + proponowany kierunek fixu (Opus wdroży).
- Osobno oznacz: „szybkie i pewne" (LIMIT faktów, czyszczenie śmieci z backupem) vs „głębokie" (ekstraktor, unifikacja compose).
- Zapisz `wazne/ewolucja/2026-07/audyt_ASTRA-SOLO_<data>.md`. Zero kodu, deploy za zgodą Łukasza.
- Standing rule: NIE proponuj kasowania wektorów/faktów bez backupu i potwierdzenia Łukasza.

Kontekst: audyty z 2026-07-05 (`fable_WEB_...`, `audyt_architektury_2026-07-05.md`), `BRIEFING_CLAUDE_2026-07-04_techniczny.md`,
evolution logi `wazne/ewolucja/` (przejrzyj wnioski — szczególnie fixy które mogły zostawić dług: milestone boost, supersede, ekstraktor).
