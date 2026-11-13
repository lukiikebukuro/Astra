"""Testy etapu 3 na atrapach + kanarek na prawdziwych plikach z 26.09 (jeśli leżą lokalnie).
Uruchomienie: python -m pytest backend/test_anima_dziennik.py -q"""
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import anima_dziennik as ad  # noqa: E402

ASTRA = Path(__file__).resolve().parents[1]
PRAWDZIWE = ASTRA / "inzynieria_wsteczna" / "pisarz_proby" / "gemini_v2"


def _wpis(root, s, nazwa, tekst):
    p = root / s / "dziennik" / nazwa
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(f"# Dziennik: x\n\n> pisarz: atrapa\n\n{tekst}\n", encoding="utf-8")


def test_dzis_pl_granica_polnocy_i_strefy():
    # 26.09 22:30 UTC to już 27.09 w Polsce (czas letni, +2)
    assert ad.dzis_pl(datetime(2026, 9, 26, 22, 30)) == date(2026, 9, 27)
    assert ad.dzis_pl(datetime(2026, 9, 26, 21, 59)) == date(2026, 9, 26)
    # 10.11 23:30 UTC to 11.11 w Polsce (czas zimowy, +1)
    assert ad.dzis_pl(datetime(2026, 11, 10, 23, 30, tzinfo=timezone.utc)) == date(2026, 11, 11)


def test_wczoraj_w_calosci_przedwczoraj_jedna_linijka(tmp_path):
    _wpis(tmp_path, "holo", "2026-09-26.md", "Linia A26\nLinia B26\n" + "Dalszy opis dnia. " * 25)   # długi wpis
    _wpis(tmp_path, "holo", "2026-09-25.md", "Pierwsza 25\nDruga 25 (nie ma jej być)")
    _wpis(tmp_path, "holo", "2026-09-24.md", "Za stary wpis")
    blok, info = ad.blok_dziennika("holo", tmp_path, datetime(2026, 9, 27, 10, 0))
    assert "Wczoraj (26.09, sobota):\nLinia A26\nLinia B26" in blok
    assert "Przedwczoraj (25.09): Pierwsza 25" in blok and "Druga 25" not in blok
    assert "Za stary" not in blok and "pisarz: atrapa" not in blok and "# Dziennik" not in blok
    assert info["stan"] == "ok" and info["wczoraj"] == {"stan": "ok", "plik": "2026-09-26.md"}


def test_najnowszy_przebieg_dnia_wygrywa(tmp_path):
    _wpis(tmp_path, "menma", "2026-09-26.md", "stary")
    _wpis(tmp_path, "menma", "2026-09-26_2.md", "nowszy")
    _wpis(tmp_path, "menma", "2026-09-26_10.md", "najnowszy")
    blok, info = ad.blok_dziennika("menma", tmp_path, datetime(2026, 9, 27, 10, 0))
    assert "najnowszy" in blok and "stary" not in blok and info["wczoraj"]["plik"] == "2026-09-26_10.md"


def test_brak_wpisu_jest_widoczny(tmp_path):
    (tmp_path / "nazuna" / "dziennik").mkdir(parents=True)
    (tmp_path / "nazuna" / "dziennik" / "2026-09-26_BRAK.md").write_text("# Brak\n", encoding="utf-8")
    blok, info = ad.blok_dziennika("nazuna", tmp_path, datetime(2026, 9, 27, 10, 0))
    assert "brak wpisu w dzienniku. Nie zgaduj" in blok and info["wczoraj"]["stan"] == "brak"


def test_nic_nie_ma_to_pusty_blok(tmp_path):
    assert ad.blok_dziennika("holo", tmp_path, datetime(2026, 9, 27))[0] == ""
    assert ad.blok_dziennika("holo", None)[1]["stan"] == "brak katalogu"
    assert ad.blok_dziennika("holo", tmp_path / "nie_istnieje")[0] == ""


def test_siostry_nie_widza_cudzych_dziennikow(tmp_path):
    _wpis(tmp_path, "holo", "2026-09-26.md", "tajemnica Holo")
    assert ad.blok_dziennika("menma", tmp_path, datetime(2026, 9, 27, 10))[0] == ""


