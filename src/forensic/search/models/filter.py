"""
Filter models for search operations
"""

from datetime import date
from enum import Enum
from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, Field


class FilterLogicalOperator(str, Enum):
    """Logical operators for combining filters"""

    AND = "AND"
    OR = "OR"
    NOT = "NOT"


class FilterOperation(str, Enum):
    """Filter comparison operations"""

    EQUALS = "eq"
    NOT_EQUALS = "ne"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    GREATER_THAN = "gt"
    GREATER_EQUAL = "gte"
    LESS_THAN = "lt"
    LESS_EQUAL = "lte"
    IN = "in"
    NOT_IN = "not_in"
    BETWEEN = "between"
    REGEX = "regex"


class SingleFilter(BaseModel):
    """
    Single filter condition

    Represents a single filter condition with field, operation, and value.
    """

    field: str = Field(description="Field to filter on")
    operation: FilterOperation = Field(description="Comparison operation")
    value: Any = Field(description="Value to compare against")
    value2: Any | None = Field(default=None)

    def applies_to(self, item: dict[str, Any]) -> bool:
        """Check if this filter applies to the given item."""
        if self.field not in item:
            return False

        item_value = item[self.field]

        match self.operation:
            case FilterOperation.EQUALS:
                return item_value == self.value
            case FilterOperation.NOT_EQUALS:
                return item_value != self.value
            case FilterOperation.CONTAINS:
                return self.value in str(item_value) if item_value else False
            case FilterOperation.NOT_CONTAINS:
                return self.value not in str(item_value) if item_value else True
            case FilterOperation.STARTS_WITH:
                return str(item_value).startswith(self.value) if item_value else False
            case FilterOperation.ENDS_WITH:
                return str(item_value).endswith(self.value) if item_value else False
            case FilterOperation.GREATER_THAN:
                return item_value > self.value
            case FilterOperation.GREATER_EQUAL:
                return item_value >= self.value
            case FilterOperation.LESS_THAN:
                return item_value < self.value
            case FilterOperation.LESS_EQUAL:
                return item_value <= self.value
            case FilterOperation.IN:
                return item_value in self.value
            case FilterOperation.NOT_IN:
                return item_value not in self.value
            case FilterOperation.BETWEEN:
                return self.value <= item_value <= self.value2 if self.value2 is not None else False
            case _:
                return False


class FilterGroup(BaseModel):
    """
    Filter group

    Represents a group of filters combined with a logical operator.
    """

    operator: FilterLogicalOperator = FilterLogicalOperator.AND
    filters: list[Union["SingleFilter", "FilterGroup"]] = Field(default_factory=list)

    def add_filter(self, filter: Union["SingleFilter", "FilterGroup"]) -> None:
        """Add a filter to this group."""
        self.filters.append(filter)

    @property
    def is_empty(self) -> bool:
        """Check if group has no filters."""
        return len(self.filters) == 0


class FilterConfig(BaseModel):
    """
    Filter configuration model

    Represents all active filters for a search operation.
    """

    date_range: tuple[date, date] | None = Field(default=None)
    speakers: list[str] | None = Field(default=None)
    importance: list[Literal["HIGH", "MEDIUM", "LOW"]] | None = Field(default=None)
    pattern_types: list[str] | None = Field(default=None)
    time_range: tuple[float, float] | None = Field(default=None)
    categories: list[str] | None = Field(default=None)
    transcript_ids: list[str] | None = Field(default=None)
    confidence_min: Annotated[float, Field(ge=0, le=1)] = 0.0
    confidence_max: Annotated[float, Field(ge=0, le=1)] = 1.0
    duration_min: Annotated[float, Field(ge=0)] = 0.0
    duration_max: Annotated[float, Field(ge=0)] = float("inf")

    @property
    def has_filters(self) -> bool:
        """Check if any filters are active."""
        return any(
            [
                self.date_range is not None,
                self.speakers is not None,
                self.importance is not None,
                self.pattern_types is not None,
                self.time_range is not None,
                self.categories is not None,
                self.transcript_ids is not None,
                self.confidence_min > 0.0,
                self.confidence_max < 1.0,
                self.duration_min > 0.0,
                self.duration_max < float("inf"),
            ]
        )

    @property
    def filter_count(self) -> int:
        """Count active filters."""
        return sum(
            [
                1 if self.date_range else 0,
                1 if self.speakers else 0,
                1 if self.importance else 0,
                1 if self.pattern_types else 0,
                1 if self.time_range else 0,
                1 if self.categories else 0,
                1 if self.transcript_ids else 0,
                1 if self.confidence_min > 0.0 else 0,
                1 if self.confidence_max < 1.0 else 0,
                1 if self.duration_min > 0.0 else 0,
                1 if self.duration_max < float("inf") else 0,
            ]
        )

    def clear(self) -> None:
        """Clear all filters."""
        self.date_range = None
        self.speakers = None
        self.importance = None
        self.pattern_types = None
        self.time_range = None
        self.categories = None
        self.transcript_ids = None
        self.confidence_min = 0.0
        self.confidence_max = 1.0
        self.duration_min = 0.0
        self.duration_max = float("inf")

    def to_dict(self) -> dict[str, Any]:
        """Convert filter config to dictionary."""
        result: dict[str, Any] = {}
        if self.date_range:
            result["date_range"] = {
                "start": self.date_range[0].isoformat(),
                "end": self.date_range[1].isoformat(),
            }
        if self.speakers:
            result["speakers"] = self.speakers
        if self.importance:
            result["importance"] = self.importance
        if self.pattern_types:
            result["pattern_types"] = self.pattern_types
        if self.time_range:
            result["time_range"] = {
                "start": self.time_range[0],
                "end": self.time_range[1],
            }
        if self.categories:
            result["categories"] = self.categories
        if self.transcript_ids:
            result["transcript_ids"] = self.transcript_ids
        if self.confidence_min > 0:
            result["confidence_min"] = self.confidence_min
        if self.confidence_max < 1.0:
            result["confidence_max"] = self.confidence_max
        if self.duration_min > 0:
            result["duration_min"] = self.duration_min
        if self.duration_max < float("inf"):
            result["duration_max"] = self.duration_max
        return result


class ActiveFilters(BaseModel):
    """
    Active filters state

    Tracks currently active filters with their display names and values.
    """

    filters: dict[str, Any] = Field(default_factory=dict)
    descriptions: dict[str, str] = Field(default_factory=dict)

    def add(self, key: str, value: Any, description: str = "") -> None:
        """Add an active filter."""
        self.filters[key] = value
        if description:
            self.descriptions[key] = description

    def remove(self, key: str) -> None:
        """Remove a filter."""
        self.filters.pop(key, None)
        self.descriptions.pop(key, None)

    def clear(self) -> None:
        """Clear all filters."""
        self.filters.clear()
        self.descriptions.clear()

    @property
    def is_empty(self) -> bool:
        """Check if no filters are active."""
        return len(self.filters) == 0

    @property
    def count(self) -> int:
        """Get number of active filters."""
        return len(self.filters)

    def get_description(self, key: str) -> str:
        """Get description for a filter."""
        return self.descriptions.get(key, key)

    def to_list(self) -> list[tuple[str, Any, str]]:
        """Convert to list of (key, value, description) tuples."""
        return [(key, value, self.descriptions.get(key, "")) for key, value in self.filters.items()]


# Enable forward references
FilterGroup.model_rebuild()


__all__ = [
    "FilterLogicalOperator",
    "FilterOperation",
    "SingleFilter",
    "FilterGroup",
    "FilterConfig",
    "ActiveFilters",
]
