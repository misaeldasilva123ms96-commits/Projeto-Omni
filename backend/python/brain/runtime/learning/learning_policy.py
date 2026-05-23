from __future__ import annotations

import os

from .models import LearningPolicy


class DeterministicLearningPolicy:
    @staticmethod
    def from_env() -> LearningPolicy:
        return LearningPolicy(
            enabled=str(os.getenv("OMINI_LEARNING_ENABLED", "true")).strip().lower() != "false",
            min_pattern_samples=max(1, int(os.getenv("OMINI_LEARNING_MIN_PATTERN_SAMPLES", "3") or "3")),
            max_signal_weight=min(1.0, max(0.0, float(os.getenv("OMINI_LEARNING_MAX_SIGNAL_WEIGHT", "0.30") or "0.30"))),
            allow_policy_hints=str(os.getenv("OMINI_LEARNING_ALLOW_POLICY_HINTS", "true")).strip().lower() != "false",
            allow_strategy_ranking=str(os.getenv("OMINI_LEARNING_ALLOW_STRATEGY_RANKING", "true")).strip().lower() != "false",
            stale_pattern_days=max(1, int(os.getenv("OMINI_LEARNING_STALE_PATTERN_DAYS", "30") or "30")),
        )
