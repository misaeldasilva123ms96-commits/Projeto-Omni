import json
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from .governance_taxonomy import (
    GovernanceReason,
    GovernanceSource,
    GovernanceSeverity,
    build_governance_decision,
    governance_dict_for_resolution,
    infer_governance_reason,
    map_legacy_reason_string,
)
from .governance_timeline import (
    GovernanceTimelineEventType,
    build_governance_timeline_event,
    infer_event_type_from_transition,
    synthesize_timeline_from_legacy,
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# Backward-compatible alias used across the codebase and tests.
ResolutionReason = GovernanceReason


class RunStatus(str, Enum):
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    AWAITING_APPROVAL = "awaiting_approval"


ACTIVE_RUN_STATUSES = {
    RunStatus.RUNNING,
    RunStatus.PAUSED,
    RunStatus.AWAITING_APPROVAL,
}


class ResolutionState(str, Enum):
    RUNNING = "running"
    HOLD = "hold"
    PAUSED = "paused"
    APPROVED = "approved"
    RESUMED = "resumed"
    ROLLBACK = "rollback"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    FAILED = "failed"


def _normalize_resolution_state(raw: str, *, status: RunStatus) -> ResolutionState:
    value = str(raw or "").strip()
    try:
        return ResolutionState(value)
    except ValueError:
        if status == RunStatus.AWAITING_APPROVAL:
            return ResolutionState.HOLD
        if status == RunStatus.PAUSED:
            return ResolutionState.PAUSED
        if status == RunStatus.COMPLETED:
            return ResolutionState.COMPLETED
        if status == RunStatus.FAILED:
            return ResolutionState.FAILED
        return ResolutionState.RUNNING


def _normalize_resolution_reason(raw: str, *, fallback: GovernanceReason) -> GovernanceReason:
    return map_legacy_reason_string(str(raw or ""), fallback=fallback)


def infer_reason_from_action(action: str, *, status: RunStatus) -> GovernanceReason:
    return infer_governance_reason(last_action=action, run_status=status.value)


def infer_resolution_state(status: RunStatus, reason: GovernanceReason) -> ResolutionState:
    if reason == GovernanceReason.PROMOTION_ROLLBACK_THRESHOLD:
        return ResolutionState.ROLLBACK
    if reason == GovernanceReason.OPERATOR_APPROVE:
        return ResolutionState.APPROVED
    if reason == GovernanceReason.OPERATOR_RESUME:
        return ResolutionState.RESUMED
    if reason == GovernanceReason.POLICY_BLOCK:
        return ResolutionState.BLOCKED
    if status == RunStatus.AWAITING_APPROVAL or reason == GovernanceReason.GOVERNANCE_HOLD:
        return ResolutionState.HOLD
    if status == RunStatus.PAUSED:
        return ResolutionState.PAUSED
    if status == RunStatus.COMPLETED:
        return ResolutionState.COMPLETED
    if status == RunStatus.FAILED:
        return ResolutionState.FAILED
    return ResolutionState.RUNNING


@dataclass(slots=True)
class ResolutionRecord:
    current_resolution: str
    previous_resolution: str
    reason: str
    decision_source: str
    timestamp: str
    operator_id: str | None = None
    promotion_metadata: dict[str, Any] = field(default_factory=dict)
    engine_mode: str | None = None

    def as_dict(self) -> dict[str, Any]:
        payload = {
            "current_resolution": self.current_resolution,
            "previous_resolution": self.previous_resolution,
            "reason": self.reason,
            "decision_source": self.decision_source,
            "timestamp": self.timestamp,
            "operator_id": self.operator_id,
            "promotion_metadata": dict(self.promotion_metadata),
            "engine_mode": self.engine_mode,
        }
        payload["governance"] = governance_dict_for_resolution(
            reason=self.reason,
            decision_source=self.decision_source,
        )
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any], *, status: RunStatus, last_action: str) -> "ResolutionRecord":
        fallback_reason = infer_reason_from_action(last_action, status=status)
        state = _normalize_resolution_state(str(payload.get("current_resolution", "")), status=status)
        reason = _normalize_resolution_reason(str(payload.get("reason", "")), fallback=fallback_reason)
        previous = str(payload.get("previous_resolution", "")).strip() or state.value
        return cls(
            current_resolution=state.value,
            previous_resolution=previous,
            reason=reason.value,
            decision_source=str(payload.get("decision_source", "runtime_orchestrator") or "runtime_orchestrator"),
            timestamp=str(payload.get("timestamp", "")).strip() or utc_now_iso(),
            operator_id=str(payload.get("operator_id", "")).strip() or None,
            promotion_metadata=dict(payload.get("promotion_metadata", {}) or {}),
            engine_mode=str(payload.get("engine_mode", "")).strip() or None,
        )


