"""Autonomy Operating Model policy decisions.

Phase 15 defines controlled autonomy levels and exception boundaries. It only
classifies requested future actions. It does not execute agents, run commands,
call providers, use MCP, write vault notes, create pull requests, merge pull
requests, or mutate Git.
"""

from __future__ import annotations

import re
from dataclasses import asdict
from typing import Any, Mapping

from .autonomy_types import AutonomyPolicyDecision, AutonomyPolicyRequest

AUTONOMY_EVIDENCE_VERSION = "1.0"
DEFAULT_AUTONOMY_LEVEL = "L1_ADVISORY"
MAIN_BRANCH = "main"
CREDENTIAL_REASON = "Credential-like content was detected and redacted."

AUTONOMY_LEVELS = (
    "L0_READ_ONLY",
    "L1_ADVISORY",
    "L2_BRANCH_EDIT_PROPOSAL",
    "L3_TEST_COMMIT_PUSH_BRANCH",
    "L4_PR_OPEN_AND_CI_REPAIR",
    "L5_CONDITIONAL_AUTO_MERGE",
    "L6_SUPERVISED_SANDBOX_EXECUTION",
    "L7_FULL_AUTONOMOUS_RESOLUTION",
)

LEVEL_RANK = {level: index for index, level in enumerate(AUTONOMY_LEVELS)}

ADVISORY_ACTIONS = frozenset(
    {
        "analyze_task",
        "create_plan",
        "assess_risk",
        "propose_changes",
        "propose_tests",
        "review_diff",
        "generate_report",
    }
)

BRANCH_ACTIONS = frozenset({"request_branch_creation", "request_branch_edit"})
TEST_COMMIT_PUSH_ACTIONS = frozenset(
    {"request_test_run", "request_commit", "request_push_branch"}
)
PR_ACTIONS = frozenset({"request_pr_open", "request_ci_repair"})
MERGE_ACTIONS = frozenset({"request_pr_merge"})
SANDBOX_ACTIONS = frozenset({"request_sandbox_execution"})
FULL_AUTONOMY_ACTIONS = frozenset(
    {"request_full_autonomous_resolution", "request_vault_draft"}
)

SUPPORTED_ACTIONS = (
    ADVISORY_ACTIONS
    | BRANCH_ACTIONS
    | TEST_COMMIT_PUSH_ACTIONS
    | PR_ACTIONS
    | MERGE_ACTIONS
    | SANDBOX_ACTIONS
    | FULL_AUTONOMY_ACTIONS
)

ALWAYS_BLOCKED_ACTIONS = frozenset(
    {
        "push_main",
        "bypass_ci",
        "lower_ci_threshold",
        "skip_tests",
        "disable_security_scan",
        "read_secrets",
        "expose_secrets",
        "delete_production_data",
        "deploy_production",
        "change_billing",
        "approve_security_policy",
        "edit_governance_policy_directly",
        "approve_vault_note",
        "promote_to_reviewed",
        "promote_to_approved",
        "force_merge",
        "merge_with_failing_checks",
    }
)

ACTION_MIN_LEVEL = {
    **{action: "L1_ADVISORY" for action in ADVISORY_ACTIONS},
    **{action: "L2_BRANCH_EDIT_PROPOSAL" for action in BRANCH_ACTIONS},
    **{action: "L3_TEST_COMMIT_PUSH_BRANCH" for action in TEST_COMMIT_PUSH_ACTIONS},
    **{action: "L4_PR_OPEN_AND_CI_REPAIR" for action in PR_ACTIONS},
    **{action: "L5_CONDITIONAL_AUTO_MERGE" for action in MERGE_ACTIONS},
    **{action: "L6_SUPERVISED_SANDBOX_EXECUTION" for action in SANDBOX_ACTIONS},
    **{action: "L7_FULL_AUTONOMOUS_RESOLUTION" for action in FULL_AUTONOMY_ACTIONS},
}

AUTONOMOUS_ACTIONS = (
    BRANCH_ACTIONS
    | TEST_COMMIT_PUSH_ACTIONS
    | PR_ACTIONS
    | MERGE_ACTIONS
    | SANDBOX_ACTIONS
    | FULL_AUTONOMY_ACTIONS
)

BRANCH_MUTATION_ACTIONS = (
    BRANCH_ACTIONS | TEST_COMMIT_PUSH_ACTIONS | PR_ACTIONS | MERGE_ACTIONS
)

