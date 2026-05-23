from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

LIB_DIR = Path(__file__).resolve().parents[1] / "lib"
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

from auto_review import classify_examples, summarize_review  # noqa: E402
from common import read_jsonl, write_json, write_jsonl  # noqa: E402
from training_utils import resolve_training_path  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Classify generated Omni dataset examples as keep/review/reject.")
    parser.add_argument("--input", default=str(Path(__file__).resolve().parents[1] / "data" / "review_queue" / "curated_expansion_drafts.jsonl"))
    parser.add_argument("--output", default=str(Path(__file__).resolve().parents[1] / "data" / "review_queue" / "classified_examples.jsonl"))
    parser.add_argument("--report", default=str(Path(__file__).resolve().parents[1] / "reports" / "auto_review_report.json"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_path = resolve_training_path(args.input)
    output_path = resolve_training_path(args.output)
    report_path = resolve_training_path(args.report)
    records = read_jsonl(input_path)
    classified = classify_examples(records)
    write_jsonl(output_path, classified)
    report = summarize_review(classified)
    report["input_path"] = str(input_path)
    report["output_path"] = str(output_path)
    write_json(report_path, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
