# Final Project Structure

## Directory Tree

```text
project/
├─ core/
│  ├─ agents/
│  │  └─ specialistRegistry.js
│  ├─ brain/
│  │  ├─ fusedSources.js
│  │  └─ fusionBrain.js
│  ├─ memory/
│  │  └─ memoryLayers.js
│  └─ planning/
│     └─ brainExecutorContract.js
├─ runtime/
│  ├─ execution/
│  │  └─ rustRuntimeManifest.js
│  └─ permissions/
│     └─ permissionBridge.js
├─ platform/
│  ├─ cli/
│  │  └─ manifest.js
│  ├─ integrations/
│  │  └─ codexIntegration.js
│  └─ providers/
│     └─ providerRouter.js
├─ storage/
│  ├─ memory/
│  │  └─ memoryPersistence.js
│  ├─ sessions/
│  │  └─ sessionPersistence.js
│  └─ transcripts/
│     └─ transcriptPersistence.js
├─ features/
│  ├─ kairos/
│  │  └─ manifest.js
│  └─ multiagent/
│     └─ delegationLayer.js
├─ observability/
│  └─ tracing/
│     └─ runtimeAudit.js
├─ configs/
│  └─ fusion-manifest.json
├─ contract/
│  ├─ runner-schema.v1.json
│  └─ brain-executor-contract.v1.json
├─ src/
│  └─ queryEngineRunnerAdapter.js
└─ tests/
   └─ fusion/
```

## Module Roles

- `core/brain`: single high-level cognitive entrypoint
- `core/agents`: specialist subagent registry and delegation map
- `core/memory`: short-term, working, and long-term memory layering
- `core/planning`: authoritative brain-to-executor contract builder
- `runtime/execution`: Rust execution authority manifest and integration targets
- `runtime/permissions`: permission logic aligned with the Rust policy model
- `platform/cli`: retained CLI/platform adoption manifest
- `platform/integrations`: Codex and platform integration adapters
- `platform/providers`: provider selection and model abstraction
- `storage/memory`: persisted memory snapshot shape
- `storage/sessions`: short-term session snapshots
- `storage/transcripts`: audit/event persistence
- `features/kairos`: optional proactive assistant layer
- `features/multiagent`: explicit specialist delegation policy
- `observability/tracing`: execution trace shape and audit capture

## Dependency Boundaries

- `core/*` may depend on `runtime/*`, `platform/*`, `storage/*`, and `observability/*`
- `runtime/*` must not depend on `core/*`
- `platform/*` must stay isolated from cognition logic
- `storage/*` must remain persistence-only
- `features/kairos/*` must not become a dependency of the default request path

## Execution Flow

1. React frontend sends request to Rust API
2. Rust API passes request to Python orchestrator
3. Python orchestrator calls Node runner
4. Node runner loads `src/queryEngineRunnerAdapter.js`
5. Adapter delegates to `core/brain/fusionBrain.js`
6. Fusion brain:
   - analyzes intent and complexity
   - selects specialists
   - builds brain-to-executor action contract
   - routes provider choice
   - checks permissions
   - executes current first-pass action path
   - records an audit entry
7. Final grounded response returns through Python and Rust unchanged
