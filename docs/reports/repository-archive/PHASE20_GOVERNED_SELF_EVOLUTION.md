# Phase 20 - Governed Self-Evolution Layer

## Mission

Phase 20 introduces the governed self-evolution layer: a bounded, policy-driven mechanism that can identify recurring operational weaknesses, propose conservative improvements, classify scope and risk, build validation plans, record governance decisions, and keep promotion blocked by default.

This is not unrestricted self-editing. It is the first explicit governance layer for bounded runtime improvement.

## Evolution Philosophy

The layer follows these principles:

1. evidence before proposal
2. proposal before validation
3. validation before promotion
4. governance before any non-trivial advancement
5. promotion disabled by default
6. explicit artifacts over hidden adaptation

## Opportunity Model

`EvolutionOpportunity` is created only from bounded recurring evidence, such as:

- repeated discouraged retry patterns
- repeated escalation outcomes
- recurring repair underperformance
- repeated validation insertion signals
- orchestration route inferiority signals

Unsupported ideas like "be smarter" or broad redesign requests are intentionally excluded.

## Proposal Model

`EvolutionProposal` includes:

- proposal id
- source opportunity id
- target subsystem
- proposal type
- scope class
- risk level
- expected affected artifacts
- evidence summary
- validation requirements
- governance status
- promotion status

Supported proposal types:

- `policy_tuning`
- `template_adjustment`
- `routing_adjustment`
- `validation_insertion`
- `bounded_runtime_refinement`

## Scope Model

Phase 20 only allows bounded proposals inside existing runtime governance boundaries.

Allowed examples:

- policy tuning in continuation or orchestration
- validation insertion in planning templates
- repair template selection refinement
- route weighting refinement

Blocked examples:

- unrestricted code generation
- multi-subsystem redesign
- frontend plus Rust plus backend simultaneous mutation
- environment mutation or dependency installation

## Risk Model

Risk is deterministic:

- `low`
- `medium`
- `high`
- `critical`

Sensitive runtime control areas like continuation, self-repair, and evolution receive elevated risk by default. Out-of-scope or over-broad changes escalate to critical and remain blocked.

## Validation Model

Every non-blocked proposal receives a validation plan.

Validation plan includes:

- targeted unit tests
- import validation
- policy consistency checks
- replay requirements for the relevant evidence class

No proposal skips validation planning.

## Governance Model

Governance decisions are explicit:

- `rejected`
- `deferred`
- `approved_for_validation`
- `approved_for_promotion`
- `blocked_by_policy`

Conservative defaults:

- `OMINI_EVOLUTION_ENABLED=false`
- `OMINI_EVOLUTION_ALLOW_VALIDATION=true`
- `OMINI_EVOLUTION_ALLOW_PROMOTION=false`
- `OMINI_EVOLUTION_MAX_ACTIVE_PROPOSALS=5`
- `OMINI_EVOLUTION_REQUIRE_GOVERNANCE_FOR_MEDIUM_AND_ABOVE=true`
- `OMINI_EVOLUTION_BLOCK_CRITICAL=true`

## Promotion Model

Promotion stays fail-safe:

- no promotion without governance
- no promotion without validation
- no promotion when policy disables it
- no promotion for blocked scope
- no promotion when rollback is absent for non-trivial cases

In Phase 20, promotion remains disabled by default.

## Integration Points

Phase 20 integrates additively:

- after learning ingestion inside action execution
- after orchestration updates in continuation handling
- alongside existing planning, repair, continuation, learning, and orchestration artifacts

It does not bypass any previous policy layer.

## Persistence

Artifacts are stored under:

- `.logs/fusion-runtime/evolution/opportunities/`
- `.logs/fusion-runtime/evolution/proposals/`
- `.logs/fusion-runtime/evolution/validations/`
- `.logs/fusion-runtime/evolution/governance/`
- `.logs/fusion-runtime/evolution/promotions/`

All artifacts remain JSONL, compact, and human-auditable.

## Limitations

Even after Phase 20, Omni intentionally still blocks:

- unrestricted self-editing
- autonomous architecture redesign
- hidden policy rewrites
- uncontrolled multi-file mutation
- dependency installation or environment mutation
- silent production promotion

## Final Assessment

With Phase 20, Omni reaches a governed maturity point:

- execution is trusted
- repair is bounded
- planning is durable
- continuation is adaptive
- learning is evidence-backed
- orchestration is explicit
- evolution is now governed

The system can now identify and prepare its own bounded improvements while still remaining under explicit policy and governance control.
