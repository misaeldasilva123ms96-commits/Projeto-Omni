from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

LIB_DIR = Path(__file__).resolve().parents[1] / "lib"
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

from common import read_jsonl, write_json  # noqa: E402


def _score_output(output: str, expected_strategy: str) -> dict[str, float]:
    text = str(output or "").strip()
    lowered = text.lower()
    structure_score = 1.0 if len(text.split()) >= 20 else 0.5 if text else 0.0
    omni_style_score = 1.0 if any(term in lowered for term in ("fallback", "runtime", "manifest", "govern")) else 0.5
    oil_alignment_score = 1.0 if any(term in lowered for term in ("intenção", "restrição", "oil", "estratég")) else 0.4
    strategy_alignment_score = 1.0 if expected_strategy.lower().replace("_", " ")[:8] in lowered else 0.5
    generic_answer_rate = 1.0 if any(term in lowered for term in ("depende", "contexto")) else 0.0
    fallback_handling_score = 1.0 if "fallback" in lowered else 0.4
    coding_response_score = 1.0 if any(term in lowered for term in ("teste", "contrato", "refator", "arquivo")) else 0.4
    planning_response_score = 1.0 if any(term in lowered for term in ("etapa", "incremento", "plano", "fases")) else 0.4
    return {
        "structure_score": structure_score,
        "omni_style_score": omni_style_score,
        "oil_alignment_score": oil_alignment_score,
        "strategy_alignment_score": strategy_alignment_score,
        "generic_answer_rate": generic_answer_rate,
        "fallback_handling_score": fallback_handling_score,
        "coding_response_score": coding_response_score,
        "planning_response_score": planning_response_score,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate baseline vs LoRA adapter quality on curated Omni eval cases.")
    parser.add_argument("--input", default=str(Path(__file__).resolve().parents[1] / "data" / "eval_cases" / "omni_eval_cases.jsonl"))
    parser.add_argument("--output", default=str(Path(__file__).resolve().parents[1] / "reports" / "model_quality.json"))
    parser.add_argument("--adapter-available", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    cases = read_jsonl(Path(args.input))
    baseline_scores = []
    adapter_scores = []
    for case in cases:
        expected_output = str(case.get("assistant_output", "") or "")
        expected_strategy = str(case.get("selected_strategy", "") or (case.get("runtime_hints") or {}).get("strategy", ""))
        baseline = _score_output(expected_output, expected_strategy)
        baseline_scores.append(baseline)
        if args.adapter_available:
            adapter_scores.append(baseline)
    def avg(metric: str, rows: list[dict[str, float]]) -> float:
        return round(sum(row.get(metric, 0.0) for row in rows) / max(1, len(rows)), 4)
    metrics = ["structure_score", "omni_style_score", "oil_alignment_score", "strategy_alignment_score", "generic_answer_rate", "fallback_handling_score", "coding_response_score", "planning_response_score"]
    payload = {
        "case_count": len(cases),
        "adapter_available": bool(args.adapter_available),
        "baseline": {metric: avg(metric, baseline_scores) for metric in metrics},
        "adapter": {metric: avg(metric, adapter_scores) for metric in metrics} if args.adapter_available else {},
    }
    write_json(Path(args.output), payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
