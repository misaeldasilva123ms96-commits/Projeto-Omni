from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

LIB_DIR = Path(__file__).resolve().parents[1] / "lib"
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

from common import read_jsonl, write_json  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate decision-ranking quality from runtime logs.")
    parser.add_argument("--input", default=str(Path(__file__).resolve().parents[2] / ".logs" / "fusion-runtime" / "execution-audit.jsonl"))
    parser.add_argument("--output", default=str(Path(__file__).resolve().parents[1] / "reports" / "decision_evaluation.json"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    records = read_jsonl(Path(args.input))
    ambiguous_case_count = 0
    ranking_applied_count = 0
    deterministic_win = 0
    model_assist_win = 0
    fallback_count = 0
    total_confidence = 0.0
    confidence_count = 0
    unsafe_override_count = 0
    review_required_count = 0

    for record in records:
        event_type = str(record.get("event_type", "") or "")
        payload = dict(record.get("payload") or {})
        if event_type == "runtime.decision.ambiguity":
            ambiguous_case_count += 1
        if event_type == "runtime.decision.ranking.applied":
            ranking_applied_count += 1
            confidence = float(payload.get("ranked_confidence", 0.0) or 0.0)
            total_confidence += confidence
            confidence_count += 1
            if str(payload.get("selected_strategy", "") or "") == str(payload.get("deterministic_strategy", "") or ""):
                deterministic_win += 1
            if str(payload.get("decision_source", "") or "").startswith("hybrid"):
                model_assist_win += 1
            if bool(payload.get("review_required", False)):
                review_required_count += 1
            if bool(payload.get("unsafe_override", False)):
                unsafe_override_count += 1
        if event_type == "runtime.decision_ranking.fallback":
            fallback_count += 1

    report = {
        "ambiguous_case_count": ambiguous_case_count,
        "ranking_applied_count": ranking_applied_count,
        "deterministic_win_rate": round(deterministic_win / max(1, ranking_applied_count), 4),
        "model_assist_win_rate": round(model_assist_win / max(1, ranking_applied_count), 4),
        "fallback_rate": round(fallback_count / max(1, ambiguous_case_count), 4),
        "average_selected_confidence": round(total_confidence / max(1, confidence_count), 4),
        "unsafe_override_count": unsafe_override_count,
        "review_required_count": review_required_count,
    }
    write_json(Path(args.output), report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

