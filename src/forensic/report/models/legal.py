from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from forensic.report.models.report import Report, ReportType


class CaseInfo(BaseModel):
    case_number: str | None = None
    court_name: str | None = None
    plaintiff: str | None = None
    defendant: str | None = None
    case_type: Literal["CRIMINAL", "CIVIL", "OTHER"] = "CRIMINAL"
    filing_date: date | None = None

class EvidenceSummary(BaseModel):
    evidence_id: str
    category: str
    importance: Literal["HIGH", "MEDIUM", "LOW"]
    timestamp: datetime
    speaker: str
    content_sample: str
    context_summary: str
    source_reference: str

    @property
    def is_high_importance(self) -> bool:
        return self.importance == "HIGH"

class EvidenceChainSummary(BaseModel):
    chain_id: str
    chain_type: Literal["TEMPORAL", "PATTERN", "SPEAKER", "TOPIC"]
    description: str
    start_date: date
    end_date: date
    total_occurrences: int
    severity: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"]
    evidence_count: int

    @property
    def duration_days(self) -> int:
        return (self.end_date - self.start_date).days

class CustodyRecord(BaseModel):
    timestamp: datetime
    action: str
    performer: str
    location: str
    notes: str = ""

class Appendix(BaseModel):
    title: str
    content: str
    appendix_type: Literal["TRANSCRIPT", "IMAGE", "DOCUMENT", "OTHER"] = "OTHER"

class LegalReport(Report):
    case_info: CaseInfo | None = None
    evidence_list: list[EvidenceSummary] = Field(default_factory=list)
    evidence_chains: list[EvidenceChainSummary] = Field(default_factory=list)
    chain_of_custody: list[CustodyRecord] = Field(default_factory=list)
    integrity_statement: str = ""
    appendices: list[Appendix] = Field(default_factory=list)
    signature_placeholder: str = ""

    def __init__(self, **data: Any) -> None:
        if "report_type" not in data:
            data["report_type"] = ReportType.LEGAL
        super().__init__(**data)

    @property
    def total_evidence(self) -> int:
        return len(self.evidence_list)

    @property
    def high_importance_count(self) -> int:
        return sum(1 for e in self.evidence_list if e.is_high_importance)
