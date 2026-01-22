"""
Unit tests for query module
"""

import pytest

from forensic.search.query import (
    ProximityQueryBuilder,
    QueryBuilder,
    QueryOptimizer,
    QueryParser,
    QueryValidator,
)
from forensic.search.models import (
    Query,
    QueryLogicalOperator,
    QueryType,
    SearchOptions,
    ValidationResult,
)


class TestQueryParser:
    """Tests for QueryParser class."""

    def setup_method(self):
        """Set up parser."""
        self.parser = QueryParser()

    def test_parse_empty_query(self):
        """Test parsing empty query."""
        query = self.parser.parse("")

        assert query.raw_query == ""
        assert query.query_type == QueryType.KEYWORD

    def test_parse_keyword_query(self):
        """Test parsing simple keyword query."""
        query = self.parser.parse("test")

        assert query.raw_query == "test"
        assert query.query_type == QueryType.KEYWORD

    def test_parse_phrase_query(self):
        """Test parsing phrase query."""
        query = self.parser.parse('"test phrase"')

        assert query.query_type == QueryType.PHRASE
        assert "test phrase" in query.raw_query

    def test_parse_boolean_and_query(self):
        """Test parsing boolean AND query."""
        query = self.parser.parse("test1 AND test2")

        assert query.query_type == QueryType.BOOLEAN
        assert query.operator == QueryLogicalOperator.AND

    def test_parse_boolean_or_query(self):
        """Test parsing boolean OR query."""
        query = self.parser.parse("test1 OR test2")

        assert query.query_type == QueryType.BOOLEAN
        assert query.operator == QueryLogicalOperator.OR

    def test_parse_wildcard_query(self):
        """Test parsing wildcard query."""
        query = self.parser.parse("test*")

        assert query.query_type == QueryType.WILDCARD

    def test_parse_regex_query(self):
        """Test parsing regex query."""
        query = self.parser.parse("regex:[A-Z]+")

        assert query.query_type == QueryType.REGEX

    def test_parse_to_structure(self):
        """Test parsing to structural information."""
        parsed = self.parser.parse_to_structure("test1 AND test2")

        assert parsed.terms is not None
        assert len(parsed.terms) >= 1


class TestQueryBuilder:
    """Tests for QueryBuilder class."""

    def setup_method(self):
        """Set up query builder."""
        self.builder = QueryBuilder()

    def test_keyword(self):
        """Test adding keyword."""
        query = self.builder.keyword("test").build()

        assert query.raw_query == "test"
        assert query.query_type == QueryType.KEYWORD

    def test_phrase(self):
        """Test adding phrase."""
        query = self.builder.phrase("test phrase").build()

        assert query.query_type == QueryType.PHRASE

    def test_and_query(self):
        """Test building AND query."""
        query = self.builder.and_query("test1", "test2").build()

        assert query.query_type == QueryType.BOOLEAN
        assert query.operator == QueryLogicalOperator.AND

    def test_or_query(self):
        """Test building OR query."""
        query = self.builder.or_query("test1", "test2").build()

        assert query.query_type == QueryType.BOOLEAN
        assert query.operator == QueryLogicalOperator.OR

    def test_not_query(self):
        """Test building NOT query."""
        query = self.builder.not_query("test").build()

        assert query.query_type == QueryType.BOOLEAN
        assert query.operator == QueryLogicalOperator.NOT

    def test_proximity(self):
        """Test adding proximity query."""
        query = self.builder.proximity("term1", "term2", 5).build()

        assert query.query_type == QueryType.PROXIMITY

    def test_field_query(self):
        """Test adding field query."""
        query = self.builder.field("speaker", "신동식").build()

        assert "speaker" in query.raw_query
        assert "신동식" in query.raw_query

    def test_reset(self):
        """Test resetting builder."""
        self.builder.keyword("test1")
        self.builder.reset()

        query = self.builder.build()

        assert query.raw_query == ""

    def test_chaining(self):
        """Test method chaining."""
        query = (self.builder
                 .keyword("test1")
                 .and_query("test2", "test3")
                 .build())

        assert query.is_compound is True


class TestProximityQueryBuilder:
    """Tests for ProximityQueryBuilder class."""

    def test_build_proximity_query(self):
        """Test building proximity query."""
        builder = ProximityQueryBuilder()

        proximity = builder.terms("term1", "term2").distance(5).build()

        assert proximity.term1 == "term1"
        assert proximity.term2 == "term2"
        assert proximity.distance == 5

    def test_ordered_proximity(self):
        """Test ordered proximity query."""
        builder = ProximityQueryBuilder()

        proximity = builder.terms("term1", "term2").ordered(True).build()

        assert proximity.ordered is True


class TestQueryValidator:
    """Tests for QueryValidator class."""

    def setup_method(self):
        """Set up validator."""
        self.validator = QueryValidator()

    def test_valid_query(self):
        """Test validating a valid query."""
        result = self.validator.validate("test query")

        assert result.is_valid is True
        assert result.has_errors is False

    def test_empty_query(self):
        """Test validating empty query."""
        result = self.validator.validate("")

        assert result.is_valid is False
        assert result.has_errors is True

    def test_too_long_query(self):
        """Test validating overly long query."""
        long_query = "word " * 300  # Over 1000 chars

        result = self.validator.validate(long_query)

        assert result.is_valid is True  # Still valid, just warning
        assert result.has_warnings is True

    def test_regex_validation(self):
        """Test regex validation."""
        result = self.validator.validate_regex("[a-z]+")

        assert result.is_valid is True

        result = self.validator.validate_regex("[invalid(")

        assert result.is_valid is False
        assert result.has_errors is True

    def test_boolean_query_validation(self):
        """Test boolean query validation."""
        result = self.validator.validate("test AND test AND")

        assert result.has_warnings is True


class TestQueryOptimizer:
    """Tests for QueryOptimizer class."""

    def setup_method(self):
        """Set up optimizer."""
        self.optimizer = QueryOptimizer()

    def test_optimize_keyword_query(self):
        """Test optimizing keyword query."""
        query = Query(
            query_id="1",
            query_type=QueryType.KEYWORD,
            raw_query="  test   query  ",  # Extra spaces
            options=SearchOptions(),
        )

        optimized = self.optimizer.optimize(query)

        assert optimized.was_optimized is True
        assert "  " not in optimized.optimized.raw_query

    def test_optimize_boolean_query(self):
        """Test optimizing boolean query."""
        sub_query1 = Query(
            query_id="2",
            query_type=QueryType.KEYWORD,
            raw_query="test1",
            options=SearchOptions(),
        )
        sub_query2 = Query(
            query_id="3",
            query_type=QueryType.KEYWORD,
            raw_query="test2",
            options=SearchOptions(),
        )

        query = Query(
            query_id="1",
            query_type=QueryType.BOOLEAN,
            raw_query="test1 AND test2",
            operator=QueryLogicalOperator.AND,
            sub_queries=[sub_query1, sub_query2],
            options=SearchOptions(),
        )

        optimized = self.optimizer.optimize(query)

        assert optimized.optimized is not None

    def test_performance_gain(self):
        """Test performance gain calculation."""
        query = Query(
            query_id="1",
            query_type=QueryType.KEYWORD,
            raw_query="  test  ",
            options=SearchOptions(),
        )

        optimized = self.optimizer.optimize(query)

        # Should have some performance gain from whitespace optimization
        assert optimized.performance_gain >= 0
