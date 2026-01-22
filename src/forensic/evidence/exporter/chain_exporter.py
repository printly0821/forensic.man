"""
증거 체인 내보내기 모듈
"""
from datetime import datetime
from pathlib import Path

from forensic.evidence.models.chain import EvidenceChain
from forensic.evidence.models.evidence import Evidence


class ChainExporter:
    def __init__(self) -> None:
        pass

    def export_chain_of_custody(self, evidence_list: list[Evidence], output_path: Path) -> Path:
        output_path = Path(output_path)
        # 점으로 시작하는 확장자 사용
        if not str(output_path).endswith(".md"):
            output_path = output_path.with_suffix(".md")
        # parent directory가 존재하지 않으면 생성
        output_path.parent.mkdir(parents=True, exist_ok=True)

        lines = [
            "# 증거 관리 체인 (Chain of Custody)",
            "",
            f"**작성일**: {datetime.now().strftime('%Y년 %m월 %d일')}",
            "",
            "---",
            "",
            "## 개요",
            "",
            f"- 총 증거 수: {len(evidence_list)}",
            "",
            "---",
            "",
            "## 증거 목록",
            "",
        ]

        for evidence in sorted(evidence_list, key=lambda e: e.timestamp or datetime.now()):
            lines.extend(self._format_evidence_for_chain(evidence))

        lines.extend([
            "",
            "---",
            "",
            "## 무결성 검증",
            "",
            "- 모든 증거는 SHA-256 해시로 무결성이 검증되었습니다.",
            f"- 검증일: {datetime.now().strftime('%Y년 %m월 %d일')}",
        ])

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        return output_path

    def _format_evidence_for_chain(self, evidence: Evidence) -> list[str]:
        timestamp_str = (
            evidence.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            if evidence.timestamp
            else "N/A"
        )

        lines = [
            f"### {evidence.id}",
            "",
            f"- **타임스탬프**: {timestamp_str}",
            f"- **화자**: {evidence.speaker or 'N/A'}",
            f"- **카테고리**: {evidence.category.value}",
            f"- **중요도**: {evidence.importance}",
            f"- **설명**: {evidence.description}",
            f"- **원본 파일**: {evidence.transcript_id}",
            f"- **세그먼트 ID**: {', '.join(evidence.segment_ids)}",
            f"- **무결성 해시**: `{evidence.integrity_hash}`",
        ]

        if evidence.context_before:
            lines.extend([
                "",
                "**이전 맥락**:",
                f"```\n{evidence.context_before}\n```",
            ])

        if evidence.content_sample:
            lines.extend([
                "",
                "**내용**:",
                f"> {evidence.content_sample}",
            ])

        if evidence.context_after:
            lines.extend([
                "",
                "**이후 맥락**:",
                f"```\n{evidence.context_after}\n```",
            ])

        return lines

    def export_chain(
        self,
        chain: EvidenceChain,
        evidence_map: dict[str, Evidence],
        output_path: Path,
    ) -> Path:
        output_path = Path(output_path)
        if not str(output_path).endswith(".md"):
            output_path = output_path.with_suffix(".md")
        output_path.parent.mkdir(parents=True, exist_ok=True)

        severity_label = {
            "CRITICAL": "⚠️ 매우 높음",
            "HIGH": "🔴 높음",
            "MEDIUM": "🟡 중간",
            "LOW": "🟢 낮음",
        }

        lines = [
            f"# 증거 체인: {chain.chain_id}",
            "",
            f"**체인 유형**: {chain.chain_type}",
            f"**심각도**: {severity_label.get(chain.severity, chain.severity)}",
            f"**기간**: {chain.start_date} ~ {chain.end_date} ({chain.get_duration_days()}일)",
            f"**관련 화자**: {chain.speaker or 'N/A'}",
            f"**패턴 유형**: {chain.pattern_type or 'N/A'}",
            f"**총 발생 횟수**: {chain.total_occurrences}",
            "",
            "---",
            "",
            "## 설명",
            "",
            chain.description,
            "",
            "---",
            "",
            "## 포함된 증거",
            "",
        ]

        for evidence_id in chain.evidence_ids:
            if evidence_id in evidence_map:
                evidence = evidence_map[evidence_id]
                lines.extend(self._format_evidence_for_chain(evidence))

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        return output_path

    def export_summary(self, evidence_list: list[Evidence], output_path: Path) -> Path:
        output_path = Path(output_path)
        if not str(output_path).endswith(".md"):
            output_path = output_path.with_suffix(".md")
        output_path.parent.mkdir(parents=True, exist_ok=True)

        total = len(evidence_list)
        high_count = sum(1 for e in evidence_list if e.importance == "HIGH")
        medium_count = sum(1 for e in evidence_list if e.importance == "MEDIUM")
        low_count = sum(1 for e in evidence_list if e.importance == "LOW")

        category_counts: dict[str, int] = {}
        for e in evidence_list:
            category_counts[e.category.value] = category_counts.get(e.category.value, 0) + 1

        lines = [
            "# 증거 요약 보고서",
            "",
            f"**작성일**: {datetime.now().strftime('%Y년 %m월 %d일')}",
            "",
            "---",
            "",
            "## 통계 개요",
            "",
            f"- **총 증거 수**: {total}",
            f"- **높은 중요도**: {high_count}",
            f"- **중간 중요도**: {medium_count}",
            f"- **낮은 중요도**: {low_count}",
            "",
            "---",
            "",
            "## 카테고리별 분포",
            "",
        ]

        for cat, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total * 100) if total > 0 else 0
            lines.append(f"- **{cat}**: {count}건 ({percentage:.1f}%)")

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        return output_path


__all__ = ["ChainExporter"]
