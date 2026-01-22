"""Signal handling for CLI operations"""

import signal
from collections.abc import Callable
from contextlib import suppress

from forensic.cli.models.progress import ProgressState


class SignalHandler:
    def __init__(self) -> None:
        self._interrupted = False
        self._original_handlers: dict[int, Callable] = {}
        self._on_interrupt_callbacks: list[Callable] = []

    def is_interrupted(self) -> bool:
        return self._interrupted

    def add_callback(self, callback: Callable) -> None:
        self._on_interrupt_callbacks.append(callback)

    def _handle_signal(self, signum: int, frame: object) -> None:
        _ = signum, frame  # Reserved for debugging
        self._interrupted = True
        for callback in self._on_interrupt_callbacks:
            with suppress(Exception):
                callback()
        self.restore()

    def setup(self, signals: list[int] | None = None) -> None:
        if signals is None:
            signals = [signal.SIGINT, signal.SIGTERM]
        for sig in signals:
            self._original_handlers[sig] = signal.signal(sig, self._handle_signal)

    def restore(self) -> None:
        for sig, handler in self._original_handlers.items():
            with suppress(Exception):
                signal.signal(sig, handler)
        self._original_handlers.clear()

    def reset(self) -> None:
        self._interrupted = False


class GracefulInterrupt:
    def __init__(
        self, progress_state: ProgressState | None = None, save_callback: Callable | None = None
    ) -> None:
        self.progress_state = progress_state
        self.save_callback = save_callback
        self.handler = SignalHandler()

    def _save_partial_results(self) -> None:
        import json

        if self.save_callback:
            with suppress(Exception):
                self.save_callback()

        if self.progress_state and self.progress_state.partial_results_path:
            try:
                with open(self.progress_state.partial_results_path, "w", encoding="utf-8") as f:
                    json.dump(
                        self.progress_state.model_dump(),
                        f,
                        indent=2,
                        ensure_ascii=False,
                        default=str,
                    )
            except Exception:
                pass

    def __enter__(self) -> SignalHandler:
        self.handler.add_callback(self._save_partial_results)
        self.handler.setup()
        return self.handler

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        _ = exc_type, exc_val, exc_tb  # Required by context manager protocol
        self.handler.restore()
        return False
