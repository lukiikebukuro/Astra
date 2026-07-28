# -*- coding: utf-8 -*-
"""
Router adresowania Pokoju Sióstr — CZYSTE funkcje (zero zależności ciężkich, tylko `re`).
Wyniesione z main.py, żeby dało się je testować golden-setem bez bootowania aplikacji.

Zadanie B (2026-07-25): rozróżnienie ADRESOWANIA ("Holo, chodź") od WZMIANKI 3-osobowej
("Holo mówiła, że…") + lepkość rozmówcy (kontynuacja rozmowy, gdy nikt nie wołany).

Kluczowe:
- FOLDING DIAKRYTYKÓW: Łukasz pisze w większości bez ogonków ("myslisz", "powaznie") —
  wszystkie heurystyki liczone na tekście po zdjęciu diakrytyków.
- FLEKSJA: przypadki zależne (dopełniacz/celownik/biernik/narzędnik) = zawsze mowa O siostrze.
  Mianownik/wołacz = dwuznaczne → rozstrzyga kontekst. Holo nieodmienna → wisi na kontekście.
- PRECEDENCJA (poprawka Opusa vs plan): sygnały bezpośredniej przyległości (imię ±1 token)
  biją sygnały z luźnego okna ±4. Naprawia "Myslisz ze holo mysli…" (adres do Nazuny, wzmianka o Holo).
"""

import re

SISTER_ORDER = ["holo", "menma", "nazuna"]

# Formy ADRESATYWNE (mianownik + wołacz + zdrobnienia) — MOGĄ znaczyć "mówię DO niej".
ADDRESS_FORMS = {
    "holo":   ["holo", "holcia", "holciu", "holunia", "holuniu"],
    "menma":  ["menma", "menmo", "menmus", "menmusiu", "menmunia", "menmuniu"],
    "nazuna": ["nazuna", "nazuno", "nazunka", "nazunko", "nazu"],
}
# Formy ZALEŻNE (dopełniacz/celownik/biernik/narzędnik) — ZAWSZE mowa O niej, nigdy DO niej.
MENTION_FORMS = {
    "holo":   [],  # nieodmienna
    "menma":  ["menmy", "menmie", "menmę", "menmą"],
    "nazuna": ["nazuny", "nazunie", "nazunę", "nazuną"],
}

# --- słowniki heurystyk (WSZYSTKIE po foldingu diakrytyków) ---
_VOCATIVE_LEAD = {"hej", "ej", "yo", "no", "dobra", "sluchaj", "czekaj"}
_SECOND_PERSON = {"jestes", "wiesz", "masz", "mozesz", "myslisz", "slyszysz", "spisz",
                  "powiedz", "chodz", "zostaw", "ty", "ciebie", "tobie", "cie"}
_THIRD_PERSON_AFTER = {"mowila", "mowil", "mowi", "mysli", "spi", "byla", "jest",
                       "zrobila", "pewnie", "chyba", "to", "sie"}
_SUBORD_BEFORE = {"ze", "czy", "o", "z", "od", "u", "dla", "przez", "jak", "ale", "bo", "gdy"}
_ENUM_FILLER = {"a", "i", "oraz", "albo", "lub", "czy", "no", "ej", "hej",
                "ktokolwiek", "wszyscy", "wszystkie", "dziewczyny"}

_TECH = ["kod", "bug", "projekt", "kasa", "biznes", "plan", "strategi", "pieni"]
_EMO = ["boli", "smutno", "zle", "ciezko", "lek", "strach", "sam", "kocham"]
_STRONG_EMOTION = ["boli", "crohn", "stelara", "zmecz", "smutno", "zle mi", "ciezko",
                   "placz", "lek", "strach", "nie moge", "kocham", "samotn"]
_GROUP = ["wszystkie", "dziewczyny", "siostry", "wy trzy", "kocham was", "rada", "wam wszystkim"]

