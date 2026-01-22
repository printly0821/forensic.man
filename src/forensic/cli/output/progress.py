"""Progress display management"""

from contextlib import contextmanager

from rich.progress import Progress, SpinnerColumn, TextColumn


class ProgressManager:
    def __init__(self, console=None, quiet: bool = False) -> None:
        self.console = console
        self.quiet = quiet

    @contextmanager
    def spinner(self, message: str = "Processing..."):
        if self.quiet:
            yield
            return
        with Progress(
            SpinnerColumn(), TextColumn(), console=self.console, transient=True
        ) as progress:
            task = progress.add_task(f"[cyan]{message}[/cyan]", total=None)
            yield
            progress.update(task, completed=1, total=1)
