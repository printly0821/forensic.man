from typing import Any


class SummaryReportBuilder:
    def __init__(self, _config: Any = None) -> None:
        self._title = "Summary Report"
        self._key_findings = []

    def set_title(self, title: str) -> "SummaryReportBuilder":
        self._title = title
        return self

    def build(self) -> Any:
        from forensic.report.generator.id_generator import generate_report_id
        from forensic.report.models.summary import SummaryReport

        report = SummaryReport(id=generate_report_id(), title=self._title)
        return report
