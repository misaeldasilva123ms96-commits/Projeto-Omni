from __future__ import annotations

from pathlib import Path


def test_training_stack_imports_and_versions() -> None:
    from packaging.version import Version
    import accelerate
    import datasets
    import huggingface_hub
    import peft
    import torch
    import transformers

    assert Version(datasets.__version__) >= Version("5.0.1")
    assert Version(huggingface_hub.__version__) >= Version("1.28.0")
    assert Version(transformers.__version__) >= Version("5.15.1")
    assert Version(peft.__version__) >= Version("0.19.1")
    assert Version(accelerate.__version__) >= Version("1.14.0")
    assert Version(torch.__version__.split("+")[0]) >= Version("2.13.0")


def test_tiny_lora_train_save_reload(tmp_path: Path) -> None:
    import torch
    from peft import LoraConfig, PeftModel, get_peft_model
    from transformers import GPT2Config, GPT2LMHeadModel, Trainer, TrainingArguments, default_data_collator

    config = GPT2Config(
        vocab_size=32,
        n_positions=16,
        n_ctx=16,
        n_embd=16,
        n_layer=1,
        n_head=1,
        bos_token_id=1,
        eos_token_id=2,
    )
    model = GPT2LMHeadModel(config)
    model = get_peft_model(
        model,
        LoraConfig(
            r=2,
            lora_alpha=4,
            lora_dropout=0.0,
            bias="none",
            task_type="CAUSAL_LM",
            target_modules=["c_attn"],
        ),
    )

    class TinyDataset(torch.utils.data.Dataset):
        def __len__(self) -> int:
            return 2

        def __getitem__(self, index: int) -> dict[str, torch.Tensor]:
            input_ids = torch.tensor([1, 3 + index, 4, 5, 6, 7, 8, 2], dtype=torch.long)
            return {
                "input_ids": input_ids,
                "attention_mask": torch.ones_like(input_ids),
                "labels": input_ids.clone(),
            }

    args = TrainingArguments(
        output_dir=str(tmp_path / "trainer"),
        max_steps=1,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=1,
        learning_rate=1e-4,
        logging_steps=1,
        save_strategy="no",
        eval_strategy="no",
        report_to=[],
        remove_unused_columns=False,
    )
    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=TinyDataset(),
        data_collator=default_data_collator,
    )
    result = trainer.train()
    assert result.global_step == 1

    adapter_dir = tmp_path / "adapter"
    model.save_pretrained(adapter_dir)
    assert (adapter_dir / "adapter_config.json").exists()

    reloaded = PeftModel.from_pretrained(GPT2LMHeadModel(config), adapter_dir)
    sample = torch.tensor([[1, 3, 4, 5, 6, 7, 8, 2]], dtype=torch.long)
    logits = reloaded(input_ids=sample).logits
    assert logits.shape[:2] == sample.shape
