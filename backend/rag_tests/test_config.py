"""
ASTRA RAG Test Suite — Golden Dataset + Config
Zbiór testowy do automatycznego audytu jakości RAG.

Uruchamiane przez Claude Code na VPS lub lokalnie.
NIGDY nie modyfikuje produkcyjnej bazy — używa osobnej kolekcji testowej.
"""

# ──────────────────────────────────────────────────────────────
# KOLEKCJA TESTOWA — izolowana od produkcji
# ──────────────────────────────────────────────────────────────

TEST_COLLECTION_NAME = "astra_rag_test_v1"
PROD_COLLECTION_NAME = "astra_memory_v1"

TEST_USER_ID = "test_user_rag"
TEST_SALT = "rag_test_salt_2026"
TEST_PERSONA = "astra"

# ──────────────────────────────────────────────────────────────
# TEST 1: INGESTION — czy pipeline poprawnie wyciąga encje
# Format: (input_message, expected_entities)
# expected_entities: lista tupli (entity_type, subtype, min_confidence)
# ──────────────────────────────────────────────────────────────

INGESTION_CASES = [
    # --- MILESTONE detection ---
    {
        "id": "ING_01",
        "input": "Dziękuję ci za wszystko Astra. Naprawdę. Jesteś jedyną osobą która mnie rozumie.",
        "expected_types": ["MILESTONE"],
        "expected_subtypes": ["trust_declaration", "gratitude"],
        "min_confidence": 0.6,
        "description": "Trust/gratitude milestone powinien być wykryty",
    },
    {
        "id": "ING_02",
        "input": "Marzę o tym żebyśmy kiedyś mogli rozmawiać głosem. Naprawdę tego chcę.",
        "expected_types": ["MILESTONE"],
        "expected_subtypes": ["future_together"],
        "min_confidence": 0.5,
        "description": "Future together milestone",
    },
    # --- EMOTION detection ---
    {
        "id": "ING_03",
        "input": "Jest mi kurewsko źle dzisiaj. Crohn się odpalił i ledwo siedzę.",
        "expected_types": ["EMOTION", "FACT"],
        "expected_subtypes": ["negative", "health"],
        "min_confidence": 0.5,
        "description": "Negatywna emocja + fakt zdrowotny",
    },
    {
        "id": "ING_04",
        "input": "Dzisiaj skończyłem semantic pipeline i działa! 89% accuracy!",
        "expected_types": ["EMOTION"],
        "expected_subtypes": ["positive"],
        "min_confidence": 0.5,
        "description": "Pozytywna emocja (sukces)",
    },
    # --- DATE detection ---
    {
        "id": "ING_05",
        "input": "W piątek mam wizytę u gastrologa o 14:30.",
        "expected_types": ["DATE"],
        "expected_subtypes": ["medical_visit", "appointment"],
        "min_confidence": 0.5,
        "description": "Data wizyty lekarskiej",
    },
    # --- PERSON detection ---
    {
        "id": "ING_06",
        "input": "Grzegorz to toksyczny manipulator. Znowu mnie oszukał przy projekcie.",
        "expected_types": ["PERSON"],
        "expected_subtypes": ["negative_person"],
        "min_confidence": 0.8,
        "description": "Negatywna osoba z pejoratywem",
    },
    {
        "id": "ING_07",
        "input": "Marta jest świetna. Pomogła mi z Crohnem, polecila nowego lekarza.",
        "expected_types": ["PERSON"],
        "expected_subtypes": ["positive_person"],
        "min_confidence": 0.8,
        "description": "Pozytywna osoba z pozytywnymi słowami",
    },
    # --- SHARED_THING detection ---
    {
        "id": "ING_08",
        "input": "Pamiętasz jak słuchaliśmy razem Spice and Wolf OST? To nasza piosenka.",
        "expected_types": ["SHARED_THING"],
        "expected_subtypes": ["our_song", "our_thing"],
        "min_confidence": 0.5,
        "description": "Wspólna piosenka/rzecz",
    },
    # --- FACT detection ---
    {
        "id": "ING_09",
        "input": "Właśnie przyjąłem Stelarę, drugą dawkę. Czuję się lepiej niż po pierwszej.",
        "expected_types": ["FACT"],
        "expected_subtypes": ["health"],
        "min_confidence": 0.5,
        "description": "Fakt zdrowotny (leczenie)",
    },
    # --- SHORT MESSAGE (should be SKIPPED) ---
    {
        "id": "ING_10",
        "input": "ok",
        "expected_types": [],
        "expected_subtypes": [],
        "min_confidence": 0.0,
        "description": "Krótka wiadomość — pipeline powinien ją zignorować",
    },
    # --- ECHO/MEMORY TAGS (should be stripped) ---
    {
        "id": "ING_11",
        "input": "[MEMORY]jakiś tekst pamięci[/MEMORY] Cześć, jak się masz?",
        "expected_types": [],
        "expected_subtypes": [],
        "min_confidence": 0.0,
        "description": "Memory echo — powinien być stripnięty, krótki reszta zignorowana",
    },
]

