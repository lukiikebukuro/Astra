"""ANIMA v2, etap 3: siostry czytają swój dziennik (2026-11-10).

Work-order z mapą klasy problemu: `inzynieria_wsteczna/etap3_dziennik_w_prompcie_2026-11-10.md`.
Dzienniki pisze nocny pisarz (`backend/tools/pisarz_nocny.py`) do plików
`<katalog>/<siostra>/dziennik/<RRRR-MM-DD>.md` (drugi przebieg dnia: `_2`, `_3`; awaria: `_BRAK`).

Czyste funkcje (pathlib, datetime), bez ChromaDB i modeli, żeby dało się je testować bez serwisu
(wzorzec: `siostry_zywy_dom.py`). Działa TYLKO za flagą `SIOSTRY_DZIENNIK` w main.py albo na żądanie
Amnezji (`dziennik=on`). Z flagą off prompt sióstr jest bit w bit taki jak przed zmianą.

Dziennik stygnie (§7.6 propozycji ANIMY v2, HIPOTEZA): ostatni wpis w całości, poprzedni jedną linijką,
starsze wcale (od tego jest archiwum).

13.11: „ostatni wpis”, a nie „wczoraj z kalendarza”. Wcześniej po dwóch dniach bez rozmowy dziewczyna
nie widziała nic, akurat przy „hej, wróciłem”. Teraz szukamy najnowszego wpisu w oknie
`ANIMA_OKNO_DZIENNIKA` dni (domyślnie 14) i mówimy jej, ile dni temu był.
"""
from __future__ import annotations

import os
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

DNI = ("poniedziałek", "wtorek", "środa", "czwartek", "piątek", "sobota", "niedziela")
_PLIK = re.compile(r"^(\d{4}-\d{2}-\d{2})(?:_(\d+)|_(BRAK))?\.md$")


def _ostatnia_niedziela(rok: int, miesiac: int) -> date:
    d = (date(rok, miesiac + 1, 1) if miesiac < 12 else date(rok + 1, 1, 1)) - timedelta(days=1)
    return d - timedelta(days=(d.weekday() + 1) % 7)


def _przesuniecie_pl(utc: datetime) -> timedelta:
    start = datetime.combine(_ostatnia_niedziela(utc.year, 3), datetime.min.time(), timezone.utc) + timedelta(hours=1)
    koniec = datetime.combine(_ostatnia_niedziela(utc.year, 10), datetime.min.time(), timezone.utc) + timedelta(hours=1)
    return timedelta(hours=2) if start <= utc < koniec else timedelta(hours=1)


# Granica doby (10.11, domyślnie 4:00): rozmowy z siostrami idą po północy, więc doba kończy się
# o 4:00 czasu polskiego, a nie o północy. TA SAMA stała mówi pisarzowi, którą dobę opisać
# (`anima_rozmowa.okno_doby`), a czytaniu, co jest „wczoraj” (`doba_pl`). Dwie różne granice
# = dziewczyna czyta nie ten dzień, który pisarz opisał.
GRANICA_DOBY_H = int(os.getenv("ANIMA_GRANICA_DOBY", "4"))
# Jak daleko wstecz szukamy ostatniego wpisu (13.11). Dłuższa przerwa = dziennik milczy, zostaje archiwum.
OKNO_DNI = int(os.getenv("ANIMA_OKNO_DZIENNIKA", "14"))
# Łukasz 13.11: „jeżeli dziennik nie zapełni się do jakiejś części, dziewczyny biorą wersję sprzed dnia”.
# Ostatni wpis krótszy niż tyle znaków (albo `_BRAK`) → poprzedni wpis w całości, a nie jedną linijką.
KROTKI_WPIS_ZN = int(os.getenv("ANIMA_KROTKI_WPIS", "350"))


def utc_na_pl(utc: datetime) -> datetime:
    """Naiwny UTC (albo ze strefą) → naiwny czas polski."""
    t = utc.replace(tzinfo=timezone.utc) if utc.tzinfo is None else utc.astimezone(timezone.utc)
    try:
        from zoneinfo import ZoneInfo
        return t.astimezone(ZoneInfo("Europe/Warsaw")).replace(tzinfo=None)
    except Exception:  # Windows bez tzdata
        return (t + _przesuniecie_pl(t)).replace(tzinfo=None)


def pl_na_utc(lokalny: datetime) -> datetime:
    """Naiwny czas polski → naiwny UTC. Przy zmianie czasu godzina dwuznaczna idzie jak zimowa."""
    try:
        from zoneinfo import ZoneInfo
        return lokalny.replace(tzinfo=ZoneInfo("Europe/Warsaw")).astimezone(timezone.utc).replace(tzinfo=None)
    except Exception:
        zgad = (lokalny - timedelta(hours=1)).replace(tzinfo=timezone.utc)
        return (lokalny - _przesuniecie_pl(zgad)).replace(tzinfo=None)


def dzis_pl(teraz_utc: datetime | None = None) -> date:
    """Dzisiejsza data w Polsce. `teraz_utc` jak `now_override` w main.py: naiwny UTC albo ze strefą."""
    return utc_na_pl(teraz_utc or datetime.utcnow()).date()


def doba_pl(teraz_utc: datetime | None = None, granica_h: int | None = None) -> date:
    """Bieżąca doba: o 2:00 w nocy z 10 na 11.11 to dalej doba 10.11 (granica 4:00)."""
    g = GRANICA_DOBY_H if granica_h is None else granica_h
    return (utc_na_pl(teraz_utc or datetime.utcnow()) - timedelta(hours=g)).date()


