"""
Unit tests for search models
"""

import pytest
from datetime import date, datetime
from pathlib import Path

from forensic.search.models import (
    ActiveFilters,
    FilterConfig,
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
    Token,
    TokenType,
    ValidationResult,
)


class TestSearchOptions:
    """Tests for SearchOptions model."""

    def test_default_options(self):
        """Test default search options."""
        options = SearchOptions()

        assert options.case_sensitive is False
        assert options.use_morpheme is True
        assert options.use_regex is False
        assert options.max_results == 1000
        assert options.timeout_seconds == 30.0
        assert options.include_context is True
        assert options.highlight is True
        assert options.search_targets == ["segment"]

    def test_custom_options(self):
        """Test custom search options."""
        options = SearchOptions(
            case_sensitive=True,
            max_results=500,
            search_targets=["transcript", "segment"],
        )

        assert options.case_sensitive is True
        assert options.max_results == 500
        assert options.search_targets == ["transcript", "segment"]

    def test_invalid_search_target(self):
        """Test validation of invalid search targets."""
        with pytest.raises(ValueError):
            SearchOptions(search_targets=["invalid"])

    def test_max_results_validation(self):
        """Test max results validation."""
        with pytest.raises(ValueError):
            SearchOptions(max_results=20000)

        with pytest.raises(ValueError):
            SearchOptions(max_results=0)


class TestSearchResult:
    """Tests for SearchResult model."""

    def test_empty_result(self):
        """Test empty search result."""
        result = SearchResult(
            query="test",
            total_hits=0,
            hits=[],
        )

        assert result.query == "test"
        assert result.total_hits == 0
        assert len(result.hits) == 0
        assert result.has_results is False

    def test_result_with_hits(self):
        """Test search result with hits."""
        hit = SearchHit(
            id="1",
            source_type="segment",
            source_id="seg1",
            score=0.8,
            matched_text="test",
        )

        result = SearchResult(
            query="test",
            total_hits=1,
            hits=[hit],
        )

        assert result.has_results is True
        assert result.total_hits == 1
        assert len(result.hits) == 1

    def test_paginated_result(self):
        """Test paginated result property."""
        result = SearchResult(
            query="test",
            total_hits=50,
            hits=[],
            page_size=20,
        )

        assert result.is_paginated is True


class TestSearchHit:
    """Tests for SearchHit model."""

    def test_search_hit_creation(self):
        """Test search hit creation."""
        hit = SearchHit(
            id="1",
            source_type="segment",
            source_id="seg1",
            score=0.8,
            matched_text="test text",
        )

        assert hit.id == "1"
        assert hit.source_type == "segment"
        assert hit.source_id == "seg1"
        assert hit.score == 0.8
        assert hit.matched_text == "test text"

    def test_full_context(self):
        """Test full context property."""
        hit = SearchHit(
            id="1",
            source_type="segment",
            source_id="seg1",
            score=0.8,
            matched_text="middle",
            context_before="before ",
            context_after=" after",
        )

        assert hit.full_context == "before middle after"


class TestMatchPosition:
    """Tests for MatchPosition model."""

    def test_match_position(self):
        """Test match position creation."""
        position = MatchPosition(start=10, end=20)

        assert position.start == 10
        assert position.end == 20
        assert position.length == 10

    def test_match_position_with_line_column(self):
        """Test match position with line and column."""
        position = MatchPosition(start=0, end=5, line=1, column=0)

        assert position.line == 1
        assert position.column == 0


class TestPaginatedResult:
    """Tests for PaginatedResult model."""

    def test_paginated_result_creation(self):
        """Test paginated result creation."""
        result = PaginatedResult.create(
            items=[1, 2, 3],
            page=1,
            page_size=10,
            total_items=25,
        )

        assert result.page == 1
        assert result.page_size == 10
        assert result.total_items == 25
        assert result.total_pages == 3
        assert result.has_previous is False
        assert result.has_next is True

    def test_first_page(self):
        """Test first page properties."""
        result = PaginatedResult.create(
            items=[],
            page=1,
            page_size=10,
            total_items=25,
        )

        assert result.has_previous is False

    def test_last_page(self):
        """Test last page properties."""
        result = PaginatedResult.create(
            items=[],
            page=3,
            page_size=10,
            total_items=25,
        )

        assert result.has_next is False
        assert result.has_previous is True


class TestFilterConfig:
    """Tests for FilterConfig model."""

    def test_empty_config(self):
        """Test empty filter config."""
        config = FilterConfig()

        assert config.has_filters is False
        assert config.filter_count == 0

    def test_speaker_filter(self):
        """Test speaker filter."""
        config = FilterConfig(speakers=["신동식", "신기연"])

        assert config.has_filters is True
        assert config.filter_count == 1
        assert config.speakers == ["신동식", "신기연"]

    def test_multiple_filters(self):
        """Test multiple filters."""
        config = FilterConfig(
            speakers=["신동식"],
            importance=["HIGH", "MEDIUM"],
        )

        assert config.has_filters is True
        assert config.filter_count == 2

    def test_clear_filters(self):
        """Test clearing filters."""
        config = FilterConfig(
            speakers=["신동식"],
            importance=["HIGH"],
        )

        config.clear()

        assert config.has_filters is False
        assert config.filter_count == 0

    def test_to_dict(self):
        """Test converting to dictionary."""
        config = FilterConfig(
            speakers=["신동식"],
            importance=["HIGH"],
        )

        result = config.to_dict()

        assert "speakers" in result
        assert result["speakers"] == ["신동식"]
        assert "importance" in result


