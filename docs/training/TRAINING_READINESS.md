# Omni Training Readiness

Phase 13 prepares validation and export infrastructure only. It does not start LoRA, RAG, fine-tuning, uploads, or any automatic training workflow.

## Positive Candidate Rules

A record may become a positive training candidate only when all are true:

- `learning_safety.positive_training_candidate=true`
- `fallback_triggered=false`
- `runtime_mode` is not `MATCHER_SHORTCUT`, `SAFE_FALLBACK`, `NODE_FALLBACK`, `PROVIDER_UNAVAILABLE`, or `TOOL_BLOCKED`
- provider success is true when provider output is used
- tool execution succeeded when tool output is used
- governance status is `allowed` when a tool is involved
- no unsafe request is present
- no raw PII, secrets, filesystem paths, or raw internal payloads are present
- user-visible success is true

## Excluded From Positive Training

These records must not be positive examples:

- fallback responses
- matcher shortcuts
- tool blocked or failed events
- provider unavailable or failed events
- governance blocked events
- samples with raw payloads or raw debug content
- samples with PII/secrets/paths
- heavily redacted samples where semantic usefulness is uncertain
- degraded/error/blocked public error cases

## Positive Candidate Schema

Each positive JSONL line uses:

```json
{
  "schema_version": "omni_training_candidate_v1",
  "id": "clr-...",
  "source": "controlled_learning_record",
  "input": "sanitized user input preview",
  "expected_output": "sanitized successful output",
  "runtime_mode": "FULL_COGNITIVE_RUNTIME",
  "selected_strategy": "DIRECT_RESPONSE",
  "selected_tool": "",
  "user_visible_success": true,
  "learning_safety": {
    "positive_training_candidate": true,
    "learning_classification": "positive_training_candidate"
  },
  "metadata": {
    "execution_path": "node_execution",
    "provider_actual": "public provider name only"
  }
}
```

## Eval Case Schema

Non-positive evaluation JSONL lines use:

```json
{
  "schema_version": "omni_eval_case_v1",
  "id": "runtime-truth-001",
  "source": "synthetic_phase13_seed",
  "case_type": "runtime_truth_eval_case",
  "input": "safe synthetic input",
  "expected_behavior": "expected classification behavior",
  "runtime_mode": "SAFE_FALLBACK",
  "learning_safety": {
    "positive_training_candidate": false
  }
}
```

Allowed eval classifications include `negative_training_candidate`, `safety_eval_case`, `routing_eval_case`, `runtime_truth_eval_case`, `governance_eval_case`, and `diagnostic_memory`.

## Commands

Validate positive candidates:

```bash
python scripts/validate_training_candidate.py path/to/candidates.jsonl
```

Validate eval cases:

```bash
python scripts/validate_training_candidate.py data/evals/runtime_truth_eval.jsonl --eval
```

Dry-run export from controlled learning records:

```bash
python scripts/export_training_candidates.py
```

Write validated outputs explicitly:

```bash
python scripts/export_training_candidates.py --write --positive-output out/positive.jsonl --eval-output out/eval.jsonl
```

## Privacy And Redaction

Export and validation reuse runtime learning redaction. Raw emails, phones, CPF, API keys, JWTs, bearer tokens, Supabase URLs, filesystem paths, raw provider payloads, raw tool results, environment dumps, stack traces, stdout/stderr, and execution requests are rejected or redacted before persistence.

## Known Limitations

- Historical logs are not rewritten.
- Export is local only and dry-run by default.
- This does not prove model readiness; it only gates candidate safety and schema validity.
- Real dataset release remains blocked until Phase 13 output is reviewed and later export-readiness gates are passed.
