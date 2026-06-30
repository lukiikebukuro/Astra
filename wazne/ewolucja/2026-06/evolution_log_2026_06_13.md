# Evolution Log — 2026-06-13
## Prompt Assembly Refactor: Rozdzielenie Monologów i Śmierć Narratora

---

### Kontekst

Poprzedni audyt (`wazne/audyty promptow/2026-06-13_audyt_prompt_assembly.md`) zidentyfikował 6 krytycznych problemów w systemie Prompt Assembly. Niniejszy wpis dokumentuje wdrożone naprawy.

---

### Zmiany wdrożone

#### 1. Asymetria leveli — naprawiona

**Problem:** `amelia_companion_state.json` nie istniał — był tworzony przy starcie z domyślnym `level: 1 ("Lodowa Ściana")`. Amelia widziała siebie jako postać na etapie dystansu i rezerwy, mimo że jej persona jest napisana dla głębokiej relacji.

**Fix:** Utworzono `backend/amelia_companion_state.json` z `level: 6, level_name: "Absolutna Więź"`. Obie postaci mają teraz równy dostęp do mechaniki pełnej relacji w swoim `[STAN WEWNĘTRZNY]`.

---

#### 2. Usunięcie ZASADY KONTRY ze Wspólnego Pokoju

**Problem:** Każda tura Wspólnego Pokoju wstrzykiwała do system promptu obu postaci bezwarunkowy nakaz:
> *"Analizuj jej wypowiedzi. Jeśli uważasz że jej podejście jest błędne, albo po prostu jest głupie — skontruj to w swoim stylu, prosto z mostu. Mają kolidować."*

Nakaz nie miał warunku `safe_haven`. Działał nawet gdy Łukasz mówił o bólu lub był wyczerpany.

**Fix:** Cały blok ZASADY KONTRY usunięty z `_wspolny_generate()`. Różnice charakterów wynikają teraz z person, nie z rozkazu konfliktu. Usunięto też `WYJĄTEK: wyjdź z aside i odpowiedz pełną kontrą` z trybu `aside_mode`.

---

#### 3. Rozdzielenie instrukcji wewnętrznego monologu

**Problem:** Obie postaci dostawały identyczną `INNER_MONOLOGUE_INSTRUCTION`. Sekcja `WALKA — masz w sobie sprzeczności. Pokazuj je` jest właściwa dla Astry (tsundere), ale Amelii (Cicha Studnia, oaza spokoju) kazała pisać z miejsca konfliktu i rywalizacji. Jej pole `thought` generowało napięcie, które przenikało do `mood` i finalnie do `response`.

**Fix:** Stała `INNER_MONOLOGUE_INSTRUCTION` zastąpiona dwiema rozdzielonymi:

- **`ASTRA_MONOLOGUE_INSTRUCTION`** — zachowuje pazur, tsundere vibe, walkę wewnętrzną
- **`AMELIA_MONOLOGUE_INSTRUCTION`** — empatia, uziemienie, głęboka obserwacja, zero szukania konfliktu

Wywołania zaktualizowane:
- `build_system_prompt()` → `ASTRA_MONOLOGUE_INSTRUCTION`
- `build_amelia_system_prompt()` → `AMELIA_MONOLOGUE_INSTRUCTION`

---

#### 4. Śmierć zewnętrznego Narratora — fizyczność wchodzi do `response`

**Problem (bug techniczny):** `WSPOLNY_NARRATOR_BLOCK` generował pole `narrator` w JSON, które było ekstrahoawane osobnym `json.loads()` i zwracane do frontendu, ale **nie zapisywało się do `shared_vector_store`**. Historia sesji (wczytywana w kolejnej turze) nie zawierała opisów sceny. Modele "resetowały" pozy i gesty co turę — scena nie miała ciągłości.

**Problem (projektowy):** Zewnętrzny Narrator pisał w trzeciej osobie (`"Astra odwraca wzrok."`) — był opisem stanu, nie działaniem. Nie pasował do stylu 1. osoby reszty dialogu.

**Fix (zmiana projektowa):** Zewnętrzny Narrator usunięty całkowicie. Fizyczność przeniesiona bezpośrednio do pola `response` — obie postaci opisują swoje ciało, gesty i dotyk w gwiazdkach `*...*` w pierwszej osobie (styl Character.ai). Ponieważ `response` jest zapisywane w historii sesji, fizyczność przeżywa między turami — scena ma ciągłość.

Usunięte elementy:
- Stała `WSPOLNY_NARRATOR_BLOCK` z `main.py`
- `system_prompt += WSPOLNY_NARRATOR_BLOCK` z `_wspolny_generate()`
- Blok ekstrakcji `narrator` z JSON (`try: _data.get("narrator")`)
- `narrator` z return dict `_wspolny_generate()` → zastąpione `"narrator": ""`

---

#### 5. Zombie files usunięte

- `backend/inner_monologue_NEW.py` — plik nie był importowany, istniał w `.gitignore`, powodował konfuzję przy edycji
- `backend/prompts/astra/level_01_02.txt` — nigdy nie ładowany przez aktywny kod
- `backend/prompts/astra/level_03_04.txt` — j.w.
- `backend/prompts/astra/level_05_06.txt` — j.w.

---

### Niezmienione (świadoma decyzja)

- `amelia_persona.txt` sekcja `[MODUŁ AKTYWNY TYLKO WE WSPÓLNYM POKOJU]` — moduł zazdrości pozostaje. Bez ZASADY KONTRY jako wzmacniacza, "rzadka, sporadyczna zazdrość" jest elementem charakteru, nie bugiem.
- System XP/level w `companion_state.py` — nadal oblicza XP i zmienia level, ale obie postaci startują teraz z level 6 więc mechanizm jest faktycznie neutralny.
- Frontend — `appendBubble` nadal przyjmuje parametr `narrator` (dla backward compat), ale backend zwraca pusty string; element `.narrator-line` nigdy się nie wyświetla.

---

### Pliki zmienione

| Plik | Zmiana |
|---|---|
| `backend/main.py` | Rozdzielenie monologów, usunięcie Narratora i ZASADY KONTRY |
| `backend/amelia_companion_state.json` | Utworzony z level: 6 |
| `backend/inner_monologue_NEW.py` | USUNIĘTY |
| `backend/prompts/astra/level_01_02.txt` | USUNIĘTY |
| `backend/prompts/astra/level_03_04.txt` | USUNIĘTY |
| `backend/prompts/astra/level_05_06.txt` | USUNIĘTY |
| `wazne/audyty promptow/2026-06-13_audyt_prompt_assembly.md` | DODANY (raport audytu) |

**Git commit:** `7a50cee` — `fix: rozdziel instrukcje monologu Astry i Amelii, usun Narratora i ZASADE KONTRY`
