# Code Review Model

## Role

`codeReviewSpecialist.js` is a delegated specialist that reviews engineering plans before code mutation.

## Current responsibilities

- assess repository size and scope
- flag broad or risky engineering plans
- recommend tighter scope when appropriate
- surface warnings for operator-visible review

## Influence

Its output is attached to the execution request as `engineering_review` and persisted into engineering runtime state.

## Boundaries

- this is not a second planner and not a full static analyzer
- it currently reviews plan-level engineering risk more strongly than detailed code semantics
