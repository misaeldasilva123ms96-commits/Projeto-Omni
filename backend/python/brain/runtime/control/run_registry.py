import json
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


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
        }

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
    ) -> "RunRecord":
        now = utc_now_iso()
        return cls(
            run_id=str(run_id).strip(),
            goal_id=str(goal_id).strip() if goal_id else None,
            session_id=str(session_id).strip(),
            status=status,
            started_at=started_at or now,
            updated_at=now,
            last_action=str(last_action or "").strip(),
            progress_score=max(0.0, min(1.0, float(progress_score or 0.0))),
            metadata=dict(metadata or {}),
        )

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "RunRecord":
        status_raw = str(payload.get("status", RunStatus.RUNNING.value) or RunStatus.RUNNING.value)
        try:
            status = RunStatus(status_raw)
        except ValueError:
            status = RunStatus.RUNNING
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
        )


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
                run = RunRecord.build(
                    run_id=run.run_id,
                    goal_id=run.goal_id or existing.goal_id,
                    session_id=run.session_id or existing.session_id,
                    status=run.status,
                    last_action=run.last_action or existing.last_action,
                    progress_score=run.progress_score,
                    metadata={**existing.metadata, **run.metadata},
                    started_at=existing.started_at,
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
    ) -> RunRecord | None:
        with self._lock:
            record = self._runs.get(str(run_id).strip())
            if record is None:
                return None
            record.status = status
            record.last_action = str(last_action or "").strip()
            record.progress_score = max(0.0, min(1.0, float(progress or 0.0)))
            record.updated_at = utc_now_iso()
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
