# PR Workflow Model

## Goal

Prepare merge-ready outputs without claiming a full hosted PR lifecycle yet.

## Live output

`pr_summary_generator.py` builds:

- title
- summary
- files changed
- why
- verification
- known risks
- merge readiness

## Grounding

The summary is built from:

- executed engineering runtime data
- milestone state
- patch sets
- verification summary
- repository analysis
- impact analysis

## Boundary

This is PR-style output, not automatic branch push or hosted PR creation.
