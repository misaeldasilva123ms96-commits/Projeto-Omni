from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from brain.runtime.orchestrator import (
    BrainOrchestrator,
    BrainPaths,
    BrainRequest,
    FeedbackRequest,
)


def _chat_request_from_args(args: list[str]) -> BrainRequest:
    message = args[0] if args else ""
    return BrainRequest(
        message=message,
        user_id=os.getenv("AI_USER_ID", "").strip(),
        session_id=os.getenv("AI_SESSION_ID", "").strip(),
        turn_id=os.getenv("OMINI_TURN_ID", "").strip(),
    )


def _feedback_request_from_env() -> FeedbackRequest:
    return FeedbackRequest(
        turn_id=os.getenv("OMINI_TURN_ID", "").strip(),
        value=os.getenv("OMINI_FEEDBACK_VALUE", "").strip(),
        text=os.getenv("OMINI_FEEDBACK_TEXT", "").strip(),
        user_id=os.getenv("AI_USER_ID", "").strip(),
        session_id=os.getenv("AI_SESSION_ID", "").strip(),
    )


def run_cli(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    orchestrator = BrainOrchestrator(BrainPaths.from_entrypoint(Path(__file__)))

    if args and args[0] == "--feedback":
        result = orchestrator.submit_feedback(_feedback_request_from_env())
        print(json.dumps(result, ensure_ascii=False))
        return 0

    result = orchestrator.run_request(_chat_request_from_args(args))
    print(result.get("response", ""))
    return 0
