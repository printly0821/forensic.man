"""
검증 보고서 생성 모듈
"""
from pathlib import Path
from typing import Any

from forensic.evidence.models.validation import (
    MergeProposal,
    ValidationReport,
    ValidationResult,
)


class ReportGenerator:
    def __init__(self) -> None:
        pass

    def generate_text_report(self, report: ValidationReport) -> str:
        lines = [
            "=" * 60,
            "증거 검증 보고서",
            "=" * 60,
            f"보고서 ID: {report.report_id}",
            f"생성 시점: {report.generated_at.strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "-" * 60,
            "요약",
            "-" * 60,
            report.summary or report.generate_summary(),
            f"무결성 점수: {report.integrity_score * 100:.1f}%",
            "",
            "-" * 60,
            "검증 결과 상세",
            "-" * 60,
        ]

        for result in report.validation_results:
            lines.extend(self._format_result(result))

        invalid_ids = report.get_invalid_evidence_ids()
        if invalid_ids:
            lines.extend([
                "",
                "-" * 60,
                "무효 증거 목록",
                "-" * 60,
            ])
            for eid in invalid_ids:
                lines.append(f"  - {eid}")

        duplicate_groups = report.get_duplicate_groups()
        if duplicate_groups:
            lines.extend([
                "",
                "-" * 60,
                "중복 증거 그룹",
                "-" * 60,
            ])
            for primary, duplicates in duplicate_groups.items():
                lines.append(f"  {primary} -> {', '.join(duplicates)}")

        lines.append("=" * 60)

        return "\n".join(lines)

    def _format_result(self, result: ValidationResult) -> list[str]:
        status = "O 유효" if result.is_valid else "X 무효"
        lines = [
            "",
            f"증거: {result.evidence_id} ({status})",
            f"  타임스탬프: {'O' if result.timestamp_valid else 'X'}",
            f"  원본 참조: {'O' if result.source_valid else 'X'}",
            f"  해시 검증: {'O' if result.hash_valid else 'X'}",
        ]

        if result.duplicate_found:
            lines.append(f"  중복 발견: {len(result.duplicate_ids)}개")
            for dup_id in result.duplicate_ids:
                lines.append(f"    - {dup_id}")

        if result.issues:
            lines.append("  문제점:")
            for issue in result.issues:
                lines.append(f"    - {issue}")

        if result.recommendations:
            lines.append("  권장 조치:")
            for rec in result.recommendations:
                lines.append(f"    - {rec}")

        return lines

    def generate_json_report(self, report: ValidationReport) -> dict[str, Any]:
        return {
            "report_id": report.report_id,
            "generated_at": report.generated_at.isoformat(),
            "summary": {
                "total_evidence": report.total_evidence,
                "valid_count": report.valid_count,
                "invalid_count": report.invalid_count,
                "duplicate_count": report.duplicate_count,
                "integrity_score": report.integrity_score,
                "summary_text": report.summary,
            },
            "validation_results": [
                {
                    "evidence_id": r.evidence_id,
                    "is_valid": r.is_valid,
                    "timestamp_valid": r.timestamp_valid,
                    "source_valid": r.source_valid,
                    "hash_valid": r.hash_valid,
                    "duplicate_found": r.duplicate_found,
                    "duplicate_ids": r.duplicate_ids,
                    "validation_time": r.validation_time.isoformat(),
                    "issues": r.issues,
                    "recommendations": r.recommendations,
                    "severity": r.get_severity(),
                }
                for r in report.validation_results
            ],
            "invalid_evidence_ids": report.get_invalid_evidence_ids(),
            "duplicate_groups": report.get_duplicate_groups(),
        }

    def save_report(
        self,
        report: ValidationReport,
        output_path: Path,
        format_type: str = "text",
    ) -> Path:
        output_path = Path(output_path)

        if format_type == "json":
            import json
            content = self.generate_json_report(report)
            output_path = output_path.with_suffix(".json")
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(content, f, ensure_ascii=False, indent=2)
        else:
            content = self.generate_text_report(report)
            output_path = output_path.with_suffix(".txt")
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(content)

        return output_path

    def generate_merge_proposal_text(self, proposal: MergeProposal) -> str:
        lines = [
            "=" * 60,
            "증거 병합 제안",
            "=" * 60,
            f"주 증거 ID: {proposal.primary_evidence_id}",
            f"병합 대상: {len(proposal.duplicate_evidence_ids)}개",
            "",
            "병합 대상 목록:",
        ]

        for dup_id in proposal.duplicate_evidence_ids:
            lines.append(f"  - {dup_id}")

        lines.extend([
            "",
            f"사유: {proposal.reason}",
            f"신뢰도: {proposal.confidence:.2f}",
            f"제안 중요도: {proposal.merged_importance}",
            "",
            "병합 후 설명:",
            f"  {proposal.merged_description}",
            "=" * 60,
        ])

        return "\n".join(lines)


__all__ = ["ReportGenerator"]
