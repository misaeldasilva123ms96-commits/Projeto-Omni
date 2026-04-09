from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .evidence_gate import EvidenceGateResult
from .mode_engine import RuntimeMode, get_allowed_actions


@dataclass(frozen=True)
class PolicyResult:
    allowed: bool
    policy_name: str
    reason: str
    severity: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PolicyBundleResult:
    allowed: bool
    results: list[PolicyResult]
    blocking_results: list[PolicyResult]


class PolicyEngine:
    def evaluate_execution_policy(self, mode: RuntimeMode, requested_action: str) -> PolicyResult:
        allowed = requested_action in get_allowed_actions(mode)
        return PolicyResult(
            allowed=allowed,
            policy_name="ExecutionPolicy",
            reason="requested action allowed in current mode" if allowed else "requested action is not allowed in current mode",
            severity="info" if allowed else "high",
            details={"mode": mode.value, "requested_action": requested_action},
        )

    def evaluate_mutation_policy(
        self,
        task_type: str,
        risk_level: str,
        evidence_result: EvidenceGateResult,
    ) -> PolicyResult:
        if task_type == "code_mutation" and risk_level == "high" and not evidence_result.enough_evidence:
            return PolicyResult(
                allowed=False,
                policy_name="MutationPolicy",
                reason="mutation requires file or runtime evidence before execution",
                severity="high",
                details={
                    "task_type": task_type,
                    "risk_level": risk_level,
                    "missing_evidence_types": evidence_result.missing_evidence_types,
                },
            )
        return PolicyResult(
            allowed=True,
            policy_name="MutationPolicy",
            reason="mutation policy allows current request",
            severity="info",
            details={"task_type": task_type, "risk_level": risk_level},
        )

    def evaluate_scope_policy(self, task_type: str, metadata: dict[str, Any] | None) -> PolicyResult:
        metadata = metadata or {}
        if task_type not in {"code_mutation", "recovery"}:
            return PolicyResult(True, "ScopePolicy", "scope policy allows non-expansive request", "info", {})

        has_scope_signal = any(
            bool(metadata.get(key))
            for key in ("target_files", "repository_analysis", "repo_impact_analysis", "workspace_state")
        )
        return PolicyResult(
            allowed=has_scope_signal,
            policy_name="ScopePolicy",
            reason="scope metadata present" if has_scope_signal else "mutation or recovery requires target scope metadata",
            severity="info" if has_scope_signal else "high",
            details={"task_type": task_type},
        )

    def evaluate_verification_policy(self, task_type: str, metadata: dict[str, Any] | None) -> PolicyResult:
        metadata = metadata or {}
        if task_type == "verification":
            return PolicyResult(
                allowed=True,
                policy_name="VerificationPolicy",
                reason="verification path is non-mutating and allowed",
                severity="info",
                details={"task_type": task_type},
            )
        if task_type == "code_mutation" and metadata.get("verification_plan") is None:
            return PolicyResult(
                allowed=True,
                policy_name="VerificationPolicy",
                reason="verification plan not yet required at initial control-layer gate",
                severity="info",
                details={"task_type": task_type},
            )
        return PolicyResult(True, "VerificationPolicy", "verification policy allows current request", "info", {})

    def evaluate_git_policy(self, metadata: dict[str, Any] | None) -> PolicyResult:
        metadata = metadata or {}
        violation = metadata.get("git_policy_violation")
        return PolicyResult(
            allowed=not bool(violation),
            policy_name="GitPolicy",
            reason="git policy allows current request" if not violation else "git policy violation detected",
            severity="info" if not violation else "medium",
            details={"violation": violation} if violation else {},
        )

    def evaluate_tool_policy(self, metadata: dict[str, Any] | None) -> PolicyResult:
        metadata = metadata or {}
        violation = metadata.get("tool_policy_violation")
        return PolicyResult(
            allowed=not bool(violation),
            policy_name="ToolPolicy",
            reason="tool policy allows current request" if not violation else "tool policy violation detected",
            severity="info" if not violation else "medium",
            details={"violation": violation} if violation else {},
        )

    def evaluate_policies(
        self,
        *,
        mode: RuntimeMode,
        requested_action: str,
        task_type: str,
        risk_level: str,
        metadata: dict[str, Any] | None,
        evidence_result: EvidenceGateResult,
    ) -> PolicyBundleResult:
        results = [
            self.evaluate_execution_policy(mode, requested_action),
            self.evaluate_mutation_policy(task_type, risk_level, evidence_result),
            self.evaluate_scope_policy(task_type, metadata),
            self.evaluate_verification_policy(task_type, metadata),
            self.evaluate_git_policy(metadata),
            self.evaluate_tool_policy(metadata),
        ]
        blocking_results = [result for result in results if not result.allowed]
        return PolicyBundleResult(
            allowed=not blocking_results,
            results=results,
            blocking_results=blocking_results,
        )
