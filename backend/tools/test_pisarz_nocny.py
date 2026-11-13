"""Testy pisarza na atrapach (zero prawdziwych rozmów, zero API).
Uruchomienie: python -m pytest backend/tools/test_pisarz_nocny.py -q"""
import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import pisarz_nocny as p  # noqa: E402

ATRAPA = """
[02:46:05] LUKASZ: Ktoś nie śpi? 4:45 na zegarku
[02:46:05] HOLO: Hmf. Ja nie śpię.
      (mysl: Krótko i ciepło.)

[04:02:10] LUKASZ: Jest 6
o 3 się obudziłem
[04:02:11] ASTRA: Dzień dobry.
      (hint: Gotowa.)
[22:02:00] LUKASZ: Gdzie ja to wy i na odwrót
[00:10:00] NAZUNA: Dobranoc, wilku.
"""


def test_czas_polski_lato_zima_i_granica():
    utc = timezone.utc
    assert p.na_czas_polski(datetime(2026, 9, 26, 2, 46, tzinfo=utc)).strftime("%H:%M") == "04:46"
    assert p.na_czas_polski(datetime(2026, 11, 10, 12, 0, tzinfo=utc)).strftime("%H:%M") == "13:00"
    # 25.10.2026 to ostatnia niedziela października: o 01:00 UTC kończy się czas letni
    assert p._przesuniecie_pl(datetime(2026, 10, 25, 0, 59, tzinfo=utc)) == timedelta(hours=2)
    assert p._przesuniecie_pl(datetime(2026, 10, 25, 1, 0, tzinfo=utc)) == timedelta(hours=1)
    # 29.03.2026 ostatnia niedziela marca: o 01:00 UTC zaczyna się czas letni
    assert p._przesuniecie_pl(datetime(2026, 3, 29, 0, 59, tzinfo=utc)) == timedelta(hours=1)
    assert p._przesuniecie_pl(datetime(2026, 3, 29, 1, 0, tzinfo=utc)) == timedelta(hours=2)


def test_regula_ue_zgadza_sie_z_baza_stref():
    from zoneinfo import ZoneInfo
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    for h in range(0, 24 * 365, 7):
        t = start + timedelta(hours=h)
        assert t.astimezone(ZoneInfo("Europe/Warsaw")).utcoffset() == p._przesuniecie_pl(t), t


def test_wczytanie_mysli_hinty_ciag_dalszy_i_polnoc():
    w = p.wczytaj_rozmowe(ATRAPA, date(2026, 9, 26))
    assert [x.kto for x in w] == ["LUKASZ", "HOLO", "LUKASZ", "ASTRA", "LUKASZ", "NAZUNA"]
    assert w[0].kiedy.strftime("%d.%m %H:%M") == "26.09 04:46"           # kanarek lekcji 1
    assert w[1].mysl == "myśl: Krótko i ciepło."
    assert w[2].tresc == "Jest 6\no 3 się obudziłem"                     # ciąg dalszy, nie nowa wiadomość
    assert w[3].mysl == "podpowiedź: Gotowa." and w[3].tresc == "Dzień dobry."
    assert w[4].kiedy.strftime("%d.%m %H:%M") == "27.09 00:02"           # UTC 22:02 to już następny dzień
    assert w[5].kiedy.strftime("%d.%m %H:%M") == "27.09 02:10"           # przejście przez północ UTC


def test_rozmowa_dla_modelu_z_myslami_i_bez():
    w = p.wczytaj_rozmowe(ATRAPA, date(2026, 9, 26))
    z = p.rozmowa_dla_modelu(w, True)
    bez = p.rozmowa_dla_modelu(w, False)
    assert "[26.09 04:46] [LUKASZ] Ktoś nie śpi?" in z
    assert "(Holo, myśl: Krótko i ciepło.)" in z and "Krótko i ciepło" not in bez