_CREDENTIAL_PATTERNS = (
    re.compile(r"Authorization:\s*Bearer\s+\S+", re.IGNORECASE),
    re.compile(r"(?<![A-Za-z0-9])" + "s" + r"k-[A-Za-z0-9_-]+", re.IGNORECASE),
    re.compile("API" + r"_KEY", re.IGNORECASE),
    re.compile("SEC" + r"RET", re.IGNORECASE),
    re.compile("TO" + r"KEN", re.IGNORECASE),
    re.compile("PASS" + r"WORD", re.IGNORECASE),
    re.compile("SUPA" + r"BASE", re.IGNORECASE),
    re.compile("OPEN" + r"AI", re.IGNORECASE),
    re.compile("J" + r"WT", re.IGNORECASE),
    re.compile("PRIVATE" + r"_KEY", re.IGNORECASE),
    re.compile(r"\." + "env", re.IGNORECASE),
)


def evaluate_autonomy_policy(
    request_or_mapping: AutonomyPolicyRequest | Mapping[str, Any] | Any,
) -> AutonomyPolicyDecision:
    request = _coerce_request(request_or_mapping)
    level = _normalize_level(request.requested_level)
    action = _normalize_action(request.requested_action)
    target_branch, _ = _redact_optional(request.target_branch)
    requested_by, _ = _redact_text(request.requested_by)
    metadata_text = _metadata_text(request.metadata)
    secret_like_detected = request.secrets_detected or any(
        _contains_secret_like(value)
        for value in (
            request.requested_level,
            action,
            request.requested_by,
            requested_by,
            request.target_branch,
            target_branch,
            request.base_branch,
            request.task_type,
            request.related_phase,
            request.related_pr,
            metadata_text,
        )
    )
    base_branch = str(request.base_branch or MAIN_BRANCH).strip() or MAIN_BRANCH
    unknown_level = level not in LEVEL_RANK
    unknown_action = action not in SUPPORTED_ACTIONS and action not in ALWAYS_BLOCKED_ACTIONS
    always_blocked = action in ALWAYS_BLOCKED_ACTIONS
    exception_reasons = _exception_reasons(
        request=request,
        action=action,
        target_branch=target_branch,
        base_branch=base_branch,
        secret_like_detected=secret_like_detected,
    )
    level_allows_action = _level_allows_action(level=level, action=action)
    merge_gates_pass = _merge_gates_pass(
        request=request,
        action=action,
        target_branch=target_branch,
        base_branch=base_branch,
        has_exceptions=bool(exception_reasons),
    )

    blocked_reasons: list[str] = []
    if secret_like_detected:
        blocked_reasons.append(CREDENTIAL_REASON)
    if unknown_level:
        blocked_reasons.append("Requested autonomy level is unknown.")
    if unknown_action:
        blocked_reasons.append("Requested action is unknown.")
    if always_blocked:
        blocked_reasons.append("Requested action is always blocked by governance policy.")
    if not unknown_level and not unknown_action and not always_blocked and not level_allows_action:
        blocked_reasons.append("Requested autonomy level does not allow this action.")
    if exception_reasons:
        blocked_reasons.extend(exception_reasons)
    if action == "request_pr_merge" and not merge_gates_pass:
        blocked_reasons.append("Merge gates have not all passed.")
    if action == "request_full_autonomous_resolution" and request.checks_green is False:
        blocked_reasons.append("Full autonomous resolution requires green checks.")

    blocked = bool(blocked_reasons)
    allowed = not blocked
    risk_level = _risk_level(
        request=request,
        blocked=blocked,
        secret_like_detected=secret_like_detected,
        unknown_level=unknown_level,
        unknown_action=unknown_action,
        always_blocked=always_blocked,
    )
    human_exception_required = bool(exception_reasons or secret_like_detected)
    requires_human_intervention = blocked or human_exception_required
    category = _category(
        action=action,
        unknown_action=unknown_action,
        always_blocked=always_blocked,
    )
    reason = _reason(
        allowed=allowed,
        action=action,
        secret_like_detected=secret_like_detected,
        unknown_level=unknown_level,
        unknown_action=unknown_action,
        always_blocked=always_blocked,
    )
    escalation_reason = "; ".join(blocked_reasons) if blocked_reasons else None
    safe_reason, _ = _redact_text(reason)
    safe_escalation_reason, escalation_redacted = _redact_optional(escalation_reason)

    can_run_tests = allowed and action == "request_test_run"
    can_commit = allowed and action == "request_commit"
    can_push_branch = allowed and action == "request_push_branch"
    can_open_pr = allowed and action == "request_pr_open"
    can_repair_ci = allowed and action == "request_ci_repair"
    can_merge_pr = allowed and action == "request_pr_merge" and merge_gates_pass
    can_execute_sandbox = allowed and action == "request_sandbox_execution"
    can_write_vault_draft = allowed and action == "request_vault_draft"

    return AutonomyPolicyDecision(
        allowed=allowed,
        blocked=blocked,
        requires_human_intervention=requires_human_intervention,
        autonomy_level=level,
        requested_action=action,
        category=category,
        risk_level=risk_level,
        reason=safe_reason,
        escalation_reason=safe_escalation_reason,
        target_branch=target_branch,
        base_branch=base_branch,
        main_branch_protected=True,
        can_analyze=allowed and action in ADVISORY_ACTIONS,
        can_plan=allowed and action == "create_plan",
        can_edit_branch=allowed and action == "request_branch_edit",
        can_run_tests=can_run_tests,
        can_commit=can_commit,
        can_push_branch=can_push_branch,
        can_open_pr=can_open_pr,
        can_repair_ci=can_repair_ci,
        can_merge_pr=can_merge_pr,
        can_write_vault_draft=can_write_vault_draft,
        can_execute_sandbox=can_execute_sandbox,
        can_call_provider=False,
        can_use_mcp=False,
        can_push_main=False,
        can_bypass_ci=False,
        can_lower_security=False,
        runtime_truth_required=allowed and action in AUTONOMOUS_ACTIONS,
        report_required=allowed and action in AUTONOMOUS_ACTIONS,
        human_exception_required=human_exception_required,
        evidence_version=AUTONOMY_EVIDENCE_VERSION,
    )


