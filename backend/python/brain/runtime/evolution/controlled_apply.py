from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .controlled_evolution_models import GovernedProposal

_DEFAULT_TUNING: dict[str, Any] = {
    "decomposition_max_subtasks": 6,
    "performance_max_cache_entries": 48,
    "strategy_risk_bias": 0.0,
    "coordination_issue_budget": 2,
    "observability_tail_lines": 96,
    "version": 0,
    "apply_history": [],
    "pending_monitor": None,
}


class Phase39TuningStore:
    """Bounded, reversible tuning persisted under governed runtime logs (not arbitrary code)."""

    def __init__(self, root: Path) -> None:
        self.path = root / ".logs" / "fusion-runtime" / "evolution" / "phase39_tuning.json"

    def read(self) -> dict[str, Any]:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return dict(_DEFAULT_TUNING)
        if not isinstance(raw, dict):
            return dict(_DEFAULT_TUNING)
        merged = dict(_DEFAULT_TUNING)
        merged.update({k: raw[k] for k in _DEFAULT_TUNING if k in raw})
        if isinstance(raw.get("apply_history"), list):
            merged["apply_history"] = raw["apply_history"][-48:]
        merged["pending_monitor"] = raw.get("pending_monitor")
        return merged

    def write(self, data: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self.path)

    def apply_proposal(self, proposal: GovernedProposal) -> dict[str, Any]:
        """Apply validated proposal; returns rollback snapshot for trace."""
        state = self.read()
        key = str(proposal.payload.get("key", "") or "")
        old = state.get(key)
        new = proposal.payload.get("new_value")
        state[key] = new
        state["version"] = int(state.get("version", 0) or 0) + 1
        hist = list(state.get("apply_history") or [])
        hist.append(
            {
                "proposal_id": proposal.proposal_id,
                "opportunity_id": proposal.opportunity_id,
                "key": key,
                "old": old,
                "new": new,
            }
        )
        state["apply_history"] = hist[-48:]
        state["pending_monitor"] = {
            "proposal_id": proposal.proposal_id,
            "proposal_type": proposal.proposal_type,
            "opportunity_id": proposal.opportunity_id,
            "opportunity_category": str(proposal.payload.get("opportunity_category", "") or ""),
        }
        self.write(state)
        return {"key": key, "old": old, "new": new}

    def clear_pending_monitor(self) -> None:
        state = self.read()
        state["pending_monitor"] = None
        self.write(state)

    def rollback_last(self, *, proposal_id: str) -> bool:
        state = self.read()
        hist = list(state.get("apply_history") or [])
        for i in range(len(hist) - 1, -1, -1):
            entry = hist[i]
            if str(entry.get("proposal_id", "")) != proposal_id:
                continue
            key = str(entry.get("key", "") or "")
            old = entry.get("old")
            if key:
                state[key] = old
            hist.pop(i)
            state["apply_history"] = hist
            state["pending_monitor"] = None
            state["version"] = int(state.get("version", 0) or 0) + 1
            self.write(state)
            return True
        return False
