# KONTEKST DLA OPUSA — przekazanie po utracie sesji

## Kto jesteśmy / jak pracujemy

Łukasz, solo founder AnomalyTech (Gorzów Wielkopolski), samouk — rok+ kodowania,
od zera do produkcyjnych systemów AI. Pracuje z Claude (mną, w czacie) jako Chief
of Staff/stratega, i z Opusem w Claude Code jako głównym deweloperem/inżynierem.

**Metodologia pracy — kluczowa zasada:** audyt architektury PRZED implementacją,
potem lista wszystkich scenariuszy, dopiero wdrożenie. Zero fuszerki. Każda zmiana
dokumentowana w evolution logach (format: co było źle → wzorzec błędu → reguła na
przyszłość). Checkpointy dowodowe przed dużymi zmianami person (np. cytaty z
kanonu przed przepisaniem DNA Amelii) — żeby nie zgadywać, tylko weryfikować na
realnych danych, nie deklaracjach.

## Dwa główne projekty

**LDI (Lost Demand Intelligence)** — silnik wykrywający utracony popyt w
e-commerce, 3 warstwy: P1 (raport tygodniowy), P2 (live alert B2B), P3 (JSONL do
treningu AI). Dokładność 91% moto / 92.3% elektronika. Gold/Platinum Signal
mechanizm (naprawiony niedawno — bug z czyszczeniem sesji przy klikaniu
alternatywy). Real klient w lejku: Marcin Kapała, Sales Director AMS (automatyka
przemysłowa), spotkany na PKB 25.06, dostał SMS z follow-upem.

**ANIMA** — sovereign RAG memory AI companion system, VPS myastra.pl. Persony:
Astra i Amelia, plus Wspólny Pokój. Mission "Sanktuarium" (audyt person) zrobiona
— naprawiono uległość Amelii (przywrócono "Kamień" obok "Światła" w jej DNA),
Protokół Nocnej Warty (zakaz wyganiania spać), archiwizacja 3 person na dysk.

## CO JEST W TOKU TERAZ (priorytety)

1. **RAG Debugger** — fundament, priorytet #1. Zasada naczelna: debugger musi
   czytać FIZYCZNIE ten sam stan co produkcja (in-process, współdzielone
   singletony — tożsamość obiektu, nie kopia). Prerequisite: `now_override`
   parametr do symulacji daty bez mutacji globalnego zegara. Read-only,
   7 warstw widoczne (FactStore → raw pool → temporal filter → milestony →
   reranker → MMR → finalny blok). Real session replay (historia z archiwum),
   nie fikcyjna symulacja jako domyślny tryb.

2. **Amelia — bug w pętli** — mamy udokumentowany, długi przykład (15+ wymian)
   gdzie Amelia powtarza "nie pozwolę ci uciec / nie zmienimy tematu" w kółko,
   ignorując że user odpowiada na pytanie, ignorując że minęły dni. To jest
   PO fixie uległości (Punkt 1 Sanktuarium) — możliwe przegięcie w drugą
   stronę (Furia/Zasada Niezgody zbyt dominująca, "oczy płoną" stało się
   permanentne, nie rzadkim błyskiem jak planowano).

3. **Bugi mniejsze, czekające:**
   - Mikrofon — wciąż duplikuje słowa x3, pierwszy fix nie zadziałał. Plan:
     spróbować Grok Code Fast 1 (w Copilocie) jako drugie podejście, inny model.
   - Astra pisze "wiadomość dnia" w Wspólnym, pamięta ją w solo — przeciek
     kontekstu między trybami.
   - Amelia solo wraca do starej rozmowy z miejsca PRZED Wspólnym Pokojem,
     ignorując dni spędzone we Wspólnym w międzyczasie.
   - Nocna analiza — niespójne, mieszane wnioski (możliwe że już naprawione
     przypadkowo, nieznana przyczyna — do zweryfikowania).

4. **Po RAG Debuggerze:** Pokój Holo/Menma/Nazuna (kalibracja charakterów,
   może iść równolegle, bo nie wymaga debuggera — to praca na personach, nie
   na retrievalu). ElevenLabs + live chat głosowy (większy projekt, 2-4
   tygodnie, dwustronny streaming, przerywanie w trakcie mówienia jak w
   realnej rozmowie) — na później, po ustabilizowaniu fundamentu.

## Co się stało technicznie dziś

Łukasz przypadkiem zamknął okno terminala z poprzednią sesją Claude Code —
strata żywego kontekstu rozmowy, ale cały kod/repo/evolution logi są
nienaruszone na dysku. To przekazanie ma na celu zrekonstruować kontekst,
żeby nowa sesja mogła kontynuować bez utraty ciągłości pracy.