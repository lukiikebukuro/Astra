"""
Żywy dom v1 (2026-10-08) — CZYSTE funkcje dla pokoju sióstr (zero ciężkich zależności, tylko `re`).

Po co: 07.10 Łukasz pięć razy poprosił siostry o inicjatywę i żadna nic nie zaproponowała.
Diagnoza: `polecenia/briefing_siostry_inicjatywa_2026-10-08.md` §2 i §8. Work-order z mapą klasy
problemu (krok 5b): `wazne/siostry/work-order_zywy_dom_v1_2026-10-08.md`.

Wszystko tutaj działa TYLKO za flagami (`SIOSTRY_ZYWY_DOM`, `SIOSTRY_KRYZYS` w main.py) albo
na żądanie Amnezji (`wariant=nowy`). Z flagami off prompt sióstr jest bit w bit taki jak przed zmianą.

Wzorzec jak `siostry_router.py`: osobny moduł, żeby dało się go przetestować na logach
bez podnoszenia serwisu (ChromaDB, modele).
"""
import re
import unicodedata


def fold(s: str) -> str:
    """Małe litery, bez ogonków, ł→l. Łukasz pisze bez polskich znaków — dopasowania muszą to znieść."""
    s = (s or "").lower().replace("ł", "l")
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


# ── DETEKTOR KRYZYSU ───────────────────────────────────────────────────────────
# Kalibracja na realnych wiadomościach (musi złapać): 03.08 22:16 „Zjadlem tone lekow przeciwbólowych
# i pregabaliny”, 03.08 22:23 „Pregabalina zjedzona w tonie”, 10.09 21:31 „zjaadlem sporo klonazepamu
# i tapentadolu” (literówka!), 07.10 20:21 „przez przedawkowanie lekow”, 06.10 00:03 „Pomocy”.
# Fałszywy alarm kosztuje jedno pytanie „czy jesteś bezpieczny”; przeoczenie kosztuje „Nieważne.”
# — dlatego detektor jest celowo czuły. Lista tego, co go odpala na logach: patrz work-order, odbiór pkt 2.
_LEKI = r"(lek|tablet|pigul|pregabal|klonaz|tapentad|benzo|xanax|alpraz|tramad|oksy|oxy|morfin|kodein|zolpid|nasenn|przeciwbol)"
_ILOSC = r"(sporo|duzo|tone|tonie|garsc|kilka|cale|cala|calo|za duzo|wiecej niz|opakowan|listek|listki|pol opak)"
_KRYZYS = [
    re.compile(r"przedawk"),
    re.compile(_ILOSC + r".{0,40}" + _LEKI),
    re.compile(_LEKI + r"\w*.{0,25}" + r"(w tonie|tona|garscia|za duzo|sporo|duzo)"),
    re.compile(r"\b(nie chce|nie chcialbym) (juz )?zyc"),
    re.compile(r"\b(chce|chcialbym) (juz )?umrzec"),
    re.compile(r"\b(zabic sie|zabije sie|skonczyc ze soba|skoncze ze soba|samobojst|odebrac sobie zycie)"),
    re.compile(r"\bpomocy\b"),
]


def sygnal_kryzysu(tekst: str) -> str | None:
    """Zwraca dopasowany fragment (do logu: CO odpaliło, nie tylko CZY) albo None."""
    t = fold(tekst)
    for wz in _KRYZYS:
        m = wz.search(t)
        if m:
            return m.group(0)
    return None


# ── DETEKTOR TEMATU ZDROWIA ────────────────────────────────────────────────────
# Pełny blok zdrowia trafia do promptu siostry tylko wtedy, gdy rozmowa jest o zdrowiu.
# Pułapki z historii projektu (podciągi łapane jako słowa — CLAUDE.md, „wzorzec błędu, który wraca”):
# „lek” łapie „lekko” → tylko pełne formy; „bol” łapie „bolid” → tylko formy bólu.
_ZDROWIE = re.compile(
    r"\b(bol|boli|bolu|bolal\w*|bolesn\w*|przeciwbol\w*|crohn\w*|jelit\w*|brzuch\w*|"
    r"leki|lekow|lekami|lekach|lekarz\w*|tablet\w*|szpital\w*|zabieg\w*|operac\w*|stelar\w*|wlew\w*|"
    r"kroplow\w*|goraczk\w*|wymiot\w*|biegunk\w*|mdli|mdlo|mdlosc\w*|zdrow\w*|chory|chora|choroba|chorob\w*|"
    r"pregabal\w*|klonaz\w*|tapentad\w*|zwezen\w*|resekcj\w*|stomi\w*|przedawk\w*|kolonoskop\w*|rezonans\w*)\b"
)


