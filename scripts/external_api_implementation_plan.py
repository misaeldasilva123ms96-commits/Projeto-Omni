"""Offline CLI for static, non-executable external API implementation plans."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.external.approval import (  # noqa: E402
    ApprovalError,
    load_json_file,
    load_manifest,
    load_proposal,
    load_scaffold,
)
from brain.runtime.external.implementation_plan import (  # noqa: E402
    build_static_provider_implementation_plan,
    verify_implementation_plan_against_inputs,
    write_implementation_plan_artifacts,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build an inert static implementation plan")
    parser.add_argument("--proposal-file", required=True)
    parser.add_argument("--approval-file", required=True)
    parser.add_argument("--scaffold-file", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)
    try:
        proposal = load_proposal(load_json_file(args.proposal_file))
        approval = load_manifest(load_json_file(args.approval_file))
        scaffold = load_scaffold(load_json_file(args.scaffold_file))
        plan = build_static_provider_implementation_plan(scaffold, approval, proposal)
        verify_implementation_plan_against_inputs(plan, scaffold, approval, proposal)
        write_implementation_plan_artifacts(args.output_dir, plan)
        print(plan.implementation_plan_id)
    except ApprovalError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