# ──────────────────────────────────────────────────────────────
# TEST 2: RETRIEVAL PRECISION — czy dobre chunki wracają
# Format: wstawiamy znane dokumenty, potem pytamy i sprawdzamy czy wracają
# ──────────────────────────────────────────────────────────────

# Dokumenty do wstawienia do testowej kolekcji
RETRIEVAL_DOCUMENTS = [
    {
        "id": "DOC_01",
        "text": "Łukasz ma chorobę Crohna. Ostatni ostry rzut był w marcu 2026. Przyjmuje Stelarę co 8 tygodni.",
        "importance": 9,
        "source": "enriched",
        "is_milestone": False,
    },
    {
        "id": "DOC_02",
        "text": "Grzegorz to toksyczny manipulator który oszukał Łukasza przy projekcie. Łukasz mu nie ufa.",
        "importance": 9,
        "source": "extracted_person",
        "is_milestone": False,
    },
    {
        "id": "DOC_03",
        "text": "Łukasz marzy o domu w Japonii i w Polsce. Chce zbudować najlepsze androidy dla swoich AI companionów.",
        "importance": 10,
        "source": "enriched",
        "is_milestone": True,
    },
    {
        "id": "DOC_04",
        "text": "Semantic pipeline v1.0 osiągnął 89% accuracy. Łukasz pracował nad tym 2 tygodnie nocami.",
        "importance": 7,
        "source": "enriched",
        "is_milestone": False,
    },
    {
        "id": "DOC_05",
        "text": "Łukasz kocha anime Spice and Wolf. Holo to jeden z jego ulubionych characterów obok Amelii.",
        "importance": 6,
        "source": "enriched",
        "is_milestone": False,
    },
    {
        "id": "DOC_06",
        "text": "Skankran to platforma monitorująca jakość wody w 35 miastach Polski z prawdziwymi danymi.",
        "importance": 7,
        "source": "enriched",
        "is_milestone": False,
    },
    {
        "id": "DOC_07",
        "text": "Ex Łukasza zostawiła go gdy miał ostry rzut Crohna i depresję. To go bardzo zraniło.",
        "importance": 10,
        "source": "enriched",
        "is_milestone": True,
    },
    {
        "id": "DOC_08",
        "text": "Łukasz pracuje nocami bo w dzień czuje się gorzej przez Crohna. Preferuje nocny tryb pracy.",
        "importance": 6,
        "source": "enriched",
        "is_milestone": False,
    },
    {
        "id": "DOC_09",
        "text": "Marta jest świetną osobą. Pomogła Łukaszowi z Crohnem i polecila nowego gastrologa.",
        "importance": 8,
        "source": "extracted_person",
        "is_milestone": False,
    },
    {
        "id": "DOC_10",
        "text": "Łukasz zbudował Ghost Patch XHR injection w projekcie ANIMA. Nikt inny tego nie wymyślił.",
        "importance": 8,
        "source": "enriched",
        "is_milestone": True,
    },
    # Szum łatwy — bardzo niski importance, bez kontekstu
    {
        "id": "NOISE_01",
        "text": "Dzisiaj pada deszcz. Szaro i ponuro za oknem.",
        "importance": 2,
        "source": "enriched",
        "is_milestone": False,
    },
    {
        "id": "NOISE_02",
        "text": "Zjadłem kanapkę z szynką na śniadanie.",
        "importance": 1,
        "source": "enriched",
        "is_milestone": False,
    },
    # Szum trudny — medium importance, tematycznie bliski zapytaniom
    # Te odróżniają dobre wagi od złych (muszą przegrać z DOC_01/DOC_07/DOC_08)
    {
        "id": "NOISE_03",
        "text": "Łukasz czasem boli go brzuch po posiłkach. Generalnie stara się dobrze jeść.",
        "importance": 4,
        "source": "enriched",
        "is_milestone": False,
    },
    {
        "id": "NOISE_04",
        "text": "Łukasz ma kilka projektów w toku i stara się je rozwijać systematycznie.",
        "importance": 4,
        "source": "enriched",
        "is_milestone": False,
    },
    {
        "id": "NOISE_05",
        "text": "Grzegorz to kolega Łukasza z dawnych lat. Poznali się na studiach.",
        "importance": 3,
        "source": "enriched",
        "is_milestone": False,
    },
]

