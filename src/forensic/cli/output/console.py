"""Console output management"""

from enum import Enum

from rich.console import Console
from rich.theme import Theme


class ColorPalette(str, Enum):
    SUCCESS = "green"
    ERROR = "red"
    WARNING = "yellow"
    INFO = "blue"


class ConsoleManager:
    THEME = Theme(
        {
            "success": "green",
            "error": "bold red",
            "warning": "bold yellow",
            "info": "blue",
        }
    )

    def __init__(
        self, color: str = "auto", unicode: bool = True, quiet: bool = False, verbose: bool = False
    ) -> None:
        self.color = color
        self.unicode = unicode
        self.quiet = quiet
        self.verbose = verbose

        force_terminal = color == "always"
        no_color = color == "never"

        self.console = Console(theme=self.THEME, force_terminal=force_terminal, no_color=no_color)

    def success(self, message: str, emoji: str = "OK") -> None:
        _ = emoji  # Reserved for future custom emoji support
        if not self.quiet:
            self.console.print(f"[success]OK[/success] {message}")

    def error(self, message: str, emoji: str = "X") -> None:
        _ = emoji  # Reserved for future custom emoji support
        self.console.print(f"[error]X[/error] {message}")

    def warning(self, message: str, emoji: str = "!") -> None:
        _ = emoji  # Reserved for future custom emoji support
        if not self.quiet:
            self.console.print(f"[warning]![/warning] {message}")

    def info(self, message: str, emoji: str = "i") -> None:
        _ = emoji  # Reserved for future custom emoji support
        if not self.quiet:
            self.console.print(f"[info]i[/info] {message}")

    def verbose(self, message: str) -> None:
        if self.verbose and not self.quiet:
            self.console.print(f"[dim]{message}[/dim]")

    def print(self, *args, **kwargs) -> None:
        self.console.print(*args, **kwargs)
