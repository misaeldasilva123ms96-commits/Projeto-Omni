from __future__ import annotations

import os

from .models import ContinuationPolicy


class DeterministicContinuationPolicy:
    @staticmethod
    def from_env() -> ContinuationPolicy:
        return ContinuationPolicy(
            max_retries_per_step=max(0, int(os.getenv("OMINI_CONTINUATION_MAX_RETRIES_PER_STEP", "2") or "2")),
            allow_replan=str(os.getenv("OMINI_CONTINUATION_ALLOW_REPLAN", "true")).lower() != "false",
            allow_auto_pause=str(os.getenv("OMINI_CONTINUATION_ALLOW_AUTO_PAUSE", "true")).lower() != "false",
            allow_auto_escalate=str(os.getenv("OMINI_CONTINUATION_ALLOW_AUTO_ESCALATE", "true")).lower() != "false",
            max_replans_per_plan=max(0, int(os.getenv("OMINI_CONTINUATION_MAX_REPLANS_PER_PLAN", "1") or "1")),
        )

    @staticmethod
    def retry_allowed(*, retry_count: int, policy: ContinuationPolicy) -> bool:
        return retry_count < policy.max_retries_per_step

    @staticmethod
    def replan_allowed(*, replan_count: int, policy: ContinuationPolicy) -> bool:
        return policy.allow_replan and replan_count < policy.max_replans_per_plan
