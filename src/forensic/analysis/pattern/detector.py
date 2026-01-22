"""
Pattern detection implementation for forensic transcript analysis.
"""

import re
from datetime import datetime
from typing import TYPE_CHECKING, Literal
from uuid import uuid4

if TYPE_CHECKING:
    from forensic.analysis.pattern.models import (
        EmotionalManipulation,
        GaslightingPattern,
        RepeatedStatement,
        ThreatPattern,
    )
    from forensic.models.transcript import Evidence, Segment, Transcript

from forensic.models.transcript import Evidence


class PatternDetector:
    """
    Comprehensive pattern detector for manipulation patterns.

    Detects gaslighting, emotional manipulation, threats, and repeated
    statements across transcript segments.

    Usage:
        detector = PatternDetector()
        patterns = detector.detect_gaslighting(segments)
        threats = detector.detect_threats(segments)
        all_evidence = detector.detect_all(transcript)
    """

    # Default detection thresholds
    DEFAULT_CONFIDENCE_THRESHOLD = 0.7
    DEFAULT_REPETITION_THRESHOLD = 3
    DEFAULT_INTENSITY_THRESHOLD: Literal["HIGH", "MEDIUM", "LOW"] = "MEDIUM"
    DEFAULT_SEVERITY_THRESHOLD: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"] = "LOW"

    def __init__(
        self,
        confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
        repetition_threshold: int = DEFAULT_REPETITION_THRESHOLD,
        intensity_threshold: Literal["HIGH", "MEDIUM", "LOW"] = DEFAULT_INTENSITY_THRESHOLD,
        severity_threshold: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"] = DEFAULT_SEVERITY_THRESHOLD,
    ) -> None:
        """
        Initialize the pattern detector.

        Args:
            confidence_threshold: Minimum confidence for pattern detection
            repetition_threshold: Minimum occurrences for repeated statements
            intensity_threshold: Minimum intensity for emotional manipulation
            severity_threshold: Minimum severity for threat detection
        """
        self._confidence_threshold = confidence_threshold
        self._repetition_threshold = repetition_threshold
        self._intensity_threshold = intensity_threshold
        self._severity_threshold = severity_threshold
        self._custom_patterns: dict[str, dict[str, list[str]]] = {}

    def add_custom_pattern(
        self,
        name: str,
        keywords: list[str],
        pattern_type: Literal["gaslighting", "manipulation", "threat"] = "gaslighting",
        context_rules: dict | None = None,  # noqa: ARG002 - Reserved for future use
    ) -> None:
        """
        Add a user-defined pattern for detection.

        Args:
            name: Unique name for the custom pattern
            keywords: List of keyword phrases to detect
            pattern_type: Type of pattern (gaslighting, manipulation, or threat)
            context_rules: Optional rules for context validation (reserved for future use)
        """
        if pattern_type not in self._custom_patterns:
            self._custom_patterns[pattern_type] = {}
        self._custom_patterns[pattern_type][name] = keywords

    def detect_gaslighting(
        self,
        segments: list[Segment],
    ) -> list[GaslightingPattern]:
        """
        Detect gaslighting patterns in transcript segments.

        Args:
            segments: List of segments to analyze

        Returns:
            List of detected gaslighting patterns
        """
        from forensic.analysis.pattern.keywords import KeywordDictionary
        from forensic.analysis.pattern.models import GaslightingPattern

        patterns: list[GaslightingPattern] = []

        for segment in segments:
            content = segment.content.lower()

            for pattern_type, keywords in KeywordDictionary.GASLIGHTING.items():
                matches = self._find_keyword_matches(content, keywords)

                if matches:
                    # Calculate confidence based on match strength
                    confidence = self._calculate_confidence(matches, keywords)

                    if confidence >= self._confidence_threshold:
                        pattern = GaslightingPattern(
                            pattern_type=pattern_type,
                            segment_ids=[segment.id],
                            speaker=segment.speaker,
                            content_sample=matches[0] if matches else segment.content[:100],
                            confidence=confidence,
                            context_before=self._get_context_before(),
                            context_after=self._get_context_after(),
                        )
                        patterns.append(pattern)

        return self._merge_gaslighting_patterns(patterns)

    def detect_repeated_statements(
        self,
        segments: list[Segment],
        threshold: int | None = None,
    ) -> list[RepeatedStatement]:
        """
        Detect repeated statements across segments.

        Args:
            segments: List of segments to analyze
            threshold: Minimum occurrences for a repeated statement

        Returns:
            List of detected repeated statements
        """
        from forensic.analysis.pattern.models import RepeatedStatement, StatementOccurrence

        min_threshold = threshold or self._repetition_threshold
        statements: dict[str, RepeatedStatement] = {}

        for segment in segments:
            # Normalize content for comparison
            normalized = self._normalize_text(segment.content)

            if normalized not in statements:
                statements[normalized] = RepeatedStatement(
                    pattern=normalized,
                    speaker=segment.speaker,
                    first_occurrence=datetime.now(),
                    last_occurrence=datetime.now(),
                )

            occurrence = StatementOccurrence(
                segment_id=segment.id,
                timestamp=datetime.now(),
                speaker=segment.speaker,
                content=segment.content,
            )

            statements[normalized].add_occurrence(occurrence)

        # Filter by threshold
        return [
            s for s in statements.values()
            if s.total_count >= min_threshold
        ]

    def detect_emotional_manipulation(
        self,
        segments: list[Segment],
    ) -> list[EmotionalManipulation]:
        """
        Detect emotional manipulation patterns.

        Args:
            segments: List of segments to analyze

        Returns:
            List of detected emotional manipulation patterns
        """
        from forensic.analysis.pattern.keywords import KeywordDictionary
        from forensic.analysis.pattern.models import EmotionalManipulation

        patterns: list[EmotionalManipulation] = []

        for segment in segments:
            content = segment.content.lower()

            for manipulation_type, keywords in KeywordDictionary.EMOTIONAL_MANIPULATION.items():
                matches = self._find_keyword_matches(content, keywords)

                if matches:
                    intensity = self._calculate_intensity(matches)

                    if self._meets_intensity_threshold(intensity):
                        pattern = EmotionalManipulation(
                            manipulation_type=manipulation_type,
                            segment_ids=[segment.id],
                            speaker=segment.speaker,
                            content_sample=matches[0] if matches else segment.content[:100],
                            intensity=intensity,
                        )
                        patterns.append(pattern)

        return patterns

    def detect_threats(
        self,
        segments: list[Segment],
    ) -> list[ThreatPattern]:
        """
        Detect threat and coercion patterns.

        Args:
            segments: List of segments to analyze

        Returns:
            List of detected threat patterns
        """
        from forensic.analysis.pattern.keywords import KeywordDictionary
        from forensic.analysis.pattern.models import ThreatPattern

        threats: list[ThreatPattern] = []

        for segment in segments:
            content = segment.content.lower()

            for threat_type, keywords in KeywordDictionary.THREAT.items():
                matches = self._find_keyword_matches(content, keywords)

                if matches:
                    severity = self._calculate_severity(matches, threat_type)

                    if self._meets_severity_threshold(severity):
                        threat = ThreatPattern(
                            threat_type=threat_type,
                            segment_ids=[segment.id],
                            speaker=segment.speaker,
                            content_sample=matches[0] if matches else segment.content[:100],
                            severity=severity,
                        )
                        threats.append(threat)

        return threats

    def detect_all(
        self,
        transcript: Transcript,
    ) -> list[Evidence]:
        """
        Detect all patterns and convert to Evidence objects.

        Args:
            transcript: Transcript to analyze

        Returns:
            List of Evidence objects for all detected patterns
        """
        evidence_list: list[Evidence] = []

        # Detect all pattern types
        gaslighting = self.detect_gaslighting(transcript.segments)
        threats = self.detect_threats(transcript.segments)
        manipulation = self.detect_emotional_manipulation(transcript.segments)

        # Convert to Evidence
        for pattern in gaslighting:
            importance = pattern.get_importance()
            evidence = Evidence(
                id=str(uuid4()),
                transcript_id=transcript.id,
                segment_ids=pattern.segment_ids,
                category=f"Gaslighting: {pattern.pattern_type}",
                description=f"{pattern.pattern_type}: {pattern.content_sample}",
                importance=importance,
                context_before=pattern.context_before,
                context_after=pattern.context_after,
            )
            evidence_list.append(evidence)

        for threat in threats:
            evidence = Evidence(
                id=str(uuid4()),
                transcript_id=transcript.id,
                segment_ids=threat.segment_ids,
                category=f"Threat: {threat.threat_type}",
                description=f"{threat.threat_type}: {threat.content_sample}",
                importance=threat.severity if threat.severity in ("HIGH", "MEDIUM", "LOW") else "HIGH",
            )
            evidence_list.append(evidence)

        for pattern in manipulation:
            evidence = Evidence(
                id=str(uuid4()),
                transcript_id=transcript.id,
                segment_ids=pattern.segment_ids,
                category=f"Manipulation: {pattern.manipulation_type}",
                description=f"{pattern.manipulation_type}: {pattern.content_sample}",
                importance=pattern.intensity,
            )
            evidence_list.append(evidence)

        return evidence_list

    @staticmethod
    def _find_keyword_matches(content: str, keywords: list[str]) -> list[str]:
        """Find which keywords appear in the content."""
        matches = []
        for keyword in keywords:
            if keyword in content:
                matches.append(keyword)
        return matches

    @staticmethod
    def _calculate_confidence(matches: list[str], all_keywords: list[str]) -> float:
        """Calculate confidence score based on keyword matches."""
        if not all_keywords:
            return 0.5
        match_ratio = len(matches) / len(all_keywords)
        return min(1.0, match_ratio * 1.5)

    @staticmethod
    def _calculate_intensity(matches: list[str]) -> Literal["HIGH", "MEDIUM", "LOW"]:
        """Calculate intensity level for emotional manipulation."""
        if len(matches) >= 3:
            return "HIGH"
        elif len(matches) >= 2:
            return "MEDIUM"
        return "LOW"

    @staticmethod
    def _calculate_severity(
        matches: list[str],
        threat_type: str,
    ) -> Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
        """Calculate severity level for threats."""
        # Explicit threats are always at least HIGH
        if threat_type == "EXPLICIT_THREAT":
            return "CRITICAL" if len(matches) >= 2 else "HIGH"
        elif threat_type in ("FINANCIAL_THREAT", "LEGAL_THREAT"):
            return "HIGH" if len(matches) >= 2 else "MEDIUM"
        else:
            return "MEDIUM" if len(matches) >= 2 else "LOW"

    def _meets_intensity_threshold(
        self,
        intensity: Literal["HIGH", "MEDIUM", "LOW"],
    ) -> bool:
        """Check if intensity meets the threshold."""
        order = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
        return order[intensity] >= order[self._intensity_threshold]

    def _meets_severity_threshold(
        self,
        severity: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"],
    ) -> bool:
        """Check if severity meets the threshold."""
        order = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}
        return order[severity] >= order[self._severity_threshold]

    @staticmethod
    def _normalize_text(text: str) -> str:
        """Normalize text for comparison."""
        # Remove common punctuation first
        text = re.sub(r"[.!?~]+", "", text)
        # Remove extra whitespace and convert to lowercase
        text = re.sub(r"\s+", " ", text).strip().lower()
        return text

    @staticmethod
    def _get_context_before() -> str:
        """Get context before a segment (placeholder)."""
        # In full implementation, this would get preceding segments
        return ""

    @staticmethod
    def _get_context_after() -> str:
        """Get context after a segment (placeholder)."""
        # In full implementation, this would get following segments
        return ""

    def _merge_gaslighting_patterns(
        self,
        patterns: list[GaslightingPattern],
    ) -> list[GaslightingPattern]:
        """Merge gaslighting patterns from the same speaker and type."""
        from forensic.analysis.pattern.models import GaslightingPattern

        merged: dict[tuple, GaslightingPattern] = {}

        for pattern in patterns:
            key = (pattern.speaker, pattern.pattern_type)

            if key in merged:
                existing = merged[key]
                existing.segment_ids.extend(pattern.segment_ids)
                existing.occurrence_count += 1
                existing.content_sample = pattern.content_sample
            else:
                pattern.occurrence_count = 1
                merged[key] = pattern

        return list(merged.values())
