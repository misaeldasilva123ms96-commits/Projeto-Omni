# PHASE 12 INTELLIGENCE UPGRADE

Branch: intelligence/intent-classifier-12

Base branch: architecture/circuit-breaker-11d

Base commit: d7476ed472bf425305d980c94ef6c4c00ee5371c

Phase: Omni Roadmap v2.1 Phase 12

Statement: feature-flagged intent classification upgrade only. Existing regex behavior remains the default. No merge into main.

## Files Changed

- `core/brain/queryEngineAuthority.js`
- `data/evals/intent_eval.jsonl`
- `docs/architecture/intent-classifier-upgrade.md`
- `docs/audit/PHASE_12_INTELLIGENCE_UPGRADE.md`
- `package.json`
- `scripts/evaluate_intent_classifier.mjs`
- `tests/runtime/intentClassifier.test.mjs`

## Classifier Paths

- Main classifier router: `core/brain/queryEngineAuthority.js`
- Existing compatibility API: `inferIntent(message)`
- Phase 2 wrapper: `inferIntentWithSource(message)`
- New router: `classifyIntent(message, context?)`
- Eval harness: `scripts/evaluate_intent_classifier.mjs`

## Classifier Modes

- `regex`: default rule-based classifier.
- `embedding`: local scaffold, no external provider call.
- `llm`: safe fallback scaffold, no provider call by default.
- `hybrid`: regex-first guardrail mode.

## Matcher Modes

- `enabled`: current matcher behavior.
- `labeled_only`: current matcher behavior with explicit labels.
- `disabled`: bypasses matchers only when classifier confidence is safe.

## Runtime Truth Behavior

Runtime truth preserves:

- `intent`
- `intent_source`
- `classifier_version`
- `classifier_mode`
- `classifier_provider_attempted`
- `classifier_provider_succeeded`
- `matcher_used`

Regex remains `rule_based` with `regex_v1`. Hybrid is labeled as `hybrid`. LLM unavailable mode fails closed to regex fallback metadata and never reports provider success.

## Eval Harness

Command:

```bash
node scripts/evaluate_intent_classifier.mjs --mode=regex --input=data/evals/intent_eval.jsonl
```

Metrics:

```json
{
  "total": 13,
  "evaluated": 13,
  "correct": 12,
  "accuracy": 0.9231,
  "fallback_rate": 0,
  "matcher_usage_rate": 0,
  "provider_usage_rate": 0,
  "low_confidence_rate": 0.3846
}
```

## Safety Rules

- No classifier output executes tools directly.
- Low-confidence classification does not trigger tool execution.
- Provider-backed classification is not required.
- LLM mode does not call providers by default.
- Raw provider output, secrets, debug internals, stack, env, and payloads are not exposed.
- Existing matchers are preserved.

## Validation Results

Passed:

- `node tests/runtime/intentClassifier.test.mjs`
- `node scripts/evaluate_intent_classifier.mjs --mode=regex --input=data/evals/intent_eval.jsonl`
- `npm run test:js-runtime`
- `npm run test:security`
- `npm --prefix frontend run typecheck`
- `python -m py_compile backend/python/brain_service.py backend/python/main.py`
- `npm test`
- `npm run test:python:pytest`
- `cd backend/rust && cargo test`
- `git diff --check`

Notes:

- `cargo test` passed with 46 Rust tests.
- `git diff --check` passed with line-ending warnings only.

## Known Limitations

- Embedding mode is a safe scaffold only.
- LLM classifier mode is not provider-backed by default.
- Eval data is synthetic and intentionally small.
- The classifier ontology still maps into the current runtime intents.

## Rollback

Set:

```bash
OMNI_INTENT_CLASSIFIER=regex
OMNI_MATCHER_MODE=enabled
```

or revert this branch.

## Gate 12

PASSED:

- Regex path remains compatible.
- Classifier router is feature-flagged.
- Matchers are labeled.
- Eval harness exists.
- Metrics are reported.
- No unsafe tool execution was introduced.
- Runtime truth labels classifier source.
- Tests were added.
- No merge into main.
