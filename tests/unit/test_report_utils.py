"""
Unit tests for report utilities.
"""

import pytest
from datetime import date, datetime, time

from forensic.report.utils.formatters import (
    DateFormatter,
    ImportanceFormatter,
    NumberFormatter,
    TimestampFormatter,
)
from forensic.report.utils.sanitizers import (
    ContentSanitizer,
    PIISanitizer,
    sanitize_text,
)
from forensic.report.utils.statistics import (
    ReportStatistics,
    StatisticsCalculator,
)


class TestDateFormatter:
    """Test DateFormatter."""

    def test_format_date_iso(self):
        """Test ISO date format."""
        result = DateFormatter.format_date(date(2025, 1, 15), "iso")
        assert result == "2025-01-15"

    def test_format_date_korean(self):
        """Test Korean date format."""
        result = DateFormatter.format_date(date(2025, 1, 15), "korean")
        assert result == "2025년 01월 15일"

    def test_format_duration_minutes(self):
        """Test duration formatting - minutes."""
        result = DateFormatter.format_duration(150)
        assert "2.5" in result
        assert "분" in result

    def test_format_date_range(self):
        """Test date range formatting."""
        start = date(2025, 1, 1)
        end = date(2025, 1, 31)
        result = DateFormatter.format_date_range(start, end)
        assert "2025년 01월 01일" in result
        assert "2025년 01월 31일" in result


class TestNumberFormatter:
    """Test NumberFormatter."""

    def test_format_number(self):
        """Test number formatting."""
        result = NumberFormatter.format_number(1234567)
        assert result == "1,234,567"

    def test_format_percentage(self):
        """Test percentage formatting."""
        result = NumberFormatter.format_percentage(25, 100)
        assert result == "25.0%"

    def test_format_size_kb(self):
        """Test size formatting - KB."""
        result = NumberFormatter.format_size(2048)
        assert "2.0" in result
        assert "KB" in result


class TestImportanceFormatter:
    """Test ImportanceFormatter."""

    def test_get_label(self):
        """Test getting Korean label."""
        assert ImportanceFormatter.get_label("CRITICAL") == "중대"
        assert ImportanceFormatter.get_label("HIGH") == "높음"
        assert ImportanceFormatter.get_label("MEDIUM") == "보통"
        assert ImportanceFormatter.get_label("LOW") == "낮음"

    def test_get_color(self):
        """Test getting color for level."""
        assert ImportanceFormatter.get_color("CRITICAL") == "#e74c3c"
        assert ImportanceFormatter.get_color("HIGH") == "#e67e22"


class TestTimestampFormatter:
    """Test TimestampFormatter."""

    def test_format_timestamp(self):
        """Test timestamp formatting."""
        result = TimestampFormatter.format_timestamp(3665.5)
        assert result == "01:01:05"


class TestPIISanitizer:
    """Test PIISanitizer."""

    def test_sanitize_phone(self):
        """Test phone number masking."""
        sanitizer = PIISanitizer(mask_phone=True)
        text = "연락처: 010-1234-5678"
        result = sanitizer.sanitize(text)
        assert "010" in result
        assert "****" in result

    def test_sanitize_id_number(self):
        """Test Korean ID number masking."""
        sanitizer = PIISanitizer(mask_id_number=True)
        text = "주민번호: 900101-1234567"
        result = sanitizer.sanitize(text)
        assert "900101" in result
        assert "*******" in result

    def test_detect_pii(self):
        """Test PII detection."""
        sanitizer = PIISanitizer()
        text = "연락: 010-1234-5678"
        detected = sanitizer.detect_pii(text)
        assert "phone_numbers" in detected


class TestContentSanitizer:
    """Test ContentSanitizer."""

    def test_normalize_whitespace(self):
        """Test whitespace normalization."""
        text = "Hello    world\n\n  Test"
        result = ContentSanitizer.normalize_whitespace(text)
        assert result == "Hello world Test"

    def test_truncate(self):
        """Test text truncation."""
        text = "This is a very long text that needs to be truncated"
        result = ContentSanitizer.truncate(text, 20)
        # The implementation returns exactly 20 chars when truncated
        assert len(result) <= 23  # 20 + "..."
        assert "..." in result

    def test_escape_html(self):
        """Test HTML escaping."""
        text = "<script>alert('xss')</script>"
        result = ContentSanitizer.escape_html(text)
        assert "&lt;" in result
        assert "&gt;" in result


class TestStatisticsCalculator:
    """Test StatisticsCalculator."""

    def test_count_by_category(self):
        """Test counting by category."""
        calc = StatisticsCalculator()

        class Item:
            def __init__(self, category):
                self.category = category

        items = [Item("A"), Item("B"), Item("A"), Item("C"), Item("A")]
        result = calc.count_by_category(items, "category")
        assert result["A"] == 3
        assert result["B"] == 1
        assert result["C"] == 1

    def test_calculate_percentages(self):
        """Test percentage calculation."""
        calc = StatisticsCalculator()
        counts = {"A": 10, "B": 20, "C": 30}
        result = calc.calculate_percentages(counts)
        # Check that the value is close to expected
        assert abs(result["A"] - 16.67) < 0.01
        assert result["C"] == 50.0

    def test_calculate_date_range(self):
        """Test date range calculation."""
        calc = StatisticsCalculator()

        class Item:
            def __init__(self, timestamp):
                self.timestamp = timestamp

        items = [
            Item(date(2025, 1, 10)),
            Item(date(2025, 1, 5)),
            Item(date(2025, 1, 20)),
        ]
        result = calc.calculate_date_range(items)
        assert result[0] == date(2025, 1, 5)
        assert result[1] == date(2025, 1, 20)

    def test_calculate_speaker_similarity(self):
        """Test speaker similarity calculation."""
        calc = StatisticsCalculator()
        speakers1 = ["A", "B", "C"]
        speakers2 = ["B", "C", "D"]
        result = calc.calculate_speaker_similarity(speakers1, speakers2)
        assert result["jaccard"] == 0.5  # 2 common / 4 total
        assert "B" in result["common"]
