from datetime import date
from typing import Literal


class ValidationError:
    def __init__(self, field: str, message: str, severity: Literal["ERROR", "WARNING"] = "ERROR") -> None:
        self.field = field
        self.message = message
        self.severity = severity

class ValidationResult:
    def __init__(self) -> None:
        self._errors: list[ValidationError] = []
        self._warnings: list[ValidationError] = []

    def add_error(self, field: str, message: str) -> None:
        self._errors.append(ValidationError(field, message, "ERROR"))

    def add_warning(self, field: str, message: str) -> None:
        self._warnings.append(ValidationError(field, message, "WARNING"))

    @property
    def is_valid(self) -> bool:
        return len(self._errors) == 0

    @property
    def errors(self) -> list[ValidationError]:
        return list(self._errors)

    @property
    def warnings(self) -> list[ValidationError]:
        return list(self._warnings)

    @property
    def has_warnings(self) -> bool:
        return len(self._warnings) > 0

class ReportDataValidator:
    def validate_date_range(self, start_date: date | None, end_date: date | None) -> ValidationResult:
        result = ValidationResult()
        if start_date and end_date and start_date > end_date:
            result.add_error("date_range", "Start date must be before end date")
        return result

    def validate_speakers(self, speakers: list[str]) -> ValidationResult:
        result = ValidationResult()
        if not speakers:
            result.add_warning("speakers", "Speaker list is empty")
        elif len(set(speakers)) != len(speakers):
            result.add_warning("speakers", "Duplicate speakers detected")
        return result

    def validate_report_config(self, config: any) -> ValidationResult:
        result = ValidationResult()
        if config is None:
            result.add_error("config", "Configuration is None")
        return result
