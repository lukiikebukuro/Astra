"""
Dom v2 (2026-11-22): scena v2, karteczka, przeczucie Menmy v0, „wiedzą, gdzie byłeś”, Astra na stałe.

Work-order z mapą klasy problemu (krok 5b): `wazne/siostry/work-order_dom_v2_2026-11-22.md`.
CZYSTE funkcje (pathlib, json, re), bez ChromaDB i modeli, żeby dało się je testować bez serwisu
(wzorzec: `siostry_zywy_dom.py`, `anima_dziennik.py`). Działa TYLKO za flagą `SIOSTRY_DOM_V2` w main.py
albo na żądanie `/api/debug/dom_v2`. Z flagą off nic stąd nie trafia do promptu ani do odpowiedzi.

Pliki stanu leżą w `<ANIMA_PLIKI_DIR>/dom/` (poza gitem, obok dzienników): `sceny.jsonl`,
`przeczucia.jsonl`, `gosc.json`. Bez katalogu wszystko działa, tylko bez pamięci między turami.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timedelta
from pathlib import Path

import anima_dziennik
import siostry_zywy_dom as zywy_dom

# ── FILTR: co z dziennika wolno pokazać w scenie, karteczce i przeczuciu ───────────────
# Jeden filtr dla trzech nowych kanałów (mapa klasy pkt 2). Lepiej pokazać mniej niż wnieść
# do sceny coś, co Łukasz chciał zostawić dla siebie (REJESTR §10, 16.11: zdrowie w czułej scenie).
_ZAKAZANE = re.compile(
    r"(konop|weed|jaran|zjaran|\bavb\b|bucha|buszk|\bwap|joint|jointa|blant|skret|zielsk|hasz|\bthc\b|\bcbd\b|"
    r"alkohol|piw[aoeu]?\b|wodk|narkot|mefedr|"
    r"pieniad|kas[aey]\b|dlug|kredyt|zarob|wyplat|bied|"
    r"\bojc|\bojciec|\btat[aeyu]?\b|\bmam[aeyu]\b|\bmatk|rodzic|klotn|awantur|"
    r"psychiatr|terapi|wstyd|plak|placz|smut|samotn)"
)
_PUNKT = re.compile(r"^\s*([-*•]|\d+[.)])\s*")


def bezpieczne_linijki(tekst: str | None) -> list[str]:
    """Linijki wpisu dziennika, które wolno pokazać w scenie i karteczce. Bez znaczników i punktorów."""
    wynik = []
    for linia in (tekst or "").splitlines():
        if not linia.strip() or "[prywatne]" in linia or "[prośba]" in linia:
            continue
        czysta = _PUNKT.sub("", linia).strip()
        if not czysta:
            continue
        if zywy_dom.temat_zdrowia(czysta) or _ZAKAZANE.search(zywy_dom.fold(czysta)):
            continue
        wynik.append(czysta)
    return wynik


def ostatni_wpis(katalog, siostra: str, teraz_utc: datetime | None = None, okno_dni: int = 3) -> tuple[str | None, str | None]:
    """(data, treść) najnowszego udanego wpisu z ostatnich `okno_dni` dób albo (None, None)."""
    if not katalog or not Path(katalog).is_dir():
        return None, None
    dzis = anima_dziennik.doba_pl(teraz_utc)
    for n in range(1, okno_dni + 1):
        dzien = dzis - timedelta(days=n)
        stan, tresc, _plik = anima_dziennik.wpis_z_dnia(Path(katalog), siostra, dzien)
        if stan == "ok" and tresc:
            return dzien.isoformat(), tresc
    return None, None


def slady_z_dziennikow(katalog, siostry: list[str], teraz_utc: datetime | None = None,
                       max_zn: int = 160) -> dict[str, str]:
    """Po jednej bezpiecznej linijce (pierwszej) z ostatniego wpisu każdej siostry."""
    slady = {}
    for s in siostry:
        _d, tresc = ostatni_wpis(katalog, s, teraz_utc)
        linie = bezpieczne_linijki(tresc)
        if linie:
            slady[s] = linie[0][:max_zn]
    return slady


# ── PAMIĘĆ SCEN (żeby kamera nie kręciła w kółko tego samego ujęcia) ───────────────────
def _plik_dom(katalog, nazwa: str) -> Path | None:
    if not katalog:
        return None
    d = Path(katalog) / "dom"
    d.mkdir(parents=True, exist_ok=True)
    return d / nazwa


def ostatnie_sceny(katalog, n: int = 4) -> list[str]:
    p = _plik_dom(katalog, "sceny.jsonl") if katalog and Path(katalog).is_dir() else None
    if not p or not p.exists():
        return []
    sceny = []
    for linia in p.read_text(encoding="utf-8").splitlines():
        try:
            sceny.append(json.loads(linia)["scena"])
        except (ValueError, KeyError, TypeError):
            continue
    return sceny[-n:]


def zapamietaj_scene(katalog, scena: str, teraz_utc: datetime | None = None, trzymaj: int = 20) -> None:
    if not scena or not katalog or not Path(katalog).is_dir():
        return
    p = _plik_dom(katalog, "sceny.jsonl")
    stare = p.read_text(encoding="utf-8").splitlines() if p.exists() else []
    stare.append(json.dumps({"ts": (teraz_utc or datetime.utcnow()).isoformat(timespec="seconds"),
                             "scena": scena}, ensure_ascii=False))
    p.write_text("\n".join(stare[-trzymaj:]) + "\n", encoding="utf-8")


# ── SCENA v2 ────────────────────────────────────────────────────────────────────
# Bez przykładowych czynności: do 21.11 kamera kopiowała przykłady z promptu i listę SCENA_CZYNNOSCI
# („Holo liczy przy stole”, „Nazuna z padem”), stąd ~40 prawie identycznych scen (work-order pkt 1).
def prompt_sceny_v2(etykiety: list[str], pora: str, dzien_tygodnia: str, przerwa_h: float,
                    slady: dict[str, str], ostatnie: list[str]) -> str:
    p = (
        "Jesteś kamerą w domu trzech sióstr. NIE jesteś reżyserem.\n"
        f"Domowniczki: {', '.join(etykiety)}. Pora: {pora}, {dzien_tygodnia}.\n"
        f"Łukasz wraca po {int(przerwa_h)} godz. nieobecności. Pokaż, co dom robił bez niego.\n"
    )
    if slady:
        p += ("Ślady ostatnich dni z dzienników sióstr. Możesz pokazać JEDEN z nich jako widoczny przedmiot, "
              "miejsce albo czynność (nie musisz, nie cytuj, nie tłumacz):\n")
        p += "".join(f"- {k}: {v}\n" for k, v in slady.items())
    if ostatnie:
        p += "Ostatnie sceny. NIE powtarzaj ich miejsca, pierwszego obrazu ani czynności:\n"
        p += "".join(f"{i}. {s}\n" for i, s in enumerate(ostatnie, 1))
    p += (
        "Za każdym razem wybierz inne miejsce w domu i inny pierwszy obraz. NIE zaczynaj od światła, "
        "cieni ani od tego, że Łukasz otwiera drzwi. Nie musisz pokazywać wszystkich; ktoś może być poza kadrem, "
        "ktoś może coś robić razem z inną.\n"
        "Napisz 2-3 zdania SCENY ZASTANEJ: co Łukasz widzi albo słyszy, wchodząc. Jeden zwykły akapit prozą: "
        "bez nagłówków, bez list, bez słowa „scena”, bez opisu, że ktoś go zauważa.\n"
        "MOŻESZ: miejsce, pora, kto w kadrze, widoczne czynności, przedmioty, dźwięki.\n"
        "NIE MOŻESZ: myśli ani emocji sióstr, słów w ich ustach, fabuły, mówienia za Łukasza, zdrowia, leków.\n"
        "Odpowiedz TYLKO tekstem sceny, bez JSON, bez cudzysłowów."
    )
    return p


_NAGLOWEK_SCENY = re.compile(r"^\s*(\**\s*scena\b.*|w kadrze\s*:.*|[^.\n]{1,30}\.\s*(poranek|popołudnie|popoludnie|wieczór|wieczor|noc)\.?\**)\s*$", re.I)


def czysc_scene(tekst: str | None, max_zdan: int = 3) -> str:
    """22.11 podgląd na VPS: bez przykładów model pisał cały scenariusz (SCENA 1, „Kuchnia. Popołudnie.”,
    „W kadrze:”). Zostaje pierwszy akapit prozy, najwyżej `max_zdan` zdań."""
    linie = [l.strip().strip("*").strip() for l in (tekst or "").splitlines()]
    proza = [l for l in linie if l and not _NAGLOWEK_SCENY.match(l)]
    if not proza:
        return ""
    zdania = re.split(r"(?<=[.!?…])\s+", proza[0])
    return " ".join(zdania[:max_zdan]).strip()


# ── KARTECZKA I PRZECZUCIE MENMY ────────────────────────────────────────────────
# Głos w jednym zdaniu, bez tików (limit tików z 06.10: żadnych „Hmf”, „ziomek”, „Mistrzu” na siłę).
GLOS = {
    "holo": "Wilczyca i głowa domu: spokojna, kupiecka, konkretna, czuła pod twardą skorupą",
    "menma": "ciepła, radosna i troskliwa; czuje jego nastrój jako pierwsza",
    "nazuna": "nocna strażniczka: wyluzowana, przekorna, z czułością schowaną za żartem",
}
GDZIE_KARTECZKA = ("na stole", "na drzwiach lodówki", "na jego poduszce", "przy czajniku", "na klawiaturze")

# Przeczucie: tylko rzeczy NADCHODZĄCE (próg z danych, nie z nastroju) i nigdy wyniki, na które
# Łukasz nie ma wpływu. Fałszywe „dostaniesz tę pracę” mogłoby naprawdę zaboleć (work-order pkt 3).
_PRZYSZLOSC = re.compile(
    r"\b(jutr\w*|pojutrz\w*|poniedzial\w*|wtor\w*|srod[aeyz]\w*|czwart\w*|piat\w*|sobot\w*|niedziel\w*|"
    r"zamierz\w*|planuj\w*|plan\w*|bedzie\w*|beda|bedziemy|zrobimy|pojedzie\w*|wroci\w*|weekend\w*|"
    r"za tydzien|w przyszl\w*|nastepn\w*)\b"
)
_WYNIKI = re.compile(
    r"(prac[aeyiu]|rekrut|deepsense|rozmow\w* o prac|odpowiedz|odpis|aplikac|ofert|wynik|egzamin|"
    r"pilotaz|zatrudn|decyzj|zdal|oblal)"
)


def sygnal_przeczucia(linie: list[str]) -> str | None:
    """Pierwsza bezpieczna linijka o czymś nadchodzącym, bez wyników poza jego wpływem. None = Menma milczy."""
    for l in linie:
        f = zywy_dom.fold(l)
        if _PRZYSZLOSC.search(f) and not _WYNIKI.search(f):
            return l
    return None


def przeczucie_dzis_bylo(katalog, doba: str) -> bool:
    p = _plik_dom(katalog, "przeczucia.jsonl") if katalog and Path(katalog).is_dir() else None
    if not p or not p.exists():
        return False
    for linia in p.read_text(encoding="utf-8").splitlines():
        try:
            if json.loads(linia).get("doba") == doba:
                return True
        except ValueError:
            continue
    return False


def zapisz_przeczucie(katalog, doba: str, zrodlo: str, tekst: str, teraz_utc: datetime | None = None) -> None:
    """Każde przeczucie z datą i źródłem; `stan` do sprawdzenia przyszłym silnikiem (trafność, kalibracja)."""
    if not katalog or not Path(katalog).is_dir() or not tekst:
        return
    p = _plik_dom(katalog, "przeczucia.jsonl")
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"doba": doba, "ts": (teraz_utc or datetime.utcnow()).isoformat(timespec="seconds"),
                            "zrodlo": zrodlo, "tekst": tekst, "stan": "do_sprawdzenia"}, ensure_ascii=False) + "\n")


def prompt_karteczki(siostra: str, etykieta: str, przerwa_h: float, gdzie: str,
                     slad: str | None, przeczucie: str | None = None) -> str:
    glos = GLOS.get(siostra, "")
    if przeczucie:
        tresc = (
            f"Twój nen czasem podsuwa ci błysk tego, co nadchodzi. Zostawiasz mu karteczkę z przeczuciem na najbliższe dni, "
            f"opartym na tym, co wiesz z dziennika: „{przeczucie}”.\n"
            "Pisz jako PRZECZUCIE, nie pewność („coś mi mówi…”, „mam przeczucie, że…”). "
            "NIE przepowiadasz wyników, na które on nie ma wpływu (praca, pieniądze, odpowiedzi firm), "
            "zdrowia ani niczego złego.\n"
        )
    else:
        tresc = (f"Możesz nawiązać do tego, co ostatnio było: „{slad}”.\n" if slad else "")
    return (
        f"Jesteś {etykieta}. {glos}.\n"
        f"Łukasza nie było w domu {int(przerwa_h)} godz. Zostawiłaś mu karteczkę {gdzie}; znajdzie ją, gdy wejdzie.\n"
        + tresc +
        "Napisz TYLKO treść karteczki: 1-2 krótkie zdania, twoim głosem, do niego, na „ty”.\n"
        "NIE: zdrowie, leki, substancje, pieniądze, praca, rekrutacja, rodzice. Bez gwiazdek, didaskaliów i cudzysłowów."
    )


def czysc_karteczke(tekst: str | None, max_zn: int = 300) -> str:
    t = (tekst or "").strip().strip('"„”«»').strip()
    t = re.sub(r"\*[^*]{0,200}\*", "", t).strip()
    return t[:max_zn]


def blok_karteczki(autor_etykieta: str, gdzie: str, tekst: str, moja: bool, przeczucie: bool) -> str:
    if not tekst:
        return ""
    p = (f"\n\n[KARTECZKA]\nKiedy Łukasza nie było, {autor_etykieta} zostawiła mu karteczkę {gdzie}: „{tekst}”. "
         "Cały dom o niej wie.")
    if moja:
        p += (" To twoja karteczka: możesz do niej nawiązać, ale nie musisz i nie czytaj jej na głos."
              + (" To było twoje przeczucie; nie upieraj się przy nim i nie rób z niego pewności." if przeczucie else ""))
    else:
        p += " Nie streszczaj jej i nie mów w imieniu autorki."
    return p


# ── WIEDZĄ, GDZIE BYŁEŚ ───────────────────────────────────────────────────────────
def minuty_u_astry(astra_ts: str | None, pokoj_ts: str | None, teraz_utc: datetime, max_h: float = 6.0) -> int | None:
    """Ile minut temu Łukasz pisał do Astry solo, jeśli to nowsze niż ostatnia wiadomość w pokoju i ≤ max_h."""
    try:
        a = datetime.fromisoformat(str(astra_ts)[:19]) if astra_ts else None
        p = datetime.fromisoformat(str(pokoj_ts)[:19]) if pokoj_ts else None
    except (ValueError, TypeError):
        return None
    if not a or (p and a <= p):
        return None
    minuty = (teraz_utc - a).total_seconds() / 60
    return int(minuty) if 0 <= minuty <= max_h * 60 else None


def blok_gdzie_byl(minuty: int) -> str:
    kiedy = "przed chwilą" if minuty < 15 else (f"ok. {minuty} min temu" if minuty < 90 else f"ok. {round(minuty / 60)} godz. temu")
    return (
        f"\n\n[GDZIE BYŁ]\nŁukasz był {kiedy} u Astry w jej pokoju, sam na sam. Treści tej rozmowy nie znasz "
        "i nie zgadujesz. Możesz to lekko zauważyć po swojemu (z przekąsem albo ciepło), ale nie wypytuj "
        "i nie rób z tego sprawy."
    )


# ── ASTRA NA STAŁE ────────────────────────────────────────────────────────────────
GOSC_STALY_TURY = 10 ** 6   # „bez limitu”: licznik się nie zmniejsza, wizyta trwa do „odejdz”


def wczytaj_gosc(katalog) -> dict:
    p = _plik_dom(katalog, "gosc.json") if katalog and Path(katalog).is_dir() else None
    if not p or not p.exists():
        return {}
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except ValueError:
        return {}


def zapisz_gosc(katalog, conversation_id: str | None, staly: bool) -> None:
    if not katalog or not Path(katalog).is_dir():
        return
    # Nadpisujemy stan, nie kasujemy pliku (zasada projektu: nic nie kasujemy po cichu).
    p = _plik_dom(katalog, "gosc.json")
    p.write_text(json.dumps({"conversation_id": conversation_id, "staly": bool(staly and conversation_id)},
                            ensure_ascii=False), encoding="utf-8")
