"""Panel formatting utilities"""
from rich.panel import Panel


class PanelFormatter:
    @staticmethod
    def success(message: str, title: str = "성공") -> Panel:
        return Panel(f"[green]{message}[/green]", title=title, border_style="green")

    @staticmethod
    def error(message: str, title: str = "오류") -> Panel:
        return Panel(f"[red]{message}[/red]", title=title, border_style="red")

    @staticmethod
    def warning(message: str, title: str = "경고") -> Panel:
        return Panel(f"[yellow]{message}[/yellow]", title=title, border_style="yellow")

    @staticmethod
    def info(message: str, title: str = "정보") -> Panel:
        return Panel(f"[blue]{message}[/blue]", title=title, border_style="blue")

    @staticmethod
    def summary(title: str = "요약", **fields) -> Panel:
        lines = [f"[bold]{k}:[/bold] {v}" for k, v in fields.items()]
        return Panel("\n".join(lines), title=title, border_style="cyan")

    @staticmethod
    def analysis_summary(result: dict) -> Panel:
        content = f"""[bold]분석 완료[/bold]

파일 수: {result.get('total_files', 0)}
세그먼트: {result.get('total_segments', 0):,}
증거: {result.get('total_evidence', 0)}
처리 시간: {result.get('processing_time_seconds', 0):.2f}초"""
        return Panel(content, title="분석 결과 요약", border_style="green")
