"""
Query optimizer for improving search performance

Analyzes and optimizes search queries for better performance.
"""

import re

from forensic.search.models.query import (
    OptimizedQuery,
    Query,
    QueryType,
)


class QueryOptimizer:
    """
    Query optimizer for improving search performance.

    Analyzes queries and applies optimizations to improve
    search speed and result quality.
    """

    def __init__(self) -> None:
        """Initialize the query optimizer."""
        self._optimizations_applied: list[str] = []

    def optimize(
        self,
        query: Query,
    ) -> OptimizedQuery:
        """
        Optimize a query for better performance.

        Args:
            query: Query to optimize

        Returns:
            OptimizedQuery with the optimized query and metadata
        """
        self._optimizations_applied.clear()
        optimized = query

        # Apply optimizations based on query type
        if query.query_type == QueryType.BOOLEAN:
            optimized = self._optimize_boolean(optimized)
        elif query.query_type == QueryType.KEYWORD:
            optimized = self._optimize_keyword(optimized)
        elif query.query_type == QueryType.REGEX:
            optimized = self._optimize_regex(optimized)

        # General optimizations
        optimized = self._optimize_general(optimized)

        # Calculate estimated performance gain
        performance_gain = self._calculate_performance_gain(query, optimized)

        return OptimizedQuery(
            original=query,
            optimized=optimized,
            optimizations_applied=self._optimizations_applied.copy(),
            performance_gain=performance_gain,
        )

    def _optimize_boolean(
        self,
        query: Query,
    ) -> Query:
        """Optimize boolean queries."""
        if not query.sub_queries:
            return query

        # Flatten nested boolean queries with same operator
        flat_sub_queries = self._flatten_boolean_tree(query)
        if flat_sub_queries != query.sub_queries:
            self._optimizations_applied.append("Flattened nested boolean queries")
            query = Query(
                query_id=query.query_id,
                query_type=QueryType.BOOLEAN,
                raw_query=query.raw_query,
                operator=query.operator,
                sub_queries=flat_sub_queries,
                options=query.options,
            )

        # Reorder sub-queries for efficiency (rarest terms first)
        reordered = self._reorder_sub_queries(query)
        if reordered != query.sub_queries:
            self._optimizations_applied.append("Reordered sub-queries by selectivity")
            query = Query(
                query_id=query.query_id,
                query_type=QueryType.BOOLEAN,
                raw_query=query.raw_query,
                operator=query.operator,
                sub_queries=reordered,
                options=query.options,
            )

        return query

    def _optimize_keyword(
        self,
        query: Query,
    ) -> Query:
        """Optimize keyword queries."""
        raw = query.raw_query

        # Remove extra whitespace
        optimized_raw = re.sub(r"\s+", " ", raw.strip())
        if optimized_raw != raw:
            self._optimizations_applied.append("Normalized whitespace")

        # Lowercase if case-insensitive
        if not query.options.case_sensitive:
            optimized_raw = optimized_raw.lower()
            if optimized_raw != raw.lower():
                self._optimizations_applied.append("Lowercased for case-insensitive search")

        if optimized_raw != query.raw_query:
            return Query(
                query_id=query.query_id,
                query_type=query.query_type,
                raw_query=optimized_raw,
                parsed_tokens=query.parsed_tokens,
                options=query.options,
            )

        return query

    def _optimize_regex(
        self,
        query: Query,
    ) -> Query:
        """Optimize regex queries."""
        raw = query.raw_query

        # Remove regex: prefix if present
        if raw.startswith("regex:"):
            raw = raw[6:]

        # Simple regex optimizations
        optimizations = []

        # Convert .* at start to prefix search if possible
        if raw.startswith(".*") and not re.search(r"[^a-zA-Z0-9]", raw[2:10]):
            new_raw = raw[2:]
            optimizations.append("Removed leading .* for prefix matching")
            raw = new_raw

        # Convert .* at end to suffix search if possible
        if raw.endswith(".*") and len(raw) > 3:
            new_raw = raw[:-2]
            optimizations.append("Removed trailing .* for suffix matching")
            raw = new_raw

        if optimizations:
            self._optimizations_applied.extend(optimizations)
            return Query(
                query_id=query.query_id,
                query_type=QueryType.REGEX,
                raw_query=f"regex:{raw}",
                parsed_tokens=query.parsed_tokens,
                options=query.options,
            )

        return query

    def _optimize_general(
        self,
        query: Query,
    ) -> Query:
        """Apply general optimizations to any query."""
        raw = query.raw_query

        # Remove duplicate terms
        if query.query_type in (QueryType.KEYWORD, QueryType.BOOLEAN):
            terms = raw.split()
            unique_terms: list[str] = []
            seen: set = set()

            for term in terms:
                upper_term = term.upper()
                if upper_term not in seen:
                    seen.add(upper_term)
                    unique_terms.append(term)

            if len(unique_terms) < len(terms):
                self._optimizations_applied.append("Removed duplicate terms")
                raw = " ".join(unique_terms)

                return Query(
                    query_id=query.query_id,
                    query_type=query.query_type,
                    raw_query=raw,
                    operator=query.operator,
                    sub_queries=query.sub_queries,
                    options=query.options,
                )

        return query

    def _flatten_boolean_tree(
        self,
        query: Query,
    ) -> list[Query]:
        """Flatten nested boolean queries with same operator."""
        if not query.sub_queries:
            return query.sub_queries

        flat: list[Query] = []
        operator = query.operator

        for sub_query in query.sub_queries:
            if sub_query.query_type == QueryType.BOOLEAN and sub_query.operator == operator:
                # Recursively flatten
                nested = self._flatten_boolean_tree(sub_query)
                flat.extend(nested)
            else:
                flat.append(sub_query)

        return flat

    def _reorder_sub_queries(
        self,
        query: Query,
    ) -> list[Query]:
        """Reorder sub-queries by estimated selectivity."""
        if not query.sub_queries or not query.operator:
            return query.sub_queries

        # Score each sub-query by selectivity (lower = more selective)
        scored = []

        for sub_query in query.sub_queries:
            score = self._estimate_selectivity(sub_query)
            scored.append((score, sub_query))

        # Sort by selectivity (most selective first)
        scored.sort(key=lambda x: x[0])

        return [sq for _, sq in scored]

    def _estimate_selectivity(
        self,
        query: Query,
    ) -> float:
        """
        Estimate query selectivity (0 = most selective, 1 = least).

        Lower scores indicate queries that will return fewer results.
        """
        score = 0.5  # Base score

        # Phrases are more selective
        if query.query_type == QueryType.PHRASE:
            score -= 0.2

        # Longer queries are more selective
        length_factor = min(len(query.raw_query) / 50, 0.2)
        score -= length_factor

        # Regex queries are variable
        if query.query_type == QueryType.REGEX:
            pattern = query.raw_query
            if pattern.startswith("regex:"):
                pattern = pattern[6:]

            # Wildcard-heavy patterns are less selective
            if pattern.count("*") + pattern.count(".") > len(pattern) / 2:
                score += 0.3

        # Field queries are more selective
        if ":" in query.raw_query:
            score -= 0.1

        return max(0.0, min(1.0, score))

    def _calculate_performance_gain(
        self,
        _original: Query,
        _optimized: Query,
    ) -> float:
        """
        Calculate estimated performance gain from optimization.

        Returns a value between 0 and 1 representing the
        fractional improvement in performance.
        """
        if not self._optimizations_applied:
            return 0.0

        gain = 0.0

        # Each optimization contributes to performance
        for opt in self._optimizations_applied:
            if "Flattened" in opt:
                gain += 0.15
            elif "Reordered" in opt:
                gain += 0.1
            elif "Duplicate" in opt:
                gain += 0.05
            elif "Lowercased" in opt:
                gain += 0.02
            elif "regex" in opt.lower():
                gain += 0.2

        return min(gain, 0.5)  # Max 50% improvement estimate


__all__ = [
    "QueryOptimizer",
]
