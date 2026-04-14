from __future__ import annotations

import argparse
import json
from pathlib import Path

from brain.runtime.control import RunRegistry, RunStatus
from brain.runtime.memory import MemoryFacade


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="control-cli")
    parser.add_argument("--root", default=None)
    subparsers = parser.add_subparsers(dest="command", required=True)

    for action in ("pause", "resume", "approve", "show"):
        subparser = subparsers.add_parser(action)
        subparser.add_argument("run_id")

    list_parser = subparsers.add_parser("list")
    list_parser.add_argument("--limit", type=int, default=50)
    return parser


def _resolve_root(raw_root: str | None) -> Path:
    if raw_root:
        return Path(raw_root)
    return Path(__file__).resolve().parents[5]


def _emit(payload: dict[str, object]) -> int:
    print(json.dumps(payload, ensure_ascii=False))
    return 0


def _record_operator_event(root: Path, *, action: str, run_id: str) -> None:
    memory = MemoryFacade(root)
    try:
        memory.record_event(
            event_type="operator_control",
            description=f"Operator {action} run {run_id}",
            metadata={
                "action": action,
                "run_id": str(run_id),
                "operator": "supabase_user",
                "source": "control.cli",
            },
        )
    finally:
        memory.close()


def _update_run(root: Path, *, run_id: str, status: RunStatus, action: str) -> dict[str, object]:
    registry = RunRegistry(root)
    current = registry.get(run_id)
    if current is None:
        return {"status": "error", "error": "run_not_found", "run": None}
    updated = registry.update_status(
        run_id=run_id,
        status=status,
        last_action=f"operator_{action}",
        progress=current.progress_score,
    )
    if updated is None:
        return {"status": "error", "error": "run_not_found", "run": None}
    _record_operator_event(root, action=action, run_id=run_id)
    return {"status": "ok", "action": action, "run": updated.as_dict()}


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()
    root = _resolve_root(args.root)
    registry = RunRegistry(root)

    if args.command == "pause":
        return _emit(_update_run(root, run_id=args.run_id, status=RunStatus.PAUSED, action="pause"))
    if args.command == "resume":
        return _emit(_update_run(root, run_id=args.run_id, status=RunStatus.RUNNING, action="resume"))
    if args.command == "approve":
        return _emit(_update_run(root, run_id=args.run_id, status=RunStatus.RUNNING, action="approve"))
    if args.command == "show":
        record = registry.get(args.run_id)
        if record is None:
            return _emit({"status": "error", "error": "run_not_found", "run": None})
        return _emit({"status": "ok", "run": record.as_dict()})
    if args.command == "list":
        runs = [item.as_dict() for item in registry.get_all(limit=max(1, args.limit))]
        return _emit({"status": "ok", "runs": runs})
    return _emit({"status": "error", "error": "unsupported_command"})


if __name__ == "__main__":
    raise SystemExit(main())
