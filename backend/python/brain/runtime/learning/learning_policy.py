from __future__ import annotations

from brain.env import read_env
from .models import LearningPolicy


class DeterministicLearningPolicy:
    @staticmethod
    def from_env() -> LearningPolicy:
        return LearningPolicy(
            enabled=read_env("OMNI_LEARNING_ENABLED", "true").lower() != "false",
            min_pattern_samples=max(1, int(read_env("OMNI_LEARNING_MIN_PATTERN_SAMPLES", "3") or "3")),
            max_signal_weight=min(1.0, max(0.0, float(read_env("OMNI_LEARNING_MAX_SIGNAL_WEIGHT", "0.30") or "0.30"))),
            allow_policy_hints=read_env("OMNI_LEARNING_ALLOW_POLICY_HINTS", "true").lower() != "false",
            allow_strategy_ranking=read_env("OMNI_LEARNING_ALLOW_STRATEGY_RANKING", "true").lower() != "false",
            stale_pattern_days=max(1, int(read_env("OMNI_LEARNING_STALE_PATTERN_DAYS", "30") or "30")),
        )
