# Autonomous Coding Workflow

## Live workflow

The current engineering workflow is:

1. understand engineering intent
2. analyze repository structure
3. build an engineering-aware plan
4. review plan risk with `codeReviewSpecialist`
5. execute engineering steps
6. run tests
7. attempt bounded debug iterations when configured
8. persist repository, patch, debug, and workspace state

## Planner behavior

For engineering intent, `advancedPlannerSpecialist.js` can emit steps such as:
- repository tree inspection
- dependency inspection
- git status inspection
- test execution
- autonomous debug loop

## Runtime integration

- planning stays under one cognitive authority
- execution still stays under one execution authority
- the engineering workflow is attached to execution requests as `engineering_workflow`

## Boundaries

- the current live path is strongest for “analyze repo” and “fix failing tests safely”
- broad feature implementation across many files is not yet fully autonomous
