"""ANIMA v2: rozmowa jednej doby z pokoju sióstr w formacie wejścia nocnego pisarza (2026-11-10).

Most między historią sesji pokoju (kolekcja `siostry_shared_session_v1` albo archiwum
`backend/sesje_archiwum/siostry_<data UTC>.json`) a `backend/tools/pisarz_nocny.py`.
TYLKO ODCZYT: nic nie zapisuje do bazy. Czyste funkcje, testy: `backend/test_anima_rozmowa.py`.

Doba = od GRANICA_DOBY_H (domyślnie 4:00) czasu polskiego danego dnia do tej samej godziny
następnego dnia. Ta sama granica co w `anima_dziennik.doba_pl`, więc „wczoraj” przy czytaniu
to dokładnie ta doba, którą pisarz opisał.

Wyjście: „[HH:MM:SS] KTO: treść” w CZASIE POLSKIM (pisarz dostaje --strefa-zrodla PL),
pod spodem wcięte „(mysl: …)” i „(hint: …)”, jak w `inzynieria_wsteczna/pisarz_proby/dzien_2026-09-26.txt`.

Ręcznie, np. zaległa doba z archiwum na VPS (nic nie woła, tylko pisze plik tekstowy):
  python backend/anima_rozmowa.py --doba 2026-11-09 --z-archiwum backend/sesje_archiwum --wyjscie /tmp/doba.txt
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path

try:
    import anima_dziennik as ad
except ImportError:  # python -I backend/anima_rozmowa.py: katalogu skryptu nie ma w sys.path
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import anima_dziennik as ad

KOLEKCJA = "siostry_shared_session_v1"
PODPIS = re.compile(r"^\[(holo|menma|nazuna|astra)\]\s*", re.I)
_WYGLADA_JAK_LINIA = re.compile(r"^\[\d\d:\d\d:\d\d\] ")


@dataclass
class Wpis:
    kiedy_utc: datetime   # naiwny UTC, jak `timestamp` w sesji
    kto: str              # LUKASZ, HOLO, MENMA, NAZUNA, ASTRA (gość), MODEL (bez podpisu)
    tresc: str
    mysl: str = ""
    hint: str = ""
    klucz: str = ""       # surowy timestamp z sufiksem seq: kolejność w tej samej sekundzie


def _czas(ts: str) -> datetime | None:
    try:
        return datetime.fromisoformat(ts[:19])
    except (ValueError, TypeError):
        return None


def wpisy(dokumenty: list, metadane: list) -> list[Wpis]:
    """Dokumenty i metadane z `collection.get()` (albo z archiwum) → wpisy po kolei."""
    out = []
    for d, m in zip(dokumenty or [], metadane or []):
        m = m or {}
        if m.get("source", "session_message") != "session_message" or not d:
            continue
        t = _czas(m.get("timestamp", ""))
        if t is None:
            continue
        if m.get("role") == "user":
            kto, tresc = "LUKASZ", d
        else:
            mm = PODPIS.match(d)
            kto, tresc = (mm.group(1).upper(), d[mm.end():]) if mm else ("MODEL", d)
        out.append(Wpis(t, kto, tresc.strip(), (m.get("thought") or "").strip(),
                        (m.get("hint") or "").strip(), m.get("timestamp", "")))
    out.sort(key=lambda w: w.klucz)
    return out


def okno_doby(doba: date, granica_h: int | None = None) -> tuple[datetime, datetime]:
    """(początek, koniec) doby w naiwnym UTC; koniec wyłącznie."""
    g = ad.GRANICA_DOBY_H if granica_h is None else granica_h
    start_pl = datetime.combine(doba, time(g))
    return ad.pl_na_utc(start_pl), ad.pl_na_utc(start_pl + timedelta(days=1))


def z_doby(lista: list[Wpis], doba: date, granica_h: int | None = None) -> list[Wpis]:
    start, koniec = okno_doby(doba, granica_h)
    return [w for w in lista if start <= w.kiedy_utc < koniec]


def podsumowanie(lista: list[Wpis]) -> dict:
    return dict(Counter(w.kto for w in lista))


def _jedna_linia(s: str) -> str:
    return " ".join(s.split())


def tekst_dla_pisarza(lista: list[Wpis]) -> str:
    bloki = []
    for w in lista:
        linie = (w.tresc or "").splitlines() or [""]
        # dalszy ciąg treści, który wygląda jak nowa wiadomość, dostaje spację z przodu
        # (parser pisarza zaczyna wiadomość tylko od „[” w pierwszej kolumnie, a spację potem zdejmuje)
        dalej = [(" " + l if _WYGLADA_JAK_LINIA.match(l) else l) for l in (x.strip() for x in linie[1:]) if l]
        blok = [f"[{ad.utc_na_pl(w.kiedy_utc):%H:%M:%S}] {w.kto}: {linie[0].strip()}", *dalej]
        if w.mysl:
            blok.append(f"      (mysl: {_jedna_linia(w.mysl)})")
        if w.hint:
            blok.append(f"      (hint: {_jedna_linia(w.hint)})")
        bloki.append("\n".join(blok))
    return "\n\n".join(bloki) + ("\n" if bloki else "")


def wpisy_z_archiwum(katalog: Path, doba: date) -> tuple[list[Wpis], list[str]]:
    """Archiwum dzienne serwisu jest po dacie UTC, a doba je przecina: czytamy oba pliki.
    Zwraca też listę brakujących plików (brak = doba może być niepełna, trzeba to powiedzieć)."""
    start, koniec = okno_doby(doba)
    dok, met, brak = [], [], []
    d = start.date()
    while d <= (koniec - timedelta(seconds=1)).date():
        p = Path(katalog) / f"siostry_{d.isoformat()}.json"
        if p.exists():
            for x in json.loads(p.read_text(encoding="utf-8")):
                dok.append(x.get("content", ""))
                met.append({"timestamp": x.get("timestamp", ""), "role": x.get("role", ""),
                            "thought": x.get("thought", ""), "hint": x.get("hint", "")})
        else:
            brak.append(p.name)
        d += timedelta(days=1)
    return z_doby(wpisy(dok, met), doba), brak


def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--doba", required=True, help="RRRR-MM-DD: doba od 4:00 tego dnia do 4:00 następnego")
    ap.add_argument("--z-archiwum", required=True, type=Path, help="katalog backend/sesje_archiwum")
    ap.add_argument("--wyjscie", required=True, type=Path)
    a = ap.parse_args(argv)

    doba = date.fromisoformat(a.doba)
    start, koniec = okno_doby(doba)
    lista, brak = wpisy_z_archiwum(a.z_archiwum, doba)
    print(f"doba {doba}: UTC {start:%d.%m %H:%M} .. {koniec:%d.%m %H:%M}; wiadomości {len(lista)} {podsumowanie(lista)}")
    for b in brak:
        print(f"UWAGA: brak pliku {b}, doba może być niepełna")
    if not podsumowanie(lista).get("LUKASZ"):
        print("NIC: tej doby nie było rozmowy, pisarz nie ma czego opisać")
        return 4
    if a.wyjscie.exists():
        print(f"STOP: {a.wyjscie} już jest (niczego nie nadpisuję)")
        return 3
    a.wyjscie.parent.mkdir(parents=True, exist_ok=True)
    a.wyjscie.write_text(tekst_dla_pisarza(lista), encoding="utf-8")
    print(f"zapisano: {a.wyjscie}  (pisarz: --data {doba} --strefa-zrodla PL)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
