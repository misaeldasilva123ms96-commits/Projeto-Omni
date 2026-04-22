from __future__ import annotations

import argparse
import sys
from pathlib import Path

LIB_DIR = Path(__file__).resolve().parents[1] / "lib"
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

from common import slugify
from dataset_pipeline import save_report, write_records
from source_ingestion import ingest_source, load_dataset_sources


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download a Hugging Face dataset slice into raw JSONL.")
    parser.add_argument("--dataset-key", default="default_small", help="Key inside dataset_sources.json")
    parser.add_argument("--config-path", default=str(Path(__file__).resolve().parents[1] / "configs" / "dataset_sources.json"))
    parser.add_argument("--output", default="", help="Optional output JSONL path")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config_path = Path(args.config_path)
    sources = load_dataset_sources(config_path)
    source_cfg = next((source for source in sources if source.source_name == args.dataset_key), None)
    if source_cfg is None:
        raise SystemExit(f"dataset key not found: {args.dataset_key}")
    output_path = Path(args.output) if args.output else Path(__file__).resolve().parents[1] / "data" / "raw" / f"{slugify(args.dataset_key)}.jsonl"
    records = ingest_source(source_cfg, project_root=Path(__file__).resolve().parents[2])
    write_records(output_path, records)
    report_path = Path(__file__).resolve().parents[1] / "reports" / f"{slugify(args.dataset_key)}.download.json"
    save_report(
        report_path,
        step="download_dataset",
        source=source_cfg.source_name,
        stats={"total_raw": len(records), "split": source_cfg.split, "output_path": str(output_path)},
    )
    print(f"Downloaded {len(records)} rows to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
