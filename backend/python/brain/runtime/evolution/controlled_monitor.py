from __future__ import annotations

from typing import Any

from .controlled_evolution_models import ImprovementOpportunity


def evaluate_monitor_and_rollback(
    *,
    pending_monitor: dict[str, Any] | None,
    opportunities: list[ImprovementOpportunity],
) -> tuple[str, bool, str | None]:
    """
    Returns (monitor_status, rollback_recommended, rollback_proposal_id).
    If the same opportunity category reappears after a monitored apply, recommend rollback.
    """
    if not pending_monitor or not isinstance(pending_monitor, dict):
        return "idle", False, None
    cat = str(pending_monitor.get("opportunity_category", "") or "").strip()
    prev_prop = str(pending_monitor.get("proposal_id", "") or "").strip()
    if not cat or not opportunities:
        return "watching", False, None
    for opp in opportunities:
        if opp.category == cat:
            return "regression_signal", True, prev_prop or None
    return "stable", False, None


def apply_rollback_if_recommended(
    *,
    rollback_recommended: bool,
    proposal_id: str | None,
    store: Any,
) -> bool:
    if not rollback_recommended or not proposal_id:
        return False
    return bool(store.rollback_last(proposal_id=proposal_id))