def _karta(**kw):
    k = {"typ": "o_nim", "dla": "wspolne", "tresc": "Lubi samotne drzewo na pagórku.",
         "zastepuje": "nowy temat", "dlaczego": "obraz z dzieciństwa", "zrodlo": "26.09, 14:57"}
    k.update(kw)
    return k


def test_walidacja():
    spis = [{"id": "k20260925-1", "typ": "o_nas", "dla": "wspolne", "tresc": "x", "stan": "niepotwierdzona"}]
    surowy = {"dziennik": {"holo": "a", "menma": "b", "nazuna": ""},
              "karty": [_karta(),
                        _karta(zastepuje=""),                                  # §7.4
                        _karta(typ="sprawa"),                                  # sprawa bez statusu
                        _karta(typ="sprawa", status="w toku"),
                        _karta(typ="fakt"),
                        _karta(zastepuje="k20260925-1"),
                        _karta(zastepuje="k19990101-9"),
                        "luźny tekst"],
              "nic": ["przytulanie: czułość, nie fakt"]}
    w = p.waliduj(surowy, spis)
    assert sorted(w.dziennik) == ["holo", "menma"] and w.uwagi == ["brak dziennika: nazuna"]
    assert len(w.karty) == 3
    powody = " | ".join(r for _, r in w.odrzucone)
    for oczekiwany in ("brak pola zastepuje", "sprawa bez statusu", "nieznany typ", "nieznane id", "nie jest obiektem"):
        assert oczekiwany in powody
    assert w.nic == ["przytulanie: czułość, nie fakt"]


def test_zapis_nie_nadpisuje_i_spis_rosnie(tmp_path):
    surowy = {"dziennik": {s: f"wpis {s}" for s in p.SIOSTRY},
              "karty": [_karta(), _karta(typ="sprawa", status="w toku", tresc="Wlew po 23.11.")], "nic": []}
    d = date(2026, 9, 26)
    for _ in range(2):
        w = p.waliduj(surowy, p.wczytaj_spis(tmp_path))
        p.zapisz(tmp_path, d, w, json.dumps(surowy), {"zrodlo_wyniku": "atrapa", "prompt": "v1"})
    assert (tmp_path / "holo" / "dziennik" / "2026-09-26.md").exists()
    assert (tmp_path / "holo" / "dziennik" / "2026-09-26_2.md").exists()       # drugi przebieg obok
    assert "26.09.2026 (sobota)" in (tmp_path / "menma" / "dziennik" / "2026-09-26.md").read_text(encoding="utf-8")
    spis = p.wczytaj_spis(tmp_path)
    assert [k["id"] for k in spis] == ["k20260926-1", "k20260926-2", "k20260926-3", "k20260926-4"]
    assert all(k["stan"] == "niepotwierdzona" for k in spis)
    assert spis[1]["status"] == "w toku"                                       # status sprawy nie nadpisany
    prop = (tmp_path / "karty" / "propozycje_2026-09-26.md").read_text(encoding="utf-8")
    assert "**status sprawy:** w toku" in prop
    assert "nowa, niepotwierdzona" in p.spis_dla_modelu(spis)


def test_brak_wpisu_jest_widoczny(tmp_path):
    pliki = p.zapisz_brak(tmp_path, date(2026, 9, 26), "Gemini: 503")
    assert len(pliki) == 3 and "Gemini: 503" in pliki[0].read_text(encoding="utf-8")


