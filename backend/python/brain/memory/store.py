from __future__ import annotations

import json
from pathlib import Path


DEFAULT_HISTORY_LIMIT = 6


def default_memory_store() -> dict[str, object]:
    return {
        "history": [],
        "user": {
            "nome": "",
            "preferencias": [],
        },
        "long_term": {},
    }


def load_memory_store(memory_path: Path, history_limit: int = DEFAULT_HISTORY_LIMIT) -> dict[str, object]:
    if not memory_path.exists():
        return default_memory_store()

    try:
        raw = memory_path.read_text(encoding="utf-8").strip()
        if not raw:
            return default_memory_store()
        parsed = json.loads(raw)
        if not isinstance(parsed, dict):
            return default_memory_store()
        history = parsed.get("history")
        user = parsed.get("user")
        if not isinstance(history, list):
            history = []
        if not isinstance(user, dict):
            user = {"nome": "", "preferencias": []}

        clean_history: list[dict[str, str]] = []
        for item in history:
            if not isinstance(item, dict):
                continue
            role = item.get("role")
            content = item.get("content")
            if role not in {"user", "assistant"}:
                continue
            if not isinstance(content, str) or not content.strip():
                continue
            clean_history.append({"role": role, "content": content.strip()})

        nome = user.get("nome", "")
        preferencias = user.get("preferencias", [])
        if not isinstance(nome, str):
            nome = ""
        if not isinstance(preferencias, list):
            preferencias = []

        return {
            "history": clean_history[-history_limit:],
            "user": {
                "nome": nome.strip(),
                "preferencias": [str(value).strip() for value in preferencias if str(value).strip()],
            },
            "long_term": parsed.get("long_term", {}),
        }
    except Exception:
        return default_memory_store()


def save_memory_store(memory_path: Path, memory_store: dict[str, object], history_limit: int = DEFAULT_HISTORY_LIMIT) -> dict[str, object]:
    history = memory_store.get("history", [])
    user = memory_store.get("user", {})
    if not isinstance(history, list):
        history = []
    if not isinstance(user, dict):
        user = {"nome": "", "preferencias": []}

    safe_history: list[dict[str, str]] = []
    for item in history[-history_limit:]:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        content = item.get("content")
        if role not in {"user", "assistant"}:
            continue
        if not isinstance(content, str) or not content.strip():
            continue
        safe_history.append({"role": role, "content": content.strip()})

    nome = user.get("nome", "")
    preferencias = user.get("preferencias", [])
    if not isinstance(nome, str):
        nome = ""
    if not isinstance(preferencias, list):
        preferencias = []

    safe_store = {
        "history": safe_history[-history_limit:],
        "user": {
            "nome": nome.strip(),
            "preferencias": [str(value).strip() for value in preferencias if str(value).strip()],
        },
        "long_term": memory_store.get("long_term", {}),
    }

    try:
        memory_path.write_text(
            json.dumps(safe_store, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception:
        pass

    return safe_store


def append_history(memory_store: dict[str, object], role: str, content: str, history_limit: int = DEFAULT_HISTORY_LIMIT) -> None:
    history = memory_store.setdefault("history", [])
    if not isinstance(history, list):
        history = []
        memory_store["history"] = history

    text = content.strip()
    if not text:
        return

    history.append({"role": role, "content": text})
    memory_store["history"] = history[-history_limit:]