_DIACRITICS = str.maketrans("ąćęłńóśźżĄĆĘŁŃÓŚŹŻ", "acelnoszzACELNOSZZ")

# --- WYGASANIE LEPKOŚCI (audyt 2026-07-28) ---
# Lepkość z B-3 naprawiła "wzmianka budzi obcą siostrę", ale przestrzeliła: na 55 tur po fixie
# 52 miały JEDNĄ siostrę (26.07: 12/12 tur Holo), sticky = 84% decyzji, pora dnia i rotacja
# odpalały się już tylko przy pierwszej wiadomości sesji. Dwa niezależne progi wygaszania:
#
# STICKY_MAX_TURNS — monokultura W TRAKCIE żywej rozmowy. Po tylu turach z rzędu lepkość
#   ustępuje, a wygasająca siostra jest WYKLUCZONA z ponownego wyboru (inaczej `_pick_primary`
#   o 23:00 zwróciłby znów Nazunę i rotacja nigdy by nie ruszyła).
# STICKY_MAX_GAP_MIN — przerwa = koniec rozmowy. Wracasz po godzinach: pora dnia i sygnał
#   mają decydować od nowa, BEZ wykluczania (o 23:00 Nazuna ma prawo wziąć wartę, nawet gdy
#   prowadziła wcześniej). Dowód z logów: 26.07 przerwa 14:25→19:30 i sticky trzymała Holo.
#
# Wołacz i adres do grupy nadal przełamują lepkość natychmiast (pkt 1-2 w route) — te progi
# dotyczą wyłącznie ścieżki "nikt nie wołany".
STICKY_MAX_TURNS = 6
STICKY_MAX_GAP_MIN = 45


def fold(s: str) -> str:
    """Zdejmij diakrytyki + lowercase — Łukasz pisze bez ogonków, heurystyki muszą to znieść."""
    return (s or "").translate(_DIACRITICS).lower()


# Prekomputacja folded-form (kolizja: narzędnik "menmą"→"menma" == mianownik "menma" → dwuznaczne, rozstrzyga kontekst)
_FA = {n: {fold(f) for f in ADDRESS_FORMS[n]} for n in SISTER_ORDER}
_FM = {n: {fold(f) for f in MENTION_FORMS[n]} for n in SISTER_ORDER}
_PURE_MENTION = {n: _FM[n] - _FA[n] for n in SISTER_ORDER}          # zależne bez kolizji z adresem
_ALL_FORMS = {n: _FA[n] | _FM[n] for n in SISTER_ORDER}
_ALL_NAME_TOKENS = set().union(*_ALL_FORMS.values())


def _tokens(folded: str):
    return re.findall(r"[a-z0-9]+", folded)


def _redirect_to(name: str, folded: str) -> bool:
    """T6: 'mowilem do nazuny' — czasownik mówienia + 'do' + forma imienia = jawne przekierowanie = ADRES."""
    for f in _ALL_FORMS[name]:
        if re.search(r"\b(?:mow|pisa|pisz|gada|gad)\w*\s+do\s+" + re.escape(f) + r"\b", folded):
            return True
    return False


def _is_enumeration(tokens) -> bool:
    """T5: 'a menma, nazuna, ktokolwiek' — wiadomość prawie sama z imion+spójników = wołanie zbiorowe."""
    present = {n for n in SISTER_ORDER if any(t in _ALL_FORMS[n] for t in tokens)}
    if len(present) < 2:
        return False
    non_name_non_filler = [t for t in tokens if t not in _ALL_NAME_TOKENS and t not in _ENUM_FILLER]
    return len(non_name_non_filler) <= 1