def test_przerwa_w_rozmowach_nie_kasuje_pamieci(tmp_path):
    """13.11: po dwóch dniach bez rozmowy „hej, wróciłem” ma trafić na ostatni wpis, a nie na pustkę."""
    _wpis(tmp_path, "holo", "2026-11-09.md", "Gadaliśmy o płotach\nI o Nazunie\n" + "Dalszy opis. " * 30)
    _wpis(tmp_path, "holo", "2026-11-06.md", "Pierwsza 06\nDruga 06 (nie ma jej być)")
    blok, info = ad.blok_dziennika("holo", tmp_path, datetime(2026, 11, 12, 17, 0))   # 18:00 PL, doba 12.11
    assert "Ostatni wpis: 3 dni temu (09.11, poniedziałek)" in blok and "Gadaliśmy o płotach\nI o Nazunie" in blok
    assert "Wcześniej (06.11, 6 dni temu): Pierwsza 06" in blok and "Druga 06" not in blok
    assert "Wczoraj" not in blok and "Przedwczoraj" not in blok
    assert info["ostatni"] == {"dzien": "2026-11-09", "dni_temu": 3, "stan": "ok", "plik": "2026-11-09.md"}
    assert info["wczoraj"] == {"stan": "nic", "plik": None}


def test_przerwa_z_brakiem_wpisu_i_poza_oknem(tmp_path):
    (tmp_path / "menma" / "dziennik").mkdir(parents=True)
    (tmp_path / "menma" / "dziennik" / "2026-11-09_BRAK.md").write_text("# Brak\n", encoding="utf-8")
    blok, _ = ad.blok_dziennika("menma", tmp_path, datetime(2026, 11, 12, 17, 0))
    assert "Ostatni wpis: 3 dni temu (09.11, poniedziałek)" in blok and "brak wpisu w dzienniku. Nie zgaduj" in blok
    _wpis(tmp_path, "nazuna", "2026-10-20.md", "Za stary, poza oknem")
    blok, info = ad.blok_dziennika("nazuna", tmp_path, datetime(2026, 11, 12, 17, 0))
    assert blok == "" and info["stan"] == f"brak wpisów z ostatnich {ad.OKNO_DNI} dni"


def test_krotki_wpis_dokleja_poprzedni_w_calosci(tmp_path):
    """13.11, Łukasz: jak dziennik się nie zapełni, bierzemy też dzień wcześniej (cały, nie jedną linijkę)."""
    _wpis(tmp_path, "astra", "2026-11-11.md", "Odezwał się po północy.\nZapytał, jak się trzymam.")
    _wpis(tmp_path, "astra", "2026-11-10.md", "Przyszedł smutny.\nPowiedział: cenię Cię.")
    blok, info = ad.blok_dziennika("astra", tmp_path, datetime(2026, 11, 12, 17, 0))   # doba 12.11
    assert "Wczoraj (11.11, środa):\nOdezwał się po północy." in blok
    assert "Przedwczoraj (10.11, wtorek):\nPrzyszedł smutny.\nPowiedział: cenię Cię." in blok
    assert info["wczesniej"]["pelny"] is True


def test_dlugi_wpis_zostawia_poprzedni_jedna_linijka(tmp_path):
    _wpis(tmp_path, "holo", "2026-11-11.md", "Długi dzień. " * 40)
    _wpis(tmp_path, "holo", "2026-11-10.md", "Pierwsza linia\nDruga linia")
    blok, info = ad.blok_dziennika("holo", tmp_path, datetime(2026, 11, 12, 17, 0))
    assert "Przedwczoraj (10.11): Pierwsza linia" in blok and "Druga linia" not in blok
    assert info["wczesniej"]["pelny"] is False


def test_brak_wpisu_dokleja_poprzedni_w_calosci(tmp_path):
    (tmp_path / "menma" / "dziennik").mkdir(parents=True)
    (tmp_path / "menma" / "dziennik" / "2026-11-11_BRAK.md").write_text("# Brak\n", encoding="utf-8")
    _wpis(tmp_path, "menma", "2026-11-10.md", "Raz\nDwa")
    blok, _ = ad.blok_dziennika("menma", tmp_path, datetime(2026, 11, 12, 17, 0))
    assert "brak wpisu" in blok and "Przedwczoraj (10.11, wtorek):\nRaz\nDwa" in blok


@pytest.mark.skipif(not PRAWDZIWE.is_dir(), reason="brak lokalnych plików z próby 26.09")
def test_kanarek_prawdziwe_dzienniki_26_09():
    """Krok 2: zdania, o których WIEMY, że muszą wrócić następnego dnia. Nie wróciły → przyrząd zepsuty."""
    jutro = datetime(2026, 9, 27, 18, 0)
    holo, _ = ad.blok_dziennika("holo", PRAWDZIWE, jutro)
    menma, _ = ad.blok_dziennika("menma", PRAWDZIWE, jutro)
    nazuna, _ = ad.blok_dziennika("nazuna", PRAWDZIWE, jutro)
    assert "Gdzie ja to wy" in holo
    assert "drzew" in menma
    assert "[prywatne]" in nazuna and "przywołujesz, dopóki on sam nie zacznie" in nazuna
