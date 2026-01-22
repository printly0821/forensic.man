"""
Wildcard pattern matching for search

Supports * (zero or more characters) and ? (exactly one character)
wildcards in search patterns.
"""

import re
import uuid

from forensic.models import Segment
from forensic.search.models import Match, MatchPosition, SearchHit, SearchOptions


class WildcardMatcher:
    """
    Wildcard pattern matcher.

    Supports * (any characters) and ? (single character) wildcards.
    """

    def __init__(self) -> None:
        """Initialize the wildcard matcher."""
        self._patterns: dict[str, re.Pattern] = {}

    def compile(self, pattern: str) -> re.Pattern:
        """
        Compile a wildcard pattern to regex.

        Args:
            pattern: Wildcard pattern with * and ?

        Returns:
            Compiled regex pattern
        """
        if pattern in self._patterns:
            return self._patterns[pattern]

        # Escape special regex characters except * and ?
        escaped = re.escape(pattern)

        # Replace escaped wildcards with regex equivalents
        # \* -> .*, \? -> .
        regex_pattern = escaped.replace(r"\*", ".*").replace(r"\?", ".")

        # Add anchors to match complete tokens/phrases
        regex_pattern = f"^{regex_pattern}$"

        compiled = re.compile(regex_pattern, re.IGNORECASE)
        self._patterns[pattern] = compiled

        return compiled

    def match(self, text: str, pattern: str) -> bool:
        """
        Check if text matches the wildcard pattern.

        Args:
            text: Text to check
            pattern: Wildcard pattern

        Returns:
            True if text matches pattern
        """
        if not pattern or not text:
            return False

        regex = self.compile(pattern)
        return bool(regex.match(text))

    def find_all(
        self,
        text: str,
        pattern: str,
    ) -> list[tuple[str, int, int]]:
        """
        Find all matches of a wildcard pattern in text.

        Args:
            text: Text to search
            pattern: Wildcard pattern

        Returns:
            List of (matched_text, start, end) tuples
        """
        if not pattern or not text:
            return []

        results: list[tuple[str, int, int]] = []

        # Convert wildcard to regex for finding
        regex_str = self._wildcard_to_regex(pattern)
        regex = re.compile(regex_str, re.IGNORECASE)

        for match in regex.finditer(text):
            results.append(
                (
                    match.group(),
                    match.start(),
                    match.end(),
                )
            )

        return results

    def _wildcard_to_regex(self, pattern: str) -> str:
        """Convert wildcard pattern to regex string."""
        # Escape special characters
        escaped = re.escape(pattern)
        # Replace escaped wildcards
        return escaped.replace(r"\*", ".*").replace(r"\?", ".")

    def clear_cache(self) -> None:
        """Clear compiled pattern cache."""
        self._patterns.clear()


class WildcardSearcher:
    """
    Wildcard-based searcher for flexible text matching.

    Supports * and ? wildcards in search queries.
    """

    def __init__(
        self,
        options: SearchOptions | None = None,
    ) -> None:
        """
        Initialize the wildcard searcher.

        Args:
            options: Search options
        """
        self._options = options or SearchOptions()
        self._matcher = WildcardMatcher()

    def search(
        self,
        pattern: str,
        segments: list[Segment],
    ) -> list[SearchHit]:
        """
        Search for wildcard pattern matches in segments.

        Args:
            pattern: Wildcard pattern (* and ? supported)
            segments: List of segments to search

        Returns:
            List of search hits
        """
        if not pattern or not segments:
            return []

        # Validate pattern
        if not self._is_valid_pattern(pattern):
            return []

        hits: list[SearchHit] = []

        for segment in segments:
            content = segment.content

            # Find all matches
            matches = self._matcher.find_all(content, pattern)

            for matched_text, start, end in matches:
                context_chars = self._options.context_chars
                context_before = content[max(0, start - context_chars) : start]
                context_after = content[end : end + context_chars]

                hit = SearchHit(
                    id=str(uuid.uuid4()),
                    source_type="segment",
                    source_id=segment.id,
                    score=self._calculate_wildcard_score(content, matched_text, start),
                    matched_text=matched_text,
                    context_before=context_before,
                    context_after=context_after,
                    speaker=segment.speaker,
                    position=MatchPosition(start=start, end=end),
                    matches=[
                        Match(
                            text=matched_text,
                            position=MatchPosition(start=start, end=end),
                            score=1.0,
                            term_matched=pattern,
                        )
                    ],
                    metadata={
                        "segment_id": segment.id,
                        "start_time": segment.start_time,
                        "end_time": segment.end_time,
                    },
                )

                hits.append(hit)

        return hits

    def search_word_wildcard(
        self,
        pattern: str,
        segments: list[Segment],
    ) -> list[SearchHit]:
        """
        Search for word-level wildcard matches.

        The pattern is matched against individual words/tokens.

        Args:
            pattern: Wildcard pattern for word matching
            segments: List of segments to search

        Returns:
            List of search hits
        """
        from forensic.search.keyword.tokenizer import Tokenizer

        if not pattern or not segments:
            return []

        tokenizer = Tokenizer()
        hits: list[SearchHit] = []

        for segment in segments:
            tokens = tokenizer.tokenize_words(segment.content)

            for token in tokens:
                if self._matcher.match(token, pattern):
                    # Find position in original text
                    pos = segment.content.lower().find(token.lower())
                    if pos != -1:
                        context_chars = self._options.context_chars
                        context_before = segment.content[max(0, pos - context_chars) : pos]
                        context_after = segment.content[
                            pos + len(token) : pos + len(token) + context_chars
                        ]

                        hit = SearchHit(
                            id=str(uuid.uuid4()),
                            source_type="segment",
                            source_id=segment.id,
                            score=0.8,
                            matched_text=segment.content[pos : pos + len(token)],
                            context_before=context_before,
                            context_after=context_after,
                            speaker=segment.speaker,
                            position=MatchPosition(start=pos, end=pos + len(token)),
                            metadata={
                                "segment_id": segment.id,
                                "matched_token": token,
                            },
                        )

                        hits.append(hit)

        return hits

    def _is_valid_pattern(self, pattern: str) -> bool:
        """Check if pattern is valid."""
        if not pattern:
            return False

        # Reject patterns with only wildcards
        stripped = pattern.replace("*", "").replace("?", "")
        return not (len(stripped) == 0 and len(pattern) > 3)

    def _calculate_wildcard_score(
        self,
        _content: str,
        matched_text: str,
        _position: int,
    ) -> float:
        """
        Calculate score for a wildcard match.

        Args:
            content: Full content
            matched_text: Matched text
            position: Match position

        Returns:
            Score between 0 and 1
        """
        # Wildcard matches get lower base score than exact matches
        base_score = 0.5

        # Bonus for more specific matches (fewer wildcards)
        specificity_bonus = min(len(matched_text) / 20, 0.3)

        return min(base_score + specificity_bonus, 1.0)


__all__ = [
    "WildcardMatcher",
    "WildcardSearcher",
]
