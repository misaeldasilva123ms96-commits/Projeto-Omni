from __future__ import annotations

import argparse
import sys
from pathlib import Path

LIB_DIR = Path(__file__).resolve().parents[1] / "lib"
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

from training_utils import format_training_examples, load_json_config, load_sft_jsonl, validate_training_config


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train a minimal LoRA adapter on Omni SFT JSONL.")
    parser.add_argument("--training-config", default=str(Path(__file__).resolve().parents[1] / "configs" / "training_config.json"))
    parser.add_argument("--lora-config", default=str(Path(__file__).resolve().parents[1] / "configs" / "lora_config.json"))
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    training_config = load_json_config(Path(args.training_config))
    lora_config = load_json_config(Path(args.lora_config))
    validate_training_config(training_config, lora_config)
    records = load_sft_jsonl(Path(training_config["dataset_path"]))
    formatted = format_training_examples(records, max_samples=int(training_config.get("max_samples", 0) or 0))
    print(f"Loaded {len(formatted)} formatted SFT examples")
    if args.dry_run:
        print("Dry run enabled; skipping model loading and training.")
        return 0
    try:
        import torch
        from datasets import Dataset
        from peft import LoraConfig, get_peft_model
        from transformers import (
            AutoModelForCausalLM,
            AutoTokenizer,
            DataCollatorForLanguageModeling,
            Trainer,
            TrainingArguments,
        )
    except Exception as exc:  # pragma: no cover
        raise SystemExit(f"training dependencies are required: {exc}") from exc

    dataset = Dataset.from_list(formatted)
    tokenizer = AutoTokenizer.from_pretrained(training_config["base_model"])
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    def tokenize(batch):
        encoded = tokenizer(
            batch["text"],
            truncation=True,
            max_length=int(training_config.get("max_length", 1024)),
            padding="max_length",
        )
        encoded["labels"] = list(encoded["input_ids"])
        return encoded

    tokenized = dataset.map(tokenize, batched=True, remove_columns=["text"])
    model = AutoModelForCausalLM.from_pretrained(training_config["base_model"])
    peft_config = LoraConfig(
        r=int(lora_config["r"]),
        lora_alpha=int(lora_config["lora_alpha"]),
        lora_dropout=float(lora_config["lora_dropout"]),
        bias=str(lora_config.get("bias", "none")),
        task_type=str(lora_config["task_type"]),
        target_modules=list(lora_config.get("target_modules", [])),
    )
    model = get_peft_model(model, peft_config)

    output_dir = Path(training_config["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)
    training_args = TrainingArguments(
        output_dir=str(output_dir),
        num_train_epochs=float(training_config["num_train_epochs"]),
        per_device_train_batch_size=int(training_config["per_device_train_batch_size"]),
        gradient_accumulation_steps=int(training_config["gradient_accumulation_steps"]),
        learning_rate=float(training_config["learning_rate"]),
        weight_decay=float(training_config.get("weight_decay", 0.0)),
        logging_steps=int(training_config["logging_steps"]),
        save_steps=int(training_config["save_steps"]),
        warmup_ratio=float(training_config.get("warmup_ratio", 0.0)),
        seed=int(training_config.get("seed", 42)),
        report_to=[],
        remove_unused_columns=False,
    )
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized,
        data_collator=DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False),
    )
    trainer.train()
    model.save_pretrained(str(output_dir))
    tokenizer.save_pretrained(str(output_dir))
    print(f"Saved LoRA adapter to {output_dir}")
    if torch.cuda.is_available():
        print(f"CUDA device used: {torch.cuda.get_device_name(0)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
