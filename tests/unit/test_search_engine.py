"""
Unit tests for search engine module
"""

import pytest
from datetime import datetime

from forensic.models import Segment, Speaker, Transcript
from forensic.search import (
    IndexBuilder,
    IndexEntry,
    InvertedIndex,
    SearchEngine,
)
from forensic.search.models import FilterConfig, SearchOptions


class TestSearchEngine:
    """Tests for SearchEngine class."""

    def test_engine_initialization(self):
        """Test search engine initialization."""
        engine = SearchEngine()

        assert engine._transcripts == []
        assert engine._segments == []
        assert engine._index_built is False

    def test_add_segments(self):
        """Test adding segments to engine."""
        engine = SearchEngine()
        segments = [
            Segment(
                id="seg1",
                speaker="신동식",
                start_time=0.0,
                end_time=1.0,
                content="테스트 내용",
                confidence=0.9,
            ),
            Segment(
                id="seg2",
                speaker="신기연",
                start_time=1.0,
                end_time=2.0,
                content="위협 내용",
                confidence=0.95,
            ),
        ]

        engine.add_segments(segments)

        assert len(engine._segments) == 2

    def test_build_index(self):
        """Test building search index."""
        engine = SearchEngine()
        segments = [
            Segment(
                id="seg1",
                speaker="신동식",
                start_time=0.0,
                end_time=1.0,
                content="테스트 내용",
                confidence=0.9,
            ),
        ]

        engine.add_segments(segments)
        stats = engine.build_index()

        assert engine._index_built is True
        assert stats.total_segments == 1
        assert stats.total_tokens > 0

    def test_search_simple(self):
        """Test simple keyword search."""
        engine = SearchEngine()
        segments = [
            Segment(
                id="seg1",
                speaker="신동식",
                start_time=0.0,
                end_time=1.0,
                content="가스라이팅 내용이 있습니다",
                confidence=0.9,
            ),
            Segment(
                id="seg2",
                speaker="신기연",
                start_time=1.0,
                end_time=2.0,
                content="일반적인 대화 내용",
                confidence=0.95,
            ),
        ]

        engine.add_segments(segments)
        result = engine.search("가스라이팅")

        assert result.total_hits == 1
        assert len(result.hits) == 1
        assert result.hits[0].source_id == "seg1"

    def test_search_no_results(self):
        """Test search with no matching results."""
        engine = SearchEngine()
        segments = [
            Segment(
                id="seg1",
                speaker="신동식",
                start_time=0.0,
                end_time=1.0,
                content="일반 내용",
                confidence=0.9,
            ),
        ]

        engine.add_segments(segments)
        result = engine.search("없는단어")

        assert result.total_hits == 0
        assert len(result.hits) == 0
        assert result.has_results is False

    def test_search_with_filters(self):
        """Test search with speaker filter."""
        engine = SearchEngine()
        segments = [
            Segment(
                id="seg1",
                speaker="신동식",
                start_time=0.0,
                end_time=1.0,
                content="테스트 내용",
                confidence=0.9,
            ),
            Segment(
                id="seg2",
                speaker="신기연",
                start_time=1.0,
                end_time=2.0,
                content="테스트 내용",
                confidence=0.95,
            ),
        ]

        engine.add_segments(segments)
        filters = FilterConfig(speakers=["신동식"])
        result = engine.search("테스트", filters=filters)

        assert result.total_hits == 1
        assert result.hits[0].speaker == "신동식"

    def test_search_regex(self):
        """Test regex search."""
        engine = SearchEngine()
        segments = [
            Segment(
                id="seg1",
                speaker="신동식",
                start_time=0.0,
                end_time=1.0,
                content="abc123def",
                confidence=0.9,
            ),
        ]

        engine.add_segments(segments)
        result = engine.search_regex(r"\d+")

        assert result.total_hits == 1
        assert "123" in result.hits[0].matched_text

    def test_search_invalid_regex(self):
        """Test invalid regex pattern."""
        engine = SearchEngine()
        segments = [
            Segment(
                id="seg1",
                speaker="신동식",
                start_time=0.0,
                end_time=1.0,
                content="test",
                confidence=0.9,
            ),
        ]

        engine.add_segments(segments)
        result = engine.search_regex(r"[invalid(")

        assert result.total_hits == 0
        assert "error" in result.metadata

    def test_get_index_stats(self):
        """Test getting index statistics."""
        engine = SearchEngine()
        segments = [
            Segment(
                id="seg1",
                speaker="신동식",
                start_time=0.0,
                end_time=1.0,
                content="test content",
                confidence=0.9,
            ),
        ]

        engine.add_segments(segments)
        engine.build_index()

        stats = engine.get_index_stats()

        assert stats.total_segments == 1
        assert stats.total_documents == 0


