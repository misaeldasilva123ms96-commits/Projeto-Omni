from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
from typing import Any


class PatternAnalyzer:
    def analyze(
        self,
        *,
        evaluations: list[dict[str, Any]],
        learning: dict[str, Any],
        sessions: list[dict[str, Any]],
        phase41_performance_sketch: dict[str, Any] | list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        weak_patterns: list[dict[str, Any]] = []
        strong_patterns: list[dict[str, Any]] = []
        recommended_adjustments: list[dict[str, Any]] = []

        capability_usage = learning.get("capability_usage", {})
        if not isinstance(capability_usage, dict):
            capability_usage = {}

        pattern_scores: dict[str, list[float]] = defaultdict(list)
        hourly_scores: dict[str, list[float]] = defaultdict(list)
        flag_counter: Counter[str] = Counter()

        for evaluation in evaluations:
            session_id = str(evaluation.get("session_id", ""))
            overall = float(evaluation.get("overall", 0.0))
            flags = evaluation.get("flags", [])
            if isinstance(flags, list):
                flag_counter.update(str(flag) for flag in flags)

            matched_session = next((item for item in sessions if str(item.get("session_id", "")) == session_id), {})
            swarm = matched_session.get("swarm", {})
            intent = str(swarm.get("intent", "unknown")) if isinstance(swarm, dict) else "unknown"
            pattern_scores[intent].append(overall)

            timestamp = str(evaluation.get("timestamp", ""))
            if timestamp:
                try:
                    hour = datetime.fromisoformat(timestamp.replace("Z", "+00:00")).strftime("%H")
                    hourly_scores[hour].append(overall)
                except Exception:
                    pass

        for pattern, scores in pattern_scores.items():
            average = round(sum(scores) / max(1, len(scores)), 3)
            record = {"pattern": pattern, "average_score": average, "samples": len(scores)}
            if average < 0.62:
                weak_patterns.append(record)
                recommended_adjustments.append(
                    {
                        "target": pattern,
                        "action": "raise_priority",
                        "reason": f"Pattern '{pattern}' has low average score {average}.",
                    }
                )
            else:
                strong_patterns.append(record)

        all_capabilities = {"generate_idea", "give_advice", "create_plan"}
        underused_capabilities = sorted(
            capability
            for capability in all_capabilities
            if int(capability_usage.get(capability, 0)) <= 1
        )
        for capability in underused_capabilities:
            recommended_adjustments.append(
                {
                    "target": capability,
                    "action": "probe_usage",
                    "reason": f"Capability '{capability}' is underused in recent sessions.",
                }
            )

        best_hours = sorted(
            (
                {"hour": hour, "average_score": round(sum(scores) / max(1, len(scores)), 3), "samples": len(scores)}
                for hour, scores in hourly_scores.items()
            ),
            key=lambda item: item["average_score"],
            reverse=True,
        )[:3]

        out: dict[str, Any] = {
            "weak_patterns": sorted(weak_patterns, key=lambda item: item["average_score"]),
            "strong_patterns": sorted(strong_patterns, key=lambda item: item["average_score"], reverse=True),
            "underused_capabilities": underused_capabilities,
            "recommended_adjustments": recommended_adjustments,
            "frequent_flags": flag_counter.most_common(5),
            "best_hours": best_hours,
        }
        if phase41_performance_sketch is not None:
            out["phase41_performance_sketch"] = phase41_performance_sketch
        return out