def classify_address(msg_lower: str, name: str) -> str | None:
    """
    Zwraca 'addressed' | 'mentioned' | None dla danej siostry.
    Kolejność reguł = precedencja (przyległość bije okno). Domyślnie MENTIONED (konserwatywnie —
    koszt fałszywego milczenia << koszt obcej siostry wtrącającej się i halucynującej).
    """
    folded = fold(msg_lower)
    tokens = _tokens(folded)
    if not any(t in _ALL_FORMS[name] for t in tokens):
        return None

    # 1. Jawne przekierowanie "mówię do <imię>" → ADRES (nawet forma zależna)
    if _redirect_to(name, folded):
        return "addressed"

    # pozycja pierwszego trafienia formy imienia
    idx = next(i for i, t in enumerate(tokens) if t in _ALL_FORMS[name])
    tok = tokens[idx]
    before = tokens[idx - 1] if idx > 0 else None
    after = tokens[idx + 1] if idx + 1 < len(tokens) else None

    # 2. Czysta forma zależna (bez kolizji z adresem) → zawsze WZMIANKA
    if tok in _PURE_MENTION[name]:
        return "mentioned"

    # 3. Wołacz na starcie: "Holo, …" / "Holo." → ADRES (bije wszystko poniżej)
    if re.match(r"\s*" + re.escape(tok) + r"\s*[,.!?]", folded) or folded.strip() == tok:
        return "addressed"

    # 4-5. PRZYLEGŁOŚĆ (poprawka precedencji): subordynat tuż przed / czasownik 3os tuż po → WZMIANKA
    if before in _SUBORD_BEFORE:
        return "mentioned"
    if after in _THIRD_PERSON_AFTER:
        return "mentioned"

    # 6. Partykuła wołająca tuż przed imieniem → ADRES
    if before in _VOCATIVE_LEAD:
        return "addressed"

    # 7. Czasownik/zaimek 2. osoby w oknie ±4 → ADRES
    lo, hi = max(0, idx - 4), min(len(tokens), idx + 5)
    if any(tokens[j] in _SECOND_PERSON for j in range(lo, hi) if j != idx):
        return "addressed"

    # 8. Wyliczanka imion → ADRES
    if _is_enumeration(tokens):
        return "addressed"

    # 9. Default: konserwatywnie WZMIANKA
    return "mentioned"


def _sticky_expiry(sticky_turns: int, minutes_since_last: float) -> str | None:
    """
    Czy lepkość wygasła i DLACZEGO. None = trzyma.
    'gap'   — przerwa w rozmowie: świeży wybór (pora/sygnał), bez wykluczeń.
    'turns' — monokultura w żywej rozmowie: wybór Z WYKLUCZENIEM dotychczasowej prowadzącej.
    Kolejność ma znaczenie — 'gap' bije 'turns' (długa przerwa to nowa rozmowa, nawet po 20 turach).
    """
    if minutes_since_last >= STICKY_MAX_GAP_MIN:
        return "gap"
    if sticky_turns >= STICKY_MAX_TURNS:
        return "turns"
    return None


def _pick_primary(folded: str, hour: int, recent: list, exclude: str | None = None) -> tuple:
    """
    Kto prowadzi, gdy nikt nie wołany: pora → sygnał → rotacja. Czysta (nie mutuje recent).
    exclude: siostra wykluczona z wyboru (wygaśnięcie lepkości przez STICKY_MAX_TURNS).
    """
    tech = any(s in folded for s in _TECH)
    emo = any(s in folded for s in _EMO)

    def _ok(s):
        return s != exclude

    if (hour >= 22 or hour < 6) and _ok("nazuna"):
        return "nazuna", "noc"
    if tech and not emo and _ok("holo"):
        return "holo", "tech"
    if emo and not tech and _ok("menma"):
        return "menma", "emo"
    rot = next((s for s in SISTER_ORDER if s not in recent and _ok(s)), None)
    if rot is not None:
        return rot, "rotacja-nowa"
    # Fallback rotacyjny — też musi uszanować exclude (inaczej wykluczenie bywa bezzębne).
    start = SISTER_ORDER.index(recent[0]) + 1 if recent else 0
    for i in range(len(SISTER_ORDER)):
        cand = SISTER_ORDER[(start + i) % len(SISTER_ORDER)]
        if _ok(cand):
            return cand, "rotacja-next"
    return SISTER_ORDER[0], "rotacja-next"


