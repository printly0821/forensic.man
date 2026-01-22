"""
Search result ranker

Provides ranking and sorting functionality for search results.
"""

from collections.abc import Callable
from datetime import datetime
from typing import Any

from forensic.search.models import SearchHit, SortBy, SortOrder


class Ranker:
    """
    Ranker for search results.

    Provides various ranking strategies for search results.
    """

    def __init__(self) -> None:
        """Initialize the ranker."""
        self._scoring_functions: dict[str, Callable[[SearchHit], float]] = {
            "relevance": self._score_relevance,
            "date": self._score_date,
            "importance": self._score_importance,
            "speaker": self._score_speaker,
            "duration": self._score_duration,
        }

    def rank(
        self,
        hits: list[SearchHit],
        sort_by: SortBy = SortBy.RELEVANCE,
        order: SortOrder = SortOrder.DESC,
    ) -> list[SearchHit]:
        """
        Rank and sort search results.

        Args:
            hits: List of search hits to rank
            sort_by: Sorting criteria
            order: Sort order (ascending or descending)

        Returns:
            Sorted list of search hits
        """
        if not hits:
            return hits

        # Get scoring function
        score_fn = self._scoring_functions.get(
            sort_by.value,
            self._score_relevance,
        )

        # Sort by score
        reverse = order == SortOrder.DESC
        sorted_hits = sorted(
            hits,
            key=lambda h: score_fn(h),
            reverse=reverse,
        )

        return sorted_hits

    def rank_by_relevance(
        self,
        hits: list[SearchHit],
    ) -> list[SearchHit]:
        """
        Rank hits by relevance score.

        Args:
            hits: List of search hits

        Returns:
            Hits sorted by relevance (descending)
        """
        return sorted(hits, key=lambda h: h.score, reverse=True)

    def rank_by_date(
        self,
        hits: list[SearchHit],
        newest_first: bool = True,
    ) -> list[SearchHit]:
        """
        Rank hits by date.

        Args:
            hits: List of search hits
            newest_first: If True, newest first; otherwise oldest first

        Returns:
            Hits sorted by date
        """

        def date_key(hit: SearchHit) -> Any:
            if hit.timestamp:
                return hit.timestamp
            # Fallback to metadata
            return hit.metadata.get("date", datetime.min)

        return sorted(
            hits,
            key=date_key,
            reverse=newest_first,
        )

    def rank_by_importance(
        self,
        hits: list[SearchHit],
        high_first: bool = True,
    ) -> list[SearchHit]:
        """
        Rank hits by importance level.

        Args:
            hits: List of search hits
            high_first: If True, HIGH importance first

        Returns:
            Hits sorted by importance
        """
        importance_order = {"HIGH": 3, "MEDIUM": 2, "LOW": 1, None: 0}

        return sorted(
            hits,
            key=lambda h: importance_order.get(h.metadata.get("importance"), 0),
            reverse=high_first,
        )

    def rank_by_speaker(
        self,
        hits: list[SearchHit],
    ) -> list[SearchHit]:
        """
        Rank and group hits by speaker.

        Args:
            hits: List of search hits

        Returns:
            Hits sorted by speaker name
        """
        return sorted(
            hits,
            key=lambda h: h.speaker or "",
        )

    def rank_custom(
        self,
        hits: list[SearchHit],
        score_fn: Callable[[SearchHit], float],
        descending: bool = True,
    ) -> list[SearchHit]:
        """
        Rank hits using a custom scoring function.

        Args:
            hits: List of search hits
            score_fn: Function that takes a SearchHit and returns a score
            descending: Whether to sort descending (high scores first)

        Returns:
            Hits sorted by custom score
        """
        return sorted(
            hits,
            key=score_fn,
            reverse=descending,
        )

    def _score_relevance(self, hit: SearchHit) -> float:
        """Get relevance score."""
        return hit.score

    def _score_date(self, hit: SearchHit) -> Any:
        """Get date for sorting."""
        if hit.timestamp:
            return hit.timestamp.timestamp()
        return 0

    def _score_importance(self, hit: SearchHit) -> float:
        """Get importance score."""
        importance_order = {"HIGH": 3.0, "MEDIUM": 2.0, "LOW": 1.0}
        return importance_order.get(
            hit.metadata.get("importance"),
            0.0,
        )

    def _score_speaker(self, hit: SearchHit) -> str:
        """Get speaker name for sorting."""
        return hit.speaker or ""

    def _score_duration(self, hit: SearchHit) -> float:
        """Get duration for sorting."""
        return hit.metadata.get("duration", 0.0)


class CustomRanker(Ranker):
    """
    Customizable ranker with user-defined scoring functions.

    Allows complex ranking strategies combining multiple factors.
    """

    def __init__(self) -> None:
        """Initialize the custom ranker."""
        super().__init__()
        self._weights: dict[str, float] = {
            "relevance": 1.0,
            "recency": 0.1,
            "importance": 0.2,
        }

    def set_weight(
        self,
        factor: str,
        weight: float,
    ) -> None:
        """
        Set weight for a ranking factor.

        Args:
            factor: Factor name (relevance, recency, importance)
            weight: Weight value (higher = more important)
        """
        self._weights[factor] = weight

    def rank_combined(
        self,
        hits: list[SearchHit],
    ) -> list[SearchHit]:
        """
        Rank using combined scoring with weighted factors.

        Args:
            hits: List of search hits

        Returns:
            Hits sorted by combined score
        """

        def combined_score(hit: SearchHit) -> float:
            score = 0.0

            # Relevance
            score += hit.score * self._weights.get("relevance", 1.0)

            # Recency (newer = higher score)
            recency_weight = self._weights.get("recency", 0.0)
            if recency_weight > 0 and hit.timestamp:
                days_old = (datetime.now() - hit.timestamp).days
                recency_score = max(0, 1 - days_old / 365)  # Decay over a year
                score += recency_score * recency_weight

            # Importance
            importance_weight = self._weights.get("importance", 0.0)
            if importance_weight > 0:
                importance_order = {"HIGH": 1.0, "MEDIUM": 0.5, "LOW": 0.0}
                importance_score = importance_order.get(
                    hit.metadata.get("importance"),
                    0.0,
                )
                score += importance_score * importance_weight

            return score

        return sorted(
            hits,
            key=combined_score,
            reverse=True,
        )


__all__ = [
    "Ranker",
    "CustomRanker",
]
