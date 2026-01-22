"""
Unit tests for result module
"""

import tempfile
from pathlib import Path

import pytest

from forensic.search.models import Match, MatchPosition, SearchHit, SortBy, SortOrder
from forensic.search.result import (
    AnsiHighlighter,
    Highlighter,
    Paginator,
    Ranker,
    ResultExporter,
    ResultFormatter,
)


class TestHighlighter:
    """Tests for Highlighter class."""

    def setup_method(self):
        """Set up highlighter."""
        self.highlighter = Highlighter(tag="mark")

    def test_highlight_text(self):
        """Test highlighting text with matches."""
        matches = [
            Match(
                text="test",
                position=MatchPosition(start=10, end=14),
                score=1.0,
                term_matched="test",
            ),
        ]

        result = self.highlighter.highlight("This is a test text.", matches)

        assert "<mark>test</mark>" in result

    def test_highlight_keywords(self):
        """Test highlighting keywords."""
        result = self.highlighter.highlight_keywords(
            "This is a test text with test cases.",
            ["test"],
        )

        assert "<mark>test</mark>" in result

    def test_highlight_regex(self):
        """Test highlighting regex matches."""
        result = self.highlighter.highlight_regex(
            "test numbers: 123, 456",
            r"\d+",
        )

        assert "<mark>123</mark>" in result
        assert "<mark>456</mark>" in result

    def test_remove_highlighting(self):
        """Test removing highlighting markup."""
        highlighted = "<mark>test</mark>"
        plain = self.highlighter.remove_highlighting(highlighted)

        assert plain == "test"

    def test_create_context_preview(self):
        """Test creating context preview."""
        text = "Before context matched text after context"
        preview = self.highlighter.create_context_preview(
            text,
            match_start=15,
            match_end=27,
            before_chars=10,
            after_chars=10,
        )

        assert preview.matched_text == "matched text"
        assert preview.before_text is not None
        assert preview.after_text is not None

    def test_custom_tag(self):
        """Test custom highlight tag."""
        highlighter = Highlighter(tag="span")

        matches = [
            Match(
                text="test",
                position=MatchPosition(start=10, end=14),
                score=1.0,
                term_matched="test",
            ),
        ]

        result = highlighter.highlight("This is a test.", matches)

        assert "<span>test</span>" in result


class TestAnsiHighlighter:
    """Tests for AnsiHighlighter class."""

    def test_ansi_highlight(self):
        """Test ANSI highlighting."""
        highlighter = AnsiHighlighter(color="yellow")

        matches = [
            Match(
                text="test",
                position=MatchPosition(start=0, end=4),
                score=1.0,
                term_matched="test",
            ),
        ]

        result = highlighter.highlight("This is a test.", matches)

        # Should contain ANSI codes
        assert "\033[" in result

    def test_bold_highlighter(self):
        """Test bold ANSI highlighter."""
        highlighter = AnsiHighlighter(bold=True)

        assert highlighter._bold is True


class TestPaginator:
    """Tests for Paginator class."""

    def setup_method(self):
        """Set up paginator."""
        self.paginator = Paginator(default_page_size=10)

    def test_paginate(self):
        """Test basic pagination."""
        items = list(range(25))
        result = self.paginator.paginate(items, page=1, page_size=10)

        assert result.page == 1
        assert result.page_size == 10
        assert result.total_items == 25
        assert result.total_pages == 3
        assert len(result.items) == 10
        assert result.has_next is True
        assert result.has_previous is False

    def test_last_page(self):
        """Test last page."""
        items = list(range(25))
        result = self.paginator.paginate(items, page=3, page_size=10)

        assert result.page == 3
        assert result.has_next is False
        assert result.has_previous is True

    def test_empty_result(self):
        """Test paginating empty list."""
        result = self.paginator.paginate([], page=1, page_size=10)

        assert result.total_items == 0
        assert result.total_pages == 0
        assert len(result.items) == 0

    def test_get_page_info(self):
        """Test getting page info."""
        info = self.paginator.get_page_info(100, page_size=10)

        assert info["total_items"] == 100
        assert info["page_size"] == 10
        assert info["total_pages"] == 10

    def test_get_offset(self):
        """Test getting offset for page."""
        offset = self.paginator.get_offset(3, page_size=10)

        assert offset == 20  # (3-1) * 10

    def test_max_page_size(self):
        """Test max page size enforcement."""
        result = self.paginator.paginate(
            list(range(100)),
            page=1,
            page_size=2000,  # Over max
        )

        # Should clamp to max page size
        assert result.page_size <= self.paginator._max_page_size


class TestRanker:
    """Tests for Ranker class."""

    def setup_method(self):
        """Set up ranker and test hits."""
        self.ranker = Ranker()

        self.hits = [
            SearchHit(
                id="1",
                source_type="segment",
                source_id="seg1",
                score=0.5,
                matched_text="low score",
            ),
            SearchHit(
                id="2",
                source_type="segment",
                source_id="seg2",
                score=0.9,
                matched_text="high score",
            ),
            SearchHit(
                id="3",
                source_type="segment",
                source_id="seg3",
                score=0.7,
                matched_text="medium score",
            ),
        ]

    def test_rank_by_relevance_desc(self):
        """Test ranking by relevance descending."""
        result = self.ranker.rank(
            self.hits,
            SortBy.RELEVANCE,
            SortOrder.DESC,
        )

        assert result[0].score >= result[1].score
        assert result[1].score >= result[2].score

    def test_rank_by_relevance_asc(self):
        """Test ranking by relevance ascending."""
        result = self.ranker.rank(
            self.hits,
            SortBy.RELEVANCE,
            SortOrder.ASC,
        )

        assert result[0].score <= result[1].score
        assert result[1].score <= result[2].score

    def test_rank_by_importance(self):
        """Test ranking by importance."""

        hits_with_importance = [
            SearchHit(
                id="1",
                source_type="segment",
                source_id="seg1",
                score=0.5,
                matched_text="low",
                metadata={"importance": "LOW"},
            ),
            SearchHit(
                id="2",
                source_type="segment",
                source_id="seg2",
                score=0.9,
                matched_text="high",
                metadata={"importance": "HIGH"},
            ),
        ]

        result = self.ranker.rank_by_importance(hits_with_importance)

        assert result[0].metadata.get("importance") == "HIGH"


