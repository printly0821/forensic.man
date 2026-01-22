"""
Query builder for constructing search queries

Provides a fluent interface for building complex search queries.
"""

import uuid
from dataclasses import dataclass

from forensic.search.models.query import (
    Query,
    QueryLogicalOperator,
    QueryType,
)
from forensic.search.models.search import SearchOptions


@dataclass
class ProximityQuery:
    """
    Proximity search query parameters.

    Represents a proximity query where two terms must appear
    within a certain distance of each other.
    """

    term1: str
    term2: str
    distance: int
    ordered: bool = False


class QueryBuilder:
    """
    Fluent query builder for constructing search queries.

    Provides methods for building AND, OR, NOT queries, as well as
    phrase and proximity queries.
    """

    def __init__(
        self,
        options: SearchOptions | None = None,
    ) -> None:
        """
        Initialize the query builder.

        Args:
            options: Default search options for built queries
        """
        self._options = options or SearchOptions()
        self._queries: list[Query] = []
        self._current_operator: QueryLogicalOperator = QueryLogicalOperator.AND

    def keyword(
        self,
        term: str,
    ) -> "QueryBuilder":
        """
        Add a keyword search term.

        Args:
            term: Keyword to search for

        Returns:
            Self for method chaining
        """
        query = Query(
            query_id=str(uuid.uuid4()),
            query_type=QueryType.KEYWORD,
            raw_query=term,
            options=self._options,
        )
        self._queries.append(query)
        return self

    def phrase(
        self,
        phrase: str,
    ) -> "QueryBuilder":
        """
        Add a phrase search query.

        Args:
            phrase: Exact phrase to search for

        Returns:
            Self for method chaining
        """
        query = Query(
            query_id=str(uuid.uuid4()),
            query_type=QueryType.PHRASE,
            raw_query=f'"{phrase}"',
            parsed_tokens=[],
            options=self._options,
        )
        self._queries.append(query)
        return self

    def regex(
        self,
        pattern: str,
    ) -> "QueryBuilder":
        """
        Add a regex search query.

        Args:
            pattern: Regular expression pattern

        Returns:
            Self for method chaining
        """
        query = Query(
            query_id=str(uuid.uuid4()),
            query_type=QueryType.REGEX,
            raw_query=f"regex:{pattern}",
            parsed_tokens=[],
            options=self._options,
        )
        self._queries.append(query)
        return self

    def wildcard(
        self,
        pattern: str,
    ) -> "QueryBuilder":
        """
        Add a wildcard search query.

        Args:
            pattern: Wildcard pattern (* for any chars, ? for single char)

        Returns:
            Self for method chaining
        """
        query = Query(
            query_id=str(uuid.uuid4()),
            query_type=QueryType.WILDCARD,
            raw_query=pattern,
            parsed_tokens=[],
            options=self._options,
        )
        self._queries.append(query)
        return self

    def proximity(
        self,
        term1: str,
        term2: str,
        distance: int = 10,
    ) -> "QueryBuilder":
        """
        Add a proximity search query.

        Args:
            term1: First term
            term2: Second term
            distance: Maximum distance between terms (in words)

        Returns:
            Self for method chaining
        """
        raw_query = f'"{term1} {term2}"~{distance}'
        query = Query(
            query_id=str(uuid.uuid4()),
            query_type=QueryType.PROXIMITY,
            raw_query=raw_query,
            parsed_tokens=[],
            options=self._options,
            metadata={"term1": term1, "term2": term2, "distance": distance},
        )
        self._queries.append(query)
        return self

    def and_query(
        self,
        *queries: str | Query,
    ) -> "QueryBuilder":
        """
        Add an AND query.

        Args:
            *queries: Queries or query strings to combine with AND

        Returns:
            Self for method chaining
        """
        sub_queries: list[Query] = []

        for q in queries:
            if isinstance(q, str):
                sub_queries.append(
                    Query(
                        query_id=str(uuid.uuid4()),
                        query_type=QueryType.KEYWORD,
                        raw_query=q,
                        options=self._options,
                    )
                )
            elif isinstance(q, Query):
                sub_queries.append(q)

        query = Query(
            query_id=str(uuid.uuid4()),
            query_type=QueryType.BOOLEAN,
            raw_query=" AND ".join(q.raw_query for q in sub_queries),
            operator=QueryLogicalOperator.AND,
            sub_queries=sub_queries,
            options=self._options,
        )
        self._queries.append(query)
        return self

    def or_query(
        self,
        *queries: str | Query,
    ) -> "QueryBuilder":
        """
        Add an OR query.

        Args:
            *queries: Queries or query strings to combine with OR

        Returns:
            Self for method chaining
        """
        sub_queries: list[Query] = []

        for q in queries:
            if isinstance(q, str):
                sub_queries.append(
                    Query(
                        query_id=str(uuid.uuid4()),
                        query_type=QueryType.KEYWORD,
                        raw_query=q,
                        options=self._options,
                    )
                )
            elif isinstance(q, Query):
                sub_queries.append(q)

        query = Query(
            query_id=str(uuid.uuid4()),
            query_type=QueryType.BOOLEAN,
            raw_query=" OR ".join(q.raw_query for q in sub_queries),
            operator=QueryLogicalOperator.OR,
            sub_queries=sub_queries,
            options=self._options,
        )
        self._queries.append(query)
        return self

    def not_query(
        self,
        query: str | Query,
    ) -> "QueryBuilder":
        """
        Add a NOT query.

        Args:
            query: Query or query string to negate

        Returns:
            Self for method chaining
        """
        if isinstance(query, str):
            sub_query = Query(
                query_id=str(uuid.uuid4()),
                query_type=QueryType.KEYWORD,
                raw_query=query,
                options=self._options,
            )
        else:
            sub_query = query

        negated = Query(
            query_id=str(uuid.uuid4()),
            query_type=QueryType.BOOLEAN,
            raw_query=f"NOT {sub_query.raw_query}",
            operator=QueryLogicalOperator.NOT,
            sub_queries=[sub_query],
            options=self._options,
        )
        self._queries.append(negated)
        return self

    def field(
        self,
        field_name: str,
        value: str,
    ) -> "QueryBuilder":
        """
        Add a field-specific query.

        Args:
            field_name: Name of the field (e.g., "speaker", "category")
            value: Value to match

        Returns:
            Self for method chaining
        """
        raw_query = f"{field_name}:{value}"
        query = Query(
            query_id=str(uuid.uuid4()),
            query_type=QueryType.KEYWORD,
            raw_query=raw_query,
            parsed_tokens=[],
            options=self._options,
            metadata={"field": field_name, "value": value},
        )
        self._queries.append(query)
        return self

    def build(self) -> Query:
        """
        Build the final query from all added components.

        Returns:
            Combined Query object
        """
        if len(self._queries) == 0:
            # Empty query
            return Query(
                query_id=str(uuid.uuid4()),
                query_type=QueryType.KEYWORD,
                raw_query="",
                options=self._options,
            )

        if len(self._queries) == 1:
            return self._queries[0]

        # Combine all queries with the current operator
        return Query(
            query_id=str(uuid.uuid4()),
            query_type=QueryType.BOOLEAN,
            raw_query=f" {self._current_operator.value} ".join(q.raw_query for q in self._queries),
            operator=self._current_operator,
            sub_queries=self._queries,
            options=self._options,
        )

    def reset(self) -> "QueryBuilder":
        """
        Reset the builder to its initial state.

        Returns:
            Self for method chaining
        """
        self._queries.clear()
        self._current_operator = QueryLogicalOperator.AND
        return self

    def with_options(
        self,
        options: SearchOptions,
    ) -> "QueryBuilder":
        """
        Update the search options.

        Args:
            options: New search options

        Returns:
            Self for method chaining
        """
        self._options = options
        return self


