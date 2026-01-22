"""
Result module for search operations

Provides result formatting, highlighting, ranking, pagination,
and export functionality for search results.
"""

from forensic.search.result.exporter import ResultExporter
from forensic.search.result.highlighter import (
    AnsiHighlighter,
    Highlighter,
)
from forensic.search.result.paginator import (
    CursorPaginator,
    Paginator,
)
from forensic.search.result.ranker import (
    CustomRanker,
    Ranker,
)
from forensic.search.result.result_formatter import ResultFormatter

__all__ = [
    "ResultFormatter",
    "Highlighter",
    "AnsiHighlighter",
    "Ranker",
    "CustomRanker",
    "Paginator",
    "CursorPaginator",
    "ResultExporter",
]
