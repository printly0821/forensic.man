from pathlib import Path


class MarkdownExporter:
    def __init__(self, include_toc: bool = True) -> None:
        self._include_toc = include_toc

    def export(self, report: any, output_path: Path) -> Path:
        if not output_path.suffix:
            output_path = output_path.with_suffix(".md")
        content = self._generate_content(report)
        output_path.write_text(content, encoding="utf-8")
        return output_path

    def _generate_content(self, report: any) -> str:
        lines = [f"# {report.title}", "", f"**Report ID**: {report.id}", ""]
        return "\n".join(lines)

def export_markdown(report: any, output_path: Path, include_toc: bool = True) -> Path:
    exporter = MarkdownExporter(include_toc=include_toc)
    return exporter.export(report, output_path)
