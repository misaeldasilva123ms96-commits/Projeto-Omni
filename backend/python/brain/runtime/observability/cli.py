from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .observability_reader import ObservabilityReader


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="observability-cli")
    parser.add_argument("--root", default=None)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("snapshot")

    traces = subparsers.add_parser("traces")
    traces.add_argument("--limit", type=int, default=10)

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
                "goals": [],
                "simulations": [],
            }
        )
    return _emit({"status": "error", "error": "unsupported_command"})


if __name__ == "__main__":
    raise SystemExit(main())
