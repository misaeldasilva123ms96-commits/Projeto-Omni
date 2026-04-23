# Model Evaluation

## Purpose

The Omni evaluation layer now supports a stronger baseline-vs-adapter comparison before and after LoRA training.

## Current focus

Evaluation is still lightweight and operational. It looks for signals that matter to Omni:

- structure
- Omni style
- OIL alignment
- strategy alignment
- generic answer risk
- fallback handling
- coding usefulness
- planning usefulness

## Baseline first

If there is no adapter available, the evaluation still runs in baseline mode and produces a report.

That keeps the workflow useful even before the first real adapter is trained.

The default report path is now `before_after_summary.json`, so the same script can be reused before and after a LoRA run without changing downstream expectations.

## Limits

This evaluation is not a full benchmark. It is a production-oriented gate to help decide whether a dataset or adapter is strong enough to justify the next training cycle.
