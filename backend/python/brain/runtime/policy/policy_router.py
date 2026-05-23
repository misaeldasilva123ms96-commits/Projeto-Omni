from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from config.provider_registry import get_available_providers

from brain.runtime.policy.performance_store import PerformanceStore
from brain.runtime.policy.policy_models import PolicyHint


class PolicyRouter:
    """Phase 41.4 — bounded policy hints; shadow by default."""

    def __init__(self, root: Path, *, performance_store: PerformanceStore | None = None) -> None:
        self._root = root
        self._performance = performance_store or PerformanceStore(root)

    def compute_hint(
        self,
        *,
        session_id: str,
        normalized_intent: str,
        baseline_provider: str | None,
        strategy_mode: str | None,
        recent_experience_rows: list[dict[str, Any]],
    ) -> PolicyHint:
        reasons: list[str] = []
        available = set(get_available_providers())
        base = (baseline_provider or "").strip().lower() or None
        if base and base not in available:
            base = next(iter(available), None) if available else None

        recommended_provider = base
        conf = 0.35

        top = self._performance.top_buckets(limit=6)
        best = None
        best_score = -1.0
        for row in top:
            m = row.get("metrics") if isinstance(row.get("metrics"), dict) else {}
            att = int(m.get("attempts", 0) or 0)
            if att < 3:
                continue
            succ = int(m.get("successes", 0) or 0)
            fb = int(m.get("fallbacks", 0) or 0)
            score = succ / max(1, att) - 0.15 * (fb / max(1, att))
            prov = str(row.get("provider", "") or "").strip().lower()
            if prov and prov in available and score > best_score:
                best_score = score
                best = prov
        if best and best_score >= 0.55 and best != base:
            recommended_provider = best
            conf = min(0.85, 0.45 + best_score * 0.35)
            reasons.append("performance_history_provider")

        if recent_experience_rows:
            fails = sum(1 for r in recent_experience_rows[:5] if not r.get("success_outcome"))
            if fails >= 2 and len(available) > 1:
                alt = next((p for p in available if p != recommended_provider), None)
                if alt:
                    recommended_provider = alt
                    conf = min(0.75, conf + 0.1)
                    reasons.append("recent_session_failures_switch")

        rec_strategy = (strategy_mode or "").strip() or None
        if recent_experience_rows and rec_strategy:
            low_q = [
                float(r["response_quality_score"])
                for r in recent_experience_rows[:3]
                if isinstance(r.get("response_quality_score"), (int, float))
            ]
            if low_q and sum(low_q) / len(low_q) < 0.45:
                reasons.append("low_quality_recent")
                conf = min(0.8, conf + 0.05)

        active = str(os.getenv("OMINI_PHASE41_POLICY_ACTIVE", "")).strip().lower() in ("1", "true", "yes")
        shadow = not active
        if shadow:
            reasons.append("shadow_mode_default")

        if recommended_provider and recommended_provider not in available:
            recommended_provider = base
            reasons.append("invalid_recommendation_fallback")

        return PolicyHint(
            recommended_provider=recommended_provider,
            recommended_strategy=rec_strategy,
            recommended_tool_profile=None,
            confidence=float(round(conf, 4)),
            policy_reason_codes=reasons or ["no_signal"],
            baseline_provider=base,
            shadow_only=shadow,
        )

    def hint_to_env_json(self, hint: PolicyHint) -> str | None:
        if hint.shadow_only:
            return None
        try:
            return json.dumps(hint.as_dict(), ensure_ascii=False)
        except (TypeError, ValueError):
            return None
