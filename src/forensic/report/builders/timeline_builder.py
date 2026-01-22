from typing import Any


class TimelineReportBuilder:
    def __init__(self, _config: Any = None) -> None:
        self._title = "Timeline Report"
        self._events = []

    def set_title(self, title: str) -> "TimelineReportBuilder":
        self._title = title
        return self

    def build(self) -> Any:
        from forensic.report.generator.id_generator import generate_report_id
        from forensic.report.models.timeline import TimelineReport

        report = TimelineReport(id=generate_report_id(), title=self._title)
        return report
