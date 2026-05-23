from __future__ import annotations

from typing import Any

from .models import ExecutionIntent, ExecutionPolicy, PreflightCheck, PreflightResult, RiskClassification, RiskLevel


class PreflightChecker:
    def run(
        self,
        *,
        intent: ExecutionIntent,
        risk: RiskClassification,
        policy: ExecutionPolicy,
        available_capabilities: set[str],
        available_tools: set[str],
        current_mode: str,
        subsystem_available: bool = True,
    ) -> PreflightResult:
        checks: list[PreflightCheck] = []
        capability = str(intent.capability or "").strip()

        checks.append(
            PreflightCheck(
                name="capability_present",
                passed=bool(capability),
                details="Capability/tool identifier is present." if capability else "Missing capability/tool identifier.",
            )
        )

        is_registered = capability in available_capabilities or capability in available_tools
        checks.append(
            PreflightCheck(
                name="capability_registered",
                passed=is_registered,
                details="Capability/tool is registered." if is_registered else f"Capability/tool {capability or '<missing>'} is not registered.",
            )
        )

        checks.append(
            PreflightCheck(
                name="subsystem_available",
                passed=subsystem_available,
                details=f"Target subsystem {intent.target_subsystem} is available." if subsystem_available else f"Target subsystem {intent.target_subsystem} is unavailable.",
            )
        )

        payload = intent.input_payload_summary if isinstance(intent.input_payload_summary, dict) else {}
        tool_arguments = payload.get("tool_arguments")
        arguments_present = not isinstance(tool_arguments, dict) or bool(tool_arguments)
        checks.append(
            PreflightCheck(
                name="arguments_present",
                passed=arguments_present,
                details="Required tool arguments are present." if arguments_present else "Tool arguments are missing or empty.",
            )
        )

        mode_allowed = current_mode not in {"blocked", "disabled"}
        checks.append(
            PreflightCheck(
                name="mode_allowed",
                passed=mode_allowed,
                details=f"Current mode {current_mode} allows execution." if mode_allowed else f"Current mode {current_mode} forbids execution.",
            )
        )

        policy_risk_allowed = self._risk_allowed(risk.level, policy)
        checks.append(
            PreflightCheck(
                name="risk_allowed_by_policy",
                passed=policy_risk_allowed,
                details="Risk is allowed by execution policy." if policy_risk_allowed else f"Risk level {risk.level.value} exceeds execution policy.",
                severity="warning",
            )
        )

        if risk.level in {RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL} and policy.require_session_for_mutation:
            has_session = bool((intent.session_id or "").strip())
            checks.append(
                PreflightCheck(
                    name="session_context_present",
                    passed=has_session,
                    details="Session context is available for mutation-prone action." if has_session else "Session context is required for mutation-prone actions.",
                )
            )

        checks.append(
            PreflightCheck(
                name="dry_run_awareness",
                passed=True,
                severity="info",
                details="Dry-run can be layered later if the selected tool supports it.",
            )
        )

        failed_checks = [item for item in checks if not item.passed and item.severity == "error"]
        if failed_checks:
            return PreflightResult(
                allowed=False,
                checks=checks,
                reason_code="preflight_failed",
                summary="; ".join(item.details for item in failed_checks),
            )

        return PreflightResult(
            allowed=True,
            checks=checks,
            reason_code="preflight_passed",
            summary="All required preflight checks passed.",
        )

    def _risk_allowed(self, risk_level: RiskLevel, policy: ExecutionPolicy) -> bool:
        if risk_level == RiskLevel.CRITICAL:
            return policy.allow_critical
        if risk_level == RiskLevel.HIGH:
            return policy.allow_high_risk and policy.max_risk in {RiskLevel.HIGH, RiskLevel.CRITICAL}
        if risk_level == RiskLevel.MEDIUM:
            return policy.max_risk in {RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL}
        return True
