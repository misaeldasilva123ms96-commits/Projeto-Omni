from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

LIB_DIR = Path(__file__).resolve().parents[1] / "lib"
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

from ambiguity_examples import build_ambiguity_examples_from_runtime_logs  # noqa: E402
from common import read_jsonl, write_json, write_jsonl  # noqa: E402
from dataset_mixer import build_mix_report, mix_dataset_records  # noqa: E402
from execution_examples import build_execution_examples_from_runtime_logs  # noqa: E402
from runtime_harvesting import build_runtime_harvest_examples  # noqa: E402
from sft_builder import build_sft_record_from_curated, build_sft_record_from_public, build_sft_report, filter_sft_records, split_sft_records  # noqa: E402
from training_utils import resolve_training_path  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the final training-ready dataset with controlled source proportions.")
    parser.add_argument("--max-records", type=int, default=500)
    parser.add_argument("--min-quality-score", type=float, default=0.68)
    parser.add_argument("--report", default=str(Path(__file__).resolve().parents[1] / "reports" / "training_ready_dataset_report.json"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    training_root = Path(__file__).resolve().parents[1]
    project_root = training_root.parents[0]
    curated_records = read_jsonl(resolve_training_path(training_root / "data" / "curated" / "omni_curated_expanded.jsonl"))
    public_records = read_jsonl(resolve_training_path(training_root / "data" / "normalized" / "mixed_normalized.jsonl"))
    runtime_records = build_runtime_harvest_examples(project_root, limit=220)
    runtime_records.extend(build_execution_examples_from_runtime_logs(project_root, limit=80))
    runtime_records.extend(build_ambiguity_examples_from_runtime_logs(project_root, limit=60))
    synthetic_records = [
        record for record in read_jsonl(resolve_training_path(training_root / "data" / "review_queue" / "gap_examples.jsonl"))
        if str(record.get("source", "") or "") == "synthetic_controlled"
    ]

    combined = list(curated_records) + list(public_records) + list(runtime_records) + list(synthetic_records)
    mixed = mix_dataset_records(
        combined,
        max_records=max(1, int(args.max_records)),
        source_quota={
            "runtime_harvest": int(args.max_records * 0.40),
            "runtime_execution": int(args.max_records * 0.15),
            "internal_curated": int(args.max_records * 0.30),
            "synthetic_controlled": int(args.max_records * 0.10),
            "default_small_instruction": int(args.max_records * 0.20),
            "pt_instruction_seed": int(args.max_records * 0.10),
        },
    )
    sft_records = []
    for record in mixed:
        if "instruction" in record or "output" in record:
            sft_records.append(build_sft_record_from_public(record))
        else:
            sft_records.append(build_sft_record_from_curated(record))
    sft_records = filter_sft_records(sft_records, min_quality_score=float(args.min_quality_score))
    splits = split_sft_records(sft_records)
    write_jsonl(training_root / "data" / "sft" / "train.jsonl", splits["train"])
    write_jsonl(training_root / "data" / "sft" / "validation.jsonl", splits["validation"])
    write_jsonl(training_root / "data" / "sft" / "test.jsonl", splits["test"])
    report = {
        "mixed": build_mix_report(mixed),
        "sft": build_sft_report(sft_records),
        "splits": {key: len(value) for key, value in splits.items()},
    }
    write_json(resolve_training_path(args.report), report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
