"""Read-only maintenance CLI for governed discovery candidates."""

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
    build_review_dossier,
    search_candidates,
)
from brain.runtime.external.gateway import ExternalAPIGateway  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Review discovery-only external API candidates")
    parser.add_argument("--source", required=True, choices=("apis-guru", "public-apis"))
    parser.add_argument("--query", default="")
    parser.add_argument("--category")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--format", choices=("json", "text"), default="text")
    args = parser.parse_args()
    client = DiscoveryClient(ExternalAPIGateway(registry=build_discovery_source_registry()))
    candidates = client.load(args.source)
    results = search_candidates(candidates, args.query, category=args.category, limit=args.limit)
    dossiers = [
        build_review_dossier(result.candidate).as_dict()
        | {"relevance_score": result.relevance_score}
        for result in results
    ]
    if args.format == "json":
        print(json.dumps(dossiers, indent=2, ensure_ascii=False))
    else:
        for dossier in dossiers:
            candidate = dossier["candidate"]
            print(f"{candidate['candidate_id']}  {candidate['name']}  [{candidate['source']}]")
            print("  manual review required; execution_authorized=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
