from __future__ import annotations

import argparse
import sys
from pathlib import Path

LIB_DIR = Path(__file__).resolve().parents[1] / "lib"
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

from common import write_json, write_jsonl  # noqa: E402
from curated_dataset_builder import build_curated_dataset  # noqa: E402
from dataset_enrichment import enrich_public_record  # noqa: E402
from dataset_mixer import build_mix_report, mix_dataset_records  # noqa: E402
from feedback_loop import build_feedback_examples_from_runtime_logs  # noqa: E402
from runtime_harvesting import build_runtime_harvest_examples  # noqa: E402
from sft_builder import (  # noqa: E402
    build_sft_record_from_curated,
    build_sft_record_from_public,
    build_sft_report,
    filter_sft_records,
    split_sft_records,
)
from source_ingestion import ingest_source, load_dataset_sources  # noqa: E402
from synthetic_examples import generate_synthetic_examples  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a mixed Omni dataset from multiple controlled sources.")
    parser.add_argument("--config", default=str(Path(__file__).resolve().parents[1] / "configs" / "dataset_sources.json"))
    parser.add_argument("--max-records", type=int, default=800)
    parser.add_argument("--min-quality-score", type=float, default=0.6)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    training_root = Path(__file__).resolve().parents[1]
    project_root = training_root.parents[0]
    sources = load_dataset_sources(Path(args.config))
    public_records: list[dict] = []
    curated_records: list[dict] = []
    source_stats: dict[str, int] = {}
    for source in sources:
        try:
            records = ingest_source(source, project_root=project_root)
        except Exception:
            records = []
        source_stats[source.source_name] = len(records)
        if source.source_type == "hf":
            public_records.extend([enrich_public_record(record) for record in records])
        else:
            curated_records.extend(records)
    curated_records.extend(build_curated_dataset())
    curated_records.extend(build_feedback_examples_from_runtime_logs(project_root, limit=80))
    curated_records.extend(build_runtime_harvest_examples(project_root, limit=80))
    curated_records.extend(generate_synthetic_examples(category="ambiguity_pairs", limit=32))
    curated_records.extend(generate_synthetic_examples(category="fallback_cases", limit=20))
    curated_records.extend(generate_synthetic_examples(category="governance_block_examples", limit=16))
    mixed_normalized = mix_dataset_records(
        public_records + curated_records,
        max_records=args.max_records,
        language_quota={"pt": int(args.max_records * 0.35), "pt-BR": int(args.max_records * 0.35)},
        task_family_quota={"runtime": 220, "coding": 180, "planning": 140, "governance": 120, "analysis": 140},
        source_quota={"synthetic_controlled": 96},
        source_minimums={"default_small_instruction": 40, "pt_instruction_seed": 20},
    )
    mixed_curated = [
        record
        for record in mixed_normalized
        if str(record.get("review_action", "") or "keep") != "reject"
    ]
    mixed_sft = []
    for record in mixed_curated:
        if "instruction" in record or "output" in record:
            mixed_sft.append(build_sft_record_from_public(record))
        elif "user_input" in record or "assistant_output" in record:
            mixed_sft.append(build_sft_record_from_curated(record))
    prefiltered_sft = list(mixed_sft)
    mixed_sft = filter_sft_records(
        mixed_sft,
        min_quality_score=args.min_quality_score,
        allowed_review_statuses={"approved", "reviewed", "draft"},
    )
    public_after_filter = [record for record in mixed_sft if str(record.get("source", "") or "").startswith("default_small_instruction") or str(record.get("source", "") or "").startswith("pt_instruction_seed")]
    if not public_after_filter:
        public_candidates = [
            build_sft_record_from_public(record)
            for record in mixed_normalized
            if (
                str(record.get("source", "") or "").startswith("default_small_instruction")
                or str(record.get("source", "") or "").startswith("pt_instruction_seed")
            )
        ]
        public_candidates.sort(key=lambda record: float(record.get("quality_score", 0.0) or 0.0), reverse=True)
        mixed_sft.extend(public_candidates[:24])
    splits = split_sft_records(mixed_sft)
    write_jsonl(training_root / "data" / "normalized" / "mixed_normalized.jsonl", mixed_normalized)
    write_jsonl(training_root / "data" / "oil" / "mixed_oil.jsonl", mixed_curated)
    write_jsonl(training_root / "data" / "sft" / "mixed_sft.jsonl", mixed_sft)
    write_jsonl(training_root / "data" / "sft" / "train.jsonl", splits["train"])
    write_jsonl(training_root / "data" / "sft" / "validation.jsonl", splits["validation"])
    write_jsonl(training_root / "data" / "sft" / "test.jsonl", splits["test"])
    report = {
        "source_ingestion": source_stats,
        "mixed_normalized": build_mix_report(mixed_normalized),
        "mixed_sft": build_sft_report(mixed_sft),
        "splits": {key: len(value) for key, value in splits.items()},
    }
    write_json(training_root / "reports" / "mixed_dataset_report.json", report)
    print(f"Built mixed dataset with {len(mixed_sft)} SFT rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
