from __future__ import annotations

import argparse
import sys
from pathlib import Path

LIB_DIR = Path(__file__).resolve().parents[1] / "lib"
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

from dataset_pipeline import load_normalization_rules, normalize_records, read_records, save_report, write_records


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Normalize filtered dataset records into Omni canonical schema.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--rules", default=str(Path(__file__).resolve().parents[1] / "configs" / "normalization_rules.json"))
    parser.add_argument("--source", default="normalized_dataset")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    records = read_records(Path(args.input))
    rules = load_normalization_rules(Path(args.rules))
    normalized, stats = normalize_records(records, source=args.source, rules=rules)
    write_records(Path(args.output), normalized)
    save_report(
        Path(__file__).resolve().parents[1] / "reports" / f"{Path(args.output).stem}.normalize.json",
        step="normalize_dataset",
        source=args.source,
        stats={**stats, "input_path": args.input, "output_path": args.output},
    )
    print(f"Normalized {stats['total_normalized']} records into {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
