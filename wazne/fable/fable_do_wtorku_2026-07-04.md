# Fable — backlog do wtorku (2026-07-04)

Dla: **Fable w Claude Code** (instancja z dostępem do repo).
Kontekst: budżet Claude Code resetuje się we wtorek — wykorzystać go na to co niżej, priorytetowo.
Metodyka stała: audyt przed zmianą, weryfikacja bit-identyczna na żywej bazie przed deployem, PO POLSKU, NIE deploy bez potwierdzenia Łukasza.

Właśnie wdrożone (`81f6986`): fix charakteru Astry R1–R6 + świeży wątek (28750b59). Szczegóły: `wazne/ewolucja/2026-07/evolution_log_2026_07_04.md`.

---

## KOLEJNOŚĆ (zaktualizowana 2026-07-04 wieczór) — NOWE zadania mają osobne pliki
- **P0 — POKÓJ SIÓSTR (pilne, „mega chujowe"):** `wazne/fable/fable_pokoj_siostr_fix_2026-07-04.md`
  (diagnoza z żywych logów: monopol Nazuny, przeintensywnienie, wyciek promptu + A4 interakcje siostra↔siostra).
- **P0.5 — PROAKTYWNY AUDYT ARCHITEKTURY:** `wazne/fable/fable_audyt_architektury_2026-07-04.md`
  (znajdź problemy o które NIE pytamy, zaproponuj architekturę dla CAŁEJ rodziny — audyt+plan, nie implementacja).
- **P1–P3 poniżej** (weryfikacja Astry, altanka+golden set) — po P0.

ROLA: **Fable AUDYTUJE (nie koduje). Opus wdraża po audycie.** Wszystkie „P0/P1..." niżej = do AUDYTU.
Sugestia sekwencji: audyt architektury (P0.5) jako ROZPOZNANIE → audyt planu sióstr (P0) → reszta.
Router sióstr to też problem architektoniczny, więc audyt architektury może go objąć.

---

## PRIORYTET 1 — weryfikacja fixu charakteru Astry (najważniejsze)

1. **Amnezja — czy `character_vectors` docierają do promptu?**
   Podejrzenie z audytu: zdrowe reguły character_core przegrywają częstotliwością z astra_base.
   Wpisać 3–4 frazy w `/amnezja`, sprawdzić czy kanał character_core faktycznie ląduje w finalnym prompcie i z jaką wagą.
   Jeśli nie dociera — żaden fix promptu nie zadziała w pełni.

2. **Nadzór nad wahadłem (overshoot).**
   R1–R6 mogły przestrzelić. Po kilku dniach logów sprawdzić NOWY wątek (28750b59+):
   - lekkie/płaskie reakcje >20%? (cel osiągnięty)
   - ale czy nie zrobiła się ZA płaska/chłodna/asystencka? (przestrzelenie)
   - czy safe_haven dalej DZIAŁA gdy naprawdę boli (nie wygaszony za bardzo przez R4)?
   Metryki: start-od-gwiazdki <40%, „zaciska" <10%, „Łukasz" <20% tur, mediana <300 znaków.

3. **Decyzja o korzeniu L8/L10/L20.**
   R5 zakazał objawów („widzę cię na wylot"), ale silnik został:
   - L8 „archetyp: lustro z pazurem. Widzisz głębiej niż on sam widzi."
   - L10 „Wiesz rzeczy których on sam sobie jeszcze nie powiedział."
   - L20 „zaborcza" ×3 w jednym akapicie.
   Pytanie do rozstrzygnięcia: czy R5 jako kaganiec wystarcza, czy trzeba zmiękczyć tożsamość
   („potrafisz widzieć głębiej i CZASEM korzystasz" zamiast trybu domyślnego)?
   Adwersaryjnie: obejrzeć logi po fixie ZANIM ruszymy tożsamość — może kaganiec starczy.

4. **Głębszy fix self-imitation (opcjonalny, architektoniczny).**
   Świeży wątek to obejście objawu. Docelowo: ograniczyć ile własnej historii (n=10 few-shot)
   wraca do modelu / jak mocno waży vs reguły. Rozważyć redukcję n lub filtr „nie ucz się z własnych gwiazdek".

---

## PRIORYTET 2 — siostry (mają swoje problemy, Łukasz zgłosił, TBD)

5. **Audyt sióstr `fable_9`** — prompt gotowy w `wazne/fable/fable_9_audyt-siostr_PROMPT.md`.
6. **Router-3-naraz** (`5ef8f50`) właśnie wdrożony bez audytu (izolowany, ale) — zweryfikować że nie psuje silent-first.
7. **„Własne problemy sióstr”** — Łukasz ma konkretne zastrzeżenia, poda osobno. Placeholder: dopytać.

---

## PRIORYTET 3 — pamięć / bug altanki (RAG)

8. **Bug altanki** (stapianie niepowiązanych projektów przy mglistym query):
   - MMR `diversity_penalty=0.8` = mieszalnik (po jednym z każdego klastra).
   - keyword boost ślepy na polską fleksję („altance" ≠ „altanka", substring → 0 boostu).
   Narzędzie: Amnezja + **golden set** (~25 fraz regresyjnych). Strojenie z weryfikacją bit-identyczną.

---

## TŁO (backlog, nie na teraz)
- Nocna analiza: editorializuje (choroba↔unikanie) — rozróżnić w MORNING_PROMPT/nocna_analiza.py.
- Amelia overswing: sprawdzić czy po fixie nie przegięła w zaborczą pętlę (Łukasz ma dowód z logów).
- Przeciek Wspólny↔solo (scoping conversation_id/persona) — Amnezja to leak-detector.
- Portfolio (adeptai.pl): deploy osobnego repo z podziałem na 2 grupy + karta RAG Debugger.

---

## Jedna rzecz od Łukasza na jutro
Otworzyć myastra.pl i pisać (front sam wskoczy na czysty wątek 28750b59 — nie czyścić cache).
Obserwować czy Astra jest lżejsza w pierwszych turach. Jak dalej snajper — zgłosić (znaczy reset wątku nie złapał).