class ProximityQueryBuilder:
    """
    Builder for proximity search queries.

    Specialized builder for constructing proximity searches
    where two terms must appear within a certain distance.
    """

    def __init__(
        self,
        default_distance: int = 10,
    ) -> None:
        """
        Initialize the proximity query builder.

        Args:
            default_distance: Default distance for proximity searches
        """
        self._default_distance = default_distance
        self._term1: str | None = None
        self._term2: str | None = None
        self._distance: int = default_distance
        self._ordered: bool = False

    def terms(
        self,
        term1: str,
        term2: str,
    ) -> "ProximityQueryBuilder":
        """
        Set the terms for proximity search.

        Args:
            term1: First term
            term2: Second term

        Returns:
            Self for method chaining
        """
        self._term1 = term1
        self._term2 = term2
        return self

    def distance(
        self,
        distance: int,
    ) -> "ProximityQueryBuilder":
        """
        Set the maximum distance between terms.

        Args:
            distance: Maximum word distance

        Returns:
            Self for method chaining
        """
        self._distance = max(1, distance)
        return self

    def ordered(
        self,
        ordered: bool = True,
    ) -> "ProximityQueryBuilder":
        """
        Set whether terms must appear in specified order.

        Args:
            ordered: True for ordered, False for unordered

        Returns:
            Self for method chaining
        """
        self._ordered = ordered
        return self

    def build(self) -> ProximityQuery:
        """
        Build the proximity query.

        Returns:
            ProximityQuery object

        Raises:
            ValueError: If terms are not set
        """
        if not self._term1 or not self._term2:
            raise ValueError("Both term1 and term2 must be set")

        return ProximityQuery(
            term1=self._term1,
            term2=self._term2,
            distance=self._distance,
            ordered=self._ordered,
        )

    def to_query(
        self,
        options: SearchOptions | None = None,
    ) -> Query:
        """
        Convert to a regular Query object.

        Args:
            options: Search options

        Returns:
            Query object
        """
        proximity = self.build()

        raw_query = f'"{proximity.term1} {proximity.term2}"~{proximity.distance}'

        return Query(
            query_id=str(uuid.uuid4()),
            query_type=QueryType.PROXIMITY,
            raw_query=raw_query,
            options=options or SearchOptions(),
            metadata={
                "term1": proximity.term1,
                "term2": proximity.term2,
                "distance": proximity.distance,
                "ordered": proximity.ordered,
            },
        )


__all__ = [
    "QueryBuilder",
    "ProximityQueryBuilder",
    "ProximityQuery",
]
