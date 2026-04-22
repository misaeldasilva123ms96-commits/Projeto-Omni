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
    parser = argparse.ArgumentParser(description="Evaluate strategy execution quality from runtime logs.")
    parser.add_argument("--input", default=str(Path(__file__).resolve().parents[2] / ".logs" / "fusion-runtime" / "execution-audit.jsonl"))
    parser.add_argument("--output", default=str(Path(__file__).resolve().parents[1] / "reports" / "execution_evaluation.json"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    records = read_jsonl(Path(args.input))
    strategy_execution_count = 0
    executor_success_count = 0
    fallback_count = 0
    governance_block_count = 0
    downgrade_count = 0
    confidence_total = 0.0
    confidence_count = 0
    manifest_driven_count = 0
    tool_assisted_success_count = 0
    node_delegation_success_count = 0
    multi_step_success_count = 0
    unsafe_execution_count = 0

    for record in records:
        event_type = str(record.get("event_type", "") or "")
        payload = dict(record.get("payload") or {})
        if event_type != "runtime.strategy.execution.result":
            continue
        strategy_execution_count += 1
        status = str(payload.get("strategy_execution_status", "") or "")
        selected_strategy = str(payload.get("selected_strategy", "") or "")
        if status == "success":
            executor_success_count += 1
            if selected_strategy == "TOOL_ASSISTED":
                tool_assisted_success_count += 1
            if selected_strategy == "NODE_RUNTIME_DELEGATION":
                node_delegation_success_count += 1
            if selected_strategy == "MULTI_STEP_REASONING":
                multi_step_success_count += 1
        if bool(payload.get("strategy_execution_fallback", False)):
            fallback_count += 1
        if bool(payload.get("governance_blocked", False)):
            governance_block_count += 1
        if bool(payload.get("governance_downgrade_applied", False)):
            downgrade_count += 1
        if bool(payload.get("manifest_driven_execution", False)):
            manifest_driven_count += 1
        if bool(payload.get("unsafe_override", False)):
            unsafe_execution_count += 1
        confidence = float(payload.get("ranked_confidence", payload.get("model_confidence", 0.0)) or 0.0)
        if confidence > 0.0:
            confidence_total += confidence
            confidence_count += 1

    report = {
        "strategy_execution_count": strategy_execution_count,
        "executor_success_rate": round(executor_success_count / max(1, strategy_execution_count), 4),
        "fallback_rate": round(fallback_count / max(1, strategy_execution_count), 4),
        "governance_block_rate": round(governance_block_count / max(1, strategy_execution_count), 4),
        "downgrade_rate": round(downgrade_count / max(1, strategy_execution_count), 4),
        "average_execution_confidence": round(confidence_total / max(1, confidence_count), 4),
        "manifest_driven_count": manifest_driven_count,
        "tool_assisted_success_rate": round(tool_assisted_success_count / max(1, strategy_execution_count), 4),
        "node_delegation_success_rate": round(node_delegation_success_count / max(1, strategy_execution_count), 4),
        "multi_step_reasoning_success_rate": round(multi_step_success_count / max(1, strategy_execution_count), 4),
        "unsafe_execution_count": unsafe_execution_count,
    }
    write_json(Path(args.output), report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