@dataclass(slots=True)
class RunRecord:
    run_id: str
    goal_id: str | None
    session_id: str
    status: RunStatus
    started_at: str
    updated_at: str
    last_action: str
    progress_score: float
    metadata: dict[str, Any] = field(default_factory=dict)
    resolution: ResolutionRecord | None = None
    resolution_history: list[dict[str, Any]] = field(default_factory=list)
    governance_timeline: list[dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "goal_id": self.goal_id,
            "session_id": self.session_id,
            "status": self.status.value,
            "started_at": self.started_at,
            "updated_at": self.updated_at,
            "last_action": self.last_action,
            "progress_score": self.progress_score,
            "metadata": dict(self.metadata),
            "resolution": self.resolution.as_dict() if self.resolution else None,
            "resolution_history": [dict(item) for item in self.resolution_history],
            "governance_timeline": [dict(item) for item in self.governance_timeline],
        }

    def _append_governance_timeline(
        self,
        *,
        event_type: str,
        resolution: ResolutionRecord,
        status: RunStatus,
    ) -> None:
        self.governance_timeline.append(
            build_governance_timeline_event(
                event_type=event_type,
                timestamp=resolution.timestamp,
                current_resolution=resolution.current_resolution,
                previous_resolution=resolution.previous_resolution,
                reason=resolution.reason,
                decision_source=resolution.decision_source,
                run_status=status.value,
                operator_id=resolution.operator_id,
                promotion_metadata=dict(resolution.promotion_metadata) if resolution.promotion_metadata else None,
                engine_mode=resolution.engine_mode,
            )
        )
        self.governance_timeline = self.governance_timeline[-80:]

    @classmethod
    def build(
        cls,
        *,
        run_id: str,
        goal_id: str | None,
        session_id: str,
        status: RunStatus,
        last_action: str,
        progress_score: float,
        metadata: dict[str, Any] | None = None,
        started_at: str | None = None,
        resolution: ResolutionRecord | None = None,
        resolution_history: list[dict[str, Any]] | None = None,
        governance_timeline: list[dict[str, Any]] | None = None,
    ) -> "RunRecord":
        now = utc_now_iso()
        fallback_reason = infer_reason_from_action(last_action, status=status)
        resolution_state = infer_resolution_state(status, fallback_reason)
        res = resolution or ResolutionRecord(
            current_resolution=resolution_state.value,
            previous_resolution=resolution_state.value,
            reason=fallback_reason.value,
            decision_source="runtime_orchestrator",
            timestamp=now,
        )
        record = cls(
            run_id=str(run_id).strip(),
            goal_id=str(goal_id).strip() if goal_id else None,
            session_id=str(session_id).strip(),
            status=status,
            started_at=started_at or now,
            updated_at=now,
            last_action=str(last_action or "").strip(),
            progress_score=max(0.0, min(1.0, float(progress_score or 0.0))),
            metadata=dict(metadata or {}),
            resolution=res,
            resolution_history=list(resolution_history or []),
            governance_timeline=list(governance_timeline) if governance_timeline is not None else [],
        )
        if governance_timeline is None:
            record._append_governance_timeline(
                event_type=GovernanceTimelineEventType.START.value,
                resolution=record.resolution,
                status=status,
            )
        return record

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "RunRecord":
        status_raw = str(payload.get("status", RunStatus.RUNNING.value) or RunStatus.RUNNING.value)
        try:
            status = RunStatus(status_raw)
        except ValueError:
            status = RunStatus.RUNNING
        raw_timeline = payload.get("governance_timeline", [])
        timeline = [dict(item) for item in raw_timeline if isinstance(item, dict)]
        if not timeline:
            timeline = synthesize_timeline_from_legacy(
                resolution_history=[
                    dict(item)
                    for item in (payload.get("resolution_history", []) or [])
                    if isinstance(item, dict)
                ],
                resolution=dict(payload.get("resolution", {}) or {}) if payload.get("resolution") else None,
                run_status=status_raw,
            )
        return cls(
            run_id=str(payload.get("run_id", "")).strip(),
            goal_id=str(payload.get("goal_id", "")).strip() or None,
            session_id=str(payload.get("session_id", "")).strip(),
            status=status,
            started_at=str(payload.get("started_at", "")).strip() or utc_now_iso(),
            updated_at=str(payload.get("updated_at", "")).strip() or utc_now_iso(),
            last_action=str(payload.get("last_action", "")).strip(),
            progress_score=max(0.0, min(1.0, float(payload.get("progress_score", 0.0) or 0.0))),
            metadata=dict(payload.get("metadata", {}) or {}),
            resolution=ResolutionRecord.from_dict(
                dict(payload.get("resolution", {}) or {}),
                status=status,
                last_action=str(payload.get("last_action", "")).strip(),
            ),
            resolution_history=[
                dict(item)
                for item in (payload.get("resolution_history", []) or [])
                if isinstance(item, dict)
            ],
            governance_timeline=timeline,
        )

    def transition_resolution(
        self,
        *,
        status: RunStatus,
        last_action: str,
        reason: str | None = None,
        decision_source: str = "runtime_orchestrator",
        operator_id: str | None = None,
        promotion_metadata: dict[str, Any] | None = None,
        engine_mode: str | None = None,
    ) -> ResolutionRecord:
        fallback_reason = infer_reason_from_action(last_action, status=status)
        normalized_reason = _normalize_resolution_reason(str(reason or ""), fallback=fallback_reason)
        next_state = infer_resolution_state(status, normalized_reason)
        previous = self.resolution.current_resolution if self.resolution else next_state.value
        next_resolution = ResolutionRecord(
            current_resolution=next_state.value,
            previous_resolution=previous,
            reason=normalized_reason.value,
            decision_source=str(decision_source or "runtime_orchestrator").strip() or "runtime_orchestrator",
            timestamp=utc_now_iso(),
            operator_id=str(operator_id or "").strip() or None,
            promotion_metadata=dict(promotion_metadata or {}),
            engine_mode=str(engine_mode or "").strip() or None,
        )
        self.resolution = next_resolution
        self.resolution_history.append(next_resolution.as_dict())
        self.resolution_history = self.resolution_history[-40:]
        event_type = infer_event_type_from_transition(
            reason=next_resolution.reason,
            run_status=status.value,
            current_resolution=next_resolution.current_resolution,
            previous_resolution=previous,
        )
        self._append_governance_timeline(event_type=event_type, resolution=next_resolution, status=status)
        return next_resolution


