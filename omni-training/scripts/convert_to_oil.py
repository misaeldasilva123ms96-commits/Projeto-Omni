from __future__ import annotations

import argparse
import sys
from pathlib import Path

LIB_DIR = Path(__file__).resolve().parents[1] / "lib"
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

from dataset_pipeline import read_records, save_report, write_records
from oil_adapter import convert_text_to_oil


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert normalized dataset into OIL-enriched JSONL.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    records = read_records(Path(args.input))
    converted: list[dict[str, object]] = []
    for record in records:
        text = "\n".join(
            part for part in (str(record.get("instruction", "")), str(record.get("input", ""))) if part.strip()
        )
        oil_payload = convert_text_to_oil(text)
        converted.append({**record, "oil": oil_payload})
    write_records(Path(args.output), converted)
    save_report(
        Path(__file__).resolve().parents[1] / "reports" / f"{Path(args.output).stem}.oil.json",
        step="convert_to_oil",
        source=str(Path(args.input).name),
        stats={
            "total_converted": len(converted),
            "total_discarded": 0,
            "input_path": args.input,
            "output_path": args.output,
        },
    )
    print(f"Converted {len(converted)} records into OIL at {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
