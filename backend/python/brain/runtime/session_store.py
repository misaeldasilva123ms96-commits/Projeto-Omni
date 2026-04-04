from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _repair_text(value: str) -> str:
    if not value:
        return ""
    if any(marker in value for marker in ("Ã", "ï¿½")):
        try:
            repaired = value.encode("latin-1", errors="ignore").decode("utf-8", errors="ignore")
            if repaired:
                return repaired
        except Exception:
            return value
    return value


def _sanitize_payload(value: Any) -> Any:
    if isinstance(value, str):
        return _repair_text(value)
    if isinstance(value, list):
        return [_sanitize_payload(item) for item in value]
    if isinstance(value, dict):
        return {key: _sanitize_payload(item) for key, item in value.items()}
    return value


class SessionStore:
    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def path_for(self, session_id: str) -> Path:
        safe_id = session_id.strip() or "python-session"
        return self.base_dir / f"{safe_id}.json"

    def save(self, session_id: str, payload: dict[str, object]) -> None:
        try:
            sanitized = _sanitize_payload(payload)
            path = self.path_for(session_id)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(sanitized, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception:
            return

    def load(self, session_id: str) -> dict[str, object]:
        path = self.path_for(session_id)
        if not path.exists():
            return {}
        try:
            raw = path.read_text(encoding="utf-8").strip()
            parsed = json.loads(raw) if raw else {}
            if isinstance(parsed, dict):
                sanitized = _sanitize_payload(parsed)
                if sanitized != parsed:
                    self.save(session_id, sanitized)
                return sanitized
        except Exception:
            return {}
        return {}
