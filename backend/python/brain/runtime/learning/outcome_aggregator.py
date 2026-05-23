from __future__ import annotations

from collections import defaultdict

from .models import PatternRecord


class OutcomeAggregator:
    def aggregate(self, records: list[PatternRecord]) -> dict[str, dict[str, float | int]]:
        grouped_success: dict[str, int] = defaultdict(int)
        grouped_failure: dict[str, int] = defaultdict(int)
        grouped_total: dict[str, int] = defaultdict(int)
        for record in records:
            grouped_success[record.category] += record.success_count
            grouped_failure[record.category] += record.failure_count
            grouped_total[record.category] += record.total_count
        summary: dict[str, dict[str, float | int]] = {}
        for category, total in grouped_total.items():
            success = grouped_success[category]
            failure = grouped_failure[category]
            summary[category] = {
                "success_count": success,
                "failure_count": failure,
                "total_count": total,
                "success_rate": (success / total) if total else 0.0,
            }
        return summary