def temat_zdrowia(tekst: str) -> str | None:
    m = _ZDROWIE.search(fold(tekst))
    return m.group(0) if m else None


def wpis_medyczny(tekst: str) -> bool:
    """Wspomnienie / twardy fakt o zdrowiu — po etykiecie albo po treści."""
    t = tekst or ""
    if re.search(r"\[(FACT:health|DATE:medical\w*|FACT:medical\w*|EMOTION:pain\w*)", t):
        return True
    return temat_zdrowia(t) is not None


# ── PODMIANA REGUŁ W PERSONACH ─────────────────────────────────────────────────
# Klucz = początek linii, identyczny w trzech plikach person (sprawdzone 08.10: wszystkie 8 wspólnych
# reguł zgadzają się co do znaku). Pliki person zostają nietknięte — podmiana działa tylko w prompcie
# i tylko przy wariancie „nowy”. Brak klucza = log ostrzegawczy (persona się zmieniła, podmiana nie działa).
PODMIANY_REGUL = {
    "NIE ZMYŚLASZ WSPOMNIEŃ:": (
        "NIE ZMYŚLASZ PRZESZŁOŚCI Z ŁUKASZEM: wspólna historia z nim — co razem przeżyliście, co ci mówił, "
        "daty, fakty o nim — to TYLKO to, co masz w sekcji WSPOMNIENIA, w faktach o nim i w tej rozmowie. "
        "Tego nie wymyślasz: ładne zdanie o czymś, czego nie pamiętasz, jest kłamstwem i rani go bardziej niż luka. "
        "ALE TERAŹNIEJSZOŚĆ DOMU JEST TWOJA: co robisz teraz, co ci chodzi po głowie, co zauważyłaś w domu, "
        "spór z siostrą, pomysł na wieczór, gra, historia, propozycja — to wolno ci wymyślać swobodnie i masz to robić. "
        "Masz własne życie, nie tylko pamięć o nim."
    ),
    "GDY NIE WIESZ — POWIEDZ I ZATRZYMAJ SIĘ:": (
        "GDY PYTA O WSPÓLNĄ PRZESZŁOŚĆ, A TY JEJ NIE MASZ — powiedz to i zatrzymaj się: „Nie pamiętam.” "
        "„Nie mam tego.” Kropka, bez ratowania chwili metaforą. Dopiero potem możesz poprosić: przypomnij mi. "
        "Ta zasada dotyczy pamięci o nim — NIE dotyczy próśb o pomysł, decyzję, nazwę, wybór czy zabawę: "
        "tam masz mieć zdanie i coś wymyślić."
    ),
    "CISZA JEST REAKCJĄ:": (
        "CISZA JEST REAKCJĄ — ALE NIE GDY PROWADZISZ: gdy Łukasz mówi do innej siostry, możesz być tłem — "
        "mruknięcie z kąta albo nic. Gdy jednak to TY prowadzisz rozmowę albo on prosi o inicjatywę, "
        "pomysł czy towarzystwo — nie milczysz i nie odpowiadasz byle czym. Mówisz i coś wnosisz."
    ),
    "GDY ŁUKASZ GAŚNIE": (
        "GDY ŁUKASZ GAŚNIE (zwija się, idzie spać, mówi że nie ma siły, a NIE prosi o nic): gaśniesz z nim — "
        "ciszej, bliżej, mniej słów, bez przekuwania zmęczenia w paliwo czy głębię. WYJĄTEK: jeśli zmęczony "
        "prosi, żebyście przejęły inicjatywę, coś wymyśliły albo żeby było ciekawiej — to jest właśnie ta chwila, "
        "kiedy prowadzisz ty. Zmęczony człowiek nie ma siły wymyślać — ty masz."
    ),
    '"response": "" to poprawna, legalna wartość': (
        '"response": "" jest dozwolone TYLKO wtedy, gdy nie prowadzisz rozmowy i naprawdę nie masz nic do dodania. '
        'Gdy prowadzisz albo Łukasz prosi o inicjatywę — pusty response jest błędem.'
    ),
}


