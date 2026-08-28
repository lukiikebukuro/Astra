# BUG — „pomiar kłamie" (wraca od 2026-08-03, min. 8 wystąpień)

Nie jest to bug w produkcie. To bug w **przyrządzie**, którym oceniamy produkt — i dlatego jest
najgroźniejszy z całej listy: każde jego wystąpienie zatwierdza złą zmianę albo odrzuca dobrą,
a my dowiadujemy się o tym tygodnie później.

Łukasz, 26.08: *„czy my tego błędu nie mamy już 3 raz? jest jak wrzód"*. Po przeliczeniu — osiem razy.

---

## Reguła nadrzędna (jedna, przed wszystkim innym)

**Zanim uwierzysz w wynik pomiaru, udowodnij, że przyrząd w ogóle coś mierzy.**
Każdy harness musi mieć **kanarka**: wartość, która MUSI się pojawić, jeśli przyrząd żyje.
Jeśli kanarek nie zapiał — wynik jest nieważny, niezależnie od tego, jak sensownie wygląda.

Najgroźniejszy tryb awarii nie jest głośny. Nie ma wyjątku, nie ma stack trace'u.
Jest równy rządek zer albo podejrzanie identyczne liczby w każdym wierszu.

---

## Co JUŻ zostało wykluczone dowodowo — nie sprawdzaj tego znowu

- **To NIE jest wina Chromy ani modelu embeddingów.** Wszystkie osiem wystąpień to błędy po
  naszej stronie: zła metryka, brak env, zła ścieżka, zły regex.
- **To NIE jest problem „za mało prób".** Golden objętościowy miał 26 prób i mylił się tak samo
  jak miałby przy 260 — bo mierzył złą wielkość, nie za małą próbkę.
