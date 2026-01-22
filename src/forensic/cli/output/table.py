"""Table formatting utilities"""
from datetime import datetime

from rich.table import Table


class TableFormatter:
    def create_table(self, headers: list[str], title: str = "") -> Table:
        table = Table(title=title, show_header=True, header_style="bold magenta")
        for header in headers:
            table.add_column(header)
        return table

    def search_results_table(self) -> Table:
        table = Table(title="검색 결과", show_header=True, header_style="bold magenta")
        table.add_column("번호", style="dim", width=6)
        table.add_column("화자", width=10)
        table.add_column("날짜", width=12)
        table.add_column("내용", width=50)
        table.add_column("점수", justify="right", width=8)
        return table

    def statistics_table(self) -> Table:
        table = Table(title="통계", show_header=True, header_style="bold cyan")
        table.add_column("항목", style="cyan", width=30)
        table.add_column("값", justify="right", width=15)
        return table

    def evidence_table(self) -> Table:
        table = Table(title="증거 목록", show_header=True, header_style="bold red")
        table.add_column("ID", style="dim", width=8)
        table.add_column("유형", width=12)
        table.add_column("중요도", width=8)
        table.add_column("화자", width=10)
        table.add_column("날짜", width=12)
        table.add_column("내용", width=40)
        return table

    def timeline_table(self) -> Table:
        table = Table(title="타임라인", show_header=True, header_style="bold blue")
        table.add_column("날짜", width=12)
        table.add_column("시간", width=8)
        table.add_column("화자", width=10)
        table.add_column("패턴", width=15)
        table.add_column("내용", width=35)
        return table

    def speaker_stats_table(self) -> Table:
        table = Table(title="화자 통계", show_header=True, header_style="bold green")
        table.add_column("화자", style="cyan", width=12)
        table.add_column("세그먼트", justify="right", width=10)
        table.add_column("단어", justify="right", width=10)
        table.add_column("증거", justify="right", width=8)
        table.add_column("지속시간", justify="right", width=12)
        return table

    @staticmethod
    def format_timestamp(ts: datetime | str | None) -> str:
        if ts is None:
            return "-"
        if isinstance(ts, str):
            try:
                ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except ValueError:
                return ts
        return ts.strftime("%Y-%m-%d %H:%M")

    @staticmethod
    def format_duration(seconds: float) -> str:
        if seconds < 60:
            return f"{seconds:.1f}초"
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}분 {secs}초"

    @staticmethod
    def format_number(n: int | float) -> str:
        return f"{n:,}"