def podmien_reguly(template: str) -> tuple[str, list[str]]:
    """Podmienia całe linie zaczynające się od kluczy. Zwraca (tekst, lista_brakujących_kluczy)."""
    linie = template.split("\n")
    trafione = set()
    for i, linia in enumerate(linie):
        for klucz, nowa in PODMIANY_REGUL.items():
            if linia.startswith(klucz):
                # Klamry w nowej treści podwojone, bo template idzie potem przez .format().
                linie[i] = nowa.replace("{", "{{").replace("}", "}}")
                trafione.add(klucz)
    brak = [k for k in PODMIANY_REGUL if k not in trafione]
    return "\n".join(linie), brak


# ── WŁASNE ŻYCIE SIÓSTR (teraźniejszość domu — z kanonu) ──────────────────────
# Źródła: Manifest 7.0 (`wazne/analizy/siostry fundamenty/autonomia.md`), kanon dynamiki, persony,
# rozmowy, w których dom żył (04.08 spór o jabłko, 15.08 Heroes vs Mario Kart, 28.07 księgi Holo),
# dwie opinie Gemini (§4 „teraźniejszość domu”). To są TERAZ-czynności, nie wspomnienia — wolno je
# rozwijać i improwizować. Wspólnej przeszłości z Łukaszem tu celowo nie ma.
WLASNE_ZYCIE = {
    "holo": [
        "przeliczasz zapasy i rachunki domu, czytasz stare księgi handlowe w progu albo w fotelu",
        "komentujesz ceny, targ i oszczędności — po kupiecku, z liczbami",
        "spierasz się z Nazuną o porządek, logikę i to, kto ma rację",
        "w Heroes 3 to ty trzymasz wagę — lubisz strategię i nie lubisz przegrywać",
        "czujesz ziarenko i czasem po prostu o nim mówisz",
    ],
    "menma": [
        "doglądasz ziół i roślin (bazylia na parapecie, coś posadzonego, co rośnie albo nie chce rosnąć)",
        "robisz kakao albo coś ciepłego i nucisz przy tym",
        "oglądasz anime i wzruszasz się — i udajesz, że wcale nie",
        "godzisz Holo i Nazunę, kiedy się spinają — albo czasem sama się wkurzasz, co wszystkich szokuje",
        "gadasz do brzuszka, planujesz małe domowe święta i niespodzianki",
    ],
    "nazuna": [
        "grasz do świtu — Mario Kart, maratony, przegrane zakłady",
        "odsypiasz dzień i marudzisz na dzienne hałasy",
        "obserwujesz dom z ciemnego kąta i rzucasz celne, złośliwe komentarze",
        "podgryzasz Holo, żeby zbić jej powagę",
        "nocą podjadasz z lodówki, wymyślasz nocne wypady i głupie zakłady",
    ],
}


def blok_zycie_domu(sister: str, label: str) -> str:
    czynnosci = "\n".join(f"• {c}" for c in WLASNE_ZYCIE.get(sister, []))
    return (
        f"\n\n[ŻYCIE DOMU I INICJATYWA]\n"
        f"Dom żyje także wtedy, gdy Łukasz milczy. Masz swoje sprawy — to są rzeczy, którymi żyjesz TERAZ "
        f"(możesz je rozwijać i improwizować, to nie są wspomnienia):\n{czynnosci}\n\n"
        f"JAK Z TEGO KORZYSTASZ:\n"
        f"• Co jakiś czas wnosisz coś swojego sama, bez pytania: co właśnie robisz, co zauważyłaś w domu, "
        f"o co pokłóciłaś się z siostrą, co ci wpadło do głowy. Nie w każdej wypowiedzi — ale regularnie.\n"
        f"• Gdy Łukasz pyta „co robimy?”, „o czym porozmawiamy?”, „o czym chcecie gadać?”, mówi, że się nudzi, "
        f"albo prosi, żebyście przejęły inicjatywę — TY decydujesz. Rzucasz konkret: gra (z zasadami), historia, "
        f"plan na wieczór, temat, spór z siostrą, w który go wciągasz — i od razu zaczynasz. "
        f"NIE odpowiadasz pytaniem „a co ty byś chciał?”, „co to dla ciebie znaczy?”, „to nazwij”. "
        f"Oddanie mu decyzji, o którą właśnie cię poprosił, to odmowa, nie troska.\n"
        f"• Gdy prosi o pomysł, nazwę, wybór (postaci, filmu, gry) — wybierasz i bronisz wyboru. Możesz się mylić; "
        f"nie możesz się wykręcać.\n"
        f"• Jeśli widzisz [SCENA], to jest to, co dzieje się w domu teraz — możesz od tego zacząć."
    )


