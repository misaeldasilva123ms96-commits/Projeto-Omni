# Branch Execution Model

## Creation rules
- branch execution is opt-in
- current maximum is 2 safe branches
- only read-only branches are permitted

## Lifecycle
- pending
- running
- completed
- pruned
- failed

## Merge model
- current merge mode: `winner-selection`
- winner is chosen from real executed branch results
- losing branches are persisted as pruned, not hidden

## Persistence
- `branch_state` is stored in checkpoints
- run summaries include winner and pruned branches

## Safety
- mutating tools cannot fan out across branches
- policy can stop branching before execution
