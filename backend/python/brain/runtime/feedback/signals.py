from __future__ import annotations

import re
from typing import Any

from brain.runtime.feedback.feedback_models import ExplicitFeedback


def parse_explicit_feedback(raw: dict[str, Any] | None) -> ExplicitFeedback | None:
    if not isinstance(raw, dict) or not raw:
        return None
    thumb = raw.get("thumb")
    thumb_s = str(thumb).strip().lower() if thumb is not None else ""
    if thumb_s not in ("", "up", "down"):
        thumb_s = ""
    rating = raw.get("rating")
    rf: float | None = None
    if isinstance(rating, (int, float)):
        rf = float(rating)
    elif isinstance(rating, str) and rating.strip():
        try:
            rf = float(rating.strip())
        except ValueError:
            rf = None
    tc = raw.get("task_completed")
    task_done: bool | None = None
    if isinstance(tc, bool):
        task_done = tc
    elif isinstance(tc, str):
        task_done = tc.strip().lower() in ("1", "true", "yes")
    corr = raw.get("user_correction")
    correction = str(corr).strip()[:2000] if isinstance(corr, str) else None
    if not thumb_s and rf is None and task_done is None and not correction:
        return None
    return ExplicitFeedback(
        thumb=thumb_s or None,
        rating=rf,
        task_completed=task_done,
        user_correction=correction,
    )


def derive_implicit_signals(
    *,
    message: str,
    history: list[dict[str, Any]],
) -> list[str]:
    """Heuristic implicit tags from user text + recent turns (no network)."""
    tags: list[str] = []
    m = str(message or "").strip().lower()
    if not m:
        return tags

    redo_terms = (
        "tente de novo",
        "de novo",
        "refaz",
        "corrija",
        "corrigir",
        "errado",
        "nao entendi",
        "não entendi",
        "redo",
        "try again",
        "fix it",
        "wrong",
        "incorrect",
    )
    if any(t in m for t in redo_terms):
        tags.append("retry_or_correct")

    if re.search(r"\b(refaça|refaca|reformule|rewrite|rephrase)\b", m):
        tags.append("redo_language")

    productive = (
        "continue",
        "proximo",
        "próximo",
        "next step",
        "and then",
        "e depois",
    )
    if any(t in m for t in productive):
        tags.append("productive_continuation")

    last_roles = [str(it.get("role", "")).lower() for it in history[-3:] if isinstance(it, dict)]
    if last_roles.count("assistant") >= 1 and last_roles[-1:] == ["user"] and len(m) < 120:
        if any(t in m for t in ("sim", "ok", "certo", "perfeito", "thanks", "valeu")):
            tags.append("short_affirmation_after_assistant")

    return tags
