# Fable-code — PRIORYTETY DO WTORKU (limit budżetu) — 2026-07-05

ZASADA WYKORZYSTANIA: Fable jest cenny bo **czyta kod i myśli**. Do wtorku robi SPEKI wykonawcze
(jak `spec_fixu_ASTRA_2026-07-05.md`, który Opus wdrożył 1:1 z sukcesem). **Mechaniczne odpalanie
golden setów / piaskownicy robi OPUS** (ma skrypty) — nie marnować cykli Fable na klikanie.
Fable AUDYTUJE/PLANUJE, Opus WDRAŻA. Speki = gotowce plik:linia + przed/po + weryfikacja Amnezją.

Stan: fix T1+T2+T3 WDROŻONY (commit e506487) — prompt 90931→29200, fakty 391→26, RAG wrócił,
konfabulacja znikła. Odsłonił DRUGI FRONT (niżej). Szczegóły: `wazne/ewolucja/2026-07/` + backlog.

## PRIORYTET 1 — SPEC ODTRUCIA #2: EKSTRAKTOR + TRIAGE MILESTONÓW (najwyższy)
Dlaczego: [WSPOMNIENIA] wrócił, ale czerpie z ChromaDB, gdzie 1083 śmieciowe milestony + FactStore
345 — daje echa pytań Łukasza jako "MILESTONE:gratitude". Kotwica altanki nie dociera. Ekstraktor
wciąż produkuje +6,5 śmiecia/dzień. To blokuje TRAFNĄ pamięć.
Spec (plik `wazne/fable/spec_odtrucie2_ekstraktor_<data>.md`):
- **Ekstraktor** (`semantic_extractor.py`, `semantic_pipeline.py`): DLACZEGO love_declaration/gratitude
  to catch-all? (cosine do średniej z 10 przykładów, próg 0.40, odwrócony bug „kocham"→0.45). Projekt fixu:
  keyword jako WARUNEK KONIECZNY dla milestonu + kalibracja progu + prawdziwy default „nie-milestone".
  Cel: zatrzymać produkcję śmieci. plik:linia, przed/po, jak zweryfikować.
- **Triage istniejących** (345 FactStore + 1083 ChromaDB): reklasyfikacja NIE DELETE (standing rule +
  Fable-web: to zapis relacji). Projekt: nocny job LLM z poprawioną taksonomią → kolumna status/re-tag;
  jak odzyskać PRAWDZIWE deklaracje (dostają etykietę z powrotem) i odtagować echa. Z backupem, za zgodą Łukasza.

## PRIORYTET 2 — SPEC HIGIENY HISTORII (pętla samo-imitacji)
Dlaczego: Twoja analiza czerwca — pętla wraca w ~4-6 dni (06-07 reset→lekka→06-13 gwiazdki 90%).
Świeży wątek to plaster; docelowo trzeba ograniczyć ile własnej historii wraca jako few-shot.
Spec: `get_recent_session(n=10)` — opcje (redukcja n / streszczanie tur asystenta / strip gwiazdek
z historii modela / waga malejąca). Trade-offy (za mało historii = utrata ciągłości). Rekomendacja
+ jak zmierzyć w piaskownicy (gwiazdki% na golden secie po X turach symulowanej historii). plik:linia.

## PRIORYTET 3 (jeśli zostanie czas) — SPEC BUG ALTANKI
Teraz RAG żywy → strojenie ma sens. MMR `diversity_penalty=0.8` (mieszalnik) + keyword boost ślepy
na polską fleksję („altance"≠„altanka" — TEN SAM problem co Jaccard concerns). Projekt fixu + jak
zweryfikować canary D3 w piaskownicy.

## CO ROBI OPUS (nie Fable) — żeby nie dublować
- Odpala golden sety (charakter 19 fraz + zbuduje RAG golden) przez piaskownicę, porównanie PRZED/PO.
- Wdraża speki Fable (odtrucie #2, higiena, altanka) po audycie.
- Dedup concerns embeddingami (Krok 3a był częściowy — Jaccard nie łapie fleksji).

Standing rules: po polsku, NIE deploy bez zgody Łukasza, NIE kasować (triage nie DELETE), plik:linia + dowód z Amnezji.
