"""Offline maintenance CLI for explicit human approval manifests."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.external.approval import (  # noqa: E402
    ApprovalError,
    HumanReviewChecklist,
    create_human_approval_manifest,
    load_json_file,
    load_manifest,
    load_proposal,
    verify_approval_against_proposal,
    write_json,
)


def _proposal(path: str):
    return load_proposal(load_json_file(path))


def _review(proposal) -> None:
    payload = {
        "proposal_id": proposal.proposal_id,
        "proposal_format_version": proposal.proposal_format_version,
        "candidate_id": proposal.candidate_id,
        "canonical_schema_sha256": proposal.canonical_schema_sha256,
        "servers": [
            {
                "scheme": item.scheme,
                "hostname": item.hostname,
                "port": item.port,
                "base_path": item.base_path,
                "templated": item.templated,
            }
            for item in proposal.declared_servers
        ],
        "operations": [
            {
                "operation_key": f"{item.method} {item.path}",
                "operation_id": item.operation_id,
                "security_mode": item.security_mode,
                "mutating_signal": item.mutating_signal,
            }
            for item in proposal.operations
        ],
        "risk_signals": proposal.risk_signals,
        "issues": proposal.issues,
        "review_blockers": proposal.review_blockers,
        "required_checklist": (
            "terms",
            "security",
            "privacy",
            "cost",
            "rate_limit",
            "provider_documentation",
            "implementation_scope",
        ),
    }
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Offline external API human approval")
    commands = parser.add_subparsers(dest="command", required=True)
    review = commands.add_parser("review")
    review.add_argument("--proposal-file", required=True)
    approve = commands.add_parser("approve")
    approve.add_argument("--proposal-file", required=True)
    approve.add_argument("--reviewed-by", required=True)
    approve.add_argument("--confirm-server-host", required=True)
    approve.add_argument("--operation", action="append", default=[])
    approve.add_argument("--approve-terms", action="store_true")
    approve.add_argument("--approve-security", action="store_true")
    approve.add_argument("--approve-privacy", action="store_true")
    approve.add_argument("--approve-cost", action="store_true")
    approve.add_argument("--approve-rate-limit", action="store_true")
    approve.add_argument("--approve-provider-docs", action="store_true")
    approve.add_argument("--approve-implementation-scope", action="store_true")
    approve.add_argument("--ack-blocker", action="append", default=[])
    approve.add_argument("--ack-mutating", action="append", default=[])
    approve.add_argument("--ack-security-exception", action="append", default=[])
    approve.add_argument("--output", required=True)
    verify = commands.add_parser("verify")
    verify.add_argument("--proposal-file", required=True)
    verify.add_argument("--manifest", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        proposal = _proposal(args.proposal_file)
        if args.command == "review":
            _review(proposal)
        elif args.command == "approve":
            checklist = HumanReviewChecklist(
                args.approve_terms,
                args.approve_security,
                args.approve_privacy,
                args.approve_cost,
                args.approve_rate_limit,
                args.approve_provider_docs,
                args.approve_implementation_scope,
            )
            manifest = create_human_approval_manifest(
                proposal,
                reviewed_by=args.reviewed_by,
                confirm_server_host=args.confirm_server_host,
                selected_operations=tuple(args.operation),
                review_checklist=checklist,
                acknowledged_review_blockers=tuple(args.ack_blocker),
                acknowledged_mutating_operations=tuple(args.ack_mutating),
                acknowledged_security_exceptions=tuple(args.ack_security_exception),
            )
            write_json(Path(args.output), manifest.as_dict())
            print(manifest.approval_id)
        else:
            manifest = load_manifest(load_json_file(args.manifest))
            verify_approval_against_proposal(manifest, proposal)
            print(manifest.approval_id)
    except ApprovalError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
