"""CLI progress tracking model"""
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field


class ProgressState(BaseModel):
    job_id: str
    started_at: datetime = Field(default_factory=datetime.now)
    last_updated: datetime = Field(default_factory=datetime.now)
    total_files: int = 0
    processed_files: int = 0
    current_file: str | None = None
    completed_files: list[str] = Field(default_factory=list)
    failed_files: list[str] = Field(default_factory=list)
    partial_results_path: Path | None = None
    can_resume: bool = True

    @property
    def progress_percentage(self) -> float:
        if self.total_files == 0:
            return 0.0
        return (self.processed_files / self.total_files) * 100

    @property
    def is_complete(self) -> bool:
        return self.processed_files >= self.total_files and self.total_files > 0

    @classmethod
    def create_new(cls, job_id: str, total_files: int, output_path: Path | None = None) -> "ProgressState":
        return cls(job_id=job_id, total_files=total_files)
