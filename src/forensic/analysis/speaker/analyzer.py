"""
Speaker identification and statistics analysis.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import uuid4

if TYPE_CHECKING:
    from forensic.analysis.speaker.models import SpeakerStatistics, TurnTakingEvent
    from forensic.models.transcript import Segment, Transcript


class SpeakerAnalyzer:
    """
    Analyzer for speaker identification and statistics.

    Provides speaker identification from segments, alias normalization,
    comprehensive statistics computation, and turn-taking pattern analysis.

    Usage:
        analyzer = SpeakerAnalyzer()
        analyzer.add_known_speaker("speaker_1", "신동식", ["동식", "신씨", "아버지"])
        analyzer.add_known_speaker("speaker_2", "신기연", ["기연", "신기연씨"])

        speaker_id = analyzer.identify_speaker(segment)
        stats = analyzer.get_statistics(speaker_id)
    """

    # Default Korean aliases for common case participants
    DEFAULT_KNOWN_SPEAKERS = {
        "speaker_1": {
            "name": "신동식",
            "aliases": ["동식", "신씨", "아버지", "신동식씨", "아빠"],
        },
        "speaker_2": {
            "name": "신기연",
            "aliases": ["기연", "신기연씨", "기연씨", "딸"],
        },
    }

    INTERRUPTION_THRESHOLD = 0.5  # Seconds of overlap to consider interruption
    OVERLAP_THRESHOLD = 0.1  # Seconds to detect overlap

    def __init__(self, unknown_label: str = "UNKNOWN") -> None:
        """
        Initialize the speaker analyzer.

        Args:
            unknown_label: Label to use for unidentified speakers
        """
        self.unknown_label: str = unknown_label
        self._known_speakers: dict[str, dict] = dict(self.DEFAULT_KNOWN_SPEAKERS)
        self._statistics: dict[str, SpeakerStatistics] = {}
        self._alias_map: dict[str, str] = {}
        self._build_alias_map()

    def add_known_speaker(
        self,
        speaker_id: str,
        name: str,
        aliases: list[str] | None = None,
    ) -> None:
        """
        Register a known speaker with their aliases.

        Args:
            speaker_id: Unique identifier for the speaker
            name: Display name for the speaker
            aliases: List of aliases for this speaker
        """
        self._known_speakers[speaker_id] = {
            "name": name,
            "aliases": aliases or [],
        }
        self._build_alias_map()

    def remove_speaker(self, speaker_id: str) -> None:
        """
        Remove a known speaker.

        Args:
            speaker_id: Speaker ID to remove
        """
        if speaker_id in self._known_speakers:
            del self._known_speakers[speaker_id]
            self._build_alias_map()

    def _build_alias_map(self) -> None:
        """Build a mapping from all aliases to speaker IDs."""
        self._alias_map = {}
        for speaker_id, info in self._known_speakers.items():
            # Map the name itself
            self._alias_map[info["name"]] = speaker_id
            # Map all aliases
            for alias in info.get("aliases", []):
                self._alias_map[alias] = speaker_id

    def identify_speaker(self, segment: "Segment") -> str:
        """
        Identify the speaker from a segment.

        Uses the speaker field from the segment and normalizes it
        to a canonical speaker ID.

        Args:
            segment: Segment to analyze

        Returns:
            Canonical speaker ID
        """
        return self.normalize_alias(segment.speaker)

    def normalize_alias(self, name: str) -> str:
        """
        Convert a speaker name or alias to canonical speaker ID.

        Args:
            name: Speaker name or alias to normalize

        Returns:
            Canonical speaker ID, or unknown_label if not found
        """
        # Direct lookup
        if name in self._alias_map:
            return self._alias_map[name]

        # Case-insensitive lookup
        name_lower = name.lower()
        for alias, speaker_id in self._alias_map.items():
            if alias.lower() == name_lower:
                return speaker_id

        # Not found - return as-is if it looks like an ID
        if name.startswith("speaker_"):
            return name

        # Return unknown label
        return self.unknown_label

    def get_canonical_name(self, speaker_id: str) -> str:
        """
        Get the canonical display name for a speaker ID.

        Args:
            speaker_id: Speaker ID to look up

        Returns:
            Display name, or the speaker_id if not found
        """
        if speaker_id in self._known_speakers:
            return self._known_speakers[speaker_id]["name"]
        return speaker_id

    def compute_statistics(
        self,
        transcripts: list["Transcript"],
    ) -> dict[str, "SpeakerStatistics"]:
        """
        Compute statistics for all speakers across transcripts.

        Args:
            transcripts: List of transcripts to analyze

        Returns:
            Dictionary mapping speaker IDs to their statistics
        """
        from forensic.analysis.speaker.models import SpeakerStatistics

        stats: dict[str, SpeakerStatistics] = {}
        speaker_timings: dict[str, list[datetime]] = {}
        total_duration = 0.0

        # First pass: collect basic stats
        for transcript in transcripts:
            total_duration += transcript.duration_seconds

            for segment in transcript.segments:
                speaker_id = self.identify_speaker(segment)
                canonical_name = self.get_canonical_name(speaker_id)

                if speaker_id not in stats:
                    stats[speaker_id] = SpeakerStatistics(
                        speaker_id=speaker_id,
                        speaker_name=canonical_name,
                        aliases=self._known_speakers.get(speaker_id, {}).get("aliases", []),
                    )
                    speaker_timings[speaker_id] = []

                # Update segment stats
                stats[speaker_id].add_segment(
                    duration=segment.duration,
                    estimated_words=self._estimate_words(segment.content),
                )

                # Track timing
                from datetime import timedelta
                segment_time = transcript.date + timedelta(seconds=segment.start_time)
                speaker_timings[speaker_id].append(segment_time)

        # Second pass: compute derived stats
        for speaker_id, speaker_stats in stats.items():
            if speaker_id in speaker_timings and speaker_timings[speaker_id]:
                speaker_stats.first_appearance = min(speaker_timings[speaker_id])
                speaker_stats.last_appearance = max(speaker_timings[speaker_id])

            # Compute speaking ratio
            if total_duration > 0:
                speaker_stats.speaking_ratio = (
                    speaker_stats.total_duration_seconds / total_duration
                )

        self._statistics = stats
        return stats

    def get_statistics(self, speaker_id: str) -> Optional["SpeakerStatistics"]:
        """
        Get statistics for a specific speaker.

        Args:
            speaker_id: Speaker ID to look up

        Returns:
            SpeakerStatistics if available, None otherwise
        """
        return self._statistics.get(speaker_id)

    def get_all_statistics(self) -> dict[str, "SpeakerStatistics"]:
        """
        Get all computed speaker statistics.

        Returns:
            Dictionary of all speaker statistics
        """
        return self._statistics.copy()

    def get_speaking_ratio(self) -> dict[str, float]:
        """
        Get speaking ratio for all speakers.

        Returns:
            Dictionary mapping speaker IDs to their speaking ratio (0.0-1.0)
        """
        return {
            speaker_id: stats.speaking_ratio
            for speaker_id, stats in self._statistics.items()
        }

    def analyze_turn_taking(
        self,
        segments: list["Segment"],
        transcript_date: datetime | None = None,
    ) -> list["TurnTakingEvent"]:
        """
        Analyze turn-taking patterns in a sequence of segments.

        Detects interruptions, overlaps, and pauses between speakers.

        Args:
            segments: List of segments to analyze (should be time-ordered)
            transcript_date: Date of the transcript for timestamp generation

        Returns:
            List of turn-taking events
        """
        from forensic.analysis.speaker.models import TurnTakingEvent

        events: list[TurnTakingEvent] = []

        if len(segments) < 2:
            return events

        base_time = transcript_date or datetime.now()

        for i in range(len(segments) - 1):
            current = segments[i]
            next_seg = segments[i + 1]

            # Skip if same speaker
            if current.speaker == next_seg.speaker:
                continue

            # Calculate gap/overlap
            gap = next_seg.start_time - current.end_time
            overlap = max(0, -gap)

            # Detect interruption
            is_interruption = overlap > self.INTERRUPTION_THRESHOLD

            # Calculate timestamp for the event
            from datetime import timedelta
            timestamp = base_time + timedelta(seconds=current.end_time)

            event = TurnTakingEvent(
                id=str(uuid4()),
                timestamp=timestamp,
                from_speaker=self.identify_speaker(current),
                to_speaker=self.identify_speaker(next_seg),
                gap_seconds=gap,
                overlap_seconds=overlap,
                interruption=is_interruption,
            )

            events.append(event)

        return events

    def get_interruption_count(self, _speaker_id: str) -> int:
        """
        Count how many times a speaker interrupted others.

        Args:
            _speaker_id: Speaker ID to check (reserved for future use)

        Returns:
            Number of interruptions by this speaker
        """
        count = 0
        for _stats in self._statistics.values():
            # This would require tracking turn events separately
            # For now, return 0 as placeholder
            pass
        return count

    def get_interruptions_received(self, _speaker_id: str) -> int:
        """
        Count how many times a speaker was interrupted.

        Args:
            _speaker_id: Speaker ID to check (reserved for future use)

        Returns:
            Number of times this speaker was interrupted
        """
        return 0  # Placeholder

    @staticmethod
    def _estimate_words(text: str) -> int:
        """
        Estimate word count for Korean text.

        Args:
            text: Text to analyze

        Returns:
            Estimated word count
        """
        # For Korean, count meaningful characters
        # This is a rough estimate
        korean_chars = sum(1 for c in text if ord("가") <= ord(c) <= ord("힣"))
        english_words = len([w for w in text.split() if w])
        return korean_chars // 2 + english_words

    @property
    def known_speaker_count(self) -> int:
        """Get the number of known speakers."""
        return len(self._known_speakers)

    @property
    def known_speakers(self) -> list[str]:
        """Get list of known speaker IDs."""
        return list(self._known_speakers.keys())
