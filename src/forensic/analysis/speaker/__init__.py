"""
Speaker analysis module for speaker identification and statistics.

This module provides functionality for:
- Identifying speakers from transcript segments
- Normalizing speaker aliases
- Computing speaker statistics
- Analyzing turn-taking patterns
"""

from forensic.analysis.speaker.analyzer import SpeakerAnalyzer
from forensic.analysis.speaker.models import SpeakerStatistics, TurnTakingEvent

__all__ = ["SpeakerAnalyzer", "SpeakerStatistics", "TurnTakingEvent"]
