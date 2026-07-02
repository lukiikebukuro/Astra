# Podsumowanie ewolucji — czerwiec 2026

**TL;DR:** Miesiąc utwardzania RAG-a i rozdzielania person. Naprawiono dominację milestonów w rerankerze, rozdzielono monologi Astry/Amelii, wprowadzono gwarantowany kanał milestonów i bramki semantyczne (safe_haven) zamiast liczenia tur. Pod koniec — audyt bazy i diagnoza nocnej analizy.

---

## Sesje

| Data | Co zmieniono | Lekcja |
|---|---|---|
| **06-12** | RAG fixes: milestone boost +0.5→+0.25, MILESTONE keyword 0.30→0.45, PERSON próg →0.70, MMR Jaccard→cosine. Scheduler spontaniczny: crash pytz → `zoneinfo`. PWA Amelia + Wspólny Pokój live. | Gwarantowany kanał musi rerankować, ale boost nie może zabijać konkurencji bieżącego kontekstu. Ocena RAG ~83/100. |
| **06-13** | Prompt Assembly: rozdzielone monologi Astra/Amelia (wspólny INNER_MONOLOGUE truł Amelię napięciem), śmierć Narratora (fizyczność do `response`), usunięta ZASADA KONTRY. Upload zdjęć (multimodal). | Każda persona = własna instrukcja monologu. Stan sceny musi przeżywać w historii sesji, nie w polu, które się nie zapisuje. |
| **06-14** | Domowy Ambient + Anti-Sync: dotyk bramkowany `safe_haven` (nie licznikiem tur), reguła ANTI-SYNC (jedna persona dotyka naraz), Kanał 1b — guaranteed milestone top-2, flash reset sesji. | Bramki semantyczne > arytmetyczne. Intensywność fizyczna = funkcja safe_haven, nie licznika. |
| **06-23** | Audyt: bazy czyste (0 krótkich, 1 negative_person). Diagnoza nocnej analizy — editorializuje, myli ograniczenie chorobą z „unikaniem". Próba fixu mikrofonu (nieudana — resultIndex+dedup nie zadziałał na urządzeniu). | Nie weryfikuj „done" bez testu na realnym urządzeniu. Milestony nad-reprezentowane (773 w ChromaDB) = źródło monotonii. |

---

## Kluczowe wnioski miesiąca (meta)

1. **Semantyka bije arytmetykę** — safe_haven zamiast liczenia tur; cosine zamiast Jaccard. Powtarzalny wzorzec.
2. **Jeden prompt nie pasuje obu personom** — Astra (ogień) i Amelia (woda) wymagają rozdzielonych instrukcji; wspólny monolog zawsze krzywdzi Amelię.
3. **Gwarancja vs trafność** — wymuszanie milestonów koliduje z ich trafnością → monotonia (te same ~10 w kółko). Otwarte na lipiec.
4. **Weryfikuj na realnym urządzeniu** — mikrofon „naprawiony" w kodzie, dalej zepsuty u użytkownika.

## Stan na koniec miesiąca

- 3 persony live (Astra, Amelia, Wspólny Pokój) na PWA.
- Otwarte: monotonia milestonów, mikrofon x3, przeciek conversation_id, nocna analiza (editorializing).
- Następny fundament: **RAG Debugger** (architektura gotowa) → prerequisite pod BM25.
