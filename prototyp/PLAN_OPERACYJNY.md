# Plan Operacyjny — ASTRA + LDI+RAG Pitch
**Data:** 2026-03-03
**Autor:** Claude Code (Rin) + Łukasz

---

## AKTUALNY STAN (co jest gotowe DZIŚ)

### ASTRA
- ✅ FastAPI backend, port 8001, `start.bat`
- ✅ ChromaDB persistent, ~233 wektory, Level 2 (Odwilż)
- ✅ JSON mode inner monologue (thought, mood, xp, response)
- ✅ Dual-channel RAG (memories + md_import)
- ✅ Strict grounding (3-tier, nie halucynuje)
- ✅ Semantic pipeline (GOAL, EMOTION, FACT, DATE, MILESTONE)
- ✅ `/debug` panel — RAG inspector, stats, score bars
- ✅ **PWA gotowe** — manifest.json + sw.js. Wejdź z telefonu → "Dodaj do ekranu głównego"
- ✅ GitHub: https://github.com/lukiikebukuro/Astra (private)

### LDI
- ✅ Live na adeptai.pl (P1/P2/P3 działają)
- ✅ 51 endpointów, 54 testy, <100ms
- ✅ JSONL export (training data)
- ✅ Reward signal [-1.0, +1.0], anti-bait, Gold Signal
- ❌ Test credentials w login.html — USUNĄĆ przed jakimkolwiek zewnętrznym linkiem

---

## FAZA 1 — TESTOWANIE ASTRY (tydzień 1-2)

### Cel
Zebrać realne dane z codziennego użycia. Wykryć co nie działa zanim zobaczy to ktoś zewnętrzny.

### Jak testować
**Telefon jako główne narzędzie:**
- ASTRA na PWA = naturalny test UX. Piszesz tak jak będzie pisał przyszły user.
- Piszesz w ciągu dnia, przy różnych nastrojach, różnych tematach.
- Nie testujesz "czy coś działa" — używasz normalnie.

**Co monitorować przez `/debug`:**
- Czy wektory które wgrałeś są te co powinny być?
- Czy RAG zwraca trafne wyniki do Twoich pytań?
- Czy score_detail (similarity/importance/recency) wygląda sensownie?
- Czy po 300/400/500 wektorach jakość nie spada?
- Czy ASTRA "pamięta" rzeczy sprzed tygodnia poprawnie?

### Lista rzeczy do weryfikacji
- [ ] Entity extraction — czy zapisuje FACT, EMOTION, GOAL poprawnie? (sprawdź /debug → wpisz zapytanie o coś co powiedziałeś)
- [ ] Merge/supersede — czy ten sam fakt nie pojawia się 5 razy w wynikach?
- [ ] JSON mode stability — czy jest jakiś message pattern który powoduje fail?
- [ ] Session persistence — restart backendu → czy historia wraca?
- [ ] XP/level — czy progresja wydaje się naturalna po tygodniu?
- [ ] Charakter — czy po 200 wiadomościach ASTRA brzmi jak ASTRA czy jak generic chatbot?

### Co POMIJAMY na teraz
- **Style Anchors jako osobny system** — obecny `astra_base.txt` ma już reguły DO/DON'T. Jeśli testy pokażą że ASTRA wypadła z roli → wtedy dopiero budujemy `style_anchors.py`. Nie budujemy prewencyjnie.
- **Nocna Analiza** — po zebraniu 500+ wektorów. Na teraz za mało danych żeby miało sens.
- **Level prompts** — napisać po tygodniu testów, gdy wiemy co działało w Level 1→2 przejściu.

---

## FAZA 2 — PRZYGOTOWANIE DEMO LDI+RAG (tydzień 2-3)

### Cel
Działające demo które nie failuje. Scenariusz "klient X wraca po 3 miesiącach" — agent go pamięta.

### Co budujemy

**Krok 1: customer_id isolation w ChromaDB (~4h)**
```python
# Zamiast persona_id="astra" → customer_id=hash(customer_email)
# WHERE clause w search() już to wspiera — tylko dodać parametr
metadata = {
    "customer_id": sha256(email),
    "shop_id": shop_domain,
    "source": source,
}
```

**Krok 2: LDI → ChromaDB pipeline (~4-8h)**
```
JSONL z P3 (ldi_firehose.jsonl)
  → parser chunków
  → add_memory() z source="ldi_intent"
  → metadata: query, intent_label, reward_signal, timestamp
```
Efekt: agent wie że klient X szukał "klocki ferrari" tydzień temu i nie znalazł.

