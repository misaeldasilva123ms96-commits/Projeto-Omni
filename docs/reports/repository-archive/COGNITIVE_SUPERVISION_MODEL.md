# Cognitive Supervision Model

## Role
- monitor execution tree size
- monitor branch count
- monitor negotiation depth
- prevent runaway behavior

## Outputs
- supervision alerts
- stop_execution flag
- runtime metrics

## Current limits
- max tree nodes
- max branches
- max negotiation turns

## Runtime integration
- supervision runs before execution
- if limits are exceeded, execution stops with `supervision_stop`

## Operator visibility
- checkpoint field: `supervision`
- run summary field: `supervision`
- inspection: `inspect_supervision(run_id)`
