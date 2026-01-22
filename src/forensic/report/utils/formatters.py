from datetime import date


class DateFormatter:
    ISO_FORMAT = "%Y-%m-%d"
    KOREAN_FORMAT = "%Y년 %m월 %d일"

    @classmethod
    def format_date(cls, date_obj: date, format_style: str = "korean") -> str:
        formats = {"iso": cls.ISO_FORMAT, "korean": cls.KOREAN_FORMAT}
        fmt = formats.get(format_style, cls.KOREAN_FORMAT)
        return date_obj.strftime(fmt)

    @classmethod
    def format_duration(cls, seconds: float) -> str:
        if seconds < 60:
            return f"{seconds:.1f}초"
        minutes = seconds / 60
        if minutes < 60:
            return f"{minutes:.1f}분"
        hours = minutes / 60
        return f"{hours:.1f}시간"

    @classmethod
    def format_date_range(cls, start_date: date, end_date: date) -> str:
        return f"{cls.format_date(start_date)} ~ {cls.format_date(end_date)}"

class NumberFormatter:
    @staticmethod
    def format_number(number: int) -> str:
        return f"{number:,}"

    @staticmethod
    def format_percentage(value: float, total: float, decimals: int = 1) -> str:
        if total == 0:
            return "0%"
        return f"{(value / total) * 100:.{decimals}f}%"

    @staticmethod
    def format_size(bytes: int) -> str:
        for unit in ["B", "KB", "MB", "GB"]:
            if bytes < 1024:
                return f"{bytes:.1f} {unit}"
            bytes /= 1024
        return f"{bytes:.1f} TB"

class ImportanceFormatter:
    LEVEL_LABELS = {"CRITICAL": "중대", "HIGH": "높음", "MEDIUM": "보통", "LOW": "낮음"}

    @classmethod
    def get_label(cls, level: str) -> str:
        return cls.LEVEL_LABELS.get(level.upper(), level)

    @classmethod
    def get_color(cls, level: str) -> str:
        colors = {"CRITICAL": "#e74c3c", "HIGH": "#e67e22", "MEDIUM": "#f39c12", "LOW": "#27ae60"}
        return colors.get(level.upper(), "#7f8c8d")

class TimestampFormatter:
    @staticmethod
    def format_timestamp(seconds: float) -> str:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
