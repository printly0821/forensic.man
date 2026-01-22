"""
Search result models
"""

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Annotated, Any, Literal, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class SortBy(str, Enum):
    """Sort options for search results"""

    RELEVANCE = "relevance"
    DATE = "date"
    IMPORTANCE = "importance"
    SPEAKER = "speaker"
    DURATION = "duration"


class SortOrder(str, Enum):
    """Sort order for search results"""

    ASC = "asc"
    DESC = "desc"


class MatchPosition(BaseModel):
    """
    Match position model

    Represents the location of a match within a text.
    """

    start: Annotated[int, Field(ge=0, description="Start character index")]
    end: Annotated[int, Field(ge=0, description="End character index")]
    line: int | None = Field(default=None, description="Line number (if applicable)")
    column: int | None = Field(default=None, description="Column number")

    @property
    def length(self) -> int:
        """Get the length of the match."""
        return self.end - self.start


class Match(BaseModel):
    """
    Match model

    Represents a single match within a search result.
    """

    text: str = Field(description="Matched text")
    position: MatchPosition = Field(description="Position of the match")
    score: Annotated[float, Field(ge=0, le=1)] = 1.0
    term_matched: str = Field(description="The search term that matched")


class SearchHit(BaseModel):
    """
    Search hit model

    Represents a single search result with context and metadata.
    """

    id: str = Field(description="Unique hit identifier")
    source_type: Literal["transcript", "segment", "evidence"] = Field(
        description="Type of source document"
    )
    source_id: str = Field(description="ID of the source document")
    score: Annotated[float, Field(ge=0, le=1)] = 0.0
    matched_text: str = Field(default="", description="Text that matched the query")
    highlighted_text: str = Field(default="", description="Matched text with highlights")
    context_before: str = Field(default="", description="Context before the match")
    context_after: str = Field(default="", description="Context after the match")
    speaker: str | None = Field(default=None, description="Speaker if applicable")
    timestamp: datetime | None = Field(default=None, description="Timestamp if applicable")
    file_path: Path | None = Field(default=None, description="Source file path")
    position: MatchPosition = Field(
        default_factory=lambda: MatchPosition(start=0, end=0), description="Position in source text"
    )
    matches: list[Match] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def full_context(self) -> str:
        """Get the full context with match."""
        return f"{self.context_before}{self.matched_text}{self.context_after}"


class ContextPreview(BaseModel):
    """
    Context preview model

    Provides context around a matched segment.
    """

    before_text: str = Field(default="")
    matched_text: str = Field(description="The matched text")
    after_text: str = Field(default="")
    before_segments_count: int = Field(default=0)
    after_segments_count: int = Field(default=0)
    highlighted: str = Field(default="")

    @property
    def full_text(self) -> str:
        """Get the full text with context."""
        return f"{self.before_text}{self.matched_text}{self.after_text}"


class PaginatedResult[T](BaseModel):
    """
    Paginated result model

    Represents a paginated view of search results.
    """

    items: list[T] = Field(default_factory=list)
    page: Annotated[int, Field(ge=1)] = 1
    page_size: Annotated[int, Field(ge=1, le=1000)] = 20
    total_items: Annotated[int, Field(ge=0)] = 0
    total_pages: Annotated[int, Field(ge=0)] = 0

    @property
    def has_previous(self) -> bool:
        """Check if there is a previous page."""
        return self.page > 1

    @property
    def has_next(self) -> bool:
        """Check if there is a next page."""
        return self.page < self.total_pages

    @classmethod
    def create(
        cls,
        items: list[T],
        page: int,
        page_size: int,
        total_items: int,
    ) -> "PaginatedResult[T]":
        """Create a paginated result with calculated total pages."""
        total_pages = (total_items + page_size - 1) // page_size if page_size > 0 else 0
        return cls(
            items=items,
            page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages,
        )


class IndexStats(BaseModel):
    """
    Index statistics model

    Provides information about the search index.
    """

    total_documents: Annotated[int, Field(ge=0)] = 0
    total_segments: Annotated[int, Field(ge=0)] = 0
    total_evidence: Annotated[int, Field(ge=0)] = 0
    total_tokens: Annotated[int, Field(ge=0)] = 0
    unique_terms: Annotated[int, Field(ge=0)] = 0
    index_size_bytes: Annotated[int, Field(ge=0)] = 0
    last_updated: datetime = Field(default_factory=datetime.now)
    build_time_seconds: Annotated[float, Field(ge=0)] = 0.0
    last_build: datetime | None = Field(default=None)

    @property
    def avg_tokens_per_segment(self) -> float:
        """Calculate average tokens per segment."""
        if self.total_segments == 0:
            return 0.0
        return self.total_tokens / self.total_segments

    @property
    def index_size_mb(self) -> float:
        """Get index size in megabytes."""
        return self.index_size_bytes / (1024 * 1024)


class SearchResult(BaseModel):
    """
    Search result model

    Contains all results from a search operation including
    metadata, statistics, and faceted information.
    """

    query: str = Field(description="The search query that was executed")
    total_hits: Annotated[int, Field(ge=0)] = 0
    hits: list[SearchHit] = Field(default_factory=list)
    search_time_ms: Annotated[float, Field(ge=0)] = 0.0
    filters_applied: list[str] = Field(default_factory=list)
    page: Annotated[int, Field(ge=1)] = 1
    page_size: Annotated[int, Field(ge=1)] = 20
    total_pages: Annotated[int, Field(ge=0)] = 0
    suggestions: list[str] = Field(default_factory=list)
    facets: dict[str, dict[str, int]] = Field(default_factory=dict)
    has_more: bool = Field(default=False)
    index_stats: Optional["IndexStats"] = Field(default=None)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def has_results(self) -> bool:
        """Check if search returned any results."""
        return self.total_hits > 0

    @property
    def is_paginated(self) -> bool:
        """Check if results are paginated."""
        return self.page_size < self.total_hits


__all__ = [
    "SortBy",
    "SortOrder",
    "MatchPosition",
    "Match",
    "SearchHit",
    "ContextPreview",
    "PaginatedResult",
    "SearchResult",
    "IndexStats",
]