class RunRegistry:
    def __init__(self, root: Path) -> None:
        self.base_dir = root / ".logs" / "fusion-runtime" / "control"
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.base_dir / "run_registry.json"
        self._lock = threading.RLock()
        self._runs: dict[str, RunRecord] = {}
        if self.path.exists():
            self.reload_from_disk()

    def register(self, run: RunRecord) -> RunRecord:
        with self._lock:
            existing = self._runs.get(run.run_id)
            if existing is not None:
                merged_timeline = list(existing.governance_timeline)
                if not merged_timeline:
                    merged_timeline = synthesize_timeline_from_legacy(
                        resolution_history=list(existing.resolution_history),
                        resolution=existing.resolution.as_dict() if existing.resolution else None,
                        run_status=existing.status.value,
                    )
                if not merged_timeline:
                    merged_timeline = None
                run = RunRecord.build(
                    run_id=run.run_id,
                    goal_id=run.goal_id or existing.goal_id,
                    session_id=run.session_id or existing.session_id,
                    status=run.status,
                    last_action=run.last_action or existing.last_action,
                    progress_score=run.progress_score,
                    metadata={**existing.metadata, **run.metadata},
                    started_at=existing.started_at,
                    resolution_history=list(existing.resolution_history),
                    governance_timeline=merged_timeline,
                )
            self._runs[run.run_id] = run
            self.flush()
            return run

    def update_status(
        self,
        run_id: str,
        status: RunStatus,
        last_action: str,
        progress: float,
        reason: str | None = None,
        decision_source: str = "runtime_orchestrator",
        operator_id: str | None = None,
        promotion_metadata: dict[str, Any] | None = None,
        engine_mode: str | None = None,
    ) -> RunRecord | None:
        with self._lock:
            record = self._runs.get(str(run_id).strip())
            if record is None:
                return None
            record.status = status
            record.last_action = str(last_action or "").strip()
            record.progress_score = max(0.0, min(1.0, float(progress or 0.0)))
            record.updated_at = utc_now_iso()
            record.transition_resolution(
                status=status,
                last_action=record.last_action,
                reason=reason,
                decision_source=decision_source,
                operator_id=operator_id,
                promotion_metadata=promotion_metadata,
                engine_mode=engine_mode,
            )
            self.flush()
            return record

    def get(self, run_id: str) -> RunRecord | None:
        with self._lock:
            self._reload_if_available()
            return self._runs.get(str(run_id).strip())

    def get_active(self) -> list[RunRecord]:
        with self._lock:
            self._reload_if_available()
            records = [item for item in self._runs.values() if item.status in ACTIVE_RUN_STATUSES]
            return sorted(records, key=lambda item: item.updated_at, reverse=True)

    def get_all(self, limit: int = 50) -> list[RunRecord]:
        with self._lock:
            self._reload_if_available()
            records = sorted(self._runs.values(), key=lambda item: item.updated_at, reverse=True)
            return records[: max(1, int(limit or 50))]

    def get_resolution_summary(self) -> dict[str, Any]:
        with self._lock:
            self._reload_if_available()
            summary = {
                "total_runs": len(self._runs),
                "resolution_counts": {state.value: 0 for state in ResolutionState},
                "reason_counts": {reason.value: 0 for reason in ResolutionReason},
                "governance": {
                    "taxonomy_version": "30.5",
                    "source_counts": {src.value: 0 for src in GovernanceSource},
                    "severity_counts": {sev.value: 0 for sev in GovernanceSeverity},
                    "blocked_by_policy": 0,
                    "waiting_operator": 0,
                    "timeline_event_counts": {},
                },
            }
            waiting_operator = 0
            for record in self._runs.values():
                resolution = record.resolution
                if resolution is None:
                    continue
                current = str(resolution.current_resolution or "").strip()
                reason = str(resolution.reason or "").strip()
                if current in summary["resolution_counts"]:
                    summary["resolution_counts"][current] += 1
                if reason in summary["reason_counts"]:
                    summary["reason_counts"][reason] += 1
                decision = build_governance_decision(
                    reason=resolution.reason,
                    decision_source=resolution.decision_source,
                )
                gov = summary["governance"]
                gov["source_counts"][decision.source.value] += 1
                gov["severity_counts"][decision.severity.value] += 1
                if decision.reason == GovernanceReason.POLICY_BLOCK:
                    gov["blocked_by_policy"] += 1
                if record.status == RunStatus.AWAITING_APPROVAL:
                    waiting_operator += 1
                elif record.status == RunStatus.PAUSED and str(record.last_action).startswith("operator_"):
                    waiting_operator += 1
                for ev in record.governance_timeline:
                    if not isinstance(ev, dict):
                        continue
                    et = str(ev.get("event_type", "") or "").strip()
                    if et:
                        counts = summary["governance"]["timeline_event_counts"]
                        counts[et] = int(counts.get(et, 0)) + 1
            summary["governance"]["waiting_operator"] = waiting_operator
            return summary

    def get_runs_waiting_operator(self) -> list[RunRecord]:
        with self._lock:
            self._reload_if_available()
            rows = []
            for record in self._runs.values():
                is_waiting_status = record.status == RunStatus.AWAITING_APPROVAL
                is_operator_pause = record.status == RunStatus.PAUSED and str(record.last_action).startswith("operator_")
                if is_waiting_status or is_operator_pause:
                    rows.append(record)
            return sorted(rows, key=lambda item: item.updated_at, reverse=True)

    def get_runs_with_rollback(self) -> list[RunRecord]:
        with self._lock:
            self._reload_if_available()
            rows = []
            for record in self._runs.values():
                resolution = record.resolution
                reason = str((resolution.reason if resolution else "") or "").strip()
                if reason == GovernanceReason.PROMOTION_ROLLBACK_THRESHOLD.value:
                    rows.append(record)
                    continue
                if str((record.metadata or {}).get("promotion_rollback_reason", "")).strip():
                    rows.append(record)
            return sorted(rows, key=lambda item: item.updated_at, reverse=True)

    def get_runs_blocked_by_policy(self) -> list[RunRecord]:
        with self._lock:
            self._reload_if_available()
            rows = []
            for record in self._runs.values():
                resolution = record.resolution
                reason = str((resolution.reason if resolution else "") or "").strip()
                if reason == GovernanceReason.POLICY_BLOCK.value:
                    rows.append(record)
                    continue
                cur = str((resolution.current_resolution if resolution else "") or "").strip().lower()
                if cur == "blocked":
                    rows.append(record)
            return sorted(rows, key=lambda item: item.updated_at, reverse=True)

    def recent_resolution_events(self, limit: int = 25) -> list[dict[str, Any]]:
        with self._lock:
            self._reload_if_available()
            events: list[dict[str, Any]] = []
            for record in self._runs.values():
                history = list(record.resolution_history)
                if not history and record.resolution is not None:
                    history = [record.resolution.as_dict()]
                for item in history:
                    if not isinstance(item, dict):
                        continue
                    events.append(
                        {
                            **item,
                            "run_id": record.run_id,
                            "session_id": record.session_id,
                            "status": record.status.value,
                        }
                    )
            events.sort(key=lambda item: str(item.get("timestamp", "")), reverse=True)
            return events[: max(1, int(limit or 25))]

    def recent_governance_timeline_events(self, limit: int = 25) -> list[dict[str, Any]]:
        with self._lock:
            self._reload_if_available()
            events: list[dict[str, Any]] = []
            for record in self._runs.values():
                for item in record.governance_timeline:
                    if not isinstance(item, dict):
                        continue
                    events.append(
                        {
                            **dict(item),
                            "run_id": record.run_id,
                            "session_id": record.session_id,
                            "status": record.status.value,
                        }
                    )
            events.sort(key=lambda item: str(item.get("timestamp", "")), reverse=True)
            return events[: max(1, int(limit or 25))]

    def latest_governance_event_by_run(self) -> dict[str, dict[str, Any]]:
        with self._lock:
            self._reload_if_available()
            out: dict[str, dict[str, Any]] = {}
            for run_id, record in self._runs.items():
                if not record.governance_timeline:
                    continue
                last = record.governance_timeline[-1]
                if isinstance(last, dict):
                    out[str(run_id)] = dict(last)
            return out

    def reload_from_disk(self) -> None:
        with self._lock:
            try:
                payload = json.loads(self.path.read_text(encoding="utf-8"))
            except Exception as error:
                raise ValueError(f"Invalid run registry data: {error}") from error
            if not isinstance(payload, dict):
                raise ValueError("Invalid run registry data: root payload must be an object.")
            raw_runs = payload.get("runs", {})
            if not isinstance(raw_runs, dict):
                raise ValueError("Invalid run registry data: runs must be a mapping.")
            self._runs = {
                str(run_id): RunRecord.from_dict(item)
                for run_id, item in raw_runs.items()
                if isinstance(item, dict)
            }

    def flush(self) -> None:
        with self._lock:
            payload = {
                "runs": {run_id: record.as_dict() for run_id, record in self._runs.items()},
            }
            temp_path = self.path.with_suffix(".tmp")
            temp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            temp_path.replace(self.path)

    def _reload_if_available(self) -> None:
        if not self.path.exists():
            return
        self.reload_from_disk()
