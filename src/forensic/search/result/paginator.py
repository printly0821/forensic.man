"""
Search result paginator

Provides pagination functionality for large result sets.
"""

from typing import Any, TypeVar

from forensic.search.models import PaginatedResult, SearchHit

T = TypeVar("T")


class Paginator:
    """
    Paginator for search results.

    Splits large result sets into pages for easier navigation.
    """

    def __init__(
        self,
        default_page_size: int = 20,
        max_page_size: int = 1000,
    ) -> None:
        """
        Initialize the paginator.

        Args:
            default_page_size: Default number of items per page
            max_page_size: Maximum allowed page size
        """
        self._default_page_size = default_page_size
        self._max_page_size = max_page_size

    def paginate(
        self,
        items: list[T],
        page: int,
        page_size: int | None = None,
    ) -> PaginatedResult:
        """
        Paginate a list of items.

        Args:
            items: List of items to paginate
            page: Page number (1-indexed)
            page_size: Number of items per page (uses default if None)

        Returns:
            PaginatedResult with items for the requested page
        """
        # Validate and clamp page size
        if page_size is None:
            page_size = self._default_page_size

        page_size = max(1, min(page_size, self._max_page_size))

        # Validate and clamp page number
        total_items = len(items)
        total_pages = (total_items + page_size - 1) // page_size if page_size > 0 else 0
        page = max(1, min(page, total_pages)) if total_pages > 0 else 1

        # Calculate start and end indices
        start = (page - 1) * page_size
        end = min(start + page_size, total_items)

        # Extract items for this page
        page_items = items[start:end]

        return PaginatedResult(
            items=page_items,  # type: ignore
            page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages,
        )

    def paginate_hits(
        self,
        hits: list[SearchHit],
        page: int,
        page_size: int | None = None,
    ) -> PaginatedResult:
        """
        Paginate search hits.

        Args:
            hits: List of search hits to paginate
            page: Page number (1-indexed)
            page_size: Number of hits per page

        Returns:
            PaginatedResult with search hits
        """
        return self.paginate(hits, page, page_size)

    def get_page_info(
        self,
        total_items: int,
        page_size: int | None = None,
    ) -> dict[str, Any]:
        """
        Get pagination information without paginating.

        Args:
            total_items: Total number of items
            page_size: Page size

        Returns:
            Dictionary with pagination metadata
        """
        if page_size is None:
            page_size = self._default_page_size

        page_size = max(1, min(page_size, self._max_page_size))

        total_pages = (total_items + page_size - 1) // page_size if page_size > 0 else 0

        return {
            "total_items": total_items,
            "page_size": page_size,
            "total_pages": total_pages,
            "has_multiple_pages": total_pages > 1,
        }

    def get_page_range(
        self,
        current_page: int,
        total_pages: int,
        window: int = 2,
    ) -> list[int]:
        """
        Get range of page numbers to display in pagination controls.

        Args:
            current_page: Current page number
            total_pages: Total number of pages
            window: Number of pages to show on each side of current page

        Returns:
            List of page numbers to display
        """
        if total_pages <= 1:
            return [1]

        # Calculate range
        start = max(1, current_page - window)
        end = min(total_pages, current_page + window)

        # Always show first page if not in range
        if start > 1:
            pages = [1]
            if start > 2:
                pages.append(-1)  # Ellipsis placeholder
        else:
            pages = []

        # Add pages in range
        pages.extend(range(start, end + 1))

        # Always show last page if not in range
        if end < total_pages:
            if end < total_pages - 1:
                pages.append(-1)  # Ellipsis placeholder
            pages.append(total_pages)

        return [p for p in pages if p != -1 or (p == -1 and len(pages) > 0)]

    def get_offset(
        self,
        page: int,
        page_size: int | None = None,
    ) -> int:
        """
        Get the offset for a given page.

        Args:
            page: Page number (1-indexed)
            page_size: Page size

        Returns:
            Offset (0-indexed) for the first item on the page
        """
        if page_size is None:
            page_size = self._default_page_size

        page = max(1, page)
        return (page - 1) * page_size

    def get_page_for_offset(
        self,
        offset: int,
        page_size: int | None = None,
    ) -> int:
        """
        Get the page number for a given offset.

        Args:
            offset: 0-indexed offset
            page_size: Page size

        Returns:
            Page number (1-indexed)
        """
        if page_size is None:
            page_size = self._default_page_size

        page_size = max(1, page_size)
        return (offset // page_size) + 1


class CursorPaginator(Paginator):
    """
    Cursor-based paginator for large datasets.

    Uses cursor-based pagination instead of offset-based
    for better performance with very large datasets.
    """

    def __init__(
        self,
        default_page_size: int = 20,
        max_page_size: int = 1000,
    ) -> None:
        """
        Initialize the cursor paginator.

        Args:
            default_page_size: Default number of items per page
            max_page_size: Maximum allowed page size
        """
        super().__init__(default_page_size, max_page_size)
        self._cursors: dict[str, int] = {}

    def create_cursor(
        self,
        item: Any,
        index: int,
    ) -> str:
        """
        Create a cursor for an item.

        Args:
            item: Item to create cursor for
            index: Index of the item in the full list

        Returns:
            Cursor string
        """
        import hashlib
        import json

        cursor_data = {"index": index, "id": getattr(item, "id", str(index))}
        cursor_json = json.dumps(cursor_data, sort_keys=True)
        cursor_hash = hashlib.sha256(cursor_json.encode()).hexdigest()[:16]

        cursor = f"{cursor_hash}:{index}"

        self._cursors[cursor] = index

        return cursor

    def parse_cursor(
        self,
        cursor: str,
    ) -> int | None:
        """
        Parse a cursor to get the offset.

        Args:
            cursor: Cursor string

        Returns:
            Offset index or None if invalid
        """
        try:
            if ":" in cursor:
                _, index = cursor.split(":", 1)
                return int(index)
        except (ValueError, IndexError):
            pass

        return None


__all__ = [
    "Paginator",
    "CursorPaginator",
]