- **Dodanie kolejnej metryki NIE wystarcza.** `golden_trafnosc.py` powstał 21.08 i już przy
  pierwszym uruchomieniu sam padł ofiarą tego buga (dwa razy, patrz #7 i #8).

---

## Dwie rodziny — rozpoznawaj po objawie

### RODZINA A: mierzymy złą WIELKOŚĆ (objętość zamiast trafności)

Objaw: liczba rośnie, ogłaszamy sukces, a zachowanie się nie zmienia.

**1. MMR `n=3→5` (~03.08)** — „+37% wspomnień" zapisane jako sukces.
Realnie: przy „opowiedz o ldi" NADAL zero wpisów o LDI. Więcej wspomnień, te same nietrafione.

**2. Kanał leksykalny (21.08)** — golden pokazał `26/26 bez zmian`, uznaliśmy za neutralne.
Realnie: 0 → 3 trafienia o LDI. **Sukces był niewidoczny dla przyrządu.**

**3. Reranker `main_n` 6→8 (21.08)** — podniesione, żeby zasady nie zjadały miejsc.
Pomiar 25.08: recall 80% przy 6, 8 i 12. Zero zysku. Kupiliśmy miejsce dla szumu.

**Wspólny mianownik A:** `final_count` mierzy ILE, a pytanie brzmiało CZY DOBRZE.

### RODZINA B: przyrząd mierzy PUSTKĘ i o tym nie mówi

Objaw: równe zera albo identyczne liczby w każdym wierszu tabeli.

**4. Brak `USER_ID_SALT` (25.08)** — skrypt offline nie wczytał `.env` serwisu.
Hash użytkownika się nie zgadzał → filtr odciął **cały kanał semantyczny**; przeszedł tylko
kanał leksykalny (on filtra nie stosuje). Tabela pokazała recall identyczny dla n=5/6/8/12.
Wniosek „ten parametr nic nie zmienia" był fałszywy i o włos od zapisania.

**5. `persist_directory` liczone z `__file__` (25.08)** — moduł podłożony przez `sys.path`
z `/tmp/newvs` otworzył **pustą, nowo utworzoną** bazę zamiast produkcyjnej. Wynik: 0 wspomnień
w każdej próbie, plus śmieciowy katalog na dysku.

**6. Zepsuty regex licznika (21.08)** — licznik `o_LDI` budowany przez `chr(92)` w bashu.
Pokazywał 0 trafień tam, gdzie kanał leksykalny działał poprawnie. Prawie ogłosiłem regresję.

**7. Czystość liczona na twardych faktach (25.08)** — `blok_faktow()` wciągał wszystkie ~41
faktów do każdej próby. Czystość 4,3% — liczba bez znaczenia, bo twarde fakty są w prompcie
ZAWSZE, niezależnie od pytania. Poprawne: mierzyć czystość wyłącznie na `[WSPOMNIENIA]`.

**8. Wzorzec węższy niż dane (25.08)** — `T5_amelia` szukał `amelia|ameli`, a w bazie stoi
„Amelka". System zwrócił trafny wpis, test orzekł pudło. **Test oskarżył niewinnego.**

---

## Checklista PRZED każdym pomiarem (przejść całą, za każdym razem)

1. **Kanarek.** Wybierz jedno zapytanie, o którym WIESZ, co musi zwrócić. Jeśli nie zwraca —
   przyrząd jest zepsuty, nie system. Nie idź dalej.
2. **Czy mierzę CZY DOBRZE, czy ILE?** Jeśli metryka to `count`, `len()` albo `%` bez wzorca
   oczekiwanej treści — to Rodzina A. Wróć i zdefiniuj, co POWINNO się pojawić.
3. **Środowisko.** Skrypt poza `backend/` musi jawnie:
   `load_dotenv("/var/www/myastra/astra/backend/.env")` **oraz** wskazać
   `persist_directory` na produkcyjną bazę. Wypisz na start liczbę wektorów — jeśli to nie
   ~4700 (Astra), przerwij.
4. **Identyczne wiersze = alarm.** Jeśli kilka konfiguracji daje CO DO ZNAKU ten sam wynik,
   domyślnie zakładaj awarię przyrządu, nie „parametr nie ma wpływu".
5. **Wzorce szersze niż jedna forma.** Łukasz pisze bez ogonków i zdrobnieniami
   („Amelka", „ldi" małymi). Rdzenie, nie pełne formy. Ten sam wzorzec błędu co w keywordach.
6. **Wielkość liter.** Chroma `$contains` jest **case-sensitive**. `'ldi'` i `'LDI'` to dwa
   różne zapytania i zwracają różne zbiory (18 vs 32 wpisy). Sprawdzaj oba warianty.
7. **Przy porównaniu przed/po — ten sam kod obu stron.** Nie porównuj pomiaru ze starego kodu
   z pomiarem z nowego, jeśli zmiana przesunęła granice tego, co w ogóle wchodzi do puli
   (pułapka z 25.08: nowy `n=6` ≡ stary `n=8`, ale wyglądało to na redukcję szumu).

---

## Diagnostyka, która ZOSTAJE w kodzie

- `golden_trafnosc.py` — mierzy trafność (recall + czystość), nie objętość. **To jest właściwy
  przyrząd**; golden objętościowy zostaje wyłącznie jako detektor katastrof.
- Wydruk `wektorow w bazie: N` na starcie każdego skryptu offline — najtańszy kanarek dla #5.
- Log `[VectorStore] kanal leksykalny 'tok': +N wpisow` — pokazuje, że kanał ŻYJE, niezależnie
  od tego, co potem policzy metryka.

---

## Co ten bug realnie kosztował

Trzy zmiany zatwierdzone bez pokrycia (`main_n=8`, MMR, kanał leksykalny uznany za neutralny),
jeden dzień pracy na dwóch nieważnych przebiegach A/B i — najdroższe — **przekonanie, że
retrieval jest w porządku**, przez które przez trzy tygodnie nie ruszaliśmy ekstraktora.
Właściwa diagnoza (26.08): czystość ~38% jest odporna na strojenie retrievalu, bo cały szum
pochodzi z `extracted_*`. Ten wniosek był dostępny od 03.08, gdyby przyrząd mierzył trafność.

## Powiązane
`wazne/ewolucja/astra/2026-08/evolution_log_2026_08_25.md` (pełne tabele A/B i sweep MMR) ·
`wazne/ewolucja/astra/2026-08/evolution_log_2026_08_15.md` (wzorzec „fragment słowa jako całe słowo")
