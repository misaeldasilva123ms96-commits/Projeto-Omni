from __future__ import annotations

import json
from pathlib import Path


DEFAULT_HISTORY_LIMIT = 6
DEFAULT_RESPONSE_STYLE = "balanced"
DEFAULT_DEPTH_PREFERENCE = "medium"
MAX_PROFILE_ITEMS = 8


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


def _normalize_list(values: object, limit: int = MAX_PROFILE_ITEMS) -> list[str]:
    if not isinstance(values, list):
        return []

    seen: set[str] = set()
    normalized: list[str] = []
    for raw in values:
        text = _repair_text(str(raw).strip())
        if not text:
            continue
        key = text.casefold()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(text)
        if len(normalized) >= limit:
            break
    return normalized


def default_memory_store() -> dict[str, object]:
    return {
        "history": [],
        "user": {
            "id": "",
            "nome": "",
            "trabalho": "",
            "preferencias": [],
            "response_style": DEFAULT_RESPONSE_STYLE,
            "depth_preference": DEFAULT_DEPTH_PREFERENCE,
            "recurring_topics": [],
            "goals": [],
        },
        "long_term": {},
    }


def normalize_user_profile(user: object) -> dict[str, object]:
    if not isinstance(user, dict):
        user = {}

    user_id = user.get("id", "")
    nome = user.get("nome", "")
    trabalho = user.get("trabalho", "")
    response_style = str(user.get("response_style", DEFAULT_RESPONSE_STYLE)).strip() or DEFAULT_RESPONSE_STYLE
    depth_preference = str(user.get("depth_preference", DEFAULT_DEPTH_PREFERENCE)).strip() or DEFAULT_DEPTH_PREFERENCE

    return {
        "id": _repair_text(str(user_id).strip()),
        "nome": _repair_text(str(nome).strip()),
        "trabalho": _repair_text(str(trabalho).strip()),
        "preferencias": _normalize_list(user.get("preferencias", [])),
        "response_style": _repair_text(response_style),
        "depth_preference": _repair_text(depth_preference),
        "recurring_topics": _normalize_list(user.get("recurring_topics", [])),
        "goals": _normalize_list(user.get("goals", [])),
    }


def _sanitize_history(history: object, history_limit: int) -> list[dict[str, str]]:
    if not isinstance(history, list):
        return []

    clean_history: list[dict[str, str]] = []
    for item in history:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        content = item.get("content")
        if role not in {"user", "assistant"}:
            continue
        if not isinstance(content, str):
            continue
        text = _repair_text(content.strip())
        if not text:
            continue
        clean_history.append({"role": role, "content": text})
    return clean_history[-history_limit:]


def load_memory_store(
    memory_path: Path,
    history_limit: int = DEFAULT_HISTORY_LIMIT,
) -> dict[str, object]:
    if not memory_path.exists():
        return default_memory_store()

    try:
        raw = memory_path.read_text(encoding="utf-8").strip()
        if not raw:
            return default_memory_store()
        parsed = json.loads(raw)
    except Exception:
        return default_memory_store()

    if not isinstance(parsed, dict):
        return default_memory_store()

    return {
        "history": _sanitize_history(parsed.get("history", []), history_limit),
        "user": normalize_user_profile(parsed.get("user", {})),
        "long_term": parsed.get("long_term", {}),
    }


def save_memory_store(
    memory_path: Path,
    memory_store: dict[str, object],
    history_limit: int = DEFAULT_HISTORY_LIMIT,
) -> dict[str, object]:
    safe_store = {
        "history": _sanitize_history(memory_store.get("history", []), history_limit),
        "user": normalize_user_profile(memory_store.get("user", {})),
        "long_term": memory_store.get("long_term", {}),
    }

    try:
        memory_path.parent.mkdir(parents=True, exist_ok=True)
        memory_path.write_text(
            json.dumps(safe_store, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception:
        pass

    return safe_store


def append_history(
    memory_store: dict[str, object],
    role: str,
    content: str,
    history_limit: int = DEFAULT_HISTORY_LIMIT,
) -> None:
    history = memory_store.setdefault("history", [])
    if not isinstance(history, list):
        history = []
        memory_store["history"] = history

    text = _repair_text(content.strip())
    if not text:
        return

    history.append({"role": role, "content": text})
    memory_store["history"] = history[-history_limit:]
    memory_store["user"] = normalize_user_profile(memory_store.get("user", {}))
