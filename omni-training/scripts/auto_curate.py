from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

LIB_DIR = Path(__file__).resolve().parents[1] / "lib"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_PYTHON = PROJECT_ROOT / "backend" / "python"
for candidate in (LIB_DIR, BACKEND_PYTHON):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from common import read_jsonl, write_json  # noqa: E402
from dataset_enrichment import enrich_curated_example  # noqa: E402

try:
    from brain.runtime.learning import LoRAInferenceEngine  # type: ignore  # noqa: E402
except Exception:  # pragma: no cover
    LoRAInferenceEngine = None  # type: ignore


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Auto-curate Omni curated examples using the current local model when available.")
    parser.add_argument("--input", default=str(Path(__file__).resolve().parents[1] / "data" / "curated" / "omni_seed_dataset.jsonl"))
    parser.add_argument("--output", default=str(Path(__file__).resolve().parents[1] / "reports" / "curation_report.json"))
    parser.add_argument("--max-samples", type=int, default=25)
    return parser.parse_args()


def token_overlap(expected: str, predicted: str) -> float:
    expected_tokens = {token for token in str(expected or "").lower().split() if token}
    predicted_tokens = {token for token in str(predicted or "").lower().split() if token}
    if not expected_tokens:
        return 0.0
    return round(len(expected_tokens & predicted_tokens) / len(expected_tokens), 4)


def classify_prediction(expected: str, predicted: str) -> str:
    overlap = token_overlap(expected, predicted)
    if overlap >= 0.65:
        return "good"
    if overlap >= 0.35:
        return "weak"
    return "incorrect"


def _fallback_prediction(example: dict[str, Any]) -> str:
    hints = dict(example.get("runtime_hints") or {})
    strategy = str(hints.get("strategy", "DIRECT_RESPONSE") or "DIRECT_RESPONSE")
    return (
        "Resposta sintetizada a partir do domínio Omni com foco em "
        f"{strategy.lower()} e compatibilidade incremental."
    )


def generate_candidate(example: dict[str, Any], engine: Any | None) -> str:
    if engine is None:
        return _fallback_prediction(example)
    prompt = (
        "<|system|>\nVocê é Omni em validação de dataset.\n"
        "<|user|>\n"
        f"INPUT: {str(example.get('user_input', '')).strip()}\n"
        f"CONTEXT: {str(example.get('context', '')).strip()}\n"
        f"OIL: {json.dumps(dict(example.get('oil') or {}), ensure_ascii=False)}\n"
        "<|assistant|>\n"
    )
    result = engine.generate_response(prompt, context={"mode": "auto_curate"})
    if result.model_used and str(result.text).strip():
        return str(result.text).strip()
    return _fallback_prediction(example)


def build_report(records: list[dict[str, Any]], *, engine: Any | None, max_samples: int) -> dict[str, Any]:
    items = []
    counters = {"good": 0, "weak": 0, "incorrect": 0}
    for raw in records[:max_samples]:
        example = enrich_curated_example(raw)
        predicted = generate_candidate(example, engine)
        expected = str(example.get("assistant_output", "")).strip()
        status = classify_prediction(expected, predicted)
        counters[status] += 1
        items.append(
            {
                "id": example.get("id"),
                "status": status,
                "quality_score": example.get("quality_score"),
                "token_overlap": token_overlap(expected, predicted),
            }
        )
    return {
        "total_examples": len(items),
        "good": counters["good"],
        "weak": counters["weak"],
        "incorrect": counters["incorrect"],
        "model_enabled": bool(engine is not None),
        "items": items,
    }


def main() -> int:
    args = parse_args()
    records = read_jsonl(Path(args.input))
    engine = None
    if LoRAInferenceEngine is not None:
        candidate = LoRAInferenceEngine(PROJECT_ROOT)
        if candidate.adapter_available():
            engine = candidate
    report = build_report(records, engine=engine, max_samples=max(1, int(args.max_samples)))
    write_json(Path(args.output), report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

