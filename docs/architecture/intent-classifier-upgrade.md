# Intent Classifier Upgrade

Phase: Omni Roadmap v2.1 Phase 12

## Purpose

Omni keeps the existing regex intent path as the default while adding a feature-flagged classifier router. The router improves observability and future extensibility without requiring provider keys, embeddings, training, LoRA, RAG, or unsafe tool execution.

## Classifier API

`core/brain/queryEngineAuthority.js` exports:

- `inferIntent(message)`: existing compatible regex intent function.
- `inferIntentWithSource(message)`: Phase 2 wrapper, still regex-backed by default.
- `classifyIntent(message, context?)`: feature-flagged router that returns classifier metadata.

Classifier result:

```json
{
  "intent": "execution",
  "intent_source": "rule_based",
  "confidence": 0.7,
  "classifier_version": "regex_v1",
  "classifier_mode": "regex",
  "matcher_used": false,
  "provider_attempted": false,
  "provider_succeeded": false
}
```

## Classifier Modes

- `regex`: default. Uses the current rule-based intent logic and preserves compatibility.
- `embedding`: scaffold only. It does not call external providers and uses the local guardrail path.
- `llm`: provider-backed classification is not enabled by default. It fails closed to regex metadata without exposing raw provider output.
- `hybrid`: regex-first guardrail mode with hybrid runtime truth labels. It does not call providers by default.

## Matcher Modes

- `enabled`: existing matcher behavior remains active and labeled.
- `labeled_only`: matchers stay enabled and emit runtime truth fields.
- `disabled`: matchers are bypassed only when classifier confidence is safe; low-confidence cases remain safe.

## Environment Variables

Canonical:

- `OMNI_INTENT_CLASSIFIER=regex|embedding|llm|hybrid`
- `OMNI_MATCHER_MODE=enabled|labeled_only|disabled`

Legacy aliases:

- `OMINI_INTENT_CLASSIFIER`
- `OMINI_MATCHER_MODE`

Precedence:

- `OMNI_*` wins over `OMINI_*`.
- Defaults are `regex` and `enabled`.

## Runtime Truth Behavior

Runtime truth now preserves classifier metadata:

- `classifier_mode`
- `classifier_version`
- `intent_source`
- `classifier_provider_attempted`
- `classifier_provider_succeeded`

Regex remains `intent_source=rule_based` and `classifier_version=regex_v1`. Hybrid is labeled as `intent_source=hybrid`. LLM unavailable mode reports a regex fallback classifier version and never claims provider success.

## Safety Rules

- No classifier mode executes tools directly.
- Low-confidence results do not trigger tool execution.
- LLM mode does not require provider keys and does not call providers by default.
- Raw provider payloads, secrets, debug internals, and stack traces are not exposed.
- Existing matchers are not removed.
- Fallback paths cannot become full cognitive runtime success by classifier metadata alone.

## Eval Harness

Run:

```bash
node scripts/evaluate_intent_classifier.mjs --mode=regex --input=data/evals/intent_eval.jsonl
```

The harness reports:

- `accuracy`
- `fallback_rate`
- `matcher_usage_rate`
- `provider_usage_rate`
- `low_confidence_rate`
- `by_intent`

The harness reads local JSONL only and does not call providers by default.

## Current Metrics

For `data/evals/intent_eval.jsonl` in regex mode:

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

## Rollback

Set:

```bash
OMNI_INTENT_CLASSIFIER=regex
OMNI_MATCHER_MODE=enabled
```

or revert the Phase 12 branch. No data migration is required.

## Limitations

- Embedding and LLM modes are safe scaffolds, not production classifiers.
- The eval dataset is intentionally small and synthetic.
- Provider-backed classification remains future work and must stay behind explicit controls.
