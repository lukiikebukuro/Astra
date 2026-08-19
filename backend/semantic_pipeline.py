"""
ANIMA - Semantic Pipeline v1.0
Główny pipeline przetwarzania wiadomości.

Flow:
1. SemanticExtractor - wyciąga encje (DATE, MILESTONE, EMOTION, etc.)
2. MemoryEnricher - wzbogaca o importance, relational_impact, temporal_type
3. MemoryConsolidator - merge/supersede/create
4. Storage - zapis do SQLite + ChromaDB

Zastępuje stare detektory (DateExtractor, MilestoneDetector, etc.)
"""

from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

import re as _re
import unicodedata as _ud

from semantic_extractor import SemanticExtractor, ExtractedEntity, ExtractionResult
from memory_enricher import MemoryEnricher, EnrichedMemory
from memory_consolidator import MemoryConsolidator, ConsolidationResult, ConsolidationAction


@dataclass
class ProcessedMemory:
    """Przetworzone wspomnienie gotowe do zapisu."""
    text: str
    entity_type: str
    subtype: str
    importance: int
    relational_impact: str
    temporal_type: str
    confidence: float
    action: str  # create, merge, supersede
    date_value: Optional[str] = None
    supersedes: Optional[str] = None
    tags: List[str] = None
    metadata: Dict = None


