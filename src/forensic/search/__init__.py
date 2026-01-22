"""
Forensic search module

Provides comprehensive search and filtering capabilities for transcript analysis.

This module implements SPEC-SEARCH-001, including:
- Keyword search with exact, partial, wildcard, and fuzzy matching
- Korean text support with morpheme analysis
- Filter engine for date, speaker, importance, and pattern-based filtering
- Query parser for complex boolean queries
- Result formatting, highlighting, ranking, and pagination
- Index builder and storage for fast search

Example usage:
    from forensic.search import SearchEngine, FilterConfig

    # Create search engine
    engine = SearchEngine()
    engine.add_transcripts(transcripts)

    # Build index
    stats = engine.build_index()

    # Search
    result = engine.search("gaslighting")

    # With filters
    filters = FilterConfig(speakers=["신동식"])
    result = engine.search("위협", filters=filters)
"""

# Models
# Engine
from forensic.search.engine import (
    IndexBuilder,
    IndexCache,
    IndexEntry,
    IndexStore,
    InvertedIndex,
    SearchEngine,
)

# Filters
from forensic.search.filter import (
    AbusePatternFilter,
    CompositeFilter,
    DateFilter,
    EmotionalManipulationFilter,
    FilterEngine,
    GaslightingFilter,
    HighImportanceFilter,
    ImportanceFilter,
    MediumHighImportanceFilter,
    PatternFilter,
    RelativeDateFilter,
    SpeakerAliasFilter,
    SpeakerFilter,
    ThreatFilter,
)

# Keyword search
from forensic.search.keyword import (
    FuzzyMatcher,
    FuzzySearcher,
    KeywordSearcher,
    KoreanTokenizer,
    NgramTokenizer,
    Tokenizer,
    WildcardMatcher,
    WildcardSearcher,
)
from forensic.search.models import (
    ActiveFilters,
    FilterConfig,
    FilterGroup,
    FilterLogicalOperator,
    FilterOperation,
    IndexStats,
    Match,
    MatchPosition,
    PaginatedResult,
    Query,
    QueryLogicalOperator,
    QueryType,
    SearchContext,
    SearchHit,
    SearchOptions,
    SearchResult,
    SingleFilter,
    SortBy,
    SortOrder,
    SuggestionType,
    Token,
    TokenType,
    ValidationResult,
)

# Query
from forensic.search.query import (
    ProximityQueryBuilder,
    QueryBuilder,
    QueryOptimizer,
    QueryParser,
    QueryValidator,
)

# Result
from forensic.search.result import (
    AnsiHighlighter,
    CursorPaginator,
    CustomRanker,
    Highlighter,
    Paginator,
    Ranker,
    ResultExporter,
    ResultFormatter,
)

__all__ = [
    # Models
    "SearchOptions",
    "SearchResult",
    "SearchHit",
    "Match",
    "MatchPosition",
    "PaginatedResult",
    "SortBy",
    "SortOrder",
    "IndexStats",
    "Query",
    "QueryType",
    "QueryLogicalOperator",
    "Token",
    "TokenType",
    "ValidationResult",
    "FilterConfig",
    "FilterOperation",
    "FilterLogicalOperator",
    "FilterGroup",
    "SingleFilter",
    "ActiveFilters",
    "SearchContext",
    "SuggestionType",
    # Engine
    "SearchEngine",
    "IndexBuilder",
    "IndexEntry",
    "InvertedIndex",
    "IndexStore",
    "IndexCache",
    # Keyword
    "Tokenizer",
    "KoreanTokenizer",
    "NgramTokenizer",
    "KeywordSearcher",
    "WildcardMatcher",
    "WildcardSearcher",
    "FuzzySearcher",
    "FuzzyMatcher",
    "LevenshteinDistance",
    # Filters
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
    # Query
    "QueryBuilder",
    "ProximityQueryBuilder",
    "QueryParser",
    "QueryValidator",
    "QueryOptimizer",
    # Result
    "ResultFormatter",
    "Highlighter",
    "AnsiHighlighter",
    "Ranker",
    "CustomRanker",
    "Paginator",
    "CursorPaginator",
    "ResultExporter",
]

# Module metadata
__version__ = "1.0.0"
__spec__ = "SPEC-SEARCH-001"
