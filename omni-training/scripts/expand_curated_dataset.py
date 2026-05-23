from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

LIB_DIR = Path(__file__).resolve().parents[1] / "lib"
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

from common import write_json  # noqa: E402
from curation_helpers import export_curated_drafts  # noqa: E402
from training_utils import resolve_training_path  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Expand the curated review queue with structured Omni drafts.")
    parser.add_argument("--per-category", type=int, default=4)
    parser.add_argument("--output", default=str(Path(__file__).resolve().parents[1] / "data" / "review_queue" / "curated_expansion_drafts.jsonl"))
    parser.add_argument("--report", default=str(Path(__file__).resolve().parents[1] / "reports" / "curated_expansion_report.json"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_path = resolve_training_path(args.output)
    report_path = resolve_training_path(args.report)
    count = export_curated_drafts(output_path, per_category=max(1, int(args.per_category)))
    report = {
        "record_count": count,
        "output_path": str(output_path),
        "review_queue": True,
    }
    write_json(report_path, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
