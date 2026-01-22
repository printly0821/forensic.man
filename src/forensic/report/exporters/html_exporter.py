from pathlib import Path


class HTMLExporter:
    DEFAULT_CSS = "<style>body{font-family:sans-serif;max-width:900px;margin:0 auto;padding:20px;}</style>"

    def __init__(self, include_css: bool = True, custom_css: str | None = None) -> None:
        self._include_css = include_css
        self._css = custom_css or self.DEFAULT_CSS

    def export(self, report: any, output_path: Path) -> Path:
        if not output_path.suffix:
            output_path = output_path.with_suffix(".html")
        content = self._generate_html(report)
        output_path.write_text(content, encoding="utf-8")
        return output_path

    def _generate_html(self, report: any) -> str:
        lines = ["<!DOCTYPE html>", "<html><head>", f"<title>{report.title}</title>"]
        if self._include_css:
            lines.append(f"{self._css}")
        lines.extend(["</head><body>", f"<h1>{report.title}</h1>", f"<p>Report ID: {report.id}</p>", "</body></html>"])
        return "\n".join(lines)

def export_html(report: any, output_path: Path, include_css: bool = True) -> Path:
    exporter = HTMLExporter(include_css=include_css)
    return exporter.export(report, output_path)
