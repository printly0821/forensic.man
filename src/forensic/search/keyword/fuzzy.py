"""
Fuzzy search using edit distance

Provides approximate string matching based on Levenshtein distance.
"""

import uuid

from forensic.models import Segment
from forensic.search.models import MatchPosition, SearchHit, SearchOptions


class LevenshteinDistance:
    """
    Levenshtein edit distance calculator.

    Computes the minimum number of single-character edits
    (insertions, deletions, or substitutions) required to change
    one string into another.
    """

    def __init__(self) -> None:
        """Initialize the distance calculator."""
        self._cache: dict[tuple[str, str], int] = {}

    def distance(self, s1: str, s2: str) -> int:
        """
        Calculate Levenshtein distance between two strings.

        Args:
            s1: First string
            s2: Second string

        Returns:
            Edit distance (number of edits required)
        """
        # Check cache
        key = (s1, s2)
        if key in self._cache:
            return self._cache[key]

        # Use shorter string for optimization
        if len(s1) < len(s2):
            s1, s2 = s2, s1

        # Empty string cases
        if len(s2) == 0:
            return len(s1)

        # Use dynamic programming
        previous_row = list(range(len(s2) + 1))

        for i, c1 in enumerate(s1):
            current_row = [i + 1]

            for j, c2 in enumerate(s2):
                # Calculate costs
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)

                current_row.append(min(insertions, deletions, substitutions))

            previous_row = current_row

        result = previous_row[-1]
        self._cache[key] = result
        return result

    def normalized_distance(self, s1: str, s2: str) -> float:
        """
        Calculate normalized distance (0 to 1).

        Args:
            s1: First string
            s2: Second string

        Returns:
            Normalized distance where 0 is identical and 1 is completely different
        """
        max_len = max(len(s1), len(s2))
        if max_len == 0:
            return 0.0

        return self.distance(s1, s2) / max_len

    def similarity(self, s1: str, s2: str) -> float:
        """
        Calculate similarity score (0 to 1).

        Args:
            s1: First string
            s2: Second string

        Returns:
            Similarity score where 1 is identical and 0 is completely different
        """
        return 1.0 - self.normalized_distance(s1, s2)

    def clear_cache(self) -> None:
        """Clear the distance cache."""
        self._cache.clear()


class FuzzyMatcher:
    """
    Fuzzy string matcher using edit distance.

    Finds approximate matches within a specified maximum distance.
    """

    def __init__(self, max_distance: int = 2) -> None:
        """
        Initialize the fuzzy matcher.

        Args:
            max_distance: Maximum edit distance for matches
        """
        self._max_distance = max_distance
        self._distance = LevenshteinDistance()

    def find_matches(
        self,
        text: str,
        pattern: str,
    ) -> list[tuple[int, int, int]]:
        """
        Find all fuzzy matches of pattern in text.

        Args:
            text: Text to search in
            pattern: Pattern to search for

        Returns:
            List of (start, end, distance) tuples
        """
        if not pattern or not text:
            return []

        matches: list[tuple[int, int, int]] = []
        pattern_len = len(pattern)
        text_len = len(text)

        # Slide a window through the text
        window_size = pattern_len + self._max_distance

        for i in range(text_len):
            # Calculate window end
            end = min(i + window_size, text_len)
            window = text[i:end]

            # Find best match in this window
            best_dist = self._max_distance + 1
            best_pos = -1
            best_end = -1

            # Try different window positions
            for j in range(len(window)):
                remaining = len(window) - j
                if remaining < pattern_len - self._max_distance:
                    break

                for k in range(j + 1, len(window) + 1):
                    candidate = window[j:k]
                    if abs(len(candidate) - pattern_len) > self._max_distance:
                        continue

                    dist = self._distance.distance(candidate, pattern)
                    if dist < best_dist:
                        best_dist = dist
                        best_pos = i + j
                        best_end = i + k

            if best_dist <= self._max_distance:
                matches.append((best_pos, best_end, best_dist))

        return matches

    def find_best_match(
        self,
        text: str,
        pattern: str,
    ) -> tuple[int, int, int] | None:
        """
        Find the best single match in text.

        Args:
            text: Text to search in
            pattern: Pattern to search for

        Returns:
            (start, end, distance) tuple or None if no match found
        """
        matches = self.find_matches(text, pattern)

        if not matches:
            return None

        # Return match with minimum distance
        return min(matches, key=lambda m: m[2])


