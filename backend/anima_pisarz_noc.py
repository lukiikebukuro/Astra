"""ANIMA v2: nocne zadanie pisarza sióstr w samym serwisie (2026-11-10).

Uruchamia je scheduler w main.py o 4:30 (po archiwum z 4:00), TYLKO za flagą `SIOSTRY_PISARZ=on`
i z ustawionym `ANIMA_PLIKI_DIR`. Domyślnie off, więc bez flagi nic się nie zmienia.

Dlaczego w serwisie, a nie cronem: sesję pokoju czytamy w TYM SAMYM procesie co serwis
(tak samo robi `daily_archive.py`), więc żaden drugi proces nie otwiera ChromaDB (lekcja 25.07).
Do bazy nic nie piszemy, tylko pliki w ANIMA_PLIKI_DIR:
  wejscie/<doba>.txt                 rozmowa doby w formacie pisarza (do wglądu i powtórki)
  <siostra>/dziennik/<doba>.md       to, co napisze pisarz (albo widoczne <doba>_BRAK.md przy awarii)
  karty/propozycje_<doba>.md, karty_spis.json, surowe/

Prywatna rozmowa idzie do Gemini (ten sam dostawca, na którym chodzi rozmowa), dlatego flagę
włącza Łukasz. Work-order: `inzynieria_wsteczna/pisarz_nocny_etap2_2026-11-10.md`.
"""
from __future__ import annotations

import importlib.util
import sys
import traceback
from datetime import datetime, timedelta
from pathlib import Path

import anima_dziennik as ad
import anima_rozmowa as ar

SIOSTRY = ("holo", "menma", "nazuna")
PISARZ = Path(__file__).resolve().parent / "tools" / "pisarz_nocny.py"


def _pisarz_main():
    if "pisarz_nocny" in sys.modules:
        return sys.modules["pisarz_nocny"].main
    spec = importlib.util.spec_from_file_location("pisarz_nocny", PISARZ)
    mod = importlib.util.module_from_spec(spec)
    # najpierw do sys.modules: @dataclass przy `from __future__ import annotations` szuka tam modułu
    # (bez tego AttributeError przy imporcie; złapane testem 10.11, zanim poszło na serwer)
    sys.modules["pisarz_nocny"] = mod
    spec.loader.exec_module(mod)
    return mod.main


def _wolny(p: Path) -> Path:
    n = 2
    while p.exists():
        p = p.with_name(f"{p.stem.split('_')[0]}_{n}{p.suffix}")
        n += 1
    return p


def zadanie_nocne(session_collection, katalog, teraz_utc: datetime | None = None,
                  wykonaj: bool = True, pisarz_main=None, persona: str = "siostry") -> dict:
    """Opisuje dobę, która właśnie się skończyła. Zwraca info do logu (CO się stało, nie tylko CZY)."""
    doba = ad.doba_pl(teraz_utc) - timedelta(days=1)
    katalog = Path(katalog)
    info = {"doba": doba.isoformat(), "persona": persona}
    postacie = ("astra",) if persona == "astra" else SIOSTRY   # etap 6 (13.11): Astra solo, osobny katalog
    try:
        gotowe = [s for s in postacie
                  if any((katalog / s / "dziennik").glob(f"{doba.isoformat()}*.md"))]
        if gotowe:  # restart serwisu albo ręczny przebieg wcześniej: nie piszemy drugi raz
            info["stan"] = f"dziennik tej doby już jest ({', '.join(gotowe)})"
            return info
        r = session_collection.get(include=["documents", "metadatas"])
        info["wpisow_w_sesji"] = len(r.get("documents") or [])
        kto_modelu = ar.PROFILE_ROZMOWY[persona]["kto_modelu"]
        lista = ar.z_doby(ar.wpisy(r.get("documents"), r.get("metadatas"), kto_modelu), doba)
        info["kto"] = ar.podsumowanie(lista)
        if not info["kto"].get("LUKASZ"):
            info["stan"] = "bez rozmowy tej doby"
            return info
        plik = _wolny(katalog / "wejscie" / f"{doba.isoformat()}.txt")
        plik.parent.mkdir(parents=True, exist_ok=True)
        plik.write_text(ar.tekst_dla_pisarza(lista), encoding="utf-8")
        info["wejscie"] = str(plik)
        argv = ["--rozmowa", str(plik), "--data", doba.isoformat(), "--strefa-zrodla", "PL",
                "--wyjscie", str(katalog), "--persona", persona]
        if wykonaj:
            argv.append("--wykonaj")
        info["kod"] = (pisarz_main or _pisarz_main())(argv)
        info["stan"] = "ok" if info["kod"] == 0 else f"pisarz zwrócił {info['kod']}"
    except Exception as e:  # scheduler nie może od tego paść; ślad do journalctl
        info["stan"] = f"błąd: {type(e).__name__}: {e}"
        traceback.print_exc()
    return info
