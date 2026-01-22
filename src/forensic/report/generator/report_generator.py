from typing import Any


class ReportGenerator:
    def __init__(self) -> None:
        from forensic.report.generator.validator import ReportDataValidator

        self._validator = ReportDataValidator()

    def generate_id(self) -> str:
        from forensic.report.generator.id_generator import generate_report_id

        return generate_report_id()

    def validate_data(self, data: dict[str, Any], _config: Any) -> Any:
        return self._validator.validate_date_range(data.get("start_date"), data.get("end_date"))

    def get_supported_formats(self) -> list[str]:
        return ["MARKDOWN", "HTML", "JSON"]

    def compute_hash(self, report: Any) -> str:
        import hashlib

        content = report.model_dump_json(exclude_none=True)
        return hashlib.sha256(content.encode("utf-8")).hexdigest()
