from __future__ import annotations

from pathlib import Path
from typing import Any

from ._reader_utils import read_tail_jsonl
from .models import GovernanceVerdictSnapshot, SpecialistDecisionSnapshot, TraceSnapshot


class SpecialistReader:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.path = root / ".logs" / "fusion-runtime" / "specialists" / "coordination_log.jsonl"

    def read_latest_trace(self) -> TraceSnapshot | None:
        traces = self.read_recent_traces(limit=1)
        return traces[0] if traces else None

    def read_recent_traces(self, *, limit: int = 10) -> list[TraceSnapshot]:
        payloads = read_tail_jsonl(self.path, limit=max(1, limit))
        return [snapshot for payload in payloads if (snapshot := self._to_snapshot(payload)) is not None]

    def _to_snapshot(self, payload: dict[str, Any]) -> TraceSnapshot | None:
        trace_id = str(payload.get("trace_id", "")).strip()
        if not trace_id:
            return None
        decisions: list[SpecialistDecisionSnapshot] = []
        for raw_decision in payload.get("decisions", []):
            if not isinstance(raw_decision, dict):
                continue
            decisions.append(
                SpecialistDecisionSnapshot(
                    decision_id=str(raw_decision.get("decision_id", "")),
                    specialist_type=str(raw_decision.get("specialist_type", "")),
                    status=str(raw_decision.get("status", "")),
                    reasoning=str(raw_decision.get("reasoning", "")),
                    confidence=float(raw_decision.get("confidence", 0.0) or 0.0),
                    simulation_id=str(raw_decision.get("simulation_id")) if raw_decision.get("simulation_id") else None,
                    decided_at=str(raw_decision.get("decided_at", "")),
                    metadata={
                        key: value
                        for key, value in raw_decision.items()
                        if key
                        not in {
                            "decision_id",
                            "specialist_type",
                            "status",
                            "reasoning",
                            "confidence",
                            "simulation_id",
                            "decided_at",
                        }
                    },
                )
            )
        governance_verdicts: list[GovernanceVerdictSnapshot] = []
        for raw_verdict in payload.get("governance_verdicts", []):
            if not isinstance(raw_verdict, dict):
                continue
            governance_verdicts.append(
                GovernanceVerdictSnapshot(
                    decision_id=str(raw_verdict.get("decision_id", "")),
                    verdict=str(raw_verdict.get("verdict", "")),
                    risk_level=str(raw_verdict.get("risk_level", "")),
                    blocked_reasons=[str(item) for item in raw_verdict.get("blocked_reasons", []) if str(item).strip()],
                    violations=[str(item) for item in raw_verdict.get("violations", []) if str(item).strip()],
                    reasoning=str(raw_verdict.get("reasoning", "")),
                    confidence=float(raw_verdict.get("confidence", 0.0) or 0.0),
                    decided_at=str(raw_verdict.get("decided_at", "")),
                )
            )
        return TraceSnapshot(
            trace_id=trace_id,
            goal_id=str(payload.get("goal_id")) if payload.get("goal_id") else None,
            session_id=str(payload.get("session_id")) if payload.get("session_id") else None,
            final_outcome=str(payload.get("final_outcome", "")),
            started_at=str(payload.get("started_at", "")),
            completed_at=str(payload.get("completed_at")) if payload.get("completed_at") else None,
            decisions=decisions,
            governance_verdicts=governance_verdicts,
            metadata=dict(payload.get("metadata", {}) or {}),
        )
