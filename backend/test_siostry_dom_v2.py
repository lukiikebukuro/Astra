"""Testy dom v2 (2026-11-22) na atrapach: filtr linijek, scena v2, karteczka, przeczucie, gość na stałe.
Uruchomienie: python -m pytest backend/test_siostry_dom_v2.py -q"""
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import siostry_dom_v2 as d2  # noqa: E402

TERAZ = datetime(2026, 11, 22, 9, 0)   # sobota 10:00 w Polsce, doba 22.11


def _wpis(root, s, dzien, tekst):
    p = root / s / "dziennik" / f"{dzien}.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(f"# Dziennik: x\n\n> pisarz: atrapa\n\n{tekst}\n", encoding="utf-8")


# ── filtr: nic prywatnego nie przechodzi do sceny, karteczki ani przeczucia ──────────
def test_bezpieczne_linijki_odcina_prywatne_prosby_zdrowie_i_substancje():
    tekst = "\n".join([
        "- Wieczorem graliśmy w Mario Kart i przegrał trzy razy.",
        "[prywatne] Mówił o czymś trudnym.",
        "[prośba] Nie pisać długich myślników.",
        "Bolał go brzuch po kolacji.",
        "Zapalił jointa przed snem.",
        "Martwił się o pieniądze.",
        "Rano chce zrobić porządek w ogrodzie.",
    ])
    assert d2.bezpieczne_linijki(tekst) == [
        "Wieczorem graliśmy w Mario Kart i przegrał trzy razy.",
        "Rano chce zrobić porządek w ogrodzie.",
    ]


def test_bezpieczne_linijki_pusty_wpis():
    assert d2.bezpieczne_linijki(None) == []
    assert d2.bezpieczne_linijki("") == []


def test_slady_biora_pierwsza_bezpieczna_linijke_z_ostatniego_wpisu(tmp_path):
    _wpis(tmp_path, "menma", "2026-11-21", "[prywatne] cos\nPodlała bazylię i zaśpiewała mu piosenkę.")
    _wpis(tmp_path, "holo", "2026-11-19", "Przeliczyła zapasy na zimę.")   # 3 dni temu: jeszcze w oknie
    _wpis(tmp_path, "nazuna", "2026-11-10", "Grała do świtu.")             # poza oknem 3 dób
    slady = d2.slady_z_dziennikow(tmp_path, ["holo", "menma", "nazuna"], TERAZ)
    assert slady == {"menma": "Podlała bazylię i zaśpiewała mu piosenkę.", "holo": "Przeliczyła zapasy na zimę."}


# ── scena v2: bez szablonu, z pamięcią scen ──────────────────────────────────────
def test_prompt_sceny_bez_przykladow_z_v1_i_z_lista_do_niepowtarzania():
    p = d2.prompt_sceny_v2(["Holo", "Menma", "Nazuna"], "poranek", "sobota", 9.0,
                           {"menma": "Podlała bazylię."}, ["Światło pada na stół, Holo liczy."])
    assert "Holo liczy coś przy stole" not in p and "Nazuna leży z padem" not in p
    assert "NIE powtarzaj" in p and "Światło pada na stół, Holo liczy." in p
    assert "Podlała bazylię." in p and "NIE zaczynaj od światła" in p
    assert "sobota" in p and "9 godz." in p


def test_pamiec_scen_trzyma_ostatnie_i_przezywa_zapis(tmp_path):
    for i in range(25):
        d2.zapamietaj_scene(tmp_path, f"scena {i}", TERAZ)
    assert d2.ostatnie_sceny(tmp_path, n=3) == ["scena 22", "scena 23", "scena 24"]
    assert len((tmp_path / "dom" / "sceny.jsonl").read_text(encoding="utf-8").splitlines()) == 20


def test_pamiec_scen_bez_katalogu_nie_wywala():
    assert d2.ostatnie_sceny(None) == []
    d2.zapamietaj_scene(None, "x")   # nic się nie dzieje


# ── przeczucie Menmy: próg z danych, bez wyników poza jego wpływem ───────────────
def test_sygnal_przeczucia_tylko_dla_nadchodzacych_rzeczy():
    assert d2.sygnal_przeczucia(["Jutro rano chce pojechać nad jezioro."]) == "Jutro rano chce pojechać nad jezioro."
    assert d2.sygnal_przeczucia(["Wczoraj graliśmy w Heroes."]) is None


