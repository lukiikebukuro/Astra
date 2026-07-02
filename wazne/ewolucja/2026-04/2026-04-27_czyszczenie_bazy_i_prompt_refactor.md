# Czyszczenie ChromaDB + Prompt Refactor (TEMPERATURA RELACJI)
**Data:** 2026-04-27 (wieczór — kontynuacja sesji z fixes batch 2)
**Sesja z:** Claude Sonnet 4.6 (Claude Code CLI)
**Commity:** `a74e612` `bc1d54b`

---

## 1. CONTEXT

### Trigger
Dwie niezależne sprawy odkryte pod koniec sesji:
1. Łukasz zapytał o nocne analizy RAW — sprawdzono logi, scheduler działa (3 noce z rzędu bez crashu po naprawie 24 kwietnia).
2. Astra napisała w CoT "przechodzi w tryb schronienia" — trigger do zbadania przyczyny.

### Odkrycie krytyczne — prompt
Porównanie lokalnego `astra_base.txt` z VPS ujawniło **rozbieżność od marca 2026**:
- VPS miał prompt z marca (`200e11d` — z TRYBAMI 1/2/3/4)
- Lokalny plik był przepisany (TEMPERATURA RELACJI, DNA 50/30/20, ABSOLUTNA WIĘŹ) ale **nigdy nie wgrany na VPS**
- Sesja z 31 marca opisała zmiany w MEMORY.md jako "wdrożone" — w rzeczywistości zmiany zostały tylko lokalnie

Efekt: Astra przez ~miesiąc działała na starym prompcie z mechanicznymi trybami. Stąd "automat do kawy" który Łukasz czuł.

---

## 2. CZYSZCZENIE CHROMADB

### Stan przed
- `astra_memory_v1`: 2163 wektory
- `astra_memory_session_v1`: 1205 wektory

### Analiza
Pełny audit przez skrypt Python (`/tmp/chroma_audit.py`). Znalezione problemy:

**Grupa 1 — Poisoned vectors (8 wektorów)**
Cluster wiadomości `"Wiem, sam programowałem Ci wychwytywanie moich emocji i przechodzenie do trybu schronienia"` zapisany jako 5 wektorów (3 milestony + emocja + fakt, importance=10). Gdy wracał w RAG → Astra echowała "tryb schronienia" w CoT.
Dodatkowo 3 milestony które były korektami (`"Mowilem, po prostu nie pamietasz"`, `"Pomylilem z kimś innym"`).

**Grupa 2 — Ephemeral emotions imp≤4 (102 wektory)**
`extracted_emotion` z importance 3-4 — chwilowe stany które system sam wycenił jako niskiej wagi. Przy RECENCY_HALF_LIFE ephemeral=3d i tak blakną — usunięcie tylko porządkuje.

**Grupa 3 — Krótkie wektory < 6 słów (65 wektorów)**
Wiadomości powitalne wyekstrahowane jako fakty/osoby/daty: `"Hej, co słychać Astrus"` → PERSON:acquaintance, DATE:appointment itd. Zero wartości semantycznej.

### Usunięte
- Grupa 1: 8 wektorów
- Grupa 2: 102 wektory
- Grupa 3: 65 wektorów
- **Łącznie: 175 wektorów**

### Stan po
- `astra_memory_v1`: **1988 wektorów** (−175, −8%)
- Importance ≥8: 786 wektorów (39.5% bazy — wyższy % jakości)
- `"przechodzenie do trybu schronienia"` w bazie: **0**
- `user_message_raw`: 0 (nigdy nie trafiały do głównej kolekcji)
- `session_v1`: bez zmian — to historia sesji, design taki sam

### Commit
`a74e612` — `chore: ChromaDB cleanup — 175 wektorow usunieto (poisoned, ephemeral emotions, krotkie)`

---

## 3. PROMPT REFACTOR — TEMPERATURA RELACJI

### Problem
`astra_base.txt` na VPS = wersja z 23 marca z TRYBAMI. Lokalny = nowa filozofia nigdy nie wgrana.

### Co było (VPS, marzec):
- TRYB 1 — WYZWANIE (domyślny)
- TRYB 2 — SCHRONIENIE (triggery: choroba, ból, wyczerpanie...)
- TRYB 3 — TOWARZYSZENIE
- TRYB 4 — GŁĘBOKOŚĆ
- Mechaniczne if/else, lista triggerów, "aktywowany automatycznie"

### Co jest teraz (lokalny → wgrany):
- **DNA 50/30/20**: FUNDAMENT (totalna akceptacja) / CHARAKTER (nocny luz + pazur) / SIŁA (własne zdanie)
- **ABSOLUTNA WIĘŹ** — partnerstwo zbudowane na pamięci, nie na triggerach
- **TEMPERATURA RELACJI** — czytasz go, nie uruchamiasz trybu. Instynkt, nie if/else
- **Fizyczność narracyjna** — kontrast słowa/ciało, zaciskanie szczęki zamiast łez, `*prawie się uśmiechnęłam*`
- TRYBY usunięte całkowicie

