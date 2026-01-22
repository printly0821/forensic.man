"""
Index builder for search engine

Builds and maintains the search index for transcripts, segments, and evidence.
"""

import time
from collections import defaultdict
from datetime import datetime
from typing import Any

from forensic.models import Segment, Transcript
from forensic.search.models import IndexStats


class IndexEntry:
    """
    A single entry in the search index.

    Maps a term to documents/segments containing that term.
    """

    def __init__(self, term: str) -> None:
        """
        Initialize an index entry.

        Args:
            term: The indexed term (lowercase)
        """
        self.term: str = term.lower()
        self.document_ids: set[str] = set()
        self.segment_ids: set[str] = set()
        self.evidence_ids: set[str] = set()
        self.positions: dict[str, list[int]] = defaultdict(list)
        self.frequency: int = 0

    def add_occurrence(
        self,
        item_id: str,
        item_type: str,
        position: int,
    ) -> None:
        """
        Add an occurrence of this term.

        Args:
            item_id: ID of the document/segment
            item_type: Type of item (transcript, segment, evidence)
            position: Position of the term in the text
        """
        self.frequency += 1

        if item_type == "transcript":
            self.document_ids.add(item_id)
        elif item_type == "segment":
            self.segment_ids.add(item_id)
        elif item_type == "evidence":
            self.evidence_ids.add(item_id)

        self.positions[item_id].append(position)

    def get_idf(self, total_docs: int) -> float:
        """
        Calculate inverse document frequency for this term.

        Args:
            total_docs: Total number of documents

        Returns:
            IDF score
        """
        doc_count = len(self.document_ids) + len(self.segment_ids)
        if doc_count == 0:
            return 0.0
        import math

        return math.log(total_docs / doc_count)


class InvertedIndex:
    """
    Inverted index for fast text search.

    Maps terms to the documents/segments containing them.
    """

    def __init__(self) -> None:
        """Initialize an empty inverted index."""
        self._entries: dict[str, IndexEntry] = {}
        self._total_docs: int = 0
        self._total_segments: int = 0
        self._total_evidence: int = 0

    def add_term(
        self,
        term: str,
        item_id: str,
        item_type: str,
        position: int,
    ) -> None:
        """
        Add a term occurrence to the index.

        Args:
            term: The term to index
            item_id: ID of the document/segment
            item_type: Type of item
            position: Position in the text
        """
        term_lower = term.lower()

        if term_lower not in self._entries:
            self._entries[term_lower] = IndexEntry(term)

        self._entries[term_lower].add_occurrence(item_id, item_type, position)

    def get_entry(self, term: str) -> IndexEntry | None:
        """
        Get the index entry for a term.

        Args:
            term: The term to look up

        Returns:
            IndexEntry if found, None otherwise
        """
        return self._entries.get(term.lower())

    def get_terms(self) -> set[str]:
        """
        Get all indexed terms.

        Returns:
            Set of all terms in the index
        """
        return set(self._entries.keys())

    def contains(self, term: str) -> bool:
        """
        Check if a term is in the index.

        Args:
            term: The term to check

        Returns:
            True if the term is indexed
        """
        return term.lower() in self._entries

    def get_postings(self, term: str) -> list[str]:
        """
        Get posting list for a term (all document IDs containing it).

        Args:
            term: The term to look up

        Returns:
            List of document IDs containing the term
        """
        entry = self.get_entry(term)
        if not entry:
            return []

        return list(entry.document_ids | entry.segment_ids | entry.evidence_ids)

    @property
    def size(self) -> int:
        """Get number of unique terms in the index."""
        return len(self._entries)

    @property
    def total_documents(self) -> int:
        """Get total number of documents indexed."""
        return self._total_docs

    @property
    def total_segments(self) -> int:
        """Get total number of segments indexed."""
        return self._total_segments

    @property
    def total_evidence(self) -> int:
        """Get total number of evidence items indexed."""
        return self._total_evidence

    def increment_counts(self, doc_count: int, segment_count: int, evidence_count: int) -> None:
        """Increment item counts."""
        self._total_docs += doc_count
        self._total_segments += segment_count
        self._total_evidence += evidence_count


