# PHASE 13 — TRAINING READINESS

Date: 2026-05-01

Base branch: memory/training-safety-09

Base commit: cb44558a896b8d7cb6e6dde258057d624a46a2d4

Working branch: training/readiness-13

## Scope

Phase 13 adds safe training-readiness infrastructure only. It does not start LoRA, RAG, fine-tuning, uploads, dataset release, or automatic training.

## Files Changed

- `docs/training/TRAINING_READINESS.md`
- `docs/audit/PHASE_13_TRAINING_READINESS.md`
- `data/evals/runtime_truth_eval.jsonl`
- `data/evals/safety_eval.jsonl`
- `data/evals/intent_eval.jsonl`
- `scripts/validate_training_candidate.py`
- `scripts/export_training_candidates.py`
- `tests/training/test_training_readiness_phase13.py`

## Schemas Created

- Positive candidate schema: `omni_training_candidate_v1`
- Eval case schema: `omni_eval_case_v1`

## Scripts Created

- `scripts/validate_training_candidate.py`
- `scripts/export_training_candidates.py`

## Eval Files Created

- `data/evals/runtime_truth_eval.jsonl`
- `data/evals/safety_eval.jsonl`
- `data/evals/intent_eval.jsonl`

## Safety Rules

Positive candidates require Phase 9 `learning_safety.positive_training_candidate=true`, no fallback, no matcher shortcut, no provider failure, no blocked/failed tool, no governance block, no unsafe public error severity, no raw PII/secrets/paths/payloads, and user-visible success.

## Tests Run / Results

- `python -m pytest -q tests/training tests/runtime/learning` — PASS. 35 passed.
- `python -m py_compile scripts/export_training_candidates.py scripts/validate_training_candidate.py backend/python/brain/runtime/learning/learning_safety.py` — PASS.
- `python scripts/validate_training_candidate.py data/evals/runtime_truth_eval.jsonl --eval` — PASS. 2 records.
- `python scripts/validate_training_candidate.py data/evals/safety_eval.jsonl --eval` — PASS. 2 records.
- `python scripts/validate_training_candidate.py data/evals/intent_eval.jsonl --eval` — PASS. 2 records.
- `python scripts/export_training_candidates.py` — PASS. Dry-run only; read 17 local controlled records, identified 5 positive candidates and 12 eval cases, wrote no output files.
- `npm run test:security` — PASS, exit code 0. Local npm wrapper emitted no detailed output.
- `node tests/security/security-regression-suite.mjs` — PASS. Consolidated security suite passed.
- `npm test` — PASS, exit code 0. Local npm wrapper emitted no detailed output.
- `npm run test:js-runtime` — TIMEOUT after 180 seconds with no output. Classified as inherited/runner-level because direct JS security tests passed through `node tests/security/security-regression-suite.mjs`.
- `npm run test:python:pytest` — PASS, exit code 0. Local npm wrapper emitted no detailed output in this run.
- `npm --prefix frontend run typecheck` — PASS, exit code 0. Local npm wrapper emitted no detailed output.
- `cd backend/rust && cargo test` — PASS. 38 passed; warning remains for unused `InvalidRequest` variant.
- `git diff --check` — PASS.

## Known Limitations

- Export remains local and dry-run by default.
- Existing historical logs are not rewritten.
- No training is started in this phase.

## Rollback

Revert the Phase 13 commit on `training/readiness-13`.

## Gate 13 Status

Status: PASSED.

Reason: safe training candidate export and validation scripts exist, unsafe positive cases are rejected, eval seed JSONL files exist and validate, export is dry-run by default, no training/upload was started, and no merge into main occurred.

## No Merge Into Main

This phase does not merge into main.
