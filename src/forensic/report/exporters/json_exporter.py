import json
from pathlib import Path


class JSONExporter:
    def __init__(self, include_metadata: bool = True, indent: int = 2) -> None:
        self._include_metadata = include_metadata
        self._indent = indent

    def export(self, report: any, output_path: Path) -> Path:
        if not output_path.suffix:
            output_path = output_path.with_suffix(".json")
        data = self._serialize_report(report)
        content = json.dumps(data, indent=self._indent, ensure_ascii=False, default=str)
        output_path.write_text(content, encoding="utf-8")
        return output_path

    def _serialize_report(self, report: any) -> dict:
        return {"id": report.id, "title": report.title, "report_type": report.report_type.value}

    def export_to_string(self, report: any) -> str:
        data = self._serialize_report(report)
        return json.dumps(data, indent=self._indent, ensure_ascii=False, default=str)

def export_json(report: any, output_path: Path, include_metadata: bool = True) -> Path:
    exporter = JSONExporter(include_metadata=include_metadata)
    return exporter.export(report, output_path)

def export_json_string(report: any, indent: int = 2) -> str:
    exporter = JSONExporter(indent=indent)
    return exporter.export_to_string(report)
