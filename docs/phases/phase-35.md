# Phase 35 — Strategy Adaptation Engine

Phase 35 introduces **controlled, observable strategy adaptation** between Phase 32 memory context and Phase 31 reasoning. It consumes **Phase 34 runtime learning records** (read-only) and emits a **`StrategyDecision`** with explicit **primary** and **fallback** `ExecutionStrategy` profiles — without mutating code, prompts, or learning artifacts.

## Implemented Scope

- **`StrategyEngine`** (`brain/runtime/strategy/strategy_engine.py`): loads the latest `RuntimeLearningStore` record when none is injected; delegates to **`StrategySelector`**.
- **`ExecutionStrategy`**: `mode` (`fast` | `deep` | `critical`), `path` (`direct` | `swarm` | `guarded`), `validation_level`, `reasoning_depth` (1–5), `risk_tolerance` (0–1).
- **`StrategyDecision`**: selected + **conservative fallback** strategies, textual `reason`, `confidence`, `signals_used`, and **`StrategyAdaptationTrace`** for audit.
- **`strategy_rules.py`**: deterministic heuristics from OIL intent, message risk tokens, memory `selected_count`, and learning `outcome_class` / negative signal counts / prior `duration_ms`.
- **Runtime integration** (`BrainOrchestrator.run`): after memory intelligence trace, **before** `ReasoningEngine.reason`, runs strategy selection, appends **`runtime.strategy_adaptation.trace`**, stamps `oil_request.extensions["strategy_adaptation"]`, passes **`preferred_mode`** into reasoning. Failures degrade to empty strategy payload and default reasoning mode selection.
- **Control/session**: `control_metadata["strategy_adaptation"]` and session `strategy_adaptation` (advisory; control plane remains authoritative).
- **Observability**: `read_recent_strategy_adaptation_traces` / `read_latest_strategy_adaptation_trace` + snapshot fields.

## Non-goals (explicit)

- No automatic code or prompt mutation, no hidden weight tuning, no self-evolution loops.
- **Phase 36+** performance tuning, advanced multi-agent coordination, dynamic replanning — not implemented.

## Flow

```text
OIL + memory context → StrategyEngine → (preferred_mode + extensions) → Reasoning → Planning → Execution → Learning
```

## Verification

Run `tests/runtime/strategy/test_strategy_engine.py` and regressions for Phases 31–34 paths (`reasoning`, `planning`, `learning`, `observability`, orchestrator integration).
