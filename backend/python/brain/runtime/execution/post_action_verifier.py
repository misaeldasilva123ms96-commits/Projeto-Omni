from __future__ import annotations

from typing import Any

from .models import ExecutionIntent, RiskClassification, RiskLevel, VerificationResult


class PostActionVerifier:
    def verify(
        self,
        *,
        intent: ExecutionIntent,
        result: dict[str, Any],
        risk: RiskClassification,
    ) -> VerificationResult:
        if not isinstance(result, dict):
            return VerificationResult(
                passed=False,
                reason_code="invalid_result_shape",
                summary="Execution result is not a dictionary.",
            )

        if not result.get("ok"):
            error_payload = result.get("error_payload", {}) if isinstance(result.get("error_payload"), dict) else {}
            message = str(error_payload.get("message", "Execution failed before verification."))
            return VerificationResult(
                passed=False,
                reason_code=str(error_payload.get("kind", "execution_failed")),
                summary=message,
            )

        payload = result.get("result_payload", {}) if isinstance(result.get("result_payload"), dict) else {}
        observed_effects: list[str] = []
        missing_fields: list[str] = []

        if not payload:
            return VerificationResult(
                passed=False,
                reason_code="empty_result_payload",
                summary="Execution succeeded but did not produce an observable payload.",
            )

        expected_fields = self._expected_fields(intent)
        for field_name in expected_fields:
            if self._lookup_field(payload, field_name) is None and self._lookup_field(result, field_name) is None:
                missing_fields.append(field_name)

        if missing_fields:
            return VerificationResult(
                passed=False,
                reason_code="missing_expected_fields",
                summary=f"Execution payload is missing expected fields: {', '.join(missing_fields)}.",
                missing_fields=missing_fields,
            )

        observed_effects.extend(self._collect_observed_effects(payload))

        if risk.level in {RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL} and not observed_effects:
            return VerificationResult(
                passed=False,
                reason_code="mutation_without_observable_effect",
                summary="Mutation-prone action did not expose any observable effect.",
            )

        return VerificationResult(
            passed=True,
            reason_code="verification_passed",
            summary="Execution output passed deterministic verification.",
            observed_effects=observed_effects,
        )

    def _expected_fields(self, intent: ExecutionIntent) -> list[str]:
        metadata = intent.metadata if isinstance(intent.metadata, dict) else {}
        explicit = metadata.get("expected_fields", [])
        if isinstance(explicit, list):
            return [str(item) for item in explicit if str(item).strip()]
        if intent.capability in {"filesystem_read", "read_file"}:
            return ["file.content"]
        if intent.capability in {"filesystem_write", "filesystem_patch_set"}:
            return ["workspace_root"]
        return []

    def _lookup_field(self, payload: dict[str, Any], path: str) -> Any | None:
        current: Any = payload
        for part in path.split("."):
            if not isinstance(current, dict) or part not in current:
                return None
            current = current[part]
        return current

    def _collect_observed_effects(self, payload: dict[str, Any]) -> list[str]:
        effects: list[str] = []
        for key in ("workspace_root", "patch", "patch_set", "matches", "tree", "runs", "file"):
            value = payload.get(key)
            if value:
                effects.append(key)
        if payload.get("stdout"):
            effects.append("stdout")
        if payload.get("summary"):
            effects.append("summary")
        return effects
