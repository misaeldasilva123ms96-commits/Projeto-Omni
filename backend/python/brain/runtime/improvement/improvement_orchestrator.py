from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Any

from brain.runtime.evolution.controlled_apply import Phase39TuningStore
from brain.runtime.evolution.controlled_evolution_models import GovernedProposal, governed_proposal_from_dict
from brain.runtime.evolution.controlled_validation import validate_governed_proposal

from .approval_gate import evaluate_approval
from .improvement_models import ImprovementCycle, SelfImprovingSystemTrace
from .improvement_pipeline import monitoring_snapshot, run_simulation_and_approval
from .rollout_manager import ImprovementRolloutStore, build_scaled_proposal


def _truthy(name: str) -> bool:
    return str(os.getenv(name, "")).strip().lower() in ("1", "true", "yes")


def _stage_name(st: dict[str, Any]) -> str:
    v = st.get("stage")
    if v is None or v == "":
        return "idle"
    return str(v)


class ImprovementOrchestrator:
    """
    Phase 40 — continuous governed improvement: simulate → approve → gradual rollout → monitor → rollback.

    Applies only through Phase39TuningStore on allow-listed proposals; never mutates code.
    """

    def __init__(self, root: Path | str) -> None:
        self.root = Path(root)
        self.store = Phase39TuningStore(self.root)
        self.rollout = ImprovementRolloutStore(self.root)

    def run_cycle(
        self,
        *,
        session_id: str,
        ce_trace: dict[str, Any],
        evidence: dict[str, Any],
    ) -> dict[str, Any]:
        trace_id = f"p40-{uuid.uuid4().hex[:18]}"
        if _truthy("OMINI_PHASE40_DISABLE"):
            return SelfImprovingSystemTrace(
                trace_id=trace_id,
                session_id=session_id,
                disabled=True,
                idle=True,
                cycle=None,
                simulation_outcome={},
                approval_decision="disabled",
                rollout_stage="disabled",
                monitoring_result={},
                rollback_status="n_a",
                degraded=False,
                error="",
            ).as_dict()

        if not _truthy("OMINI_PHASE40_ENABLE"):
            return SelfImprovingSystemTrace(
                trace_id=trace_id,
                session_id=session_id,
                disabled=False,
                idle=True,
                cycle=None,
                simulation_outcome={},
                approval_decision="idle",
                rollout_stage="idle",
                monitoring_result={},
                rollback_status="n_a",
                degraded=False,
                error="",
            ).as_dict()

        degraded = False
        err = ""
        tuning = self.store.read()
        rstate = self.rollout.read()
        proposals_raw = list(ce_trace.get("proposals") or [])
        apply40 = _truthy("OMINI_PHASE40_APPLY")

        # Monitor / rollback path for in-flight rollout without fresh CE proposal
        if not proposals_raw and _stage_name(rstate) not in (
            "idle",
            "complete",
            "rolled_back",
            "rolled_back_partial",
        ):
            mon = monitoring_snapshot(rollout_state=rstate, evidence=evidence)
            rb_status = "none"
            if mon.get("regression") and list(rstate.get("applied_proposal_ids") or []):
                last_id = str(rstate["applied_proposal_ids"][-1])
                if self.store.rollback_last(proposal_id=last_id):
                    rb_status = "applied_partial"
                    self.rollout.mark_stage("rolled_back_partial")
                else:
                    rb_status = "failed"
                    degraded = True
            tr = SelfImprovingSystemTrace(
                trace_id=trace_id,
                session_id=session_id,
                disabled=False,
                idle=False,
                cycle={"id": str(rstate.get("cycle_id") or ""), "stage": str(rstate.get("stage") or "")},
                simulation_outcome={"note": "monitor_only_no_new_ce_proposal"},
                approval_decision="n_a",
                rollout_stage=str(rstate.get("stage") or ""),
                monitoring_result=dict(mon),
                rollback_status=rb_status,
                degraded=degraded,
                error=err,
            )
            return tr.as_dict()

        if not proposals_raw:
            return SelfImprovingSystemTrace(
                trace_id=trace_id,
                session_id=session_id,
                disabled=False,
                idle=True,
                cycle=None,
                simulation_outcome={},
                approval_decision="idle",
                rollout_stage="idle",
                monitoring_result=monitoring_snapshot(rollout_state=rstate, evidence=evidence),
                rollback_status="none",
                degraded=False,
                error="",
            ).as_dict()

        base_prop = governed_proposal_from_dict(proposals_raw[0])
        sim, approval = run_simulation_and_approval(
            proposal=base_prop,
            current_tuning=tuning,
            evidence=evidence,
        )

        if approval.status in ("pending", "rejected"):
            cycle = ImprovementCycle(
                id=str(rstate.get("cycle_id") or ""),
                proposals=[base_prop.as_dict()],
                simulation_result=dict(sim),
                approval_status=approval.status,
                rollout_stage=str(rstate.get("stage") or "idle"),
                monitoring_state=monitoring_snapshot(rollout_state=rstate, evidence=evidence),
                rollback_available=False,
            )
            return SelfImprovingSystemTrace(
                trace_id=trace_id,
                session_id=session_id,
                disabled=False,
                idle=False,
                cycle=cycle.as_dict(),
                simulation_outcome=dict(sim),
                approval_decision=approval.status,
                rollout_stage=str(rstate.get("stage") or "idle"),
                monitoring_result=monitoring_snapshot(rollout_state=rstate, evidence=evidence),
                rollback_status="none",
                degraded=False,
                error="",
            ).as_dict()

        key = str(base_prop.payload.get("key", "") or "")
        target_val = base_prop.payload.get("new_value")
        fp = f"{base_prop.opportunity_id}:{key}:{target_val!r}"
        try:
            bd = float(evidence.get("duration_ms") or 0.0)
        except (TypeError, ValueError):
            bd = 0.0

        if str(rstate.get("stage") or "") == "complete" and rstate.get("cycle_fingerprint") == fp:
            return SelfImprovingSystemTrace(
                trace_id=trace_id,
                session_id=session_id,
                disabled=False,
                idle=True,
                cycle={"id": str(rstate.get("cycle_id") or ""), "stage": "complete", "cycle_fingerprint": fp},
                simulation_outcome=dict(sim),
                approval_decision=approval.status,
                rollout_stage="complete",
                monitoring_result=monitoring_snapshot(rollout_state=rstate, evidence=evidence),
                rollback_status="none",
                degraded=False,
                error="",
            ).as_dict()

        if rstate.get("cycle_fingerprint") != fp:
            rstate = self.rollout.reset_cycle(
                session_id=session_id,
                cycle_fingerprint=fp,
                baseline_duration_ms=bd,
                baseline_tuning_value=tuning.get(key),
                tuning_key=key,
                target_value=target_val,
            )

        mon_pre = monitoring_snapshot(rollout_state=rstate, evidence=evidence)
        stage = str(rstate.get("stage") or "idle")
        rollback_status = "none"

        if stage in ("canary_applied", "expanded_applied") and mon_pre.get("regression"):
            for pid in reversed(list(rstate.get("applied_proposal_ids") or [])):
                self.store.rollback_last(proposal_id=str(pid))
            rollback_status = "applied_chain"
            self.rollout.mark_stage("rolled_back")
            self.rollout.clear_active()
            cycle = ImprovementCycle(
                id=str(rstate.get("cycle_id") or ""),
                proposals=[base_prop.as_dict()],
                simulation_result=dict(sim),
                approval_status=approval.status,
                rollout_stage="rolled_back",
                monitoring_state=dict(mon_pre),
                rollback_available=True,
            )
            return SelfImprovingSystemTrace(
                trace_id=trace_id,
                session_id=session_id,
                disabled=False,
                idle=False,
                cycle=cycle.as_dict(),
                simulation_outcome=dict(sim),
                approval_decision=approval.status,
                rollout_stage="rolled_back",
                monitoring_result=dict(mon_pre),
                rollback_status=rollback_status,
                degraded=False,
                error="",
            ).as_dict()

        baseline_anchor = rstate.get("baseline_tuning_value")
        next_apply: GovernedProposal | None = None
        next_stage_after = stage

        if stage == "awaiting_canary" and apply40:
            next_apply = build_scaled_proposal(
                base=base_prop,
                baseline_value=baseline_anchor,
                target_value=rstate.get("target_value", target_val),
                fraction=0.25,
                suffix="-p40-canary",
            )
            next_stage_after = "canary_applied"
        elif stage == "canary_applied" and apply40:
            next_apply = build_scaled_proposal(
                base=base_prop,
                baseline_value=baseline_anchor,
                target_value=rstate.get("target_value", target_val),
                fraction=0.55,
                suffix="-p40-expanded",
            )
            next_stage_after = "expanded_applied"
        elif stage == "expanded_applied" and apply40:
            full_payload = dict(base_prop.payload)
            full_payload["new_value"] = rstate.get("target_value", target_val)
            next_apply = GovernedProposal(
                proposal_id=f"{base_prop.proposal_id}-p40-full",
                opportunity_id=base_prop.opportunity_id,
                proposal_type=base_prop.proposal_type,
                scope=base_prop.scope,
                target_layer=base_prop.target_layer,
                change_summary=base_prop.change_summary,
                risk_class=base_prop.risk_class,
                validation_requirements=list(base_prop.validation_requirements),
                approval_state="rollout_full",
                apply_status="pending",
                monitor_status="pending",
                rollback_status="rollback_ready",
                payload=full_payload,
            )
            next_stage_after = "complete"

        apply_status = "skipped_policy"
        if next_apply is not None:
            vr = validate_governed_proposal(next_apply)
            if not vr.accepted:
                apply_status = "rejected_validation"
                degraded = True
                err = ",".join(vr.messages)
            else:
                try:
                    self.store.apply_proposal(next_apply)
                    apply_status = "applied"
                    self.rollout.record_apply(
                        next_apply.proposal_id,
                        target_value=next_apply.payload.get("new_value"),
                        tuning_key=key,
                    )
                    self.rollout.mark_stage(next_stage_after)
                except Exception as exc:
                    apply_status = "apply_failed"
                    degraded = True
                    err = str(exc)
        elif stage == "awaiting_canary" and not apply40:
            apply_status = "skipped_policy"

        rstate2 = self.rollout.read()
        mon_post = monitoring_snapshot(rollout_state=rstate2, evidence=evidence)
        cycle = ImprovementCycle(
            id=str(rstate2.get("cycle_id") or ""),
            proposals=[base_prop.as_dict()],
            simulation_result=dict(sim),
            approval_status=approval.status,
            rollout_stage=str(rstate2.get("stage") or stage),
            monitoring_state={"pre": dict(mon_pre), "post": dict(mon_post), "apply_status": apply_status},
            rollback_available=True,
        )

        return SelfImprovingSystemTrace(
            trace_id=trace_id,
            session_id=session_id,
            disabled=False,
            idle=False,
            cycle=cycle.as_dict(),
            simulation_outcome=dict(sim),
            approval_decision=approval.status,
            rollout_stage=str(rstate2.get("stage") or stage),
            monitoring_result=dict(mon_post),
            rollback_status=rollback_status,
            degraded=degraded,
            error=err,
        ).as_dict()
