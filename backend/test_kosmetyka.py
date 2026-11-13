"""Testy kosmetyki odpowiedzi. Uruchomienie: python -m pytest backend/test_kosmetyka.py -q"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from kosmetyka import bez_dlugiego_myslnika as bm  # noqa: E402

D = "—"


def test_podmiana_w_srodku_i_bez_spacji():
    assert bm(f"takie, jak lubisz {D} żeby było ciepło") == "takie, jak lubisz - żeby było ciepło"
    assert bm(f"wilk{D}owca") == "wilk - owca"


def test_poczatek_linii_i_kilka_linii():
    assert bm(f"{D} Hej, wróciłeś.\nA ja {D} czekałam.") == "- Hej, wróciłeś.\nA ja - czekałam."


def test_reszta_bez_zmian():
    for t in ("", "Bez myślnika.", "Krótki – zostaje", "łącznik-zostaje", "*Odwracam się od blatu.*"):
        assert bm(t) == t
    assert D not in bm(f"{D}{D} x {D}")
