from __future__ import annotations

import json
import sys
from pathlib import Path


def _resolve_repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _load_query_engine():
    repo_root = _resolve_repo_root()
    claw_root = repo_root / "claw-code-main"
    if not claw_root.exists():
        raise FileNotFoundError(f"claw-code-main nao encontrado em: {claw_root}")

    sys.path.insert(0, str(claw_root))
    sys.path.insert(0, str(repo_root))

    from src.query_engine import QueryEnginePort  # type: ignore

    return QueryEnginePort


def run(message: str) -> dict[str, object]:
    QueryEnginePort = _load_query_engine()
    engine = QueryEnginePort.from_workspace()
    result = engine.submit_message(message)

    return {
        "response": result.output,
        "session_id": engine.session_id,
        "source": "python-query-engine",
        "matched_commands": list(result.matched_commands),
        "matched_tools": list(result.matched_tools),
        "stop_reason": result.stop_reason,
        "usage": {
            "input_tokens": result.usage.input_tokens,
            "output_tokens": result.usage.output_tokens,
        },
    }


def main() -> int:
    if len(sys.argv) < 2:
        print(json.dumps({"error": "payload ausente"}))
        return 1

    try:
        payload = json.loads(sys.argv[1])
        message = str(payload.get("message", "")).strip()
        if not message:
            print(json.dumps({"error": "message obrigatoria"}))
            return 1

        response = run(message)
        print(json.dumps(response, ensure_ascii=False))
        return 0
    except Exception as exc:  # pragma: no cover - runtime boundary
        print(json.dumps({"error": str(exc)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
