from __future__ import annotations

from typing import Any

from .evolution_application import EvolutionApplicationStatus
from .evolution_models import EvolutionProposalStatus
from .evolution_validation import EvolutionValidationOutcome

CONTROLLED_SELF_EVOLUTION_PROGRAM = "30.17-30.20"
CONTROLLED_SELF_EVOLUTION_PHASE = "30.20"


def _proposal_counts_template() -> dict[str, int]:
    return {status.value: 0 for status in EvolutionProposalStatus}


def _validation_counts_template() -> dict[str, int]:
    return {status.value: 0 for status in EvolutionValidationOutcome}


def _application_counts_template() -> dict[str, int]:
    return {status.value: 0 for status in EvolutionApplicationStatus}


def empty_governed_evolution_summary() -> dict[str, Any]:
    """Canonical empty payload for governed evolution operational reads."""
    proposal_counts = _proposal_counts_template()
    return {
        "governed": True,
        "program": CONTROLLED_SELF_EVOLUTION_PROGRAM,
        "program_phase": CONTROLLED_SELF_EVOLUTION_PHASE,
        "total_proposals": 0,
        # Backward-compatible key preserved.
        "status_counts": dict(proposal_counts),
        # Preferred key for closure readability.
        "proposal_counts": dict(proposal_counts),
        "recent_proposals": [],
        "validation_counts": _validation_counts_template(),
        "proposals_with_recent_validation": [],
        "latest_validation_by_proposal": {},
        "application_counts": _application_counts_template(),
        "proposals_with_recent_application": [],
        "latest_application_by_proposal": {},
        "rollback_counts": {
            "executed": 0,
            "available": 0,
        },
        "lifecycle": {
            "allowed_statuses": [status.value for status in EvolutionProposalStatus],
            "terminal_statuses": [
                EvolutionProposalStatus.APPROVED.value,
                EvolutionProposalStatus.REJECTED.value,
                EvolutionProposalStatus.DEFERRED.value,
            ],
            "auto_apply_enabled": False,
        },
    }


def normalize_governed_evolution_summary(payload: dict[str, Any] | None) -> dict[str, Any]:
    """Normalize potentially partial payloads to the closure-stable shape."""
    base = empty_governed_evolution_summary()
    data = dict(payload or {})
    normalized = dict(base)
    normalized.update(data)

    status_counts = dict(normalized.get("status_counts", {}) or {})
    proposal_counts = dict(normalized.get("proposal_counts", {}) or {})
    for key, default in base["proposal_counts"].items():
        status_counts[key] = int(status_counts.get(key, default) or 0)
        proposal_counts[key] = int(proposal_counts.get(key, status_counts[key]) or 0)
    normalized["status_counts"] = status_counts
    normalized["proposal_counts"] = proposal_counts

    validation_counts = dict(normalized.get("validation_counts", {}) or {})
    for key, default in base["validation_counts"].items():
        validation_counts[key] = int(validation_counts.get(key, default) or 0)
    normalized["validation_counts"] = validation_counts

    application_counts = dict(normalized.get("application_counts", {}) or {})
    for key, default in base["application_counts"].items():
        application_counts[key] = int(application_counts.get(key, default) or 0)
    normalized["application_counts"] = application_counts

    rollback_counts = dict(normalized.get("rollback_counts", {}) or {})
    rollback_counts["executed"] = int(rollback_counts.get("executed", 0) or 0)
    rollback_counts["available"] = int(rollback_counts.get("available", 0) or 0)
    normalized["rollback_counts"] = rollback_counts

    normalized["recent_proposals"] = [dict(item) for item in (normalized.get("recent_proposals", []) or []) if isinstance(item, dict)]
    normalized["proposals_with_recent_validation"] = [
        dict(item) for item in (normalized.get("proposals_with_recent_validation", []) or []) if isinstance(item, dict)
    ]
    normalized["proposals_with_recent_application"] = [
        dict(item) for item in (normalized.get("proposals_with_recent_application", []) or []) if isinstance(item, dict)
    ]
    normalized["latest_validation_by_proposal"] = {
        str(k): dict(v)
        for k, v in dict(normalized.get("latest_validation_by_proposal", {}) or {}).items()
        if isinstance(v, dict)
    }
    normalized["latest_application_by_proposal"] = {
        str(k): dict(v)
        for k, v in dict(normalized.get("latest_application_by_proposal", {}) or {}).items()
        if isinstance(v, dict)
    }
    lifecycle = dict(normalized.get("lifecycle", {}) or {})
    lifecycle.setdefault("allowed_statuses", base["lifecycle"]["allowed_statuses"])
    lifecycle.setdefault("terminal_statuses", base["lifecycle"]["terminal_statuses"])
    lifecycle["auto_apply_enabled"] = bool(lifecycle.get("auto_apply_enabled", False))
    normalized["lifecycle"] = lifecycle
    normalized["governed"] = True
    normalized["program"] = CONTROLLED_SELF_EVOLUTION_PROGRAM
    normalized["program_phase"] = CONTROLLED_SELF_EVOLUTION_PHASE
    normalized["total_proposals"] = int(normalized.get("total_proposals", 0) or 0)
    return normalized


def validate_governed_evolution_summary_shape(payload: dict[str, Any]) -> None:
    """Raise ``ValueError`` when required closure keys are missing."""
    required = (
        "governed",
        "total_proposals",
        "proposal_counts",
        "validation_counts",
        "application_counts",
        "rollback_counts",
        "latest_validation_by_proposal",
        "latest_application_by_proposal",
        "lifecycle",
    )
    missing = [key for key in required if key not in payload]
    if missing:
        raise ValueError(f"invalid governed_evolution summary: missing keys {missing}")
