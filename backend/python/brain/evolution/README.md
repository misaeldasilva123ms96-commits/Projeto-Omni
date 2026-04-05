# Evolution Layer

The evolution layer turns passive logs into an auditable, heuristic self-optimization loop.

## Loop Diagram

```text
Recent sessions + transcripts + learning.json
                    |
                    v
              +-----------+
              | Evaluator |
              +-----------+
                    |
                    v
          scored turns + flags + overall
                    |
                    v
          +-------------------+
          | Pattern Analyzer  |
          +-------------------+
                    |
                    v
      weak patterns / strong patterns / adjustments
                    |
                    v
          +-------------------+
          | Strategy Updater  |
          +-------------------+
                    |
          score_gain > threshold ?
              /             \
            yes              no
            |                |
            v                v
   snapshot strategy_vN   reject proposal
            |
            v
   orchestrator reads strategy_state.json
```

## Score Metrics

- `relevance`: token-level semantic overlap between input and output, weighted by keyword carryover.
- `coherence`: checks if the answer still matches the recent session context and conversation flow.
- `completeness`: estimates whether the user request was actually addressed, not just acknowledged.
- `efficiency`: measures whether the answer length matches the task size, avoiding both under-answering and verbosity.

`overall` is a weighted score:

```text
0.35 relevance
0.20 coherence
0.30 completeness
0.15 efficiency
```

## Files

- `evaluator.py`: creates one multidimensional evaluation per response
- `pattern_analyzer.py`: identifies weak and strong behavior clusters
- `strategy_updater.py`: writes versioned strategy snapshots and supports rollback
- `evolution_loop.py`: daemon loop that periodically proposes or applies updates
- `dashboard.py`: CLI view into scores, patterns and strategy history
- `snapshots/strategy_vN.json`: immutable strategy snapshots

## Dashboard Guide

Run:

```text
python -m brain.evolution.dashboard
```

What to read first:

- `Current evolution version`: active strategy state used by the orchestrator
- `Average score (recent)`: health indicator of recent turns
- `Top weak patterns`: where the system still underperforms
- `Top strong patterns`: stable areas where the system is already reliable
- `Underused capabilities`: capabilities that may need routing changes or demotion
- `Strategy versions`: recent automatic strategy updates with justification

Rollback:

```text
python -m brain.evolution.dashboard rollback 2
```

This restores `strategy_v2.json` as the active strategy state without changing the Rust/Python stdout contract.
