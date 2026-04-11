from __future__ import annotations

from datetime import datetime, timedelta, timezone

from .models import LearningPolicy, PatternRecord, StrategyRanking, parse_iso_timestamp


class StrategyRanker:
    def rank(self, *, records: list[PatternRecord], policy: LearningPolicy) -> list[StrategyRanking]:
        if not policy.allow_strategy_ranking:
            return []
        stale_cutoff = datetime.now(timezone.utc) - timedelta(days=policy.stale_pattern_days)
        rankings: list[StrategyRanking] = []
        for record in records:
            if record.total_count < policy.min_pattern_samples:
                continue
            last_seen = parse_iso_timestamp(record.last_seen)
            if last_seen is not None and last_seen < stale_cutoff:
                continue
            confidence = min(0.95, 0.45 + (record.total_count / (policy.min_pattern_samples * 10)))
            rankings.append(
                StrategyRanking.build(
                    strategy_key=record.pattern_key,
                    category=record.category,
                    score=record.success_ratio,
                    confidence=confidence,
                    evidence_count=record.total_count,
                    recommendation=f"Prefer pattern {record.pattern_key} based on {record.total_count} observed outcomes.",
                    metadata=dict(record.metadata),
                )
            )
        rankings.sort(key=lambda item: (item.score, item.confidence, item.evidence_count), reverse=True)
        return rankings
