# Execution State Schema

## Top-level object
- `session_id`
- `task_id`
- `run_id`
- `goal_tree`
- `branch_states`
- `agent_contributions`
- `negotiation`
- `simulation_results`
- `strategy_usage`
- `policy_decisions`
- `fusion_outputs`
- `runtime_metrics`
- `supervision`

## Purpose
- dashboard-ready execution visualization
- operator debugging
- machine-readable runtime state export

## Source
- built in `backend/python/brain/runtime/execution_state.py`
- embedded into `run-summaries.jsonl`
