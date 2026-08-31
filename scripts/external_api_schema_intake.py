"""Maintenance-only CLI for exact candidate-bound schema review proposals."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.external.discovery import (  # noqa: E402
    DiscoveryClient,
    build_discovery_source_registry,
)
from brain.runtime.external.gateway import ExternalAPIGateway  # noqa: E402
from brain.runtime.external.schema_intake import SchemaIntakeClient, SchemaIntakeError  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze one APIs.guru discovery schema")
    parser.add_argument("--candidate-id", required=True)
    parser.add_argument("--source", choices=("apis-guru",), default="apis-guru")
    parser.add_argument("--format", choices=("json", "text"), default="text")
    args = parser.parse_args()
    candidates = DiscoveryClient(
        ExternalAPIGateway(registry=build_discovery_source_registry())
    ).load(args.source)
    candidate = next((item for item in candidates if item.candidate_id == args.candidate_id), None)
    if candidate is None:
        raise SchemaIntakeError("candidate_not_found")
    proposal = SchemaIntakeClient().intake(candidate)
    if args.format == "json":
        print(json.dumps(proposal.as_dict(), indent=2, ensure_ascii=False))
    else:
        print(f"proposal: {proposal.proposal_id}")
        print(f"candidate: {proposal.candidate_id}")
        print(f"OpenAPI: {proposal.detected_openapi_version}")
        print(f"operations: {proposal.operation_count}")
        print("manual review required; execution_authorized=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
