"""
Pattern detection module for identifying manipulation patterns.

This module provides functionality for:
- Detecting gaslighting patterns
- Identifying repeated statements
- Finding emotional manipulation expressions
- Detecting threat and coercion patterns
- Custom pattern definition
"""

from forensic.analysis.pattern.detector import PatternDetector
from forensic.analysis.pattern.keywords import KeywordDictionary
from forensic.analysis.pattern.models import (
    EmotionalManipulation,
    GaslightingPattern,
    RepeatedStatement,
    StatementOccurrence,
    ThreatPattern,
)

__all__ = [
    "PatternDetector",
    "KeywordDictionary",
    "GaslightingPattern",
    "ThreatPattern",
    "RepeatedStatement",
    "StatementOccurrence",
    "EmotionalManipulation",
]
