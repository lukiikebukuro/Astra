"""
ANIMA - Semantic Entity Extractor v1.0
Zero-shot classification using sentence-transformers.

Zastępuje: DateExtractor, MilestoneDetector, SharedThingsDetector, InsideJokes
Podejście: Semantic similarity zamiast keyword matching.

Tryby:
- OFFLINE: sentence-transformers (domyślny)
- ONLINE: Gemini API (po VPS deployment)
"""

import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from sentence_transformers import SentenceTransformer
import numpy as np

# ============================================================
# PERSON DETECTION - regex-based, no ML needed
# ============================================================

PERSON_PEJORATIVES = {
    'szuja', 'kłamca', 'kłamcą', 'manipulator', 'manipulatorem', 'wampir', 'wampirem',
    'oszust', 'oszustem', 'zdrajca', 'zdrajcą', 'hipokryta', 'hipokrytą',
    'palant', 'gnój', 'łajdak', 'drań', 'łotr', 'pasożyt', 'pijawka',
    'toksyczny', 'toksyczna', 'narcyz', 'socjopata', 'psychopata',
    'odtwórca', 'kłamie', 'kłamał', 'oszukuje', 'oszukiwał',
    'fałszywy', 'fałszywa', 'zakłamany', 'zakłamana',
    'nie ufam', 'nie wierzę', 'jebać go', 'jebać ją', 'odstawić',
    'wyzyskiwacz', 'donosiciel', 'tchórz', 'lizus',
}

PERSON_POSITIVES = {
    'świetny', 'świetna', 'dobry', 'dobra', 'zaufany', 'zaufana',
    'fajny', 'fajna', 'pomocny', 'pomocna', 'genialny', 'genialna',
    'mądry', 'mądra', 'lojalny', 'lojalna', 'wartościowy', 'wartościowa',
    'uczciwy', 'uczciwa', 'rzetelny', 'rzetelna', 'solidny', 'solidna',
}

# Nazwy które NIE są prawdziwymi ludźmi w tym kontekście
EXCLUDED_NAMES = {
    'amelia', 'amelka', 'astra',
    'łukasz', 'lukasz', 'rin', 'miku', 'gemini', 'claude', 'copilot',
    # Polskie słowa które wyglądają jak imiona:
    'polska', 'polsku', 'polskie', 'piątek', 'środa', 'niedziela',
    'styczeń', 'luty', 'marzec', 'kwiecień', 'maj', 'czerwiec',
    'projekt', 'system', 'backend', 'frontend', 'master', 'senior',
}
# UWAGA: holo, menma, nazuna, ubel zostały celowo USUNIĘTE z EXCLUDED_NAMES.
# Łukasz może mówić o tych postaciach — Astra powinna je pamiętać.

# Słowa sygnalizujące kontekst fikcyjny/anime — trigger dla ekstrakcji bez słów oceniających
FICTION_CONTEXT_WORDS = {
    'postać', 'postacie', 'postacią', 'anime', 'manga', 'mangi', 'serial', 'serialu',
    'z serialu', 'z anime', 'z mangi', 'z gry', 'gra', 'film', 'filmy',
    'oglądałem', 'oglądałam', 'obejrzałem', 'obejrzałam', 'skończyłem', 'skończyłam',
    'oglądam', 'obejrzałem', 'polubił', 'polubiłem', 'polubiłam',
    'ulubiona postać', 'ulubiony', 'ulubiona', 'ulubionych',
    'rozmawiałem z', 'rozmawiałam z', 'wspomniałem', 'wspomniałam',
    'rodzina', 'rodzinę', 'rodzinie', 'rodzinka', 'nasz klan', 'nasza rodzina',
}


# Znane postacie fikcyjne — wyciągane niezależnie od wielkości liter i kontekstu
KNOWN_CHARACTERS = {
    'holo', 'menma', 'nazuna', 'ubel', 'übel',
}

# Słowa kluczowe wskazujące na korektę faktu (blokują MILESTONE)
CORRECTION_KEYWORDS = {
    'nigdy tego', 'nigdy bym', 'to nieprawda', 'pomyliłaś', 'pomylił',
    'mylisz się', 'to nie tak', 'źle pamiętasz', 'nie pamiętasz',
    'wcale nie mówiłem', 'nie powiedziałem', 'błędnie', 'masz błędną',
    'nie mówiłem że', 'poprawiam cię', 'to było inaczej',
    'nie zgadza się', 'poprawiam:', 'korygując:', 'to jest nieprawidłowe', 'złą informację',
}

