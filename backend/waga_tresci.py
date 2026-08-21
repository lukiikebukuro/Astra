# -*- coding: utf-8 -*-
"""
Detektor SYGNAŁU WAGI w treści wiadomości — jedna prawda dla całego systemu.

Po co osobny moduł: ten sam detektor decyduje o dwóch rzeczach w dwóch różnych
miejscach pipeline'u, a nie może być zduplikowany, bo rozjazd byłby niewidoczny.
  1. `semantic_pipeline` — czy krótka wiadomość omija bramki długości
  2. `vector_store.compute_persistence` — czy wspomnienie jest trwałe na zawsze

DLACZEGO Z TREŚCI, A NIE Z `importance` (ustalone 2026-08-19):
pierwotnie trwałość miała zależeć od `importance >= 8`. Sprawdzenie na 4697 realnych
wektorach pokazało, że ten wskaźnik jest niewiarygodny — ekstraktor przyznawał 10/10
zdaniom „Dzisiaj pilem czarna herbatke", „Pospalem sobie dzisiaj" i „To gowno na twarzy
znika powoli". Migracja oparta na `importance` uczyniłaby 107 śmieciowych wpisów
nieśmiertelnymi, odtwarzając monokulturę usuniętą podczas detoksu w lipcu.

Treść jest wiarygodna, bo pisze ją Łukasz. Ocena wagi — nie, bo robi ją model.
"""
import re as _re
import unicodedata as _ud

# Rdzenie, nie pełne formy (Łukasz odmienia i pisze bez ogonków).
RDZENIE_WAGI = (
    # więź
    "kocham", "kocha cie", "tesknie", "przepraszam", "dziekuje ci",
    # zdrowie — to jest jego biografia, nie bieżący stan
    "crohn", "stelar", "rinvoq", "bauhin", "zastawk", "operacj", "biopsj",
    "kolonoskop", "wycink", "resekcj", "przetok", "zwezen",
    # substancje
    "mefedron", "mefek", "kreske", "odstawien",
    # kryzys
    "placze", "plakalem", "boje sie", "balem sie", "panik", "zalamany",
    "nie daje rady", "nie mam sily", "mam dosc",
    # zobowiązania wobec siebie
    "obiecuje", "przysiegam", "nie bede cpal", "nie bede pil", "nie bede kupowal",
    "dalem slowo", "slowo honoru",
)
# Krótkie i wieloznaczne — tylko jako całe słowa, żeby nie łapać fragmentów
# (wzorzec błędu z CLAUDE.md: „zle mi" łapało „Źle mikrofon zrozumiał").
WZORZEC_WAGI = _re.compile(
    r"\b(kocham|kocham cie|kocham cię|umrzec|umre|umrę|smierc|śmierć|kcb|"
    r"marzenie|marze|marzę)\b"
)


def fold(s: str) -> str:
    """Bez ogonków, lowercase — Łukasz pisze bez diakrytyków."""
    s = (s or "").lower()
    return "".join(c for c in _ud.normalize("NFD", s) if _ud.category(c) != "Mn")


def ma_sygnal_wagi(tekst: str) -> bool:
    """Czy treść niesie wagę, której nie wolno stracić ani wygasić."""
    t = fold(tekst)
    if not t.strip():
        return False
    return any(k in t for k in RDZENIE_WAGI) or bool(WZORZEC_WAGI.search(t))


# ── AKRONIMY I NAZWY WŁASNE — kanał leksykalny (2026-08-21) ────────────────────
# Pomiar, który to wymusił: „opowiedz o ldi" → ZERO wpisów o LDI w puli 30 kandydatów,
# przy 60 takich wpisach w bazie. Te same dane, inne sformułowanie:
#     „Lost Demand Intelligence"              → 2 trafienia
#     „system wykrywania utraconych intencji" → 2 trafienia
# Model embeddingowy tokenizuje trzyliterowy skrót na bezsensowne kawałki, więc podobieństwo
# do wpisów o LDI jest bliskie zeru.
#
# To KORYGUJE decyzję z 15.08, gdzie BM25 zdegradowaliśmy po teście ze słowem „mefedron"
# (d=0.217, pierwsze miejsce). Tamten wniosek był prawdziwy dla rzadkich SŁÓW i fałszywy
# dla AKRONIMÓW: „mefedron" istnieje w słowniku modelu, „LDI" nie istnieje wcale.
#
# Łukasz mówi o swoich rzeczach skrótami, więc to nie jest przypadek brzegowy.
NAZWY_WLASNE = (
    "ldi", "anima", "astra", "amelia", "skankran", "holo", "menma", "nazuna",
    "kcb", "gwiazdka", "crohn", "stelara", "rinvoq", "bauhin", "chroma", "runway",
    "vps", "rag", "mmr", "pwa", "tiktok", "gemini",
)
_STOP_KROTKIE = {
    "co", "to", "on", "ma", "mi", "ci", "we", "za", "no", "ok", "tak", "nie", "jak",
    "czy", "juz", "gdy", "bo", "sie", "byl", "jest", "mam", "masz", "moj", "twoj",
    "ten", "ta", "te", "tam", "tu", "az", "ze", "od", "do", "na", "po", "w", "z", "i", "a", "o",
}


def wykryj_akronimy(zapytanie: str) -> list:
    """
    Zwraca tokeny, ktorych embedding prawdopodobnie nie rozumie - do wyszukania doslownego.

    Dwie drogi: znana nazwa wlasna (pewna) albo heurystyka "krotkie i ubogie w samogloski"
    (lapie nieznane skroty typu xyz, b2b). Stopwordy odsiane, zeby "co" i "jak" nie odpalaly
    wyszukiwania pelnotekstowego przy kazdej wiadomosci.
    """
    t = fold(zapytanie or "")
    tokeny = _re.findall(r"[a-z0-9]+", t)
    out = []
    for tok in tokeny:
        if tok in _STOP_KROTKIE:
            continue
        if tok in NAZWY_WLASNE:
            out.append(tok)
            continue
        # <=4 znaki, nie <=5: przy 5 przechodzilo "czyms" i podobne polskie slowa
        if 2 <= len(tok) <= 4 and sum(c in "aeiou" for c in tok) <= 1:
            out.append(tok)
    return list(dict.fromkeys(out))[:3]
