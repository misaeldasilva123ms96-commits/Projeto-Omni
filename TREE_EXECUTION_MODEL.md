# Tree Execution Model

## Core model
- `execution_tree.root_node_id`
- `nodes[]`

## Node fields
- `node_id`
- `parent_id`
- `branch_id`
- `owner_agent`
- `goal_id`
- `step_id`
- `state`
- `retries`
- `children`

## States
- pending
- running
- completed
- partial
- failed

## Runtime behavior
- step execution updates the matching tree node
- parent nodes roll up child completion or failure
- branch nodes remain bounded and safe

## Persistence
- checkpoint stores `execution_tree`
- run summaries also expose `execution_tree`

## Visualization readiness
- the tree payload is machine-readable and ready for future UI rendering