class FuzzySearcher:
    """
    Fuzzy searcher for approximate text matching.

    Finds matches that are similar but not exact using edit distance.
    """

    def __init__(
        self,
        max_distance: int = 2,
        options: SearchOptions | None = None,
    ) -> None:
        """
        Initialize the fuzzy searcher.

        Args:
            max_distance: Maximum edit distance for matches
            options: Search options
        """
        self._max_distance = max_distance
        self._options = options or SearchOptions()
        self._matcher = FuzzyMatcher(max_distance)

    def search(
        self,
        keyword: str,
        segments: list[Segment],
        max_distance: int | None = None,
    ) -> list[SearchHit]:
        """
        Search for fuzzy matches of keyword in segments.

        Args:
            keyword: Keyword to search for
            segments: List of segments to search
            max_distance: Override default max distance

        Returns:
            List of search hits
        """
        if not keyword or not segments:
            return []

        if max_distance is not None:
            self._matcher._max_distance = max_distance
        else:
            self._matcher._max_distance = self._max_distance

        hits: list[SearchHit] = []

        for segment in segments:
            content = segment.content
            matches = self._matcher.find_matches(content, keyword)

            for start, end, dist in matches:
                matched_text = content[start:end]
                similarity = self._matcher._distance.similarity(matched_text, keyword)

                context_chars = self._options.context_chars
                context_before = content[max(0, start - context_chars) : start]
                context_after = content[end : end + context_chars]

                hit = SearchHit(
                    id=str(uuid.uuid4()),
                    source_type="segment",
                    source_id=segment.id,
                    score=similarity * 0.7,  # Lower base score for fuzzy matches
                    matched_text=matched_text,
                    context_before=context_before,
                    context_after=context_after,
                    speaker=segment.speaker,
                    position=MatchPosition(start=start, end=end),
                    matches=[],
                    metadata={
                        "segment_id": segment.id,
                        "start_time": segment.start_time,
                        "end_time": segment.end_time,
                        "edit_distance": dist,
                        "similarity": similarity,
                    },
                )

                hits.append(hit)

        # Sort by similarity score
        hits.sort(key=lambda h: h.metadata.get("similarity", 0), reverse=True)

        return hits

    def find_similar(
        self,
        text: str,
        candidates: list[str],
        threshold: float = 0.7,
    ) -> list[tuple[str, float]]:
        """
        Find candidates similar to the given text.

        Args:
            text: Text to compare against
            candidates: List of candidate strings
            threshold: Minimum similarity threshold

        Returns:
            List of (candidate, similarity) tuples above threshold
        """
        results: list[tuple[str, float]] = []

        for candidate in candidates:
            similarity = self._matcher._distance.similarity(text, candidate)
            if similarity >= threshold:
                results.append((candidate, similarity))

        # Sort by similarity descending
        results.sort(key=lambda x: x[1], reverse=True)

        return results

    def suggest_corrections(
        self,
        word: str,
        vocabulary: list[str],
        max_suggestions: int = 5,
    ) -> list[tuple[str, float]]:
        """
        Suggest spelling corrections for a word.

        Args:
            word: Word to check
            vocabulary: List of valid words
            max_suggestions: Maximum number of suggestions

        Returns:
            List of (suggestion, similarity) tuples
        """
        suggestions = self.find_similar(word, vocabulary, threshold=0.5)
        return suggestions[:max_suggestions]


__all__ = [
    "LevenshteinDistance",
    "FuzzyMatcher",
    "FuzzySearcher",
]
