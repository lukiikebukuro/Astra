# -*- coding: utf-8 -*-
"""
GOLDEN SET — router adresowania Pokoju Sióstr (Zadanie B, 2026-07-25).
Czyste funkcje → zero API, zero Gemini. Uruchom: python router_golden.py
Testuje siostry_router.route(...) na realnych przypadkach z logów (T1–T7) + syntetyki.
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_BACKEND = os.path.abspath(os.path.join(_HERE, "..", "..", "..", "backend"))
sys.path.insert(0, _BACKEND)

import siostry_router as R

# (id, opis, msg, hour, last_full_speaker, recent, expected_routing)
# Opcjonalne 8. i 9. pole: sticky_turns, minutes_since_last (domyślnie 0, 0.0 — lepkość świeża).
CASES = [
    # --- T1–T7: realne logi (sekcja B.1 planu Fable) ---
    ("T1", "wzmianka 3 imion w rozmowie z Nazuną → tylko Nazuna (lepkość); Holo/Menma milczą",
     "Nazuna taka czula?? Nie poznaje. Holo pewnie w snie glebokim a menma ... Menma to menma",
     23, "nazuna", [], [("nazuna", "full")]),
    ("T2", "pytanie DO Nazuny O Holo ('myslisz ze holo mysli') → Nazuna, nie Holo",
     "Myslisz ze holo mysli tak samo o przeszlosci z lawrencem?",
     0, "nazuna", [], [("nazuna", "full")]),
    ("T3", "wzmianka 3-os. czas przeszly ('ale holo sie odezwala') → Nazuna",
     "Ale holo zie odezwala przed chwila",
     0, "nazuna", [], [("nazuna", "full")]),
    ("T4", "wolacz na starcie + 2. osoba ('Holo. Nie wiesz') → Holo (musi DALEJ dzialac)",
     "Holo. Nie wiesz kim jest Astra?powaznie?",
     0, None, [], [("holo", "full")]),
    ("T5", "wyliczanka imion ('A menma, nazuna, ktokolwiek') → Menma full + Nazuna aside",
     "A menma, nazuna, ktokolwiekM",
     0, None, [], [("menma", "full"), ("nazuna", "aside")]),
    ("T6", "przekierowanie 'Mowilem do nazuny' → Nazuna (mimo dopelniacza)",
     "A ty znowu nie spisz? Mowilem do nazuny",
     0, "holo", [], [("nazuna", "full")]),
    ("T7", "nikt nie wolany, start sesji → pick_primary (rotacja)",
     "Dzien dobry",
     11, None, [], [("holo", "full")]),

    # --- syntetyki ---
    ("S1", "wolacz odmieniony 'Nazuno, chodz' → Nazuna",
     "Nazuno, chodz tu na chwile", 14, None, [], [("nazuna", "full")]),
    ("S2", "wolacz-pytanie 'Menmus?' → Menma",
     "Menmus?", 14, None, [], [("menma", "full")]),
    ("S3", "adres do Holo + wzmianka Menmy ('Holo, powiedz Menmie...') → tylko Holo",
     "Holo, powiedz Menmie ze wszystko gra", 14, None, [], [("holo", "full")]),
    ("S4", "sama wzmianka BEZ lepkosci ('menma spi juz?') → pick_primary, Menma NIE budzi sie",
     "menma spi juz?", 14, None, ["nazuna"], [("holo", "full")]),
    ("S5", "lepkosc + silna emocja ('boli mnie brzuch') → Nazuna full + Menma aside",
     "boli mnie brzuch znowu", 1, "nazuna", [], [("nazuna", "full"), ("menma", "aside")]),
    ("S6", "noc, start → Nazuna (pora)",
     "co tam slychac", 23, None, [], [("nazuna", "full")]),
    ("S7", "LEPKOSC bije PORE: rozmowa z Holo o 23 → dalej Holo (nie Nazuna)",
     "no wiec jak myslisz", 23, "holo", [], [("holo", "full")]),
    ("S8", "tech, start → Holo (sygnal)",
     "jak stoimy z projektem ldi", 14, None, [], [("holo", "full")]),
    ("S9", "adres do grupy ('dziewczyny co myslicie') → wszystkie trzy",
     "dziewczyny co myslicie o tym", 14, "nazuna", [], [("holo", "full"), ("menma", "aside"), ("nazuna", "aside")]),

    # --- W1–W7: WYGASANIE LEPKOSCI (audyt 2026-07-28) ---
    # Przypadki modeluja realny wzorzec z logow: 26.07 dwanascie tur z rzedu Holo,
    # w tym przerwa 14:25 -> 19:30, ktorej lepkosc nie przetrwala w projekcie, a przetrwala w kodzie.
    ("W1", "lepkosc TRZYMA ponizej progu (5 tur, rozmowa ciagla) → dalej Holo",
     "no i co dalej", 14, "holo", ["holo"], [("holo", "full")], 5, 2.0),
    ("W2", "lepkosc WYGASA na progu (6 tur) → rotacja, Holo WYKLUCZONA",
     "no i co dalej", 14, "holo", ["holo"], [("menma", "full")], 6, 2.0),
    ("W3", "monokultura 26.07 (12 tur Holo, dzien) → ustepuje, nie Holo",
     "hej jak dzien wasz", 16, "holo", ["holo"], [("menma", "full")], 12, 3.0),
    ("W4", "wygasniecie 'turns' w NOCY → Nazuna moze wziac warte (nie jest wykluczona)",
     "no i co dalej", 23, "holo", ["holo"], [("nazuna", "full")], 8, 2.0),
    ("W5", "wygasniecie 'turns' gdy prowadzila NAZUNA w nocy → wyklucz ja, mimo pory",
     "no i co dalej", 23, "nazuna", ["nazuna"], [("holo", "full")], 8, 2.0),
    ("W6", "PRZERWA 5h (log 26.07 14:25->19:30) → swiezy pick, lepkosc zapomniana",
     "hej jak dzien wasz", 19, "holo", ["holo"], [("menma", "full")], 3, 305.0),
    ("W7", "przerwa 5h W NOCY → pora decyduje od nowa, ta sama siostra dozwolona",
     "hej", 23, "nazuna", ["nazuna"], [("nazuna", "full")], 3, 305.0),
    ("W8", "wolacz PRZELAMUJE wygasla lepkosc tak samo jak swieza",
     "Holo, chodz tu", 14, "menma", ["menma"], [("holo", "full")], 20, 500.0),
]


def run():
    passed, failed = 0, 0
    for case in CASES:
        cid, desc, msg, hour, last, recent, expected = case[:7]
        sticky_turns = case[7] if len(case) > 7 else 0
        gap_min = case[8] if len(case) > 8 else 0.0
        res = R.route(msg, hour=hour, last_full_speaker=last, recent=list(recent),
                      sticky_turns=sticky_turns, minutes_since_last=gap_min)
        got = res["routing"]
        ok = got == expected
        if ok:
            passed += 1
            print(f"  [PASS] {cid}: {got}")
        else:
            failed += 1
            print(f"  [FAIL] {cid}: {desc}")
            print(f"         msg      = {msg!r}")
            print(f"         expected = {expected}")
            print(f"         got      = {got}   (reason={res['reason']}, addressed={res['addressed']}, mentioned={res['mentioned']})")
    print(f"\n=== {passed}/{passed+failed} PASS ===")
    return failed == 0


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
