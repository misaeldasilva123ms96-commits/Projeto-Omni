from __future__ import annotations

import argparse
import sys
from pathlib import Path

LIB_DIR = Path(__file__).resolve().parents[1] / "lib"
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

from common import read_json, slugify
from dataset_pipeline import save_report, write_records


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download a Hugging Face dataset slice into raw JSONL.")
    parser.add_argument("--dataset-key", default="default_small", help="Key inside dataset_sources.json")
    parser.add_argument("--config-path", default=str(Path(__file__).resolve().parents[1] / "configs" / "dataset_sources.json"))
    parser.add_argument("--output", default="", help="Optional output JSONL path")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config_path = Path(args.config_path)
    config = read_json(config_path)
    if args.dataset_key not in config:
        raise SystemExit(f"dataset key not found: {args.dataset_key}")
    source_cfg = config[args.dataset_key]
    try:
        from datasets import load_dataset
    except Exception as exc:  # pragma: no cover
        raise SystemExit(f"datasets library is required: {exc}") from exc

    dataset_name = str(source_cfg["dataset_name"])
    dataset_config = source_cfg.get("dataset_config")
    split = str(source_cfg.get("split") or "train[:128]")
    revision = source_cfg.get("revision")
    output_path = Path(args.output) if args.output else Path(__file__).resolve().parents[1] / "data" / "raw" / f"{slugify(args.dataset_key)}.jsonl"

    dataset = load_dataset(dataset_name, name=dataset_config, split=split, revision=revision, streaming=bool(source_cfg.get("streaming", False)))
    records = [dict(row) for row in dataset]
    write_records(output_path, records)
    report_path = Path(__file__).resolve().parents[1] / "reports" / f"{slugify(args.dataset_key)}.download.json"
    save_report(
        report_path,
        step="download_dataset",
        source=dataset_name,
        stats={"total_raw": len(records), "split": split, "output_path": str(output_path)},
    )
    print(f"Downloaded {len(records)} rows to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