def test_sygnal_przeczucia_nie_dotyka_pracy_i_odpowiedzi_firm():
    assert d2.sygnal_przeczucia(["W poniedziałek sprawdza odpowiedzi z aplikacji."]) is None
    assert d2.sygnal_przeczucia(["Jutro czeka na decyzję po rozmowie o pracę."]) is None


def test_przeczucie_raz_na_dobe(tmp_path):
    assert not d2.przeczucie_dzis_bylo(tmp_path, "2026-11-22")
    d2.zapisz_przeczucie(tmp_path, "2026-11-22", "Jutro jezioro.", "Coś mi mówi, że nad jeziorem będzie zimno.", TERAZ)
    assert d2.przeczucie_dzis_bylo(tmp_path, "2026-11-22")
    assert not d2.przeczucie_dzis_bylo(tmp_path, "2026-11-23")
    rek = json.loads((tmp_path / "dom" / "przeczucia.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert rek["stan"] == "do_sprawdzenia" and rek["zrodlo"] == "Jutro jezioro."


# ── karteczka ───────────────────────────────────────────────────────────────────
def test_prompt_karteczki_zwykly_i_przeczucie():
    zw = d2.prompt_karteczki("nazuna", "Nazuna", 8, "na stole", "Grała do świtu.")
    assert "Grała do świtu." in zw and "PRZECZUCIE" not in zw and "NIE: zdrowie" in zw
    pr = d2.prompt_karteczki("menma", "Menma", 8, "przy czajniku", None, przeczucie="Jutro jezioro.")
    assert "PRZECZUCIE" in pr and "Jutro jezioro." in pr and "NIE przepowiadasz wyników" in pr


def test_czysc_karteczke_usuwa_cudzyslowy_i_didaskalia():
    assert d2.czysc_karteczke('„*uśmiecha się* Obudź mnie, jak wstaniesz.”') == "Obudź mnie, jak wstaniesz."
    assert d2.czysc_karteczke(None) == ""


def test_blok_karteczki_inny_dla_autorki_i_dla_reszty():
    moja = d2.blok_karteczki("Menma", "na stole", "Coś mi mówi…", moja=True, przeczucie=True)
    cudza = d2.blok_karteczki("Menma", "na stole", "Coś mi mówi…", moja=False, przeczucie=True)
    assert "To twoja karteczka" in moja and "twoje przeczucie" in moja
    assert "Nie streszczaj" in cudza and "To twoja karteczka" not in cudza
    assert d2.blok_karteczki("Menma", "na stole", "", moja=True, przeczucie=False) == ""


# ── wiedzą, gdzie byłeś: tylko fakt i czas ──────────────────────────────────────
def test_minuty_u_astry_tylko_gdy_nowsze_niz_pokoj_i_niedawno():
    teraz = datetime(2026, 11, 22, 1, 0)
    assert d2.minuty_u_astry("2026-11-22T00:40:00.1", "2026-11-21T20:00:00.1", teraz) == 20
    assert d2.minuty_u_astry("2026-11-21T19:00:00.1", "2026-11-21T20:00:00.1", teraz) is None   # pokój nowszy
    assert d2.minuty_u_astry("2026-11-21T10:00:00.1", None, teraz) is None                     # > 6 h
    assert d2.minuty_u_astry(None, None, teraz) is None


def test_blok_gdzie_byl_bez_tresci():
    b = d2.blok_gdzie_byl(20)
    assert "ok. 20 min temu" in b and "Treści tej rozmowy nie znasz" in b
    assert "przed chwilą" in d2.blok_gdzie_byl(5)


# ── Astra na stałe: stan w pliku, nadpisywany, nie kasowany ─────────────────────
def test_gosc_na_stale_zapis_odczyt_i_odeslanie(tmp_path):
    assert d2.wczytaj_gosc(tmp_path) == {}
    d2.zapisz_gosc(tmp_path, "abc", True)
    assert d2.wczytaj_gosc(tmp_path) == {"conversation_id": "abc", "staly": True}
    d2.zapisz_gosc(tmp_path, "abc", False)
    assert d2.wczytaj_gosc(tmp_path)["staly"] is False
    assert (tmp_path / "dom" / "gosc.json").exists()
