"""
Speaker filter for search results

Provides speaker-based filtering for segments and search results.
"""

from typing import TypeVar

from forensic.models import Segment
from forensic.search.models import SearchHit

T = TypeVar("T", Segment, SearchHit, dict)


class SpeakerFilter:
    """
    Speaker-based filter for search results.

    Filters items based on speaker IDs or names.
    """

    def __init__(self) -> None:
        """Initialize the speaker filter."""
        self._included_speakers: set[str] = set()
        self._excluded_speakers: set[str] = set()

    def include_speakers(self, speakers: list[str] | set[str]) -> None:
        """
        Set the speakers to include.

        Args:
            speakers: List or set of speaker IDs/names to include
        """
        self._included_speakers = set(speakers)

    def exclude_speakers(self, speakers: list[str] | set[str]) -> None:
        """
        Set the speakers to exclude.

        Args:
            speakers: List or set of speaker IDs/names to exclude
        """
        self._excluded_speakers = set(speakers)

    def add_speaker(self, speaker: str) -> None:
        """
        Add a speaker to the inclusion list.

        Args:
            speaker: Speaker ID/name to include
        """
        self._included_speakers.add(speaker)

    def remove_speaker(self, speaker: str) -> None:
        """
        Remove a speaker from the inclusion list.

        Args:
            speaker: Speaker ID/name to remove
        """
        self._included_speakers.discard(speaker)

    def exclude_speaker(self, speaker: str) -> None:
        """
        Add a speaker to the exclusion list.

        Args:
            speaker: Speaker ID/name to exclude
        """
        self._excluded_speakers.add(speaker)

    def filter(self, items: list[T]) -> list[T]:
        """
        Filter items by speaker.

        Args:
            items: List of items to filter

        Returns:
            Filtered items matching speaker criteria
        """
        result: list[T] = []

        for item in items:
            speaker = self._extract_speaker(item)

            # Skip if speaker is excluded
            if speaker in self._excluded_speakers:
                continue

            # Skip if included speakers are set and speaker is not included
            if self._included_speakers and speaker not in self._included_speakers:
                continue

            result.append(item)

        return result

    def matches(self, item: T) -> bool:
        """
        Check if an item matches the speaker filter.

        Args:
            item: Item to check

        Returns:
            True if item matches the filter
        """
        speaker = self._extract_speaker(item)

        if speaker in self._excluded_speakers:
            return False

        return not (self._included_speakers and speaker not in self._included_speakers)

    def clear(self) -> None:
        """Clear all speaker filters."""
        self._included_speakers.clear()
        self._excluded_speakers.clear()

    def get_filtered_speakers(self) -> dict[str, set[str]]:
        """
        Get the current speaker filter configuration.

        Returns:
            Dictionary with 'included' and 'excluded' speaker sets
        """
        return {
            "included": self._included_speakers.copy(),
            "excluded": self._excluded_speakers.copy(),
        }

    def _extract_speaker(self, item: T) -> str | None:
        """Extract speaker from an item."""
        if isinstance(item, (Segment, SearchHit)):
            return item.speaker
        elif isinstance(item, dict):
            return item.get("speaker")
        return None


class SpeakerAliasFilter(SpeakerFilter):
    """
    Speaker filter with alias support.

    Allows filtering by speaker name with automatic alias resolution.
    """

    def __init__(self) -> None:
        """Initialize the speaker alias filter."""
        super().__init__()
        self._aliases: dict[str, set[str]] = {}

    def add_alias(self, canonical_name: str, alias: str) -> None:
        """
        Add an alias for a speaker.

        Args:
            canonical_name: The canonical speaker name
            alias: An alias for the speaker
        """
        if canonical_name not in self._aliases:
            self._aliases[canonical_name] = set()

        self._aliases[canonical_name].add(alias)

    def add_aliases(self, canonical_name: str, aliases: list[str]) -> None:
        """
        Add multiple aliases for a speaker.

        Args:
            canonical_name: The canonical speaker name
            aliases: List of aliases for the speaker
        """
        if canonical_name not in self._aliases:
            self._aliases[canonical_name] = set()

        self._aliases[canonical_name].update(aliases)

    def resolve_speaker(self, speaker: str | None) -> str | None:
        """
        Resolve a speaker name to its canonical form.

        Args:
            speaker: Speaker name to resolve

        Returns:
            Canonical speaker name or None if not found
        """
        if speaker is None:
            return None

        # Check if it's already a canonical name
        if speaker in self._aliases:
            return speaker

        # Search through aliases
        for canonical, aliases in self._aliases.items():
            if speaker in aliases:
                return canonical

        # If no alias found, return the original
        return speaker

    def filter(self, items: list[T]) -> list[T]:
        """
        Filter items by speaker with alias resolution.

        Args:
            items: List of items to filter

        Returns:
            Filtered items
        """
        # Expand included speakers to include their aliases
        expanded_included: set[str] = set(self._included_speakers)

        for speaker in self._included_speakers:
            if speaker in self._aliases:
                expanded_included.update(self._aliases[speaker])

        # Expand excluded speakers
        expanded_excluded: set[str] = set(self._excluded_speakers)

        for speaker in self._excluded_speakers:
            if speaker in self._aliases:
                expanded_excluded.update(self._aliases[speaker])

        # Create a temporary filter with expanded speakers
        temp_filter = SpeakerFilter()
        temp_filter._included_speakers = expanded_included
        temp_filter._excluded_speakers = expanded_excluded

        return temp_filter.filter(items)


__all__ = [
    "SpeakerFilter",
    "SpeakerAliasFilter",
]
