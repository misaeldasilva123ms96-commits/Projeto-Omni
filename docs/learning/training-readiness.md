# Training Readiness

## Purpose

`training_readiness.py` exists to answer a practical question before a real LoRA run:

Is the Omni dataset ready for a short useful training cycle?

## What it checks

- total example count
- distribution by source
- distribution by task family
- distribution by language
- examples above quality threshold
- reviewed and approved examples
- synthetic example count
- runtime-derived example count

## Decisions

The script emits one of:

- `NOT_READY`
- `READY_FOR_SMALL_LORA`
- `READY_FOR_MEDIUM_LORA`

It now also checks:

- PT-BR ratio
- runtime-derived ratio
- synthetic ratio

## How to use it

Run it after building `mixed_sft.jsonl` and before starting a non-trivial training run.

This keeps training decisions data-driven and avoids spending time on adapters that are underfed or badly mixed.
