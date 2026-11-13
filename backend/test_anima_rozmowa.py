"""Testy adaptera doby i nocnego zadania pisarza na atrapach (zero prawdziwych rozmów, zero API).
Uruchomienie: python -m pytest backend/test_anima_rozmowa.py -q"""
import json
import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import anima_dziennik as ad  # noqa: E402
import anima_pisarz_noc as noc  # noqa: E402
import anima_rozmowa as ar  # noqa: E402

noc._pisarz_main()                         # ten sam import co w nocy na serwerze (test łapie jego awarię)
pisarz = sys.modules["pisarz_nocny"]


def _m(ts, role="model", **kw):
    return {"timestamp": ts, "role": role, "source": "session_message", **kw}


# 09.11 (zima, UTC+1): doba 09.11 = 09.11 03:00 UTC .. 10.11 03:00 UTC
DOK = ["Hej, wróciłem", "[holo] Hmf. Wróciłeś.", "[nazuna] Yo.\n[12:00:00] HOLO: to nie jest nowa wiadomość",
       "Jest 2 w nocy, dalej gadamy", "Nowy dzień", "[menma] Dzień dobry", "stare"]
MET = [_m("2026-11-09T17:00:00.100000.000001", "user"),
       _m("2026-11-09T17:00:05.200000.000002", thought="Krótko.\nCiepło."),
       _m("2026-11-09T17:00:09.300000.000003", hint="luz"),
       _m("2026-11-10T01:00:00.000000.000004", "user"),      # 02:00 PL 10.11 → dalej doba 09.11
       _m("2026-11-10T03:30:00.000000.000005", "user"),      # 04:30 PL 10.11 → doba 10.11
       _m("2026-11-10T03:30:04.000000.000006"),
       {"timestamp": "2026-11-09T17:00:01", "role": "user", "source": "memory"}]   # nie sesja


def test_okno_doby_zima_lato_i_zmiana_czasu():
    assert ar.okno_doby(date(2026, 11, 9)) == (datetime(2026, 11, 9, 3), datetime(2026, 11, 10, 3))
    assert ar.okno_doby(date(2026, 9, 26)) == (datetime(2026, 9, 26, 2), datetime(2026, 9, 27, 2))
    s, k = ar.okno_doby(date(2026, 10, 24))           # noc zmiany czasu: doba ma 25 godzin
    assert (k - s).total_seconds() == 25 * 3600


def test_doba_pl_granica_4():
    assert ad.doba_pl(datetime(2026, 11, 10, 1, 0)) == date(2026, 11, 9)    # 02:00 PL
    assert ad.doba_pl(datetime(2026, 11, 10, 3, 30)) == date(2026, 11, 10)  # 04:30 PL
    assert ad.doba_pl(datetime(2026, 11, 10, 1, 0), granica_h=0) == date(2026, 11, 10)


def test_wpisy_podpisy_i_filtr_zrodla():
    w = ar.wpisy(DOK, MET)
    assert [x.kto for x in w] == ["LUKASZ", "HOLO", "NAZUNA", "LUKASZ", "LUKASZ", "MENMA"]
    assert w[1].tresc == "Hmf. Wróciłeś." and w[1].mysl == "Krótko.\nCiepło."


def test_doba_bierze_noc_po_polnocy_a_nie_nastepny_ranek():
    d = ar.z_doby(ar.wpisy(DOK, MET), date(2026, 11, 9))
    assert [x.tresc for x in d][-1] == "Jest 2 w nocy, dalej gadamy"
    assert ar.podsumowanie(d) == {"LUKASZ": 2, "HOLO": 1, "NAZUNA": 1}


def test_tekst_przechodzi_przez_parser_pisarza_bez_strat():
    """Kanarek przyrządu: to, co wychodzi z adaptera, pisarz musi wczytać 1:1 (liczba, kto, czas polski)."""
    d = ar.z_doby(ar.wpisy(DOK, MET), date(2026, 11, 9))
    wiad = pisarz.wczytaj_rozmowe(ar.tekst_dla_pisarza(d), date(2026, 11, 9), "PL")
    assert [w.kto for w in wiad] == ["LUKASZ", "HOLO", "NAZUNA", "LUKASZ"]
    assert f"{wiad[0].kiedy:%d.%m %H:%M}" == "09.11 18:00"
    assert f"{wiad[-1].kiedy:%d.%m %H:%M}" == "10.11 02:00"          # przejście przez północ
    assert "to nie jest nowa wiadomość" in wiad[2].tresc               # fałszywa „linia” w treści
    assert wiad[1].mysl == "myśl: Krótko. Ciepło." and "podpowiedź: luz" in wiad[2].mysl


