"""Kosmetyka odpowiedzi (2026-11-13).

Łukasz 13.11: „niech nie piszą tego długiego myślnika, bo siara”. Długi myślnik (U+2014) wygląda jak
tekst z modelu, a nie od osoby. Prośba w prompcie nie daje pewności, więc podmieniamy go deterministycznie
po odpowiedzi modelu, ZANIM trafi do sesji: historia przestaje wtedy uczyć model myślników.

Czysta funkcja, bez zależności. Flaga per pokój jest w main.py (`BEZ_DLUGIEGO_MYSLNIKA`).
Krótki myślnik „–” i łącznik „-” zostają bez zmian.
"""
from __future__ import annotations

import re

_MYSLNIK = re.compile(r"[ \t]*—[ \t]*")
_NA_POCZATKU = re.compile(r"(?m)^ - ")


def bez_dlugiego_myslnika(tekst: str) -> str:
    """„słowo — słowo” i „słowo—słowo” → „słowo - słowo”; „— Hej” na początku linii → „- Hej”."""
    if not tekst or "—" not in tekst:
        return tekst
    return _NA_POCZATKU.sub("- ", _MYSLNIK.sub(" - ", tekst))
