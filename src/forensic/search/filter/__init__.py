"""
Filter module for search results

Provides filtering functionality for search results based on
various criteria including date, speaker, importance, and pattern types.
"""

from forensic.search.filter.date_filter import (
    DateFilter,
    RelativeDateFilter,
)
from forensic.search.filter.filter_engine import (
    CompositeFilter,
    FilterEngine,
)
from forensic.search.filter.importance_filter import (
    HighImportanceFilter,
    ImportanceFilter,
    MediumHighImportanceFilter,
)
from forensic.search.filter.pattern_filter import (
    AbusePatternFilter,
    EmotionalManipulationFilter,
    GaslightingFilter,
    PatternFilter,
    ThreatFilter,
)
from forensic.search.filter.speaker_filter import (
    SpeakerAliasFilter,
    SpeakerFilter,
)

__all__ = [
    "FilterEngine",
    "CompositeFilter",
    "DateFilter",
    "RelativeDateFilter",
    "SpeakerFilter",
    "SpeakerAliasFilter",
    "ImportanceFilter",
    "HighImportanceFilter",
    "MediumHighImportanceFilter",
    "PatternFilter",
    "GaslightingFilter",
    "ThreatFilter",
    "EmotionalManipulationFilter",
    "AbusePatternFilter",
]
