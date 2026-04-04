from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
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


@dataclass(frozen=True)
class TranscriptEntry:
    role: str
    content: str
    timestamp: str
    turn_id: str = ""
    session_id: str = ""
    user_id: str = ""


class TranscriptStore:
    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _session_path(self, session_id: str) -> Path:
        safe_session_id = session_id.strip() or "default"
        return self.base_dir / f"{safe_session_id}.jsonl"

    def load_recent_history(self, session_id: str, limit: int = 6) -> list[dict[str, str]]:
        path = self._session_path(session_id)
        if not path.exists():
            return []
        entries: list[dict[str, str]] = []
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except Exception:
            return []
        for line in lines[-limit * 2 :]:
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except Exception:
                continue
            role = payload.get("role")
            content = payload.get("content")
            if role not in {"user", "assistant"}:
                continue
            if not isinstance(content, str) or not content.strip():
                continue
            entries.append({"role": role, "content": _repair_text(content.strip())})
        return entries[-limit:]

    def append_turn(
        self,
        session_id: str,
        user_message: str,
        assistant_response: str,
        *,
        turn_id: str = "",
        user_id: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        path = self._session_path(session_id)
        timestamp = datetime.now(timezone.utc).isoformat()
        metadata = metadata or {}
        entries = [
            TranscriptEntry(
                role="user",
                content=_repair_text(user_message.strip()),
                timestamp=timestamp,
                turn_id=turn_id,
                session_id=session_id,
                user_id=user_id,
            ),
            TranscriptEntry(
                role="assistant",
                content=_repair_text(assistant_response.strip()),
                timestamp=timestamp,
                turn_id=turn_id,
                session_id=session_id,
                user_id=user_id,
            ),
        ]
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as handle:
                for entry in entries:
                    handle.write(
                        json.dumps(
                            {
                                "role": entry.role,
                                "content": entry.content,
                                "timestamp": entry.timestamp,
                                "turn_id": entry.turn_id,
                                "session_id": entry.session_id,
                                "user_id": entry.user_id,
                                "metadata": metadata,
                            },
                            ensure_ascii=False,
                        )
                    )
                    handle.write("\n")
        except Exception:
            return
