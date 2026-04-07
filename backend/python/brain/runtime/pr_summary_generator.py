from __future__ import annotations

from typing import Any


def build_pr_summary(
    *,
    message: str,
    milestone_state: dict[str, Any] | None,
    patch_sets: list[dict[str, Any]] | None,
    verification_summary: dict[str, Any] | None,
    repository_analysis: dict[str, Any] | None,
    impact_analysis: dict[str, Any] | None,
) -> dict[str, Any]:
    patch_sets = patch_sets or []
    affected_files = []
    for patch_set in patch_sets:
        affected_files.extend(patch_set.get("affected_files", []))
    affected_files = sorted(set(affected_files))
    verification_summary = verification_summary or {}
    merge_ready = bool(verification_summary.get("ok")) and not any(
        milestone.get("state") == "blocked" for milestone in (milestone_state or {}).get("milestones", [])
    )
    return {
        "title": f"Engineering update: {str(message or '').strip()[:72]}".strip(),
        "summary": "Generated from executed runtime work and verification artifacts.",
        "files_changed": affected_files,
        "why": {
            "message": message,
            "dominant_language": (repository_analysis or {}).get("language_profile", {}).get("dominant_language"),
            "impact_summary": (impact_analysis or {}).get("integration_risk_summary", {}),
        },
        "verification": verification_summary,
        "known_risks": (impact_analysis or {}).get("integration_risk_summary", {}).get("flags", []),
        "merge_readiness": {
            "status": "ready" if merge_ready else "needs-review",
            "reason": "verification_passed" if merge_ready else "verification_or_milestones_incomplete",
        },
    }
