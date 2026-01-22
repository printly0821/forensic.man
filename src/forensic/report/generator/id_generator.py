from datetime import date
from threading import Lock
from typing import ClassVar


class ReportIdGenerator:
    _instance: ClassVar["ReportIdGenerator | None"] = None
    _lock: ClassVar[Lock] = Lock()
    _daily_counters: dict[str, int] = {}
    _counter_lock: Lock = Lock()

    def __new__(cls) -> "ReportIdGenerator":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def generate(self) -> str:
        date_key = date.today().strftime("%Y%m%d")
        with self._counter_lock:
            if date_key not in self._daily_counters:
                self._daily_counters[date_key] = 0
            self._daily_counters[date_key] += 1
            counter = self._daily_counters[date_key]
        return f"RPT-{date_key}-{counter:04d}"

_id_generator = ReportIdGenerator()

def generate_report_id() -> str:
    return _id_generator.generate()

def is_valid_report_id(report_id: str) -> bool:
    parts = report_id.split("-")
    return len(parts) == 3 and parts[0] == "RPT"

def parse_report_id(report_id: str) -> dict[str, str | int]:
    parts = report_id.split("-")
    return {"prefix": parts[0], "date": parts[1], "sequence": int(parts[2])}