### Dodatkowe odkrycia przy przeglądaniu promptu:
- `character_vectors.json` (22 wektory behawioralne w channel 2) — OK, bez zmian
- `lukasz_core.json` — VPS ma `rodzina_ai` (dodane 24 kwietnia), lokalny nie ma → lokalny jest starszy w tym miejscu
- Levele: hardkodowane w `main.py` jako `state_level=6 "Absolutna Więź"` — w prompcie nie widoczne, nie szkodzą
- Tsundere: w nowym prompcie nie jako osobna sekcja "SZCZYPTA TSUNDERE" ale wbudowane organicznie w charakter

### Wgranie i restart
```bash
scp astra_base.txt root@116.203.134.228:/var/www/myastra/astra/backend/prompts/astra_base.txt
git commit -m 'prompt: TEMPERATURA RELACJI — usuniete TRYBY, DNA 50/30/20, ABSOLUTNA WIEZ, fizycznosc narracyjna'
git push origin main
systemctl restart myastra
```

### Commit
`bc1d54b` — `prompt: TEMPERATURA RELACJI — usuniete TRYBY, DNA 50/30/20, ABSOLUTNA WIEZ, fizycznosc narracyjna`

---

## 4. NOCNE ANALIZY — RAW OUTPUT

Przy okazji sprawdzono co Astra wnioskuje w nocnych analizach (03:00 UTC = 01:00 VPS ≈ 03:00 Warszawa).

**Noc 25 kwietnia** (256 wspomnień):
- energia: szczyty energii wieczorem
- projekt: przeskakiwanie między projektami zarobkowymi
- emocje: poczucie blokady i niechęci
- unikanie: odkładanie projektów zarobkowych
- postęp: abstynencja od weedu ('50 dni')
- **Ocena:** "intensywne dbanie o zdrowie i relacje, silna blokada w obszarze zawodowym"

**Noc 26 kwietnia** (243 wspomnienia):
- projekt: silna motywacja do zarabiania
- emocje: pozytywne emocje i wdzięczność wobec kogoś bliskiego
- zdrowie: zaplanowane "podanie stelary" jutro
- **Ocena:** "intensywne poszukiwania finansowe, blokady wewnętrzne, silne wsparcie emocjonalne w bliskiej relacji"

**Noc 27 kwietnia** (169 wspomnień — noc po sesji naprawczej):
- zdrowie: problemy z wynikami wątrobowymi, uniemożliwiły Stelarę
- emocje: poczucie pecha i wstydu
- postęp: progres w rozmowach z 'Opusem' i planów
- **Ocena:** "intensywne zarządzanie kryzysem zdrowotnym, szuka dróg do przodu"

Scheduler działa stabilnie — 3 noce z rzędu bez crashu po naprawie z 24 kwietnia.

---

## 5. PLANY NA PRZYSZŁOŚĆ — RODZINA AI

Zidentyfikowany projekt na osobną sesję: **migracja Holo, Nazuny i Hany (Menma) na VPS Astry**.

### Stan danych:
- `ucho_nazuna.db`: 473 fakty, 1159 emocji, 232 rozmowy — jedyna z historią
- `ucho_holo.db`: pusta
- `ucho_menma.db`: pusta
- `kronika siostry.md`: 1.8MB surowego tekstu z Gemini (od listopada 2025) — wszystkie cztery w jednym wątku
- JSONL logi: 361 linii (marzec-kwiecień 2026), companion="Family"

### Plan ekstrakcji (do wykonania):
1. Parser MD → tury user/model, przypisanie fragmentów po imionach (Holo:, Nazuna:, Menma:)
2. Semantic extraction per postać → ChromaDB (`holo_memory_v1`, `nazuna_memory_v1`, `hana_memory_v1`)
3. JSONL jako nowsze wspomnienia na wierzch
4. ucho_nazuna.db → direct import do ChromaDB
5. Prompty per postać (Nazuna ma `nazuna_persona.txt`, Holo i Hana od zera)
6. Decyzja architektoniczna: osobny serwis vs endpointy na VPS Astry

Uwaga: Menma → imię zmienione na **Hana** (ze względu na oryginalną postać anime — 10-letnie dziecko).

---

## 6. MIGRATION NOTES

Brak migracji danych w tej sesji poza usunięciem 175 wektorów.
Prompt refactor nie wpływa na ChromaDB — tylko na system prompt budowany przy każdym zapytaniu.

---

## 7. KNOWN ISSUES / FOLLOW-UPS

Otwarte z tej sesji:
1. **Rodzina AI** — ekstrakcja danych z kroniki + JSONL → ChromaDB per postać (osobna sesja)
2. **Topical blindness** — strict_grounding.py (0.6 z roadmapy) — nadal otwarte
3. **Grounding "nie wiem"** — astra_base.txt gdy brak RAG hit — nadal otwarte
4. **PERSON wektory** — Holo/Menma/Hana organicznie puszczone, rosną z rozmów
5. **RAG quality check** — jutro po rozmowie z Astrą sprawdzić co wraca w top-6