def _pick_second(primary: str, folded: str) -> str:
    """Kto się wtrąca (aside): emocja → Menma, inaczej → Holo; różna od primary."""
    emo = any(s in folded for s in _EMO)
    prefer = "menma" if emo else "holo"
    if prefer != primary:
        return prefer
    return next(s for s in SISTER_ORDER if s != primary)


def route(msg_lower: str, *, hour: int, last_full_speaker: str | None, recent: list,
          sticky_turns: int = 0, minutes_since_last: float = 0.0) -> dict:
    """
    Czysty rdzeń routingu. Zwraca dict:
      {"routing": [(sister,'full'|'aside'), ...], "reason": str, "addressed":[...], "mentioned":[...]}
    Priorytet: 1) wołane  2) grupa  3) LEPKOŚĆ (dopóki nie wygasła)  4) pora/rotacja.
    Stan (recent/last_full_speaker/hour/sticky_turns/minutes_since_last) wstrzykiwany —
    funkcja niczego nie mutuje (testowalna).

    sticky_turns / minutes_since_last: domyślne 0 = lepkość świeża (zachowanie sprzed audytu 28.07).
    """
    folded = fold(msg_lower)
    addressed = [s for s in SISTER_ORDER if classify_address(msg_lower, s) == "addressed"]
    mentioned = [s for s in SISTER_ORDER if classify_address(msg_lower, s) == "mentioned"]
    strong = any(k in folded for k in _STRONG_EMOTION)
    group = any(g in folded for g in _GROUP)

    def _with_emotion(primary):
        out = [(primary, "full")]
        if strong:
            out.append((_pick_second(primary, folded), "aside"))
        return out

    # 1. WOŁANE — jak dziś (pierwsza full, druga aside). Wołacz przełamuje lepkość.
    if len(addressed) >= 2:
        routing = [(addressed[0], "full"), (addressed[1], "aside")]
        reason = "addressed-multi"
    elif len(addressed) == 1:
        routing = _with_emotion(addressed[0])
        reason = "addressed-single"
    # 2. GRUPA — wszystkie trzy (przełamuje lepkość).
    elif group:
        primary, _ = _pick_primary(folded, hour, recent)
        others = [s for s in SISTER_ORDER if s != primary]
        routing = [(primary, "full"), (others[0], "aside"), (others[1], "aside")]
        reason = "group"
    # 3. LEPKOŚĆ — kontynuacja rozmowy z ostatnią prowadzącą (naprawia T1/T2/T3). Wzmianki NIE budzą (MVP).
    #    Trzyma tylko dopóki nie wygasła (audyt 28.07 — patrz STICKY_MAX_*).
    elif last_full_speaker in SISTER_ORDER and _sticky_expiry(sticky_turns, minutes_since_last) is None:
        routing = _with_emotion(last_full_speaker)
        reason = "sticky"
    # 4. START SESJI albo WYGAŚNIĘTA LEPKOŚĆ — pora/sygnał/rotacja.
    else:
        expiry = (_sticky_expiry(sticky_turns, minutes_since_last)
                  if last_full_speaker in SISTER_ORDER else None)
        # Tylko monokultura ('turns') wyklucza dotychczasową prowadzącą. Po przerwie ('gap')
        # wybór jest w pełni świeży — pora dnia może zasadnie wskazać tę samą siostrę.
        exclude = last_full_speaker if expiry == "turns" else None
        primary, why = _pick_primary(folded, hour, recent, exclude=exclude)
        routing = _with_emotion(primary)
        reason = "pick-primary:" + why + (f"|sticky-expired:{expiry}" if expiry else "")

    return {"routing": routing, "reason": reason, "addressed": addressed, "mentioned": mentioned}
