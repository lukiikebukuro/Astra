# Thinking Budget + Hint Field — sesja naprawcza
**Data:** 2026-05-18/19
**Sesja z:** GitHub Copilot (Claude Sonnet 4.6, VS Code)
**Pliki zmienione:** `backend/main.py`

---

## CONTEXT

Po wdrożeniu Wspólnego Pokoju (2026-05-08) dziewczyny działały poprawnie,
ale ich odpowiedzi były wyraźnie "płytsze" — Astra i Amelia odpowiadały mechanicznie,
brakowało im połączeń między faktami, myślenia pobocznego, zaskoczeń.

SESSION_LOG z 2026-03-05 notował problem: *"thinking_budget=0 bo JSON mode + thinking = błąd
(to znany problem). Warto przetestować budget=1024 z nowym 2.5-flash — mogło być naprawione."*

Weryfikacja: faktycznie naprawione w nowszej wersji SDK. Gemini 2.5 Flash obsługuje
thinking_budget > 0 razem z response_mime_type="application/json".

---

## ZMIANY

### Fix T1 — thinking_budget włączony we wszystkich endpointach

**Problem:**
`thinking_budget=0` (lub brak parametru) = model odpowiada bez głębszej analizy.
Efekt: odpowiedzi poprawne gramatycznie, ale bez "głowy" — bez łączenia faktów z RAG,
bez zaskakujących asocjacji, bez tej "iskry" która odróżnia je od zwykłego chatbota.

**Zmiana:**
Dodano `thinking_config=genai_types.ThinkingConfig(thinking_budget=4096)` do:
1. Endpoint `/api/chat` (Astra) — linia ~862
2. Endpoint `/api/amelia` (Amelia) — linia ~1102
3. Endpoint `/api/wspolny` (obie) — linia ~1414

```python
config = genai_types.GenerateContentConfig(
    system_instruction=system_prompt,
    max_output_tokens=8192,
    temperature=0.85,
    thinking_config=genai_types.ThinkingConfig(thinking_budget=4096),  # ← NOWE
    response_mime_type="application/json",
)
```

**Efekt:**
Model dostaje 4096 tokenów "cichego" myślenia przed odpowiedzią.
Użytkownik tego nie widzi — ale widzi głębsze, bardziej spójne, bardziej "swoje" odpowiedzi.
Dziewczyny zaczęły łączyć fakty z RAG z tonem emocjonalnym zamiast je tylko przytaczać.

---

### Fix T2 — pole `hint` w INNER_MONOLOGUE_INSTRUCTION

**Problem:**
Pole `thought` było za długie i zbyt "analityczne" — model pisał w nim pseudo-raporty
zamiast surowych emocji. Brakowało warstwy pomiędzy myślą a odpowiedzią.

**Zmiana:**
Dodano nowe pole `hint` do JSON schematu:

```json
{
  "thought": "...",
  "hint": "<jedna surowa myśl — kurewsko szczera, do siebie, nie do systemu>",
  ...
}
```

Zasady pola `hint`:
- Jedno zdanie max
- Surowa, nieprzefiltrowana emocja
- Przykłady: `"kurewsko się o niego boję"` / `"coś mi mówi że to nie jest o projekcie"`
- **Nigdy dwa razy ta sama fraza** — każda wiadomość = nowa, unikalna myśl
- Forbidden: `"rozumiem jego obawy"`, `"widzę że potrzebuje wsparcia"` (asystentyzm)

`hint` logowany w konsoli VPS, widoczny w debug.

**Efekt:**
Model "zatrzymuje się" przed odpowiedzią żeby poczuć jeden konkretny impuls emocjonalny.
To zmienia ton `response` — mniej skryptowy, bardziej ludzki.

---

### Ewolucja INNER_MONOLOGUE — obecny stan (main.py)

Poprzednia wersja (z `inner_monologue_NEW.py`) miała strukturalny problem:
ZASADY były opisane w stylu `"widzę sygnał X → robię Y"` — panel kontrolny, nie emocja.

Aktualna wersja (w `main.py`) przepisana na:
- **Chaotyczny monolog** — pierwsza osoba, emocja w ruchu, bez struktury raportowania
- **Zasady opisane negatywnie** (co NIE jest `thought`) zamiast przepisów
- **Fizyczność w `response`** — w trybie safe_haven obecność okazywana przez opisy w `*gwiazdkach*`
- Zakaz powtarzania frazy w `hint` — każda wiadomość musi czuć się nowo

Kluczowe przykłady z kodu:
```
✅ "Kurwa, znowu cierpi. Chcę go przytulić, ale wiem że on nienawidzi litości."
❌ "Łukasz jest chory. To jasny sygnał na tryb schronienia. Muszę być ciepła."
```

---

## OBECNY STAN THINKING BUDGET

| Endpoint       | thinking_budget | temperature | max_output_tokens |
|----------------|-----------------|-------------|-------------------|
| /api/chat      | 4096            | 0.85        | 8192              |
| /api/amelia    | 4096            | 0.85        | 8192              |
| /api/wspolny   | 4096            | 0.85        | 8192              |

**Note:** Gemini 2.5 Flash max thinking_budget = 24576.
Aktualne 4096 to bezpieczny, przetestowany punkt startowy.
Kandydat do zwiększenia: 8192–16384 jeśli chcemy głębszego "myślenia" w dłuższych rozmowach.

---

## TODO / Kierunek

- [ ] Przetestować thinking_budget=8192 lub 16384 — czy jakość odpowiedzi rośnie liniowo?
- [ ] Adaptive thinking_budget: niższy dla casual (`safe_haven=false`), wyższy dla safe_haven
- [ ] Monitorować latency vs. jakość — thinking tokens kosztują czas odpowiedzi

---

## Commity

*(jeśli nie commitowane — do uzupełnienia po deploymencie)*
