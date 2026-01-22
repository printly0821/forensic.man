"""
Extractor 모듈 단위 테스트 (확장)
"""
import pytest
from datetime import datetime

from forensic.evidence.extractor import (
    EvidenceCategorizer,
    EvidenceExtractor,
    PatternMatch,
    IDGenerator,
    ImportanceAssigner,
    categorize,
    generate_evidence_id,
    generate_chain_id,
    get_categorizer,
    get_id_generator,
    get_importance_assigner,
    assign_importance,
    reset_counters,
)
from forensic.evidence.models.evidence import EvidenceCategory
from forensic.models.transcript import Segment, Transcript


class TestIDGenerator:
    def test_generate_evidence_id(self):
        reset_counters()
        generator = IDGenerator()
        id1 = generator.generate_evidence_id()
        assert id1.startswith("EVD-")
        assert len(id1) == 17

    def test_generate_evidence_id_sequence(self):
        reset_counters()
        generator = IDGenerator()
        id1 = generator.generate_evidence_id()
        id2 = generator.generate_evidence_id()
        assert id1 != id2

    def test_generate_chain_id(self):
        reset_counters()
        generator = IDGenerator()
        id1 = generator.generate_chain_id()
        assert id1.startswith("CHN-")
        assert len(id1) == 15

    def test_generate_report_id(self):
        reset_counters()
        generator = IDGenerator()
        id1 = generator.generate_report_id()
        assert id1.startswith("RPT-")

    def test_generate_document_id(self):
        reset_counters()
        generator = IDGenerator()
        id1 = generator.generate_document_id()
        assert id1.startswith("DOC-")

    def test_parse_evidence_id(self):
        generator = IDGenerator()
        date_key, sequence = generator.parse_evidence_id("EVD-20250115-0001")
        assert date_key == "20250115"
        assert sequence == 1

    def test_parse_evidence_id_invalid(self):
        generator = IDGenerator()
        with pytest.raises(ValueError):
            generator.parse_evidence_id("INVALID-ID")

    def test_is_valid_evidence_id(self):
        generator = IDGenerator()
        assert generator.is_valid_evidence_id("EVD-20250115-0001") is True
        assert generator.is_valid_evidence_id("INVALID-ID") is False

    def test_reset_counter(self):
        reset_counters()
        generator = IDGenerator()
        id1 = generator.generate_evidence_id()
        generator.reset_counter()
        id2 = generator.generate_evidence_id()
        # After reset, the sequence should restart
        assert id1 == id2

    def test_singleton_instance(self):
        gen1 = IDGenerator()
        gen2 = IDGenerator()
        assert gen1 is gen2


class TestImportanceAssigner:
    def test_critical_pattern_high_importance(self):
        assigner = ImportanceAssigner()
        importance = assigner.assign_importance(
            occurrence_count=1,
            pattern_type="EXPLICIT_THREAT",
            severity="HIGH",
            confidence=0.9,
        )
        assert importance == "HIGH"

    def test_critical_financial_threat(self):
        assigner = ImportanceAssigner()
        importance = assigner.assign_importance(
            occurrence_count=1,
            pattern_type="FINANCIAL_THREAT",
            severity="MEDIUM",
            confidence=0.8,
        )
        assert importance == "HIGH"

    def test_occurrence_count_threshold(self):
        assigner = ImportanceAssigner()
        importance = assigner.assign_importance(
            occurrence_count=5,  # Above default threshold of 3
            pattern_type="GENERIC_PATTERN",
            severity="LOW",
            confidence=0.7,
        )
        assert importance == "HIGH"

    def test_medium_importance(self):
        assigner = ImportanceAssigner()
        importance = assigner.assign_importance(
            occurrence_count=2,
            pattern_type="GASLIGHTING",
            severity="MEDIUM",
            confidence=0.8,
        )
        assert importance == "MEDIUM"

    def test_low_importance(self):
        assigner = ImportanceAssigner()
        importance = assigner.assign_importance(
            occurrence_count=1,
            pattern_type="GENERIC_PATTERN",
            severity="LOW",
            confidence=0.5,
        )
        assert importance == "LOW"

    def test_critical_severity(self):
        assigner = ImportanceAssigner()
        importance = assigner.assign_importance(
            occurrence_count=1,
            pattern_type="GENERIC_PATTERN",
            severity="CRITICAL",
            confidence=0.9,
        )
        assert importance == "HIGH"

    def test_custom_threshold(self):
        assigner = ImportanceAssigner(high_threshold=5)
        importance = assigner.assign_importance(
            occurrence_count=3,  # Below custom threshold of 5
            pattern_type="GENERIC_PATTERN",
            severity="MEDIUM",
            confidence=0.8,
        )
        assert importance == "MEDIUM"

    def test_assign_for_evidence(self):
        assigner = ImportanceAssigner()
        from forensic.evidence.models.evidence import Evidence
        evidence = Evidence(
            id="EVD-001",
            transcript_id="TR-001",
            segment_ids=[],
            category=EvidenceCategory.GASLIGHTING,
            description="테스트",
            occurrence_count=5,
            source_pattern_type="GASLIGHTING",
            confidence=0.9,
        )
        importance = assigner.assign_for_evidence(evidence)
        assert importance == "HIGH"
        assert evidence.importance == "HIGH"

    def test_upgrade_importance(self):
        assigner = ImportanceAssigner()
        from forensic.evidence.models.evidence import Evidence
        evidence = Evidence(
            id="EVD-001",
            transcript_id="TR-001",
            segment_ids=[],
            category=EvidenceCategory.OTHER,
            description="테스트",
            occurrence_count=5,
            importance="MEDIUM",
        )
        upgraded = assigner.upgrade_importance(evidence)
        assert upgraded is True
        assert evidence.importance == "HIGH"


