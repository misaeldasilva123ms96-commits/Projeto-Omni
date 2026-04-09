from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class WorkingMemoryStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def _default_payload(self) -> dict[str, Any]:
        return {"sessions": {}}

    def _load(self) -> dict[str, Any]:
        try:
            raw = self.path.read_text(encoding="utf-8").strip()
            parsed = json.loads(raw) if raw else {}
            if isinstance(parsed, dict):
                sessions = parsed.get("sessions", {})
                if isinstance(sessions, dict):
                    return {"sessions": sessions}
        except Exception:
            pass
        return self._default_payload()

    def _save(self, payload: dict[str, Any]) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            return

    def update_session(self, session_id: str, state: dict[str, Any]) -> dict[str, Any]:
        payload = self._load()
        sessions = payload.setdefault("sessions", {})
        previous = sessions.get(session_id, {})
        if not isinstance(previous, dict):
            previous = {}
        merged = {**previous, **state, "updated_at": _utc_now()}
        sessions[session_id] = merged
        self._save(payload)
        return merged

    def load_session(self, session_id: str) -> dict[str, Any]:
        payload = self._load()
        session = payload.get("sessions", {}).get(session_id, {})
        return session if isinstance(session, dict) else {}