def test_na_sucho_nie_wola_api(tmp_path, monkeypatch):
    def nie_wolno(*a, **k):
        raise AssertionError("na sucho nie wolno wołać API")
    monkeypatch.setattr(p, "wolaj_gemini", nie_wolno)
    plik = tmp_path / "dzien.txt"
    plik.write_text(ATRAPA, encoding="utf-8")
    prompt = tmp_path / "prompt.md"
    prompt.write_text("naglowek\n---\nJesteś pisarzem.", encoding="utf-8")
    assert p.main(["--rozmowa", str(plik), "--data", "2026-09-26", "--wyjscie", str(tmp_path / "out"),
                   "--prompt", str(prompt)]) == 0
    podglad = (tmp_path / "out" / "podglad" / "wejscie_2026-09-26.txt").read_text(encoding="utf-8")
    assert "Jesteś pisarzem." in podglad and "naglowek" not in podglad
    assert "DATA DNIA: 2026-09-26 (sobota)" in podglad and "pierwsza noc pisarza" in podglad


def test_drugi_przebieg_tego_dnia_zatrzymany(tmp_path):
    """10.11: Gemini w drugim przebiegu widział karty ręcznej próby i je przepisał. Teraz STOP."""
    plik = tmp_path / "dzien.txt"
    plik.write_text(ATRAPA, encoding="utf-8")
    prompt = tmp_path / "prompt.md"
    prompt.write_text("x\n---\nJesteś pisarzem.", encoding="utf-8")
    wynik = tmp_path / "wynik.json"
    wynik.write_text(json.dumps({"dziennik": {s: "w" for s in p.SIOSTRY}, "karty": [_karta()], "nic": []}),
                     encoding="utf-8")
    argi = ["--rozmowa", str(plik), "--data", "2026-09-26", "--wyjscie", str(tmp_path / "out"),
            "--prompt", str(prompt), "--z-wyniku", str(wynik)]
    assert p.main(argi) == 0
    assert p.main(argi) == 3                                   # ten sam dzień, ten sam spis: STOP
    assert len(p.wczytaj_spis(tmp_path / "out")) == 1          # spis nietknięty
    assert p.main(argi + ["--ten-sam-dzien"]) == 0             # świadomie: wolno
    assert len(p.wczytaj_spis(tmp_path / "out")) == 2


def test_potwierdza_i_zastapienie_bez_kasowania(tmp_path):
    """Prompt v2, zasada 9: ten sam fakt wrócił → potwierdzenie; fakt się zmienił → stara karta nieaktualna."""
    d1, d2 = date(2026, 9, 26), date(2026, 9, 27)
    pierwszy = {"dziennik": {}, "karty": [_karta(), _karta(typ="sprawa", status="w toku", tresc="Wlew 10.11.")]}
    p.zapisz(tmp_path, d1, p.waliduj(pierwszy, []), "{}", {"zrodlo_wyniku": "a", "prompt": "v2"})
    drugi = {"dziennik": {}, "karty": [
        {"zastepuje": "potwierdza k20260926-1", "zrodlo": "27.09, 10:00"},
        _karta(typ="sprawa", status="w toku", tresc="Wlew przełożony, po 23.11.", zastepuje="k20260926-2"),
        {"zastepuje": "potwierdza k20260101-1", "zrodlo": "x"}]}
    w = p.waliduj(drugi, p.wczytaj_spis(tmp_path))
    assert [c for c, _ in w.potwierdzenia] == ["k20260926-1"] and len(w.karty) == 1
    assert "potwierdza nieznane id" in w.odrzucone[0][1]
    p.zapisz(tmp_path, d2, w, "{}", {"zrodlo_wyniku": "a", "prompt": "v2"})
    spis = {k["id"]: k for k in p.wczytaj_spis(tmp_path)}
    assert spis["k20260926-1"]["potwierdzenia"] == ["2026-09-27"] and spis["k20260926-1"]["stan"] == "niepotwierdzona"
    assert spis["k20260926-2"]["stan"] == "nieaktualna"                    # nie zniknęła
    assert spis["k20260926-2"]["zastapiona_przez"] == "k20260927-1"
    assert "Wlew 10.11." not in p.spis_dla_modelu(list(spis.values()))     # pisarz widzi tylko aktualne
    assert "Wlew przełożony" in p.spis_dla_modelu(list(spis.values()))