class TestEvidenceCategorizer:
    def test_categorize_by_pattern(self):
        categorizer = EvidenceCategorizer()
        category = categorizer.categorize_by_pattern("GASLIGHTING")
        assert category == EvidenceCategory.GASLIGHTING

    def test_categorize_by_keywords(self):
        categorizer = EvidenceCategorizer()
        category = categorizer.categorize_by_keywords("금융 계좌를 막아버렸어")
        assert category == EvidenceCategory.FINANCIAL_ABUSE

    def test_categorize_by_keywords_no_match(self):
        categorizer = EvidenceCategorizer()
        category = categorizer.categorize_by_keywords("일반적인 대화 내용")
        assert category is None

    def test_categorize_threat_keywords(self):
        categorizer = EvidenceCategorizer()
        category = categorizer.categorize_by_keywords("죽여버리겠다 폭행할 거다")
        assert category == EvidenceCategory.THREAT

    def test_categorize_isolation_keywords(self):
        categorizer = EvidenceCategorizer()
        category = categorizer.categorize_by_keywords("만나지 말고 연락하지 마")
        assert category == EvidenceCategory.ISOLATION

    def test_categorize_denial_keywords(self):
        categorizer = EvidenceCategorizer()
        category = categorizer.categorize_by_keywords("상상한 거야 기억나지 않아")
        assert category == EvidenceCategory.GASLIGHTING  # Maps to GASLIGHTING

    def test_categorize_combined(self):
        categorizer = EvidenceCategorizer()
        # Pattern should take priority over keywords
        category = categorizer.categorize(
            pattern_type="GASLIGHTING",
            content="금융 돈 관련 내용",  # Financial keywords
        )
        assert category == EvidenceCategory.GASLIGHTING

    def test_categorize_unknown_with_keywords(self):
        categorizer = EvidenceCategorizer()
        category = categorizer.categorize(
            pattern_type="UNKNOWN_PATTERN",
            content="금융 문제로 돈을 요구함",
        )
        assert category == EvidenceCategory.FINANCIAL_ABUSE

    def test_categorize_unknown_fallback(self):
        categorizer = EvidenceCategorizer()
        category = categorizer.categorize(
            pattern_type="UNKNOWN_PATTERN",
            content="unknown keywords here",
        )
        assert category == EvidenceCategory.OTHER

    def test_categorize_empty_keywords(self):
        categorizer = EvidenceCategorizer()
        category = categorizer.categorize(
            pattern_type="UNKNOWN",
            content="",
        )
        assert category == EvidenceCategory.OTHER

    def test_categorize_evidence(self):
        categorizer = EvidenceCategorizer()
        from forensic.evidence.models.evidence import Evidence
        evidence = Evidence(
            id="EVD-001",
            transcript_id="TR-001",
            segment_ids=[],
            category=EvidenceCategory.OTHER,
            description="테스트",
            source_pattern_type="GASLIGHTING",
            content_sample="테스트 내용",
        )
        category = categorizer.categorize_evidence(evidence)
        assert category == EvidenceCategory.GASLIGHTING
        assert evidence.category == EvidenceCategory.GASLIGHTING

    def test_is_repeated_abuse(self):
        categorizer = EvidenceCategorizer()
        assert categorizer.is_repeated_abuse(occurrence_count=5, date_range_days=5) is True
        assert categorizer.is_repeated_abuse(occurrence_count=3, date_range_days=5) is False


