from __future__ import annotations

import argparse
import sys
from pathlib import Path

LIB_DIR = Path(__file__).resolve().parents[1] / "lib"
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

from dataset_pipeline import filter_raw_records, load_normalization_rules, read_records, save_report, write_records


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Filter raw dataset records before normalization.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--rules", default=str(Path(__file__).resolve().parents[1] / "configs" / "normalization_rules.json"))
    parser.add_argument("--source", default="filtered_dataset")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)
    rules = load_normalization_rules(Path(args.rules))
    records = read_records(input_path)
    filtered, stats = filter_raw_records(records, rules)
    write_records(output_path, filtered)
    save_report(
        Path(__file__).resolve().parents[1] / "reports" / f"{output_path.stem}.filter.json",
        step="filter_dataset",
        source=args.source,
        stats={**stats, "input_path": str(input_path), "output_path": str(output_path)},
    )
    print(f"Filtered {stats['total_filtered']} / {stats['total_raw']} records into {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
