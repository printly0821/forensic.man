"""forensic search command"""

import json
import sys
from pathlib import Path

import click
from rich.console import Console

from forensic.cli.output.table import TableFormatter
from forensic.cli.utils.validators import DateRangeValidator


@click.command()
@click.argument("query", required=True)
@click.option("--speaker", "-s", help="화자 필터")
@click.option("--date", "-d", help="날짜 범위 (YYYY-MM-DD:YYYY-MM-DD)")
@click.option("--importance", "-I", type=click.Choice(["HIGH", "MEDIUM", "LOW"]), multiple=True)
@click.option("--pattern", "-P", multiple=True)
@click.option("--regex", "-r", is_flag=True)
@click.option("--case-sensitive", is_flag=True)
@click.option("--limit", "-l", type=int, default=20)
@click.option("--output", "-o", type=click.Path())
@click.option("--format", "-F", type=click.Choice(["table", "json", "csv"]), default="table")
@click.pass_context
def search(
    ctx: click.Context,
    query: str,
    speaker: str | None,
    date: str | None,
    importance: tuple,
    pattern: tuple,
    regex: bool,
    case_sensitive: bool,
    limit: int,
    output: str | None,
    format: str,
) -> None:
    """키워드/패턴 검색"""
    _ = speaker, importance, pattern, regex, case_sensitive, limit  # Reserved for future use

    console_manager = ctx.obj.get("console_manager")
    console: Console = ctx.obj.get("console", Console())

    date_range = None
    if date:
        try:
            date_range = DateRangeValidator.validate_range(date)
        except ValueError as e:
            console_manager.error(f"날짜 오류: {e}")
            sys.exit(1)

    _ = date_range  # Reserved for future use

    console_manager.info(f"검색 중: '{query}'")
    results = []

    if format == "table":
        _display_table(results, console, console_manager)
    elif format == "json":
        _display_json(results, console)
    elif format == "csv":
        _display_csv(results, console)

    if output:
        _save_results(results, output, format, console_manager)


def _display_table(results: list, console: Console, console_manager) -> None:
    table = TableFormatter().search_results_table()
    if not results:
        console_manager.warning("검색 결과가 없습니다.")
        return
    for idx, result in enumerate(results[:20], 1):
        table.add_row(
            str(idx),
            result.get("speaker", "-"),
            result.get("date", "-"),
            result.get("text", "")[:50],
            str(result.get("score", 0)),
        )
    console.print(table)


def _display_json(results: list, console: Console) -> None:
    console.print_json(data=results)


def _display_csv(results: list, console: Console) -> None:
    import csv
    from io import StringIO

    output = StringIO()
    if results:
        writer = csv.DictWriter(output, fieldnames=["idx", "speaker", "date", "text", "score"])
        writer.writeheader()
        for idx, result in enumerate(results, 1):
            writer.writerow(
                {
                    "idx": idx,
                    "speaker": result.get("speaker", ""),
                    "date": result.get("date", ""),
                    "text": result.get("text", "")[:100],
                    "score": result.get("score", 0),
                }
            )
    console.print(output.getvalue())


def _save_results(results: list, output: str, format: str, console_manager) -> None:
    _ = format  # Reserved for future use
    output_path = Path(output)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    console_manager.success(f"결과 저장됨: {output_path}")
