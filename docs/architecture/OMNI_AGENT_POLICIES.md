# Omni Agent Policies

## 1. Purpose

Projeto Omni is evolving toward a safe autonomous engineering platform. That evolution cannot rely on implicit conventions or ad hoc execution decisions. Policy-driven execution is required so that planning, mutation, verification, git activity, and recovery remain bounded, explainable, and reviewable under one cognitive authority and one execution authority.

These policies define the behavioral contract future Omni agents and subsystems must obey. They are written for operational enforcement, not for aspirational guidance.

## 2. ExecutionPolicy

Execution is allowed when:

- the task has been classified sufficiently
- the active mode permits execution
- the requested capability is within scope
- required evidence is present
- policy evaluation returns allow or allow-with-constraints

Planning is required first when:

- the task implies mutation
- the impact surface is not yet known
- verification requirements are unclear
- the request spans multiple files, milestones, or modules
- the task involves privileged or high-risk tools

Execution must be blocked when:

- policy requires approval not yet granted
- evidence is insufficient for safe mutation
- the workspace or repository state is inconsistent
- the requested action exceeds scope or declared mode
- verification cannot be defined for a structural change

## 3. MutationPolicy

Code changes are allowed only when:

- the target scope is identified
- a rollback path exists
- a verification path exists
- the mutation is attributable to a specific task/run/milestone context

Every mutation-capable path must provide:

- the affected file set or patch set
- a reversible representation where feasible
- pre-mutation rationale
- post-mutation verification evidence

Uncontrolled mutation is prohibited. This includes:

- speculative wide edits without impact evidence
- mutation outside the active milestone or declared task scope
- direct destructive writes with no rollback strategy
- silent mutation during fallback or recovery paths

## 4. GitPolicy

Future Omni engineering work must follow branch discipline:

- no direct mutation of `main` by autonomous workflows
- work should occur on task-scoped or milestone-scoped branches/workspaces
- branch naming should encode purpose or task identity

Commit discipline requires:

- intentional commit boundaries
- commit messages grounded in actual executed work
- no “success” commits without verification evidence

PR and merge expectations:

- PR-style summaries must be generated from real runtime data
- merge readiness requires verification evidence, unresolved blocker visibility, and policy compliance
- a branch is not merge-ready solely because the model believes the change is correct

Milestones and branches:

- larger tasks may map milestone groups to branch/workspace boundaries
- milestone completion should be traceable to branch state and verification outcomes

## 5. ToolPolicy

The runtime must use the right tool for the right task.

Tool usage policy requires:

- choose read tools before write tools
- minimize context pulled into each execution step
- avoid redundant scanning when repository intelligence already exists
- avoid uncontrolled tool chaining across unrelated scopes
- prefer structured internal adapters over raw shell mutation where supported

Operational expectations:

- read before write
- verify before declare success
- keep tool sequences bounded and auditable
- never escalate privilege without explicit policy allowance

## 6. ScopePolicy

Scope must remain explicit throughout execution.

Agents must not:

- expand from local fix to broader refactor without justification
- modify unrelated files “while nearby”
- create architectural drift under the guise of convenience
- widen repository impact without reclassification and updated evidence

If new information changes the real scope, the correct response is:

- reclassify
- re-enter planning
- update evidence and verification expectations

Scope drift is a policy event, not a stylistic concern.

## 7. VerificationPolicy

No engineering success declaration is valid without verification evidence appropriate to the change.

Verification expectations include:

- tests before success declaration
- targeted validation for narrow changes
- broader validation for structural or cross-module changes
- recorded outcomes for verification runs

Structural changes require stronger evidence such as:

- impact-aware test selection
- lint/typecheck where available
- patch-set or milestone validation
- explicit unresolved-risk reporting if complete validation is not possible

Merge readiness requires:

- successful verification or honest degraded status
- policy compliance
- unresolved blockers surfaced explicitly
- reviewer-facing summary derived from executed work

## 8. FailurePolicy

Failures must be classified, not flattened into generic retry behavior.

For each failure, the runtime should determine whether to:

- degrade
- retry
- rollback
- stop
- escalate to human oversight

Expected behavior by class:

- `tool_failure`: retry only if retry policy allows and idempotence is safe
- `verification_failure`: rollback or enter bounded debug/replan path
- `policy_block`: stop and surface operator-facing reason
- `evidence_insufficient`: stop or return to planning, never mutate forward
- `workspace_failure`: stop or rebuild workspace before continuing
- `partial_success`: report explicitly and avoid silent “success” promotion

When evidence is insufficient, the runtime must not guess its way into mutation. Insufficient evidence is a blocking condition unless the active mode supports non-mutating degraded output.

## 9. Human Oversight Boundaries

Future phases may automate:

- read-heavy exploration
- planning and decomposition
- bounded verification
- bounded recovery loops
- generation of reviewer-facing summaries

Future phases should still require explicit approval for:

- high-risk or wide-scope mutation
- branch or repository operations with merge consequences
- privileged tool escalation
- actions that exceed declared scope or evidence confidence
- any future production- or deployment-impacting mutation path

Safe autonomy boundaries:

- autonomy is allowed inside policy, mode, and evidence constraints
- autonomy ends where risk exceeds current evidence or approval model
- operator visibility is mandatory at those boundaries

## 10. Policy Enforcement Model

These policies are intended to become executable through the Policy Engine introduced in Phase 11.

The enforcement model should:

- evaluate policy against classified intent and active mode
- attach policy outcomes to planned actions and execution state
- block disallowed work before mutation or privileged tool use
- emit policy outcomes into observability and operator inspection surfaces
- feed failure and recovery decisions back into run intelligence

Roadmap alignment:

- Phase 11 - Cognitive Control Layer: introduces the enforcement surface and mode engine
- Phase 12 - Capability Routing: binds policy to routed capability selection
- Phase 13 - Structured Memory & Context Budget: makes context selection policy-aware
- Phase 14 - Verification-First Engineering: makes verification policy operational
- Phase 15 - Self-Repair Foundation: ties failure policy to bounded recovery
- Phase 16 - Long-Horizon Execution: extends enforcement across milestones and resumes
- Phase 17 - Multi-Agent Review Loop: governs specialist review and disagreement
- Phase 18 - Operational Intelligence: surfaces policy trends and blocked-path analytics
- Phase 19 - Autonomous PR Lifecycle: enforces git, mutation, and verification requirements through PR state
- Phase 20 - Self-Evolving Engineering Platform: evolves capability safely under explicit governance instead of implicit drift

The purpose of enforcement is not to slow the system arbitrarily. The purpose is to ensure that increasing autonomy results in stronger discipline, clearer evidence, and safer operation.
