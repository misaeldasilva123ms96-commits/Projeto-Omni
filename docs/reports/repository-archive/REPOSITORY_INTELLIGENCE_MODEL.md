# Repository Intelligence Model

## Purpose

The repository intelligence layer gives the planner a structural view of the active codebase before engineering actions begin.

## Live outputs

`repositoryAnalyzer.js` produces:
- `repository_map`
- `file_index`
- `dependency_graph`
- `language_profile`

It also detects:
- dependency manifests such as `package.json`, `pyproject.toml`, `requirements.txt`, and `Cargo.toml`
- likely entry points
- framework hints from dependency files and config files

## Runtime integration

- `queryEngineAuthority.js` runs repository analysis for engineering intent.
- The result is persisted through `runtimeMemoryStore.updateRepositoryAnalysis(...)`.
- `advancedPlannerSpecialist.js` receives `repositoryAnalysis` and uses it to build engineering plans.
- The Python runtime persists repository analysis in checkpoints, execution state, and run summaries.

## Boundaries

- This is a bounded file-system scan, not a full semantic code indexer.
- Module relationships are inferred from repository structure and dependency files, not full AST or language-server analysis.
