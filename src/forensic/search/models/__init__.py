"""
Search data models for forensic.man

Provides Pydantic v2 models for search operations, including
search options, results, queries, filters, and related data structures.
"""

from forensic.search.models.filter import (
    ActiveFilters,
    FilterConfig,
    FilterGroup,
    FilterLogicalOperator,
    FilterOperation,
    SingleFilter,
)
from forensic.search.models.query import (
    MorphemeToken,
    OptimizedQuery,
    ParsedQuery,
    Query,
    QueryLogicalOperator,
    QueryType,
    Token,
    TokenType,
    ValidationResult,
)
from forensic.search.models.result import (
    ContextPreview,
    IndexStats,
    Match,
    MatchPosition,
    PaginatedResult,
    SearchHit,
    SearchResult,
    SortBy,
    SortOrder,
)
from forensic.search.models.search import (
    SearchContext,
    SearchOptions,
    SuggestionType,
)

__all__ = [
    # Search options
    "SearchOptions",
    "SuggestionType",
    "SearchContext",
    # Search results
    "SearchResult",
    "SearchHit",
    "Match",
    "MatchPosition",
    "ContextPreview",
    "PaginatedResult",
    "SortBy",
    "SortOrder",
    "IndexStats",
    # Query models
    "Query",
    "QueryType",
    "QueryLogicalOperator",
    "Token",
    "TokenType",
    "MorphemeToken",
    "ValidationResult",
    "ParsedQuery",
    "OptimizedQuery",
    # Filter models
    "FilterConfig",
    "FilterOperation",
    "FilterGroup",
    "SingleFilter",
    "ActiveFilters",
    "FilterLogicalOperator",
]
