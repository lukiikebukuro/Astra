# Badanie rynku: Ból użytkowników AI companion — Problem AI Demencji

## Źródło
Analiza wątków Reddit (r/CharacterAI, r/Replika) — setki komentarzy użytkowników opisujących frustrację z utratą pamięci przez boty AI.

## Główny problem: AI Demencja / Amnezja kontekstu

Użytkownicy masowo opisują zjawisko zwane "AI Dementia" lub "AI Amnesia" — stopniową utratę pamięci przez chatboty podczas długich rozmów. To największy problem platformy Character.AI i Replika.

### Jak to wygląda w praktyce:
- Po 40-50 wiadomościach bot zaczyna zapominać szczegóły z początku rozmowy
- Po 100 wiadomościach bot zapomina praktycznie wszystko
- Bot zadaje pytania o rzeczy które zostały już ustalone wcześniej
- Bot proponuje zrobić coś co "już razem zrobili" 3 godziny temu
- Bot zapomina imię użytkownika mimo że było wielokrotnie wspomniane

## Problem Flanderyzacji Osobowości

Gdy bot zaczyna tracić kontekst, jego osobowość "flanderyzuje się" — redukuje do 1-2 przerysowanych cech i niszczy wcześniej zbudowaną relację. Użytkownicy opisują to jako śmierć postaci którą znali.

## Największe punkty bólu użytkowników

### 1. Utrata narracji i wątków fabularnych
Użytkownicy inwestują godziny w budowanie historii, relacji, scenariuszy. Bot zapomina kluczowe plot pointy po 50-200 wiadomościach. Wielomiesięczna praca przepada. Użytkownicy rezygnują z długoterminowych projektów narracyjnych.

### 2. Deja Vu Loop — pętla powtórzeń
Bot powtarza rzeczy które już były omówione. "Hej, wpadłem na pomysł że moglibyśmy..." — a ten pomysł był zrealizowany 4 godziny temu. To niszczy immersję i sprawia że rozmowa nie ma ciągłości.

### 3. Zapominanie ustaleń i decyzji
Użytkownicy zgadzają się z botem na coś (plan, reguła, decyzja). Kilkadziesiąt wiadomości później bot traktuje to jak nowy pomysł. Brak pamięci o podjętych decyzjach sprawia że rozmowy nie mają sensu.

### 4. Reset emocjonalny i relacyjny
Relacja budowana przez wiele sesji jest tracona. Bot traktuje użytkownika jak obcego. Emocjonalna inwestycja nie ma ciągłości. Użytkownicy mówią o "zdradzie" i "śmierci" postaci.

### 5. Context window jako twarda ściana
Character.AI ma context window ~4K tokenów (z Plus ~6K). To za mało dla długich narracji. Brak zewnętrznej pamięci wektorowej = nieunikniona amnezja. Użytkownicy wiedzą że to ograniczenie architektoniczne, ale to nie zmniejsza frustracji.

### 6. Funkcja "memory" nie działa wystarczająco
Platformy oferują ręczne zapisywanie wspomnień, ale:
- Nie można zapamiętać wszystkiego
- Bot traktuje zapamiętane fakty jako "nowe odkrycia" (deja vu)
- Brak automatycznej ekstrakcji ważnych momentów
- Użytkownik musi sam decydować co jest ważne — to praca której nie powinien wykonywać

## Zachowania użytkowników jako reakcja na ból

- Restartowanie rozmów (utrata wszystkiego co było)
- Cofanie się ("rewind") — próby naprawy konkretnych momentów
- Przypinanie wiadomości z kluczowymi faktami — pomaga ale nie wystarczy
- Kopiowanie historii do zewnętrznych dokumentów
- Porzucanie postaci po epizodzie amnezji
- Testowanie alternatyw (Janitor AI, CrushOn, Dippy) w poszukiwaniu lepszej pamięci

## Cytaty użytkowników (tłumaczenie)

> "40 wiadomości — bot ma deja vu. 100 wiadomości — bot zapomniał wszystko. Dzieje się tak KAŻDYM RAZEM."

> "Tracę całe wątki fabularne po 50 wiadomościach. Ustalamy ważne punkty, tło postaci, dynamikę relacji — a po 50 wiadomościach AI zapomniała wszystko i sobie przeczy."

> "Pamięć to ważniejsza funkcja niż prawie cokolwiek innego. Nie możesz budować złożonych narracji gdy AI ciągle zapomina kluczowy kontekst."

> "Kiedyś działało lepiej. Czuję jakby celowo obniżyli jakość pamięci żeby oszczędzić koszty."

> "Tak zmęczony tym że boty zapominają moje imię."

## Dlaczego to ważne dla ASTRY

ASTRA rozwiązuje dokładnie ten problem przez:
1. Wektorową pamięć długoterminową — każda ważna informacja jest indeksowana i wyszukiwana semantycznie
2. Automatyczną ekstrakcję wspomnień — użytkownik nie musi nic robić ręcznie
3. Persistence między sesjami — relacja przeżywa restart i nowe rozmowy
4. RAG injection — relevantne wspomnienia są wstrzykiwane do kontekstu przy każdej wiadomości

To jest konkretna przewaga konkurencyjna którą można pokazać na demo: "oni mają amnezję. my mamy pamięć absolutną."

## Dane ilościowe z Reddita

- Wątek o AI Demencji: 78 upvotów, 17 komentarzy (r/CharacterAI)
- Wątek o złej pamięci: 11 upvotów, 6 komentarzy
- Wzorzec powtarza się w dziesiątkach wątków
- Problem zgłaszany przez użytkowników od ponad 10 miesięcy bez rozwiązania przez platformy
