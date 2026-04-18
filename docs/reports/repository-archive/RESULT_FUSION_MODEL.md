# Result Fusion Model

## Normalization
- executed steps are normalized into contributions with specialist, branch, tool, summary, and confidence

## Conflict detection
- contributions with the same conflict key are compared
- differing summaries produce explicit conflict records

## Merge policy
- highest-confidence grounded contribution wins
- unresolved conflicts remain visible to operators

## Branch handling
- winner branch and pruned branches are attached to fusion data

## Operator view
- run intelligence includes contribution count, specialist set, branch count, and winner branch
