# Phase 23 - Internal Simulation Layer

## Mission

Phase 23 adds the first bounded internal deliberation layer to Omni. Before the continuation layer commits to a route, the runtime can now simulate a fixed set of candidate paths and use that forecast conservatively.

The simulator is:

- bounded
- deterministic
- auditable
- goal-aware
- goal-none-safe
- advisory-first

## Simulation Philosophy

The simulator does not generate arbitrary plans.

It only evaluates four bounded routes:

- `retry`
- `repair`
- `replan`
- `pause`

This is not free-form rollout. It is structured forecasting over a fixed operational route set using:

- episodic memory
- semantic memory
- procedural memory
- goal context
- active constraints
- current runtime state

## Bounded Route Set

Phase 23 never invents new routes.

The route set is intentionally fixed so the runtime can reason before acting without becoming an unrestricted planner.

## Forecasting Model

The forecasting pipeline is split into two modes.

### History-backed estimate

When similar episodes meet the minimum threshold:

- success rate comes from observed outcomes
- constraint risk comes from failure distribution
- cost comes from bounded duration proxies
- confidence rises with sample size

### Heuristic fallback

When history is sparse:

- deterministic heuristics are used
- confidence is kept explicitly low
- the result records that heuristic fallback occurred

This keeps the simulator useful from early adoption onward.

## Semantic Enrichment Model

Semantic memory only enriches route forecasts.

It never dominates them.

Bounded semantic rules:

- semantic facts must pass confidence gating
- total semantic adjustment is capped at `±0.25`
- enrichment updates are recorded in route reasoning and metadata

This keeps semantic recall interpretable and prevents runaway amplification.

## Route Selection Model

Route selection is explicit and conservative.

Scoring combines:

- estimated success rate
- goal alignment
- constraint risk
- estimated cost

Design rules:

- success and goal alignment dominate
- constraint risk is penalized strongly
- cost is penalized lightly
- `pause` receives an explicit penalty so safety does not masquerade as goal completion

Hard constraint filtering:

- if hard constraints are active, routes with `constraint_risk > 0.7` are filtered from normal ranking
- if all routes are unsafe, ranking falls back to the full set so the runtime can still surface the least bad option

## Goal None-Safe Behavior

The simulator does not assume a goal exists.

When goal data is absent:

- simulation still runs
- `goal_alignment` falls back to neutral values
- no direct attribute access on `None` occurs

When goal data exists, the simulator prefers:

1. explicit `goal.metadata["goal_type"]`
2. `goal.intent`
3. conservative description inference

## Integration With Continuation

Continuation remains authoritative for lifecycle control.

Integration order:

1. Goal evaluation runs first
2. if goal is achieved or failed, simulation is skipped
3. if simulator is absent, pre-Phase-23 behavior remains intact
4. if simulator is present:
   - high-confidence executable routes may be followed directly
   - low-confidence recommendations remain advisory and are blended into the baseline decision

Important limitation:

- `repair` is simulated, but continuation does not directly execute a new repair route at this boundary
- when `repair` wins, the recommendation is preserved as advisory metadata instead of becoming a hidden new execution path

## Integration With Memory

Simulation uses the memory interfaces introduced in Phase 22:

- `recall_similar(event_type, progress)`
- `get_procedural_recommendation(goal_type)`
- `get_semantic_facts(subject)`

Simulation outputs are persisted append-only at:

- `.logs/fusion-runtime/simulation/simulation_log.jsonl`

Goal episodes can now carry `simulation_id` in metadata, preparing later feedback loops without implementing a full simulation accuracy engine yet.

## Integration With Evolution

Governed evolution can now run an optional simulation pre-check for continuation- or orchestration-impacting proposals.

This pre-check:

- does not bypass governance
- does not auto-promote anything
- can block route-impacting proposals when simulation indicates pause/safety preservation is the safest bounded response under active goal constraints

## Limitations

- route set is fixed to four options
- no speculative route synthesis exists
- no tree search exists
- no LLM rollout exists
- `repair` remains advisory at the continuation boundary
- semantic enrichment depends on explicit and bounded facts; it does not infer opaque beliefs

## How This Prepares Phase 24

Phase 23 gives Omni a safe internal forecasting layer.

That means Phase 24 can build on:

- append-only simulation audit trails
- simulation-aware continuation metadata
- simulation-linked episodes
- bounded route scoring

without needing to jump directly into unrestricted specialist or autonomous agent behavior.
