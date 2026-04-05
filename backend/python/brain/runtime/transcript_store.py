from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class TranscriptEntry:
    role: str
    content: str
    timestamp: str


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
        for line in lines[-limit:]:
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
            entries.append({"role": role, "content": content.strip()})
        return entries[-limit:]

    def append_turn(self, session_id: str, user_message: str, assistant_response: str) -> None:
        path = self._session_path(session_id)
        timestamp = datetime.now(timezone.utc).isoformat()
        entries = [
            TranscriptEntry(role="user", content=user_message.strip(), timestamp=timestamp),
            TranscriptEntry(role="assistant", content=assistant_response.strip(), timestamp=timestamp),
        ]
        try:
            with path.open("a", encoding="utf-8") as handle:
                for entry in entries:
                    handle.write(
                        json.dumps(
                            {"role": entry.role, "content": entry.content, "timestamp": entry.timestamp},
                            ensure_ascii=False,
                        )
                    )
                    handle.write("\n")
        except Exception:
            return