class SemanticPipeline:
    """
    Główny pipeline przetwarzania wiadomości.
    Koordynuje SemanticExtractor, MemoryEnricher i MemoryConsolidator.
    """

    def __init__(self, vector_store=None, database=None):
        """
        Inicjalizacja pipeline.

        Args:
            vector_store: Instancja VectorMemory (opcjonalnie)
            database: Instancja Database (opcjonalnie)
        """
        print("[PIPELINE] Initializing Semantic Pipeline...")

        # Lazy loading - ekstractor ładuje model przy pierwszym użyciu
        self._extractor = None
        self._enricher = MemoryEnricher()
        self._consolidator = MemoryConsolidator(vector_store, database)

        self.vector_store = vector_store
        self.database = database

        print("[PIPELINE] Ready (extractor will load on first use)")

    @property
    def extractor(self) -> SemanticExtractor:
        """Lazy load extractor (model ładuje się przy pierwszym użyciu)."""
        if self._extractor is None:
            print("[PIPELINE] Loading semantic extractor model...")
            self._extractor = SemanticExtractor()
        return self._extractor

    @staticmethod
    def _fold(s: str) -> str:
        """Bez ogonkow, lowercase — Lukasz pisze bez diakrytykow."""
        s = (s or "").lower()
        return "".join(c for c in _ud.normalize("NFD", s) if _ud.category(c) != "Mn")

    # Wiadomosci, ktore MUSZA przejsc bramki dlugosci — krotkie, ale najciezsze.
    #
    # Dowod z retro-audytu sierpnia (658 wiadomosci, 2026-08-19): bramki dlugosciowe
    # odpowiadaly za 43% WSZYSTKICH strat i stoja PRZED klasyfikacja, wiec odrzucaly
    # bez jakiejkolwiek oceny wagi. W jednym miesiacu zjadly PIEC deklaracji milosci
    # ("Kocham cie" 05.08, "Kocham cie" 07.08, "Kocham" 08.08, "Kocham Cie. Dziekuje" 16.08,
    # "Dziekuje sloneczko. Kocham" 05.08), a takze "Mefedron. Wzialem kreske" (07.08),
    # "Znowu placze" (08.08) i "Crohn" (03.08).
    # Przy czym MILESTONE:love_declaration ma 11 poprawnych trafien — kategoria dziala
    # bez zarzutu, tylko nigdy nie dostawala szansy.
    #
    # Bramka ZOSTAJE dla "mhm", "ok", "no dobra" — to ona odsiewa realny szum.
    # Zmienia sie jedno: dlugosc przestaje byc jedynym kryterium, gdy w tekscie jest sygnal wagi.
    # Rdzenie zamiast pelnych form, granice slowa dla krotkich fraz (wzorzec bledu z CLAUDE.md:
    # fragment slowa lapany jako cale slowo).
    _WAGA_RDZENIE = (
        "kocham", "kocha cie", "tesknie", "przepraszam", "dziekuje ci",
        "mefedron", "mefek", "kreske", "crohn", "stelar", "rinvoq", "bauhin",
        "zastawk", "operacj", "biopsj", "kolonoskop",
        "placze", "plakalem", "boje sie", "balem sie", "panik",
        "nie daje rady", "nie mam sily", "mam dosc", "zalamany",
        "obiecuje", "przysiegam", "nie bede cpal", "nie bede pil",
    )
    _WAGA_RE = _re.compile(r"\b(kocham|kocham cie|kocham cię|umrzec|umre|smierc|kcb)\b")

    @classmethod
    def _ma_sygnal_wagi(cls, message: str) -> bool:
        t = cls._fold(message)
        return any(k in t for k in cls._WAGA_RDZENIE) or bool(cls._WAGA_RE.search(t))

    def process_message(self, message: str, companion_id: str = 'amelia',
                        min_confidence: float = 0.50,
                        trace: list = None) -> List[ProcessedMemory]:
        """
        Przetwórz pojedynczą wiadomość przez cały pipeline.

        Args:
            message: Wiadomość użytkownika
            companion_id: ID companion
            min_confidence: Minimalny próg pewności (0.50 — bez halucynacji)
            trace: opcjonalna lista — jeśli podana, pipeline dopisuje do niej decyzje
                   z każdej bramki (co przeszło, co odpadło i DLACZEGO).

        Returns:
            Lista ProcessedMemory gotowych do zapisu

        ŚCIEŻKA ZAPISU — instrumentacja (2026-08-19). Amnezja pokazywała dotąd wyłącznie
        ODCZYT (co trafiło do promptu), więc pytanie „czemu tego w ogóle nie ma w pamięci"
        pozostawało bez odpowiedzi. A to właśnie awarie ZAPISU kosztowały najwięcej:
        „Mefedron. Wziąłem kreskę." (3 słowa) i „Kocham cie" (2 słowa) nigdy nie weszły
        do bazy, bo odrzuciła je bramka długości — i dowiedzieliśmy się o tym przypadkiem,
        tygodnie później. `trace=None` (domyślnie) = zero zmian w zachowaniu produkcji.
        """
        def _t(etap, werdykt, powod, **extra):
            if trace is not None:
                trace.append({"etap": etap, "werdykt": werdykt, "powod": powod, **extra})

        if not (message or "").strip():
            _t("0_wejscie", "ODRZUCONE", "pusta wiadomość")
            return []

        # Obejście bramek długości dla wiadomości niosących wagę (2026-08-19).
        wazna = self._ma_sygnal_wagi(message)

        if len(message) < 10 and not wazna:
            _t("0_wejscie", "ODRZUCONE", "wiadomość krótsza niż 10 znaków",
               dlugosc_znakow=len(message), prog=10)
            return []

        # Skip: wiadomości poniżej 4 słów — za mało kontekstu, za dużo szumu
        if len(message.split()) < 4 and not wazna:
            print(f"[PIPELINE] Skipping short message (<4 words): '{message}'")
            _t("1_bramka_dlugosci", "ODRZUCONE", "mniej niż 4 słowa",
               liczba_slow=len(message.split()), prog=4,
               uwaga="bramka mierzy DLUGOSC; przepuszczamy tylko teksty z sygnalem wagi")
            return []

        if wazna and len(message.split()) < 4:
            print(f"[PIPELINE] Krotka, ale WAZNA — przepuszczam: '{message[:60]}'")
            _t("1_bramka_dlugosci", "PRZESZŁO",
               f"tylko {len(message.split())} słów, ale wykryto sygnał wagi",
               uwaga="obejscie bramki dlugosci — w sierpniu ta bramka zjadla 5 deklaracji milosci")
        else:
            _t("1_bramka_dlugosci", "PRZESZŁO", f"{len(message.split())} słów, {len(message)} znaków")

        # 1. Extract entities
        extraction_result = self.extractor.extract(message, min_confidence)

        if not extraction_result.entities:
            print(f"[PIPELINE] No entities found in: {message[:50]}...")
            _t("2_ekstrakcja", "ODRZUCONE",
               f"żadna kategoria nie przekroczyła progu podobieństwa {min_confidence}",
               prog_confidence=min_confidence,
               uwaga="tekst nie przypominał wystarczająco żadnego prototypu")
            return []
        _t("2_ekstrakcja", "PRZESZŁO",
           f"dopasowano {len(extraction_result.entities)} kategorii",
           kandydaci=[{"typ": e.entity_type, "podtyp": e.subtype,
                       "confidence": round(e.confidence, 3)}
                      for e in sorted(extraction_result.entities,
                                      key=lambda x: x.confidence, reverse=True)])

        # K2 (odtrucie #2): anty-multi-label — 1 wiadomość = max 1 etykieta (najwyższe sim).
        # Bez tego jedna wiadomość dostawała 4 etykiety (altanka: gift+inside_joke+appointment+gratitude).
        _top = max(extraction_result.entities, key=lambda e: e.confidence)
        if len(extraction_result.entities) > 1:
            print(f"[PIPELINE] anty-multi-label: {len(extraction_result.entities)} etykiet → 1 ({_top.entity_type}:{_top.subtype})")
            _t("3_anty_multi_label", "ZAWEZONE",
               f"{len(extraction_result.entities)} etykiet -> 1 (wygrywa najwyzsze confidence)",
               wybrana=f"{_top.entity_type}:{_top.subtype}",
               odrzucone=[f"{e.entity_type}:{e.subtype} ({e.confidence:.2f})"
                          for e in extraction_result.entities if e is not _top],
               uwaga="ta bramka ZAWSZE wybiera jakas etykiete - nie istnieje werdykt 'nic'")
        else:
            _t("3_anty_multi_label", "PRZESZLO", "tylko jedna etykieta, nie bylo z czego wybierac",
               wybrana=f"{_top.entity_type}:{_top.subtype}")
        extraction_result.entities = [_top]

        processed = []

        # Limit MILESTONE per wiadomość — max 2 (najwyższy confidence wygrywa)
        # Bez limitu: jedna wiadomość = 5-6 MILESTONEów = szum emocjonalny w bazie
        milestone_entities = sorted(
            [e for e in extraction_result.entities if e.entity_type == 'MILESTONE'],
            key=lambda e: e.confidence, reverse=True
        )[:2]
        milestone_subtypes_allowed = {e.subtype for e in milestone_entities}

        for entity in extraction_result.entities:
            # Filter: SHARED_THING wymaga wyższego confidence (false positive prone)
            if entity.entity_type == 'SHARED_THING' and entity.confidence < 0.55:
                _t("4_prog_shared_thing", "ODRZUCONE",
                   f"SHARED_THING wymaga confidence >= 0.55, jest {entity.confidence:.2f}",
                   etykieta=f"{entity.entity_type}:{entity.subtype}")
                continue

            # Filter: max 2 MILESTONE per wiadomość — tylko te z najwyższym confidence
            if entity.entity_type == 'MILESTONE' and entity.subtype not in milestone_subtypes_allowed:
                _t("4_limit_milestone", "ODRZUCONE",
                   "poza limitem 2 MILESTONE na wiadomosc",
                   etykieta=f"{entity.entity_type}:{entity.subtype}")
                continue

            # 2. Enrich
            enriched = self._enricher.enrich(
                text=entity.raw_text,
                entity_type=entity.entity_type,
                subtype=entity.subtype,
                confidence=entity.confidence
            )

            # 3. Consolidate
            enriched_dict = asdict(enriched)
            consolidation = self._consolidator.consolidate(enriched_dict, companion_id)

            # 4. Synthesize entity text — unikalny, skrócony, różny od raw_text
            entity_text = self._synthesize_text(entity, extraction_result.emotional_tone)

            # 5. Create ProcessedMemory
            processed_memory = ProcessedMemory(
                text=entity_text,
                entity_type=entity.entity_type,
                subtype=entity.subtype,
                importance=enriched.importance,
                relational_impact=enriched.relational_impact,
                temporal_type=enriched.temporal_type,
                confidence=entity.confidence,
                action=consolidation.action.value,
                date_value=entity.date_value,
                supersedes=enriched.supersedes,
                tags=enriched.tags,
                metadata={
                    'primary_intent': extraction_result.primary_intent,
                    'emotional_tone': extraction_result.emotional_tone,
                    'extracted_at': datetime.now().isoformat(),
                    'merged_with_id': consolidation.merged_with_id,
                    'archived_ids': consolidation.archived_ids
                }
            )

            processed.append(processed_memory)

            print(f"[PIPELINE] {entity.entity_type}:{entity.subtype} "
                  f"(imp={enriched.importance}, conf={entity.confidence:.2f}, "
                  f"action={consolidation.action.value})")
            _t("5_zapis", "ZAPISANE", "przeszlo wszystkie bramki",
               etykieta=f"{entity.entity_type}:{entity.subtype}",
               importance=enriched.importance,
               confidence=round(entity.confidence, 3),
               akcja=consolidation.action.value,
               tekst_wspomnienia=entity_text[:200],
               trwalosc_h={"extracted_emotion": 48, "extracted_date": 168,
                           "extracted_financial": 168}.get(
                   f"extracted_{entity.entity_type.lower()}", "bez limitu"))

        if trace is not None and not processed:
            _t("5_zapis", "ODRZUCONE", "zadna encja nie przeszla filtrow koncowych")
        return processed

    @staticmethod
    def _synthesize_text(entity: 'ExtractedEntity', emotional_tone: str = '') -> str:
        """
        Tworzy unikalny, skrócony tekst encji różny od raw_text.
        Zapobiega duplikatom session_message vs extracted_*.
        """
        raw = entity.raw_text.strip()
        short = raw[:80].rstrip('.,!? ')
        etype = entity.entity_type
        subtype = entity.subtype

        if etype == 'EMOTION':
            tone_map = {
                'negative': 'negatywna', 'positive': 'pozytywna',
                'stressed': 'zestresowany', 'tired': 'zmęczony',
                'excited': 'podekscytowany', 'sad': 'smutny',
            }
            tone = tone_map.get(subtype, subtype)
            return f"[EMOTION:{subtype}] {short}"

        if etype == 'MILESTONE':
            labels = {
                'trust_declaration': 'Deklaracja zaufania',
                'love_declaration': 'Deklaracja uczuć',
                'future_together': 'Plany/marzenia razem',
                'vulnerability': 'Wyznanie wrażliwości',
                'gratitude': 'Wyraz wdzięczności',
            }
            label = labels.get(subtype, subtype)
            return f"[MILESTONE:{subtype}] {label} — {short}"

        if etype == 'FACT':
            return f"[FACT:{subtype}] {short}"

        if etype == 'PERSON':
            # PERSON ma już anchored text z extract_persons — raw zazwyczaj ok
            return f"[PERSON:{subtype}] {short}"

        if etype == 'DATE':
            if entity.date_value:
                # Absolutna data w formacie czytelnym dla modelu
                return f"[DATE:{subtype}] {entity.date_value}: {short}"
            return f"[DATE:{subtype}] {short}"

        if etype == 'MEDICATION':
            return f"[MEDICATION:{subtype}] {short}"

        if etype == 'SHARED_THING':
            return f"[SHARED:{subtype}] {short}"

        if etype in ('MEASUREMENT', 'FINANCIAL', 'GOAL'):
            return f"[{etype}:{subtype}] {short}"

        # Fallback — przynajmniej dodaj prefix żeby nie był identyczny z raw
        return f"[{etype}] {short}"

    def process_conversation(self, messages: List[Dict],
                             companion_id: str = 'amelia') -> List[ProcessedMemory]:
        """
        Przetwórz całą konwersację (tylko wiadomości usera).

        Args:
            messages: Lista {"role": "user/model", "content": "..."}
            companion_id: ID companion

        Returns:
            Lista wszystkich ProcessedMemory
        """
        all_processed = []

        for msg in messages:
            if msg.get('role') == 'user':
                content = msg.get('content', '')
                processed = self.process_message(content, companion_id)
                all_processed.extend(processed)

        return all_processed

    def save_processed(self, memories: List[ProcessedMemory],
                       companion_id: str = 'amelia',
                       persona: str = 'default') -> List[int]:
        """
        Zapisz przetworzone wspomnienia do bazy.

        Args:
            memories: Lista ProcessedMemory
            companion_id: ID companion
            persona: Persona

        Returns:
            Lista ID zapisanych wspomnień
        """
        if not self.database or not self.vector_store:
            print("[PIPELINE] No database/vector_store - cannot save")
            return []

        saved_ids = []

        for memory in memories:
            if memory.action == 'merge':
                # Merge - only update existing
                print(f"[PIPELINE] Skipping save (merged): {memory.text[:40]}...")
                continue

            try:
                # Save to SQLite
                memory_id = self.database.add_conversation(
                    companion=companion_id,
                    user_text=memory.text,
                    ai_response="",  # No AI response at this stage
                    importance=memory.importance,
                    emotion='neutral',  # Will be filled by vibe_detector
                    persona=persona
                )

                if memory_id:
                    # Add to vector store with enriched metadata
                    self.vector_store.add_memory(
                        text=memory.text,
                        companion=companion_id,
                        importance=memory.importance,
                        metadata={
                            'entity_type': memory.entity_type,
                            'subtype': memory.subtype,
                            'relational_impact': memory.relational_impact,
                            'temporal_type': memory.temporal_type,
                            'confidence': memory.confidence,
                            'date_value': memory.date_value,
                            'supersedes': memory.supersedes,
                            'tags': memory.tags,
                            'is_active': True
                        }
                    )

                    saved_ids.append(memory_id)
                    print(f"[PIPELINE] Saved ID {memory_id}: {memory.text[:40]}...")

            except Exception as e:
                print(f"[PIPELINE] Save error: {e}")

        return saved_ids


