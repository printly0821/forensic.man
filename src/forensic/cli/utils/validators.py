"""Input validators for CLI commands"""

import re
from pathlib import Path


class DateRangeValidator:
    DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
    RANGE_PATTERN = re.compile(r"^(\d{4}-\d{2}-\d{2}):(\d{4}-\d{2}-\d{2})$")

    @classmethod
    def validate_date(cls, date_str: str):
        from datetime import datetime

        if not cls.DATE_PATTERN.match(date_str):
            msg = f"Invalid date format: '{date_str}'. Expected YYYY-MM-DD."
            raise ValueError(msg)
        try:
            return datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError as e:
            msg = f"Invalid date: '{date_str}'. {e}"
            raise ValueError(msg) from e

    @classmethod
    def validate_range(cls, range_str: str):
        match = cls.RANGE_PATTERN.match(range_str)
        if not match:
            msg = f"Invalid range format: '{range_str}'. Expected YYYY-MM-DD:YYYY-MM-DD."
            raise ValueError(msg)
        start_str, end_str = match.groups()
        start = cls.validate_date(start_str)
        end = cls.validate_date(end_str)
        if start > end:
            msg = f"Start date ({start_str}) must be before end date ({end_str})."
            raise ValueError(msg)
        return start, end


class FilePathValidator:
    @staticmethod
    def validate_input_path(path: str | Path) -> Path:
        path_obj = Path(path).resolve()
        if not path_obj.exists():
            msg = f"Input path does not exist: {path}"
            raise ValueError(msg)
        return path_obj

    @staticmethod
    def validate_output_path(path: str | Path, create: bool = False) -> Path:
        path_obj = Path(path).resolve()
        if path_obj.exists() and not path_obj.is_dir():
            msg = f"Output path exists but is not a directory: {path}"
            raise ValueError(msg)
        if create and not path_obj.exists():
            from contextlib import suppress

            with suppress(OSError):
                path_obj.mkdir(parents=True, exist_ok=True)
        return path_obj


class SpeakerValidator:
    KNOWN_SPEAKERS = {
        "신동식": ["신동식", "동식", "아빠", "피고인"],
        "신기연": ["신기연", "기연", "엄마", "피해자"],
    }

    @classmethod
    def normalize_name(cls, name: str) -> str:
        name = name.strip()
        for canonical, aliases in cls.KNOWN_SPEAKERS.items():
            if name in aliases or name == canonical:
                return canonical
        return name

    @classmethod
    def validate_speaker(cls, name: str) -> str:
        normalized = cls.normalize_name(name)
        if normalized not in cls.KNOWN_SPEAKERS:
            known_list = ", ".join(cls.KNOWN_SPEAKERS.keys())
            msg = f"Unknown speaker: '{name}'. Known: {known_list}"
            raise ValueError(msg)
        return normalized


class OutputFormatValidator:
    VALID_FORMATS = {
        "table": "Terminal table output",
        "json": "JSON format",
        "csv": "CSV format",
        "markdown": "Markdown format",
        "html": "HTML format",
        "pdf": "PDF format",
    }

    @classmethod
    def validate(cls, format_str: str, command: str = "command") -> str:
        format_lower = format_str.lower()
        if format_lower not in cls.VALID_FORMATS:
            valid_list = ", ".join(cls.VALID_FORMATS.keys())
            msg = f"Invalid format '{format_str}' for {command}. Valid: {valid_list}"
            raise ValueError(msg)
        return format_lower
