"""
Result formatter for search results

Provides formatting and presentation of search results.
"""

from typing import Any

from forensic.search.models import (
    SearchHit,
    SearchResult,
    SortBy,
    SortOrder,
)
from forensic.search.result.exporter import ResultExporter
from forensic.search.result.highlighter import Highlighter
from forensic.search.result.paginator import Paginator
from forensic.search.result.ranker import Ranker


class ResultFormatter:
    """
    Main formatter for search results.

    Provides comprehensive formatting, highlighting, pagination,
    and export functionality for search results.
    """

    def __init__(
        self,
        highlight_tag: str = "mark",
    ) -> None:
        """
        Initialize the result formatter.

        Args:
            highlight_tag: HTML tag for highlighting matches
        """
        self._highlight_tag = highlight_tag
        self._highlighter = Highlighter(tag=highlight_tag)
        self._ranker = Ranker()
        self._paginator = Paginator()
        self._exporter = ResultExporter()

    def format_summary(
        self,
        result: SearchResult,
        max_hits: int = 5,
    ) -> str:
        """
        Format a summary of search results.

        Args:
            result: Search result to summarize
            max_hits: Maximum number of hits to include in summary

        Returns:
            Formatted summary string
        """
        lines = [
            f"Search Query: {result.query}",
            f"Total Hits: {result.total_hits}",
            f"Search Time: {result.search_time_ms:.2f}ms",
        ]

        if result.filters_applied:
            lines.append(f"Filters: {', '.join(result.filters_applied)}")

        lines.append("")

        # Add top results
        top_hits = result.hits[:max_hits]
        for i, hit in enumerate(top_hits, 1):
            lines.append(f"{i}. [{hit.source_type}] {hit.source_id}")
            lines.append(f"   Score: {hit.score:.2f}")
            lines.append(f"   Match: {hit.matched_text}")

            if hit.speaker:
                lines.append(f"   Speaker: {hit.speaker}")

            if hit.context_before or hit.context_after:
                context = f"...{hit.context_before}[{hit.matched_text}]{hit.context_after}..."
                lines.append(f"   Context: {context}")

            lines.append("")

        if result.total_hits > max_hits:
            lines.append(f"... and {result.total_hits - max_hits} more results")

        return "\n".join(lines)

    def format_hit(
        self,
        hit: SearchHit,
        include_context: bool = True,
        highlight: bool = True,
    ) -> str:
        """
        Format a single search hit.

        Args:
            hit: Search hit to format
            include_context: Whether to include context
            highlight: Whether to highlight matched text

        Returns:
            Formatted hit string
        """
        lines = [
            f"Source: {hit.source_type} ({hit.source_id})",
            f"Score: {hit.score:.2f}",
        ]

        if hit.speaker:
            lines.append(f"Speaker: {hit.speaker}")

        if hit.timestamp:
            lines.append(f"Timestamp: {hit.timestamp}")

        matched = hit.matched_text
        if highlight and hit.highlighted_text:
            matched = hit.highlighted_text

        lines.append(f"\nMatched: {matched}")

        if include_context:
            if hit.context_before:
                lines.append(f"Before: ...{hit.context_before}")
            if hit.context_after:
                lines.append(f"After: {hit.context_after}...")

        return "\n".join(lines)

    def format_hits(
        self,
        hits: list[SearchHit],
        include_context: bool = True,
        highlight: bool = True,
    ) -> str:
        """
        Format multiple search hits.

        Args:
            hits: List of search hits to format
            include_context: Whether to include context
            highlight: Whether to highlight matched text

        Returns:
            Formatted hits string
        """
        lines = []

        for i, hit in enumerate(hits, 1):
            lines.append(f"--- Result {i} ---")
            lines.append(self.format_hit(hit, include_context, highlight))
            lines.append("")

        return "\n".join(lines)

    def format_compact(
        self,
        result: SearchResult,
    ) -> str:
        """
        Format search results in compact format.

        Args:
            result: Search result to format

        Returns:
            Compact formatted string
        """
        lines = [
            f"Query: {result.query}",
            f"Results: {result.total_hits} hits in {result.search_time_ms:.2f}ms",
            "",
        ]

        for hit in result.hits:
            line = f"[{hit.score:.2f}] {hit.matched_text}"
            if hit.speaker:
                line += f" ({hit.speaker})"
            lines.append(line)

        return "\n".join(lines)

    def format_detailed(
        self,
        result: SearchResult,
    ) -> str:
        """
        Format search results in detailed format.

        Args:
            result: Search result to format

        Returns:
            Detailed formatted string
        """
        lines = [
            "=" * 60,
            "SEARCH RESULTS",
            "=" * 60,
            f"Query: {result.query}",
            f"Total Hits: {result.total_hits}",
            f"Search Time: {result.search_time_ms:.2f}ms",
            f"Page: {result.page}/{result.total_pages}",
        ]

        if result.filters_applied:
            lines.append(f"Applied Filters: {', '.join(result.filters_applied)}")

        if result.facets:
            lines.append("\nFacets:")
            for facet_name, facet_values in result.facets.items():
                lines.append(f"  {facet_name}:")
                for value, count in facet_values.items():
                    lines.append(f"    {value}: {count}")

        lines.append("\n" + "=" * 60)

        for i, hit in enumerate(result.hits, 1):
            lines.append(f"\n--- RESULT {i} ---")
            lines.append(self.format_hit(hit, include_context=True, highlight=True))

        return "\n".join(lines)

    def get_highlighter(self) -> Highlighter:
        """Get the highlighter instance."""
        return self._highlighter

    def get_ranker(self) -> Ranker:
        """Get the ranker instance."""
        return self._ranker

    def get_paginator(self) -> Paginator:
        """Get the paginator instance."""
        return self._paginator

    def get_exporter(self) -> ResultExporter:
        """Get the exporter instance."""
        return self._exporter

    def sort_results(
        self,
        hits: list[SearchHit],
        sort_by: SortBy = SortBy.RELEVANCE,
        order: SortOrder = SortOrder.DESC,
    ) -> list[SearchHit]:
        """
        Sort search results.

        Args:
            hits: List of search hits to sort
            sort_by: Sort criteria
            order: Sort order

        Returns:
            Sorted list of search hits
        """
        return self._ranker.rank(hits, sort_by, order)

    def paginate(
        self,
        hits: list[SearchHit],
        page: int,
        page_size: int = 20,
    ) -> Any:
        """
        Paginate search results.

        Args:
            hits: List of search hits to paginate
            page: Page number (1-indexed)
            page_size: Items per page

        Returns:
            PaginatedResult
        """
        return self._paginator.paginate_hits(hits, page, page_size)

    def highlight_hit(
        self,
        hit: SearchHit,
    ) -> SearchHit:
        """
        Add highlighting to a search hit.

        Args:
            hit: Search hit to highlight

        Returns:
            SearchHit with highlighted text
        """
        return self._highlighter.highlight_hit(hit)

    def export_results(
        self,
        hits: list[SearchHit],
        output_path: str,
        format: str = "json",
    ) -> Any:
        """
        Export search results to a file.

        Args:
            hits: List of search hits to export
            output_path: Path to output file
            format: Export format

        Returns:
            Path to the exported file
        """
        return self._exporter.export(hits, output_path, format)


__all__ = [
    "ResultFormatter",
]
