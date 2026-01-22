"""
법적 문서 내보내기 모듈
"""
from pathlib import Path

from forensic.evidence.models.evidence import Evidence
from forensic.evidence.models.export import EvidenceSummary, ExportConfig, LegalDocument


class LegalExporter:
    def __init__(self, config: ExportConfig = None) -> None:
        self.config = config or ExportConfig()

    def export_legal_format(
        self,
        evidence_list: list[Evidence],
        output_path: Path,
        template: str = "korean_criminal",
        case_reference: str | None = None,
    ) -> Path:
        output_path = Path(output_path)
        if not str(output_path).endswith(".md"):
            output_path = output_path.with_suffix(".md")
        output_path.parent.mkdir(parents=True, exist_ok=True)

        filtered = self._filter_by_config(evidence_list)

        document = self._create_legal_document(
            filtered,
            template=template,
            case_reference=case_reference,
        )

        content = self._render_legal_document(document, template)

        with open(output_path, "w", encoding=self.config.output_encoding) as f:
            f.write(content)

        for evidence in filtered:
            evidence.export_status = "EXPORTED"

        return output_path

    def _filter_by_config(self, evidence_list: list[Evidence]) -> list[Evidence]:
        return [e for e in evidence_list if self.config.should_include_evidence(e)]

    def _create_legal_document(
        self,
        evidence_list: list[Evidence],
        template: str,
        case_reference: str | None,
    ) -> LegalDocument:
        from forensic.evidence.extractor.id_generator import generate_document_id

        document = LegalDocument(
            document_id=generate_document_id(),
            title=self._get_title(template),
            case_reference=case_reference,
        )

        for evidence in evidence_list:
            summary = EvidenceSummary.from_evidence(evidence)
            document.add_evidence_summary(summary)

        document.timeline_summary = self._generate_timeline_summary(evidence_list)
        document.pattern_analysis = self._generate_pattern_analysis(evidence_list)
        document.speaker_analysis = self._generate_speaker_analysis(evidence_list)
        document.conclusion = self._generate_conclusion(document, evidence_list)
        document.generate_integrity_statement()

        return document

    def _get_title(self, template: str) -> str:
        titles = {
            "korean_criminal": "형사소송 증거목록",
            "korean_civil": "민사소송 증거목록",
            "investigation": "수사 관련 증거목록",
        }
        return titles.get(template, "증거목록")

    def _generate_timeline_summary(self, evidence_list: list[Evidence]) -> str:
        if not evidence_list:
            return "증거가 없습니다."
        sorted_evidence = sorted(
            [e for e in evidence_list if e.timestamp],
            key=lambda e: e.timestamp,
        )
        if not sorted_evidence:
            return "타임스탬프가 있는 증거가 없습니다."

        lines = ["## 시계열 요약\n"]
        current_date = None
        for evidence in sorted_evidence:
            if evidence.timestamp:
                ev_date = evidence.timestamp.date()
                if ev_date != current_date:
                    lines.append(f"\n### {ev_date}")
                    current_date = ev_date
                time_str = evidence.timestamp.strftime("%H:%M")
                lines.append(
                    f"- **{time_str}** [{evidence.id}] {evidence.description} "
                    f"({evidence.speaker}, {evidence.importance})"
                )
        return "\n".join(lines)

    def _generate_pattern_analysis(self, evidence_list: list[Evidence]) -> str:
        if not evidence_list:
            return "분석할 증거가 없습니다."
        pattern_counts: dict[str, int] = {}
        for e in evidence_list:
            if e.source_pattern_type:
                pattern_counts[e.source_pattern_type] = (
                    pattern_counts.get(e.source_pattern_type, 0) + 1
                )
        lines = ["## 패턴 분석\n"]
        if pattern_counts:
            lines.append("### 탐지된 패턴\n")
            for pattern, count in sorted(
                pattern_counts.items(), key=lambda x: x[1], reverse=True
            ):
                lines.append(f"- **{pattern}**: {count}회")
        category_counts: dict[str, int] = {}
        for e in evidence_list:
            cat = e.category.value
            category_counts[cat] = category_counts.get(cat, 0) + 1
        if category_counts:
            lines.append("\n### 카테고리별 분류\n")
            for category, count in sorted(
                category_counts.items(), key=lambda x: x[1], reverse=True
            ):
                lines.append(f"- **{category}**: {count}건")
        return "\n".join(lines)

    def _generate_speaker_analysis(self, evidence_list: list[Evidence]) -> str:
        if not evidence_list:
            return "분석할 증거가 없습니다."
        speaker_stats: dict[str, dict] = {}
        for e in evidence_list:
            if not e.speaker:
                continue
            if e.speaker not in speaker_stats:
                speaker_stats[e.speaker] = {
                    "total": 0,
                    "high_importance": 0,
                    "categories": {},
                }
            speaker_stats[e.speaker]["total"] += 1
            if e.importance == "HIGH":
                speaker_stats[e.speaker]["high_importance"] += 1
            cat = e.category.value
            speaker_stats[e.speaker]["categories"][cat] = (
                speaker_stats[e.speaker]["categories"].get(cat, 0) + 1
            )
        lines = ["## 화자 분석\n"]
        for speaker, stats in sorted(speaker_stats.items()):
            lines.append(f"\n### {speaker}\n")
            lines.append(f"- 총 증거: {stats['total']}건")
            lines.append(f"- 높은 중요도: {stats['high_importance']}건")
            lines.append("- 카테고리:")
            for cat, count in sorted(
                stats["categories"].items(), key=lambda x: x[1], reverse=True
            ):
                lines.append(f"  - {cat}: {count}건")
        return "\n".join(lines)

    def _generate_conclusion(self, document: LegalDocument, evidence_list: list[Evidence]) -> str:
        high_count = document.get_high_importance_count()
        total_count = document.get_total_evidence_count()
        category_counts = document.get_category_counts()

        lines = [
            "## 결론\n",
            f"- 본 보고서는 총 {total_count}건의 증거를 포함하고 있습니다.",
            f"- 그 중 높은 중요도(HIGH)로 분류된 증거는 {high_count}건입니다.",
        ]

        if category_counts:
            lines.append("\n### 카테고리별 현황\n")
            for cat, count in sorted(
                category_counts.items(), key=lambda x: x[1], reverse=True
            ):
                lines.append(f"- {cat}: {count}건")

        high_importance = [e for e in evidence_list if e.importance == "HIGH"]
        if high_importance:
            lines.append("\n### 주요 관심 증거\n")
            for e in high_importance[:5]:
                ts = e.timestamp.date() if e.timestamp else "N/A"
                lines.append(
                    f"- **{e.id}**: {e.description} ({e.source_pattern_type}, {ts})"
                )

        return "\n".join(lines)

    def _render_legal_document(self, document: LegalDocument, template: str) -> str:
        if template == "korean_criminal":
            return self._render_korean_criminal(document)
        elif template == "korean_civil":
            return self._render_korean_civil(document)
        else:
            return self._render_default(document)

    def _render_korean_criminal(self, document: LegalDocument) -> str:
        lines = [
            "# 형사소송 증거목록",
            "",
            f"**문서 번호**: {document.document_id}",
            f"**사건 번호**: {document.case_reference or '미지정'}",
            f"**작성일**: {document.generated_at.strftime('%Y년 %m월 %d일')}",
            "",
            "---",
            "",
            document.timeline_summary,
            "",
            "---",
            "",
            document.pattern_analysis,
            "",
            "---",
            "",
            document.speaker_analysis,
            "",
            "---",
            "",
            document.conclusion,
            "",
            "---",
            "",
            "## 무결성 보증",
            "",
            document.integrity_statement,
            "",
            "---",
            "",
            "**작성자**: ____________________",
            "**확인자**: ____________________",
        ]
        return "\n".join(lines)

    def _render_korean_civil(self, document: LegalDocument) -> str:
        lines = [
            "# 민사소송 증거목록",
            "",
            f"**문서 번호**: {document.document_id}",
            f"**사건 번호**: {document.case_reference or '미지정'}",
            f"**작성일**: {document.generated_at.strftime('%Y년 %m월 %d일')}",
            "",
            "---",
            "",
            document.timeline_summary,
            "",
            "---",
            "",
            document.pattern_analysis,
            "",
            "---",
            "",
            document.speaker_analysis,
            "",
            "---",
            "",
            document.conclusion,
            "",
            "---",
            "",
            "## 무결성 보증",
            "",
            document.integrity_statement,
            "",
            "---",
            "",
            "**작성자**: ____________________",
            "**확인자**: ____________________",
        ]
        return "\n".join(lines)

    def _render_default(self, document: LegalDocument) -> str:
        lines = [
            "# 증거목록",
            "",
            f"**문서 번호**: {document.document_id}",
            f"**작성일**: {document.generated_at.strftime('%Y년 %m월 %d일')}",
            "",
            "---",
            "",
            document.timeline_summary,
            "",
            "---",
            "",
            document.pattern_analysis,
            "",
            "---",
            "",
            document.speaker_analysis,
            "",
            "---",
            "",
            document.conclusion,
            "",
            "---",
            "",
            "## 무결성 보증",
            "",
            document.integrity_statement,
        ]
        return "\n".join(lines)


__all__ = ["LegalExporter"]
