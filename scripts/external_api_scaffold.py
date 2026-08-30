"""Offline writer for non-executable external API review scaffolds."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.external.approval import (  # noqa: E402
    ApprovalError,
    create_non_executable_scaffold,
    load_json_file,
    load_manifest,
    load_proposal,
    write_scaffold_artifacts,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate an inert provider review scaffold")
    parser.add_argument("--proposal-file", required=True)
    parser.add_argument("--approval-file", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)
    try:
        proposal = load_proposal(load_json_file(args.proposal_file))
        manifest = load_manifest(load_json_file(args.approval_file))
        scaffold = create_non_executable_scaffold(manifest, proposal)
        write_scaffold_artifacts(args.output_dir, scaffold)
        print(scaffold.scaffold_id)
    except ApprovalError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
