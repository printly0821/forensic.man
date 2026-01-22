from datetime import date, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ReportType(str, Enum):
    LEGAL = "LEGAL"
    TIMELINE = "TIMELINE"
    SUMMARY = "SUMMARY"

class ReportFormat(str, Enum):
    MARKDOWN = "MARKDOWN"
    HTML = "HTML"
    PDF = "PDF"
    JSON = "JSON"

class ReportMetadata(BaseModel):
    created_at: datetime = Field(default_factory=datetime.now)
    created_by: str = "forensic.man"
    version: str = "1.0.0"
    date_range: tuple[date, date] | None = None
    total_files: int = 0
    total_duration_minutes: float = 0
    integrity_hash: str = ""
    custom_fields: dict[str, Any] = Field(default_factory=dict)

class ReportSection(BaseModel):
    title: str
    content: str = ""
    order: int = 0
    subsections: list["ReportSection"] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

class Report(BaseModel):
    id: str
    report_type: ReportType
    title: str
    metadata: ReportMetadata = Field(default_factory=ReportMetadata)
    sections: list[ReportSection] = Field(default_factory=list)
    custom_data: dict[str, Any] = Field(default_factory=dict)

    @property
    def created_at(self) -> datetime:
        return self.metadata.created_at