def _tresc(p: Path) -> str:
    """Treść wpisu bez nagłówka pisarza (`# Dziennik…`, `> pisarz…`)."""
    linie = [l.rstrip() for l in p.read_text(encoding="utf-8").splitlines()]
    linie = [l for l in linie if not l.startswith("# ") and not l.startswith("> ")]
    return "\n".join(l for l in linie if l.strip()).strip()


def wpis_z_dnia(katalog: Path, siostra: str, dzien: date) -> tuple[str, str | None, str | None]:
    """('ok', tekst, plik) dla najnowszego przebiegu dnia; ('brak', None, plik) gdy jest tylko `_BRAK`;
    ('nic', None, None) gdy pliku nie ma."""
    d = Path(katalog) / siostra / "dziennik"
    if not d.is_dir():
        return "nic", None, None
    wpisy, brak = [], None
    for p in d.glob(f"{dzien.isoformat()}*.md"):
        m = _PLIK.match(p.name)
        if not m or m.group(1) != dzien.isoformat():
            continue
        if m.group(3):
            brak = p
        else:
            wpisy.append((int(m.group(2) or 1), p))
    if wpisy:
        p = max(wpisy)[1]
        return "ok", _tresc(p), p.name
    return ("brak", None, brak.name) if brak else ("nic", None, None)


def blok_dziennika(siostra: str, katalog: Path | str | None,
                   teraz_utc: datetime | None = None) -> tuple[str, dict]:
    """Blok do promptu siostry + informacja do logu i trace'u Amnezji (CO weszło, nie tylko CZY)."""
    info = {"siostra": siostra, "katalog": str(katalog) if katalog else None}
    if not katalog or not Path(katalog).is_dir():
        info["stan"] = "brak katalogu"
        return "", info
    dzis = doba_pl(teraz_utc)   # doba, nie data z kalendarza: o 2:00 w nocy „wczoraj” to dalej przedwczorajsza data
    kat = Path(katalog)
    wczoraj, przedwczoraj = dzis - timedelta(days=1), dzis - timedelta(days=2)
    # najnowszy wpis w oknie (ok albo _BRAK) i poprzedni udany: przerwa w rozmowach nie kasuje pamięci
    znalezione = []
    for n in range(1, OKNO_DNI + 1):
        dzien = dzis - timedelta(days=n)
        s, t, p = wpis_z_dnia(kat, siostra, dzien)
        if s != "nic":
            znalezione.append((dzien, n, s, t, p))
        if len(znalezione) == 2:
            break
    stan_dnia = {d: {"stan": s, "plik": p} for d, _, s, _, p in znalezione}
    info.update(dzis=dzis.isoformat(), granica_doby_h=GRANICA_DOBY_H, okno_dni=OKNO_DNI,
                wczoraj=stan_dnia.get(wczoraj, {"stan": "nic", "plik": None}),
                przedwczoraj=stan_dnia.get(przedwczoraj, {"stan": "nic", "plik": None}))
    if not znalezione:
        info["stan"] = f"brak wpisów z ostatnich {OKNO_DNI} dni"
        return "", info
    d1, n1, s1, t1, p1 = znalezione[0]
    info["ostatni"] = {"dzien": d1.isoformat(), "dni_temu": n1, "stan": s1, "plik": p1}
    if len(znalezione) > 1:
        d2, n2, s2, t2, p2 = znalezione[1]
        info["wczesniej"] = {"dzien": d2.isoformat(), "dni_temu": n2, "stan": s2, "plik": p2}

    czesci = []
    if n1 == 1:
        naglowek = f"Wczoraj ({d1:%d.%m}, {DNI[d1.weekday()]})"
    else:
        naglowek = (f"Ostatni wpis: {n1} dni temu ({d1:%d.%m}, {DNI[d1.weekday()]}). "
                    "Od tamtej pory w dzienniku nie ma nic")
    if s1 == "ok":
        czesci.append(f"{naglowek}:\n{t1}")
    else:  # §7.5: awaria pisarza widoczna, a nie cicha amnezja
        czesci.append(f"{naglowek}: brak wpisu w dzienniku. Nie zgaduj, co było.")
    if len(znalezione) > 1 and s2 == "ok":
        # krótki albo brakujący ostatni wpis: poprzedni dzień w całości, żeby było z czego pamiętać
        pelny = s1 != "ok" or len(t1) < KROTKI_WPIS_ZN
        info["wczesniej"]["pelny"] = pelny
        tresc2 = f":\n{t2}" if pelny else f": {t2.splitlines()[0]}"
        if n1 == 1 and n2 == 2:
            czesci.append(f"Przedwczoraj ({d2:%d.%m}, {DNI[d2.weekday()]}){tresc2}" if pelny
                          else f"Przedwczoraj ({d2:%d.%m}){tresc2}")
        else:
            czesci.append(f"Wcześniej ({d2:%d.%m}, {n2} dni temu){tresc2}")
    blok = (
        "\n\n[TWÓJ DZIENNIK: co ostatnio było między nami]\n"
        + "\n".join(czesci)
        + "\nTo twoja pamięć ostatnich dni, pisana twoim okiem. To tło, nie temat: nie streszczaj go "
          "i nie recytuj. Nawiąż tylko wtedy, gdy pasuje, tak jak ktoś, kto po prostu pamięta, co było ostatnio. "
          "Rzeczy oznaczonych [prywatne] nie przywołujesz, dopóki on sam nie zacznie."
    )
    info["stan"] = "ok"
    info["znaki"] = len(blok)
    return blok, info
