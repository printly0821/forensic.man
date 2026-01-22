"""
Keyword searcher for exact and partial matching

Provides keyword search with support for exact match,
partial match, and phrase search.
"""

import uuid

from forensic.models import Segment, Transcript
from forensic.search.models import Match, MatchPosition, SearchHit, SearchOptions


class SearchHitExtended(SearchHit):
    """Extended search hit with additional metadata for keyword search."""

    def __init__(
        self,
        **kwargs,
    ):
        super().__init__(**kwargs)


class KeywordSearcher:
    """
    Keyword-based searcher for transcripts and segments.

    Provides exact match, partial match, and phrase search capabilities.
    """

    def __init__(self, options: SearchOptions | None = None) -> None:
        """
        Initialize the keyword searcher.

        Args:
            options: Default search options
        """
        self._options = options or SearchOptions()

    def search_exact(
        self,
        keyword: str,
        segments: list[Segment],
        case_sensitive: bool = False,
    ) -> list[SearchHit]:
        """
        Search for exact keyword matches.

        Args:
            keyword: Keyword to search for
            segments: List of segments to search
            case_sensitive: Whether to match case exactly

        Returns:
            List of search hits
        """
        if not keyword or not segments:
            return []

        hits: list[SearchHit] = []
        search_keyword = keyword if case_sensitive else keyword.lower()

        for segment in segments:
            content = segment.content
            search_content = content if case_sensitive else content.lower()

            position = 0
            while True:
                pos = search_content.find(search_keyword, position)
                if pos == -1:
                    break

                # Extract context
                context_chars = self._options.context_chars
                context_before = content[max(0, pos - context_chars) : pos]
                context_after = content[pos + len(keyword) : pos + len(keyword) + context_chars]

                hit = SearchHit(
                    id=str(uuid.uuid4()),
                    source_type="segment",
                    source_id=segment.id,
                    score=self._calculate_exact_score(content, keyword, pos),
                    matched_text=content[pos : pos + len(keyword)],
                    context_before=context_before,
                    context_after=context_after,
                    speaker=segment.speaker,
                    position=MatchPosition(start=pos, end=pos + len(keyword)),
                    matches=[
                        Match(
                            text=content[pos : pos + len(keyword)],
                            position=MatchPosition(start=pos, end=pos + len(keyword)),
                            score=1.0,
                            term_matched=keyword,
                        )
                    ],
                    metadata={
                        "segment_id": segment.id,
                        "start_time": segment.start_time,
                        "end_time": segment.end_time,
                        "confidence": segment.confidence,
                    },
                )

                hits.append(hit)
                position = pos + 1

        return hits

    def search_partial(
        self,
        keyword: str,
        segments: list[Segment],
        case_sensitive: bool = False,
    ) -> list[SearchHit]:
        """
        Search for partial keyword matches (substring).

        Args:
            keyword: Keyword to search for
            segments: List of segments to search
            case_sensitive: Whether to match case exactly

        Returns:
            List of search hits
        """
        # Partial search is the same as exact search for substrings
        return self.search_exact(keyword, segments, case_sensitive)

    def search_phrase(
        self,
        phrase: str,
        segments: list[Segment],
        case_sensitive: bool = False,
    ) -> list[SearchHit]:
        """
        Search for exact phrase matches.

        Args:
            phrase: Phrase to search for
            segments: List of segments to search
            case_sensitive: Whether to match case exactly

        Returns:
            List of search hits
        """
        if not phrase:
            return []

        # Phrase search is exact search for the full phrase
        return self.search_exact(phrase, segments, case_sensitive)

    def search_multiple(
        self,
        keywords: list[str],
        segments: list[Segment],
        match_all: bool = True,
        case_sensitive: bool = False,
    ) -> list[SearchHit]:
        """
        Search for multiple keywords.

        Args:
            keywords: List of keywords to search
            segments: List of segments to search
            match_all: If True, only return segments containing ALL keywords
            case_sensitive: Whether to match case exactly

        Returns:
            List of search hits
        """
        if not keywords or not segments:
            return []

        # Collect hits for each keyword
        all_hits: dict[str, list[SearchHit]] = {}

        for keyword in keywords:
            hits = self.search_exact(keyword, segments, case_sensitive)
            keyword_lower = keyword.lower() if not case_sensitive else keyword
            all_hits[keyword_lower] = hits

        if match_all:
            # For AND logic, find segments that match all keywords
            segment_hits: dict[str, list[SearchHit]] = {}

            for hits in all_hits.values():
                for hit in hits:
                    seg_id = hit.source_id
                    if seg_id not in segment_hits:
                        segment_hits[seg_id] = []
                    segment_hits[seg_id].append(hit)

            # Filter segments that have hits for all keywords
            result: list[SearchHit] = []
            for _seg_id, hits in segment_hits.items():
                if len(hits) == len(keywords):
                    result.extend(hits)

            return result
        else:
            # For OR logic, return all hits
            result: list[SearchHit] = []
            for hits in all_hits.values():
                result.extend(hits)

            return result

    def search_in_transcripts(
        self,
        keyword: str,
        transcripts: list[Transcript],
        case_sensitive: bool = False,
    ) -> list[SearchHit]:
        """
        Search for keyword in transcripts.

        Args:
            keyword: Keyword to search for
            transcripts: List of transcripts to search
            case_sensitive: Whether to match case exactly

        Returns:
            List of search hits
        """
        if not keyword or not transcripts:
            return []

        hits: list[SearchHit] = []
        search_keyword = keyword if case_sensitive else keyword.lower()

        for transcript in transcripts:
            content = transcript.content
            search_content = content if case_sensitive else content.lower()

            position = 0
            while True:
                pos = search_content.find(search_keyword, position)
                if pos == -1:
                    break

                context_chars = self._options.context_chars
                context_before = content[max(0, pos - context_chars) : pos]
                context_after = content[pos + len(keyword) : pos + len(keyword) + context_chars]

                hit = SearchHit(
                    id=str(uuid.uuid4()),
                    source_type="transcript",
                    source_id=transcript.id,
                    score=self._calculate_exact_score(content, keyword, pos),
                    matched_text=content[pos : pos + len(keyword)],
                    context_before=context_before,
                    context_after=context_after,
                    timestamp=transcript.date,
                    file_path=transcript.file_path,
                    position=MatchPosition(start=pos, end=pos + len(keyword)),
                    matches=[
                        Match(
                            text=content[pos : pos + len(keyword)],
                            position=MatchPosition(start=pos, end=pos + len(keyword)),
                            score=1.0,
                            term_matched=keyword,
                        )
                    ],
                    metadata={
                        "transcript_id": transcript.id,
                        "duration": transcript.duration_seconds,
                    },
                )

                hits.append(hit)
                position = pos + 1

        return hits

    def count_occurrences(
        self,
        keyword: str,
        text: str,
        case_sensitive: bool = False,
    ) -> int:
        """
        Count occurrences of a keyword in text.

        Args:
            keyword: Keyword to count
            text: Text to search in
            case_sensitive: Whether to match case exactly

        Returns:
            Number of occurrences
        """
        if not keyword or not text:
            return 0

        search_text = text if case_sensitive else text.lower()
        search_keyword = keyword if case_sensitive else keyword.lower()

        count = 0
        position = 0

        while True:
            pos = search_text.find(search_keyword, position)
            if pos == -1:
                break
            count += 1
            position = pos + 1

        return count

    def _calculate_exact_score(
        self,
        content: str,
        keyword: str,
        position: int,
    ) -> float:
        """
        Calculate score for an exact match.

        Args:
            content: Full content text
            keyword: Matched keyword
            position: Position of match

        Returns:
            Score between 0 and 1
        """
        base_score = 0.7

        # Position bonus (earlier matches score higher)
        position_factor = 1.0 - (position / max(len(content), 1))
        position_bonus = position_factor * 0.2

        # Length bonus (longer keywords score higher)
        length_factor = min(len(keyword) / 10, 1.0)
        length_bonus = length_factor * 0.1

        return min(base_score + position_bonus + length_bonus, 1.0)


__all__ = [
    "KeywordSearcher",
]
