from __future__ import annotations

import json
from pathlib import Path

from ..persistence import atomic_write_json, file_lock


class SessionStore:
    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def path_for(self, session_id: str) -> Path:
        safe_id = session_id.strip() or "python-session"
        return self.base_dir / f"{safe_id}.json"

    def save(self, session_id: str, payload: dict[str, object]) -> None:
        try:
            path = self.path_for(session_id)
            with file_lock(path):
                atomic_write_json(path, payload)
        except Exception:
            return

    def load(self, session_id: str) -> dict[str, object]:
        path = self.path_for(session_id)
        if not path.exists():
            return {}
        try:
            raw = path.read_text(encoding="utf-8").strip()
            parsed = json.loads(raw) if raw else {}
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}
