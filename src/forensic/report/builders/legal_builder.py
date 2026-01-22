from datetime import date
from typing import Any


class LegalReportBuilder:
    def __init__(self, _config: Any = None) -> None:
        self._title = "Legal Evidence Report"
        self._evidence_list = []
        self._date_range: tuple[date, date] | None = None

    def set_title(self, title: str) -> "LegalReportBuilder":
        self._title = title
        return self

    def build(self) -> Any:
        from forensic.report.generator.id_generator import generate_report_id
        from forensic.report.models.legal import LegalReport

        report = LegalReport(id=generate_report_id(), title=self._title)
        return report
