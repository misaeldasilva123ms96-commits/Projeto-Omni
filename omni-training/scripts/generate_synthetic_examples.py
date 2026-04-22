from __future__ import annotations

import argparse
import sys
from pathlib import Path

LIB_DIR = Path(__file__).resolve().parents[1] / "lib"
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

from common import write_json  # noqa: E402
from synthetic_examples import export_synthetic_examples, generate_synthetic_examples  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate controlled synthetic Omni examples for narrow gaps.")
    parser.add_argument("--category", default="ambiguity_pairs")
    parser.add_argument("--limit", type=int, default=24)
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    examples = generate_synthetic_examples(category=args.category, limit=args.limit)
    output_path = Path(args.output)
    export_synthetic_examples(output_path, examples)
    write_json(
        Path(__file__).resolve().parents[1] / "reports" / f"{output_path.stem}.synthetic.json",
        {"category": args.category, "generated": len(examples), "output_path": str(output_path)},
    )
    print(f"Generated {len(examples)} synthetic controlled examples into {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
