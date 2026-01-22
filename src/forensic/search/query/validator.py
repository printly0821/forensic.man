"""
Query validator for search queries

Validates search queries for correctness and provides suggestions.
"""

import re

from forensic.search.models.query import (
    Query,
    QueryType,
    ValidationResult,
)
from forensic.search.models.search import SearchOptions


class QueryValidator:
    """
    Validator for search queries.

    Checks queries for validity and provides error messages
    and suggestions for improvement.
    """

    # Max query length
    MAX_QUERY_LENGTH = 1000

    # Invalid characters
    INVALID_CHARS = set("<>\\")

    # Reserved words that need special handling
    RESERVED_WORDS = {"AND", "OR", "NOT", "TO"}

    def __init__(self) -> None:
        """Initialize the query validator."""
        self._patterns: list[re.Pattern] = [
            re.compile(r"\*{2,}"),  # Multiple consecutive wildcards
            re.compile(r"\?{2,}"),  # Multiple consecutive single wildcards
        ]

    def validate(
        self,
        query: str | Query,
        _options: SearchOptions | None = None,
    ) -> ValidationResult:
        """
        Validate a search query.

        Args:
            query: Query string or Query object to validate
            options: Search options for context

        Returns:
            ValidationResult with errors, warnings, and suggestions
        """
        result = ValidationResult(is_valid=True)

        if isinstance(query, Query):
            query_string = query.raw_query
            query_type = query.query_type
        else:
            query_string = query
            query_type = None

        # Check for empty query
        if not query_string or not query_string.strip():
            result.add_error("Query cannot be empty")
            return result

        # Check length
        if len(query_string) > self.MAX_QUERY_LENGTH:
            result.add_warning(
                f"Query is very long ({len(query_string)} chars). "
                f"Consider using more specific terms."
            )

        # Check for invalid characters
        self._validate_characters(query_string, result)

        # Detect query type from string if not provided
        if query_type is None:
            upper_query = query_string.upper()
            if " AND " in upper_query or " OR " in upper_query or " NOT " in upper_query:
                query_type = QueryType.BOOLEAN
            elif query_string.startswith("regex:"):
                query_type = QueryType.REGEX
            elif "*" in query_string or "?" in query_string:
                query_type = QueryType.WILDCARD
            elif "~" in query_string and '"' in query_string:
                query_type = QueryType.PROXIMITY

        # Validate based on query type
        if query_type == QueryType.REGEX:
            self._validate_regex(query_string, result)
        elif query_type == QueryType.BOOLEAN:
            self._validate_boolean(query_string, result)
        elif query_type == QueryType.PROXIMITY:
            self._validate_proximity(query_string, result)
        elif query_type == QueryType.WILDCARD:
            self._validate_wildcard(query_string, result)

        # Check for common mistakes
        self._validate_common_mistakes(query_string, result)

        # Generate suggestions
        if result.is_valid and not result.has_warnings:
            self._generate_suggestions(query_string, result)

        return result

    def validate_regex(self, pattern: str) -> ValidationResult:
        """
        Validate a regex pattern.

        Args:
            pattern: Regex pattern to validate

        Returns:
            ValidationResult
        """
        result = ValidationResult(is_valid=True)

        try:
            re.compile(pattern)
        except re.error as e:
            result.add_error(f"Invalid regex pattern: {e}")
            result.is_valid = False

        return result

    def _validate_characters(
        self,
        query: str,
        result: ValidationResult,
    ) -> None:
        """Check for invalid characters."""
        found_invalid = [c for c in query if c in self.INVALID_CHARS]
        if found_invalid:
            result.add_error(f"Query contains invalid characters: {', '.join(set(found_invalid))}")
            result.is_valid = False

    def _validate_regex(
        self,
        query: str,
        result: ValidationResult,
    ) -> None:
        """Validate regex query."""
        # Remove regex: prefix if present
        pattern = query[6:] if query.startswith("regex:") else query

        validation = self.validate_regex(pattern)
        if not validation.is_valid:
            result.errors.extend(validation.errors)
            result.is_valid = False

    def _validate_boolean(
        self,
        query: str,
        result: ValidationResult,
    ) -> None:
        """Validate boolean query."""
        # Check for unbalanced operators
        upper_query = query.upper()

        # Check for consecutive operators
        if re.search(r"(AND|OR|NOT)\s+(AND|OR|NOT)", upper_query):
            result.add_warning("Consecutive boolean operators detected")

        # Check for operators at start/end
        stripped = query.strip()
        if stripped.upper().startswith(("AND ", "OR ", "NOT ")):
            result.add_warning("Query starts with a boolean operator")

        if stripped.upper().endswith((" AND", " OR", " NOT")):
            result.add_warning("Query ends with a boolean operator")

    def _validate_proximity(
        self,
        query: str,
        result: ValidationResult,
    ) -> None:
        """Validate proximity query."""
        # Check for valid proximity syntax
        pattern = re.compile(r'"(.+?)"\s*~\s*(\d+)')
        match = pattern.search(query)

        if not match:
            result.add_warning('Proximity query syntax should be: "phrase"~N')
            return

        distance = int(match.group(2))
        if distance < 1:
            result.add_error("Proximity distance must be at least 1")
            result.is_valid = False
        elif distance > 100:
            result.add_warning("Proximity distance is very large (> 100)")

    def _validate_wildcard(
        self,
        query: str,
        result: ValidationResult,
    ) -> None:
        """Validate wildcard query."""
        # Check for problematic patterns
        for pattern in self._patterns:
            if pattern.search(query):
                result.add_warning(
                    "Query contains multiple consecutive wildcards, which may slow down search"
                )

        # Check for leading wildcards
        if query.startswith("*"):
            result.add_warning("Leading wildcard may slow down search")

        # Check for only wildcards
        stripped = query.replace("*", "").replace("?", "").strip()
        if not stripped:
            result.add_error("Query cannot contain only wildcards")
            result.is_valid = False

    def _validate_common_mistakes(
        self,
        query: str,
        result: ValidationResult,
    ) -> None:
        """Check for common query mistakes."""
        # Check for mixed Korean and English without spaces
        has_korean = any(0xAC00 <= ord(c) <= 0xD7A3 for c in query)
        has_english = any(c.isalpha() and ord(c) < 128 for c in query)

        if (
            has_korean
            and has_english
            and not re.search(r"[가-힣]\s+[a-zA-Z]|[a-zA-Z]\s+[가-힣]", query)
        ):
            # Check if properly spaced
            result.add_suggestion("Consider adding spaces between Korean and English text")

        # Check for very common words
        common_words = {"이다", "있다", "하다", "되다", "the", "is", "are", "was"}
        words = query.lower().split()
        if any(w in common_words for w in words):
            result.add_suggestion("Query contains common words that may return many results")

    def _generate_suggestions(
        self,
        query: str,
        result: ValidationResult,
    ) -> None:
        """Generate query improvement suggestions."""
        # Suggest quotes for phrases
        if " " in query and not query.startswith('"'):
            result.add_suggestion(f'For exact phrase search, use: "{query}"')

        # Suggest field-specific search
        result.add_suggestion('Use field-specific search like "speaker:name" for better results')


__all__ = [
    "QueryValidator",
]