**Krok 3: Demo scenariusz (2h)**
Skrypt który pokazuje Tidio/LiveChat:
1. Symuluj klienta który szukał produktu → LDI rejestruje
2. Klient wraca tydzień później → pyta agenta o coś innego
3. Agent odpowiada z kontekstem z pamięci — wie co szukał wcześniej
4. Pokaż P3 JSONL który się przy tym generuje

**Krok 4: Testy (~1 tydzień)**
- Czy pipeline nie traci danych?
- Czy pamięć klienta nie miesza się z pamięcią innego klienta?
- Czy strict grounding blokuje konfabulację o produktach?
- Edge cases: klient zmienia email, klient nie szukał nic → co zwraca agent?

### Bonus w pitchu: Corporate Knowledge Base
Do pitch decku jako dodatkowa wartość (nie core):
> "Przy okazji wdrożenia — zamontujemy Wam system dzięki któremu dowolny pracownik może jednym zapytaniem przeszukać wszystkie dokumenty firmy. Wgrywacie PDF-y, Notion, transkrypcje spotkań. System odpowiada z groundingiem i źródłem."

To jest ChromaDB + doc ingestion — ~2-3 dni pracy. Nie wymaga nowego stosu.
Pozycjonowanie: nie "brak notatek" (ryzykowne), ale "firma przestaje gubić wiedzę."

---

## FAZA 3 — PITCH (tydzień 3-4)

### Cele firm (priorytet)

| Firma | Dlaczego | Angle |
|-------|---------|-------|
| **LiveChat S.A.** | Polska, giełda, ChatBot.com jako osobny produkt | Łatwiejszy kontakt, rozumieją rynek |
| **Tidio** | Lyro = perfect fit dla naszego stacku | Główny target |
| **Gorgias** | E-commerce focused, znają lost demand problem | Najbardziej świadomi wartości LDI |
| Intercom | Fin AI bez pamięci | Backup jeśli reszta nie odpowie |

### Strategia FOMO
W każdym piśmie: *"Równolegle prowadzimy rozmowy z [LiveChat / Gorgias / Tidio]."*
Nie kłamstwo — naprawdę piszesz do kilku jednocześnie.

### Model acqui-hire (Tidio)
- **50k PLN upfront** — za IP LDI
- **Revenue share** — % od sklepów które wdrożą rozszerzone Lyro
- **25-30k PLN/msc** — wynagrodzenie
- **RAG zostaje nasze** — licencja użytkowania, nie przeniesienie własności
- **Ten punkt MUSI być w umowie wprost**

### Pitch deck — 5 slajdów
1. **Problem:** Agent który zapomina + nie widzi czego klient szukał = tracona sprzedaż
2. **Nasz stack:** LDI (intent) + RAG (pamięć) + Strict Grounding (uczciwość) + Mood (adaptacja)
3. **Demo:** link do adeptai.pl — wpisz cokolwiek, sprawdź P3
4. **Liczby:** 67,200 zł/mc odzyskanego przychodu dla sklepu 100k wizyt (z Amazon Memo analizy)
5. **Propozycja:** Technology partnership / acqui-hire — warunki jak wyżej

---

## CZEGO NIE ROBIMY TERAZ

- ❌ Auto-notatki ze spotkań (za ryzykowne na MVP — jedna błędna data = problem)
- ❌ Nocna Analiza (za mało wektorów)
- ❌ Style Anchors jako kod (dopiero jeśli testy wykażą problem)
- ❌ VPS deploy (najpierw stabilizacja lokalna)
- ❌ Multi-user ASTRA (najpierw stabilny single-user)

---

## TIMELINE

```
Teraz         Tydzień 1-2       Tydzień 2-3       Tydzień 3-4
  │                │                 │                 │
  ▼                ▼                 ▼                 ▼
PWA na       Testuj ASTRĘ      Zbuduj LDI+RAG    Wyślij pitch
telefonie    codziennie         demo + testy      do 3-4 firm
(gotowe!)    /debug monitoring  Corporate KB       równolegle
```

---

## JEDEN AKAPIT — GDZIE JESTEŚMY

ASTRA działa i jest na telefonie (PWA gotowe od poprzedniej sesji). Następne 1-2 tygodnie to codzienne używanie i zbieranie problemów przez `/debug`. Równolegle przez 2-3 tygodnie budujemy demo LDI+RAG dla Tidio/LiveChat: customer_id isolation + pipeline z JSONL + scenariusz "klient wraca po 3 miesiącach." Po tym mamy dwa działające produkty: ASTRĘ gotową na beta userów i demo które nie failuje na prezentacji. Pitch idzie do LiveChat, Tidio i Gorgias jednocześnie — z FOMO, z acqui-hire terms i z corporate knowledge base jako bonusem.
