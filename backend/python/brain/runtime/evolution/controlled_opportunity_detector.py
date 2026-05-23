from __future__ import annotations

import uuid
from typing import Any

from .controlled_evolution_models import ImprovementOpportunity


class ControlledOpportunityDetector:
    """Phase 39 — selective, explainable opportunity detection from one-turn evidence (bounded)."""

    MAX_OPPORTUNITIES_PER_TURN = 2

    def detect(self, *, session_id: str, evidence: dict[str, Any]) -> list[ImprovementOpportunity]:
        out: list[ImprovementOpportunity] = []

        perf = evidence.get("performance") if isinstance(evidence.get("performance"), dict) else {}
        pt = perf.get("trace") if isinstance(perf.get("trace"), dict) else {}
        if bool(pt.get("degraded")):
            out.append(
                ImprovementOpportunity(
                    opportunity_id=f"opp39-{uuid.uuid4().hex[:12]}",
                    session_id=session_id,
                    source_type="performance",
                    category="repeated_degraded_fallback",
                    summary="Performance optimization degraded to uncompressed boundary this turn.",
                    confidence=0.75,
                    evidence_refs=[str(pt.get("trace_id", "")).strip() or "perf_trace"],
                    recommended_proposal_type="performance_cache_tune",
                    governance_relevant=True,
                    metadata={"trace_id": pt.get("trace_id")},
                )
            )

        td = evidence.get("task_decomposition") if isinstance(evidence.get("task_decomposition"), dict) else {}
        ttr = td.get("trace") if isinstance(td.get("trace"), dict) else {}
        if bool(ttr.get("truncated")):
            out.append(
                ImprovementOpportunity(
                    opportunity_id=f"opp39-{uuid.uuid4().hex[:12]}",
                    session_id=session_id,
                    source_type="decomposition",
                    category="repeated_truncation_signal",
                    summary="Task decomposition hit truncation caps this turn.",
                    confidence=0.7,
                    evidence_refs=[str(ttr.get("trace_id", "")).strip() or "dec_trace"],
                    recommended_proposal_type="decomposition_limit_tune",
                    governance_relevant=True,
                    metadata={"subtask_count": ttr.get("subtask_count")},
                )
            )

        coord = evidence.get("coordination") if isinstance(evidence.get("coordination"), dict) else {}
        ctr = coord.get("trace") if isinstance(coord.get("trace"), dict) else {}
        issues = ctr.get("issues_aggregate") if isinstance(ctr.get("issues_aggregate"), list) else []
        if len(issues) >= 2:
            out.append(
                ImprovementOpportunity(
                    opportunity_id=f"opp39-{uuid.uuid4().hex[:12]}",
                    session_id=session_id,
                    source_type="coordination",
                    category="persistent_validator_pressure",
                    summary="Coordination validator aggregated multiple issues this turn.",
                    confidence=0.55,
                    evidence_refs=[str(ctr.get("coordination_id", "")).strip() or "coord"],
                    recommended_proposal_type="advisory_routing_preference",
                    governance_relevant=True,
                    metadata={"issues": issues[:8]},
                )
            )

        lt = evidence.get("learning_trace") if isinstance(evidence.get("learning_trace"), dict) else {}
        if bool(lt.get("execution_degraded")) or str(lt.get("outcome_class", "")).lower() in ("negative", "failure"):
            out.append(
                ImprovementOpportunity(
                    opportunity_id=f"opp39-{uuid.uuid4().hex[:12]}",
                    session_id=session_id,
                    source_type="learning",
                    category="negative_learning_outcome",
                    summary="Learning intelligence classified a degraded or negative turn outcome.",
                    confidence=0.6,
                    evidence_refs=[str(lt.get("learning_record_id", "")).strip() or "learning"],
                    recommended_proposal_type="strategy_bias_shift",
                    governance_relevant=True,
                    metadata={"outcome_class": lt.get("outcome_class")},
                )
            )

        lr = str(evidence.get("last_runtime_reason", "") or "").strip()
        if lr in ("empty_swarm_response", "control_layer_block", "reasoning_validation_block"):
            out.append(
                ImprovementOpportunity(
                    opportunity_id=f"opp39-{uuid.uuid4().hex[:12]}",
                    session_id=session_id,
                    source_type="runtime",
                    category="fallback_or_block_pressure",
                    summary=f"Runtime ended with guarded reason code: {lr}.",
                    confidence=0.5,
                    evidence_refs=[lr],
                    recommended_proposal_type="observability_threshold_tune",
                    governance_relevant=True,
                    metadata={"last_runtime_reason": lr},
                )
            )

        return out[: self.MAX_OPPORTUNITIES_PER_TURN]
