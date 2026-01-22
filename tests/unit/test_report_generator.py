"""
Unit tests for report generator.
"""

import pytest
from datetime import date

from forensic.report.generator.id_generator import (
    ReportIdGenerator,
    generate_report_id,
    is_valid_report_id,
    parse_report_id,
)
from forensic.report.generator.validator import (
    ReportDataValidator,
    ValidationResult,
)
from forensic.report.models.config import ReportConfig


class TestReportIdGenerator:
    """Test report ID generation."""

    def test_generate_id(self):
        """Test generating a report ID."""
        gen = ReportIdGenerator()
        report_id = gen.generate()
        assert report_id.startswith("RPT-")
        assert is_valid_report_id(report_id) is True

    def test_generate_id_sequential(self):
        """Test sequential ID generation."""
        gen = ReportIdGenerator()
        id1 = gen.generate()
        id2 = gen.generate()
        parts1 = parse_report_id(id1)
        parts2 = parse_report_id(id2)
        assert parts1["date"] == parts2["date"]
        assert parts2["sequence"] == parts1["sequence"] + 1

    def test_parse_id(self):
        """Test parsing report ID."""
        report_id = "RPT-20250115-0042"
        parts = parse_report_id(report_id)
        assert parts["prefix"] == "RPT"
        assert parts["date"] == "20250115"
        assert parts["sequence"] == 42

    def test_is_valid_id(self):
        """Test ID validation."""
        assert is_valid_report_id("RPT-20250115-0001") is True
        assert is_valid_report_id("INVALID") is False

    def test_singleton(self):
        """Test singleton pattern."""
        gen1 = ReportIdGenerator()
        gen2 = ReportIdGenerator()
        assert gen1 is gen2


class TestValidationResult:
    """Test ValidationResult."""

    def test_initial_state(self):
        """Test initial validation result state."""
        result = ValidationResult()
        assert result.is_valid is True
        assert result.errors == []
        assert result.has_warnings is False

    def test_add_error(self):
        """Test adding an error."""
        result = ValidationResult()
        result.add_error("field1", "Error message")
        assert result.is_valid is False
        assert len(result.errors) == 1

    def test_add_warning(self):
        """Test adding a warning."""
        result = ValidationResult()
        result.add_warning("field1", "Warning message")
        assert result.is_valid is True
        assert result.has_warnings is True


class TestReportDataValidator:
    """Test ReportDataValidator."""

    def test_validate_date_range_valid(self):
        """Test validating valid date range."""
        validator = ReportDataValidator()
        result = validator.validate_date_range(
            date(2025, 1, 1),
            date(2025, 1, 31),
        )
        assert result.is_valid is True

    def test_validate_date_range_invalid(self):
        """Test validating invalid date range."""
        validator = ReportDataValidator()
        result = validator.validate_date_range(
            date(2025, 1, 31),
            date(2025, 1, 1),
        )
        assert result.is_valid is False

    def test_validate_speakers(self):
        """Test speaker validation."""
        validator = ReportDataValidator()
        result = validator.validate_speakers(["Speaker A", "Speaker B"])
        assert result.is_valid is True

    def test_validate_speakers_empty(self):
        """Test validating empty speaker list."""
        validator = ReportDataValidator()
        result = validator.validate_speakers([])
        assert result.has_warnings is True

    def test_validate_speakers_duplicates(self):
        """Test validating speakers with duplicates."""
        validator = ReportDataValidator()
        result = validator.validate_speakers(["Speaker A", "Speaker A"])
        assert result.has_warnings is True

    def test_validate_report_config_valid(self):
        """Test validating valid report config."""
        validator = ReportDataValidator()
        config = ReportConfig(output_format="MARKDOWN")
        result = validator.validate_report_config(config)
        assert result.is_valid is True
