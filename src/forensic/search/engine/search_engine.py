"""
Search engine implementation

Provides the main SearchEngine class for performing searches on transcripts,
segments, and evidence with support for keyword, regex, and morpheme-based searches.
"""

import re
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from forensic.models import Segment, Transcript
from forensic.search.models import (
    FilterConfig,
    IndexStats,
    Match,
    MatchPosition,
    SearchContext,
    SearchHit,
    SearchOptions,
    SearchResult,
)


class SearchEngine:
    """
    Main search engine for forensic transcript analysis

    Provides keyword search, regex search, and morpheme-based search
    with filtering and ranking capabilities.
    """

    def __init__(
        self,
        transcripts: list[Transcript] | None = None,
        segments: list[Segment] | None = None,
        options: SearchOptions | None = None,
    ) -> None:
        """
        Initialize the search engine.

        Args:
            transcripts: List of transcripts to search
            segments: List of segments to search
            options: Default search options
        """
        self._transcripts: list[Transcript] = transcripts or []
        self._segments: list[Segment] = segments or []
        self._evidence: list[Any] = []  # Will be populated from evidence module
        self._options: SearchOptions = options or SearchOptions()
        self._index_built: bool = False
        self._index_stats: IndexStats = IndexStats()

    def add_transcripts(self, transcripts: list[Transcript]) -> None:
        """
        Add transcripts to the search index.

        Args:
            transcripts: List of transcripts to add
        """
        self._transcripts.extend(transcripts)
        for t in transcripts:
            self._segments.extend(t.segments)
        self._index_built = False

    def add_segments(self, segments: list[Segment]) -> None:
        """
        Add segments to the search index.

        Args:
            segments: List of segments to add
        """
        self._segments.extend(segments)
        self._index_built = False

    def add_evidence(self, evidence: list[Any]) -> None:
        """
        Add evidence to the search index.

        Args:
            evidence: List of evidence items to add
        """
        self._evidence.extend(evidence)
        self._index_built = False

    def build_index(self) -> IndexStats:
        """
        Build the search index from loaded data.

        Returns:
            Index statistics after building
        """
        start_time = time.time()

        # Count items
        total_documents = len(self._transcripts)
        total_segments = len(self._segments)
        total_evidence = len(self._evidence)

        # Tokenize and count
        total_tokens = 0
        unique_terms = set()

        for segment in self._segments:
            tokens = self._tokenize_text(segment.content)
            total_tokens += len(tokens)
            unique_terms.update(token.text.lower() for token in tokens)

        for transcript in self._transcripts:
            tokens = self._tokenize_text(transcript.content)
            total_tokens += len(tokens)
            unique_terms.update(token.text.lower() for token in tokens)

        for ev in self._evidence:
            content = getattr(ev, "description", "") or ""
            tokens = self._tokenize_text(content)
            total_tokens += len(tokens)
            unique_terms.update(token.text.lower() for token in tokens)

        build_time = time.time() - start_time

        self._index_stats = IndexStats(
            total_documents=total_documents,
            total_segments=total_segments,
            total_evidence=total_evidence,
            total_tokens=total_tokens,
            unique_terms=len(unique_terms),
            last_updated=datetime.now(),
            build_time_seconds=build_time,
            last_build=datetime.now(),
        )

        self._index_built = True
        return self._index_stats

    def search(
        self,
        query: str,
        options: SearchOptions | None = None,
        filters: FilterConfig | None = None,
    ) -> SearchResult:
        """
        Perform a basic keyword search.

        Args:
            query: Search query string
            options: Search options (uses default if not provided)
            filters: Filter configuration

        Returns:
            Search results with hits and metadata
        """
        start_time = time.time()
        opts = options or self._options
        ctx = SearchContext(
            query_id=str(uuid.uuid4()),
            timeout_seconds=opts.timeout_seconds,
        )

        # Validate query
        if not query or not query.strip():
            return SearchResult(
                query=query,
                total_hits=0,
                hits=[],
                search_time_ms=(time.time() - start_time) * 1000,
            )

        # Determine search targets
        targets = opts.search_targets or ["segment"]

        # Collect hits from all targets
        all_hits: list[SearchHit] = []

        if "transcript" in targets:
            all_hits.extend(self._search_transcripts(query, opts, ctx))

        if "segment" in targets:
            all_hits.extend(self._search_segments(query, opts, ctx))

        if "evidence" in targets:
            all_hits.extend(self._search_evidence(query, opts, ctx))

        # Apply filters
        if filters and filters.has_filters:
            all_hits = self._apply_filters(all_hits, filters)

        # Sort by score
        all_hits.sort(key=lambda h: h.score, reverse=True)

        # Apply max results limit
        all_hits = all_hits[: opts.max_results]

        search_time = (time.time() - start_time) * 1000

        # Build facets
        facets = self._build_facets(all_hits)

        return SearchResult(
            query=query,
            total_hits=len(all_hits),
            hits=all_hits,
            search_time_ms=search_time,
            filters_applied=filters.to_dict().keys() if filters else [],
            facets=facets,
            index_stats=self._index_stats if self._index_built else None,
        )

    def search_regex(
        self,
        pattern: str,
        options: SearchOptions | None = None,
        filters: FilterConfig | None = None,
    ) -> SearchResult:
        """
        Perform a regex search.

        Args:
            pattern: Regular expression pattern
            options: Search options
            filters: Filter configuration

        Returns:
            Search results
        """
        start_time = time.time()
        opts = options or self._options

        # Validate regex
        try:
            regex = re.compile(pattern, re.IGNORECASE if not opts.case_sensitive else 0)
        except re.error as e:
            return SearchResult(
                query=pattern,
                total_hits=0,
                hits=[],
                search_time_ms=(time.time() - start_time) * 1000,
                metadata={"error": f"Invalid regex: {e}"},
            )

        all_hits: list[SearchHit] = []

        # Search segments
        for segment in self._segments:
            for match in regex.finditer(segment.content):
                hit = self._create_regex_hit(segment, match, pattern, "segment", opts)
                all_hits.append(hit)

        # Apply filters
        if filters and filters.has_filters:
            all_hits = self._apply_filters(all_hits, filters)

        all_hits.sort(key=lambda h: h.score, reverse=True)
        all_hits = all_hits[: opts.max_results]

        return SearchResult(
            query=pattern,
            total_hits=len(all_hits),
            hits=all_hits,
            search_time_ms=(time.time() - start_time) * 1000,
            filters_applied=filters.to_dict().keys() if filters else [],
        )

    def search_morpheme(
        self,
        query: str,
        options: SearchOptions | None = None,
        filters: FilterConfig | None = None,
    ) -> SearchResult:
        """
        Perform a morpheme-based search for Korean text.

        This uses simple tokenization as a fallback. For full morpheme
        analysis, integrate with MeCab or Komoran.

        Args:
            query: Search query
            options: Search options
            filters: Filter configuration

        Returns:
            Search results
        """
        # For now, delegate to regular search with morpheme tokenization
        opts = options or self._options
        # Tokenize query for better matching
        query_tokens = self._tokenize_text(query)
        expanded_query = " ".join(t.text for t in query_tokens)

        return self.search(expanded_query, opts, filters)

    def get_index_stats(self) -> IndexStats:
        """
        Get current index statistics.

        Returns:
            Index statistics
        """
        return self._index_stats

    def _tokenize_text(self, text: str) -> list[Any]:
        """
        Simple tokenization of text.

        For production use with Korean, replace with MeCab/Konlpy.
        """
        from forensic.search.models.query import Token, TokenType

        if not text:
            return []

        tokens: list[Any] = []
        current = ""
        start = 0

        for i, char in enumerate(text):
            if char.isspace():
                if current:
                    tokens.append(Token(text=current, start=start, end=i))
                    current = ""
                    start = i + 1
                tokens.append(Token(text=char, start=i, end=i + 1, token_type=TokenType.WHITESPACE))
            elif char in ".,!?;:()[]{}\"'":
                if current:
                    tokens.append(Token(text=current, start=start, end=i))
                    current = ""
                    start = i + 1
                tokens.append(
                    Token(text=char, start=i, end=i + 1, token_type=TokenType.PUNCTUATION)
                )
            elif char.isdigit():
                if current and not current.isdigit():
                    tokens.append(Token(text=current, start=start, end=i))
                    current = ""
                    start = i
                current += char
            else:
                if current and current.isdigit():
                    tokens.append(Token(text=current, start=start, end=i))
                    current = ""
                    start = i
                current += char

        if current:
            tokens.append(Token(text=current, start=start, end=len(text)))

        return tokens

    def _search_segments(
        self,
        query: str,
        options: SearchOptions,
        ctx: SearchContext,
    ) -> list[SearchHit]:
        """Search within segments."""

        hits: list[SearchHit] = []
        query_lower = query.lower() if not options.case_sensitive else query

        for segment in self._segments:
            if ctx.is_timeout:
                break

            content = segment.content
            search_content = content.lower() if not options.case_sensitive else content

            # Find all matches
            start = 0
            while True:
                pos = search_content.find(query_lower, start)
                if pos == -1:
                    break

                # Calculate score based on position and content
                score = self._calculate_score(content, query, pos)

                # Extract context
                context_before = content[max(0, pos - options.context_chars) : pos]
                context_after = content[pos + len(query) : pos + len(query) + options.context_chars]

                hit = SearchHit(
                    id=str(uuid.uuid4()),
                    source_type="segment",
                    source_id=segment.id,
                    score=score,
                    matched_text=content[pos : pos + len(query)],
                    context_before=context_before,
                    context_after=context_after,
                    speaker=segment.speaker,
                    file_path=None,
                    position=MatchPosition(start=pos, end=pos + len(query)),
                    matches=[
                        Match(
                            text=content[pos : pos + len(query)],
                            position=MatchPosition(start=pos, end=pos + len(query)),
                            score=score,
                            term_matched=query,
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
                start = pos + 1

            ctx.results_found += len(hits)
            ctx.documents_processed += 1

        return hits

    def _search_transcripts(
        self,
        query: str,
        options: SearchOptions,
        ctx: SearchContext,
    ) -> list[SearchHit]:
        """Search within transcripts."""
        hits: list[SearchHit] = []
        query_lower = query.lower() if not options.case_sensitive else query

        for transcript in self._transcripts:
            if ctx.is_timeout:
                break

            content = transcript.content
            search_content = content.lower() if not options.case_sensitive else content

            start = 0
            while True:
                pos = search_content.find(query_lower, start)
                if pos == -1:
                    break

                score = self._calculate_score(content, query, pos)

                context_before = content[max(0, pos - options.context_chars) : pos]
                context_after = content[pos + len(query) : pos + len(query) + options.context_chars]

                hit = SearchHit(
                    id=str(uuid.uuid4()),
                    source_type="transcript",
                    source_id=transcript.id,
                    score=score,
                    matched_text=content[pos : pos + len(query)],
                    context_before=context_before,
                    context_after=context_after,
                    timestamp=transcript.date,
                    file_path=transcript.file_path,
                    position=MatchPosition(start=pos, end=pos + len(query)),
                    metadata={
                        "transcript_id": transcript.id,
                        "duration": transcript.duration_seconds,
                        "speaker_count": transcript.speaker_count,
                    },
                )

                hits.append(hit)
                start = pos + 1

            ctx.results_found += len(hits)
            ctx.documents_processed += 1

        return hits

    def _search_evidence(
        self,
        query: str,
        options: SearchOptions,
        ctx: SearchContext,
    ) -> list[SearchHit]:
        """Search within evidence items."""
        hits: list[SearchHit] = []
        query_lower = query.lower() if not options.case_sensitive else query

        for ev in self._evidence:
            if ctx.is_timeout:
                break

            content = getattr(ev, "description", "") or ""
            content_sample = getattr(ev, "content_sample", "") or ""
            full_content = f"{content} {content_sample}"

            search_content = full_content.lower() if not options.case_sensitive else full_content

            start = 0
            while True:
                pos = search_content.find(query_lower, start)
                if pos == -1:
                    break

                score = self._calculate_score(full_content, query, pos)

                context_before = full_content[max(0, pos - options.context_chars) : pos]
                context_after = full_content[
                    pos + len(query) : pos + len(query) + options.context_chars
                ]

                hit = SearchHit(
                    id=str(uuid.uuid4()),
                    source_type="evidence",
                    source_id=ev.id,
                    score=score,
                    matched_text=full_content[pos : pos + len(query)],
                    context_before=context_before,
                    context_after=context_after,
                    position=MatchPosition(start=pos, end=pos + len(query)),
                    metadata={
                        "evidence_id": ev.id,
                        "category": str(getattr(ev, "category", "")),
                        "importance": getattr(ev, "importance", "MEDIUM"),
                    },
                )

                hits.append(hit)
                start = pos + 1

            ctx.results_found += len(hits)
            ctx.documents_processed += 1

        return hits

    def _create_regex_hit(
        self,
        source: Segment | Transcript,
        match: re.Match,
        _pattern: str,  # noqa: ARG002
        source_type: str,
        options: SearchOptions,
    ) -> SearchHit:
        """Create a SearchHit from a regex match."""
        matched_text = match.group()
        start, end = match.span()

        context_before = match.string[max(0, start - options.context_chars) : start]
        context_after = match.string[
            end : end + options.context_chars
            if len(match.string) >= end + options.context_chars
            else len(match.string)
        ]

        metadata: dict[str, Any] = {}
        speaker: str | None = None
        file_path: Path | None = None
        timestamp: datetime | None = None

        if isinstance(source, Segment):
            metadata["segment_id"] = source.id
            metadata["start_time"] = source.start_time
            metadata["end_time"] = source.end_time
            speaker = source.speaker
        elif isinstance(source, Transcript):
            metadata["transcript_id"] = source.id
            file_path = source.file_path
            timestamp = source.date

        return SearchHit(
            id=str(uuid.uuid4()),
            source_type=source_type,  # type: ignore
            source_id=source.id,
            score=1.0,
            matched_text=matched_text,
            context_before=context_before,
            context_after=context_after,
            speaker=speaker,
            timestamp=timestamp,
            file_path=file_path,
            position=MatchPosition(start=start, end=end),
            metadata=metadata,
        )

    def _calculate_score(self, content: str, query: str, position: int) -> float:
        """
        Calculate relevance score for a match.

        Higher score for matches closer to the start of content.
        """
        base_score = 0.5

        # Position bonus (earlier matches get higher scores)
        position_factor = 1.0 - (position / max(len(content), 1))
        position_bonus = position_factor * 0.3

        # Exact phrase bonus
        phrase_bonus = 0.2 if " " in query else 0.0

        return min(base_score + position_bonus + phrase_bonus, 1.0)

    def _apply_filters(self, hits: list[SearchHit], filters: FilterConfig) -> list[SearchHit]:
        """Apply filters to search results."""
        filtered = hits

        if filters.speakers:
            filtered = [h for h in filtered if h.speaker in filters.speakers]

        if filters.importance:
            filtered = [h for h in filtered if h.metadata.get("importance") in filters.importance]

        if filters.pattern_types:
            filtered = [h for h in filtered if h.metadata.get("category") in filters.pattern_types]

        if filters.transcript_ids:
            filtered = [
                h for h in filtered if h.metadata.get("transcript_id") in filters.transcript_ids
            ]

        return filtered

    def _build_facets(self, hits: list[SearchHit]) -> dict[str, dict[str, int]]:
        """Build facet information from search results."""
        facets: dict[str, dict[str, int]] = {}

        # Speaker facet
        speaker_counts: dict[str, int] = {}
        for hit in hits:
            if hit.speaker:
                speaker_counts[hit.speaker] = speaker_counts.get(hit.speaker, 0) + 1
        if speaker_counts:
            facets["speaker"] = speaker_counts

        # Source type facet
        type_counts: dict[str, int] = {}
        for hit in hits:
            source_type = hit.source_type
            type_counts[source_type] = type_counts.get(source_type, 0) + 1
        if type_counts:
            facets["source_type"] = type_counts

        return facets


__all__ = ["SearchEngine"]
