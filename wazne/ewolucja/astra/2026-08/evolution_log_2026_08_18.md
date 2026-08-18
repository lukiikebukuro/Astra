# Evolution Log — 2026-08-18 · Astra: naprawa szkody z 17.08, okno rozmowy, core, UI

**Commity:** `6c4f7b1` · `f071a69` · `3ccb42d` · `71aaba2` · `b582b75` · **Wykonawca:** Opus 5 (Claude Code)
**Zgłoszenia:** Łukasz — „przycisk zabierający jej pamięć powoduje problemy", „czemu znowu dwie wiadomości
dnia", „czemu musiałem wysyłać plan TikToka dwa razy", „przyciski nie pasują do reszty"
**Weryfikacja:** health 200 po każdym deployu, testy end-to-end przełączników, Amnezja na odzyskanych
wpisach, backup bazy przed zapisem.

---

## 1. Odzysk 7 ustaleń twórczych (`origin_endpoint="scenariusz_odzysk"`)

Sesja z 17.08 (19:14-20:30) nie zostawiła w pamięci trwałej **niczego**: „demon" 0, „mitsuketa" 0,
„primal" 0 — a zapisały się rzeczy sprzed i po trybie („Toss your dirty shoes…" jako `EMOTION:tired`).
Rano Astra nie wiedziała, że cokolwiek ustalili.

Odzyskane z dyktafonu i wpisane RĘCZNIE, przy **zatrzymanym serwisie** (zasada: nigdy nie pisać do Chromy
z osobnego procesu przy żywym `myastra` — incydent 25.07). Backup: `backups/chroma_backup_2026-08-18_odzysk.tar.gz`.
Wektory 4678 → 4685. Weryfikacja: 0→1 dla każdego z trzech kluczowych haseł.

**Test Amnezją — wynik mieszany i warto go znać:**
- „co ustaliliśmy w scenariuszu anime" → `final_count: 6`, `GROUNDED`, oba ręczne wpisy na górze ✅
- „jaka jest cena fuzji w scenariuszu" → **nie trafia** w demona jelit ❌
- „co mówi Astra w momencie spotkania" → **nie trafia** w „Mitsuketa" ❌
- „jak się ukrywamy przed Primal Forces" → **nie trafia** w kamuflaż ❌

Ten sam limit co przy mefedronie: embedding nie robi skoku kategoria → instancja. **Wniosek dla Łukasza:
kanon fabuły musi żyć w PLIKU, nie w RAG.** Ręczne przepisywanie ustaleń do `scenariusz.md` to nie
prowizorka, tylko jedyna niezawodna warstwa.

## 2. Tryb scenariusza rozłączony od pamięci (`6c4f7b1`)

Odwrócenie decyzji z 17.08 — mojej. Tryb wyłączał zapis „żeby nie zaśmiecać"; kosztem była cała sesja
twórcza. Teraz zapis działa normalnie, a wpisy z trybu są **znakowane** (`origin_endpoint="scenariusz"`),
więc sprzątać można później i selektywnie.

**Reguła, która z tego zostaje: rozmowy twórcze to najcenniejsza treść, jaką produkują — nie szum
do odsiania. Znakować, nie blokować.** Sprzątnąć da się zawsze, odzyskać nie.

