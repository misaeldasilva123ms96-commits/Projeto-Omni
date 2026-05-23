from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

LIB_DIR = Path(__file__).resolve().parents[1] / "lib"
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

from common import read_jsonl, write_json  # noqa: E402
from dataset_quality import evaluate_dataset_records  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate Omni dataset quality and OIL alignment.")
    parser.add_argument("--input", default=str(Path(__file__).resolve().parents[1] / "data" / "curated" / "omni_seed_dataset.jsonl"))
    parser.add_argument("--output", default=str(Path(__file__).resolve().parents[1] / "reports" / "dataset_evaluation.json"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    records = read_jsonl(Path(args.input))
    report = evaluate_dataset_records(records)
    write_json(Path(args.output), report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