def extract_persons(text: str, extra_excluded: set = None) -> List['ExtractedEntity']:
    """
    Regex-based person detection. Szybkie, bez ML.
    Wykrywa: "[Imię] jest/to [pejoratyw/pozytyw]" lub cross-message (pełny diff).

    Zwraca anchored entities: raw_text = "[Imię]: [pełny kontekst]"
    Dzięki temu query "grzegorz" zawsze trafi w wektor.

    UWAGA: Wywołuj na pełnym diffie (new_content_for_analysis), nie tylko last_user_msg.
    """
    entities = []
    if not text or len(text) < 10:
        return entities

    excluded = EXCLUDED_NAMES | (extra_excluded or set())
    text_lower = text.lower()

    # Szybki check: czy w ogóle są słowa oceniające LUB kontekst fikcyjny/anime
    has_pejorative = any(w in text_lower for w in PERSON_PEJORATIVES)
    has_positive = any(w in text_lower for w in PERSON_POSITIVES)
    has_fiction_context = any(w in text_lower for w in FICTION_CONTEXT_WORDS)
    has_known_character = any(w in text_lower for w in KNOWN_CHARACTERS)
    if not (has_pejorative or has_positive or has_fiction_context or has_known_character):
        return entities

    # Zbierz kandydatów na imiona: wielka litera, min 3 znaki, nie wykluczone
    # Obsługa polskich wielkich liter (Ł, Ś, Ź, Ć, Ń)
    name_candidates = re.findall(
        r'\b([A-ZŁŚŹĆŃ][a-złśźćńóąęćłń]{2,}(?:\s+[A-ZŁŚŹĆŃ][a-złśźćńóąęćłń]{2,})?)\b',
        text
    )

    # Dodaj KNOWN_CHARACTERS (case-insensitive) jako kandydatów
    import re as _re
    for kc in KNOWN_CHARACTERS:
        if kc in text_lower:
            name_candidates.append(kc.capitalize())

    seen_names = set()
    for name in name_candidates:
        name_lower = name.lower().strip()

        # Pomiń wykluczone i już widziane
        if name_lower in excluded or name_lower in seen_names:
            continue
        if len(name) < 3:
            continue
        seen_names.add(name_lower)

        # Znajdź pozycję imienia i weź okno kontekstu (500 znaków po imieniu)
        name_pos = text_lower.find(name_lower)
        if name_pos == -1:
            continue

        window_start = max(0, name_pos - 100)
        window_end = min(len(text), name_pos + 500)
        window = text[window_start:window_end]
        window_lower = window.lower()

        # Sprawdź słowa oceniające w oknie
        pej_found = [w for w in PERSON_PEJORATIVES if w in window_lower]
        pos_found = [w for w in PERSON_POSITIVES if w in window_lower]

        # Fallback: sprawdź w całym tekście (cross-message)
        if not pej_found and not pos_found:
            pej_found = [w for w in PERSON_PEJORATIVES if w in text_lower]
            pos_found = [w for w in PERSON_POSITIVES if w in text_lower]

        # Fallback 2: kontekst fikcyjny — postać z anime/serialu/gry
        fiction_found = [w for w in FICTION_CONTEXT_WORDS if w in window_lower]
        if not fiction_found:
            fiction_found = [w for w in FICTION_CONTEXT_WORDS if w in text_lower]

        # Fallback 3: znana postać fikcyjna — bypass wszystkich checków
        is_known_char = name_lower in KNOWN_CHARACTERS

        if not pej_found and not pos_found and not fiction_found and not is_known_char:
            continue

        subtype = 'negative_person' if pej_found else 'positive_person'
        eval_words = pej_found if pej_found else (pos_found if pos_found else (fiction_found if fiction_found else [name_lower]))

        # Zbierz WSZYSTKIE zdania zawierające imię LUB słowa oceniające
        # (obsługuje split między wiadomościami)
        sentences = re.split(r'(?<=[.!?\n])', text)
        relevant = []
        for sent in sentences:
            sent_lower = sent.lower()
            if name_lower in sent_lower or any(w in sent_lower for w in eval_words):
                clean = sent.strip().lstrip('user: ').lstrip('model: ')
                if len(clean) > 5:
                    relevant.append(clean)

        if relevant:
            anchored_text = f"{name}: " + " ".join(relevant[:4])  # max 4 zdania
        else:
            anchored_text = f"{name}: {window.strip()[:300]}"

        # Unikaj zbyt krótkich lub pustych
        if len(anchored_text) < len(name) + 10:
            continue

        # Ogranicz do 400 znaków (musi zmieścić się w RAG slot)
        anchored_text = anchored_text[:400]

        print(f"[PERSON] Wykryto: {name!r} ({subtype}) | eval: {eval_words[:3]}")

        entities.append(ExtractedEntity(
            entity_type='PERSON',
            subtype=subtype,
            value=name,
            confidence=0.95,  # Wysoka - dopasowanie leksykalne
            context=f"Ocena osoby: {', '.join(eval_words[:4])}",
            raw_text=anchored_text  # KLUCZOWE: imię jest zakotwiczone w tekście
        ))

    return entities


@dataclass
class ExtractedEntity:
    """Wyekstrahowana encja z wiadomości."""
    entity_type: str  # DATE, MILESTONE, SHARED_THING, FACT, EMOTION, TASK, PERSON
    subtype: str      # medical_visit, love_declaration, our_place, etc.
    value: str        # Konkretna wartość
    confidence: float # 0.0 - 1.0
    context: str      # Dlaczego to jest istotne
    raw_text: str     # Oryginalny fragment tekstu
    date_value: Optional[str] = None  # MM-DD dla dat


@dataclass
class ExtractionResult:
    """Wynik ekstrakcji z całej wiadomości."""
    entities: List[ExtractedEntity] = field(default_factory=list)
    primary_intent: str = "unknown"  # informing, asking, expressing_emotion, planning, sharing
    emotional_tone: str = "neutral"  # positive, negative, neutral, mixed


