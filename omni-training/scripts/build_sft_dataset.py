from __future__ import annotations

import argparse
import sys
from pathlib import Path

LIB_DIR = Path(__file__).resolve().parents[1] / "lib"
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

from dataset_pipeline import read_records, save_report, write_records
from sft_builder import (
    build_sft_record_from_curated,
    build_sft_record_from_public,
    build_sft_report,
    filter_sft_records,
    split_sft_records,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Omni SFT JSONL from OIL-enriched and curated datasets.")
    parser.add_argument("--public-input", default="")
    parser.add_argument("--curated-input", default=str(Path(__file__).resolve().parents[1] / "data" / "curated" / "omni_seed_dataset.jsonl"))
    parser.add_argument("--output", required=True)
    parser.add_argument("--min-quality-score", type=float, default=0.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    records: list[dict[str, object]] = []
    public_count = 0
    curated_count = 0
    if args.public_input:
        for record in read_records(Path(args.public_input)):
            records.append(build_sft_record_from_public(record))
            public_count += 1
    if args.curated_input and Path(args.curated_input).exists():
        for record in read_records(Path(args.curated_input)):
            records.append(build_sft_record_from_curated(record))
            curated_count += 1
    records = filter_sft_records(records, min_quality_score=args.min_quality_score)
    write_records(Path(args.output), records)
    splits = split_sft_records(records)
    output_path = Path(args.output)
    write_records(output_path.with_name("train.jsonl"), splits["train"])
    write_records(output_path.with_name("validation.jsonl"), splits["validation"])
    write_records(output_path.with_name("test.jsonl"), splits["test"])
    save_report(
        Path(__file__).resolve().parents[1] / "reports" / f"{Path(args.output).stem}.sft.json",
        step="build_sft_dataset",
        source="omni-training",
        stats={
            "total_converted": len(records),
            "public_examples": public_count,
            "curated_examples": curated_count,
            "output_path": args.output,
            "splits": {key: len(value) for key, value in splits.items()},
            "report": build_sft_report(records),
        },
    )
    print(f"Built {len(records)} SFT rows into {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
