from __future__ import annotations

import json
import re
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


def _sanitize_payload(value: Any) -> Any:
    if isinstance(value, str):
        return _repair_text(value)
    if isinstance(value, list):
        return [_sanitize_payload(item) for item in value]
    if isinstance(value, dict):
        return {key: _sanitize_payload(item) for key, item in value.items()}
    return value


def _session_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def _short_title(value: str, limit: int = 60) -> str:
    normalized = re.sub(r"\s+", " ", _repair_text(value or "").replace("\n", " ").strip())
    if not normalized:
        return ""
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 1].rstrip() + "…"


def _first_user_message(payload: dict[str, Any]) -> str:
    turns = payload.get("turns", [])
    if isinstance(turns, list):
        for turn in turns:
            if not isinstance(turn, dict):
                continue
            message = turn.get("message")
            if isinstance(message, str) and message.strip():
                return message

    history = payload.get("history", [])
    if isinstance(history, list):
        for item in history:
            if not isinstance(item, dict):
                continue
            if item.get("role") != "user":
                continue
            content = item.get("content")
            if isinstance(content, str) and content.strip():
                return content
    return ""


def _normalize_session_payload(session_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    normalized = _sanitize_payload(payload)
    if not isinstance(normalized, dict):
        normalized = {}

    now = _session_timestamp()
    normalized["session_id"] = str(normalized.get("session_id") or session_id).strip() or session_id

    title = normalized.get("title")
    if not isinstance(title, str) or not title.strip():
        title = _short_title(_first_user_message(normalized)) or "Nova conversa"
    normalized["title"] = title

    created_at = normalized.get("created_at")
    if not isinstance(created_at, str) or not created_at.strip():
        turns = normalized.get("turns", [])
        if isinstance(turns, list) and turns:
            first_turn = turns[0] if isinstance(turns[0], dict) else {}
            created_at = first_turn.get("created_at") if isinstance(first_turn, dict) else ""
        normalized["created_at"] = created_at if isinstance(created_at, str) and created_at.strip() else now

    updated_at = normalized.get("updated_at")
    if not isinstance(updated_at, str) or not updated_at.strip():
        turns = normalized.get("turns", [])
        if isinstance(turns, list) and turns:
            last_turn = turns[-1] if isinstance(turns[-1], dict) else {}
            updated_at = last_turn.get("created_at") if isinstance(last_turn, dict) else ""
        normalized["updated_at"] = updated_at if isinstance(updated_at, str) and updated_at.strip() else normalized["created_at"]

    return normalized


class SessionStore:
    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def path_for(self, session_id: str) -> Path:
        safe_id = session_id.strip() or "python-session"
        return self.base_dir / f"{safe_id}.json"

    def save(self, session_id: str, payload: dict[str, object]) -> None:
        try:
            sanitized = _normalize_session_payload(session_id, payload)
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
                sanitized = _normalize_session_payload(session_id, parsed)
                if sanitized != parsed:
                    self.save(session_id, sanitized)
                return sanitized
        except Exception:
            return {}
        return {}
