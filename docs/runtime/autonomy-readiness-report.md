# Omni Autonomy Readiness Report

**Date:** 2026-06-26
**Branch:** `feature/autonomy-readiness-report`
**Base:** `main` (after PR #411 merged by Misael)
**Author:** Misael
**Review status:** Draft — not approved for autonomous execution

---

## 1. Executive Summary

Omni has implemented an **advisory-only autonomy stack** that evaluates runtime
context and produces structured decisions (continue, retry, replan, pause,
escalate, abort-safe). Every decision is marked `advisory=true`. **No
autonomous execution path is wired.** Two high-risk decision types
(`SELF_REPAIR`, `SWITCH_PROVIDER`) are statically disabled and fall back to
`CONTINUE`. The system can observe, fingerprint errors, track progress versus
stagnation, and display decisions in the Cockpit — but it **cannot execute**
any of those decisions autonomously.

**Omni autonomy is NOT approved for autonomous execution yet. Current mode is
advisory-only.**

---

## 2. Current Status: Advisory-Only

| Dimension | Status |
|-----------|--------|
| Decision engine | Implemented — `AutonomyController.decide()` |
| Decision execution | **Not wired** — no executor interprets advisory output |
| Default autonomy level | `supervised` (equivalent to L1_ADVISORY) |
| Disabled decisions | `SELF_REPAIR`, `SWITCH_PROVIDER` — fall back to `CONTINUE` |
| Disabled actions (policy) | `push_main`, `bypass_ci`, `deploy_production`, `force_merge`, etc. |
| Persistence | In-memory receipt log + optional governance events via MemoryFacade |
| Cockpit visibility | Read-only: current decision, controller stats, decision timeline |
| Human-in-the-loop | Escalation reports built; no automated escalation delivery |

---

## 3. Architecture Overview

```
Runtime Error/Event
       |
       v
  SmartErrorProgressTracker  ──►  ErrorFingerprint (SHA256)
       |                           ProgressTrackerOutput
       v
  AutonomySessionTracker     ──►  Per-session state (process-local)
       |
       v
  AutonomyController.decide()
       |
       v
  evaluate_policy()          ──►  AutonomyDecision { advisory=true }
       |
       ├──► AutonomyReceipt (in-memory receipt log)
       ├──► GovernanceEvent (via MemoryFacade → JSONL | SQLite)
       └──► EscalationReport (if ESCALATE_TO_MISAEL)
              |
              v
         Cockpit (read-only UI)
```

**Important:** The controller output is advisory only. No downstream executor
consumes the decision to perform autonomous actions.

---

## 4. Implemented Components

### Core Runtime (`backend/python/brain/runtime/autonomy/`)

| File | Purpose |
|------|---------|
| `autonomy_controller.py` | `AutonomyController` — orchestrates policy evaluation, receipts, governance events |
| `autonomy_policy.py` | `evaluate_policy()` — context evaluation against thresholds |
| `autonomy_models.py` | `DecisionType`, `AutonomyContext`, `AutonomyDecision`, `DISABLED_DECISIONS` |
| `autonomy_session_state.py` | `AutonomySessionState` — dataclass for per-session metadata |
| `autonomy_session_tracker.py` | `AutonomySessionTracker` — tracks stagnation/progress across turns |
| `autonomy_receipt.py` | `AutonomyReceipt`, `AutonomyReceiptLog` — audit receipts |
| `autonomy_escalation.py` | `EscalationReport`, escalation category classifier |
| `error_progress_tracker.py` | `SmartErrorProgressTracker` — error fingerprinting, scoring |
| `error_progress_models.py` | `ErrorFingerprint`, `ProgressTrackerOutput`, `StrategyAttempt` |

### Governance Policy (`backend/python/brain/runtime/governance/`)

| File | Purpose |
|------|---------|
| `autonomy_types.py` | `AutonomyPolicyRequest`, `AutonomyPolicyDecision` |
| `autonomy_policy.py` | `evaluate_autonomy_policy()` — level-based policy (L0–L7), always-blocked actions |

### Memory / Evidence (`backend/python/brain/memory/`)

| File | Purpose |
|------|---------|
| `runtime_integration.py` | `record_governance_event()` — lazy-init `MemoryFacade` |
| `evidence_memory.py` | `EvidenceMemoryStore` — JSON file-based evidence records |
| `memory_facade.py` | `MemoryFacade` — dual writes to JSONL + optional SQLite |
| `hybrid.py` | `HybridMemory` — user/preferences/learning store |

### Frontend Cockpit (`frontend/src/`)

| File | Purpose |
|------|---------|
| `components/runtime/RuntimeAutonomyTab.tsx` | Read-only autonomy panel showing current decision, stats, timeline |
| `lib/runtimeTypes.ts` | TypeScript types: `RuntimeAutonomyStatus`, `RuntimeAutonomyStats`, `AutonomyTimelineItem` |
| `lib/omniData.ts` | `fetchAutonomyTimeline()` — reconstructs timeline from Supabase message metadata |

### Tests

| Path | Purpose |
|------|---------|
| `tests/runtime/test_autonomy_operating_model.py` | Tests for governance-level autonomy policy |
| `backend/python/tests/runtime/autonomy/test_autonomy_controller.py` | Controller unit tests |
| `backend/python/tests/runtime/autonomy/test_autonomy_policy_tracker.py` | Tracker-merged policy tests |
| `backend/python/tests/runtime/autonomy/test_autonomy_session_tracker.py` | Session tracker tests |
| `backend/python/tests/runtime/autonomy/test_autonomy_wiring_session_state.py` | Wiring tests |

---

## 5. Evidence Flow

1. **Error occurs** in runtime → metadata passed to `AutonomyContext`
2. **SmartErrorProgressTracker.classify()** generates an `ErrorFingerprint` (SHA256 of normalized fields) and a `ProgressTrackerOutput` with stagnation/progress scores
3. **AutonomyController.decide()** calls `evaluate_policy()` with context + tracker metadata
4. **evaluate_policy()** returns an `AutonomyDecision { advisory=true }`
5. **AutonomyReceipt** is logged in-memory (`AutonomyReceiptLog`)
6. **GovernanceEvent** is recorded via `MemoryFacade.record_governance_event()` (if available) — written to JSONL (default) and optionally SQLite
7. **Cockpit** reconstructs the decision timeline from `cognitiveRuntimeInspection.autonomy_evaluation` in Supabase chat message metadata

**Known limitations:**
- No dedicated evidence persistence endpoint — evidence is embedded in message metadata
- The `EvidenceMemoryStore` (JSON file) exists but is not wired into the controller
- Governance events are fire-and-forget with silent failure on error
- No evidence query API for the frontend — timeline reconstruction is Supabase-based

---

## 6. Memory / Persistence Behavior

| Store | Default | Opt-in | Scope |
|-------|---------|--------|-------|
| `AutonomyReceiptLog` | In-memory list | N/A | Process-local; lost on restart |
| `AutonomySessionTracker` | In-memory dict | N/A | Process-local; lost on restart |
| `SmartErrorProgressTracker` | In-memory dict | N/A | Process-local; lost on restart |
| Governance events | JSONL (`MEMORY_BACKEND_JSONL`) | SQLite via `OMINI_ENABLE_SQLITE_MEMORY=true` | Durable across restarts if enabled |
| Cockpit timeline | Supabase `chat_messages.metadata` | Always-on (depends on Supabase) | Durable via Supabase |
| Evidence store | JSON file | N/A | File-based, not wired to controller |

**SQLite is opt-in.** The safe default backend is JSONL. Without SQLite enabled,
governance events are written only to JSONL (append-only audit mirror).

---

## 7. Cockpit Visibility

The **Runtime Inspector** includes an **Autonomia** tab (`RuntimeAutonomyTab`)
that displays:

- **Current decision** — decision type, risk level, advisory flag, reason
- **Progress Tracker** — progress score, stagnation score, state, stagnant
  attempts, fingerprint ID, recommended hint, evidence summary
- **Controller Metrics** — total evaluations, escalation rate, active sessions,
  last decision, advisory mode indicator
- **Decision Timeline** — reverse-chronological list of past autonomy decisions
  with risk level, fingerprint, progress/stagnation scores, strategies attempted

All displays are **read-only**. No controls for changing autonomy level,
enabling decisions, or executing actions.

The timeline is sourced from Supabase message metadata, not from the controller
receipt log (which is process-local).

---

## 8. Safety Guarantees Currently Enforced

### Static (code-level)

1. **All decisions are advisory** — `AutonomyDecision.advisory = True` always
2. **Disabled decisions** — `DISABLED_DECISIONS = {SELF_REPAIR, SWITCH_PROVIDER}`;
   any policy return of these types is overridden to `CONTINUE`
3. **Hard-coded escalation triggers** in `evaluate_policy()`:
   - Direct main push or merge attempted → `ESCALATE_TO_MISAEL`
   - Secret detected → `ESCALATE_TO_MISAEL`
   - Protected file involved → `ESCALATE_TO_MISAEL`
   - Unsafe CI or security signal → `ESCALATE_TO_MISAEL`
   - Conflict detected → `ESCALATE_TO_MISAEL`
   - Production/deploy action → `ESCALATE_TO_MISAEL`
   - No safe next action → `ABORT_SAFE`
4. **Always-blocked actions** in governance policy: `push_main`, `bypass_ci`,
   `deploy_production`, `force_merge`, `merge_with_failing_checks`, etc.
5. **Safe defaults** — `autonomy_level = "supervised"`,
   `SAFE_DEFAULT_BACKEND = "jsonl"`

### Process (operational)

6. **Manual merge by Misael only** — no automated PR merge enabled
7. **No auto-merge** — disabled at process level
8. **No direct push to main** — enforced by both code and process
9. **Branch-only work** — all changes on feature branches
10. **Read-only UI** — Cockpit shows data but has no mutation controls

---

## 9. Explicitly Disabled Actions

The following are blocked at the governance policy level
(`backend/python/brain/runtime/governance/autonomy_policy.py:68`):

- `push_main`
- `bypass_ci`
- `lower_ci_threshold`
- `skip_tests`
- `disable_security_scan`
- `read_secrets`, `expose_secrets`
- `delete_production_data`
- `deploy_production`
- `change_billing`
- `approve_security_policy`
- `edit_governance_policy_directly`
- `approve_vault_note`
- `promote_to_reviewed`, `promote_to_approved`
- `force_merge`
- `merge_with_failing_checks`

Additionally, at the controller level
(`backend/python/brain/runtime/autonomy/autonomy_models.py:52`):

- `SELF_REPAIR` — disabled, falls back to `CONTINUE`
- `SWITCH_PROVIDER` — disabled, falls back to `CONTINUE`

---

## 10. Known Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| No downstream executor wired | **Critical** | Advisory decisions are observed but not acted upon |
| Process-local state (tracker, receipts) is lost on restart | **Medium** | Governance events may persist via JSONL/SQLite, but session history resets |
| Timeline depends on Supabase message metadata | **Medium** | If messages are pruned or metadata stripped, timeline is lost |
| No end-to-end integration tests for autonomy flow | **Medium** | Components tested in isolation but not as a pipeline |
| Evidence memory store not wired to controller | **Low** | `EvidenceMemoryStore` exists but controller writes only governance events |
| Governance events are fire-and-forget with silent failure | **Low** | Errors in `record_governance_event()` are logged at DEBUG level only |
| SQLite opt-in means most deployments use JSONL only | **Low** | JSONL is append-only, no query capability |
| Escalation reports are built but not delivered | **Low** | No notification channel exists for escalations |
| No rate limiting on decision evaluation | **Low** | Controller can be called arbitrarily without throttle |
| Fingerprint-based evidence not queryable from frontend | **Low** | No API endpoint exposes the evidence store |

---

## 11. What Blocks Autonomous Execution

1. **No decision executor** — There is no component that reads an
   `AutonomyDecision` and performs the corresponding action (e.g., actual retry,
   actual replan, actual self-repair)
2. **No adjudicator** — There is no adjudication layer that decides whether to
   follow the advisory decision
3. **All decisions are advisory-only** — `advisory=True` is hard-coded in
   `_make_decision()`
4. **SELF_REPAIR and SWITCH_PROVIDER are statically disabled** — Overridden to
   `CONTINUE` regardless of context
5. **Process-local session state** — Session tracker and receipt log are
   in-memory and lost on restart
6. **No CI integration** — The controller has no connection to CI systems
7. **No commit/push/PR tooling** — No safe command gate or controlled commit
   gate is wired into the autonomy pipeline
8. **No provider switching logic** — The `SWITCH_PROVIDER` decision exists in
   the enum but is disabled and has no implementation
9. **No self-repair logic** — The `SELF_REPAIR` decision exists in the enum but
   is disabled and has no implementation

---

## 12. Required Gates Before Enabling Auto-RETRY

- [ ] **Decision executor** — A component that can safely execute a retry of the
  last action using the same or equivalent context
- [ ] **Retry budget** — Maximum number of automatic retries per session or per
  error type, enforced by the executor
- [ ] **Idempotency check** — Verify that the operation being retried is
  idempotent or safe to repeat
- [ ] **Escalation on persistent failure** — After N retries (default should be
  3 or less), escalate instead of continuing to retry
- [ ] **Observability** — Each retry must produce a governance event and be
  visible in the Cockpit timeline
- [ ] **Manual override** — Ability for Misael to disable auto-retry at runtime
  without code change

---

## 13. Required Gates Before Enabling Auto-REPLAN

- [ ] **Replan executor** — A component that can generate a new plan based on
  the current context and failure evidence
- [ ] **Plan validation** — New plan must be validated against the same safety
  gates before execution
- [ ] **Plan history limit** — Maximum number of replans per task before forced
  escalation
- [ ] **No infinite loop protection** — Combined retry + replan cycle limit
- [ ] **Evidence carry-forward** — Previous failure evidence must be available to
  inform the new plan
- [ ] **Cockpit notification** — User must be able to see that a replan occurred
  and why

---

## 14. Required Gates Before Enabling SELF_REPAIR

- [ ] **Self-repair implementation** — The `SELF_REPAIR` decision type currently
  has no executor or logic behind it
- [ ] **Scoped repair surface** — Define exactly what self-repair can modify
  (e.g., config files, dependency versions, test assertions) and what is
  off-limits (secrets, production, governance policy)
- [ ] **Validation after repair** — Every repair must be followed by validation
  (e.g., tests must pass)
- [ ] **Rollback capability** — Repair changes must be revertible
- [ ] **Human approval for medium+ risk** — Self-repair with medium or higher
  risk level must require human approval
- [ ] **Audit trail** — Every repair must produce a governance event with before
  and after state

---

## 15. Required Gates Before Enabling Provider Switching

- [ ] **Provider switch implementation** — The `SWITCH_PROVIDER` decision type
  currently has no executor or logic behind it
- [ ] **Provider health tracking** — Reliable detection of provider unavailability
  vs. transient errors
- [ ] **Fallback ordering** — Defined order of provider fallback with failure
  tracking per provider
- [ ] **Credential safety** — Provider switching must not leak or mix credentials
- [ ] **Cost awareness** — Provider switch should consider cost implications
- [ ] **User notification** — User must be informed when provider is switched
  automatically

---

## 16. Required Gates Before Enabling CI Repair

- [ ] **CI integration** — The autonomy system must be able to read CI check
  results
- [ ] **Scoped CI repair** — Define what CI configuration changes are allowed
  (e.g., dependency version bumps, test fixes) and what is blocked (CI
  threshold changes, test skipping)
- [ ] **Post-repair validation** — Changes must be re-validated via CI
- [ ] **Rollback on failure** — If CI repair causes new failures, changes must
  be rolled back automatically
- [ ] **Human approval threshold** — CI repairs that modify test configuration,
  CI pipeline definitions, or security checks must require human approval
- [ ] **Circuit breaker** — Repeated CI repair failures must halt the repair
  loop and escalate

---

## 17. Required Gates Before Any Commit/Push/PR Automation

- [ ] **Controlled commit gate** — A component that validates what can be
  committed (no secrets, no governance policy changes, no production changes
  without approval)
- [ ] **Safe command execution gate** — A component that validates shell commands
  before execution (Phase 16 in the operating model)
- [ ] **Commit scope validation** — Only changes scoped to the current task may
  be committed
- [ ] **Push protection** — Push to main must always be blocked at the
  infrastructure level
- [ ] **PR draft-only** — Automated PRs must open as draft, never as
  ready-for-review
- [ ] **No auto-merge** — Automated PRs must never auto-merge
- [ ] **Runtime Truth requirement** — Autonomous actions must have Runtime Truth
  evidence and a report (as defined in the autonomy operating model)
- [ ] **User consent** — Explicit user consent must be required before any
  automated commit/push/PR
- [ ] **Kill switch** — A way for the user to disable all commit/push/PR
  automation at runtime

---

## 18. Manual Merge Policy

- **Only Misael may merge PRs to main.**
- No automated merge is enabled or will be enabled.
- PRs on this branch and any subsequent autonomy branches shall be opened as
  draft PRs and reviewed by Misael before manual merge.
- No auto-merge setting shall be enabled.

---

## 19. Recommended Rollout Phases

### Phase 0: Advisory-only (current) — In progress
- [x] Autonomy controller implemented
- [x] Smart Error Progress Tracker implemented
- [x] Per-session state tracking
- [x] Advisory-only decisions
- [x] Cockpit read-only visibility
- [x] Controller stats display
- [x] Decision timeline display
- [x] Governance event persistence (JSONL/SQLite)

### Phase 1: Hardened advisory
- [ ] Dedicated evidence endpoint (not embedded in message metadata)
- [ ] Evidence query API for frontend
- [ ] Escalation delivery channel (e.g., Cockpit notification)
- [ ] Non-volatile session state (SQLite-backed tracker)
- [ ] End-to-end integration tests
- [ ] Rate limiting on controller evaluation
- [ ] SQLite as default backend for governance events

### Phase 2: Supervised retry
- [ ] Retry executor with budget and idempotency check
- [ ] Manual override for auto-retry
- [ ] Enhanced observability for retries
- [ ] Human-in-the-loop for escalated decisions

### Phase 3: Supervised replan
- [ ] Replan executor with plan validation
- [ ] Cycle limit enforcement
- [ ] Evidence carry-forward

### Phase 4: Sandbox execution (Phase 16)
- [ ] Safe command execution gate
- [ ] Runtime Truth integration
- [ ] Sandbox isolation
- [ ] Controlled commit gate

### Phase 5: CI-aware automation
- [ ] CI integration
- [ ] Scoped CI repair
- [ ] PR draft automation

---

## 20. Go/No-Go Checklist

| Criterion | Status |
|-----------|--------|
| All decisions are advisory | ✅ Yes |
| Disabled decisions blocked | ✅ Yes |
| Safety escalation triggers in place | ✅ Yes |
| Cockpit read-only visibility | ✅ Yes |
| Governance events persisted | ✅ Partial (JSONL default, SQLite opt-in) |
| Decision executor wired | ❌ No |
| End-to-end autonomy tests pass | ❌ No (no integration tests) |
| Session state survives restart | ❌ No (process-local) |
| Escalation delivery works | ❌ No |
| User consent mechanism exists | ❌ No |
| Kill switch exists | ❌ No |
| Auto-RETRY enabled | ❌ No |
| Auto-REPLAN enabled | ❌ No |
| SELF_REPAIR enabled | ❌ No (disabled) |
| SWITCH_PROVIDER enabled | ❌ No (disabled) |
| Commit/push/PR automation enabled | ❌ No |
| CI repair enabled | ❌ No |
| Auto-merge enabled | ❌ No |
| Misael reviewed and approved | ⏳ Pending |

---

## Conclusion

**Omni autonomy is NOT approved for autonomous execution yet. Current mode is
advisory-only.**

The advisory stack is well-structured and provides a solid foundation for future
autonomous capabilities. The system can observe, fingerprint, classify, and
display runtime decisions. However, no executor interprets those decisions, no
adjudicator decides whether to follow them, and no autonomous action can be
taken. Two decision types (`SELF_REPAIR`, `SWITCH_PROVIDER`) are statically
disabled. Session state is process-local and lost on restart.

The rollout should proceed through the recommended phases starting with
hardened advisory (Phase 1), followed by supervised retry (Phase 2), supervised
replan (Phase 3), sandbox execution (Phase 4), and finally CI-aware automation
(Phase 5). Each phase requires explicit Misael approval before proceeding.

---

*This report is documentation only. No code behavior, configuration, secrets,
or production settings were changed.*