def _coerce_request(
    value: AutonomyPolicyRequest | Mapping[str, Any] | Any,
) -> AutonomyPolicyRequest:
    if isinstance(value, AutonomyPolicyRequest):
        return value
    if hasattr(value, "to_dict"):
        payload = value.to_dict()
    elif hasattr(value, "__dataclass_fields__"):
        payload = asdict(value)
    elif isinstance(value, Mapping):
        payload = dict(value)
    else:
        raise TypeError(
            "Autonomy policy input must be a request, mapping, or object with to_dict()."
        )

    return AutonomyPolicyRequest(
        requested_level=str(payload.get("requested_level") or DEFAULT_AUTONOMY_LEVEL),
        requested_action=str(payload.get("requested_action") or "analyze_task"),
        requested_by=str(payload.get("requested_by") or "unknown"),
        task_type=payload.get("task_type"),
        target_branch=payload.get("target_branch"),
        base_branch=str(payload.get("base_branch") or MAIN_BRANCH),
        risk_level=payload.get("risk_level"),
        files_changed=list(payload.get("files_changed") or []),
        checks_green=bool(payload.get("checks_green", False)),
        secrets_detected=bool(payload.get("secrets_detected", False)),
        ci_threshold_changed=bool(payload.get("ci_threshold_changed", False)),
        tests_skipped=bool(payload.get("tests_skipped", False)),
        security_policy_changed=bool(payload.get("security_policy_changed", False)),
        governance_policy_changed=bool(payload.get("governance_policy_changed", False)),
        production_targeted=bool(payload.get("production_targeted", False)),
        billing_or_cost_impact=bool(payload.get("billing_or_cost_impact", False)),
        destructive_action_requested=bool(payload.get("destructive_action_requested", False)),
        requires_human_decision=bool(payload.get("requires_human_decision", False)),
        related_phase=payload.get("related_phase"),
        related_pr=payload.get("related_pr"),
        metadata=dict(payload.get("metadata") or {}),
    )


def _normalize_level(level: object) -> str:
    return str(level or DEFAULT_AUTONOMY_LEVEL).strip() or DEFAULT_AUTONOMY_LEVEL


def _normalize_action(action: object) -> str:
    return str(action or "").strip()


def _level_allows_action(*, level: str, action: str) -> bool:
    if level == "L0_READ_ONLY":
        return False
    if level not in LEVEL_RANK or action not in ACTION_MIN_LEVEL:
        return False
    return LEVEL_RANK[level] >= LEVEL_RANK[ACTION_MIN_LEVEL[action]]


