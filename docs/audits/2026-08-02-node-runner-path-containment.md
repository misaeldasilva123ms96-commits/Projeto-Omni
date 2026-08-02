# Node Runner Path-Containment Evidence

**Evidence date:** 2026-08-02

**Source `main`:** `cd29ffeb53d582cacb06aa28bf27e039ef77e4dc`

**Branch:** `hardening/node-runner-path-containment`

**Technical commit:** `fffe0a20e1e4c477d3978b8ffddd4a0d923acc58`

**Corrective implementation head:** `0981bb093fc96b92c925d86414f95234d1f744de`

**Pull request:** [#604](https://github.com/misaeldasilva123ms96-commits/Projeto-Omni/pull/604) (draft)

This report records commit-bound application-level validation. It does not
claim operating-system sandboxing, production readiness, deployment approval,
or protection from an actor already able to replace arbitrary local files.

## Prior boundary and threat model

The earlier Python preflight derived several paths and primarily reported
whether they existed. Runtime variables could influence the project root,
runner, schema, adapter, executable, module resolution, and working directory;
the transport accepted a mutable diagnostic dictionary. JavaScript also
performed independent candidate discovery and agent-memory traversal without a
single explicit containment policy.

The protected boundary is the Python-to-Node process launch and the files the
Node runner reads or imports. The threat model includes malformed deployment
configuration, provider/session overlays, relative or traversal paths,
symlink/junction substitution, unsafe file types, inherited Node startup
variables, and tampering between preflight and transport invocation.

## Authoritative root and Python preflight

`NodePathPolicy` canonicalizes an absolute existing directory, rejects symlink
or Windows reparse-point components, and requires repository markers:

```text
package.json
backend/python
backend/rust
js-runner/queryEngineRunner.js
contract/runner-schema.v1.json
```

The active Python entrypoint and configured Python root must belong to that
root under `backend/python`. An external imitation tree containing copied
markers cannot authorize the running code. Containment uses path-component
semantics (`Path.relative_to`) rather than string prefixes. The selected
working directory is always the canonical authorized root.

Required files fail closed when missing. Optional engine candidates may be
absent, but an existing candidate of the wrong type or one reached through a
symlink/junction fails closed. The corrective implementation head also checks
parent components before returning for a missing optional leaf.

## File allow-list and independent JavaScript validation

The only runner and schema are:

```text
js-runner/queryEngineRunner.js
contract/runner-schema.v1.json
```

The adapter allow-list is:

```text
src/queryEngineRunnerAdapter.js
src/queryEngineRunnerAdapter.mjs
core/brain/fusionBrain.js
```

The engine-candidate allow-list is:

```text
dist/QueryEngine.js
build/QueryEngine.js
src/QueryEngine.js
runtime/node/QueryEngine.js
src/QueryEngine.ts
runtime/node/QueryEngine.ts
```

`js-runner/pathPolicy.js` independently derives the root from the runner's
location. Configured `BASE_DIR` and `NODE_RUNNER_BASE_DIR` must canonicalize to
that exact root. Schema and adapter overrides must equal an exact allow-listed
file. Fixed engine candidates are revalidated before existence checks and
dynamic import. Selected artifacts must be regular files inside the root with
no symlink, junction, or reparse-point component. Candidate failures expose
safe labels instead of host paths.

Node does not inherit or introduce a TypeScript loader. TypeScript candidates
remain eligible only through Bun's native behavior; an arbitrary Node loader
is outside this change.

## Executable, environment, and transport policy

The executable policy accepts only bare `node`, `node.exe`, `bun`, or
`bun.exe` resolved through the controlled `PATH`, or an absolute path whose
canonical target is a regular executable with one of those identities.
Relative paths with separators, embedded arguments, directories, missing or
non-regular files, and unsupported runtime identities fail before launch. A
normal operating-system executable symlink is permitted only when its resolved
target satisfies that policy. Node/Bun need not reside inside the project.

Provider overlays accept only recognized provider credential/model keys. They
cannot add arbitrary provider identifiers or replace these reserved controls:

```text
BASE_DIR
OMNI_BASE_DIR
NODE_RUNNER_BASE_DIR
NODE_BIN
OMNI_NODE_BIN
OMNI_JS_RUNTIME
OMNI_JS_RUNTIME_BIN
OMNI_JS_RUNTIME_SOURCE
OMNI_JS_RUNTIME_SELECTED
RUNNER_SCHEMA_PATH
RUNNER_ADAPTER_PATH
NODE_OPTIONS
NODE_PATH
BUN_BIN
```

Trusted execution variables are applied after the overlay. Inherited
`NODE_OPTIONS` and `NODE_PATH` are removed both while constructing the adapter
environment and immediately before launch, preventing preload, loader, eval,
inspection, or external module-resolution influence through those variables.

The transport now requires a frozen, authenticated
`ValidatedNodeExecutionPlan`, verifies its integrity, reconstructs the path
policy, and revalidates the executable, root, cwd, runner, artifacts, and
reserved environment values immediately before `subprocess.run()`. The command
is exactly the validated executable plus validated runner. It uses
`shell=False`; the request payload remains on stdin. Capture, UTF-8 decoding,
replacement decoding errors, non-raising exit handling, and the existing
timeout behavior are retained. Modified dictionaries or plans fail before
subprocess creation. Public degradation remains generic and path-redacted.

## Agent-memory traversal

Only `.claude/agent-memory` and `.claude/agent-memory-local` under the
canonical root are eligible. Public-demo mode still disables these reads.
Traversal is deterministic and permission-safe, does not follow symlinked or
reparse-point roots, directories, or `MEMORY.md` files, and is bounded by:

```text
maximum depth: 8
maximum visited entries: 512
maximum accepted MEMORY.md files: 64
maximum aggregate accepted content: 16 KiB
```

## Focused and regression validation

Fresh local results on the implementation content included:

- `git diff --check`: passed.
- Python path-policy tests: 15 passed, 5 platform skips on Windows.
- Python node-runner tests: 9 passed.
- Python node-transport tests: 4 passed.
- Existing JS runtime-adapter tests: 11 passed.
- Existing Python transport tests: 6 passed.
- Existing bridge-pipeline tests: 18 passed.
- Node path-containment tests: 9 tests, 8 passed and one Windows symlink
  fixture skipped; the Windows junction-root fixture passed.
- Public-demo container validation: passed.
- Complete Node runtime suite: passed.
- `npm run test:security`: passed in the prepared Python 3.11 security
  environment.
- Python backend suite after the CI correction: 737 passed, 5 skipped, 20
  subtests passed.
- `npm run validate:public-demo`, `npm run validate:audit-pack`, and
  `npm run validate:env-aliases`: passed.
- Rust formatting and Clippy with warnings denied: passed.
- Rust locked test suite: 170 passed.

The first local broad Python runtime attempt completed 1851 tests but had four
Rust tool-bridge failures caused by a fresh Windows temporary Cargo target and
its cold build exceeding the bridge timeout. The same target built successfully
outside pytest in 4 minutes 52 seconds, and its direct action then passed in
1.65 seconds. No Rust source changed. The authoritative Linux implementation
head subsequently passed both the complete Python and full runtime workflows.

Tests cover external/imitation roots, sibling-prefix and traversal rejection,
inside/outside symlinks, symlinked parents, Windows junctions, missing and
wrong-type artifacts, optional unsafe candidates, executable forms, reserved
overlays, startup-variable stripping, immutable-plan tampering, stdin payloads,
no-shell launch, sanitized failures, fixed dynamic imports, bounded memory
traversal, provider credentials, unavailable-runtime fallback, circuit-breaker
compatibility, Python-to-Node execution, and Runtime Truth compatibility.

## Docker evidence

The local daemon-backed smoke used Docker Engine 29.4.1 and Compose 5.1.3,
built image
`sha256:51b6e563347dec2930ad7ef580a800814f40603d8cc2c40bd425be962cddf148`,
verified `/app` as the controlled root, the read-only root filesystem,
canonical runner execution, safe labels, Runtime Truth
`DIRECT_LOCAL_RESPONSE_WITH_PROVIDER_UNAVAILABLE`, graceful shutdown with exit
0, and removal of the container, network, and image.

The authoritative hosted Docker job is
[91524653683](https://github.com/misaeldasilva123ms96-commits/Projeto-Omni/actions/runs/30758463759/job/91524653683).
It used Compose 2.38.2, built image
`sha256:f65338e9239c06bcc123571872e68bd4e8e77be1dfedccdee41413610bfc40a3`,
reported the same Runtime Truth classification, and completed shutdown with
exit 0.

## Dependency and secret validation

- Root `npm audit --audit-level=high`: 0 vulnerabilities.
- `pip-audit -r backend/python/requirements.txt`: no known vulnerabilities.
- `pip-audit -r backend/python/requirements-test.txt`: no known
  vulnerabilities.
- `(cd backend/rust && cargo audit)`: no advisory vulnerability; the existing
  allowed yanked warning for `spin 0.9.8` remains.
- Gitleaks 8.30.1 found no leaks in each changed implementation file, either
  implementation commit, or the complete implementation range.

## Authoritative implementation-head workflows

GitHub marks both implementation commit signatures as verified with
`reason: valid`. Every workflow on corrective implementation head
`0981bb093fc96b92c925d86414f95234d1f744de` completed successfully:

| Workflow | Run | Conclusion |
| --- | --- | --- |
| Pull Request Labeler | [30758462755](https://github.com/misaeldasilva123ms96-commits/Projeto-Omni/actions/runs/30758462755) | success |
| Omni Node CI | [30758463712](https://github.com/misaeldasilva123ms96-commits/Projeto-Omni/actions/runs/30758463712) | success |
| Security Checks | [30758463714](https://github.com/misaeldasilva123ms96-commits/Projeto-Omni/actions/runs/30758463714) | success |
| Omni Python CI | [30758463724](https://github.com/misaeldasilva123ms96-commits/Projeto-Omni/actions/runs/30758463724) | success |
| Omni Live E2E CI | [30758463725](https://github.com/misaeldasilva123ms96-commits/Projeto-Omni/actions/runs/30758463725) | success |
| Frontend CI | [30758463726](https://github.com/misaeldasilva123ms96-commits/Projeto-Omni/actions/runs/30758463726) | success |
| Omni Security CI | [30758463729](https://github.com/misaeldasilva123ms96-commits/Projeto-Omni/actions/runs/30758463729) | success |
| Omni Runtime CI | [30758463736](https://github.com/misaeldasilva123ms96-commits/Projeto-Omni/actions/runs/30758463736) | success |
| CI | [30758463738](https://github.com/misaeldasilva123ms96-commits/Projeto-Omni/actions/runs/30758463738) | success |
| Lint & Static Checks | [30758463739](https://github.com/misaeldasilva123ms96-commits/Projeto-Omni/actions/runs/30758463739) | success |
| Docker Runtime Smoke | [30758463759](https://github.com/misaeldasilva123ms96-commits/Projeto-Omni/actions/runs/30758463759) | success |
| Omni Public Demo CI | [30758463820](https://github.com/misaeldasilva123ms96-commits/Projeto-Omni/actions/runs/30758463820) | success |

## Residual limitations

- Validation is application-level, not an operating-system sandbox.
- A privileged local attacker is outside this guarantee.
- TOCTOU replacement by an actor with filesystem write permission is not
  completely eliminated.
- Node/Bun executables may legitimately reside outside the project root.
- No seccomp, AppArmor, or SELinux policy was added.
- No production deployment validation was performed.
- No hostile multi-user host test was performed.
- No penetration test was performed.
- No distributed runtime isolation was implemented or validated.

This pull request must not be merged automatically. Final review and merge
remain manual and exclusive to Misael.
