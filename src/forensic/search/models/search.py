"""
Search options and configuration models
"""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field, field_validator


class SearchOptions(BaseModel):
    """
    Search options model

    Configures search behavior including case sensitivity,
    morpheme analysis, regex support, and result limits.
    """

    case_sensitive: bool = Field(
        default=False, description="Whether to distinguish between uppercase and lowercase"
    )
    use_morpheme: bool = Field(
        default=True, description="Whether to use morpheme analysis for Korean text"
    )
    use_regex: bool = Field(
        default=False, description="Whether to interpret the query as a regular expression"
    )
    max_results: Annotated[int, Field(ge=1, le=10000, default=1000)] = 1000
    timeout_seconds: Annotated[float, Field(ge=0.1, le=300, default=30.0)] = 30.0
    include_context: bool = Field(
        default=True, description="Whether to include context before and after matches"
    )
    context_chars: Annotated[int, Field(ge=0, le=500, default=100)] = 100
    highlight: bool = Field(default=True, description="Whether to highlight matched text")
    search_targets: list[Literal["transcript", "segment", "evidence"]] = Field(
        default_factory=lambda: ["segment"]
    )
    fuzzy_max_distance: Annotated[int, Field(ge=0, le=5, default=2)] = 2
    proximity_distance: Annotated[int, Field(ge=1, le=50, default=10)] = 10

    @field_validator("search_targets")
    @classmethod
    def validate_search_targets(cls, v: list[str]) -> list[str]:
        """Validate search targets are valid."""
        valid_targets = {"transcript", "segment", "evidence"}
        for target in v:
            if target not in valid_targets:
                raise ValueError(f"Invalid search target: {target}")
        return v


class SuggestionType(str):
    """Search suggestion types"""

    SPELLING = "spelling"
    MORPHEME = "morpheme"
    RELATED = "related"
    EXPANDED = "expanded"


class SearchContext(BaseModel):
    """
    Search execution context

    Tracks search state during execution for timeout and progress monitoring.
    """

    query_id: str
    started_at: datetime = Field(default_factory=datetime.now)
    timeout_seconds: float = 30.0
    results_found: int = 0
    documents_processed: int = 0
    cancelled: bool = False

    @property
    def is_timeout(self) -> bool:
        """Check if search has timed out."""
        elapsed = (datetime.now() - self.started_at).total_seconds()
        return elapsed >= self.timeout_seconds

    @property
    def elapsed_seconds(self) -> float:
        """Get elapsed time in seconds."""
        return (datetime.now() - self.started_at).total_seconds()


__all__ = [
    "SearchOptions",
    "SuggestionType",
    "SearchContext",
]
