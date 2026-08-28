# -*- coding: utf-8 -*-
"""
AUDYT AMNEZJI — niezmienniki na trace'ie odczytu.

Sprawdza, czy debugger mowi prawde o tym, skad biora sie wpisy w prompcie.
Read-only: wola wylacznie `/api/debug/inspect`, nic nie zapisuje.

Powod istnienia (audyt 2026-08-28): Amnezja stala sie konstrukcja nosna — stoi na niej
`golden_trafnosc.py`, a na nim decyzje o parametrach pamieci. Nigdy nie byla testowana.
Pierwszy przebieg znalazl, ze ~25% promptu nie mialo rodowodu w trace (Kanal 2 i 3
bez etapow). Ten skrypt pilnuje, zeby to nie wrocilo.

ZASADA (wazne/bugi/pomiar_klamie.md): przyrzad musi NADAZAC za systemem. Kazdy nowy
kanal retrievalu = nowa nazwa w ETAPY_ZRODLOWE ponizej, inaczej audyt zglosi naruszenie,
ktorego nie ma. Jesli dopisujesz kanal do `search_memories` — dopisz go TU w tym samym commicie.

Uzycie (na VPS):
    ./venv/bin/python tools/audyt_amnezji.py
"""
import json
import re
import sys
import urllib.parse
import urllib.request

BASE = "http://127.0.0.1:8001/api/debug/inspect"

ZAPYTANIA = [
    "opowiedz o ldi",
    "jak sie czuje moje jelito",
    "co robilismy wczoraj",
    "opowiedz o anima",
    "co wiesz o amelii",
]

# Kazdy etap, ktory MOZE byc zrodlem wpisu w `8_final`.
# Aktualizowac razem z kazda zmiana kanalow w vector_store.search_memories.
ETAPY_ZRODLOWE = (
    "2_po_wykluczeniu",
    "2b_po_kanale_leksykalnym",
    "3_po_reranku",
    "4_po_temporal",
    "5_milestony",
    "5b_own_life",
    "5c_kanal2_zasady",
    "5d_kanal3_wiedza",
    "6_po_mmr_facts",
    "7_kanal1_final",
    "9a_domieszka_shared",
)


def inspect(query, persona="astra"):
    url = "%s?query=%s&persona=%s" % (BASE, urllib.parse.quote(query), urllib.parse.quote(persona))
    with urllib.request.urlopen(url, timeout=180) as r:
        return json.loads(r.read().decode("utf-8"))


def klucz(item):
    """Stabilny identyfikator wpisu miedzy etapami. `_rec` przycina tekst do 100 znakow."""
    if isinstance(item, dict):
        return (item.get("text") or "")[:70]
    return str(item)[:70]


def main():
    naruszenia = []
    for q in ZAPYTANIA:
        d = inspect(q)
        etapy = {s["name"]: s for s in (d.get("stages") or [])}
        prompt = d.get("system_prompt") or ""

        def zbior(nazwa):
            return {klucz(i) for i in (etapy.get(nazwa, {}).get("items") or [])}

        # KANAREK: jesli trace jest pusty, przyrzad nie mierzy niczego
        if not etapy:
            print("KANAREK PADL: brak etapow w odpowiedzi dla %r" % q)
            return 2

        zrodla = set()
        for nazwa in ETAPY_ZRODLOWE:
            zrodla |= zbior(nazwa)

        # I1 — zaden wpis nie moze pojawic sie w `8_final` znikad
        znikad = zbior("8_final") - zrodla
        if znikad:
            naruszenia.append(("I1: wpis w 8_final bez zrodla w zadnym etapie", q, sorted(znikad)))

        # I2 — budzet nie wymysla wpisow
        nadmiar = zbior("9c_po_budzecie") - zbior("9b_final_prompt")
        if nadmiar:
            naruszenia.append(("I2: 9c nie jest podzbiorem 9b", q, sorted(nadmiar)))

        # I3 — kazdy wpis z ostatniego etapu realnie laduje w prompcie
        w = re.search(r"\[WSPOMNIENIA\](.*?)\[/WSPOMNIENIA\]", prompt, re.S)
        z = re.search(r"\[TWOJE ZASADY[^\]]*\](.*?)(?=\n\[|\Z)", prompt, re.S)
        widoczne = (w.group(1) if w else "") + (z.group(1) if z else "")
        gubione = [t for t in zbior("9c_po_budzecie") if t[:40] not in widoczne]
        if gubione:
            naruszenia.append(("I3: wpis z 9c nie trafil do promptu", q, sorted(gubione)))

        # I4 — liczba linii w prompcie zgadza sie z ostatnim etapem
        lw = len([l for l in (w.group(1).split("\n") if w else []) if l.strip().startswith("-")])
        lz = len([l for l in (z.group(1).split("\n") if z else []) if l.strip().startswith("•")])
        c9 = etapy.get("9c_po_budzecie", {}).get("count", 0)
        if lw + lz != c9:
            naruszenia.append(("I4: prompt ma inna liczbe wpisow niz 9c", q,
                               ["prompt=%d (wspomnienia %d + zasady %d) vs 9c=%d" % (lw + lz, lw, lz, c9)]))

        print("[%-26s] pula=%-3s po_wykl=%-3s po_leks=%-3s kanal2=%-2s final=%-3s | prompt %d+%d"
              % (q,
                 etapy.get("1_pula_surowa", {}).get("count"),
                 etapy.get("2_po_wykluczeniu", {}).get("count"),
                 etapy.get("2b_po_kanale_leksykalnym", {}).get("count"),
                 etapy.get("5c_kanal2_zasady", {}).get("count"),
                 etapy.get("8_final", {}).get("count"), lw, lz))

    print("\n" + "=" * 72)
    if not naruszenia:
        print("BRAK NARUSZEN — trace spelnia wszystkie cztery niezmienniki (I1-I4)")
        print("=" * 72)
        return 0
    print("NARUSZENIA: %d" % len(naruszenia))
    for typ, q, przyklady in naruszenia:
        print("\n  %s\n    zapytanie: %r" % (typ, q))
        for p in przyklady[:3]:
            print("      -> %s" % p)
    print("=" * 72)
    return 1


if __name__ == "__main__":
    sys.exit(main())
