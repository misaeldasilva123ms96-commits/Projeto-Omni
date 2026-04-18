# Reflection Model

## Triggers
- Hierarchical runs
- Weak or failed runs
- Policy-blocked execution paths when review is useful

## Bounded behavior
- Reflection is not recursive.
- Reflection uses explicit triggers and a bounded summary format.
- Reflection does not expose hidden chain-of-thought.

## Effects
- Produces a reflection summary linked to the run.
- Can update execution-learning memory.
- Improves future planning by feeding structured lessons back into retrieval.

## Observability
- Event: `runtime.reflection`
- Stored in checkpoint as `reflection_summary`
- Included in run summaries
