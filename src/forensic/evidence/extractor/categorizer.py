"""
증거 카테고리 분류 모듈
"""

from forensic.evidence.models.evidence import Evidence, EvidenceCategory


class EvidenceCategorizer:
    PATTERN_CATEGORY_MAP = {
        "GASLIGHTING": EvidenceCategory.GASLIGHTING,
        "DENIAL_OF_REALITY": EvidenceCategory.GASLIGHTING,
        "TRIVIALIZING": EvidenceCategory.GASLIGHTING,
        "COUNTERING": EvidenceCategory.GASLIGHTING,
        "FORGETTING_DENIAL": EvidenceCategory.GASLIGHTING,
        "BLOCKING_DIVERTING": EvidenceCategory.GASLIGHTING,
        "EMOTIONAL_MANIPULATION": EvidenceCategory.EMOTIONAL_MANIPULATION,
        "GUILT_TRIPPING": EvidenceCategory.EMOTIONAL_MANIPULATION,
        "PLAYING_VICTIM": EvidenceCategory.EMOTIONAL_MANIPULATION,
        "BLAME_SHIFTING": EvidenceCategory.EMOTIONAL_MANIPULATION,
        "SILENT_TREATMENT": EvidenceCategory.EMOTIONAL_MANIPULATION,
        "EXPLICIT_THREAT": EvidenceCategory.THREAT,
        "FINANCIAL_THREAT": EvidenceCategory.FINANCIAL_ABUSE,
        "VIOLENCE_THREAT": EvidenceCategory.THREAT,
        "DIRECT_THREAT": EvidenceCategory.THREAT,
        "INTIMIDATION": EvidenceCategory.THREAT,
        "ISOLATION_TACTIC": EvidenceCategory.ISOLATION,
        "SOCIAL_RESTRICTION": EvidenceCategory.ISOLATION,
        "CONTACT_BLOCKING": EvidenceCategory.ISOLATION,
        "FINANCIAL_CONTROL": EvidenceCategory.FINANCIAL_ABUSE,
        "MONEY_WITHHOLDING": EvidenceCategory.FINANCIAL_ABUSE,
        "Economic_COERCION": EvidenceCategory.FINANCIAL_ABUSE,
        "DENIAL": EvidenceCategory.DENIAL,
        "GASLIGHTING_DENIAL": EvidenceCategory.GASLIGHTING,
    }

    KEYWORD_CATEGORY_RULES = {
        EvidenceCategory.THREAT: ["죽여", "때려", "가만두지", "신고", "폭행", "위협"],
        EvidenceCategory.FINANCIAL_ABUSE: [
            "돈", "카드", "계좌", "용돈", "재산", "생활비", "경제적"
        ],
        EvidenceCategory.ISOLATION: ["만나지", "연락하지", "고립", "외출", "금지"],
        EvidenceCategory.GASLIGHTING: ["기억나지", "상상", "과민", "잘못", "허위"],
    }

    def __init__(
        self,
        pattern_map: dict[str, EvidenceCategory] | None = None,
        keyword_rules: dict[EvidenceCategory, list[str]] | None = None,
    ) -> None:
        self.pattern_map = pattern_map or self.PATTERN_CATEGORY_MAP
        self.keyword_rules = keyword_rules or self.KEYWORD_CATEGORY_RULES

    def categorize_by_pattern(self, pattern_type: str) -> EvidenceCategory:
        if pattern_type in self.pattern_map:
            return self.pattern_map[pattern_type]
        for pattern, category in self.pattern_map.items():
            if pattern in pattern_type or pattern_type in pattern:
                return category
        return EvidenceCategory.OTHER

    def categorize_by_keywords(self, content: str) -> EvidenceCategory | None:
        if not content:
            return None
        content_lower = content.lower()
        for category, keywords in self.keyword_rules.items():
            if any(keyword in content_lower for keyword in keywords):
                return category
        return None

    def categorize(
        self,
        pattern_type: str,
        content: str = "",
    ) -> EvidenceCategory:
        category = self.categorize_by_pattern(pattern_type)
        if category == EvidenceCategory.OTHER and content:
            keyword_category = self.categorize_by_keywords(content)
            if keyword_category:
                category = keyword_category
        return category

    def categorize_evidence(self, evidence: Evidence) -> EvidenceCategory:
        category = self.categorize(
            pattern_type=evidence.source_pattern_type,
            content=evidence.content_sample,
        )
        evidence.category = category
        return category

    def is_repeated_abuse(self, occurrence_count: int, date_range_days: int) -> bool:
        return occurrence_count >= 5 and date_range_days >= 5


_default_categorizer: EvidenceCategorizer | None = None


def get_categorizer() -> EvidenceCategorizer:
    global _default_categorizer
    if _default_categorizer is None:
        _default_categorizer = EvidenceCategorizer()
    return _default_categorizer


def categorize(
    pattern_type: str,
    content: str = "",
) -> EvidenceCategory:
    return get_categorizer().categorize(pattern_type, content)


__all__ = ["EvidenceCategorizer", "get_categorizer", "categorize"]
