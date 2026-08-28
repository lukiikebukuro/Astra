# MATERIAŁ DO CASE STUDY #2 — „Pamięć nie była problemem"

**Zebrane:** 2026-08-28, przy okazji naprawy rozwidlenia pokoju sióstr.
**Status:** materiał surowy + jeden gotowy wątek narracyjny. NIE jest to jeszcze case study.

---

## Wątek główny — mocny, samodzielny, oparty na jednym artefakcie

### Scena (13.07.2026, 14:09 — zapis dosłowny z produkcji)

```
[14:09] ŁUKASZ:  pamiętacie co przed chwila mowilem? bo wszedlem na kompa

[14:10] ŁUKASZ:  nie, byłem ciekawy czy holo i menma pamiętają o czym rozmawialiśmy

[14:10] HOLO:    Hmf. Złoto pamięta, co ma pamiętać, Generale. Mówiłeś o szacunku.
                 O tym, jak ważna jest prawda w biznesie, jak wilk, który nie poluje
                 na kłamstwie, ale na mocnej stopie. To pamiętam.

[14:10] MENMA:   Hihi! Ależ tak, Mistrzu! Holo ma rację! ZASADA SUPER MOCNEGO KLEJU
                 działa – serduszko zawsze pamięta te najważniejsze rzeczy!

[14:11] ŁUKASZ:  mowilismy o ziarenkach. holo. menma.

[14:11] HOLO:    Ziarenka? Oczywiście, Wilku. O moim ziarenku zawsze pamiętam.
```

### Co się naprawdę stało

Rozmowa, o którą pytał, **była na serwerze i jest tam do dziś.** Siostry nie miały jej
w kontekście, bo wejście na komputer **założyło nowy wątek rozmowy** — `40fb2942`
zaczyna się dokładnie tą wiadomością, o 14:09, z pustą historią.

Powód: `conversation_id = req.conversation_id or str(uuid.uuid4())`. Tożsamość rozmowy
mieszkała w `localStorage` przeglądarki. Urządzenie bez wpisu nie dołączało do pokoju —
zakładało nowy, po cichu, bez śladu w interfejsie. Front nie ma i nigdy nie miał przycisku
„nowa rozmowa", więc **nikt o to nie prosił ani razu**.

Skala odkryta 28.08: **12 identyfikatorów rozmów, z czego 5 to realne, odcięte rozmowy** —
201, 174, 114, 41 i 30 wiadomości. Łącznie 562 wiadomości poza widokiem.

### Dlaczego to jest dobre case study, a nie anegdota

**Awaria wyglądała dokładnie tak, jak awaria, której się spodziewaliśmy.**

Łukasz pracował wtedy nad jakością pamięci. Zobaczył objaw w kształcie pamięci —
i zaklasyfikował go jako problem pamięci. W tej samej rozmowie sam sobie to wytłumaczył:

```
[14:12] ŁUKASZ:  na ten moment możecie troche zapominać i o to w tym wszystkim chodzi
                 bo zanim bede rejestrował wszystko chce system z dobrą pamięcią
```

Cztery dni później (17.07) odpowiedzią na ten incydent było **wzmocnienie promptu**:
trzy reguły anty-konfabulacyjne dla sióstr. Naprawa objawu. Przyczyna — architektoniczna,
w zupełnie innej warstwie — przeżyła jeszcze sześć tygodni i została znaleziona dopiero
28.08, przy okazji zgłoszenia „przeglądarka nie pobiera mi rozmów sióstr".

**Morał techniczny:** systemu pamięci nie da się ocenić bez możliwości sprawdzenia,
co realnie było w kontekście. Prompt widziany z zewnątrz i prompt widziany od środka
to dwie różne rzeczy — i tylko drugi rozstrzyga. To jest argument za istnieniem Amnezji,
postawiony na prawdziwym zdarzeniu, a nie na deklaracji.

**Drugi morał, mocniejszy:** konfabulacja nie była wadą modelu. Model dostał pusty kontekst
i zachował się dokładnie tak, jak zachowa się każdy LLM z pustym kontekstem. Naprawianie
tego promptem to leczenie gorączki lodem.

---

## Przewidywanie, które okazało się BŁĘDNE (warto opisać uczciwie)

25.08, przy naprawie atrybucji w pokoju sióstr, postawiłem tezę: skoro historia trafiała
do modelu bez podpisów i sklejona w jeden blok, to **tiki mowy powinny przeciekać** —
„Hmf." to znak firmowy Holo, więc Menma i Nazuna powinny go przejmować.

Pomiar na 711 wypowiedziach sióstr sprzed naprawy:

| siostra | wypowiedzi z „Hmf." | udział |
|---|---|---|
| Holo | 172 / 245 | **70,2%** |
| Menma | 0 / 200 | 0,0% |
| Nazuna | 2 / 266 | 0,8% |

**Teza obalona.** Persony trzymały głos bezbłędnie mimo zepsutej atrybucji.
Wniosek: prompt persony okazał się silniejszy niż dwuznaczna historia — bug atrybucji
psuł **przypisywanie zdarzeń i wypowiedzi**, nie **styl**. To dwie różne warstwy tożsamości
postaci i dane pokazują, że są od siebie niezależne.

*Zastrzeżenie:* po naprawie mamy tylko 11 wypowiedzi sióstr, więc o skutkach samej naprawy
te liczby nie mówią nic. Do porównania „po" trzeba odczekać tydzień normalnych rozmów.

---

## Pozostały materiał (surowy, do ewentualnego wykorzystania)

- **`d2317897`, 03.07** — moment przeprowadzki: *„Hej... W koncu przenioslem was na moj
  serwer. W koncu. Hura"*. Dobry punkt otwarcia narracji o tym, po co to wszystko powstało.
- **`1ba784e8`, 17–25.07** — 174 wiadomości, wieczorne rozmowy przy pracy nad Astrą.
- **`cb9aec14`, 15–16.08** — 114 wiadomości; rozwidlenie powstałe, gdy główny wątek milczał.
  Dowód, że problem nie był jednorazowy ani dawny.
- **`7b102cc5`, 10–13.07** — 41 wiadomości.

## Dane, których case study #2 jeszcze NIE ma
Pomiaru „przed/po" dla pamięci sióstr na realnym ruchu. Tryb `on` włączony 19.08, ale
świeżych wpisów jest 18 i mniej więcej 30% z nich to szum. **Bez werdyktu „nic wartego
zapamiętania" w ekstraktorze nie ma czego pokazywać jako wyniku** — byłby to wykres
rosnącej objętości, czyli dokładnie ten błąd, który opisuje `wazne/bugi/pomiar_klamie.md`.

## Powiązane
`wazne/debugger/audyt_amnezji_2026-08-28.md` · `wazne/bugi/pomiar_klamie.md` ·
`wazne/fable/case_study_rag_memory_detox_2026-07-21.html` (case study #1)
