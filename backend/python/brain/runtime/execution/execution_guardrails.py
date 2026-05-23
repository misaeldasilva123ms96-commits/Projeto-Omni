from __future__ import annotations

from .models import ExecutionPolicy, GuardrailDecision, PreflightResult, RiskClassification, RiskLevel, RISK_ORDER


class ExecutionGuardrails:
    def decide(
        self,
        *,
        risk: RiskClassification,
        preflight: PreflightResult,
        policy: ExecutionPolicy,
    ) -> GuardrailDecision:
        if not preflight.allowed:
            return GuardrailDecision(
                allowed=False,
                reason_code="preflight_failed",
                summary=preflight.summary,
            )

        if risk.level == RiskLevel.CRITICAL and not policy.allow_critical:
            return GuardrailDecision(
                allowed=False,
                reason_code="critical_risk_blocked",
                summary="Critical actions require explicit policy allowance.",
            )

        if risk.level == RiskLevel.HIGH and not policy.allow_high_risk:
            return GuardrailDecision(
                allowed=False,
                reason_code="high_risk_blocked",
                summary="High-risk actions are blocked by the current execution policy.",
            )

        if RISK_ORDER[risk.level] > RISK_ORDER[policy.max_risk]:
            return GuardrailDecision(
                allowed=False,
                reason_code="risk_above_policy_ceiling",
                summary=f"Risk level {risk.level.value} exceeds the current execution policy ceiling.",
            )

        return GuardrailDecision(
            allowed=True,
            reason_code="allowed",
            summary="Action passed trusted execution guardrails.",
            fallback_mode="execute",
        )
