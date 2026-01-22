"""forensic report command"""

import json
import sys
from contextlib import suppress
from pathlib import Path

import click
from rich.console import Console

from forensic.cli.models.config import ForensicCLIConfig
from forensic.cli.utils.validators import FilePathValidator, OutputFormatValidator


@click.command()
@click.option(
    "--type",
    "-t",
    "report_type",
    required=True,
    type=click.Choice(["legal", "timeline", "summary", "evidence", "statistical"]),
)
@click.option("--output", "-o", required=True, type=click.Path())
@click.option(
    "--format", "-f", type=click.Choice(["markdown", "html", "json", "pdf"]), default="markdown"
)
@click.option("--template", type=click.Path(exists=True))
@click.option("--date-range", "-d")
@click.option("--speaker", "-s")
@click.option("--min-importance", type=click.Choice(["HIGH", "MEDIUM", "LOW"]), default="LOW")
@click.pass_context
def report(
    ctx: click.Context,
    report_type: str,
    output: str,
    format: str,
    template: str | None,
    date_range: str | None,
    speaker: str | None,
    min_importance: str,
) -> None:
    """보고서 생성"""
    _ = template, date_range, speaker, min_importance  # Reserved for future use

    console_manager = ctx.obj.get("console_manager")
    config: ForensicCLIConfig = ctx.obj.get("config", ForensicCLIConfig())
    console: Console = ctx.obj.get("console", Console())

    _ = config  # Reserved for future use

    try:
        output_path = FilePathValidator.validate_output_path(Path(output), create=True)
    except ValueError as e:
        console_manager.error(f"출력 경로 오류: {e}")
        sys.exit(1)

    format = OutputFormatValidator.validate(format, "report")
    console_manager.info(f"{report_type} 보고서 생성 중...")

    _generate_report(report_type, output_path, format, console_manager)


def _generate_report(report_type: str, output_path: Path, format: str, console_manager) -> None:
    content = f"# {report_type.capitalize()} 보고서\n\n내용이 준비되었습니다."
    output_file = output_path / f"report.{format}"

    if format == "markdown":
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(content)
    elif format == "json":
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump({"content": content, "type": report_type}, f, indent=2, ensure_ascii=False)
    elif format == "html":
        html_content = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Report</title></head>
<body>{content}</body></html>"""
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html_content)
    elif format == "pdf":
        # PDF generation placeholder
        with suppress(NotImplementedError), open(output_file, "w", encoding="utf-8") as f:
            f.write(content)

    console_manager.success(f"보고서 생성됨: {output_file}")