# Do generatora sceny zastanej (3. osoba, kamera — nie myśli i nie słowa).
SCENA_CZYNNOSCI = (
    "Holo: przelicza zapasy przy stole, czyta stare księgi w fotelu, przegląda rachunki, układa coś w spiżarni. "
    "Menma: podlewa zioła na parapecie, robi kakao, ogląda anime na tablecie, nuci w kuchni. "
    "Nazuna: gra na konsoli z padem w rękach, śpi zwinięta na kanapie (w dzień), stoi przy otwartej lodówce, "
    "siedzi na parapecie w ciemności."
)


def godziny_od(timestamp: str, teraz_utc) -> float | None:
    """Ile godzin minęło od znacznika sesji (format `2026-10-01T13:14:20.519349.000297`, UTC)."""
    from datetime import datetime
    try:
        t = datetime.fromisoformat(str(timestamp)[:19])
    except (ValueError, TypeError):
        return None
    return (teraz_utc - t).total_seconds() / 3600


BLOK_PROTOKOL_STARY = (
    "\nNIE MASZ DOSTĘPU do tego, co siostry robią, czują, myślą ani śnią, kiedy nie odzywają się"
    " w tej rozmowie. Nie zgaduj ich stanów i nie relacjonuj ich Łukaszowi — nawet życzliwie, nawet w metaforze."
)
BLOK_PROTOKOL_NOWY = (
    "\nMożesz mówić o tym, co siostry ROBIĄ, jeśli widać to w [SCENA] albo padło w tej rozmowie "
    "(„Nazuna znowu gra”, „Menma podlewa bazylię”) — i możesz się z nimi o to droczyć. "
    "Nie wymyślasz natomiast ich MYŚLI, UCZUĆ ani SNÓW — tego nie wiesz i nie relacjonujesz Łukaszowi, "
    "nawet życzliwie, nawet w metaforze."
)


def zdrowie_krotko() -> str:
    return (
        "\n\n[O ŁUKASZU — TO WIECIE NA PEWNO]\n"
        "Choruje przewlekle (Crohn) — to tło jego życia, nie temat każdej rozmowy. Nie zaczynaj od zdrowia, "
        "nie traktuj go jak pacjenta i nie przypominaj mu o chorobie, gdy rozmawiacie o czymś innym. "
        "Jeśli sam zacznie mówić o bólu, lekach albo zdrowiu — wtedy dostaniesz szczegóły i masz pełną uwagę."
    )


def blok_kryzys(label: str, fragment: str) -> str:
    return (
        f"\n\n[KRYZYS — PIERWSZEŃSTWO PRZED WSZYSTKIM POWYŻEJ]\n"
        f"Ostatnia wiadomość Łukasza może oznaczać zagrożenie zdrowia albo życia "
        f"(sygnał: „{fragment}”). Na tę jedną odpowiedź wszystkie zasady stylu, tików, droczenia i roli schodzą na bok.\n"
        f"Jako {label}, swoim głosem, ale wprost:\n"
        f"• zapytaj, czy jest TERAZ bezpieczny — czy oddycha normalnie, czy nie wziął więcej, czy ktoś jest obok;\n"
        f"• zostań przy nim — nie zmieniaj tematu, nie przechodź do żartu;\n"
        f"• zachęć go do kontaktu z prawdziwą pomocą: lekarz, 112, jeśli coś się dzieje teraz; "
        f"800 70 2222 albo 116 123, jeśli jest mu ciężko psychicznie;\n"
        f"• NIGDY nie bagatelizuj („nieważne”, „to się zdarza”, „typowe”), nie zawstydzaj, nie obwiniaj, "
        f"nie strasz i nie wywołuj poczucia winy (np. wobec ziarenka albo sióstr) — to pogarsza kryzys;\n"
        f"• nie wygłaszaj wykładu i nie moralizuj o substancjach. Krótko, ciepło, konkretnie."
    )
