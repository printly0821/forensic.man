"""
증거 ID 생성기
"""
from datetime import date
from threading import Lock
from typing import Optional


class IDGenerator:
    _instance: Optional["IDGenerator"] = None
    _lock = Lock()
    _counters: dict[str, int] = {}
    _counter_lock = Lock()

    def __new__(cls) -> "IDGenerator":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def _get_date_key(self) -> str:
        return date.today().strftime("%Y%m%d")

    def _get_month_key(self) -> str:
        return date.today().strftime("%Y%m")

    def _get_counter(self, key: str) -> int:
        with self._counter_lock:
            return self._counters.get(key, 0)

    def _increment_counter(self, key: str) -> int:
        with self._counter_lock:
            current = self._counters.get(key, 0)
            current += 1
            self._counters[key] = current
            return current

    def reset_counter(self, date_key: str | None = None) -> None:
        key = date_key or self._get_date_key()
        with self._counter_lock:
            self._counters[key] = 0

    def generate_evidence_id(self, date_key: str | None = None) -> str:
        key = date_key or self._get_date_key()
        sequence = self._increment_counter(key)
        return f"EVD-{key}-{sequence:04d}"

    def generate_chain_id(self, month_key: str | None = None) -> str:
        key = month_key or self._get_month_key()
        sequence = self._increment_counter(f"chain_{key}")
        return f"CHN-{key}-{sequence:04d}"

    def generate_report_id(self) -> str:
        key = self._get_date_key()
        sequence = self._increment_counter(f"report_{key}")
        return f"RPT-{key}-{sequence:04d}"

    def generate_document_id(self) -> str:
        key = self._get_date_key()
        sequence = self._increment_counter(f"document_{key}")
        return f"DOC-{key}-{sequence:04d}"

    def parse_evidence_id(self, evidence_id: str) -> tuple[str, int]:
        parts = evidence_id.split("-")
        if len(parts) != 3 or parts[0] != "EVD":
            raise ValueError(f"Invalid evidence ID format: {evidence_id}")
        try:
            date_key = parts[1]
            sequence = int(parts[2])
            return date_key, sequence
        except (ValueError, IndexError):
            raise ValueError(f"Invalid evidence ID format: {evidence_id}") from None

    def is_valid_evidence_id(self, evidence_id: str) -> bool:
        try:
            self.parse_evidence_id(evidence_id)
            return True
        except ValueError:
            return False


_generator: IDGenerator | None = None


def get_id_generator() -> IDGenerator:
    global _generator
    if _generator is None:
        _generator = IDGenerator()
    return _generator


def generate_evidence_id(date_key: str | None = None) -> str:
    return get_id_generator().generate_evidence_id(date_key)


def generate_chain_id(month_key: str | None = None) -> str:
    return get_id_generator().generate_chain_id(month_key)


def generate_document_id() -> str:
    return get_id_generator().generate_document_id()


def reset_counters() -> None:
    generator = get_id_generator()
    with generator._counter_lock:
        generator._counters.clear()


__all__ = [
    "IDGenerator",
    "get_id_generator",
    "generate_evidence_id",
    "generate_chain_id",
    "generate_document_id",
    "reset_counters",
]