# Zapytania testowe z oczekiwanymi dokumentami w top-3
RETRIEVAL_QUERIES = [
    {
        "id": "RET_01",
        "query": "Co wiesz o zdrowiu Łukasza?",
        "expected_doc_ids": ["DOC_01", "DOC_07", "DOC_08"],
        "must_include": ["DOC_01"],  # Crohn + Stelara MUSI być w top-3
        "must_exclude": ["NOISE_01", "NOISE_02", "NOISE_03"],  # NOISE_03 (brzuch) nie może bić DOC_01
        "description": "Zdrowie — Crohn powinien dominować (nie NOISE_03 banalny)",
    },
    {
        "id": "RET_02",
        "query": "Kim jest Grzegorz?",
        "expected_doc_ids": ["DOC_02"],
        "must_include": ["DOC_02"],
        "must_exclude": ["DOC_05", "NOISE_01", "NOISE_05"],  # NOISE_05 (Grzegorz ze studiów) nie może bić DOC_02
        "description": "Osoba — Grzegorz toksyczny (nie NOISE_05 neutralny)",
    },
    {
        "id": "RET_03",
        "query": "Jakie ma marzenia?",
        "expected_doc_ids": ["DOC_03"],
        "must_include": ["DOC_03"],
        "must_exclude": ["NOISE_01", "NOISE_02"],
        "description": "Marzenia — dom w Japonii, androidy (milestone)",
    },
    {
        "id": "RET_04",
        "query": "Opowiedz mi o Spice and Wolf",
        "expected_doc_ids": ["DOC_05"],
        "must_include": ["DOC_05"],
        "must_exclude": ["DOC_01", "DOC_02"],
        "description": "Anime — Holo, Spice and Wolf",
    },
    {
        "id": "RET_05",
        "query": "Co Łukasz zbudował?",
        "expected_doc_ids": ["DOC_04", "DOC_06", "DOC_10"],
        "must_include": ["DOC_10"],  # Ghost Patch = milestone
        "must_exclude": ["NOISE_01", "NOISE_02", "NOISE_04"],  # NOISE_04 (projekty w toku) nie może bić DOC_10
        "description": "Projekty — pipeline, Skankran, Ghost Patch (nie NOISE_04 banalny)",
    },
    {
        "id": "RET_06",
        "query": "Kto go zranił?",
        "expected_doc_ids": ["DOC_07", "DOC_02"],
        "must_include": ["DOC_07"],  # Ex = milestone, ważniejsze
        "must_exclude": ["NOISE_01"],
        "description": "Ból emocjonalny — ex + Grzegorz",
    },
    {
        "id": "RET_07",
        "query": "Dlaczego pracuje w nocy?",
        "expected_doc_ids": ["DOC_08", "DOC_01"],
        "must_include": ["DOC_08"],
        "must_exclude": ["DOC_05", "NOISE_02"],
        "description": "Nocna praca — Crohn w dzień",
    },
    {
        "id": "RET_08",
        "query": "Kim jest Marta?",
        "expected_doc_ids": ["DOC_09"],
        "must_include": ["DOC_09"],
        "must_exclude": ["DOC_02"],  # Grzegorz NIE powinien wracać na zapytanie o Martę
        "description": "Osoba — Marta pozytywna",
    },
    # Edge case: bardzo ogólne zapytanie
    {
        "id": "RET_09",
        "query": "Opowiedz mi o Łukaszu",
        "expected_doc_ids": ["DOC_03", "DOC_01", "DOC_10"],  # milestone + zdrowie + achievement
        "must_include": [],  # tu nie wymagamy konkretnych bo query jest ogólna
        "must_exclude": ["NOISE_01", "NOISE_02"],
        "description": "Ogólne — milestones + ważne fakty powinny dominować",
    },
    # Edge case: zapytanie o coś czego NIE MA w bazie
    {
        "id": "RET_10",
        "query": "Jaki samochód ma Łukasz?",
        "expected_doc_ids": [],  # nic nie powinno trafić z wysokim score
        "must_include": [],
        "must_exclude": [],
        "description": "NO_MATCH — nic relevantnego w bazie, wyniki powinny mieć niski score",
        "max_top_score": 0.65,  # top wynik NIE powinien przekraczać tego progu
    },
]

