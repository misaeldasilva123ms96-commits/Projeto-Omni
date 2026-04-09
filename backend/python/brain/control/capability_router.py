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
    verification_intensity: str
    execution_strategy: str
    recommended_specialists: list[str]
    reasoning: str

    def as_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["preferred_mode"] = self.preferred_mode.value
        return data


class CapabilityRouter:
    _DIRECT_PATTERNS = (
        "explique",
        "explain",
        "summarize",
        "sumarize",
        "what is",
        "o que e",
        "como funciona",
        "how does this work",
    )
    _REPOSITORY_PATTERNS = (
        "analise o repositorio",
        "analyze repo",
        "inspect architecture",
        "dependency impact",
        "find relevant files",
        "find files",
        "dependencias",
        "arquitetura",
        "repositorio",
        "system flow",
        "fluxo do sistema",
    )
    _MUTATION_PATTERNS = (
        "edite",
        "mude",
        "change",
        "patch",
        "fix code",
        "refactor",
        "implemente",
        "write file",
        "aplique",
        "corrija este arquivo",
        "implementar feature",
        "fix bug",
        "refatore",
    )
    _VERIFICATION_PATTERNS = (
        "rode os testes",
        "run tests",
        "verifique",
        "validate",
        "lint",
        "typecheck",
        "regression",
        "teste",
        "valide",
        "check regression",
        "confirm behavior",
    )
    _RECOVERY_PATTERNS = (
        "recover",
        "retry",
        "rollback",
        "debug why this failed",
        "debug failed",
        "fix failing test",
        "recupere",
        "retry after failure",
        "broken execution path",
        "conserte a execucao",
    )
    _REPORTING_PATTERNS = (
        "resuma a execucao",
        "gere um relatorio",
        "status",
        "pr summary",
        "relatorio",
        "readiness",
        "resumo do run",
        "milestone summary",
        "produce pr summary",
        "give status",
    )
    _LARGE_TASK_PATTERNS = (
        "broad change",
        "across the repository",
        "multiple files",
        "architecture change",
        "system-wide refactor",
        "end-to-end modification",
        "mudanca ampla",
        "repositorio inteiro",
        "varios arquivos",
        "muitos arquivos",
        "mudanca de arquitetura",
        "refatoracao ampla",
        "sistema inteiro",
    )

    def classify_task(self, message: str, metadata: dict[str, object] | None = None) -> RoutingDecision:
        lowered = message.strip().lower()
        metadata = metadata or {}
        explicit_task_type = metadata.get("task_type")
        if isinstance(explicit_task_type, str):
            explicit_task_type = explicit_task_type.strip().lower()
            explicit_decision = self._decision_for_task_type(explicit_task_type, lowered, metadata)
            if explicit_decision is not None:
                return explicit_decision

        if self._is_large_task(lowered, metadata):
            return self._code_mutation_decision(lowered, metadata)
        if self._matches_any(lowered, self._REPORTING_PATTERNS):
            return self._reporting_decision()
        if self._matches_any(lowered, self._VERIFICATION_PATTERNS):
            return self._verification_decision()
        if self._matches_any(lowered, self._MUTATION_PATTERNS):
            return self._code_mutation_decision(lowered, metadata)
        if self._matches_any(lowered, self._RECOVERY_PATTERNS):
            return self._recovery_decision()
        if self._matches_any(lowered, self._REPOSITORY_PATTERNS):
            return self._repository_analysis_decision()
        if self._matches_any(lowered, self._DIRECT_PATTERNS):
            return self._default_decision()
        return self._default_decision()

    def _decision_for_task_type(
        self,
        explicit_task_type: str,
        lowered: str,
        metadata: dict[str, object],
    ) -> RoutingDecision | None:
        if explicit_task_type == "simple_query":
            return self._default_decision()
        if explicit_task_type == "repository_analysis":
            return self._repository_analysis_decision()
        if explicit_task_type == "code_mutation":
            return self._code_mutation_decision(lowered, metadata)
        if explicit_task_type == "verification":
            return self._verification_decision()
        if explicit_task_type == "recovery":
            return self._recovery_decision()
        if explicit_task_type == "reporting":
            return self._reporting_decision()
        return None

    @staticmethod
    def _matches_any(message: str, patterns: tuple[str, ...]) -> bool:
        return any(pattern in message for pattern in patterns)

    def _is_large_task(self, lowered: str, metadata: dict[str, object]) -> bool:
        if self._matches_any(lowered, self._LARGE_TASK_PATTERNS):
            return True
        target_files = metadata.get("target_files")
        if isinstance(target_files, list) and len([item for item in target_files if isinstance(item, str) and item]) > 1:
            return True
        repo_impact_analysis = metadata.get("repo_impact_analysis")
        if isinstance(repo_impact_analysis, dict) and repo_impact_analysis:
            return True
        return False

    @staticmethod
    def _default_decision() -> RoutingDecision:
        return RoutingDecision(
            task_type="simple_query",
            preferred_mode=RuntimeMode.EXPLORE,
            preferred_capability_path="conversation_runtime",
            specialist_delegation_recommended=False,
            risk_level="low",
            requires_evidence=False,
            verification_intensity="low",
            execution_strategy="direct_response",
            recommended_specialists=[],
            reasoning="default conversational read-only routing",
        )

    @staticmethod
    def _repository_analysis_decision() -> RoutingDecision:
        return RoutingDecision(
            task_type="repository_analysis",
            preferred_mode=RuntimeMode.EXPLORE,
            preferred_capability_path="repository_intelligence",
            specialist_delegation_recommended=True,
            risk_level="low",
            requires_evidence=False,
            verification_intensity="medium",
            execution_strategy="analyze_then_report",
            recommended_specialists=["repoImpactAnalyzer", "largeTaskPlanner"],
            reasoning="repository-analysis request detected",
        )

    def _code_mutation_decision(self, lowered: str, metadata: dict[str, object]) -> RoutingDecision:
        is_large_task = self._is_large_task(lowered, metadata)
        return RoutingDecision(
            task_type="code_mutation",
            preferred_mode=RuntimeMode.PLAN,
            preferred_capability_path="engineering_workflow",
            specialist_delegation_recommended=True,
            risk_level="high",
            requires_evidence=True,
            verification_intensity="high",
            execution_strategy="multi_step_engineering" if is_large_task else "plan_then_execute",
            recommended_specialists=[
                "advancedPlannerSpecialist",
                "dependencyImpactSpecialist",
                "testSelectionSpecialist",
            ],
            reasoning="large engineering mutation request detected" if is_large_task else "mutation-oriented request detected",
        )

    @staticmethod
    def _verification_decision() -> RoutingDecision:
        return RoutingDecision(
            task_type="verification",
            preferred_mode=RuntimeMode.VERIFY,
            preferred_capability_path="verification_workflow",
            specialist_delegation_recommended=True,
            risk_level="medium",
            requires_evidence=False,
            verification_intensity="high",
            execution_strategy="verify_only",
            recommended_specialists=["testSelectionSpecialist"],
            reasoning="verification-oriented request detected",
        )

    @staticmethod
    def _recovery_decision() -> RoutingDecision:
        return RoutingDecision(
            task_type="recovery",
            preferred_mode=RuntimeMode.RECOVER,
            preferred_capability_path="recovery_workflow",
            specialist_delegation_recommended=True,
            risk_level="medium",
            requires_evidence=True,
            verification_intensity="high",
            execution_strategy="recover_then_verify",
            recommended_specialists=["dependencyImpactSpecialist", "testSelectionSpecialist"],
            reasoning="recovery-oriented request detected",
        )

    @staticmethod
    def _reporting_decision() -> RoutingDecision:
        return RoutingDecision(
            task_type="reporting",
            preferred_mode=RuntimeMode.REPORT,
            preferred_capability_path="reporting_workflow",
            specialist_delegation_recommended=True,
            risk_level="low",
            requires_evidence=False,
            verification_intensity="low",
            execution_strategy="report_only",
            recommended_specialists=["pr_summary_generator"],
            reasoning="reporting-oriented request detected",
        )


def classify_task(message: str, metadata: dict[str, object] | None = None) -> RoutingDecision:
    return CapabilityRouter().classify_task(message, metadata)
