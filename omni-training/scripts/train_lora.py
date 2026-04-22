from __future__ import annotations

import argparse
import sys
from pathlib import Path

LIB_DIR = Path(__file__).resolve().parents[1] / "lib"
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

from training_utils import (
    format_training_examples,
    load_json_config,
    load_sft_jsonl,
    resolve_training_path,
    summarize_training_records,
    validate_training_config,
)
from sft_builder import filter_sft_records


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
    records = filter_sft_records(
        records,
        min_quality_score=float(training_config.get("min_quality_score", 0.0) or 0.0),
        allowed_review_statuses={str(item) for item in list(training_config.get("review_status_filters", []) or [])},
        source_filters={str(item) for item in list(training_config.get("source_filters", []) or [])},
        task_family_filters={str(item) for item in list(training_config.get("task_family_filters", []) or [])},
    )
    formatted = format_training_examples(records, max_samples=int(training_config.get("max_train_samples", training_config.get("max_samples", 0)) or 0))
    summary = summarize_training_records(records)
    print(f"Loaded {len(formatted)} formatted SFT examples")
    print(f"Training summary: {summary}")
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
    validation_records = []
    validation_path = training_config.get("validation_dataset_path")
    if validation_path:
        try:
            validation_records = filter_sft_records(
                load_sft_jsonl(Path(validation_path)),
                min_quality_score=float(training_config.get("min_quality_score", 0.0) or 0.0),
                allowed_review_statuses={str(item) for item in list(training_config.get("review_status_filters", []) or [])},
                source_filters={str(item) for item in list(training_config.get("source_filters", []) or [])},
                task_family_filters={str(item) for item in list(training_config.get("task_family_filters", []) or [])},
            )
        except FileNotFoundError:
            validation_records = []
    formatted_validation = format_training_examples(validation_records, max_samples=int(training_config.get("max_eval_samples", 0) or 0))
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

    tokenized = dataset.map(tokenize, batched=True, remove_columns=list(dataset.column_names))
    eval_dataset = None
    if formatted_validation:
        eval_dataset = Dataset.from_list(formatted_validation).map(tokenize, batched=True, remove_columns=list(Dataset.from_list(formatted_validation).column_names))
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

    output_dir = resolve_training_path(training_config["output_dir"])
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
        evaluation_strategy="steps" if eval_dataset is not None else "no",
        eval_steps=int(training_config.get("save_steps", 25)),
        report_to=[],
        remove_unused_columns=False,
    )
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized,
        eval_dataset=eval_dataset,
        data_collator=DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False),
    )
    trainer.train()
    model.save_pretrained(str(output_dir))
    tokenizer.save_pretrained(str(output_dir))
    print(f"Saved LoRA adapter to {output_dir}")
    print(f"Final training summary: {summary}")
    if torch.cuda.is_available():
        print(f"CUDA device used: {torch.cuda.get_device_name(0)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