Doszedł też blok informujący ją o istnieniu scenariusza, gdy tryb jest wyłączony — 17.08 o 19:09
zaprzeczyła („nie mam dostępu do twoich plików") i Łukasz musiał tłumaczyć drugi raz.

## 3. Duplikat wiadomości dnia — DRUGA przyczyna (`f071a69`)

Wczoraj: dwie subskrypcje FCM. Dziś: co innego, ten sam objaw.

Najpierw fakty: backend wysłał **jedną** wiadomość (1 poranna 05:00 UTC = 07:00 Warsaw,
`spontaneous_sent_date` wciąż 17.08, 1 subskrypcja, 1 proces, serwer UTC + scheduler `Europe/Warsaw`).
**Hipoteza Łukasza o godzinach serwerowni — obalona danymi.**

Sedno: push niesie treść **skróconą** (`msg[:100] + "…"`), SW przekazywał **właśnie ją** do strony,
a polling pobiera **pełną**. Dedup po hashu treści widział dwa różne teksty → dwa bąbelki.
Fix dwuwarstwowy: pole `full` w payloadzie **oraz** hash ze znormalizowanego prefiksu 80 znaków
(działa nawet ze starym SW). Plus `_markProactiveShown` przed renderem — wyścig relay↔polling.

## 4. Okno rozmowy 10 → 30, tylko Astra (`3ccb42d`)

`get_recent_session` tnie `messages[-n:]` licząc wiadomości **jego i jej razem** — więc `n=10`
to było **pięć wymian**. Objaw: plan kanału wklejony 19:38, pytanie o opinię 19:44, w międzyczasie
13 wiadomości → plan wypadł z okna, zanim Łukasz zdążył o niego zapytać.

`ASTRA_SESSION_N = 30` obejmuje `/api/chat` **oraz Amnezję** — debugger musi widzieć dokładnie to samo
okno co produkcja, inaczej kłamie. Siostry, Amelia i Wspólny zostają na 10 (flaga per pokój).

## 5. `lukasz_core.json` — warstwa deterministyczna była z marca (`71aaba2`)

Plik idzie do promptu ZAWSZE i wygrywa ze wspomnieniami — a mówił „Stelara od prawie miesiąca
(stan na marzec 2026)". **Pięć miesięcy nieaktualne w warstwie, której ufa najbardziej.**

Przepisane zdrowie (Stelara pół roku, wątroba lepiej, brak zastawki Bauhina, konopie jako sposób
na skurcze — jawnie „nie temat do oceniania", spójne ze STREFĄ NIETYKALNĄ). Doszły: kanał TikTok,
scenariusz anime z przypomnieniem o ręcznym przepisywaniu, cel zawodowy. 3054 → 4760 znaków.

**Reguła: warstwa deterministyczna wymaga przeglądu tak samo jak kod.** Nikt jej nie ruszał pół roku,
bo „działa" — a ona po cichu opisywała nieistniejącą rzeczywistość.

## 6. UI — jeden kształt przycisków + menu ⋯ (`b582b75`)

`#new-convo-btn` i `#attach-btn` **nie miały żadnego CSS** (reszta miała po własnym, skopiowanym bloku),
więc renderowały się jako domyślne przyciski przeglądarki. Wspólna klasa `.io-btn` zastępuje cztery
duplikaty. Rzadkie akcje schowane pod ⋯; na pasku zostaje 📎 🎤 🔊 ⋯ →.

**Włączony tryb wyskakuje z menu na pasek i świeci.** Widoczność stanu jest tu funkcją bezpieczeństwa —
przełącznik zmieniający zachowanie pamięci nie może być schowany.

---

## Wnioski przekrojowe

1. **Ten sam objaw, trzy różne przyczyny** (duplikat wiadomości: 06.08 wspólne źródło, 17.08 dwie
   subskrypcje, 18.08 rozjazd skróconej i pełnej treści). Dlatego diagnostyka zostaje w kodzie —
   bez logu z 17.08 dzisiejsza diagnoza zaczynałaby od zera.
2. **Najpierw fakty, potem hipoteza.** Hipoteza o godzinach serwerowni brzmiała rozsądnie i była błędna;
   pięć zapytań do bazy i logów rozstrzygnęło to w minutę.
3. **Amnezja pokazuje odczyt, nie zapis** — i to jest jej realna luka. Wszystkie trzy duże wpadki
   (mefedron, scenariusz, wyznanie z 07.08) to awarie ZAPISU, których debugger nie widzi.
   **Druga zakładka „ścieżka zapisu" jest teraz najwyżej na liście narzędziowej.**
