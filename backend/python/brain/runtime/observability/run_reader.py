from pathlib import Path
from typing import Any

from brain.runtime.control import RunRegistry
from brain.runtime.control.run_identity import normalize_run_id
from brain.runtime.evolution import EvolutionService
from brain.runtime.control.governance_read_model import build_operational_governance_snapshot
from brain.runtime.control.program_closure import (
    empty_operational_governance_fallback,
    empty_resolution_summary_fallback,
)


def read_active_runs(root: Path) -> list[dict[str, Any]]:
    try:
        registry = RunRegistry(root)
        return [item.as_dict() for item in registry.get_active()]
    except Exception:
        return []


def read_run(root: Path, run_id: str) -> dict[str, Any] | None:
    raw = normalize_run_id(str(run_id or ""))
    if not raw:
        return None
    try:
        registry = RunRegistry(root)
        record = registry.get(raw)
    except Exception:
        return None
    return record.as_dict() if record is not None else None


def read_runs(root: Path, *, limit: int = 50) -> list[dict[str, Any]]:
    try:
        registry = RunRegistry(root)
        return [item.as_dict() for item in registry.get_all(limit=max(1, int(limit or 50)))]
    except Exception:
        return []


def read_resolution_summary(root: Path) -> dict[str, Any]:
    try:
        registry = RunRegistry(root)
        return registry.get_resolution_summary()
    except Exception:
        return empty_resolution_summary_fallback()


def read_runs_waiting_operator(root: Path) -> list[dict[str, Any]]:
    try:
        registry = RunRegistry(root)
        return [item.as_dict() for item in registry.get_runs_waiting_operator()]
    except Exception:
        return []


def read_runs_with_rollback(root: Path) -> list[dict[str, Any]]:
    try:
        registry = RunRegistry(root)
        return [item.as_dict() for item in registry.get_runs_with_rollback()]
    except Exception:
        return []


def read_recent_resolution_events(root: Path, *, limit: int = 25) -> list[dict[str, Any]]:
    try:
        registry = RunRegistry(root)
        return registry.recent_resolution_events(limit=max(1, int(limit or 25)))
    except Exception:
        return []


def read_recent_governance_timeline_events(root: Path, *, limit: int = 25) -> list[dict[str, Any]]:
    try:
        registry = RunRegistry(root)
        return registry.recent_governance_timeline_events(limit=max(1, int(limit or 25)))
    except Exception:
        return []


def read_latest_governance_event_by_run(root: Path) -> dict[str, dict[str, Any]]:
    try:
        registry = RunRegistry(root)
        return registry.latest_governance_event_by_run()
    except Exception:
        return {}


def read_operational_governance(root: Path, *, timeline_limit: int = 25) -> dict[str, Any]:
    try:
        registry = RunRegistry(root)
        return build_operational_governance_snapshot(registry, timeline_limit=timeline_limit)
    except Exception:
        return empty_operational_governance_fallback(summary=read_resolution_summary(root))


def read_evolution_summary(root: Path, *, recent_limit: int = 10) -> dict[str, Any]:
    try:
        service = EvolutionService(root)
        return service.summary(recent_limit=max(1, int(recent_limit or 10)))
    except Exception:
        return {
            "governed": True,
            "total_proposals": 0,
            "status_counts": {
                "proposed": 0,
                "under_review": 0,
                "approved": 0,
                "rejected": 0,
                "deferred": 0,
            },
            "recent_proposals": [],
            "validation_counts": {
                "valid": 0,
                "invalid": 0,
                "risky": 0,
                "inconclusive": 0,
            },
            "proposals_with_recent_validation": [],
            "latest_validation_by_proposal": {},
            "application_counts": {
                "pending": 0,
                "applying": 0,
                "applied": 0,
                "failed": 0,
                "rolled_back": 0,
            },
            "proposals_with_recent_application": [],
            "latest_application_by_proposal": {},
            "rollback_counts": {
                "executed": 0,
                "available": 0,
            },
            "lifecycle": {
                "allowed_statuses": ["proposed", "under_review", "approved", "rejected", "deferred"],
                "terminal_statuses": ["approved", "rejected", "deferred"],
                "auto_apply_enabled": False,
            },
        }


def read_evolution_proposal(root: Path, proposal_id: str) -> dict[str, Any] | None:
    proposal_key = str(proposal_id or "").strip()
    if not proposal_key:
        return None
    try:
        service = EvolutionService(root)
        proposal = service.get_proposal(proposal_key)
        return proposal.as_dict() if proposal is not None else None
    except Exception:
        return None
