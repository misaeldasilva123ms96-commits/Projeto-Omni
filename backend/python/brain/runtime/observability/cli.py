from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .observability_reader import ObservabilityReader
from .run_reader import (
    read_active_runs,
    read_recent_resolution_events,
    read_resolution_summary,
    read_run,
    read_runs,
    read_runs_waiting_operator,
    read_runs_with_rollback,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="observability-cli")
    parser.add_argument("--root", default=None)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("snapshot")

    traces = subparsers.add_parser("traces")
    traces.add_argument("--limit", type=int, default=10)

    runs = subparsers.add_parser("runs")
    runs.add_argument("--limit", type=int, default=50)
    inspect_run = subparsers.add_parser("inspect_run")
    inspect_run.add_argument("run_id")
    list_runs = subparsers.add_parser("list_runs")
    list_runs.add_argument("--limit", type=int, default=50)
    subparsers.add_parser("resolution_summary")
    waiting = subparsers.add_parser("runs_waiting_operator")
    waiting.add_argument("--limit", type=int, default=50)
    rollback = subparsers.add_parser("runs_with_rollback")
    rollback.add_argument("--limit", type=int, default=50)
    recent_resolution = subparsers.add_parser("recent_resolution_events")
    recent_resolution.add_argument("--limit", type=int, default=25)

    goal_history = subparsers.add_parser("goal_history")
    goal_history.add_argument("--limit", type=int, default=10)

    simulation_history = subparsers.add_parser("simulation_history")
    simulation_history.add_argument("--limit", type=int, default=10)
    simulation_history.add_argument("--goal-id", default=None)
    return parser


def _resolve_root(raw_root: str | None) -> Path:
    if raw_root:
        return Path(raw_root)
    return Path(__file__).resolve().parents[5]


def _emit(payload: dict[str, Any]) -> int:
    print(json.dumps(payload, ensure_ascii=False))
    return 0


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    try:
        reader = ObservabilityReader(_resolve_root(args.root))
        if args.command == "snapshot":
            return _emit({"status": "ok", "snapshot": reader.snapshot().as_dict()})
        if args.command == "traces":
            return _emit({"status": "ok", "traces": reader.trace_history(limit=max(1, args.limit))})
        if args.command == "runs":
            runs = read_active_runs(_resolve_root(args.root))
            return _emit({"status": "ok", "runs": runs[: max(1, args.limit)]})
        if args.command == "inspect_run":
            return _emit({"status": "ok", "run": read_run(_resolve_root(args.root), args.run_id)})
        if args.command == "list_runs":
            return _emit({"status": "ok", "runs": read_runs(_resolve_root(args.root), limit=max(1, args.limit))})
        if args.command == "resolution_summary":
            return _emit({"status": "ok", "summary": read_resolution_summary(_resolve_root(args.root))})
        if args.command == "runs_waiting_operator":
            runs = read_runs_waiting_operator(_resolve_root(args.root))
            return _emit({"status": "ok", "runs": runs[: max(1, args.limit)]})
        if args.command == "runs_with_rollback":
            runs = read_runs_with_rollback(_resolve_root(args.root))
            return _emit({"status": "ok", "runs": runs[: max(1, args.limit)]})
        if args.command == "recent_resolution_events":
            events = read_recent_resolution_events(_resolve_root(args.root), limit=max(1, args.limit))
            return _emit({"status": "ok", "events": events})
        if args.command == "goal_history":
            return _emit({"status": "ok", "goals": reader.goal_history(limit=max(1, args.limit))})
        if args.command == "simulation_history":
            return _emit(
                {
                    "status": "ok",
                    "simulations": reader.simulation_history(limit=max(1, args.limit), goal_id=args.goal_id),
                }
            )
    except Exception as error:
        return _emit(
            {
                "status": "error",
                "error": str(error),
                "snapshot": None,
                "traces": [],
                "runs": [],
                "run": None,
                "goals": [],
                "simulations": [],
                "summary": {},
                "events": [],
            }
        )
    return _emit({"status": "error", "error": "unsupported_command"})


if __name__ == "__main__":
    raise SystemExit(main())