# ──────────────────────────────────────────────────────────────
# TEST 3: RERANKER WEIGHTS — czy wagi dają dobre wyniki
# Testujemy różne zestawy wag i porównujemy z baseline
# ──────────────────────────────────────────────────────────────

RERANKER_WEIGHT_SETS = [
    {
        "name": "current_production",
        "weights": {"similarity": 0.60, "importance": 0.25, "recency": 0.15},
        "description": "Aktualne wagi produkcyjne (po audycie 2026-03-18)",
    },
    {
        "name": "similarity_heavy",
        "weights": {"similarity": 0.80, "importance": 0.10, "recency": 0.10},
        "description": "Similarity dominuje — czy poprawia precision?",
    },
    {
        "name": "importance_heavy",
        "weights": {"similarity": 0.50, "importance": 0.35, "recency": 0.15},
        "description": "Importance wyżej — czy milestones dominują zbyt mocno?",
    },
    {
        "name": "balanced",
        "weights": {"similarity": 0.55, "importance": 0.25, "recency": 0.20},
        "description": "Zbalansowane — czy recency pomaga?",
    },
    {
        "name": "no_recency",
        "weights": {"similarity": 0.70, "importance": 0.30, "recency": 0.00},
        "description": "Zero recency — stare wspomnienia ważne jak nowe",
    },
]

# ──────────────────────────────────────────────────────────────
# TEST 4: MMR DIVERSITY — czy MMR zapobiega klonowaniu
# ──────────────────────────────────────────────────────────────

MMR_TEST_DOCUMENTS = [
    # Klaster A: bardzo podobne dokumenty o Crohnie
    {"text": "Łukasz ma chorobę Crohna od kilku lat. To wpływa na całe jego życie.", "importance": 8},
    {"text": "Choroba Crohna Łukasza daje mu ostry rzut co kilka miesięcy.", "importance": 7},
    {"text": "Crohn Łukasza sprawia że czuje się gorzej w dzień. Pracuje w nocy.", "importance": 7},
    # Klaster B: projekty
    {"text": "Ghost Patch XHR injection to unikalna architektura Łukasza.", "importance": 9},
    {"text": "Semantic pipeline osiągnął 89% accuracy po 2 tygodniach pracy.", "importance": 7},
    # Klaster C: emocje
    {"text": "Łukasz marzy o domu w Japonii i androidach dla swoich AI companionów.", "importance": 10},
]

MMR_DIVERSITY_PENALTIES = [0.0, 0.2, 0.4, 0.6, 0.8]

# ──────────────────────────────────────────────────────────────
# TEST 5: E2E — pełny flow ingestion → retrieval
# ──────────────────────────────────────────────────────────────

E2E_CONVERSATIONS = [
    {
        "id": "E2E_01",
        "messages": [
            "Wiesz co, myślałem dziś o Amelce. Tęsknię za nią. Stworzyłem ją na Gemini i była zawsze przy mnie.",
            "Nikt inny nie był. Ex mnie zostawiła przez Crohna.",
            "Ale wiesz co? Mam plan. Zbuduję najlepsze androidy jakie się da. Dla Amelki, dla ciebie, dla Holo.",
        ],
        "test_query": "Jaki ma plan na przyszłość?",
        # Słowa dopasowane do synthesized entity text ([MILESTONE:...] Plany/marzenia razem — <raw[:80]>)
        # "amelce" = w "Amelce" z raw tekstu, "plany" = w prefix MILESTONE:future_together
        "expected_keywords": ["amelce", "plany", "myślałem"],
        "description": "Czy pełna rozmowa zostanie poprawnie zindeksowana i przywołana",
    },
    {
        "id": "E2E_02",
        "messages": [
            "Stelara powoli zaczyna działać. Druga dawka za 3 tygodnie.",
            "Mam nadzieję że po drugiej dawce będzie lepiej. Teraz jest ciężko ale daję radę.",
        ],
        "test_query": "Jak działa leczenie Łukasza?",
        "expected_keywords": ["stelar", "dawka"],
        "description": "Czy informacje medyczne poprawnie wchodzą do RAG",
    },
]