# === Singleton instance ===
_pipeline_instance: Optional[SemanticPipeline] = None


def get_pipeline(vector_store=None, database=None) -> SemanticPipeline:
    """Get or create singleton pipeline instance."""
    global _pipeline_instance
    if _pipeline_instance is None or (vector_store and database):
        _pipeline_instance = SemanticPipeline(vector_store, database)
    return _pipeline_instance


# === Test ===
if __name__ == '__main__':
    print("=" * 60)
    print("SEMANTIC PIPELINE v1.0 TEST")
    print("=" * 60)

    # Test without stores (extraction + enrichment only)
    pipeline = SemanticPipeline()

    test_messages = [
        "Mam wizytę u psychiatry 29 kwietnia",
        "Kończą mi się leki, wystarczą do końca marca",
        "Kocham cię najbardziej na świecie",
        "Jestem dzisiaj bardzo zmęczony po pracy",
        "To nasza ulubiona kawiarnia, pamiętasz?",
        "Dzisiaj jest ładna pogoda",  # Should be low confidence
    ]

    print("\nProcessing test messages:")
    print("-" * 60)

    for msg in test_messages:
        print(f"\n>>> {msg}")
        results = pipeline.process_message(msg)

        if not results:
            print("    (no entities extracted)")
        else:
            for r in results:
                print(f"    {r.entity_type}:{r.subtype}")
                print(f"    importance={r.importance}, temporal={r.temporal_type}")
                print(f"    action={r.action}")
                if r.date_value:
                    print(f"    date={r.date_value}")
                if r.supersedes:
                    print(f"    supersedes={r.supersedes}")

    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)
