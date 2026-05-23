from __future__ import annotations

from typing import Any, Callable

from .execution_guardrails import ExecutionGuardrails
from .execution_receipt import build_execution_receipt
from .models import (
    ExecutionIntent,
    ExecutionPolicy,
    PreflightCheck,
    PreflightResult,
    RiskClassification,
    RiskLevel,
    TrustedExecutionResult,
    VerificationResult,
)
from .post_action_verifier import PostActionVerifier
from .preflight_checks import PreflightChecker
from .risk_classifier import DeterministicRiskClassifier


class TrustedExecutor:
    def __init__(
        self,
        *,
        available_capabilities: set[str] | None = None,
        available_tools: set[str] | None = None,
        policy: ExecutionPolicy | None = None,
    ) -> None:
        self.available_capabilities = available_capabilities or set()
        self.available_tools = available_tools or set()
        self.policy = policy or ExecutionPolicy()
        self.risk_classifier = DeterministicRiskClassifier()
        self.preflight_checker = PreflightChecker()
        self.guardrails = ExecutionGuardrails()
        self.verifier = PostActionVerifier()

    def execute(
        self,
        *,
        intent: ExecutionIntent,
        execute_callback: Callable[[], dict[str, Any]],
        current_mode: str = "live",
        retry_count: int = 0,
        subsystem_available: bool = True,
    ) -> TrustedExecutionResult:
        risk = self.risk_classifier.classify(intent)
        preflight = self.preflight_checker.run(
            intent=intent,
            risk=risk,
            policy=self.policy,
            available_capabilities=self.available_capabilities,
            available_tools=self.available_tools,
            current_mode=current_mode,
            subsystem_available=subsystem_available,
        )
        guardrail = self.guardrails.decide(
            risk=risk,
            preflight=preflight,
            policy=self.policy,
        )

        if not guardrail.allowed:
            verification = VerificationResult(
                passed=False,
                reason_code="execution_skipped",
                summary="Execution did not run because trusted execution guardrails denied it.",
            )
            denied_result = {
                "ok": False,
                "error_payload": {
                    "kind": guardrail.reason_code,
                    "message": guardrail.summary,
                },
            }
            receipt = build_execution_receipt(
                intent=intent,
                risk=risk,
                preflight_status="failed",
                execution_status="denied",
                verification_status="skipped",
                retry_count=retry_count,
                rollback_status="not_applicable",
                summary=guardrail.summary,
                error_details=denied_result["error_payload"],
                metadata={
                    "guardrail": guardrail.as_dict(),
                    "preflight": preflight.as_dict(),
                },
            )
            denied_result["execution_receipt"] = receipt.as_dict()
            denied_result["trusted_execution"] = {
                "risk": risk.as_dict(),
                "preflight": preflight.as_dict(),
                "guardrail": guardrail.as_dict(),
                "verification": verification.as_dict(),
            }
            return TrustedExecutionResult(
                result=denied_result,
                receipt=receipt,
                risk=risk,
                preflight=preflight,
                verification=verification,
                guardrail=guardrail,
            )

        try:
            callback_result = execute_callback()
        except Exception as exc:
            callback_result = {
                "ok": False,
                "error_payload": {
                    "kind": "execution_exception",
                    "message": str(exc),
                },
            }

        verification = self.verifier.verify(
            intent=intent,
            result=callback_result,
            risk=risk,
        )
        if not verification.passed and callback_result.get("ok"):
            callback_result = dict(callback_result)
            callback_result["ok"] = False
            callback_result["error_payload"] = {
                "kind": "verification_failed",
                "message": verification.summary,
                "reason_code": verification.reason_code,
            }

        receipt = build_execution_receipt(
            intent=intent,
            risk=risk,
            preflight_status="passed",
            execution_status="succeeded" if callback_result.get("ok") else "failed",
            verification_status="passed" if verification.passed else "failed",
            retry_count=retry_count,
            rollback_status="not_applicable",
            summary=verification.summary if verification.summary else "Trusted execution completed.",
            error_details=dict(callback_result.get("error_payload", {}) or {}),
            metadata={
                "guardrail": guardrail.as_dict(),
                "preflight": preflight.as_dict(),
                "verification": verification.as_dict(),
            },
        )
        callback_result = dict(callback_result)
        callback_result["execution_receipt"] = receipt.as_dict()
        callback_result["trusted_execution"] = {
            "risk": risk.as_dict(),
            "preflight": preflight.as_dict(),
            "guardrail": guardrail.as_dict(),
            "verification": verification.as_dict(),
        }
        return TrustedExecutionResult(
            result=callback_result,
            receipt=receipt,
            risk=risk,
            preflight=preflight,
            verification=verification,
            guardrail=guardrail,
        )

    @staticmethod
    def permissive_preflight() -> PreflightResult:
        return PreflightResult(
            allowed=True,
            checks=[PreflightCheck(name="noop", passed=True, details="No preflight checks were required.")],
            reason_code="preflight_passed",
            summary="No preflight checks were required.",
        )
