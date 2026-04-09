from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class DecisionMemoryStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def _default_payload(self) -> dict[str, Any]:
        return {"entries": []}

    def _load(self) -> dict[str, Any]:
        try:
            raw = self.path.read_text(encoding="utf-8").strip()
            parsed = json.loads(raw) if raw else {}
            if isinstance(parsed, dict) and isinstance(parsed.get("entries", []), list):
                return {"entries": parsed.get("entries", [])}
        except Exception:
            pass
        return self._default_payload()

    def _save(self, payload: dict[str, Any]) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            return

    def record_decision(
        self,
        *,
        session_id: str,
        task_id: str,
        run_id: str,
        decision_type: str,
        reason: str,
        task_type: str = "",
        reason_code: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload = self._load()
        entries = payload.setdefault("entries", [])
        entry = {
            "entry_id": f"{session_id}:{task_id or 'task'}:{run_id or 'run'}:{len(entries) + 1}",
            "timestamp": _utc_now(),
            "session_id": session_id,
            "task_id": task_id,
            "run_id": run_id,
            "decision_type": decision_type,
            "task_type": task_type,
            "reason_code": reason_code,
            "reason": reason,
            "metadata": metadata or {},
        }
        entries.append(entry)
        payload["entries"] = entries[-200:]
        self._save(payload)
        return entry

    def find_decisions(
        self,
        *,
        session_id: str | None = None,
        task_type: str | None = None,
        decision_type: str | None = None,
        reason_code: str | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        payload = self._load()
        entries = payload.get("entries", [])
        if not isinstance(entries, list):
            return []
        matches: list[dict[str, Any]] = []
        for item in reversed(entries):
            if not isinstance(item, dict):
                continue
            if session_id and item.get("session_id") != session_id:
                continue
            if task_type and item.get("task_type") != task_type:
                continue
            if decision_type and item.get("decision_type") != decision_type:
                continue
            if reason_code and item.get("reason_code") != reason_code:
                continue
            matches.append(item)
            if len(matches) >= limit:
                break
        return matches