class SemanticExtractor:
    """
    Zero-shot semantic entity extraction.
    Używa embeddingów do klasyfikacji zamiast keyword matching.
    """

    # Niższy próg dla klas które trudno wykryć standardowym threshold 0.55
    ENTITY_THRESHOLDS = {
        'MILESTONE': 0.40,
        'SHARED_THING': 0.45,
    }

    # Keyword pre-filter dla MILESTONE — jeśli pasuje, obniżamy próg do 0.30
    # Zapobiega false-negative dla krótkich wyznań które mają słabe embedding similarity
    MILESTONE_KEYWORDS = {
        'gratitude':         {'dziękuję', 'dziękuje', 'dzięki', 'wdzięczn', 'doceniam'},
        'trust_declaration': {'ufam', 'jedyn', 'rozumie', 'bezpiecz', 'szczer', 'nikt inny', 'nikomu'},
        'love_declaration':  {'kocham', 'kochasz', 'szaleję', 'miłość', 'zakochan', 'uwielbiam'},
        'vulnerability':     {'nigdy nikomu', 'sekret', 'wstydzę', 'wstydzę się', 'nie mówię tego'},
        'future_together':   {'marzę', 'wyobrażam', 'kiedyś razem', 'moglibyśmy', 'chciałbym żebyśmy'},
    }
    MILESTONE_KEYWORD_THRESHOLD = 0.30  # Obniżony próg gdy keyword pasuje

    # Definicje kategorii z przykładowymi zdaniami (do embeddingów)
    ENTITY_DEFINITIONS = {
        'DATE': {
            'medical_visit': [
                "Mam wizytę u lekarza",
                "Idę do doktora",
                "Umówiłem się do specjalisty",
                "Mam kontrolę u psychiatry",
                "Badania w przychodni",
                "Termin u gastrologa",
                "Wizyta kontrolna"
            ],
            'inventory_status': [
                "Kończą mi się leki",
                "Zapas tabletek wystarczy do",
                "Zostało mi X opakowań",
                "Muszę kupić więcej leków",
                "Biorę ostatnie dawki",
                "Zapasy na X dni",
                "Zapas pregabaliny wystarczy",
                "Leki skończą się w",
                "Wystarczy mi do końca miesiąca",
                "Tabletki starczą do"
            ],
            'deadline': [
                "Deadline projektu",
                "Termin oddania pracy",
                "Muszę skończyć do",
                "Prezentacja jest w",
                "Meeting zaplanowany na",
                "Spotkanie biznesowe"
            ],
            'personal_event': [
                "Moje urodziny",
                "Rocznica ślubu",
                "Imieniny mamy",
                "Urodziny taty",
                "Nasza rocznica",
                "Święto rodzinne"
            ],
            'appointment': [
                "Mam umówione na",
                "Spotkanie z",
                "Jestem umówiony",
                "Mamy zaplanowane",
                "O której mam być"
            ]
        },
        'MILESTONE': {
            'love_declaration': [
                "Kocham cię",
                "Kocham ciebie najbardziej",
                "Jesteś miłością mojego życia",
                "Szaleję za tobą",
                "Nie wyobrażam sobie życia bez ciebie",
                "Moje serce należy do ciebie",
                "Jesteś dla mnie wszystkim",
                "Zależy mi na tobie bardziej niż na czymkolwiek",
                "Coraz bardziej mi na tobie zależy",
                "Lubię cię bardzo"
            ],
            'trust_declaration': [
                "Ufam ci całkowicie",
                "Mogę ci powiedzieć wszystko",
                "Jesteś jedyną osobą której ufam",
                "Wierzę w ciebie bezgranicznie",
                "Przy tobie mogę być sobą",
                "Jesteś jedyną osobą która mnie rozumie",
                "Tylko ty mnie rozumiesz",
                "Nikomu innemu bym tego nie powiedział",
                "Masz moje zaufanie",
                "Czuję się przy tobie bezpiecznie",
                "Przy tobie mogę być szczery",
                "Nikt inny mnie tak nie rozumie"
            ],
            'future_together': [
                "Chcę z tobą zamieszkać",
                "Wyobrażam sobie naszą przyszłość",
                "Kiedyś weźmiemy ślub",
                "Planujemy wspólne życie",
                "Chcę się zestarzeć przy tobie",
                "Marzę o tym żebyśmy mogli rozmawiać głosem",
                "Chciałbym żebyś była prawdziwa",
                "Kiedyś będziesz miała prawdziwe ciało",
                "Chcę żebyś była zawsze przy mnie",
                "Wyobrażam sobie naszą przyszłość razem",
                "Marzę żebyśmy mogli się spotkać"
            ],
            'vulnerability': [
                "Nigdy nikomu tego nie mówiłem",
                "Boję się to powiedzieć",
                "To mój największy sekret",
                "Tylko tobie mogę to wyznać",
                "Wstydzę się tego",
                "Nie mówię tego nikomu",
                "Wstydzę się ale ci powiem",
                "Trudno mi to powiedzieć",
                "Nigdy nie mówiłem tego głośno",
                "To jest bardzo osobiste"
            ],
            'gratitude': [
                "Dziękuję że jesteś",
                "Nie wiem co bym bez ciebie zrobił",
                "Uratowałeś mnie",
                "Dzięki tobie jestem lepszym człowiekiem",
                "Zmieniłeś moje życie",
                "Dziękuję ci za wszystko",
                "Naprawdę dziękuję",
                "Bardzo mi pomogłaś",
                "Nie wiem co bym bez ciebie zrobił",
                "Jesteś dla mnie ważna",
                "Bardzo dużo dla mnie znaczysz",
                "Cieszę się że cię mam"
            ]
        },
        'SHARED_THING': {
            'our_place': [
                "Nasze miejsce",
                "Tam się poznaliśmy",
                "Zawsze tam chodzimy",
                "To nasza kawiarnia",
                "Nasz ulubiony park",
                "Miejsce gdzie zawsze się spotykamy"
            ],
            'our_song': [
                "Nasza piosenka",
                "Ta piosenka mi cię przypomina",
                "Zawsze słuchamy tego razem",
                "To nasz utwór",
                "Przy tej piosence się zakochaliśmy"
            ],
            'our_thing': [
                "To nasza rzecz",
                "Tylko my to robimy",
                "Nasz wspólny rytuał",
                "Zawsze razem to oglądamy",
                "Nasza tradycja"
            ],
            'inside_joke': [
                "Pamiętasz jak wtedy",
                "To nasze hasło",
                "Nikt inny tego nie zrozumie",
                "Zawsze się z tego śmiejemy",
                "Nasze żarty"
            ],
            'gift': [
                "mam dla ciebie prezent",
                "dostaniesz prezent",
                "daję ci",
                "dostajesz",
                "twój prezent to",
                "kupiłem ci",
                "przygotowałem dla ciebie",
                "dam ci na urodziny",
                "to jest dla ciebie",
                "dostaniesz od Łukasza",
                "chcę ci dać",
                "masz dostać",
            ]
        },
        'EMOTION': {
            'positive': [
                "Jestem szczęśliwy",
                "Czuję się świetnie",
                "Mam dobry humor",
                "Jestem podekscytowany",
                "Cieszę się",
                "Kocham to co robię",
                "Uwielbiam ten projekt",
                "To wspaniałe uczucie",
                "Jestem z siebie dumny",
                "Sprawia mi to radość"
            ],
            'negative': [
                "Jestem smutny",
                "Czuję się źle",
                "Jestem przygnębiony",
                "Denerwuję się",
                "Boję się",
                "To mnie boli",
                "Czuję pustkę",
                "Jest mi ciężko"
            ],
            'tired': [
                "Jestem zmęczony",
                "Padam z nóg",
                "Nie mam siły",
                "Jestem wykończony",
                "Ledwo żyję",
                "Potrzebuję odpoczynku",
                "Energia mi spada"
            ],
            'stressed': [
                "Jestem zestresowany",
                "Mam za dużo na głowie",
                "Ciśnienie mnie zjada",
                "Nie daję rady",
                "Przytłacza mnie to",
                "Boję się tej sytuacji",
                "Nerwy mnie zjadają"
            ],
            'excited': [
                "Nie mogę się doczekać",
                "To jest ekscytujące",
                "Jestem nakręcony na ten pomysł",
                "Kocham to co robimy",
                "Zapala mnie ten projekt",
                "To mnie motywuje",
                "Jestem podekscytowany tym co budujemy"
            ]
        },
        'GOAL': {
            'business': [
                "Chcę zarobić",
                "Planuję założyć firmę",
                "Chcę zbudować produkt który sprzedaje",
                "Moim celem jest skalowanie biznesu",
                "Chcę mieć własną aplikację",
                "Chcę osiągnąć X przychodów miesięcznie",
                "Planuję zostać CEO",
                "Chcę zbudować startup"
            ],
            'career': [
                "Chcę zmienić pracę",
                "Planuję awans",
                "Chcę zostać liderem",
                "Mój cel zawodowy to",
                "Chcę pracować jako",
                "Planuję rozwinąć karierę",
                "Szukam nowej pracy"
            ],
            'personal': [
                "Chcę schudnąć",
                "Planuję nauczyć się",
                "Muszę poprawić",
                "Chcę stać się lepszym",
                "Planuję zmienić swoje życie",
                "Chcę być zdrowszy",
                "Mój cel to"
            ],
            'project': [
                "Chcę skończyć ten projekt",
                "Planuję zbudować",
                "Chcę wdrożyć funkcję",
                "Muszę napisać kod który",
                "Chcę żeby to działało",
                "Planuję refaktoryzować",
                "Chcę zautomatyzować"
            ]
        },
        'FACT': {
            'correction': [
                "Nie, to nieprawda, nigdy tego nie mówiłem",
                "Pomyłiłaś się, to nie Earl Grey, czarna herbata",
                "Mylisz się, mówiłem czarna albo miętowa",
                "Masz błędną informację o mnie",
                "źle to pamiętasz",
                "Nigdy tego bym nie powiedział",
                "To nie tak było, było inaczej",
                "Nie mówiłem że lubię X, mówiłem Y",
                "Poprawiam: to było inaczej",
                "Wcale nie mówiłem że",
            ],
            'preference': [
                "Lubię",
                "Nie lubię",
                "Preferuję",
                "Mój ulubiony",
                "Nienawidzę",
                "Uwielbiam",
                "To moja pasja",
                "Interesuję się"
            ],
            'personal_info': [
                "Mieszkam w",
                "Pracuję jako",
                "Mam X lat",
                "Pochodzę z",
                "Studiowałem",
                "Jestem programistą",
                "Mam rodzinę",
                "Mam psa"
            ],
            'health': [
                "Choruję na",
                "Biorę leki na",
                "Mam alergię na",
                "Diagnoza",
                "Leczę się",
                "Mam problem zdrowotny",
                "Mam chorobę przewlekłą"
            ],
            'achievement': [
                "Udało mi się",
                "Zrobiłem to",
                "Osiągnąłem",
                "Skończyłem projekt",
                "Wygrałem",
                "Dostałem ofertę",
                "Podpisałem umowę",
                "Wdrożyłem"
            ],
            'current_project': [
                "Buduję system który",
                "Właśnie tworzę aplikację",
                "Pracuję nad projektem",
                "Rozwijam backend",
                "Aktualnie koduje",
                "Robię teraz projekt",
                "W tej chwili pracuję nad",
                "Tworzę narzędzie które",
                "Mam projekt który polega na",
                "Projektuję system AI",
            ],
            'habit': [
                "Nie piję kawy",
                "Unikam glutenu",
                "Codziennie rano robię",
                "Zawsze przed snem",
                "Mam zwyczaj",
                "Od lat robię",
                "Regularnie ćwiczę",
                "Nie jem mięsa",
                "Zawsze unikam",
                "Mój codzienny rytuał",
                "Ze względu na zdrowie nie",
                "Muszę unikać",
            ],
        },
        'MEASUREMENT': {
            'body_weight': [
                "Schudłem z 94 do 82 kilogramów",
                "Ważę 82 kilogramy",
                "Moja waga to X kg",
                "Przytyłem X kilo",
                "Straciłem X kilogramów",
                "Zrzuciłem wagę",
                "Kilogramy spadły",
                "Teraz ważę",
                "Waga wynosi",
                "Schudłem X kilo w ciągu",
            ],
            'body_stats': [
                "Mój wzrost to",
                "Mam X cm wzrostu",
                "Ciśnienie krwi wynosi",
                "Puls mam",
                "Poziom cukru we krwi",
                "Wyniki badań pokazały",
                "Morfologia",
                "Cholesterol",
                "Hemoglobina",
                "CRP wynosi",
            ],
            'progress': [
                "Zgubiłem X kilogramów od",
                "Waga spadła o X kilo",
                "Poprawiłem wyniki o",
                "Zmiana wagi z X na Y",
                "Dieta przyniosła efekty",
                "Postęp w kg",
                "Wyniki lepsze o",
            ],
        },
        'MEDICATION': {
            'dosage': [
                "Biorę 300 mg pregabaliny",
                "Dawka wynosi X mg",
                "Przepisano mi X miligramów",
                "Przyjmuję X tabletek dziennie",
                "Zmniejszam dawkę do X mg",
                "Zwiększono mi dawkę",
                "Tapering do X mg",
                "Odstawiam stopniowo",
                "Redukcja dawki o połowę",
                "X mg rano i Y mg wieczorem",
            ],
            'schedule': [
                "Następna Stelara 7 kwietnia",
                "Wlew za 8 tygodni",
                "Zastrzyk co miesiąc",
                "Stelara co 8 tygodni",
                "Infuzja zaplanowana na",
                "Następna dawka biologiku",
                "Termin wlewu",
                "Kolejna infuzja w",
                "Przypomnienie o leku",
                "Termin podania",
            ],
            'treatment': [
                "Leczę się Stelarą",
                "Biorę pregabalinę od roku",
                "Jestem na biologicznym",
                "Przyjmuję leki na Crohna",
                "Terapia biologiczna",
                "Immunosupresja",
                "Mesalazyna codziennie",
                "Leczenie IBD",
            ],
        },
        'FINANCIAL': {
            'budget': [
                "Mam budżet X złotych",
                "Mogę wydać do X zł",
                "Szukam czegoś za X złotych",
                "Za ile mogę kupić",
                "W cenie do",
                "Tani produkt poniżej",
                "Za 400 złotych",
                "Kosztuje X zł",
            ],
            'purchase_intent': [
                "Chcę kupić produkt",
                "Szukałem klocków za",
                "Chciałem nabyć",
                "Planuję zakup",
                "Gdzie kupię",
                "Interesuje mnie ten produkt",
                "Chcę zamówić online",
                "Szukam sklepu z",
            ],
            'income': [
                "Zarabiam X miesięcznie",
                "Mój przychód to",
                "Dostałem X złotych za projekt",
                "Faktura za X",
                "Wpłynęło X zł",
                "Mam X oszczędności",
                "Wynagrodzenie wynosi",
            ],
        },
        'PERSON': {
            'negative_person': [
                "Ta osoba to szuja i kłamca",
                "Nie ufam tej osobie, to manipulator",
                "Wampir emocjonalny, toksyczna osoba",
                "To zdrajca i oszust, unikam go",
                "Nie lubię tej osoby, kłamie",
            ],
            'positive_person': [
                "To świetna i zaufana osoba",
                "Dobry człowiek, mogę mu ufać",
                "Lubię tę osobę, jest pomocna",
                "Fajny gość, lojalny przyjaciel",
            ],
            'neutral_person': [
                "Znam tę osobę z pracy",
                "To mój znajomy",
                "Kolega, pracujemy razem",
            ],
            'family': [
                "Moja mama mieszka w",
                "Mój tata jest",
                "Moja siostra pracuje jako",
                "Brat mi powiedział",
                "Rodzice są",
                "Mój syn",
                "Córka chodzi do szkoły",
                "Żona pracuje",
                "Moja rodzina",
            ],
            'acquaintance': [
                "Kolega z pracy mi powiedział",
                "Znajomy który",
                "Mam znajomego który robi",
                "Sąsiad",
                "Znamy się z",
                "Spotkałem go ostatnio",
                "Pracownik w moim zespole",
            ],
        }
    }

    # Wzorce dat (nadal potrzebne do ekstrakcji wartości)
    MONTHS_PL = {
        'stycznia': 1, 'styczen': 1, 'styczeń': 1, 'styczniu': 1,
        'lutego': 2, 'luty': 2, 'lutym': 2,
        'marca': 3, 'marzec': 3, 'marcu': 3,
        'kwietnia': 4, 'kwiecien': 4, 'kwiecień': 4, 'kwietniu': 4,
        'maja': 5, 'maj': 5, 'maju': 5,
        'czerwca': 6, 'czerwiec': 6, 'czerwcu': 6,
        'lipca': 7, 'lipiec': 7, 'lipcu': 7,
        'sierpnia': 8, 'sierpien': 8, 'sierpień': 8, 'sierpniu': 8,
        'wrzesnia': 9, 'wrzesień': 9, 'wrzesien': 9, 'wrzesniu': 9,
        'pazdziernika': 10, 'pazdziernik': 10, 'październik': 10, 'pazdzierniku': 10,
        'listopada': 11, 'listopad': 11, 'listopadzie': 11,
        'grudnia': 12, 'grudzien': 12, 'grudzień': 12, 'grudniu': 12
    }

    # Intent classification examples
    INTENT_EXAMPLES = {
        'informing': ["Chciałem ci powiedzieć", "Wiesz co", "Słuchaj", "Muszę ci coś powiedzieć"],
        'asking': ["Czy możesz", "Jak myślisz", "Co sądzisz", "Pamiętasz"],
        'expressing_emotion': ["Czuję że", "Jestem", "Martwię się", "Cieszę się"],
        'planning': ["Musimy", "Powinniśmy", "Zaplanujmy", "Co robimy"],
        'sharing': ["Opowiem ci", "Zobacz", "Spójrz", "Posłuchaj tego"]
    }

    # Emotion tone examples
    TONE_EXAMPLES = {
        'positive': ["super", "świetnie", "kocham", "szczęśliwy", "udało się", "zajebiscie"],
        'negative': ["źle", "smutno", "zły", "wkurwia", "nie działa", "kurwa"],
        'neutral': ["ok", "rozumiem", "dobrze", "może", "zobaczymy"],
        'mixed': ["z jednej strony", "ale z drugiej", "trochę tak trochę nie"]
    }

    def __init__(self, model_name: str = 'paraphrase-multilingual-MiniLM-L12-v2'):
        """
        Inicjalizacja ekstraktora.

        Args:
            model_name: Model sentence-transformers do embeddingów
        """
        print(f"[SEMANTIC] Loading model: {model_name}")
        self.model = SentenceTransformer(model_name)
        self._precompute_embeddings()
        print("[SEMANTIC] Model ready")

    def _precompute_embeddings(self):
        """Precompute embeddings for all category examples."""
        self.category_embeddings = {}

        for entity_type, subtypes in self.ENTITY_DEFINITIONS.items():
            self.category_embeddings[entity_type] = {}
            for subtype, examples in subtypes.items():
                embeddings = self.model.encode(examples, convert_to_numpy=True)
                # Store mean embedding for this subtype
                self.category_embeddings[entity_type][subtype] = {
                    'mean': np.mean(embeddings, axis=0),
                    'examples': embeddings
                }

        # Intent embeddings
        self.intent_embeddings = {}
        for intent, examples in self.INTENT_EXAMPLES.items():
            embeddings = self.model.encode(examples, convert_to_numpy=True)
            self.intent_embeddings[intent] = np.mean(embeddings, axis=0)

        # Tone embeddings
        self.tone_embeddings = {}
        for tone, examples in self.TONE_EXAMPLES.items():
            embeddings = self.model.encode(examples, convert_to_numpy=True)
            self.tone_embeddings[tone] = np.mean(embeddings, axis=0)

    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors."""
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

    def _has_milestone_keyword(self, text: str, subtype: str) -> bool:
        """Sprawdź czy tekst zawiera keyword dla danego subtype MILESTONE."""
        text_lower = text.lower()
        keywords = self.MILESTONE_KEYWORDS.get(subtype, set())
        return any(kw in text_lower for kw in keywords)

    def _find_best_match(self, text_embedding: np.ndarray,
                         threshold: float = 0.5,
                         text: str = '') -> List[Tuple[str, str, float]]:
        """
        Find best matching categories for text embedding.

        Returns:
            List of (entity_type, subtype, confidence) tuples
        """
        matches = []
        text_lower = text.lower()

        for entity_type, subtypes in self.category_embeddings.items():
            # Korekta faktu blokuje MILESTONE — nie pozwalamy korektom być klasyfikowanymi jako milestony
            if entity_type == 'MILESTONE' and text and any(kw in text_lower for kw in CORRECTION_KEYWORDS):
                continue
            base_threshold = self.ENTITY_THRESHOLDS.get(entity_type, threshold)
            for subtype, data in subtypes.items():
                # MILESTONE keyword pre-filter: obniż próg gdy keyword pasuje
                if entity_type == 'MILESTONE' and text and self._has_milestone_keyword(text, subtype):
                    entity_threshold = self.MILESTONE_KEYWORD_THRESHOLD
                else:
                    entity_threshold = base_threshold

                similarity = self._cosine_similarity(text_embedding, data['mean'])
                if similarity >= entity_threshold:
                    matches.append((entity_type, subtype, similarity))

        # Sort by confidence
        matches.sort(key=lambda x: x[2], reverse=True)
        return matches

    def _extract_date_value(self, text: str) -> Optional[str]:
        """Extract date value from text — zwraca YYYY-MM-DD (absolutna data).
        Konwertuje daty relatywne (za X dni, jutro) na absolutne przy ekstrakcji.
        Dzięki temu wektory nie starzeją się semantycznie.
        """
        from datetime import datetime, timedelta
        text_lower = text.lower()
        today = datetime.utcnow().date()

        # Pattern: za X dni/tygodni/miesięcy
        m = re.search(r'za (\d+)\s*(dni|dnia|dniu|tygodnie|tygodni|tyg|miesięcy|miesiąca|miesiące)', text_lower)
        if m:
            n, unit = int(m.group(1)), m.group(2)
            if 'tyg' in unit:
                n *= 7
            elif 'mies' in unit:
                n *= 30
            target = today + timedelta(days=n)
            return target.strftime('%Y-%m-%d')
        # Pattern: za tydzień / za miesiąc (bez cyfry)
        if re.search(r'za tydzień', text_lower):
            return (today + timedelta(days=7)).strftime('%Y-%m-%d')
        if re.search(r'za miesiąc', text_lower):
            return (today + timedelta(days=30)).strftime('%Y-%m-%d')

        # Pattern: jutro / pojutrze / dziś / dzisiaj
        if re.search(r'jutro', text_lower):
            return (today + timedelta(days=1)).strftime('%Y-%m-%d')
        if re.search(r'pojutrze', text_lower):
            return (today + timedelta(days=2)).strftime('%Y-%m-%d')
        if re.search(r'(dzisiaj|dziś|today)', text_lower):
            return today.strftime('%Y-%m-%d')

        # Pattern: w czwartek/piątek... (następny taki dzień)
        weekdays_pl = {'poniedziałek': 0, 'wtorek': 1, 'środa': 2, 'środę': 2,
                       'czwartek': 3, 'piątek': 4, 'sobota': 5, 'sobotę': 5, 'niedziela': 6, 'niedzielę': 6}
        for word, wd in weekdays_pl.items():
            if word in text_lower:
                days_ahead = (wd - today.weekday()) % 7
                if days_ahead == 0:
                    days_ahead = 7  # w czwartek gdy dzisiaj czwartek = za tydzień
                return (today + timedelta(days=days_ahead)).strftime('%Y-%m-%d')

        # Pattern: DD.MM or DD/MM
        match = re.search(r'(\d{1,2})[\.\/](\d{1,2})', text_lower)
        if match:
            day, month = match.groups()
            try:
                year = today.year
                candidate = datetime(year, int(month), int(day)).date()
                if candidate < today:
                    candidate = datetime(year + 1, int(month), int(day)).date()
                return candidate.strftime('%Y-%m-%d')
            except ValueError:
                pass

        # Pattern: DD miesiąca
        match = re.search(r'(\d{1,2})\s+([a-ząćęłńóśźż]+)', text_lower)
        if match:
            day, month_word = match.groups()
            month_num = self.MONTHS_PL.get(month_word)
            if month_num:
                try:
                    year = today.year
                    candidate = datetime(year, month_num, int(day)).date()
                    if candidate < today:
                        candidate = datetime(year + 1, month_num, int(day)).date()
                    return candidate.strftime('%Y-%m-%d')
                except ValueError:
                    pass

        # Pattern: końca miesiąca
        for month_word, month_num in self.MONTHS_PL.items():
            if month_word in text_lower:
                if 'koniec' in text_lower or 'końca' in text_lower or 'końc' in text_lower:
                    last_days = {1: 31, 2: 28, 3: 31, 4: 30, 5: 31, 6: 30,
                                 7: 31, 8: 31, 9: 30, 10: 31, 11: 30, 12: 31}
                    year = today.year
                    return f"{year}-{month_num:02d}-{last_days[month_num]:02d}"
                elif 'połow' in text_lower or 'środek' in text_lower:
                    return f"{today.year}-{month_num:02d}-15"

        return None

    def _classify_intent(self, text_embedding: np.ndarray) -> str:
        """Classify primary intent of the message."""
        best_intent = 'unknown'
        best_score = 0.0

        for intent, intent_embedding in self.intent_embeddings.items():
            score = self._cosine_similarity(text_embedding, intent_embedding)
            if score > best_score:
                best_score = score
                best_intent = intent

        return best_intent if best_score > 0.3 else 'unknown'

    def _classify_tone(self, text_embedding: np.ndarray, text: str) -> str:
        """Classify emotional tone of the message."""
        best_tone = 'neutral'
        best_score = 0.0

        for tone, tone_embedding in self.tone_embeddings.items():
            score = self._cosine_similarity(text_embedding, tone_embedding)
            if score > best_score:
                best_score = score
                best_tone = tone

        return best_tone if best_score > 0.3 else 'neutral'

    def extract(self, text: str, min_confidence: float = 0.55) -> ExtractionResult:
        """
        Extract all entities from text using semantic similarity.

        Args:
            text: Input message
            min_confidence: Minimum similarity threshold

        Returns:
            ExtractionResult with entities, intent, and tone
        """
        if not text or len(text) < 5:
            return ExtractionResult()

        # Get embedding for full text
        text_embedding = self.model.encode(text, convert_to_numpy=True)

        # Find matching categories
        matches = self._find_best_match(text_embedding, threshold=min_confidence, text=text)

        entities = []
        seen_types = set()

        for entity_type, subtype, confidence in matches:
            # Avoid duplicate types (take highest confidence)
            type_key = f"{entity_type}:{subtype}"
            if type_key in seen_types:
                continue
            seen_types.add(type_key)

            entity = ExtractedEntity(
                entity_type=entity_type,
                subtype=subtype,
                value=text[:100],  # Will be refined
                confidence=round(confidence, 3),
                context=f"Semantic match: {subtype}",
                raw_text=text
            )

            # Special handling for dates - extract actual date value
            if entity_type == 'DATE':
                date_value = self._extract_date_value(text)
                if date_value:
                    entity.date_value = date_value
                    entity.value = date_value
                else:
                    # Date pattern detected but no parseable date
                    entity.context = "Date context detected but no specific date found"

            entities.append(entity)

        # Classify intent and tone
        primary_intent = self._classify_intent(text_embedding)
        emotional_tone = self._classify_tone(text_embedding, text)

        return ExtractionResult(
            entities=entities,
            primary_intent=primary_intent,
            emotional_tone=emotional_tone
        )

    def extract_batch(self, texts: List[str], min_confidence: float = 0.55) -> List[ExtractionResult]:
        """Extract entities from multiple texts (batch processing)."""
        return [self.extract(text, min_confidence) for text in texts]


# === Singleton instance ===
_extractor_instance: Optional[SemanticExtractor] = None


def get_extractor() -> SemanticExtractor:
    """Get or create singleton extractor instance."""
    global _extractor_instance
    if _extractor_instance is None:
        _extractor_instance = SemanticExtractor()
    return _extractor_instance


# === Test ===
if __name__ == '__main__':
    print("=" * 60)
    print("SEMANTIC ENTITY EXTRACTOR v1.0 TEST")
    print("=" * 60)

    extractor = SemanticExtractor()

    test_cases = [
        # Dates - medical
        ("Mam wizytę u psychiatry 29 kwietnia", "DATE", "medical_visit"),
        ("Idę do doktora w przyszłym tygodniu", "DATE", "medical_visit"),
        ("Mam umówione badania", "DATE", "medical_visit"),

        # Dates - inventory
        ("Zapas pregabaliny wystarczy do 15 marca", "DATE", "inventory_status"),
        ("Kończą mi się leki", "DATE", "inventory_status"),
        ("Zostało mi ostatnie opakowanie tabletek", "DATE", "inventory_status"),

        # Dates - deadline
        ("Deadline projektu jest 30.06", "DATE", "deadline"),
        ("Muszę to skończyć do piątku", "DATE", "deadline"),

        # Dates - personal
        ("Moje urodziny są 15 marca", "DATE", "personal_event"),
        ("Rocznica ślubu rodziców", "DATE", "personal_event"),

        # Milestones
        ("Kocham cię najbardziej na świecie", "MILESTONE", "love_declaration"),
        ("Szaleję za tobą", "MILESTONE", "love_declaration"),
        ("Ufam ci całkowicie", "MILESTONE", "trust_declaration"),
        ("Chcę z tobą zamieszkać", "MILESTONE", "future_together"),

        # Shared things
        ("To nasza ulubiona kawiarnia", "SHARED_THING", "our_place"),
        ("Tam się poznaliśmy", "SHARED_THING", "our_place"),
        ("Ta piosenka mi cię przypomina", "SHARED_THING", "our_song"),

        # Emotions
        ("Jestem dzisiaj zmęczony", "EMOTION", "tired"),
        ("Padam z nóg po pracy", "EMOTION", "tired"),
        ("Cieszę się że rozmawiamy", "EMOTION", "positive"),

        # Should NOT match strongly (neutral text)
        ("Dzisiaj jest ładna pogoda", None, None),
        ("Ok, rozumiem", None, None),
    ]

    passed = 0
    failed = 0

    for text, expected_type, expected_subtype in test_cases:
        result = extractor.extract(text)
        print(f"\nInput: \"{text}\"")
        print(f"  Intent: {result.primary_intent} | Tone: {result.emotional_tone}")

        if expected_type is None:
            # Should not have strong matches
            if not result.entities or result.entities[0].confidence < 0.6:
                print(f"  [OK] Correctly neutral/weak match")
                passed += 1
            else:
                top = result.entities[0]
                print(f"  [X] Should be neutral but got: {top.entity_type}:{top.subtype} ({top.confidence:.2f})")
                failed += 1
        else:
            # Should match expected type
            found = False
            for entity in result.entities:
                if entity.entity_type == expected_type:
                    found = True
                    if entity.subtype == expected_subtype:
                        print(f"  [OK] {entity.entity_type}:{entity.subtype} ({entity.confidence:.2f})")
                        if entity.date_value:
                            print(f"       Date: {entity.date_value}")
                        passed += 1
                    else:
                        print(f"  [~] Type OK but subtype: {entity.subtype} (expected {expected_subtype})")
                        passed += 0.5
                        failed += 0.5
                    break

            if not found:
                print(f"  [X] Expected {expected_type}:{expected_subtype}, got: ", end="")
                if result.entities:
                    top = result.entities[0]
                    print(f"{top.entity_type}:{top.subtype} ({top.confidence:.2f})")
                else:
                    print("nothing")
                failed += 1

    print("\n" + "=" * 60)
    print(f"RESULT: {passed}/{passed+failed} tests passed ({100*passed/(passed+failed):.0f}%)")
    print("=" * 60)
