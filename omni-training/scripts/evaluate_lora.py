from __future__ import annotations

import argparse
import sys
from pathlib import Path

LIB_DIR = Path(__file__).resolve().parents[1] / "lib"
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

from training_utils import load_json_config, load_sft_jsonl


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a minimal evaluation/smoke generation on a LoRA adapter.")
    parser.add_argument("--training-config", default=str(Path(__file__).resolve().parents[1] / "configs" / "training_config.json"))
    parser.add_argument("--max-samples", type=int, default=3)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    training_config = load_json_config(Path(args.training_config))
    records = load_sft_jsonl(Path(training_config["dataset_path"]))[: max(1, args.max_samples)]
    prompts = [str(record.get("prompt_text", "")).strip() for record in records if str(record.get("prompt_text", "")).strip()]
    print(f"Prepared {len(prompts)} prompts for evaluation")
    if args.dry_run:
        print("Dry run enabled; skipping model loading.")
        return 0
    try:
        import torch
        from peft import PeftModel
        from transformers import AutoModelForCausalLM, AutoTokenizer
    except Exception as exc:  # pragma: no cover
        raise SystemExit(f"evaluation dependencies are required: {exc}") from exc

    base_model = training_config["base_model"]
    adapter_dir = training_config["output_dir"]
    tokenizer = AutoTokenizer.from_pretrained(adapter_dir if Path(adapter_dir).exists() else base_model)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(base_model)
    if Path(adapter_dir).exists():
        model = PeftModel.from_pretrained(model, adapter_dir)
    model.eval()
    for index, prompt in enumerate(prompts, start=1):
        inputs = tokenizer(prompt, return_tensors="pt")
        with torch.no_grad():
            outputs = model.generate(**inputs, max_new_tokens=128)
        text = tokenizer.decode(outputs[0], skip_special_tokens=True)
        print(f"\n=== SAMPLE {index} ===\n{text}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