class TestIndexStats:
    """Tests for IndexStats model."""

    def test_index_stats(self):
        """Test index stats creation."""
        stats = IndexStats(
            total_documents=10,
            total_segments=100,
            total_evidence=50,
        )

        assert stats.total_documents == 10
        assert stats.total_segments == 100
        assert stats.total_evidence == 50

    def test_avg_tokens_per_segment(self):
        """Test average tokens calculation."""
        stats = IndexStats(
            total_segments=100,
            total_tokens=1000,
        )

        assert stats.avg_tokens_per_segment == 10.0

    def test_index_size_mb(self):
        """Test index size in megabytes."""
        stats = IndexStats(
            index_size_bytes=1024 * 1024,  # 1 MB
        )

        assert stats.index_size_mb == 1.0


class TestQuery:
    """Tests for Query model."""

    def test_keyword_query(self):
        """Test keyword query creation."""
        query = Query(
            query_id="1",
            query_type=QueryType.KEYWORD,
            raw_query="test",
        )

        assert query.query_type == QueryType.KEYWORD
        assert query.raw_query == "test"
        assert query.is_compound is False

    def test_compound_query(self):
        """Test compound query with sub-queries."""
        sub_query = Query(
            query_id="2",
            query_type=QueryType.KEYWORD,
            raw_query="test1",
        )

        query = Query(
            query_id="1",
            query_type=QueryType.BOOLEAN,
            raw_query="test1 AND test2",
            sub_queries=[sub_query],
            operator=QueryLogicalOperator.AND,
        )

        assert query.is_compound is True
        assert query.has_operator is True
        assert len(query.sub_queries) == 1


class TestValidationResult:
    """Tests for ValidationResult model."""

    def test_valid_result(self):
        """Test valid validation result."""
        result = ValidationResult(is_valid=True)

        assert result.is_valid is True
        assert result.has_errors is False

    def test_add_error(self):
        """Test adding error."""
        result = ValidationResult(is_valid=True)

        result.add_error("Test error")

        assert result.is_valid is False
        assert result.has_errors is True
        assert "Test error" in result.errors

    def test_add_warning(self):
        """Test adding warning."""
        result = ValidationResult(is_valid=True)

        result.add_warning("Test warning")

        assert result.has_warnings is True
        assert "Test warning" in result.warnings

    def test_add_suggestion(self):
        """Test adding suggestion."""
        result = ValidationResult(is_valid=True)

        result.add_suggestion("Test suggestion")

        assert "Test suggestion" in result.suggestions


class TestToken:
    """Tests for Token model."""

    def test_word_token(self):
        """Test word token creation."""
        token = Token(
            text="test",
            start=0,
            end=4,
            token_type=TokenType.WORD,
        )

        assert token.text == "test"
        assert token.start == 0
        assert token.end == 4
        assert token.length == 4
        assert token.token_type == TokenType.WORD

    def test_whitespace_token(self):
        """Test whitespace token."""
        token = Token(
            text=" ",
            start=4,
            end=5,
            token_type=TokenType.WHITESPACE,
        )

        assert token.token_type == TokenType.WHITESPACE


class TestSingleFilter:
    """Tests for SingleFilter model."""

    def test_equals_filter(self):
        """Test equals filter operation."""
        filter = SingleFilter(
            field="speaker",
            operation=FilterOperation.EQUALS,
            value="신동식",
        )

        item = {"speaker": "신동식"}

        assert filter.applies_to(item) is True

    def test_contains_filter(self):
        """Test contains filter operation."""
        filter = SingleFilter(
            field="content",
            operation=FilterOperation.CONTAINS,
            value="test",
        )

        assert filter.applies_to({"content": "test text"}) is True
        assert filter.applies_to({"content": "other"}) is False

    def test_greater_than_filter(self):
        """Test greater than filter."""
        filter = SingleFilter(
            field="score",
            operation=FilterOperation.GREATER_THAN,
            value=0.5,
        )

        assert filter.applies_to({"score": 0.8}) is True
        assert filter.applies_to({"score": 0.3}) is False


class TestSearchContext:
    """Tests for SearchContext model."""

    def test_search_context(self):
        """Test search context creation."""
        context = SearchContext(
            query_id="test",
            timeout_seconds=30.0,
        )

        assert context.query_id == "test"
        assert context.timeout_seconds == 30.0
        assert context.is_timeout is False

    def test_timeout_check(self):
        """Test timeout detection."""
        context = SearchContext(
            query_id="test",
            timeout_seconds=0.0,  # Immediate timeout
        )

        # After creation, should be timed out
        assert context.is_timeout is True


class TestActiveFilters:
    """Tests for ActiveFilters model."""

    def test_add_filter(self):
        """Test adding active filter."""
        filters = ActiveFilters()

        filters.add("speaker", "신동식", "Speaker: 신동식")

        assert filters.count == 1
        assert filters.is_empty is False

    def test_remove_filter(self):
        """Test removing filter."""
        filters = ActiveFilters()

        filters.add("speaker", "신동식")
        filters.remove("speaker")

        assert filters.is_empty is True

    def test_get_description(self):
        """Test getting filter description."""
        filters = ActiveFilters()

        filters.add("speaker", "신동식", "Speaker: 신동식")

        assert filters.get_description("speaker") == "Speaker: 신동식"


class TestSortEnums:
    """Tests for sort-related enums."""

    def test_sort_by_values(self):
        """Test SortBy enum values."""
        assert SortBy.RELEVANCE.value == "relevance"
        assert SortBy.DATE.value == "date"
        assert SortBy.IMPORTANCE.value == "importance"

    def test_sort_order_values(self):
        """Test SortOrder enum values."""
        assert SortOrder.ASC.value == "asc"
        assert SortOrder.DESC.value == "desc"