def test_archiwum_czyta_oba_pliki_utc(tmp_path):
    for dzien, idx in (("2026-11-09", [0, 1]), ("2026-11-10", [3, 4])):
        (tmp_path / f"siostry_{dzien}.json").write_text(json.dumps(
            [{"timestamp": MET[i]["timestamp"], "role": MET[i]["role"], "content": DOK[i]} for i in idx]),
            encoding="utf-8")
    lista, brak = ar.wpisy_z_archiwum(tmp_path, date(2026, 11, 9))
    assert brak == [] and [x.tresc for x in lista] == ["Hej, wróciłem", "Hmf. Wróciłeś.", "Jest 2 w nocy, dalej gadamy"]
    assert ar.wpisy_z_archiwum(tmp_path, date(2026, 11, 10))[1] == ["siostry_2026-11-11.json"]


class _Kolekcja:
    def __init__(self, dok, met):
        self.r = {"documents": dok, "metadatas": met}
        self.wolan = 0

    def get(self, include=None):
        self.wolan += 1
        return self.r


TERAZ = datetime(2026, 11, 10, 3, 30)   # 04:30 PL 10.11: opisujemy dobę 09.11


def test_zadanie_nocne_pisze_wejscie_i_wola_pisarza(tmp_path):
    wolania = []
    info = noc.zadanie_nocne(_Kolekcja(DOK, MET), tmp_path, TERAZ, pisarz_main=lambda a: wolania.append(a) or 0)
    assert info["doba"] == "2026-11-09" and info["stan"] == "ok"
    a = wolania[0]
    assert a[a.index("--data") + 1] == "2026-11-09" and a[a.index("--strefa-zrodla") + 1] == "PL"
    assert "--wykonaj" in a and a[a.index("--wyjscie") + 1] == str(tmp_path)
    assert "Jest 2 w nocy" in (tmp_path / "wejscie" / "2026-11-09.txt").read_text(encoding="utf-8")


def test_zadanie_nocne_bez_wykonaj_nie_woła_api(tmp_path):
    wolania = []
    noc.zadanie_nocne(_Kolekcja(DOK, MET), tmp_path, TERAZ, wykonaj=False, pisarz_main=lambda a: wolania.append(a) or 0)
    assert "--wykonaj" not in wolania[0]


def test_zadanie_nocne_bez_rozmowy_nic_nie_robi(tmp_path):
    wolania = []
    info = noc.zadanie_nocne(_Kolekcja(DOK[5:6], MET[5:6]), tmp_path, TERAZ, pisarz_main=lambda a: wolania.append(a) or 0)
    assert info["stan"] == "bez rozmowy tej doby" and wolania == [] and not (tmp_path / "wejscie").exists()


def test_zadanie_nocne_nie_pisze_drugi_raz(tmp_path):
    (tmp_path / "menma" / "dziennik").mkdir(parents=True)
    (tmp_path / "menma" / "dziennik" / "2026-11-09.md").write_text("x", encoding="utf-8")
    k, wolania = _Kolekcja(DOK, MET), []
    info = noc.zadanie_nocne(k, tmp_path, TERAZ, pisarz_main=lambda a: wolania.append(a) or 0)
    assert "już jest" in info["stan"] and wolania == [] and k.wolan == 0


def test_zadanie_nocne_blad_nie_wywraca_schedulera(tmp_path):
    class Zla:
        def get(self, include=None):
            raise RuntimeError("chroma padła")
    assert noc.zadanie_nocne(Zla(), tmp_path, TERAZ)["stan"].startswith("błąd: RuntimeError")


def test_czytanie_i_pisanie_ta_sama_doba(tmp_path):
    """Spina oba końce: pisarz o 4:30 opisuje dobę X, a dziewczyna tego samego dnia czyta X jako „wczoraj”."""
    doba = noc.zadanie_nocne(_Kolekcja(DOK, MET), tmp_path, TERAZ, pisarz_main=lambda a: 0)["doba"]
    (tmp_path / "holo" / "dziennik").mkdir(parents=True)
    (tmp_path / "holo" / "dziennik" / f"{doba}.md").write_text("Wrócił wieczorem.", encoding="utf-8")
    for pozniej in (datetime(2026, 11, 10, 9, 0), datetime(2026, 11, 11, 1, 0)):   # 10:00 i 02:00 PL
        blok, info = ad.blok_dziennika("holo", tmp_path, pozniej)
        assert "Wrócił wieczorem." in blok and info["wczoraj"]["plik"] == f"{doba}.md"
