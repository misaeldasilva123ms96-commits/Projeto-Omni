from __future__ import annotations

from dataclasses import asdict, dataclass

from .mode_engine import RuntimeMode


@dataclass(frozen=True)
class RoutingDecision:
    task_type: str
    preferred_mode: RuntimeMode
    preferred_capability_path: str
    specialist_delegation_recommended: bool
    risk_level: str
    requires_evidence: bool
    reason: str

    def as_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["preferred_mode"] = self.preferred_mode.value
        return data


class CapabilityRouter:
    _ROUTES: tuple[tuple[str, tuple[str, ...], RoutingDecision], ...] = (
        (
            "reporting",
            ("resuma a execucao", "gere um relatorio", "status", "pr summary", "relatorio", "readiness", "resumo do run"),
            RoutingDecision(
                task_type="reporting",
                preferred_mode=RuntimeMode.REPORT,
                preferred_capability_path="reporting_workflow",
                specialist_delegation_recommended=True,
                risk_level="low",
                requires_evidence=False,
                reason="reporting-oriented request detected",
            ),
        ),
        (
            "code_mutation",
            ("edite", "mude", "change", "patch", "fix code", "refactor", "implemente", "write file", "aplique", "corrija este arquivo"),
            RoutingDecision(
                task_type="code_mutation",
                preferred_mode=RuntimeMode.PLAN,
                preferred_capability_path="engineering_workflow",
                specialist_delegation_recommended=True,
                risk_level="high",
                requires_evidence=True,
                reason="mutation-oriented request detected",
            ),
        ),
        (
            "recovery",
            ("recover", "retry", "rollback", "debug failed", "corrija", "conserte", "fix failing test", "recupere"),
            RoutingDecision(
                task_type="recovery",
                preferred_mode=RuntimeMode.RECOVER,
                preferred_capability_path="recovery_workflow",
                specialist_delegation_recommended=True,
                risk_level="medium",
                requires_evidence=True,
                reason="recovery-oriented request detected",
            ),
        ),
        (
            "verification",
            ("rode os testes", "verifique", "validate", "lint", "typecheck", "regression", "teste", "valide"),
            RoutingDecision(
                task_type="verification",
                preferred_mode=RuntimeMode.VERIFY,
                preferred_capability_path="verification_workflow",
                specialist_delegation_recommended=True,
                risk_level="medium",
                requires_evidence=False,
                reason="verification-oriented request detected",
            ),
        ),
        (
            "repository_analysis",
            ("analise o repositorio", "inspect architecture", "dependency", "impact", "find files", "dependencias", "arquitetura", "repositorio"),
            RoutingDecision(
                task_type="repository_analysis",
                preferred_mode=RuntimeMode.EXPLORE,
                preferred_capability_path="repository_intelligence",
                specialist_delegation_recommended=True,
                risk_level="low",
                requires_evidence=False,
                reason="repository-analysis request detected",
            ),
        ),
    )

    def classify_task(self, message: str, metadata: dict[str, object] | None = None) -> RoutingDecision:
        lowered = message.strip().lower()
        metadata = metadata or {}
        explicit_task_type = metadata.get("task_type")
        if isinstance(explicit_task_type, str):
            explicit_task_type = explicit_task_type.strip().lower()
            for _, _, decision in self._ROUTES:
                if decision.task_type == explicit_task_type:
                    return decision
            if explicit_task_type == "simple_query":
                return self._default_decision()

        for _, triggers, decision in self._ROUTES:
            if any(trigger in lowered for trigger in triggers):
                return decision
        return self._default_decision()

    @staticmethod
    def _default_decision() -> RoutingDecision:
        return RoutingDecision(
            task_type="simple_query",
            preferred_mode=RuntimeMode.EXPLORE,
            preferred_capability_path="conversation_runtime",
            specialist_delegation_recommended=False,
            risk_level="low",
            requires_evidence=False,
            reason="default conversational read-only routing",
        )


def classify_task(message: str, metadata: dict[str, object] | None = None) -> RoutingDecision:
    return CapabilityRouter().classify_task(message, metadata)
