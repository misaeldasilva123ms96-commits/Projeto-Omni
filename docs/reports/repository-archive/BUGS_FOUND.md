# Bugs Found

## 1. Node runner was hard to exercise safely in process-level integration tests

- severity: low
- scope: localized
- blocking: yes
- disposition: fixed-now
- file affected: [js-runner/queryEngineRunner.js](C:\Users\Misael\OneDrive\Área de Trabalho\Projeto omini\Projeto omini\project\js-runner\queryEngineRunner.js)

Notes:

- The runner executed `main()` immediately on import, which forced subprocess-based testing.
- In the constrained test environment, subprocess spawning from the `.mjs` harness hit `EPERM`.
- Fix applied: export the runner helpers and guard CLI execution with `if (require.main === module)`.

## 2. QueryEngine smoke path emits a module type warning under Node

- severity: low
- scope: localized
- blocking: no
- disposition: deferred
- file affected: [runtime/node/QueryEngine.ts](C:\Users\Misael\OneDrive\Área de Trabalho\Projeto omini\Projeto omini\project\runtime\node\QueryEngine.ts)

Notes:

- The smoke test still passes and captures the expected controlled failure.
- Node warns that the `.ts` file is reparsed as ESM because the package is not marked `type: module`.
- This does not block Gate 2 and should be handled in a later runtime packaging phase, not in this minimal test phase.
