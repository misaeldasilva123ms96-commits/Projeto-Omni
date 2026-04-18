from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Any

from .controlled_apply import Phase39TuningStore
from .controlled_evolution_models import ControlledSelfEvolutionTrace, GovernedProposal
from .controlled_monitor import apply_rollback_if_recommended, evaluate_monitor_and_rollback
from .controlled_opportunity_detector import ControlledOpportunityDetector
from .controlled_proposal_builder import ControlledProposalBuilder
from .controlled_validation import validate_governed_proposal


class ControlledEvolutionEngine:
    """Phase 39 — governed detect → propose → validate → apply → monitor/rollback (parameter tuning only)."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.store = Phase39TuningStore(root)
        self.detector = ControlledOpportunityDetector()
        self.builder = ControlledProposalBuilder()

    def evaluate_turn(
        self,
        *,
        session_id: str,
        evidence: dict[str, Any],
        skip_apply: bool = False,
    ) -> dict[str, Any]:
        trace_id = f"ce39-{uuid.uuid4().hex[:18]}"
        disabled = str(os.getenv("OMINI_PHASE39_DISABLE", "")).strip().lower() in ("1", "true", "yes")
        if disabled:
            tr = ControlledSelfEvolutionTrace(
                trace_id=trace_id,
                session_id=session_id,
                disabled=True,
                opportunity_count=0,
                proposal_count=0,
                validation_passed=False,
                validation_messages=["phase39_disabled_by_env"],
                apply_status="skipped",
                monitor_status="idle",
                rollback_recommended=False,
                rollback_applied=False,
                degraded=False,
                error="",
            )
            return tr.as_dict()

        degraded = False
        err = ""
        tuning = self.store.read()
        pending = tuning.get("pending_monitor") if isinstance(tuning.get("pending_monitor"), dict) else None

        opportunities = self.detector.detect(session_id=session_id, evidence=evidence)
        _mon_status, rb_rec, rb_prop = evaluate_monitor_and_rollback(
            pending_monitor=pending,
            opportunities=opportunities,
        )
        rollback_applied = apply_rollback_if_recommended(
            rollback_recommended=rb_rec,
            proposal_id=rb_prop,
            store=self.store,
        )
        if rollback_applied:
            self.store.clear_pending_monitor()
            tr = ControlledSelfEvolutionTrace(
                trace_id=trace_id,
                session_id=session_id,
                disabled=False,
                opportunity_count=len(opportunities),
                proposal_count=0,
                validation_passed=False,
                validation_messages=["rollback_executed"],
                apply_status="rollback",
                monitor_status="rollback_applied",
                rollback_recommended=True,
                rollback_applied=True,
                degraded=False,
                error="",
                opportunities=[o.as_dict() for o in opportunities],
            )
            return tr.as_dict()

        if not opportunities and pending:
            self.store.clear_pending_monitor()

        proposals_built: list[GovernedProposal] = []
        for opp in opportunities:
            prop = self.builder.build(opportunity=opp, current_tuning=tuning)
            if prop is not None:
                proposals_built.append(prop)
                break

        if not proposals_built:
            tr = ControlledSelfEvolutionTrace(
                trace_id=trace_id,
                session_id=session_id,
                disabled=False,
                opportunity_count=len(opportunities),
                proposal_count=0,
                validation_passed=True,
                validation_messages=["no_actionable_proposal"],
                apply_status="skipped",
                monitor_status=_mon_status or "idle",
                rollback_recommended=False,
                rollback_applied=False,
                degraded=degraded,
                error=err,
                opportunities=[o.as_dict() for o in opportunities],
            )
            return tr.as_dict()

        prop = proposals_built[0]
        vr = validate_governed_proposal(prop)
        apply_enabled = str(os.getenv("OMINI_PHASE39_APPLY", "")).strip().lower() in ("1", "true", "yes")
        if skip_apply:
            apply_enabled = False
        apply_status = "skipped_policy"
        if vr.accepted and apply_enabled:
            try:
                self.store.apply_proposal(prop)
                prop.apply_status = "applied"
                apply_status = "applied"
            except Exception as exc:
                degraded = True
                err = str(exc)
                apply_status = "apply_failed"
                prop.apply_status = "failed"
        elif vr.accepted:
            prop.apply_status = "skipped_policy"
            apply_status = "skipped_policy"
        else:
            prop.apply_status = "rejected_validation"
            apply_status = "rejected_validation"

        prop.monitor_status = "pending_next_turn" if apply_status == "applied" else "n_a"
        prop.rollback_status = "rollback_ready" if apply_status == "applied" else "n_a"

        tr = ControlledSelfEvolutionTrace(
            trace_id=trace_id,
            session_id=session_id,
            disabled=False,
            opportunity_count=len(opportunities),
            proposal_count=len(proposals_built),
            validation_passed=vr.accepted,
            validation_messages=list(vr.messages),
            apply_status=apply_status,
            monitor_status=prop.monitor_status,
            rollback_recommended=False,
            rollback_applied=False,
            degraded=degraded,
            error=err,
            opportunities=[o.as_dict() for o in opportunities],
            proposals=[prop.as_dict()],
        )
        return tr.as_dict()
