"""Nocny pisarz dziennika sióstr: ANIMA v2, etap 2 („w cieniu”).

Plan: inzynieria_wsteczna/propozycja_anima_v2_2026-11-03.md (§3 pisarz, §5 etap 2, §7 poprawki).
Work-order tego kroku: inzynieria_wsteczna/pisarz_nocny_etap2_2026-11-10.md.

Czyta surową rozmowę jednego dnia z pokoju sióstr i pisze do plików:
  - dziennik każdej siostry (Markdown, jeden plik na dzień),
  - propozycje kart pamięci (oznaczone „nowa, niepotwierdzona”),
  - listę „nic” (co pisarz świadomie pominął) i surowy JSON odpowiedzi modelu.
Nic nie trafia do promptu ani do bazy. Nic się nie nadpisuje (istniejący plik dostaje przyrostek _2, _3...).

Tryby:
  (domyślnie) na sucho: składa wejście dla modelu, liczy rozmiar, zapisuje podgląd. ZERO wywołań API.
  --wykonaj: woła Gemini. Tylko po „tak” Łukasza (prywatne rozmowy idą do zewnętrznego API, płatne).
  --z-wyniku PLIK: bierze gotowy JSON (np. ręczną próbę Claude) i puszcza go przez tę samą walidację i zapis.

Przykład (na sucho, próba z 26.09):
  python backend/tools/pisarz_nocny.py --rozmowa inzynieria_wsteczna/pisarz_proby/dzien_2026-09-26.txt --data 2026-09-26
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ASTRA = Path(__file__).resolve().parents[2]
# v2 w backend/prompts (10.11), żeby pojechał z deployem; v1 zostaje w inzynieria_wsteczna jako historia
DOMYSLNY_PROMPT = ASTRA / "backend" / "prompts" / "pisarz_v2_prompt.md"
DOMYSLNE_WYJSCIE = ASTRA / "inzynieria_wsteczna" / "pisarz_proby" / "anima_pliki"
DOMYSLNY_MODEL = "gemini-3.1-pro-preview"   # §7.3: pisarz na mocniejszym modelu niż rozmowa

SIOSTRY = ("holo", "menma", "nazuna")
IMIONA = {"holo": "Holo", "menma": "Menma", "nazuna": "Nazuna"}
IMIONA_DOP = {"holo": "Holo", "menma": "Menmy", "nazuna": "Nazuny"}   # „Dziennik Nazuny”
TYPY_KART = {"o_nim", "jak_z_nim", "sprawa", "o_nas"}
DLA_KOGO = {"wspolne", *SIOSTRY}
STATUSY_SPRAWY = {"pomysł", "w toku", "zrobione", "porzucone"}
DNI_TYGODNIA = ("poniedziałek", "wtorek", "środa", "czwartek", "piątek", "sobota", "niedziela")


# ---------------------------------------------------------------- czas polski
def _ostatnia_niedziela(rok: int, miesiac: int) -> date:
    d = date(rok, miesiac + 1, 1) - timedelta(days=1) if miesiac < 12 else date(rok, 12, 31)
    return d - timedelta(days=(d.weekday() + 1) % 7)


def _przesuniecie_pl(utc: datetime) -> timedelta:
    """Reguła UE bez bazy stref: czas letni od ostatniej niedzieli marca 01:00 UTC
    do ostatniej niedzieli października 01:00 UTC. Zapas, gdy brak tzdata (Windows bez pakietu)."""
    rok = utc.year
    start = datetime.combine(_ostatnia_niedziela(rok, 3), datetime.min.time(), timezone.utc) + timedelta(hours=1)
    koniec = datetime.combine(_ostatnia_niedziela(rok, 10), datetime.min.time(), timezone.utc) + timedelta(hours=1)
    return timedelta(hours=2) if start <= utc < koniec else timedelta(hours=1)


def na_czas_polski(utc: datetime) -> datetime:
    """UTC -> czas polski (lekcja 1 z próby 26.09: surowy eksport ma godziny w UTC)."""
    utc = utc.astimezone(timezone.utc)
    try:
        from zoneinfo import ZoneInfo
        return utc.astimezone(ZoneInfo("Europe/Warsaw"))
    except Exception:
        return utc.astimezone(timezone(_przesuniecie_pl(utc)))


# ---------------------------------------------------------------- wczytanie rozmowy
@dataclass
class Wiadomosc:
    kiedy: datetime          # czas polski, ze strefą
    kto: str                 # LUKASZ, HOLO, MENMA, NAZUNA, ASTRA...
    tresc: str
    mysl: str | None = None  # „(mysl: ...)” postaci; Łukasz nie ma myśli


_LINIA = re.compile(r"^\[(\d\d):(\d\d):(\d\d)\] ([A-ZĄĆĘŁŃÓŚŹŻ_]+): ?(.*)$")
_MYSL = re.compile(r"^\s+\((mysl|hint): ?(.*?)\)?\s*$", re.S)


def wczytaj_rozmowe(tekst: str, dzien_zrodla: date, strefa_zrodla: str = "UTC") -> list[Wiadomosc]:
    """Format eksportu z pisarz_proby: „[HH:MM:SS] KTO: treść”, pod spodem wcięte „(mysl: ...)”.
    Godzina, która cofa się względem poprzedniej, oznacza przejście przez północ."""
    wynik: list[Wiadomosc] = []
    dzien = dzien_zrodla
    poprzednia: datetime | None = None
    for linia in tekst.splitlines():
        m = _LINIA.match(linia)
        if m:
            g, mi, s, kto, tresc = m.groups()
            kiedy = datetime(dzien.year, dzien.month, dzien.day, int(g), int(mi), int(s))
            if poprzednia and kiedy < poprzednia - timedelta(hours=1):
                dzien += timedelta(days=1)
                kiedy += timedelta(days=1)
            poprzednia = kiedy
            if strefa_zrodla.upper() == "UTC":
                kiedy_pl = na_czas_polski(kiedy.replace(tzinfo=timezone.utc))
            else:  # już polski
                kiedy_pl = kiedy.replace(tzinfo=timezone(_przesuniecie_pl(kiedy.replace(tzinfo=timezone.utc))))
            wynik.append(Wiadomosc(kiedy_pl, kto, tresc.strip()))
            continue
        if not wynik or not linia.strip():
            continue
        mm = _MYSL.match(linia)
        if mm:  # myśl postaci albo podpowiedź (hint) Astry: nie jest częścią wypowiedzi
            rodzaj = "myśl" if mm.group(1) == "mysl" else "podpowiedź"
            kawalek = f"{rodzaj}: {mm.group(2).strip().rstrip(')')}"
            wynik[-1].mysl = kawalek if wynik[-1].mysl is None else f"{wynik[-1].mysl} | {kawalek}"
        else:  # dalszy ciąg treści w kolejnej linii
            wynik[-1].tresc += "\n" + linia.strip()
    return wynik


def rozmowa_dla_modelu(wiadomosci: list[Wiadomosc], z_myslami: bool = True) -> str:
    linie = []
    for w in wiadomosci:
        linie.append(f"[{w.kiedy:%d.%m %H:%M}] [{w.kto}] {w.tresc}")
        if z_myslami and w.mysl:
            linie.append(f"      ({w.kto.capitalize()}, {w.mysl})")
    return "\n".join(linie)


# ---------------------------------------------------------------- spis kart (w cieniu: tylko propozycje)
def wczytaj_spis(root: Path) -> list[dict]:
    p = root / "karty_spis.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else []


def spis_dla_modelu(spis: list[dict]) -> str:
    """Lekcja 2 z próby 26.09: bez spisu pole `zastepuje` jest zawsze „nowy temat” i karty się dublują."""
    aktywne = [k for k in spis if k.get("stan") != "nieaktualna"]
    if not aktywne:
        return "(spis jest pusty: to pierwsza noc pisarza)"
    return "\n".join(f"- [{k['id']}] {k['typ']}, dla: {k['dla']}"
                     f"{' (nowa, niepotwierdzona)' if k.get('stan') == 'niepotwierdzona' else ''}: {k['tresc']}"
                     for k in aktywne)


def zloz_wejscie(prompt_md: str, dzien: date, rozmowa: str, spis: list[dict]) -> tuple[str, str]:
    instrukcja = prompt_md.split("---", 1)[1].strip() if "---" in prompt_md else prompt_md.strip()
    instrukcja += ("\n\n**Spis kart** dostajesz na wejściu, każda karta z id w nawiasie kwadratowym "
                   "(np. `k20260926-1`). W polu `zastepuje` używasz tych id, zgodnie z zasadami wyżej.")
    tresc = (f"DATA DNIA: {dzien.isoformat()} ({DNI_TYGODNIA[dzien.weekday()]})\n"
             f"Godziny w rozmowie są w czasie polskim, z datą (rozmowa może przejść przez północ).\n\n"
             f"SPIS KART:\n{spis_dla_modelu(spis)}\n\nROZMOWA:\n{rozmowa}")
    return instrukcja, tresc


# ---------------------------------------------------------------- walidacja odpowiedzi
@dataclass
class Wynik:
    dziennik: dict[str, str] = field(default_factory=dict)
    karty: list[dict] = field(default_factory=list)
    odrzucone: list[tuple[dict, str]] = field(default_factory=list)
    nic: list[str] = field(default_factory=list)
    uwagi: list[str] = field(default_factory=list)
    potwierdzenia: list[tuple[str, dict]] = field(default_factory=list)   # (id, karta): ten sam fakt wrócił


def _pusty(x) -> bool:
    return not isinstance(x, str) or not x.strip()


def waliduj(surowy: dict, spis: list[dict]) -> Wynik:
    w = Wynik()
    znane_id = {k["id"] for k in spis}
    dz = surowy.get("dziennik") or {}
    for s in SIOSTRY:
        if _pusty(dz.get(s)):
            w.uwagi.append(f"brak dziennika: {s}")
        else:
            w.dziennik[s] = dz[s].strip()
    for k in surowy.get("karty") or []:
        if not isinstance(k, dict):
            w.odrzucone.append(({"tresc": str(k)}, "karta nie jest obiektem"))
            continue
        z = (k.get("zastepuje") or "").strip()
        if z.lower().startswith("potwierdza"):   # prompt v2, zasada 9: bez nowej karty
            czesci = z.split(None, 1)
            cel = czesci[1].strip() if len(czesci) > 1 else ""
            if cel in znane_id:
                w.potwierdzenia.append((cel, k))
            else:
                w.odrzucone.append((k, f"potwierdza nieznane id {cel!r}"))
            continue
        powody = []
        if k.get("typ") not in TYPY_KART:
            powody.append(f"nieznany typ {k.get('typ')!r}")
        if k.get("dla") not in DLA_KOGO:
            powody.append(f"nieznane „dla” {k.get('dla')!r}")
        for pole in ("tresc", "dlaczego", "zrodlo", "zastepuje"):
            if _pusty(k.get(pole)):
                powody.append(f"brak pola {pole}")   # §7.4: bez `zastepuje` zapis odrzucony
        if k.get("typ") == "sprawa" and k.get("status") not in STATUSY_SPRAWY:
            powody.append(f"sprawa bez statusu z listy {sorted(STATUSY_SPRAWY)}")
        if z and not z.lower().startswith("nowy temat") and z not in znane_id:
            powody.append(f"zastepuje nieznane id {z!r}")
        if powody:
            w.odrzucone.append((k, "; ".join(powody)))
        else:
            w.karty.append(k)
    w.nic = [str(x) for x in (surowy.get("nic") or [])]
    return w


# ---------------------------------------------------------------- zapis do plików
def bezpieczna_sciezka(p: Path) -> Path:
    """Nigdy nie nadpisujemy: drugi przebieg tego samego dnia idzie obok, z przyrostkiem."""
    if not p.exists():
        return p
    n = 2
    while (q := p.with_name(f"{p.stem}_{n}{p.suffix}")).exists():
        n += 1
    return q


def _zapisz(p: Path, tekst: str) -> Path:
    p.parent.mkdir(parents=True, exist_ok=True)
    p = bezpieczna_sciezka(p)
    p.write_text(tekst, encoding="utf-8")
    return p


def zapisz(root: Path, dzien: date, wynik: Wynik, surowy_tekst: str, meta: dict) -> list[Path]:
    zapisane = []
    naglowek = (f"> pisarz: {meta.get('zrodlo_wyniku')}, prompt: {meta.get('prompt')}, "
                f"w cieniu (nie trafia do promptu ani do bazy)\n")
    dzien_tyg = DNI_TYGODNIA[dzien.weekday()]
    for s, tekst in wynik.dziennik.items():
        zapisane.append(_zapisz(root / s / "dziennik" / f"{dzien.isoformat()}.md",
                                f"# Dziennik {IMIONA_DOP[s]}: {dzien:%d.%m.%Y} ({dzien_tyg})\n\n{naglowek}\n{tekst}\n"))

    spis = wczytaj_spis(root)
    prefiks = f"k{dzien:%Y%m%d}-"
    nr = 1 + max([int(k["id"].split("-")[1]) for k in spis if k["id"].startswith(prefiks)] or [0])
    linie = [f"# Propozycje kart: {dzien:%d.%m.%Y}\n", naglowek,
             "Każda karta ma status **nowa, niepotwierdzona** przez 7 dni (§7.2). "
             "Łukasz może zawetować albo poprawić; nic tu nie trafia do promptu.\n"]
    for k in wynik.karty:
        # `stan` = stan karty w spisie (niepotwierdzona / aktywna / nieaktualna);
        # `status` zostaje tym, co podał pisarz przy sprawie (pomysł / w toku / zrobione / porzucone)
        k = dict(k, id=f"{prefiks}{nr}", data=dzien.isoformat(), stan="niepotwierdzona")
        nr += 1
        spis.append({x: k[x] for x in ("id", "typ", "dla", "tresc", "data", "stan", "status") if x in k})
        for stara in spis:   # etap 1 w plikach: zastąpienie bez kasowania, stara karta dostaje stan
            if stara["id"] == k["zastepuje"].strip():
                stara["stan"] = "nieaktualna"
                stara["zastapiona_przez"] = k["id"]
        linie += [f"\n## [{k['id']}] {k['typ']}, dla: {k['dla']}",
                  f"- **treść:** {k['tresc']}"]
        if k["typ"] == "sprawa":
            linie.append(f"- **status sprawy:** {k.get('status')}")
        linie += [f"- **zastępuje:** {k['zastepuje']}", f"- **dlaczego:** {k['dlaczego']}",
                  f"- **źródło:** {k['zrodlo']}"]
    if wynik.potwierdzenia:
        linie.append("\n## Potwierdzone (ten sam fakt wrócił, bez nowej karty)")
        for cel, k in wynik.potwierdzenia:
            for stara in spis:
                if stara["id"] == cel:
                    stara.setdefault("potwierdzenia", []).append(dzien.isoformat())
            linie.append(f"- [{cel}] ← {k.get('zrodlo', '?')}")
    if wynik.odrzucone:
        linie.append("\n## Odrzucone przez walidację (do wglądu, nie do spisu)")
        linie += [f"- {k.get('tresc', '?')} → **{powod}**" for k, powod in wynik.odrzucone]
    if wynik.nic:
        linie.append("\n## „Nic”: co pisarz świadomie pominął")
        linie += [f"- {x}" for x in wynik.nic]
    if wynik.uwagi:
        linie.append("\n## Uwagi")
        linie += [f"- {x}" for x in wynik.uwagi]
    zapisane.append(_zapisz(root / "karty" / f"propozycje_{dzien.isoformat()}.md", "\n".join(linie) + "\n"))

    spis_p = root / "karty_spis.json"
    tmp = spis_p.with_suffix(".tmp")
    tmp.write_text(json.dumps(spis, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(spis_p)     # spis tylko rośnie; karty nie znikają, dostają status
    zapisane.append(spis_p)
    zapisane.append(_zapisz(root / "surowe" / f"{dzien.isoformat()}_{meta.get('zrodlo_wyniku', 'wynik')}.json",
                            surowy_tekst))
    return zapisane


def zapisz_brak(root: Path, dzien: date, powod: str) -> list[Path]:
    """§7.5: nocna awaria nie może dać po cichu amnezji. Brak wpisu ma być widoczny."""
    return [_zapisz(root / s / "dziennik" / f"{dzien.isoformat()}_BRAK.md",
                    f"# Brak wpisu z dnia {dzien:%d.%m.%Y}\n\nPisarz zawiódł: {powod}\n"
                    f"Rano do promptu powinien pójść skrót wczorajszej surowej rozmowy (etap 3).\n")
            for s in SIOSTRY]


# ---------------------------------------------------------------- Gemini (tylko --wykonaj)
def klucz_api() -> str:
    if os.environ.get("GEMINI_API_KEY"):
        return os.environ["GEMINI_API_KEY"]
    env = ASTRA / "backend" / ".env"
    if env.exists():
        for linia in env.read_text(encoding="utf-8").splitlines():
            if linia.startswith("GEMINI_API_KEY="):
                return linia.split("=", 1)[1].strip().strip('"').strip("'")
    sys.exit("brak GEMINI_API_KEY (ani w środowisku, ani w backend/.env)")


def wolaj_gemini(instrukcja: str, tresc: str, model: str, proby: int = 3) -> tuple[str, dict]:
    from google import genai
    from google.genai import types
    klient = genai.Client(api_key=klucz_api())
    ostatni = None
    for n in range(proby):
        try:
            odp = klient.models.generate_content(
                model=model, contents=tresc,
                config=types.GenerateContentConfig(system_instruction=instrukcja, temperature=0.4,
                                                   max_output_tokens=8192,
                                                   response_mime_type="application/json"))
            u = odp.usage_metadata
            return odp.text or "", {"wejscie": u.prompt_token_count, "wyjscie": u.candidates_token_count}
        except Exception as e:  # 402 (brak środków) nie ponawiamy, 429/500/503 tak
            ostatni = e
            kod = getattr(e, "code", None)
            if kod not in (429, 500, 503) or n == proby - 1:
                break
            time.sleep(5 * 3 ** n)
    raise RuntimeError(f"Gemini: {type(ostatni).__name__} {getattr(ostatni, 'code', '')}".strip())


# ---------------------------------------------------------------- main
def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--rozmowa", required=True, type=Path, help="plik z rozmową dnia (format eksportu pisarz_proby)")
    ap.add_argument("--data", required=True, help="dzień, z którego jest plik (YYYY-MM-DD, w strefie źródła)")
    ap.add_argument("--strefa-zrodla", default="UTC", choices=["UTC", "PL"])
    ap.add_argument("--wyjscie", type=Path, default=DOMYSLNE_WYJSCIE)
    ap.add_argument("--prompt", type=Path, default=DOMYSLNY_PROMPT)
    ap.add_argument("--model", default=DOMYSLNY_MODEL)
    ap.add_argument("--bez-mysli", action="store_true", help="nie podawaj pisarzowi myśli postaci")
    ap.add_argument("--ten-sam-dzien", action="store_true",
                    help="pozwól pisać, choć spis ma już karty z tego dnia (domyślnie STOP)")
    tryb = ap.add_mutually_exclusive_group()
    tryb.add_argument("--wykonaj", action="store_true", help="naprawdę zawołaj Gemini (po „tak” Łukasza)")
    tryb.add_argument("--z-wyniku", type=Path, help="gotowy JSON pisarza do walidacji i zapisu")
    a = ap.parse_args(argv)

    dzien = date.fromisoformat(a.data)
    wiad = wczytaj_rozmowe(a.rozmowa.read_text(encoding="utf-8"), dzien, a.strefa_zrodla)
    if not wiad:
        print("STOP: nie wczytano ani jednej wiadomości (zły format pliku?)")
        return 2
    kto = {}
    for w in wiad:
        kto[w.kto] = kto.get(w.kto, 0) + 1
    print(f"wiadomości: {len(wiad)} {kto}")
    print(f"czas polski: od {wiad[0].kiedy:%d.%m %H:%M} do {wiad[-1].kiedy:%d.%m %H:%M}")

    spis = wczytaj_spis(a.wyjscie)
    instrukcja, tresc = zloz_wejscie(a.prompt.read_text(encoding="utf-8"), dzien,
                                     rozmowa_dla_modelu(wiad, not a.bez_mysli), spis)
    bajty = len((instrukcja + tresc).encode("utf-8"))
    print(f"wejście dla modelu: {bajty} B, ok. {bajty / 3.3:,.0f} tokenów; kart w spisie: {len(spis)}")

    # 10.11: drugi przebieg tego samego dnia widział w spisie karty pierwszego i je przepisał
    # (4 z 5 kart Gemini „zastępowało” karty ręcznej próby). Porównanie dwóch pisarzy wymaga osobnych --wyjscie.
    z_tego_dnia = [k["id"] for k in spis if k.get("data") == dzien.isoformat()]
    if z_tego_dnia:
        print(f"UWAGA: spis ma już {len(z_tego_dnia)} kart(y) z tego dnia ({', '.join(z_tego_dnia)}). "
              f"Ten przebieg nie będzie niezależny.")
        if (a.wykonaj or a.z_wyniku) and not a.ten_sam_dzien:
            print("STOP: do porównania użyj osobnego --wyjscie; świadomie dopisać: --ten-sam-dzien")
            return 3

    if a.z_wyniku:
        surowy_tekst = a.z_wyniku.read_text(encoding="utf-8")
        zrodlo = a.z_wyniku.stem
    elif a.wykonaj:
        try:
            surowy_tekst, uzycie = wolaj_gemini(instrukcja, tresc, a.model)
            print(f"Gemini OK: {uzycie}")
        except RuntimeError as e:
            for p in zapisz_brak(a.wyjscie, dzien, str(e)):
                print(f"zapisano: {p}")
            print(f"STOP: {e}")
            return 1
        zrodlo = a.model
    else:
        p = _zapisz(a.wyjscie / "podglad" / f"wejscie_{dzien.isoformat()}.txt",
                    f"=== INSTRUKCJA ===\n{instrukcja}\n\n=== TREŚĆ ===\n{tresc}\n")
        print(f"NA SUCHO: zero wywołań API. Podgląd wejścia: {p}")
        return 0

    try:
        surowy = json.loads(surowy_tekst)
    except json.JSONDecodeError as e:
        for p in zapisz_brak(a.wyjscie, dzien, f"odpowiedź to nie JSON ({e})"):
            print(f"zapisano: {p}")
        _zapisz(a.wyjscie / "surowe" / f"{dzien.isoformat()}_{zrodlo}_ZEPSUTY.txt", surowy_tekst)
        return 1
    wynik = waliduj(surowy, spis)
    print(f"dzienniki: {sorted(wynik.dziennik)}; karty: {len(wynik.karty)} przyjęte, "
          f"{len(wynik.odrzucone)} odrzucone; „nic”: {len(wynik.nic)}")
    for u in wynik.uwagi:
        print(f"UWAGA: {u}")
    for p in zapisz(a.wyjscie, dzien, wynik, surowy_tekst,
                    {"zrodlo_wyniku": zrodlo, "prompt": a.prompt.name}):
        print(f"zapisano: {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
