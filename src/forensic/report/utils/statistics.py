from collections import Counter
from datetime import date
from typing import Any


class StatisticsCalculator:
    @staticmethod
    def count_by_category(items: list[Any], key: str = "category") -> dict[str, int]:
        counter = Counter()
        for item in items:
            category = getattr(item, key, "UNKNOWN")
            counter[str(category)] += 1
        return dict(counter)

    @staticmethod
    def calculate_percentages(counts: dict[str, int]) -> dict[str, float]:
        total = sum(counts.values())
        if total == 0:
            return dict.fromkeys(counts, 0.0)
        return {k: (v / total) * 100 for k, v in counts.items()}

    @staticmethod
    def calculate_date_range(items: list[Any], date_key: str = "timestamp") -> tuple[date | None, date | None]:
        dates = []
        for item in items:
            timestamp = getattr(item, date_key, None)
            if timestamp:
                if hasattr(timestamp, "date"):
                    dates.append(timestamp.date())
                else:
                    dates.append(timestamp)
        if not dates:
            return (None, None)
        return (min(dates), max(dates))

    @staticmethod
    def calculate_speaker_similarity(speakers1: list[str], speakers2: list[str]) -> dict[str, Any]:
        set1, set2 = set(speakers1), set(speakers2)
        intersection = set1 & set2
        union = set1 | set2
        jaccard = len(intersection) / len(union) if union else 0
        return {"jaccard": jaccard, "common": sorted(intersection),
                "unique_to_first": sorted(set1 - set2), "unique_to_second": sorted(set2 - set1)}

class ReportStatistics:
    def analyze_evidence(self, evidence: list[Any]) -> dict[str, Any]:
        calc = StatisticsCalculator()
        return {"total": len(evidence), "by_category": calc.count_by_category(evidence, "category")}

    def analyze_speakers(self, segments: list[Any]) -> dict[str, Any]:
        calc = StatisticsCalculator()
        return {"total_segments": len(segments), "segment_counts": calc.count_by_category(segments, "speaker")}
