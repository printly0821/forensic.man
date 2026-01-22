"""forensic timeline command"""

import click
from rich.console import Console

from forensic.cli.output.table import TableFormatter


@click.command()
@click.option("--start", "-s", help="시작 날짜 (YYYY-MM-DD)")
@click.option("--end", "-e", help="종료 날짜 (YYYY-MM-DD)")
@click.option("--speaker", help="특정 화자 필터")
@click.option("--pattern", "-p", multiple=True)
@click.option("--output", "-o", type=click.Path())
@click.option("--format", "-f", type=click.Choice(["text", "json", "html"]), default="text")
@click.option("--resolution", "-r", type=click.Choice(["day", "week", "month"]), default="day")
@click.pass_context
def timeline(
    ctx: click.Context,
    start: str | None,
    end: str | None,
    speaker: str | None,
    pattern: tuple,
    output: str | None,
    format: str,
    resolution: str,
) -> None:
    """시계열 분석 및 타임라인 표시"""
    _ = start, end, speaker, pattern, resolution, output  # Reserved for future use

    console_manager = ctx.obj.get("console_manager")
    console: Console = ctx.obj.get("console", Console())

    console_manager.info("타임라인 생성 중...")
    events = _generate_timeline()

    if format == "text":
        _display_text_timeline(events, console, console_manager)
    elif format == "json":
        _display_json_timeline(events, console)
    elif format == "html":
        html_content = _generate_html_timeline(events)
        console.print(html_content)


def _generate_timeline() -> list:
    return [
        {
            "date": "2025-07-15",
            "time": "14:23",
            "speaker": "신동식",
            "pattern": "GASLIGHTING",
            "importance": "HIGH",
            "text": "네가 기억을 못 하는 건 뭐가 문제야?",
        }
    ]


def _display_text_timeline(events: list, console: Console, console_manager) -> None:
    table = TableFormatter().timeline_table()
    if not events:
        console_manager.warning("타임라인에 표시할 이벤트가 없습니다.")
        return
    for event in events:
        table.add_row(
            event.get("date", "-"),
            event.get("time", "-"),
            event.get("speaker", "-"),
            event.get("pattern", "-"),
            event.get("text", "")[:35],
        )
    console.print(table)


def _display_json_timeline(events: list, console: Console) -> None:
    console.print_json(data=events)


def _generate_html_timeline(events: list) -> str:
    _ = events  # Reserved for future use
    return "<!DOCTYPE html><html><body><h1>타임라인</h1></body></html>"
