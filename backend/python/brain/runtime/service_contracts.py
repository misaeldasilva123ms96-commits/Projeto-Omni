from __future__ import annotations

from typing import Any


def validate_start_task_request(*, user_id: str, session_id: str, message: str) -> dict[str, Any]:
    normalized_user_id = str(user_id or "").strip()
    normalized_session_id = str(session_id or "").strip()
    normalized_message = str(message or "").strip()
    if not normalized_user_id:
        raise ValueError("user_id is required")
    if not normalized_session_id:
        raise ValueError("session_id is required")
    if not normalized_message:
        raise ValueError("message is required")
    return {
        "user_id": normalized_user_id,
        "session_id": normalized_session_id,
        "message": normalized_message,
    }


def build_task_envelope(*, user_id: str, session_id: str, task_id: str, response: str) -> dict[str, Any]:
    return {
        "status": "completed",
        "user_id": user_id,
        "session_id": session_id,
        "task_id": task_id,
        "response": response,
        "links": {
            "inspect_task": {"task_id": task_id, "session_id": session_id},
            "latest_transcript": {"session_id": session_id},
            "inspect_hierarchy": {"task_id": task_id, "session_id": session_id},
            "inspect_learning": {"task_id": task_id, "session_id": session_id},
        },
    }


def build_task_status(*, run_id: str, checkpoint: dict[str, Any]) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "task_id": checkpoint.get("task_id"),
        "session_id": checkpoint.get("session_id"),
        "status": checkpoint.get("status", "unknown"),
        "next_step_index": checkpoint.get("next_step_index", 0),
        "total_actions": checkpoint.get("total_actions", 0),
        "plan_hierarchy": checkpoint.get("plan_hierarchy"),
        "reflection_available": bool(checkpoint.get("reflection_summary")),
        "operator_links": {
            "inspect_checkpoint": {"run_id": run_id},
            "inspect_policy": {"run_id": run_id},
            "inspect_learning": {"run_id": run_id},
        },
    }
