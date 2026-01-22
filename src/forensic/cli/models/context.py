"""CLI context model"""
from pathlib import Path

from pydantic import BaseModel
from rich.console import Console


class CLIContext(BaseModel):
    verbose: bool = False
    quiet: bool = False
    config_path: Path = Path.home() / ".forensic" / "config.yaml"
    _console: Console | None = None

    class Config:
        arbitrary_types_allowed = True

    @property
    def console(self) -> Console:
        if self._console is None:
            self._console = Console()
        return self._console

    def set_console(self, console: Console) -> None:
        self._console = console

    def should_show_progress(self) -> bool:
        return not self.quiet

    def should_show_verbose(self) -> bool:
        return self.verbose and not self.quiet
