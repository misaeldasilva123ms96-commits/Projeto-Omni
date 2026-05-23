# Workspace Model

## Purpose

Engineering tasks need a consistent workspace abstraction for snapshotting, mutation, and recovery.

## Live capabilities

`workspace_manager.py` supports:
- creation of task workspaces from a source root
- workspace snapshots with file hashes
- file rollback from stored backups

## Persisted state

Workspace information is exposed through:
- execution state
- checkpoints
- run summaries
- task service inspection endpoints

## Boundaries

- workspaces are file-system copies and snapshots, not full Git worktrees
- this phase does not yet manage long-lived isolated engineering branches automatically
