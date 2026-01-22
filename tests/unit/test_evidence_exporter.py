"""
Exporter 모듈 단위 테스트
"""
import json
import pytest
from datetime import datetime
from pathlib import Path

from forensic.evidence.exporter import ChainExporter, JSONExporter, LegalExporter
from forensic.evidence.models.evidence import Evidence, EvidenceCategory
from forensic.evidence.models.export import ExportConfig


@pytest.fixture
def temp_output_dir(tmp_path: Path) -> Path:
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    return output_dir


@pytest.fixture
def sample_evidence_list() -> list[Evidence]:
    # ID 생성을 통해 올바른 형식의 ID 사용
    from forensic.evidence.extractor.id_generator import reset_counters
    reset_counters()
    
    evidence_list = []
    for i in range(1, 10):
        from forensic.evidence.extractor.id_generator import generate_evidence_id
        eid = generate_evidence_id()
        
        evidence_list.append(
            Evidence(
                id=eid,
                transcript_id="TR-001",
                segment_ids=[f"seg-{i}"],
                category=[
                    EvidenceCategory.THREAT,
                    EvidenceCategory.GASLIGHTING,
                    EvidenceCategory.EMOTIONAL_MANIPULATION,
                ][i % 3],
                description=f"증거 {i}",
                importance=["HIGH", "MEDIUM", "LOW"][i % 3],
                speaker="A" if i % 2 == 0 else "B",
                content_sample=f"내용 {i}",
                timestamp=datetime(2025, 1, 1 + i // 5, 12, 0, 0),
                context_before="이전 맥락",
                context_after="이후 맥락",
                integrity_hash=f"hash-{i}",
            )
        )
    return evidence_list


class TestExportConfig:
    def test_should_include_by_importance(self):
        config = ExportConfig(min_importance="HIGH")

        high_evidence = Evidence(
            id="EVD-TEST-001",
            transcript_id="TR-001",
            segment_ids=[],
            category=EvidenceCategory.OTHER,
            description="HIGH",
            importance="HIGH",
        )

        low_evidence = Evidence(
            id="EVD-TEST-002",
            transcript_id="TR-001",
            segment_ids=[],
            category=EvidenceCategory.OTHER,
            description="LOW",
            importance="LOW",
        )

        assert config.should_include_evidence(high_evidence) is True
        assert config.should_include_evidence(low_evidence) is False

    def test_get_file_extension(self):
        config = ExportConfig(format="JSON")
        assert config.get_file_extension() == ".json"

        config.format = "LEGAL"
        assert config.get_file_extension() == ".md"


class TestJSONExporter:
    def test_export_json(self, temp_output_dir: Path, sample_evidence_list: list[Evidence]):
        exporter = JSONExporter()
        output_path = temp_output_dir / "evidence"

        result_path = exporter.export_json(
            sample_evidence_list, output_path, include_context=True
        )

        assert result_path.exists()
        assert result_path.suffix == ".json"

        with open(result_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert "evidence" in data
        assert data["total_count"] == len(sample_evidence_list)


class TestLegalExporter:
    def test_export_legal_format(
        self, temp_output_dir: Path, sample_evidence_list: list[Evidence]
    ):
        exporter = LegalExporter()
        output_path = temp_output_dir / "legal"

        result_path = exporter.export_legal_format(
            sample_evidence_list, output_path, template="korean_criminal"
        )

        assert result_path.exists()
        assert result_path.suffix == ".md"

        with open(result_path, "r", encoding="utf-8") as f:
            content = f.read()

        assert "형사소송 증거목록" in content
        assert "무결성" in content


class TestChainExporter:
    def test_export_chain_of_custody(
        self, temp_output_dir: Path, sample_evidence_list: list[Evidence]
    ):
        exporter = ChainExporter()
        output_path = temp_output_dir / "chain"

        result_path = exporter.export_chain_of_custody(sample_evidence_list, output_path)

        assert result_path.exists()

        with open(result_path, "r", encoding="utf-8") as f:
            content = f.read()

        assert "Chain of Custody" in content or "증거 관리" in content

    def test_export_summary(
        self, temp_output_dir: Path, sample_evidence_list: list[Evidence]
    ):
        exporter = ChainExporter()
        output_path = temp_output_dir / "summary"

        result_path = exporter.export_summary(sample_evidence_list, output_path)

        assert result_path.exists()

        with open(result_path, "r", encoding="utf-8") as f:
            content = f.read()

        assert "요약" in content or "증거" in content