class TestInvertedIndex:
    """Tests for InvertedIndex class."""

    def test_index_initialization(self):
        """Test index initialization."""
        index = InvertedIndex()

        assert index.size == 0
        assert index.total_documents == 0

    def test_add_term(self):
        """Test adding term to index."""
        index = InvertedIndex()

        index.add_term("test", "doc1", "segment", 0)

        assert index.size == 1
        assert index.contains("test") is True

    def test_get_entry(self):
        """Test getting index entry."""
        index = InvertedIndex()

        index.add_term("test", "doc1", "segment", 0)

        entry = index.get_entry("test")

        assert entry is not None
        assert entry.term == "test"
        assert "doc1" in entry.segment_ids

    def test_get_postings(self):
        """Test getting posting list."""
        index = InvertedIndex()

        index.add_term("test", "doc1", "segment", 0)
        index.add_term("test", "doc2", "segment", 5)

        postings = index.get_postings("test")

        assert len(postings) == 2
        assert "doc1" in postings
        assert "doc2" in postings

    def test_contains(self):
        """Test contains method."""
        index = InvertedIndex()

        assert index.contains("test") is False

        index.add_term("test", "doc1", "segment", 0)

        assert index.contains("test") is True
        assert index.contains("other") is False


class TestIndexBuilder:
    """Tests for IndexBuilder class."""

    def test_builder_initialization(self):
        """Test index builder initialization."""
        builder = IndexBuilder()

        assert builder.is_built is False
        assert builder.index.size == 0

    def test_build_from_segments(self):
        """Test building index from segments."""
        builder = IndexBuilder()
        segments = [
            Segment(
                id="seg1",
                speaker="신동식",
                start_time=0.0,
                end_time=1.0,
                content="test content here",
                confidence=0.9,
            ),
        ]

        stats = builder.build(segments=segments)

        assert builder.is_built is True
        assert stats.total_segments == 1
        assert stats.unique_terms > 0

    def test_add_segments_incremental(self):
        """Test incrementally adding segments."""
        builder = IndexBuilder()

        # Initial build
        segments1 = [
            Segment(
                id="seg1",
                speaker="신동식",
                start_time=0.0,
                end_time=1.0,
                content="test",
                confidence=0.9,
            ),
        ]
        builder.build(segments=segments1)

        # Add more
        segments2 = [
            Segment(
                id="seg2",
                speaker="신기연",
                start_time=1.0,
                end_time=2.0,
                content="more content",
                confidence=0.95,
            ),
        ]
        builder.add_segments(segments2)

        stats = builder.get_stats()

        assert stats.total_segments == 2

    def test_get_stats(self):
        """Test getting index statistics."""
        builder = IndexBuilder()
        segments = [
            Segment(
                id="seg1",
                speaker="신동식",
                start_time=0.0,
                end_time=1.0,
                content="test",
                confidence=0.9,
            ),
        ]

        builder.build(segments=segments)
        stats = builder.get_stats()

        assert stats.total_segments == 1
        assert stats.total_tokens > 0


class TestIndexEntry:
    """Tests for IndexEntry class."""

    def test_entry_initialization(self):
        """Test index entry initialization."""
        entry = IndexEntry("test")

        assert entry.term == "test"
        assert entry.frequency == 0
        assert len(entry.document_ids) == 0

    def test_add_occurrence(self):
        """Test adding occurrence to entry."""
        entry = IndexEntry("test")

        entry.add_occurrence("doc1", "segment", 0)

        assert entry.frequency == 1
        assert "doc1" in entry.segment_ids
        assert entry.positions["doc1"] == [0]

    def test_idf_calculation(self):
        """Test IDF calculation."""
        entry = IndexEntry("test")

        # Add to 2 documents
        entry.add_occurrence("doc1", "segment", 0)
        entry.add_occurrence("doc2", "segment", 0)

        import math

        idf = entry.get_idf(4)  # 4 total docs

        expected = math.log(4 / 2)
        assert abs(idf - expected) < 0.001


class TestSearchOptions:
    """Tests for SearchOptions with SearchEngine."""

    def test_custom_options(self):
        """Test search with custom options."""
        engine = SearchEngine(
            options=SearchOptions(
                max_results=10,
                case_sensitive=True,
            ),
        )
        segments = [
            Segment(
                id="seg1",
                speaker="신동식",
                start_time=0.0,
                end_time=1.0,
                content="TEST Test test",
                confidence=0.9,
            ),
        ]

        engine.add_segments(segments)
        result = engine.search("TEST")

        # Case sensitive should find only exact match
        assert result.total_hits >= 1