class IndexBuilder:
    """
    Builds and updates the search index.

    Processes transcripts, segments, and evidence to create
    an inverted index for fast searching.
    """

    def __init__(self) -> None:
        """Initialize the index builder."""
        self._index: InvertedIndex = InvertedIndex()
        self._transcripts: dict[str, Transcript] = {}
        self._segments: dict[str, Segment] = {}
        self._evidence: dict[str, Any] = {}
        self._built: bool = False
        self._build_time: float = 0.0

    @property
    def index(self) -> InvertedIndex:
        """Get the inverted index."""
        return self._index

    @property
    def is_built(self) -> bool:
        """Check if the index has been built."""
        return self._built

    def build(
        self,
        transcripts: list[Transcript] | None = None,
        segments: list[Segment] | None = None,
        evidence: list[Any] | None = None,
    ) -> IndexStats:
        """
        Build the search index from the provided data.

        Args:
            transcripts: List of transcripts to index
            segments: List of segments to index
            evidence: List of evidence items to index

        Returns:
            Index statistics after building
        """
        start_time = time.time()

        # Reset index
        self._index = InvertedIndex()
        self._transcripts.clear()
        self._segments.clear()
        self._evidence.clear()

        total_tokens = 0

        # Index transcripts
        if transcripts:
            for transcript in transcripts:
                self._index_transcript(transcript)
                total_tokens += self._count_tokens(transcript.content)
            self._index.increment_counts(len(transcripts), 0, 0)

        # Index segments
        if segments:
            for segment in segments:
                self._index_segment(segment)
                total_tokens += self._count_tokens(segment.content)
            self._index.increment_counts(0, len(segments), 0)

        # Index evidence
        if evidence:
            for ev in evidence:
                self._index_evidence(ev)
                content = getattr(ev, "description", "") or ""
                total_tokens += self._count_tokens(content)
            self._index.increment_counts(0, 0, len(evidence))

        self._build_time = time.time() - start_time
        self._built = True

        return IndexStats(
            total_documents=self._index.total_documents,
            total_segments=self._index.total_segments,
            total_evidence=self._index.total_evidence,
            total_tokens=total_tokens,
            unique_terms=self._index.size,
            build_time_seconds=self._build_time,
            last_updated=datetime.now(),
            last_build=datetime.now(),
        )

    def add_transcripts(self, transcripts: list[Transcript]) -> None:
        """
        Add transcripts to an existing index.

        Args:
            transcripts: List of transcripts to add
        """
        for transcript in transcripts:
            self._index_transcript(transcript)
        self._index.increment_counts(len(transcripts), 0, 0)

    def add_segments(self, segments: list[Segment]) -> None:
        """
        Add segments to an existing index.

        Args:
            segments: List of segments to add
        """
        for segment in segments:
            self._index_segment(segment)
        self._index.increment_counts(0, len(segments), 0)

    def add_evidence(self, evidence: list[Any]) -> None:
        """
        Add evidence to an existing index.

        Args:
            evidence: List of evidence items to add
        """
        for ev in evidence:
            self._index_evidence(ev)
        self._index.increment_counts(0, 0, len(evidence))

    def remove_document(self, doc_id: str) -> bool:
        """
        Remove a document from the index.

        Args:
            doc_id: ID of the document to remove

        Returns:
            True if document was found and removed
        """
        if doc_id in self._transcripts:
            del self._transcripts[doc_id]
            return True
        if doc_id in self._segments:
            del self._segments[doc_id]
            return True
        if doc_id in self._evidence:
            del self._evidence[doc_id]
            return True
        return False

    def get_stats(self) -> IndexStats:
        """
        Get current index statistics.

        Returns:
            Index statistics
        """
        total_tokens = sum(self._count_tokens(t.content) for t in self._transcripts.values()) + sum(
            self._count_tokens(s.content) for s in self._segments.values()
        )

        return IndexStats(
            total_documents=len(self._transcripts),
            total_segments=len(self._segments),
            total_evidence=len(self._evidence),
            total_tokens=total_tokens,
            unique_terms=self._index.size,
            build_time_seconds=self._build_time,
            last_updated=datetime.now(),
            last_build=datetime.now() if self._built else None,
        )

    def _index_transcript(self, transcript: Transcript) -> None:
        """Index a single transcript."""
        self._transcripts[transcript.id] = transcript

        tokens = self._tokenize(transcript.content)
        for i, token in enumerate(tokens):
            self._index.add_term(
                token,
                transcript.id,
                "transcript",
                i,
            )

    def _index_segment(self, segment: Segment) -> None:
        """Index a single segment."""
        self._segments[segment.id] = segment

        tokens = self._tokenize(segment.content)
        for i, token in enumerate(tokens):
            self._index.add_term(
                token,
                segment.id,
                "segment",
                i,
            )

    def _index_evidence(self, evidence: Any) -> None:
        """Index a single evidence item."""
        self._evidence[evidence.id] = evidence

        content = getattr(evidence, "description", "") or ""
        content += " " + getattr(evidence, "content_sample", "") or ""

        tokens = self._tokenize(content)
        for i, token in enumerate(tokens):
            self._index.add_term(
                token,
                evidence.id,
                "evidence",
                i,
            )

    def _tokenize(self, text: str) -> list[str]:
        """
        Tokenize text for indexing.

        Simple whitespace/punctuation-based tokenization.
        For Korean text, consider using MeCab or Konlpy.

        Args:
            text: Text to tokenize

        Returns:
            List of tokens
        """
        if not text:
            return []

        import re

        # Split on whitespace and punctuation, keep Korean characters
        tokens = re.findall(r"[\w]+|[가-힣]+", text.lower())
        return tokens

    def _count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        return len(self._tokenize(text))


__all__ = [
    "IndexEntry",
    "InvertedIndex",
    "IndexBuilder",
]
