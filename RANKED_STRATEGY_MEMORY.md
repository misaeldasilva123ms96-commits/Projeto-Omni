# Ranked Strategy Memory

## Ranking model
- confidence
- success count
- failure count
- avoidance count
- ranking score

## Selection
- ranked suggestions are loaded before planning
- planner and simulation can consume the top strategies

## Influence
- inspection-first or branch-friendly strategies can change step ordering and coordination hints

## Provenance
- each suggestion includes task/run lineage and trigger metadata

## Boundaries
- explainable file-backed ranking only
- no hidden retraining or opaque autonomous policy changes
