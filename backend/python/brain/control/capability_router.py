from __future__ import annotations

from dataclasses import asdict, dataclass, field

from brain.runtime.models.capability_routing import CapabilityRoutingRecord

from .mode_engine import RuntimeMode


@dataclass(frozen=True)
class RoutingDecision:
    intent: str
    strategy: str
    confidence: float
    requires_tools: bool
    requires_node_runtime: bool
    fallback_allowed: bool
    internal_reasoning_hint: str
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
    suggested_tools: list[str] = field(default_factory=list)
    must_execute: bool = False
    decision_reason_codes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["preferred_mode"] = self.preferred_mode.value
        return data

    def as_runtime_record(self) -> CapabilityRoutingRecord:
        return CapabilityRoutingRecord(
            intent=self.intent,
            strategy=self.strategy,
            confidence=self.confidence,
            requires_tools=self.requires_tools,
            requires_node_runtime=self.requires_node_runtime,
            fallback_allowed=self.fallback_allowed,
            internal_reasoning_hint=self.internal_reasoning_hint,
        )


class CapabilityRouter:
    _FILE_READ_PATTERNS = (
        "analise o arquivo",
        "analyze the file",
        "analyze file",
        "leia o arquivo",
        "read the file",
        "read file",
        "abra o arquivo",
        "open the file",
        "mostre o arquivo",
        "show the file",
        "conteudo do arquivo",
        "contents of file",
    )
    _FILE_SEARCH_PATTERNS = (
        "encontre o arquivo",
        "find the file",
        "find file",
        "procure o arquivo",
        "search file",
        "busque o arquivo",
        "localize o arquivo",
        "glob ",
    )
    _FILE_REFERENCE_HINTS = (
        ".json",
        ".ts",
        ".tsx",
        ".js",
        ".jsx",
        ".py",
        ".rs",
        ".toml",
        ".md",
        ".yaml",
        ".yml",
        "package.json",
        "cargo.toml",
        "requirements.txt",
        "pyproject.toml",
        "tsconfig.json",
    )
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
        "ajuste",
        "corrija o",
        "corrija a",
        "fix the",
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
        if self._looks_like_file_read(lowered):
            return self._file_read_decision()
        if self._looks_like_file_search(lowered):
            return self._file_search_decision()
        if self._matches_any(lowered, self._REPORTING_PATTERNS):
            return self._reporting_decision()
        if self._matches_any(lowered, self._RECOVERY_PATTERNS):
            return self._recovery_decision()
        if self._matches_any(lowered, self._VERIFICATION_PATTERNS):
            return self._verification_decision()
        if self._matches_any(lowered, self._MUTATION_PATTERNS):
            return self._code_mutation_decision(lowered, metadata)
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

    def _looks_like_file_read(self, lowered: str) -> bool:
        if self._matches_any(lowered, self._FILE_READ_PATTERNS):
            return True
        return any(hint in lowered for hint in self._FILE_REFERENCE_HINTS) and any(
            token in lowered for token in ("analise", "analyze", "leia", "read", "abra", "open", "explique", "explain")
        )

    def _looks_like_file_search(self, lowered: str) -> bool:
        if self._matches_any(lowered, self._FILE_SEARCH_PATTERNS):
            return True
        return any(hint in lowered for hint in self._FILE_REFERENCE_HINTS) and any(
            token in lowered for token in ("encontre", "find", "procure", "search", "busque", "localize")
        )

    @staticmethod
    def _default_decision() -> RoutingDecision:
        return RoutingDecision(
            intent="ask_question",
            strategy="DIRECT_RESPONSE",
            confidence=0.64,
            requires_tools=False,
            requires_node_runtime=False,
            fallback_allowed=True,
            internal_reasoning_hint="deterministic conversational routing selected",
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
            suggested_tools=[],
            must_execute=False,
            decision_reason_codes=["default_conversational_route"],
        )

    @staticmethod
    def _file_read_decision() -> RoutingDecision:
        return RoutingDecision(
            intent="analyze",
            strategy="TOOL_ASSISTED",
            confidence=0.88,
            requires_tools=True,
            requires_node_runtime=False,
            fallback_allowed=True,
            internal_reasoning_hint="explicit file inspection should use a deterministic local read path before synthesis",
            task_type="repository_analysis",
            preferred_mode=RuntimeMode.EXPLORE,
            preferred_capability_path="repository_intelligence",
            specialist_delegation_recommended=False,
            risk_level="low",
            requires_evidence=True,
            verification_intensity="medium",
            execution_strategy="inspect_then_report",
            recommended_specialists=[],
            reasoning="explicit file inspection request detected",
            suggested_tools=["read_file"],
            must_execute=True,
            decision_reason_codes=["explicit_file_read", "deterministic_tool_first"],
        )

    @staticmethod
    def _file_search_decision() -> RoutingDecision:
        return RoutingDecision(
            intent="analyze",
            strategy="TOOL_ASSISTED",
            confidence=0.84,
            requires_tools=True,
            requires_node_runtime=False,
            fallback_allowed=True,
            internal_reasoning_hint="workspace file discovery should use deterministic search before higher-cost reasoning",
            task_type="repository_analysis",
            preferred_mode=RuntimeMode.EXPLORE,
            preferred_capability_path="repository_intelligence",
            specialist_delegation_recommended=False,
            risk_level="low",
            requires_evidence=True,
            verification_intensity="medium",
            execution_strategy="inspect_then_report",
            recommended_specialists=[],
            reasoning="explicit workspace file search request detected",
            suggested_tools=["glob_search"],
            must_execute=True,
            decision_reason_codes=["explicit_file_search", "deterministic_tool_first"],
        )

    @staticmethod
    def _repository_analysis_decision() -> RoutingDecision:
        return RoutingDecision(
            intent="analyze",
            strategy="MULTI_STEP_REASONING",
            confidence=0.81,
            requires_tools=False,
            requires_node_runtime=False,
            fallback_allowed=True,
            internal_reasoning_hint="repository analysis benefits from staged reasoning",
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
            suggested_tools=["code_search"],
            must_execute=False,
            decision_reason_codes=["repository_analysis_route"],
        )

    def _code_mutation_decision(self, lowered: str, metadata: dict[str, object]) -> RoutingDecision:
        is_large_task = self._is_large_task(lowered, metadata)
        requires_node_runtime = bool(metadata.get("requires_node_runtime")) or any(
            signal in lowered
            for signal in ("node runtime", "bun", "queryengine", "js-runner", "javascript bridge", "node bridge")
        )
        return RoutingDecision(
            intent="execute_tool_like_action" if requires_node_runtime else "plan",
            strategy="NODE_RUNTIME_DELEGATION" if requires_node_runtime else "TOOL_ASSISTED",
            confidence=0.86 if is_large_task else 0.8,
            requires_tools=True,
            requires_node_runtime=requires_node_runtime,
            fallback_allowed=True,
            internal_reasoning_hint=(
                "mutation request delegated through node runtime aware workflow"
                if requires_node_runtime
                else "mutation request requires staged execution planning"
            ),
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
            suggested_tools=["read_file", "test_runner"] if requires_node_runtime else ["write_file", "test_runner"],
            must_execute=True,
            decision_reason_codes=[
                "code_mutation_route",
                "node_runtime_required" if requires_node_runtime else "tool_assisted_mutation",
            ],
        )

    @staticmethod
    def _verification_decision() -> RoutingDecision:
        return RoutingDecision(
            intent="classify",
            strategy="TOOL_ASSISTED",
            confidence=0.78,
            requires_tools=True,
            requires_node_runtime=False,
            fallback_allowed=True,
            internal_reasoning_hint="verification requests are better served by tool-backed validation",
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
            suggested_tools=["test_runner"],
            must_execute=True,
            decision_reason_codes=["verification_route", "tool_backed_validation"],
        )

    @staticmethod
    def _recovery_decision() -> RoutingDecision:
        return RoutingDecision(
            intent="analyze",
            strategy="MULTI_STEP_REASONING",
            confidence=0.79,
            requires_tools=True,
            requires_node_runtime=False,
            fallback_allowed=True,
            internal_reasoning_hint="recovery flows combine diagnosis, targeted changes, and verification",
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
            suggested_tools=["read_file", "test_runner"],
            must_execute=True,
            decision_reason_codes=["recovery_route", "diagnose_then_verify"],
        )

    @staticmethod
    def _reporting_decision() -> RoutingDecision:
        return RoutingDecision(
            intent="summarize",
            strategy="DIRECT_RESPONSE",
            confidence=0.72,
            requires_tools=False,
            requires_node_runtime=False,
            fallback_allowed=True,
            internal_reasoning_hint="reporting requests synthesize existing runtime artifacts",
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
            suggested_tools=[],
            must_execute=False,
            decision_reason_codes=["reporting_route"],
        )


def classify_task(message: str, metadata: dict[str, object] | None = None) -> RoutingDecision:
    return CapabilityRouter().classify_task(message, metadata)
