"""
Forensic analysis module for transcript pattern detection and temporal analysis.

This module provides comprehensive analysis capabilities including:
- Timeline construction and temporal organization
- Speaker identification and statistics
- Pattern detection (gaslighting, threats, emotional manipulation)

Main components:
- TimelineBuilder: Build chronologically ordered timelines
- SpeakerAnalyzer: Identify speakers and compute statistics
- PatternDetector: Detect manipulation patterns
"""

from forensic.analysis.pattern import (
    EmotionalManipulation,
    GaslightingPattern,
    PatternDetector,
    ThreatPattern,
)
from forensic.analysis.speaker import SpeakerAnalyzer, SpeakerStatistics, TurnTakingEvent
from forensic.analysis.timeline import Timeline, TimelineBuilder, TimelineEvent

__all__ = [
    # Timeline
    "Timeline",
    "TimelineBuilder",
    "TimelineEvent",
    # Speaker
    "SpeakerAnalyzer",
    "SpeakerStatistics",
    "TurnTakingEvent",
    # Pattern
    "PatternDetector",
    "GaslightingPattern",
    "ThreatPattern",
    "EmotionalManipulation",
]
