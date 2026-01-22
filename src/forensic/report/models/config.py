from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, Field


class ReportConfig(BaseModel):
    output_format: Literal["MARKDOWN", "HTML", "PDF", "JSON"] = "MARKDOWN"
    language: str = "ko"
    include_toc: bool = True
    include_statistics: bool = True
    include_charts: bool = False
    date_filter: tuple[date, date] | None = None
    category_filter: list[str] | None = None
    speaker_filter: list[str] | None = None
    min_importance: Literal["HIGH", "MEDIUM", "LOW"] = "LOW"
    page_size: str = "A4"
    template: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    def should_include_evidence(self, importance: str) -> bool:
        importance_levels = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
        min_level = importance_levels[self.min_importance]
        evidence_level = importance_levels.get(importance, 0)
        return evidence_level >= min_level

class LegalReportConfig(ReportConfig):
    include_chain_of_custody: bool = True
    include_integrity_statement: bool = True
    max_evidence_per_page: int = 10
    case_number: str | None = None
    court_name: str | None = None

class TimelineReportConfig(ReportConfig):
    default_template: str = "chronological"
    highlight_threshold: int = 3
    include_monthly_summary: bool = True

class SummaryReportConfig(ReportConfig):
    default_template: str = "executive"
    max_key_findings: int = 10
    include_recommendations: bool = True
