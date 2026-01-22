"""CLI result models"""
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field


class SpeakerStats(BaseModel):
    speaker_id: str
    speaker_name: str
    total_segments: int = 0
    total_words: int = 0
    total_duration_seconds: float = 0.0
    evidence_count: int = 0
    patterns_found: dict[str, int] = Field(default_factory=dict)


class ProcessingError(BaseModel):
    file_path: str
    error_type: str
    error_message: str
    timestamp: datetime = Field(default_factory=datetime.now)
    recovered: bool = False


class AnalyzeResult(BaseModel):
    total_files: int = 0
    total_segments: int = 0
    total_evidence: int = 0
    processing_time_seconds: float = 0.0
    patterns_found: dict[str, int] = Field(default_factory=dict)
    speaker_stats: dict[str, SpeakerStats] = Field(default_factory=dict)
    errors: list[ProcessingError] = Field(default_factory=list)
    cache_hits: int = 0
    output_path: Path | None = None

    def add_speaker_stats(self, stats: SpeakerStats) -> None:
        self.speaker_stats[stats.speaker_id] = stats

    def add_error(self, error: ProcessingError) -> None:
        self.errors.append(error)

    def increment_pattern_count(self, pattern_type: str) -> None:
        self.patterns_found[pattern_type] = self.patterns_found.get(pattern_type, 0) + 1

    @property
    def success_rate(self) -> float:
        if self.total_files == 0:
            return 0.0
        failed = len([e for e in self.errors if not e.recovered])
        return ((self.total_files - failed) / self.total_files) * 100
