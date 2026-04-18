from __future__ import annotations

import json
import math
import uuid
from copy import deepcopy
from pathlib import Path
from typing import Any

from brain.runtime.evolution.controlled_evolution_models import GovernedProposal


def _lerp_value(baseline: float, target: float, t: float) -> float:
    return baseline + (target - baseline) * t


def _coerce_numeric(val: Any, *, as_int: bool) -> float:
    v = float(val)
    if as_int:
        return float(int(round(v)))
    return float(v)


def build_scaled_proposal(
    *,
    base: GovernedProposal,
    baseline_value: Any,
    target_value: Any,
    fraction: float,
    suffix: str,
) -> GovernedProposal:
    """Bounded intermediate rollout value between on-disk baseline and CE target."""
    key = str(base.payload.get("key", "") or "")
    as_int = key != "strategy_risk_bias"
    if baseline_value is None:
        baseline_value = base.payload.get("previous_value")
    if baseline_value is None:
        baseline_value = 6 if as_int else 0.0
    b = _coerce_numeric(baseline_value, as_int=as_int)
    t = _coerce_numeric(target_value, as_int=as_int)
    mid = _lerp_value(b, t, min(1.0, max(0.0, fraction)))
    if as_int:
        # Half-up avoids Python banker's round (e.g. 6.5 -> 6) which would stall canary rollouts.
        mid_v = int(math.floor(mid + 0.5))
    else:
        mid_v = float(mid)
    payload = deepcopy(dict(base.payload))
    payload["new_value"] = mid_v
    payload["rollout_fraction"] = fraction
    payload["rollout_suffix"] = suffix
    return GovernedProposal(
        proposal_id=f"{base.proposal_id}{suffix}",
        opportunity_id=base.opportunity_id,
        proposal_type=base.proposal_type,
        scope=base.scope,
        target_layer=base.target_layer,
        change_summary=f"{base.change_summary} [rollout {suffix} frac={fraction}]",
        risk_class=base.risk_class,
        validation_requirements=list(base.validation_requirements),
        approval_state="rollout_scaled",
        apply_status="pending",
        monitor_status="pending",
        rollback_status="rollback_ready",
        payload=payload,
    )


_DEFAULT_STATE: dict[str, Any] = {
    "version": 0,
    "cycle_id": None,
    "session_id": None,
    "cycle_fingerprint": None,
    "stage": "idle",
    "baseline_duration_ms": None,
    "baseline_tuning_value": None,
    "applied_proposal_ids": [],
    "target_value": None,
    "last_applied_value": None,
    "tuning_key": None,
}


class ImprovementRolloutStore:
    """Persists one active rollout cycle (bounded, auditable)."""

    def __init__(self, root: Path) -> None:
        self.path = root / ".logs" / "fusion-runtime" / "improvement" / "phase40_rollout.json"

    def read(self) -> dict[str, Any]:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return dict(_DEFAULT_STATE)
        if not isinstance(raw, dict):
            return dict(_DEFAULT_STATE)
        merged = dict(_DEFAULT_STATE)
        merged.update({k: raw[k] for k in _DEFAULT_STATE if k in raw})
        if isinstance(raw.get("applied_proposal_ids"), list):
            merged["applied_proposal_ids"] = [str(x) for x in raw["applied_proposal_ids"]][-16:]
        return merged

    def write(self, data: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self.path)

    def reset_cycle(
        self,
        *,
        session_id: str,
        cycle_fingerprint: str,
        baseline_duration_ms: float,
        baseline_tuning_value: Any,
        tuning_key: str,
        target_value: Any,
    ) -> dict[str, Any]:
        st = dict(_DEFAULT_STATE)
        st["version"] = int(self.read().get("version", 0) or 0) + 1
        st["cycle_id"] = f"p40-{uuid.uuid4().hex[:16]}"
        st["session_id"] = session_id
        st["cycle_fingerprint"] = cycle_fingerprint
        st["stage"] = "awaiting_canary"
        st["baseline_duration_ms"] = float(baseline_duration_ms)
        st["baseline_tuning_value"] = baseline_tuning_value
        st["tuning_key"] = tuning_key
        st["target_value"] = target_value
        st["applied_proposal_ids"] = []
        self.write(st)
        return st

    def mark_stage(self, stage: str) -> None:
        st = self.read()
        st["stage"] = stage
        st["version"] = int(st.get("version", 0) or 0) + 1
        self.write(st)

    def record_apply(self, proposal_id: str, *, target_value: Any, tuning_key: str) -> None:
        st = self.read()
        ids = list(st.get("applied_proposal_ids") or [])
        ids.append(str(proposal_id))
        st["applied_proposal_ids"] = ids[-16:]
        # Preserve rollout target_value from reset_cycle (final CE cap); do not clobber with intermediates.
        st.setdefault("target_value", target_value)
        st["last_applied_value"] = target_value
        st["tuning_key"] = tuning_key
        st["version"] = int(st.get("version", 0) or 0) + 1
        self.write(st)

    def clear_active(self) -> None:
        self.write(dict(_DEFAULT_STATE))
