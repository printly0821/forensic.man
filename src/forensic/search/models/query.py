"""
Query models for search operations
"""

from datetime import datetime
from enum import Enum
from typing import Annotated

from pydantic import BaseModel, Field

from forensic.search.models.search import SearchOptions


class TokenType(str, Enum):
    """Token types for text analysis"""

    WORD = "word"
    NUMBER = "number"
    PUNCTUATION = "punctuation"
    WHITESPACE = "whitespace"
    SPECIAL = "special"


class QueryType(str, Enum):
    """Query types"""

    KEYWORD = "keyword"
    PHRASE = "phrase"
    REGEX = "regex"
    BOOLEAN = "boolean"
    PROXIMITY = "proximity"
    WILDCARD = "wildcard"
    FUZZY = "fuzzy"


class QueryLogicalOperator(str, Enum):
    """Logical operators for boolean queries"""

    AND = "AND"
    OR = "OR"
    NOT = "NOT"


class Token(BaseModel):
    """
    Token model

    Represents a single token from text tokenization.
    """

    text: str = Field(description="Token text")
    start: Annotated[int, Field(ge=0)] = 0
    end: Annotated[int, Field(ge=0)] = 0
    token_type: TokenType = TokenType.WORD

    @property
    def length(self) -> int:
        """Get token length."""
        return self.end - self.start


class MorphemeToken(BaseModel):
    """
    Morpheme token model for Korean text analysis

    Represents a morpheme from Korean morphological analysis.
    """

    text: str = Field(description="Original text")
    lemma: str = Field(description="Base form/dictionary form")
    pos: str = Field(description="Part of speech tag (NNG, VV, JKS, etc.)")
    start: Annotated[int, Field(ge=0)] = 0
    end: Annotated[int, Field(ge=0)] = 0
    is_content_word: bool = Field(
        default=False, description="Whether this is a content word (noun, verb, adjective, etc.)"
    )

    @property
    def is_noun(self) -> bool:
        """Check if morpheme is a noun."""
        return self.pos.startswith("N")

    @property
    def is_verb(self) -> bool:
        """Check if morpheme is a verb."""
        return self.pos.startswith("V")

    @property
    def is_josa(self) -> bool:
        """Check if morpheme is a particle (josa)."""
        return self.pos.startswith("J")


class Query(BaseModel):
    """
    Query model

    Represents a parsed and validated search query.
    """

    query_id: str = Field(description="Unique query identifier")
    query_type: QueryType = QueryType.KEYWORD
    raw_query: str = Field(description="Original query string")
    parsed_tokens: list[Token] = Field(default_factory=list)
    operator: QueryLogicalOperator | None = Field(default=None)
    sub_queries: list["Query"] = Field(default_factory=list)
    options: SearchOptions = Field(default_factory=SearchOptions)
    created_at: datetime = Field(default_factory=datetime.now)
    is_valid: bool = Field(default=True)
    error_message: str | None = Field(default=None)

    @property
    def is_compound(self) -> bool:
        """Check if this is a compound query (has sub-queries)."""
        return len(self.sub_queries) > 0

    @property
    def has_operator(self) -> bool:
        """Check if query has a logical operator."""
        return self.operator is not None


class ValidationResult(BaseModel):
    """
    Query validation result

    Contains validation status and any errors or warnings.
    """

    is_valid: bool = Field(description="Whether the query is valid")
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        """Check if there are validation errors."""
        return len(self.errors) > 0

    @property
    def has_warnings(self) -> bool:
        """Check if there are warnings."""
        return len(self.warnings) > 0

    def add_error(self, error: str) -> None:
        """Add a validation error."""
        self.errors.append(error)
        self.is_valid = False

    def add_warning(self, warning: str) -> None:
        """Add a validation warning."""
        self.warnings.append(warning)

    def add_suggestion(self, suggestion: str) -> None:
        """Add a suggestion."""
        self.suggestions.append(suggestion)


class ParsedQuery(BaseModel):
    """
    Parsed query model with structural information

    Contains the parsed structure of a search query including
    terms, operators, and groups.
    """

    root: Query = Field(description="Root query node")
    terms: list[str] = Field(default_factory=list)
    excluded_terms: list[str] = Field(default_factory=list)
    required_terms: list[str] = Field(default_factory=list)
    optional_terms: list[str] = Field(default_factory=list)
    phrases: list[str] = Field(default_factory=list)
    regex_patterns: list[str] = Field(default_factory=list)
    field_queries: dict[str, list[str]] = Field(default_factory=dict)

    @property
    def has_terms(self) -> bool:
        """Check if query has any search terms."""
        return len(self.terms) > 0

    @property
    def is_empty(self) -> bool:
        """Check if query is empty."""
        return not self.has_terms


class OptimizedQuery(BaseModel):
    """
    Optimized query model

    Represents a query after optimization passes.
    """

    original: Query = Field(description="Original query before optimization")
    optimized: Query = Field(description="Optimized query")
    optimizations_applied: list[str] = Field(default_factory=list)
    performance_gain: Annotated[float, Field(ge=0)] = 0.0

    @property
    def was_optimized(self) -> bool:
        """Check if any optimizations were applied."""
        return len(self.optimizations_applied) > 0


# Enable forward references
Query.model_rebuild()


__all__ = [
    "TokenType",
    "QueryType",
    "QueryLogicalOperator",
    "Token",
    "MorphemeToken",
    "Query",
    "ValidationResult",
    "ParsedQuery",
    "OptimizedQuery",
]
