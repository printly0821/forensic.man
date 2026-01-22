"""forensic config command"""

import os
import platform
import sys

import click
from rich.console import Console

from forensic.cli.models.config import ForensicCLIConfig
from forensic.cli.utils.config_loader import CLIConfigLoader
from forensic.cli.utils.dgx_detector import DGXSparkDetector


@click.command()
@click.option("--show", is_flag=True, help="현재 설정 표시")
@click.option("--edit", is_flag=True, help="설정 파일 편집")
@click.option("--reset", is_flag=True, help="기본 설정으로 초기화")
@click.option("--set", "set_values", nargs=2, multiple=True)
@click.option("--get", "get_key")
@click.option("--system-info", is_flag=True)
@click.pass_context
def config(
    ctx: click.Context,
    show: bool,
    edit: bool,
    reset: bool,
    set_values: tuple,
    get_key: str | None,
    system_info: bool,
) -> None:
    """설정 관리"""
    _ = edit, reset, set_values  # Reserved for future use

    console_manager = ctx.obj.get("console_manager")
    config_loader: CLIConfigLoader = ctx.obj.get("config_loader", CLIConfigLoader())
    console: Console = ctx.obj.get("console", Console())

    if system_info:
        _show_system_info(console, console_manager)
        return

    if get_key:
        _get_config_value(get_key, config_loader, console_manager)
        return

    if show:
        _show_config(config_loader.config, console, console_manager)
        return


def _show_system_info(console: Console, console_manager) -> None:
    _ = console_manager  # Reserved for future use

    from rich.panel import Panel

    detector = DGXSparkDetector()
    is_dgx = detector.is_dgx_spark()
    dgx_info = detector.detect() if is_dgx else {}

    info_lines = [
        f"플랫폼: {platform.system()} ({platform.machine()})",
        f"Python: {sys.version.split()[0]}",
        f"CPU 코어: {os.cpu_count()}개",
    ]

    if is_dgx:
        info_lines.extend(["", "[bold green]DGX Spark 감지됨[/bold green]"])

    _ = dgx_info  # Reserved for future use

    panel = Panel("\n".join(info_lines), title="시스템 정보", border_style="blue")
    console.print(panel)


def _get_config_value(key: str, config_loader: CLIConfigLoader, console_manager) -> None:
    value = config_loader.config.get(key)
    if value is None:
        console_manager.warning(f"설정 '{key}'을(를) 찾을 수 없습니다.")
        return
    console_manager.info(f"{key}: {value}")


def _show_config(config: ForensicCLIConfig, console: Console, console_manager) -> None:
    _ = console_manager  # Reserved for future use

    from rich.table import Table

    table = Table(title="현재 설정", show_header=True)
    table.add_column("섹션", style="cyan")
    table.add_column("항목", style="dim")
    table.add_column("값", justify="right")

    for key, value in [
        ("parallel_workers", config.analysis.parallel_workers),
        ("enable_gpu", config.analysis.enable_gpu),
        ("max_results", config.search.max_results),
        ("default_format", config.report.default_format),
        ("enabled", config.cache.enabled),
        ("color", config.output.color),
    ]:
        table.add_row("분석/검색/보고서/캐시/출력", key, str(value))

    console.print(table)
