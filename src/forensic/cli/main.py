"""CLI main entry point"""

import sys
from pathlib import Path

import click
from rich.console import Console

# Import commands at top level
from forensic.cli.commands.analyze_cmd import analyze
from forensic.cli.commands.config_cmd import config
from forensic.cli.commands.report_cmd import report
from forensic.cli.commands.search_cmd import search
from forensic.cli.commands.timeline_cmd import timeline
from forensic.cli.output.console import ConsoleManager
from forensic.cli.utils.config_loader import CLIConfigLoader


@click.group()
@click.version_option(version="0.1.0", prog_name="forensic")
@click.option("--verbose", "-v", is_flag=True, help="상세 로그 출력")
@click.option("--quiet", "-q", is_flag=True, help="최소 출력")
@click.option("--config", "-c", type=click.Path(exists=True), default=None, help="설정 파일 경로")
@click.option(
    "--color", type=click.Choice(["auto", "always", "never"]), default="auto", help="색상 출력 모드"
)
@click.pass_context
def cli(ctx: click.Context, verbose: bool, quiet: bool, config: str | None, color: str) -> None:
    """forensic.man - 녹취자료 분석 CLI 도구"""
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    ctx.obj["quiet"] = quiet
    ctx.obj["config_path"] = config
    ctx.obj["color"] = color

    config_path = Path(config) if config else None
    config_loader = CLIConfigLoader(config_path)
    ctx.obj["config"] = config_loader.config
    ctx.obj["config_loader"] = config_loader

    console_config = ctx.obj["config"].output
    console_color = color if color != "auto" else console_config.color
    ctx.obj["console_manager"] = ConsoleManager(
        color=console_color,
        unicode=console_config.unicode,
        quiet=quiet or console_config.quiet,
        verbose=verbose or console_config.verbose,
    )
    ctx.obj["console"] = Console()


# Register commands at module level
cli.add_command(analyze)
cli.add_command(search)
cli.add_command(report)
cli.add_command(timeline)
cli.add_command(config)


def main() -> int:
    try:
        cli()
        return 0
    except KeyboardInterrupt:
        print("\n작업이 중단되었습니다.", file=sys.stderr)
        return 130
    except Exception as exc:
        console = Console()
        console.print(f"[red]오류가 발생했습니다:[/red] {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