class TestCustomRanker:
    """Tests for CustomRanker class."""

    def test_combined_scoring(self):
        """Test combined scoring with weights."""
        ranker = Ranker()

        # Test custom scoring function
        def custom_score(hit):
            return hit.score * 2

        result = ranker.rank_custom(
            [
                SearchHit(
                    id="1",
                    source_type="segment",
                    source_id="seg1",
                    score=0.5,
                    matched_text="test",
                ),
                SearchHit(
                    id="2",
                    source_type="segment",
                    source_id="seg2",
                    score=0.9,
                    matched_text="test",
                ),
            ],
            custom_score,
        )

        assert result[0].id == "2"  # Higher score first


class TestResultExporter:
    """Tests for ResultExporter class."""

    def setup_method(self):
        """Set up exporter and test hits."""
        self.exporter = ResultExporter()
        self.temp_dir = tempfile.mkdtemp()

        self.hits = [
            SearchHit(
                id="1",
                source_type="segment",
                source_id="seg1",
                score=0.9,
                matched_text="test match",
                speaker="신동식",
            ),
            SearchHit(
                id="2",
                source_type="segment",
                source_id="seg2",
                score=0.7,
                matched_text="another match",
                speaker="신기연",
            ),
        ]

    def test_export_json(self):
        """Test exporting to JSON."""
        output_path = Path(self.temp_dir) / "results.json"

        result = self.exporter.export_json(self.hits, output_path)

        assert result.exists()
        assert result == output_path

    def test_export_csv(self):
        """Test exporting to CSV."""
        output_path = Path(self.temp_dir) / "results.csv"

        result = self.exporter.export_csv(self.hits, output_path)

        assert result.exists()

    def test_export_markdown(self):
        """Test exporting to Markdown."""
        output_path = Path(self.temp_dir) / "results.md"

        result = self.exporter.export_markdown(
            self.hits,
            output_path,
            title="Test Results",
        )

        assert result.exists()

    def test_export_html(self):
        """Test exporting to HTML."""
        output_path = Path(self.temp_dir) / "results.html"

        result = self.exporter.export_html(self.hits, output_path)

        assert result.exists()

    def test_export_unsupported_format(self):
        """Test exporting to unsupported format."""
        output_path = Path(self.temp_dir) / "results.xyz"

        with pytest.raises(ValueError):
            self.exporter.export(self.hits, output_path, format="xyz")


class TestResultFormatter:
    """Tests for ResultFormatter class."""

    def setup_method(self):
        """Set up formatter."""
        self.formatter = ResultFormatter()

    def test_format_summary(self):
        """Test formatting result summary."""
        from forensic.search.models import SearchResult

        result = SearchResult(
            query="test",
            total_hits=2,
            hits=[
                SearchHit(
                    id="1",
                    source_type="segment",
                    source_id="seg1",
                    score=0.9,
                    matched_text="test",
                ),
                SearchHit(
                    id="2",
                    source_type="segment",
                    source_id="seg2",
                    score=0.7,
                    matched_text="test",
                ),
            ],
        )

        summary = self.formatter.format_summary(result, max_hits=2)

        assert "test" in summary
        assert "2" in summary  # total hits

    def test_format_hit(self):
        """Test formatting single hit."""
        hit = SearchHit(
            id="1",
            source_type="segment",
            source_id="seg1",
            score=0.9,
            matched_text="test match",
            speaker="신동식",
        )

        formatted = self.formatter.format_hit(hit)

        assert "seg1" in formatted
        assert "0.9" in formatted
        assert "신동식" in formatted

    def test_format_compact(self):
        """Test compact formatting."""
        from forensic.search.models import SearchResult

        result = SearchResult(
            query="test",
            total_hits=2,
            hits=[
                SearchHit(
                    id="1",
                    source_type="segment",
                    source_id="seg1",
                    score=0.9,
                    matched_text="test",
                ),
            ],
        )

        compact = self.formatter.format_compact(result)

        assert "test" in compact

    def test_sort_results(self):
        """Test sorting results."""
        hits = [
            SearchHit(
                id="1",
                source_type="segment",
                source_id="seg1",
                score=0.5,
                matched_text="low",
            ),
            SearchHit(
                id="2",
                source_type="segment",
                source_id="seg2",
                score=0.9,
                matched_text="high",
            ),
        ]

        sorted_hits = self.formatter.sort_results(
            hits,
            SortBy.RELEVANCE,
            SortOrder.DESC,
        )

        assert sorted_hits[0].score >= sorted_hits[1].score

    def test_paginate(self):
        """Test pagination through formatter."""
        hits = [
            SearchHit(
                id=str(i),
                source_type="segment",
                source_id=f"seg{i}",
                score=0.5,
                matched_text=f"match {i}",
            )
            for i in range(25)
        ]

        paginated = self.formatter.paginate(hits, page=2, page_size=10)

        assert paginated.page == 2
        assert len(paginated.items) == 10

    def tearDown(self):
        """Clean up temp directory."""
        import shutil

        if hasattr(self, "temp_dir"):
            shutil.rmtree(self.temp_dir, ignore_errors=True)
