"""
Gaslighting Detection Module

Detects gaslighting patterns in speech for forensic analysis.
Identifies manipulation techniques used in abusive relationships.

REQ-T-005: Gaslighting pattern detection.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from forensic.models.speech import GaslightingIndicator, GaslightingType

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


@dataclass
class GaslightingPattern:
    """A gaslighting pattern with regex and metadata."""

    name: str
    type: GaslightingType
    patterns: list[str]
    keywords: list[str]
    severity: str = "MEDIUM"
    examples: list[str] | None = None


class GaslightingPatterns:
    """
    Korean gaslighting patterns for detection.

    Based on psychological research on gaslighting in Korean context.
    """

    # Denial patterns (부정)
    DENIAL = GaslightingPattern(
        name="denial",
        type=GaslightingType.DENIAL,
        patterns=[
            r"그런 적 없[어아]",
            r"네가 착각한 거[야여요]",
            r"기억이 잘못됐[어아]",
            r"나는 절대 안 그랬[어아]",
            r"거짓말이[야여요]",
            r"허위사실 유포[이야요]",
        ],
        keywords=["아니라고", "없다고", "거짓말", "착각", "기억 오류"],
        severity="MEDIUM",
        examples=[
            "나는 너한테 그런 말 한 적 없어.",
            "네가 기억을 잘못하고 있는 거야.",
            "그건 네가 지어낸 이야기야.",
        ],
    )

    # Counter-attack patterns (반격)
    COUNTER_ATTACK = GaslightingPattern(
        name="counter_attack",
        type=GaslightingType.COUNTER_ATTACK,
        patterns=[
            r"네가 문제[이야야]",
            r"네 탓[이야야]",
            r"너만 그렇[게 생겼어]",
            r"네가 너무 예민하[ glove]",
            r"네가 이상하[ glove]",
        ],
        keywords=["너 때문에", "네가", "너만", "네 탓", "너랑"],
        severity="HIGH",
        examples=[
            "문제는 너야, 네가 예민한 거야.",
            "너만 그렇게 생각해, 정상적인 사람은 아무도 안 그래.",
            "네가 나를 화나게 만들었어.",
        ],
    )

    # Trivializing patterns (축소)
    TRIVIALIZING = GaslightingPattern(
        name="trivializing",
        type=GaslightingType.TRIVIALIZING,
        patterns=[
            r"그거 별거 아[닌야]",
            r"과민 반응[이야요]",
            r"장난[이야이었어]",
            r"농담[이야이었어]",
            r"심각하게 받아들이지 마[ glove]",
        ],
        keywords=["별거 아냐", "과민", "장난", "농담", "심각"],
        severity="MEDIUM",
        examples=[
            "그거 별거 아니야, 왜 그렇게 심각하게 받아들여?",
            "농담이었어, 왜 화를 내?",
            "너네가 그걸로 화를 다냐?",
        ],
    )

    # Forgetting/Denial of memory (망각)
    FORGETTING = GaslightingPattern(
        name="forgetting",
        type=GaslightingType.FORGETTING,
        patterns=[
            r"기억 안 나[ glove]",
            r"모르겠[ glove]",
            r"그런 일 없었[는데는데]",
            r"네가 말한 적 있[ 니 ]? ",
            r"아 정말[ glove]? 기억이 안 나네",
        ],
        keywords=["기억 안 나", "모르겠", "못 알아듣겠", "무슨 소리야"],
        severity="MEDIUM",
        examples=[
            "기억 안 나, 네가 내게 그런 말 한 적 없는데.",
            "뭔 소리야, 모르겠는데.",
            "내가 언제 그랬다고?",
        ],
    )

    # Blocking/Diversion (차단)
    BLOCKING = GaslightingPattern(
        name="blocking",
        type=GaslightingType.BLOCKING,
        patterns=[
            r"화제 변경",
            r"다른 이야기[하자로]",
            r"그건 중요하지 않[ glove]",
            r"집중하지 마[ glove]",
            r"신경 쓰지 마[ glove]",
        ],
        keywords=["topic change", "subject change", "not important", "focus on"],
        severity="LOW",
        examples=[
            "그건 중요하지 않아, 다른 이야기 하자.",
            "왜 그걸로 꼬투리를 잡아?",
            "우리 더 중요한 이야기나 하자.",
        ],
    )

    # Gaslighting by proxy (대리 가스라이팅)
    PROXY = GaslightingPattern(
        name="proxy",
        type=GaslightingType.GASLIGHTING_BY_PROXY,
        patterns=[
            r"[다른 사람]도 널 그렇게 생 각[해해요]",
            r"모두가 널 이상하다고 해[ glove]",
            r"사람들[이야말이] 다 네 말을 안 민[어어요]",
        ],
        keywords=["모두가", "사람들이", "다른 사람도", "남들도"],
        severity="HIGH",
        examples=[
            "다른 사람들도 널 그렇게 생각해.",
            "우리 친구들도 네가 이상하다고 해.",
            "누구도 네 말을 안 믌 거야.",
        ],
    )

    @classmethod
    def all_patterns(cls) -> list[GaslightingPattern]:
        """Get all gaslighting patterns."""
        return [
            cls.DENIAL,
            cls.COUNTER_ATTACK,
            cls.TRIVIALIZING,
            cls.FORGETTING,
            cls.BLOCKING,
            cls.PROXY,
        ]


class GaslightingDetector:
    """
    Gaslighting pattern detector for forensic analysis.

    Analyzes text for gaslighting manipulation patterns.
    """

    def __init__(self) -> None:
        """Initialize the detector."""
        self.patterns = GaslightingPatterns.all_patterns()
        self._compiled_patterns = self._compile_patterns()

    def _compile_patterns(self) -> list[tuple[GaslightingPattern, list[re.Pattern]]]:
        """Compile regex patterns for matching."""
        compiled = []

        for pattern_def in self.patterns:
            compiled_regex = []
            for pattern_str in pattern_def.patterns:
                try:
                    compiled_regex.append(re.compile(pattern_str, re.IGNORECASE))
                except re.error:
                    logger.warning(f"Invalid regex pattern: {pattern_str}")
            compiled.append((pattern_def, compiled_regex))

        return compiled

    def detect_in_text(
        self,
        text: str,
        segment_id: str = "",
    ) -> list[GaslightingIndicator]:
        """
        Detect gaslighting patterns in text.

        Args:
            text: Text to analyze
            segment_id: Segment identifier

        Returns:
            List of detected gaslighting indicators
        """
        indicators: list[GaslightingIndicator] = []

        for pattern_def, regexes in self._compiled_patterns:
            matches: list[tuple[str, int, int]] = []

            # Find all matches
            for regex in regexes:
                for match in regex.finditer(text):
                    matches.append((match.group(), match.start(), match.end()))

            if matches:
                # Find best match (longest)
                best_match = max(matches, key=lambda m: len(m[0]))

                indicator = GaslightingIndicator(
                    segment_id=segment_id,
                    type=pattern_def.type,
                    severity=pattern_def.severity,
                    confidence=self._calculate_confidence(text, pattern_def),
                    evidence=best_match[0],
                    context=self._get_context(text, best_match[1], best_match[2]),
                )
                indicators.append(indicator)

        return indicators

    def _calculate_confidence(self, text: str, pattern: GaslightingPattern) -> float:
        """
        Calculate confidence score for detection.

        Args:
            text: Text being analyzed
            pattern: Pattern that matched

        Returns:
            Confidence score (0-1)
        """
        # Base confidence from keyword presence
        keyword_count = sum(1 for kw in pattern.keywords if kw in text)
        base_confidence = min(1.0, keyword_count / 3.0 + 0.5)

        # Adjust based on severity
        if pattern.severity == "HIGH":
            base_confidence *= 1.1
        elif pattern.severity == "LOW":
            base_confidence *= 0.9

        return float(min(1.0, base_confidence))

    def _get_context(
        self,
        text: str,
        start: int,
        end: int,
        context_size: int = 50,
    ) -> str:
        """
        Get context around a match.

        Args:
            text: Full text
            start: Match start position
            end: Match end position
            context_size: Context window size

        Returns:
            Context string
        """
        context_start = max(0, start - context_size)
        context_end = min(len(text), end + context_size)

        context = text[context_start:context_end]

        # Add ellipsis if truncated
        prefix = "..." if context_start > 0 else ""
        suffix = "..." if context_end < len(text) else ""

        return prefix + context + suffix

    def detect_from_transcript(
        self,
        transcript: str,
        segment_id: str = "",
    ) -> list[GaslightingIndicator]:
        """
        Detect gaslighting in a transcript.

        Args:
            transcript: Full transcript text
            segment_id: Segment identifier

        Returns:
            List of gaslighting indicators
        """
        return self.detect_in_text(transcript, segment_id)

    def detect_from_segments(
        self,
        segments: list[tuple[str, str]],  # (segment_id, text)
    ) -> list[GaslightingIndicator]:
        """
        Detect gaslighting in multiple segments.

        Args:
            segments: List of (segment_id, text) tuples

        Returns:
            List of gaslighting indicators
        """
        indicators: list[GaslightingIndicator] = []

        for segment_id, text in segments:
            segment_indicators = self.detect_in_text(text, segment_id)
            indicators.extend(segment_indicators)

        return indicators

    def get_statistics(
        self,
        indicators: list[GaslightingIndicator],
    ) -> dict[str, int | dict[str, int]]:
        """
        Get statistics on detected gaslighting.

        Args:
            indicators: List of gaslighting indicators

        Returns:
            Statistics dictionary
        """
        total_count = len(indicators)

        type_counts: dict[str, int] = {}
        severity_counts: dict[str, int] = {}

        for indicator in indicators:
            type_name = indicator.type.value
            type_counts[type_name] = type_counts.get(type_name, 0) + 1

            severity_counts[indicator.severity] = severity_counts.get(indicator.severity, 0) + 1

        return {
            "total_count": total_count,
            "by_type": type_counts,
            "by_severity": severity_counts,
        }

    def classify_severity(
        self,
        indicators: list[GaslightingIndicator],
    ) -> str:
        """
        Classify overall severity of gaslighting.

        Args:
            indicators: List of gaslighting indicators

        Returns:
            Overall severity level (LOW, MEDIUM, HIGH)
        """
        if not indicators:
            return "NONE"

        high_count = sum(1 for i in indicators if i.severity == "HIGH")
        medium_count = sum(1 for i in indicators if i.severity == "MEDIUM")

        if high_count >= 2 or (high_count >= 1 and medium_count >= 3):
            return "HIGH"
        elif medium_count >= 2 or high_count >= 1:
            return "MEDIUM"
        else:
            return "LOW"


class GaslightingReportGenerator:
    """
    Generate human-readable gaslighting detection reports.
    """

    def __init__(self) -> None:
        """Initialize the report generator."""
        self.detector = GaslightingDetector()

    def generate_report(
        self,
        indicators: list[GaslightingIndicator],
        _transcript_text: str = "",
    ) -> str:
        """
        Generate a gaslighting detection report.

        Args:
            indicators: List of detected indicators
            transcript_text: Full transcript for context

        Returns:
            Formatted report string
        """
        lines: list[str] = []

        lines.append("=" * 60)
        lines.append("가스라이팅 탐지 보고서 (Gaslighting Detection Report)")
        lines.append("=" * 60)
        lines.append("")

        # Summary
        stats = self.detector.get_statistics(indicators)
        overall_severity = self.detector.classify_severity(indicators)

        lines.append("## 개요 (Summary)")
        lines.append(f"탐지된 패턴 수: {stats['total_count']}")
        lines.append(f"전체 심각도: {overall_severity}")
        lines.append("")

        # By type
        if stats["by_type"]:
            lines.append("## 패턴 유형별 분류 (By Type)")
            for type_name, count in stats["by_type"].items():
                type_korean = self._get_type_korean(type_name)
                lines.append(f"  - {type_korean}: {count}건")
            lines.append("")

        # By severity
        if stats["by_severity"]:
            lines.append("## 심각도별 분류 (By Severity)")
            for severity, count in sorted(stats["by_severity"].items()):
                lines.append(f"  - {severity}: {count}건")
            lines.append("")

        # Detailed findings
        if indicators:
            lines.append("## 상세 발견 사항 (Detailed Findings)")
            for i, indicator in enumerate(indicators, 1):
                lines.append(
                    f"{i}. [{indicator.type.value.upper()}] (심각도: {indicator.severity})"
                )
                lines.append(f"   증거: {indicator.evidence}")
                if indicator.context:
                    lines.append(f"   맥락: {indicator.context}")
                lines.append("")

        # Conclusion
        lines.append("## 결론 (Conclusion)")
        conclusion = self._generate_conclusion(overall_severity, stats["total_count"])
        lines.append(conclusion)
        lines.append("")
        lines.append("=" * 60)

        return "\n".join(lines)

    def _get_type_korean(self, type_name: str) -> str:
        """Get Korean name for gaslighting type."""
        korean_names = {
            "denial": "부정",
            "counter_attack": "반격",
            "trivializing": "축소",
            "forgetting": "망각",
            "blocking": "차단",
            "proxy": "대리 가스라이팅",
        }
        return korean_names.get(type_name, type_name)

    def _generate_conclusion(self, severity: str, count: int) -> str:
        """Generate conclusion text."""
        conclusions = {
            "HIGH": (
                f"고위험 수준의 가스라이팅 패턴이 {count}건 탐지되었습니다. "
                "전문가의 추가 검토가 권장됩니다."
            ),
            "MEDIUM": (
                f"중간 수준의 가스라이팅 패턴이 {count}건 탐지되었습니다. "
                "지속적인 관찰이 필요합니다."
            ),
            "LOW": f"저위험 수준의 가스라이팅 패턴이 {count}건 탐지되었습니다.",
        }
        return conclusions.get(severity, "가스라이팅 패턴이 탐지되지 않았습니다.")
