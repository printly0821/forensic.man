"""
Query parser for search operations

Parses search query strings into structured Query objects.
"""

import re
import uuid

from forensic.search.models.query import (
    ParsedQuery,
    Query,
    QueryLogicalOperator,
    QueryType,
    Token,
)
from forensic.search.models.search import SearchOptions


class QueryParser:
    """
    Query parser for search queries.

    Parses search query strings into structured Query objects
    with support for boolean operators, phrases, and field queries.
    """

    # Query syntax patterns
    BOOLEAN_OPERATORS = ["AND", "OR", "NOT", "&", "|", "!"]
    FIELD_PATTERN = re.compile(r"(\w+):([\"'].+?[\"']|\S+)")
    PHRASE_PATTERN = re.compile(r"\"(.+?)\"")
    PROXIMITY_PATTERN = re.compile(r"\"(.+?)\"\s*~\s*(\d+)")
    WILDCARD_PATTERN = re.compile(r"(\S*\*\S*|\S*\?\S*)")

    def __init__(self, options: SearchOptions | None = None) -> None:
        """
        Initialize the query parser.

        Args:
            options: Default search options
        """
        self._options = options or SearchOptions()

    def parse(self, query_string: str) -> Query:
        """
        Parse a query string into a Query object.

        Args:
            query_string: Raw query string

        Returns:
            Parsed Query object
        """
        query_string = query_string.strip()

        if not query_string:
            return self._create_empty_query()

        # Detect query type
        query_type = self._detect_query_type(query_string)

        # Parse based on type
        if query_type == QueryType.BOOLEAN:
            return self._parse_boolean_query(query_string)
        elif query_type == QueryType.PROXIMITY:
            return self._parse_proximity_query(query_string)
        elif query_type == QueryType.PHRASE:
            return self._parse_phrase_query(query_string)
        elif query_type == QueryType.REGEX:
            return self._parse_regex_query(query_string)
        elif query_type == QueryType.WILDCARD:
            return self._parse_wildcard_query(query_string)
        else:
            return self._parse_keyword_query(query_string)

    def parse_to_structure(self, query_string: str) -> ParsedQuery:
        """
        Parse query into structural information.

        Args:
            query_string: Raw query string

        Returns:
            ParsedQuery with structural information
        """
        root_query = self.parse(query_string)

        # Extract terms
        terms = self._extract_terms(query_string)
        excluded_terms = self._extract_excluded_terms(query_string)
        required_terms = self._extract_required_terms(query_string)
        phrases = self._extract_phrases(query_string)
        field_queries = self._extract_field_queries(query_string)

        return ParsedQuery(
            root=root_query,
            terms=terms,
            excluded_terms=excluded_terms,
            required_terms=required_terms,
            optional_terms=[],
            phrases=phrases,
            regex_patterns=[],
            field_queries=field_queries,
        )

    def _create_empty_query(self) -> Query:
        """Create an empty query object."""
        return Query(
            query_id=str(uuid.uuid4()),
            query_type=QueryType.KEYWORD,
            raw_query="",
            options=self._options,
        )

    def _detect_query_type(self, query_string: str) -> QueryType:
        """Detect the type of query from the string."""
        # Check for regex patterns
        if query_string.startswith("regex:") or self._has_regex_pattern(query_string):
            return QueryType.REGEX

        # Check for proximity search
        if self.PROXIMITY_PATTERN.search(query_string):
            return QueryType.PROXIMITY

        # Check for boolean operators
        upper_query = query_string.upper()
        if any(op in upper_query for op in [" AND ", " OR ", " NOT "]):
            return QueryType.BOOLEAN

        # Check for phrases
        if self.PHRASE_PATTERN.search(query_string):
            # Check if entire query is a phrase
            match = self.PHRASE_PATTERN.search(query_string)
            if match and match.group(0) == query_string:
                return QueryType.PHRASE

        # Check for wildcards
        if self.WILDCARD_PATTERN.search(query_string):
            return QueryType.WILDCARD

        # Default to keyword
        return QueryType.KEYWORD

    def _has_regex_pattern(self, query_string: str) -> bool:
        """Check if query has regex-specific characters."""
        regex_chars = {"[", "]", "(", ")", "^", "$", ".", "+", "{", "}", "\\"}
        return any(c in query_string for c in regex_chars)

    def _parse_keyword_query(self, query_string: str) -> Query:
        """Parse a simple keyword query."""
        tokens = self._tokenize(query_string)

        return Query(
            query_id=str(uuid.uuid4()),
            query_type=QueryType.KEYWORD,
            raw_query=query_string,
            parsed_tokens=tokens,
            options=self._options,
        )

    def _parse_phrase_query(self, query_string: str) -> Query:
        """Parse a phrase query."""
        match = self.PHRASE_PATTERN.search(query_string)
        phrase = match.group(1) if match else query_string.strip('"')

        return Query(
            query_id=str(uuid.uuid4()),
            query_type=QueryType.PHRASE,
            raw_query=query_string,
            parsed_tokens=[Token(text=phrase, start=0, end=len(phrase))],
            options=self._options,
        )

    def _parse_regex_query(self, query_string: str) -> Query:
        """Parse a regex query."""
        # Strip regex: prefix if present
        pattern = query_string[6:].strip() if query_string.startswith("regex:") else query_string

        return Query(
            query_id=str(uuid.uuid4()),
            query_type=QueryType.REGEX,
            raw_query=query_string,
            parsed_tokens=[Token(text=pattern, start=0, end=len(pattern))],
            options=self._options,
        )

    def _parse_wildcard_query(self, query_string: str) -> Query:
        """Parse a wildcard query."""
        return Query(
            query_id=str(uuid.uuid4()),
            query_type=QueryType.WILDCARD,
            raw_query=query_string,
            parsed_tokens=[Token(text=query_string, start=0, end=len(query_string))],
            options=self._options,
        )

    def _parse_proximity_query(self, query_string: str) -> Query:
        """Parse a proximity search query."""
        match = self.PROXIMITY_PATTERN.search(query_string)
        if match:
            phrase = match.group(1)
            distance = int(match.group(2))
        else:
            phrase = query_string
            distance = self._options.proximity_distance

        return Query(
            query_id=str(uuid.uuid4()),
            query_type=QueryType.PROXIMITY,
            raw_query=query_string,
            parsed_tokens=[Token(text=phrase, start=0, end=len(phrase))],
            options=self._options,
            metadata={"distance": distance},
        )

    def _parse_boolean_query(self, query_string: str) -> Query:
        """Parse a boolean query with AND, OR, NOT operators."""
        # Split by operators while preserving quoted phrases
        parts = self._split_boolean_query(query_string)

        # Build sub-queries
        sub_queries: list[Query] = []
        operator: QueryLogicalOperator | None = None

        for part in parts:
            part = part.strip()
            if not part:
                continue

            upper_part = part.upper()

            if upper_part in ("AND", "&"):
                operator = QueryLogicalOperator.AND
            elif upper_part in ("OR", "|"):
                operator = QueryLogicalOperator.OR
            elif upper_part in ("NOT", "!"):
                operator = QueryLogicalOperator.NOT
            elif part.startswith("-"):
                # Negation prefix
                sub_query = self.parse(part[1:])
                sub_query.operator = QueryLogicalOperator.NOT
                sub_queries.append(sub_query)
            else:
                sub_query = self.parse(part)
                sub_queries.append(sub_query)

        return Query(
            query_id=str(uuid.uuid4()),
            query_type=QueryType.BOOLEAN,
            raw_query=query_string,
            parsed_tokens=self._tokenize(query_string),
            operator=operator,
            sub_queries=sub_queries,
            options=self._options,
        )

    def _split_boolean_query(self, query_string: str) -> list[str]:
        """Split boolean query into parts, preserving quoted phrases."""
        parts: list[str] = []
        current = ""
        in_quotes = False

        for char in query_string:
            if char == '"':
                in_quotes = not in_quotes
                current += char
            elif char in " \t" and not in_quotes:
                if current:
                    parts.append(current)
                    current = ""
            else:
                current += char

        if current:
            parts.append(current)

        return parts

    def _tokenize(self, text: str) -> list[Token]:
        """Simple tokenization for query parsing."""
        tokens: list[Token] = []
        position = 0
        length = len(text)
        current = ""
        start = 0

        while position < length:
            char = text[position]

            if char.isspace():
                if current:
                    tokens.append(Token(text=current, start=start, end=position))
                    current = ""
                    start = position + 1
                position += 1
            elif char in "(),:<>=":
                if current:
                    tokens.append(Token(text=current, start=start, end=position))
                    current = ""
                    start = position + 1
                tokens.append(Token(text=char, start=position, end=position + 1))
                position += 1
            elif char == '"':
                # Find end of quote
                end = text.find('"', position + 1)
                if end != -1:
                    tokens.append(Token(text=text[position : end + 1], start=position, end=end + 1))
                    position = end + 1
                    start = position
                else:
                    current += char
                    position += 1
            else:
                if not current:
                    start = position
                current += char
                position += 1

        if current:
            tokens.append(Token(text=current, start=start, end=position))

        return tokens

    def _extract_terms(self, query_string: str) -> list[str]:
        """Extract all search terms from query."""
        # Remove phrases
        without_phrases = self.PHRASE_PATTERN.sub("", query_string)
        # Remove field queries
        without_fields = self.FIELD_PATTERN.sub("", without_phrases)
        # Remove operators
        without_ops = re.sub(r"\b(AND|OR|NOT)\b", "", without_fields, flags=re.IGNORECASE)
        # Split and clean
        terms = [t.strip().strip("\"'") for t in without_ops.split() if t.strip()]
        return [t for t in terms if t and not set(t).intersection({"&", "|", "!"})]

    def _extract_excluded_terms(self, query_string: str) -> list[str]:
        """Extract terms prefixed with NOT or -."""
        terms: list[str] = []
        # Match NOT term or -term
        pattern = re.compile(r"(?:NOT|!)\s+(\S+)|-(\S+)", re.IGNORECASE)
        for match in pattern.finditer(query_string):
            term = match.group(1) or match.group(2)
            if term:
                # Remove quotes if present
                terms.append(term.strip("\"'"))
        return terms

    def _extract_required_terms(self, query_string: str) -> list[str]:
        """Extract terms that must be present (AND)."""
        terms: list[str] = []
        # Match AND term patterns
        pattern = re.compile(r"AND\s+(\S+)", re.IGNORECASE)
        for match in pattern.finditer(query_string):
            term = match.group(1)
            if term:
                terms.append(term.strip("\"'"))
        return terms

    def _extract_phrases(self, query_string: str) -> list[str]:
        """Extract quoted phrases."""
        return self.PHRASE_PATTERN.findall(query_string)

    def _extract_field_queries(self, query_string: str) -> dict[str, list[str]]:
        """Extract field-specific queries (e.g., speaker:name)."""
        field_queries: dict[str, list[str]] = {}

        for match in self.FIELD_PATTERN.finditer(query_string):
            field = match.group(1).lower()
            value = match.group(2).strip("\"'")

            if field not in field_queries:
                field_queries[field] = []

            field_queries[field].append(value)

        return field_queries


__all__ = [
    "QueryParser",
]