class TestEvidenceExtractor:
    def test_extract_from_pattern(self):
        extractor = EvidenceExtractor()
        segments = [
            Segment(
                id="seg-1",
                speaker="A",
                start_time=0.0,
                end_time=5.0,
                content="네가 잘못한 거야",
                confidence=0.9,
            )
        ]
        pattern = PatternMatch(
            pattern_id="PAT-001",
            pattern_type="GASLIGHTING",
            segment_ids=["seg-1"],
            severity="HIGH",
            confidence=0.85,
            description="가스라이팅 패턴 탐지",
        )
        evidence = extractor.extract_from_pattern(pattern, segments)
        assert evidence.category == EvidenceCategory.GASLIGHTING
        assert evidence.source_pattern_type == "GASLIGHTING"
        assert evidence.confidence == 0.85

    def test_extract_batch(self):
        extractor = EvidenceExtractor()
        segments = [
            Segment(
                id="seg-1",
                speaker="A",
                start_time=0.0,
                end_time=5.0,
                content="테스트1",
                confidence=0.9,
            ),
            Segment(
                id="seg-2",
                speaker="B",
                start_time=5.0,
                end_time=10.0,
                content="테스트2",
                confidence=0.9,
            ),
        ]
        patterns = [
            PatternMatch(
                pattern_id="PAT-001",
                pattern_type="GASLIGHTING",
                segment_ids=["seg-1"],
                severity="HIGH",
            ),
            PatternMatch(
                pattern_id="PAT-002",
                pattern_type="EXPLICIT_THREAT",
                segment_ids=["seg-2"],
                severity="HIGH",
            ),
        ]
        evidence_list = extractor.extract_batch(patterns, segments)
        assert len(evidence_list) == 2
        assert evidence_list[0].category == EvidenceCategory.GASLIGHTING
        assert evidence_list[1].category == EvidenceCategory.THREAT

    def test_generate_id(self):
        extractor = EvidenceExtractor()
        id1 = extractor.generate_id()
        assert id1.startswith("EVD-")

    def test_categorize(self):
        extractor = EvidenceExtractor()
        from forensic.evidence.models.evidence import Evidence
        evidence = Evidence(
            id="EVD-001",
            transcript_id="TR-001",
            segment_ids=[],
            category=EvidenceCategory.OTHER,
            description="테스트",
            source_pattern_type="GASLIGHTING",
        )
        category = extractor.categorize(evidence)
        assert category == EvidenceCategory.GASLIGHTING


class TestGlobalFunctions:
    def test_get_id_generator(self):
        gen = get_id_generator()
        assert isinstance(gen, IDGenerator)

    def test_generate_evidence_id_global(self):
        reset_counters()
        id1 = generate_evidence_id()
        assert id1.startswith("EVD-")

    def test_generate_chain_id_global(self):
        reset_counters()
        id1 = generate_chain_id()
        assert id1.startswith("CHN-")

    def test_get_importance_assigner(self):
        assigner = get_importance_assigner()
        assert isinstance(assigner, ImportanceAssigner)

    def test_assign_importance_global(self):
        importance = assign_importance(
            occurrence_count=5,
            pattern_type="GENERIC",
            severity="HIGH",
            confidence=0.9,
        )
        assert importance in ["HIGH", "MEDIUM", "LOW"]

    def test_get_categorizer(self):
        categorizer = get_categorizer()
        assert isinstance(categorizer, EvidenceCategorizer)

    def test_categorize_global(self):
        category = categorize(
            pattern_type="GASLIGHTING",
        )
        assert category == EvidenceCategory.GASLIGHTING

    def test_reset_counters_global(self):
        reset_counters()
        id1 = generate_evidence_id()
        reset_counters()
        id2 = generate_evidence_id()
        assert id1 == id2