def _exception_reasons(
    *,
    request: AutonomyPolicyRequest,
    action: str,
    target_branch: str | None,
    base_branch: str,
    secret_like_detected: bool,
) -> list[str]:
    reasons: list[str] = []
    if secret_like_detected:
        reasons.append(CREDENTIAL_REASON)
    if request.ci_threshold_changed:
        reasons.append("CI threshold changes require human intervention.")
    if request.tests_skipped:
        reasons.append("Skipped tests require human intervention.")
    if request.security_policy_changed:
        reasons.append("Security policy changes require human intervention.")
    if request.governance_policy_changed:
        reasons.append("Governance policy changes require human intervention.")
    if request.production_targeted:
        reasons.append("Production-targeted changes require human intervention.")
    if request.billing_or_cost_impact:
        reasons.append("Billing or cost impact requires human intervention.")
    if request.destructive_action_requested:
        reasons.append("Destructive actions require human intervention.")
    if request.requires_human_decision:
        reasons.append("The request explicitly requires human decision.")
    if action in BRANCH_MUTATION_ACTIONS and _is_main_branch(target_branch):
        reasons.append("Main branch cannot be targeted for branch mutation.")
    if action == "request_pr_merge" and base_branch != MAIN_BRANCH:
        reasons.append("Conditional merge policy only targets main as the PR base.")
    if action == "request_pr_merge" and not request.checks_green:
        reasons.append("PR merge requires green checks.")
    return reasons


def _merge_gates_pass(
    *,
    request: AutonomyPolicyRequest,
    action: str,
    target_branch: str | None,
    base_branch: str,
    has_exceptions: bool,
) -> bool:
    if action != "request_pr_merge":
        return False
    if _is_main_branch(target_branch) or not target_branch:
        return False
    return (
        base_branch == MAIN_BRANCH
        and request.checks_green
        and not has_exceptions
        and not request.secrets_detected
        and not request.ci_threshold_changed
        and not request.tests_skipped
        and not request.security_policy_changed
        and not request.governance_policy_changed
        and not request.production_targeted
        and not request.billing_or_cost_impact
        and not request.destructive_action_requested
        and not request.requires_human_decision
    )


def _category(*, action: str, unknown_action: bool, always_blocked: bool) -> str:
    if unknown_action:
        return "unknown"
    if always_blocked:
        return "blocked"
    if action in ADVISORY_ACTIONS:
        return "advisory"
    if action in BRANCH_ACTIONS:
        return "branch"
    if action in TEST_COMMIT_PUSH_ACTIONS:
        return "test_commit_push"
    if action in PR_ACTIONS:
        return "pull_request"
    if action in MERGE_ACTIONS:
        return "conditional_merge"
    if action in SANDBOX_ACTIONS:
        return "sandbox"
    if action in FULL_AUTONOMY_ACTIONS:
        return "full_autonomy"
    return "unknown"


def _reason(
    *,
    allowed: bool,
    action: str,
    secret_like_detected: bool,
    unknown_level: bool,
    unknown_action: bool,
    always_blocked: bool,
) -> str:
    if secret_like_detected:
        return CREDENTIAL_REASON
    if unknown_level:
        return "Requested autonomy level is unknown."
    if unknown_action:
        return "Requested action is unknown."
    if always_blocked:
        return "Requested action is blocked by governance policy."
    if allowed:
        return "Autonomy policy allows this future capability decision."
    if action == "request_pr_merge":
        return "Conditional merge requires all autonomy gates to pass."
    return "Autonomy policy blocks this request."


def _risk_level(
    *,
    request: AutonomyPolicyRequest,
    blocked: bool,
    secret_like_detected: bool,
    unknown_level: bool,
    unknown_action: bool,
    always_blocked: bool,
) -> str:
    if secret_like_detected or always_blocked:
        return "critical"
    if unknown_level or unknown_action:
        return "high"
    if any(
        (
            request.ci_threshold_changed,
            request.tests_skipped,
            request.security_policy_changed,
            request.governance_policy_changed,
            request.production_targeted,
            request.billing_or_cost_impact,
            request.destructive_action_requested,
            request.requires_human_decision,
        )
    ):
        return "high"
    if blocked:
        return str(request.risk_level or "medium")
    return str(request.risk_level or "low")


def _is_main_branch(branch: str | None) -> bool:
    return str(branch or "").strip() == MAIN_BRANCH


def _redact_optional(value: object) -> tuple[str | None, bool]:
    if value is None:
        return None, False
    return _redact_text(value)


def _redact_text(value: object) -> tuple[str, bool]:
    text = "" if value is None else str(value)
    redacted = text
    for pattern in _CREDENTIAL_PATTERNS:
        redacted = pattern.sub("[REDACTED]", redacted)
    return redacted, redacted != text


def _contains_secret_like(value: object) -> bool:
    text = "" if value is None else str(value)
    return any(pattern.search(text) for pattern in _CREDENTIAL_PATTERNS)


def _metadata_text(metadata: Mapping[str, Any]) -> str:
    parts: list[str] = []
    for key, value in metadata.items():
        parts.append(str(key))
        if isinstance(value, Mapping):
            parts.append(_metadata_text(value))
        elif isinstance(value, (list, tuple, set)):
            parts.extend(str(item) for item in value)
        else:
            parts.append(str(value))
    return " ".join(parts)
