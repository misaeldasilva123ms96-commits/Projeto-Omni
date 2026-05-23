# Dataset Expansion

## Why 8 examples are not enough

The original Omni seed dataset was enough to validate ingestion, OIL conversion, SFT formatting and LoRA plumbing.

It is not enough to produce useful adaptation because:

- it does not cover enough task families
- it does not represent ambiguity, fallback and degraded execution with enough frequency
- it does not provide enough variation in PT-BR technical prompts
- it is too small to distinguish strong patterns from noise

## Expansion strategy

The expanded pipeline keeps a strict separation between:

- `raw`
- `normalized`
- `oil`
- `curated`
- `sft`

The growth path now combines:

- filtered public instruction data
- internal curated Omni examples
- runtime harvesting
- ambiguity and execution examples
- synthetic controlled examples only for narrow gaps

## Safety rules

- no raw public dataset goes directly into final training
- every record keeps a source and metadata trail
- synthetic records are always marked as `synthetic_controlled`
- runtime-derived records start as review candidates

## Near-term goal

The current structure is ready to support a mixed dataset in the 500 to 2,000 useful-example range once ingestion is run and the review queue is expanded.

