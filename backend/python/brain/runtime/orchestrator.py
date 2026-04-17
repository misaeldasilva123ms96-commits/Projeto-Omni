from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import shutil
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from brain.control.capability_router import CapabilityRouter
from brain.control.evidence_gate import EvidenceGate, EvidenceGateResult
from brain.control.mode_engine import RuntimeMode, build_mode_transition_event, can_transition
from brain.control.policy_engine import PolicyBundleResult, PolicyEngine, PolicyResult
from brain.evolution.evaluator import Evaluator
from brain.evolution.strategy_updater import StrategyUpdater
from brain.memory.context_budget import ContextBudgetDecision, ContextBudgetManager, RetrievalPlan
from brain.memory.decision_memory import DecisionMemoryStore
from brain.memory.evidence_memory import EvidenceMemoryStore
from brain.memory.hybrid import HybridMemory
from brain.memory.store import (
    DEFAULT_HISTORY_LIMIT,
    append_history,
    load_memory_store,
    save_memory_store,
)
from brain.runtime.language import normalize_input_to_oil_request
from brain.memory.working_memory import WorkingMemoryStore
from brain.registry import describe_agents, describe_capabilities, recommend_capabilities
from brain.runtime.checkpoint_store import CheckpointStore
from brain.runtime.continuation import ContinuationDecisionType, ContinuationExecutor
from brain.runtime.control import GovernanceResolutionController, RunRegistry, RunStatus
from brain.runtime.control.run_identity import coerce_runtime_run_id, validate_run_id_for_new_write
from brain.runtime.control.governed_tools import (
    GOVERNED_TOOLS_STRICT_BLOCK_KIND,
    build_strict_block_evaluation,
    evaluate_tool_governance,
    governance_dict_for_strict_block,
    is_strict_governed_tools_mode,
    sync_governed_tools_from_trusted_executor_surface,
)
from brain.runtime.execution import ExecutionIntent, ExecutionPolicy, RiskLevel, TrustedExecutor
from brain.runtime.execution_state import build_execution_state
from brain.runtime.engineering_tools import ENGINEERING_TOOLS, execute_engineering_action, supports_engineering_tool
from brain.runtime.engine_adoption_store import EngineAdoptionStore
from brain.runtime.evolution import EvolutionExecutor
from brain.runtime.goals import GoalContext
from brain.runtime.js_runtime_adapter import JSRuntimeAdapter
from brain.runtime.learning import LearningExecutor
from brain.runtime.memory import MemoryFacade, UnifiedMemoryLayer
from brain.runtime.orchestration import OrchestrationExecutor
from brain.runtime.orchestrator_services import (
    CompletionService,
    ExecutionDispatchService,
    GovernanceIntegrationService,
    RunLifecycleService,
    SessionService,
)
from brain.runtime.reasoning import ReasoningEngine
from brain.runtime.milestone_manager import MilestoneManager
from brain.runtime.planning import PlanningEngine, PlanningExecutor
from brain.runtime.pr_summary_generator import build_pr_summary
from brain.runtime.self_repair import RepairStatus, SelfRepairLoop
from brain.runtime.self_repair.repair_policy import RepairPolicyEngine
from brain.runtime.session_store import SessionStore
from brain.runtime.simulation import ActionSimulator, SimulationStore
from brain.runtime.specialists import SpecialistCoordinator
from brain.runtime.rust_executor_bridge import execute_action, summarize_action_result
from brain.runtime.supervision import CognitiveSupervisor
from brain.runtime.transcript_store import TranscriptStore
from brain.swarm.swarm_orchestrator import SwarmOrchestrator


SAFE_FALLBACK_RESPONSE = "Nao consegui processar isso ainda, mas estou aprendendo."
NODE_FALLBACK_RESPONSE = (
    "Modo fallback ativo: o motor Node nao respondeu de forma utilizavel, "
    "entao mantive uma resposta degradada e segura."
)
MOCK_RUNTIME_RESPONSE = (
    "Modo mock ativo: esta resposta foi gerada sem acionar o caminho completo do runtime."
)
SUBPROCESS_TIMEOUT_SECONDS = 60
DEFAULT_SESSION_ID = "python-session"
CONTROL_LAYER_BLOCK_PREFIX = "Execucao bloqueada pela camada de controle"
MUTATING_TOOLS = {
    "write_file",
    "filesystem_write",
    "git_commit",
    "package_manager",
    "autonomous_debug_loop",
    "filesystem_patch_set",
    "shell_command",
}
VERIFICATION_TOOLS = {"test_runner", "verification_runner"}
READ_ONLY_TOOLS = {
    "read_file",
    "filesystem_read",
    "directory_tree",
    "glob_search",
    "grep_search",
    "code_search",
    "dependency_inspection",
    "git_status",
    "git_diff",
}
TRUSTED_EXECUTION_KNOWN_TOOLS = (
    MUTATING_TOOLS
    | VERIFICATION_TOOLS
    | READ_ONLY_TOOLS
    | ENGINEERING_TOOLS
    | {
        "shell_command",
        "read_file",
        "write_file",
        "glob_search",
        "grep_search",
        "none",
    }
)


@dataclass
class BrainPaths:
    root: Path
    python_root: Path
    memory_json: Path
    memory_dir: Path
    transcripts_dir: Path
    sessions_dir: Path
    js_runner: Path
    swarm_log: Path
    evolution_dir: Path

    @staticmethod
    def _is_project_root(candidate: Path) -> bool:
        return (
            (candidate / "backend" / "python").exists()
            and (candidate / "backend" / "rust").exists()
            and (candidate / "package.json").exists()
        )

    @classmethod
    def _detect_project_root(cls, entrypoint: Path) -> Path:
        env_root = os.getenv("BASE_DIR", "").strip()
        if env_root:
            candidate = Path(env_root).resolve()
            if cls._is_project_root(candidate):
                return candidate

        entrypoint = entrypoint.resolve()
        search_start = entrypoint if entrypoint.is_dir() else entrypoint.parent
        for candidate in (search_start, *search_start.parents):
            resolved = candidate.resolve()
            if cls._is_project_root(resolved):
                return resolved

        current_dir = os.path.dirname(os.path.abspath(__file__))
        return Path(os.path.abspath(os.path.join(current_dir, "../../../../"))).resolve()

    @classmethod
    def _detect_python_root(cls, project_root: Path, entrypoint: Path) -> Path:
        env_python_root = os.getenv("PYTHON_BASE_DIR", "").strip()
        if env_python_root:
            candidate = Path(env_python_root).resolve()
            if (candidate / "brain").exists():
                return candidate

        entrypoint = entrypoint.resolve()
        if entrypoint.is_file() and entrypoint.parent.name == "python":
            return entrypoint.parent
        if entrypoint.is_file() and entrypoint.parent.name == "runtime":
            return entrypoint.parents[2]
        return (project_root / "backend" / "python").resolve()

    @classmethod
    def from_entrypoint(cls, entrypoint: Path) -> "BrainPaths":
        project_root = cls._detect_project_root(entrypoint)
        python_root = cls._detect_python_root(project_root, entrypoint)
        return cls(
            root=project_root,
            python_root=python_root,
            memory_json=Path(os.getenv("MEMORY_JSON_PATH", str(python_root / "memory.json"))),
            memory_dir=Path(os.getenv("MEMORY_DIR", str(python_root / "memory"))),
            transcripts_dir=Path(os.getenv("TRANSCRIPTS_DIR", str(python_root / "transcripts"))),
            sessions_dir=Path(
                os.getenv(
                    "SESSIONS_DIR",
                    str(python_root / "brain" / "runtime" / "sessions"),
                )
            ),
            js_runner=project_root / "js-runner" / "queryEngineRunner.js",
            swarm_log=python_root / "brain" / "runtime" / "swarm_log.json",
            evolution_dir=python_root / "brain" / "evolution",
        )


class BrainOrchestrator:
    def _governance_resolution_controller(self) -> GovernanceResolutionController | None:
        """Present when ``run_registry`` initialized; absent if ``__init__`` was bypassed (e.g. partial tests)."""
        return getattr(self, "_governance_controller", None)

    def __init__(self, paths: BrainPaths) -> None:
        self.paths = paths
        self._closed = False
        self.hybrid_memory = HybridMemory(paths.memory_dir)
        memory_log_dir = paths.root / ".logs" / "fusion-runtime"
        self.working_memory = WorkingMemoryStore(memory_log_dir / "working-memory.json")
        self.decision_memory = DecisionMemoryStore(memory_log_dir / "decision-memory.json")
        self.evidence_memory = EvidenceMemoryStore(memory_log_dir / "evidence-memory.json")
        self.context_budget_manager = ContextBudgetManager()
        self.transcript_store = TranscriptStore(paths.transcripts_dir)
        self.checkpoint_store = CheckpointStore(paths.root)
        self.session_store = SessionStore(paths.sessions_dir)
        self.swarm_orchestrator = SwarmOrchestrator(paths.swarm_log)
        self.evaluator = Evaluator()
        self.strategy_updater = StrategyUpdater(paths.evolution_dir)
        self.supervisor = CognitiveSupervisor()
        self.capability_router = CapabilityRouter()
        self.evidence_gate = EvidenceGate()
        self.policy_engine = PolicyEngine()
        self.current_control_mode = RuntimeMode.EXPLORE
        self.last_runtime_mode = "live"
        self.last_runtime_reason = "startup"
        self.trusted_executor = TrustedExecutor(
            available_capabilities={item["name"] for item in describe_capabilities()},
            available_tools=set(TRUSTED_EXECUTION_KNOWN_TOOLS),
            policy=self._trusted_execution_policy(),
        )
        sync_governed_tools_from_trusted_executor_surface(self.trusted_executor.available_tools)
        self.evolution_executor = EvolutionExecutor(self.paths.root)
        self.memory_facade = MemoryFacade(self.paths.root)
        self.engine_adoption_store = EngineAdoptionStore(self.paths.root)
        try:
            self.run_registry = RunRegistry(self.paths.root)
            self._governance_controller = GovernanceResolutionController(self.run_registry)
        except Exception:
            self.run_registry = None
            self._governance_controller = None
        self.learning_executor = LearningExecutor(self.paths.root, memory_facade=self.memory_facade)
        self.orchestration_executor = OrchestrationExecutor(self.paths.root)
        self.simulation_store = SimulationStore(self.paths.root)
        self.action_simulator = ActionSimulator(self.paths.root, memory_facade=self.memory_facade, store=self.simulation_store)
        self.specialist_coordinator = SpecialistCoordinator(
            self.paths.root,
            memory_facade=self.memory_facade,
            simulator=self.action_simulator,
            simulation_store=self.simulation_store,
        )
        self.continuation_executor = ContinuationExecutor(
            self.paths.root,
            memory_facade=self.memory_facade,
            simulator=self.action_simulator,
        )
        self.planning_executor = PlanningExecutor(self.paths.root)
        self._session_service = SessionService(self.checkpoint_store)
        self._run_lifecycle = RunLifecycleService(
            run_registry=self.run_registry,
            get_controller=self._governance_resolution_controller,
        )
        self._governance_integration = GovernanceIntegrationService(
            run_registry=self.run_registry,
            get_controller=self._governance_resolution_controller,
            run_lifecycle=self._run_lifecycle,
        )
        self._completion_service = CompletionService(
            get_controller=self._governance_resolution_controller,
            run_lifecycle=self._run_lifecycle,
            progress_fn=BrainOrchestrator._progress_from_step_results,
        )
        self._execution_dispatch = ExecutionDispatchService(
            self,
            governance=self._governance_integration,
            progress_fn=BrainOrchestrator._progress_from_step_results,
        )
        self.js_runtime_adapter = JSRuntimeAdapter(self.paths.root)
        self.reasoning_engine = ReasoningEngine()
        self.unified_memory = UnifiedMemoryLayer(
            transcript_store=self.transcript_store,
            memory_facade=self.memory_facade,
            working_store=self.working_memory,
            decision_store=self.decision_memory,
            evidence_store=self.evidence_memory,
            run_registry=self.run_registry,
        )
        self.planning_engine = PlanningEngine()
        self.self_repair_loop = SelfRepairLoop(
            workspace_root=self.paths.root,
            policy=self._self_repair_policy(),
        )

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            self.memory_facade.close()
        except Exception:
            return

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            return

    def _trusted_execution_policy(self) -> ExecutionPolicy:
        allow_high_risk = str(os.getenv("OMINI_ALLOW_HIGH_RISK", "true")).lower() != "false"
        allow_critical = str(os.getenv("OMINI_ALLOW_CRITICAL", "false")).lower() == "true"
        max_risk = RiskLevel.CRITICAL if allow_critical else RiskLevel.HIGH if allow_high_risk else RiskLevel.MEDIUM
        return ExecutionPolicy(
            max_risk=max_risk,
            allow_high_risk=allow_high_risk,
            allow_critical=allow_critical,
            require_session_for_mutation=True,
        )

    def _self_repair_policy(self):
        return RepairPolicyEngine.from_env()

    def _build_execution_intent(
        self,
        *,
        action: dict[str, Any],
        session_id: str,
        task_id: str,
        run_id: str,
    ) -> ExecutionIntent:
        selected_tool = str(action.get("selected_tool", "")).strip()
        tool_arguments = dict(action.get("tool_arguments", {}) or {})
        description = str(
            action.get("description")
            or action.get("title")
            or action.get("goal")
            or action.get("summary")
            or f"Execute {selected_tool or 'runtime action'}"
        ).strip()
        if selected_tool in READ_ONLY_TOOLS:
            action_type = "read"
        elif selected_tool in MUTATING_TOOLS:
            action_type = "mutate"
        elif selected_tool in VERIFICATION_TOOLS:
            action_type = "verify"
        elif selected_tool in {"shell_command", "git_commit", "package_manager"}:
            action_type = "execute"
        else:
            action_type = str(action.get("action_type", "execute") or "execute")

        expected_fields: list[str] = []
        if selected_tool in {"filesystem_read", "read_file"}:
            expected_fields.append("file.content")
        elif selected_tool in {"filesystem_write", "filesystem_patch_set"}:
            expected_fields.append("workspace_root")

        return ExecutionIntent(
            action_id=str(action.get("step_id", "") or action.get("action_id", selected_tool or "runtime-action")),
            action_type=action_type,
            capability=selected_tool or str(action.get("selected_capability", "unknown-tool")),
            description=description,
            input_payload_summary={
                "selected_tool": selected_tool,
                "tool_arguments": tool_arguments,
                "selected_agent": action.get("selected_agent"),
            },
            expected_outcome=str(action.get("expected_outcome", f"Successful completion of {selected_tool or 'runtime action'}")).strip(),
            reversible=selected_tool in READ_ONLY_TOOLS or selected_tool in VERIFICATION_TOOLS,
            target_subsystem="engineering_tools" if supports_engineering_tool(selected_tool) else "rust_bridge",
            session_id=session_id or None,
            task_id=task_id or None,
            run_id=run_id or None,
            metadata={"expected_fields": expected_fields},
        )

    def run(self, message: str) -> str:
        self.last_runtime_mode = self._selected_runtime_mode()
        self.last_runtime_reason = "configured_mode"
        strategy_state = self.strategy_updater.load_current_state()
        history_limit = int(strategy_state.get("memory_rules", {}).get("history_limit", DEFAULT_HISTORY_LIMIT))
        session_id = self._session_id()

        memory_store = load_memory_store(
            self.paths.memory_json,
            history_limit=history_limit,
        )
        transcript_history = self.transcript_store.load_recent_history(
            session_id,
            limit=history_limit,
        )
        memory_store["history"] = self._merge_recent_history(
            transcript_history,
            memory_store.get("history", [])
            if isinstance(memory_store.get("history", []), list)
            else [],
            history_limit,
        )

        if not message.strip():
            self.last_runtime_mode = "fallback"
            self.last_runtime_reason = "empty_message"
            return SAFE_FALLBACK_RESPONSE

        if self.last_runtime_mode == "mock":
            self._record_runtime_mode_event(
                session_id=session_id,
                mode="mock",
                reason_code="mock_mode_configured",
                details={"message_preview": message[:120]},
            )
            return MOCK_RUNTIME_RESPONSE

        reasoning_handoff: dict[str, Any]
        reasoning_payload: dict[str, Any]
        memory_context_payload: dict[str, Any]
        planning_payload: dict[str, Any] = {}
        try:
            reasoning_oil_request = normalize_input_to_oil_request(
                message,
                session_id=session_id,
                run_id="",
                metadata={
                    "source_component": "runtime.orchestrator",
                    "reasoning_phase": "memory_context_build",
                },
            )
            memory_context = self.unified_memory.build_reasoning_context(
                session_id=session_id,
                run_id="",
                query=message,
                oil_request=reasoning_oil_request,
                memory_store=memory_store,
                max_items=8,
            )
            memory_context_payload = memory_context.as_dict()
            self._append_runtime_event(
                event_type="runtime.memory_intelligence.trace",
                session_id=session_id,
                task_id="",
                run_id="",
                payload={
                    "context_id": memory_context_payload.get("context_id"),
                    "selected_count": memory_context_payload.get("selected_count", 0),
                    "total_candidates": memory_context_payload.get("total_candidates", 0),
                    "sources_used": memory_context_payload.get("sources_used", []),
                    "context_summary": memory_context_payload.get("context_summary", ""),
                    "scoring": memory_context_payload.get("scoring", {}),
                },
            )
            reasoning_outcome = self.reasoning_engine.reason(
                raw_input=message,
                session_id=session_id,
                run_id="",
                source_component="runtime.orchestrator",
                oil_request=reasoning_oil_request,
                memory_context=memory_context_payload,
            )
            reasoning_handoff = dict(reasoning_outcome.execution_handoff)
            reasoning_payload = reasoning_outcome.as_dict()
            self._append_runtime_event(
                event_type="runtime.reasoning.trace",
                session_id=session_id,
                task_id="",
                run_id="",
                payload={
                    "trace": reasoning_outcome.trace.as_dict(),
                    "handoff": reasoning_handoff,
                    "oil_request": reasoning_outcome.oil_request.serialize(),
                    "oil_result": reasoning_outcome.oil_result.serialize(),
                },
            )
            runtime_message = reasoning_outcome.normalized_input or message
        except Exception as exc:
            runtime_message = message
            reasoning_handoff = {
                "proceed": True,
                "mode": "fast",
                "intent": self._predict_intent(message),
                "suggested_capabilities": [],
                "validation": {"outcome": "fallback"},
            }
            memory_context_payload = {
                "context_id": "",
                "selected_count": 0,
                "sources_used": [],
                "context_summary": "memory_context_build_failed",
            }
            reasoning_payload = {
                "mode": "fast",
                "normalized_input": message.strip(),
                "execution_handoff": reasoning_handoff,
                "trace": {
                    "trace_id": "",
                    "mode": "fast",
                    "validation_result": "fallback",
                    "handoff_decision": "proceed",
                },
                "error": str(exc),
                "memory_context": dict(memory_context_payload),
            }
            self._append_runtime_event(
                event_type="runtime.reasoning.trace",
                session_id=session_id,
                task_id="",
                run_id="",
                payload={
                    "trace": reasoning_payload["trace"],
                    "handoff": reasoning_handoff,
                    "error": str(exc),
                },
            )
        if not reasoning_handoff.get("proceed", False):
            self.last_runtime_mode = "fallback"
            self.last_runtime_reason = "reasoning_validation_block"
            return SAFE_FALLBACK_RESPONSE
        control_metadata = self._build_control_metadata(message=runtime_message)
        control_metadata["reasoning"] = reasoning_payload
        control_metadata["memory_intelligence"] = dict(memory_context_payload)
        control_result = self._evaluate_control_layer(
            session_id=session_id,
            message=runtime_message,
            task_id="",
            run_id="",
            metadata=control_metadata,
        )
        context_budget, retrieval_plan = self._build_context_budget(
            routing_decision=control_result["routing_decision"]
        )
        memory_context = self._update_structured_memory(
            session_id=session_id,
            task_id="",
            run_id="",
            message=runtime_message,
            control_metadata=control_metadata,
            control_result=control_result,
            budget=context_budget,
            retrieval_plan=retrieval_plan,
            strategy_state=strategy_state if isinstance(strategy_state, dict) else None,
        )
        self._emit_control_event(
            "runtime.control.routing_decision",
            session_id=session_id,
            task_id="",
            run_id="",
            payload={
                "control_mode": self.current_control_mode.value,
                "task_type": control_result["routing_decision"].task_type,
                "capability_path": control_result["routing_decision"].preferred_capability_path,
                "risk_level": control_result["routing_decision"].risk_level,
                "execution_strategy": control_result["routing_decision"].execution_strategy,
                "verification_intensity": control_result["routing_decision"].verification_intensity,
                "recommended_specialists": control_result["routing_decision"].recommended_specialists,
                "delegation_recommended": control_result["routing_decision"].specialist_delegation_recommended,
                "routing_reason": control_result["routing_decision"].reasoning,
                "allowed": control_result["allowed"],
            },
        )
        if not control_result["allowed"]:
            self._record_control_outcome_memory(
                session_id=session_id,
                task_id="",
                run_id="",
                control_result=control_result,
                allowed=False,
            )
            self._emit_control_event(
                str(control_result["blocked_event_type"]),
                session_id=session_id,
                task_id="",
                run_id="",
                payload={
                    "control_mode": self.current_control_mode.value,
                    "task_type": control_result["routing_decision"].task_type,
                    "capability_path": control_result["routing_decision"].preferred_capability_path,
                    "risk_level": control_result["routing_decision"].risk_level,
                    "execution_strategy": control_result["routing_decision"].execution_strategy,
                    "verification_intensity": control_result["routing_decision"].verification_intensity,
                    "recommended_specialists": control_result["routing_decision"].recommended_specialists,
                    "delegation_recommended": control_result["routing_decision"].specialist_delegation_recommended,
                    "routing_reason": control_result["routing_decision"].reasoning,
                    "policy_results": [self._policy_result_to_dict(item) for item in control_result["policy_result"].results],
                    "missing_evidence_types": control_result["evidence_result"].missing_evidence_types,
                    "reason_code": control_result["blocked_reason_code"],
                    "allowed": False,
                },
            )
            if can_transition(self.current_control_mode, RuntimeMode.REPORT):
                self._emit_control_event(
                    "runtime.control.mode_transition",
                    session_id=session_id,
                    task_id="",
                    run_id="",
                    payload=build_mode_transition_event(
                        session_id=session_id,
                        from_mode=self.current_control_mode,
                        to_mode=RuntimeMode.REPORT,
                        reason_code="control_layer_block",
                        details={"task_type": control_result["routing_decision"].task_type},
                    ),
                )
                self.current_control_mode = RuntimeMode.REPORT
            self.last_runtime_mode = "fallback"
            self.last_runtime_reason = "control_layer_block"
            return str(control_result["blocked_response"])

        if control_result["mode_transition"] is not None:
            self._emit_control_event(
                "runtime.control.mode_transition",
                session_id=session_id,
                task_id="",
                run_id="",
                payload=control_result["mode_transition"],
            )
            self.current_control_mode = control_result["target_mode"]
        self._record_control_outcome_memory(
            session_id=session_id,
            task_id="",
            run_id="",
            control_result=control_result,
            allowed=True,
        )
        self._emit_control_event(
            "runtime.control.execution_allowed",
            session_id=session_id,
            task_id="",
            run_id="",
            payload={
                "control_mode": self.current_control_mode.value,
                "task_type": control_result["routing_decision"].task_type,
                "capability_path": control_result["routing_decision"].preferred_capability_path,
                "risk_level": control_result["routing_decision"].risk_level,
                "execution_strategy": control_result["routing_decision"].execution_strategy,
                "verification_intensity": control_result["routing_decision"].verification_intensity,
                "recommended_specialists": control_result["routing_decision"].recommended_specialists,
                "delegation_recommended": control_result["routing_decision"].specialist_delegation_recommended,
                "routing_reason": control_result["routing_decision"].reasoning,
                "policy_results": [self._policy_result_to_dict(item) for item in control_result["policy_result"].results],
                "missing_evidence_types": control_result["evidence_result"].missing_evidence_types,
                "reason_code": "execution_allowed",
                "allowed": True,
            },
        )

        rd = control_result["routing_decision"]
        execution_plan, planning_trace = self.planning_engine.build_execution_plan(
            handoff=dict(reasoning_handoff),
            reasoning_trace=dict(reasoning_payload.get("trace") or {}),
            session_id=session_id,
            run_id="",
            task_id="",
            normalized_input=str(runtime_message).strip(),
            control_routing={
                "task_type": rd.task_type,
                "risk_level": rd.risk_level,
                "execution_strategy": rd.execution_strategy,
                "verification_intensity": rd.verification_intensity,
            },
        )
        planning_payload = {
            "execution_plan": execution_plan.as_dict(),
            "planning_trace": planning_trace.as_dict(),
        }
        self._append_runtime_event(
            event_type="runtime.planning_intelligence.trace",
            session_id=session_id,
            task_id="",
            run_id="",
            payload=dict(planning_payload),
        )

        self._extract_user_learning(memory_store, message)
        append_history(
            memory_store,
            "user",
            message,
            history_limit=history_limit,
        )

        available_capabilities = self._weighted_capabilities(
            describe_capabilities(),
            strategy_state,
        )
        reasoning_capabilities = [
            str(item).strip()
            for item in reasoning_handoff.get("suggested_capabilities", [])
            if str(item).strip()
        ]
        recommended_capabilities = recommend_capabilities(runtime_message)
        suggested_capabilities = self._weighted_capability_names(
            reasoning_capabilities + recommended_capabilities,
            strategy_state,
        )
        predicted_intent = str(reasoning_handoff.get("intent", "")).strip() or self._predict_intent(runtime_message)
        budgeted_history = self._slice_history_for_budget(
            memory_store.get("history", []),
            context_budget.budget_level,
        )
        summary = self.summarize_history(budgeted_history)
        direct_response = self._answer_from_memory(memory_store, runtime_message)

        swarm_result: dict[str, Any] = {
            "response": direct_response,
            "intent": predicted_intent,
            "delegates": [],
            "agent_trace": [],
            "memory_signal": {},
        }

        if not direct_response:
            swarm_context: dict[str, Any] = {
                "context_budget": self._budget_to_dict(context_budget),
                "retrieval_plan": self._retrieval_plan_to_dict(retrieval_plan),
                "structured_memory": memory_context["retrieved_context"],
                "reasoning_handoff": dict(reasoning_handoff),
                "memory_intelligence": dict(memory_context_payload),
            }
            if planning_payload:
                swarm_context["execution_plan"] = planning_payload["execution_plan"]
                swarm_context["planning_trace"] = planning_payload["planning_trace"]
            swarm_result = asyncio.run(
                self.swarm_orchestrator.run(
                    message=runtime_message,
                    session_id=session_id,
                    memory_store=memory_store,
                    history=budgeted_history,
                    summary=summary,
                    capabilities=available_capabilities,
                    executor=lambda payload: self._async_node_execution(
                        message=runtime_message,
                        memory_store=memory_store,
                        available_capabilities=available_capabilities,
                        session_id=session_id,
                        swarm_payload=payload,
                        context_session=swarm_context,
                    ),
                )
            )

        response = str(swarm_result.get("response", "")).strip() or SAFE_FALLBACK_RESPONSE
        if response == SAFE_FALLBACK_RESPONSE and self.last_runtime_mode == "live":
            self.last_runtime_mode = "fallback"
            self.last_runtime_reason = "empty_swarm_response"
            self._record_runtime_mode_event(
                session_id=session_id,
                mode="fallback",
                reason_code="empty_swarm_response",
                details={"message_preview": message[:120]},
            )

        evaluation = self.evaluator.evaluate(
            session_id=session_id,
            message=message,
            response=response,
            history=memory_store.get("history", []) if isinstance(memory_store.get("history", []), list) else [],
        )

        append_history(
            memory_store,
            "assistant",
            response,
            history_limit=history_limit,
        )
        safe_store = save_memory_store(
            self.paths.memory_json,
            memory_store,
            history_limit=history_limit,
        )
        self.hybrid_memory.sync_from_store(safe_store)
        self.hybrid_memory.record_learning(
            message=message,
            response=response,
            intent=str(swarm_result.get("intent", predicted_intent)),
            capabilities=suggested_capabilities,
        )
        self.hybrid_memory.record_evaluation(evaluation)
        self.transcript_store.append_turn(session_id, message, response)

        evolution_version = int(strategy_state.get("version", 0))
        session_payload = {
            "session_id": session_id,
            "history": safe_store.get("history", []),
            "user": safe_store.get("user", {}),
            "summary": self.summarize_history(safe_store.get("history", [])),
            "capabilities": available_capabilities,
            "agent_registry": describe_agents(),
            "agent_trace": swarm_result.get("agent_trace", []),
            "swarm": {
                "intent": swarm_result.get("intent", predicted_intent),
                "delegates": swarm_result.get("delegates", []),
                "memory_signal": swarm_result.get("memory_signal", {}),
            },
            "reasoning": reasoning_payload,
            "memory_intelligence": dict(memory_context_payload),
            "planning_intelligence": dict(planning_payload),
            "evaluation": evaluation,
            "evolution_version": evolution_version,
        }
        self.session_store.save(session_id, session_payload)
        return response

    async def _async_node_execution(
        self,
        *,
        message: str,
        memory_store: dict[str, object],
        available_capabilities: list[dict[str, str]],
        session_id: str,
        swarm_payload: dict[str, Any],
        context_session: dict[str, Any] | None = None,
    ) -> str:
        extra_session = {"swarm_request": swarm_payload}
        if context_session:
            extra_session.update(context_session)
        return self._call_node_query_engine(
            message=message,
            memory_store=memory_store,
            available_capabilities=available_capabilities,
            session_id=session_id,
            extra_session=extra_session,
        )

    def _session_id(self) -> str:
        configured = os.getenv("AI_SESSION_ID", "").strip()
        return configured or DEFAULT_SESSION_ID

    @staticmethod
    def _selected_runtime_mode() -> str:
        configured = str(os.getenv("OMINI_RUNTIME_MODE", "live") or "live").strip().lower()
        if configured in {"fallback", "mock"}:
            return configured
        return "live"

    @staticmethod
    def _requested_action_for_task_type(task_type: str) -> str:
        return {
            "simple_query": "read",
            "repository_analysis": "search",
            "code_mutation": "plan",
            "verification": "test",
            "recovery": "retry",
            "reporting": "generate_report",
        }.get(task_type, "read")

    @staticmethod
    def _policy_result_to_dict(result: PolicyResult) -> dict[str, Any]:
        return {
            "allowed": result.allowed,
            "policy_name": result.policy_name,
            "reason": result.reason,
            "severity": result.severity,
            "details": result.details,
        }

    @staticmethod
    def _bundle_to_dict(bundle: PolicyBundleResult) -> dict[str, Any]:
        return {
            "allowed": bundle.allowed,
            "results": [BrainOrchestrator._policy_result_to_dict(item) for item in bundle.results],
            "blocking_results": [BrainOrchestrator._policy_result_to_dict(item) for item in bundle.blocking_results],
        }

    @staticmethod
    def _evidence_to_dict(evidence: EvidenceGateResult) -> dict[str, Any]:
        return {
            "enough_evidence": evidence.enough_evidence,
            "missing_evidence_types": evidence.missing_evidence_types,
            "recommendation": evidence.recommendation,
            "severity": evidence.severity,
        }

    @staticmethod
    def _budget_to_dict(budget: ContextBudgetDecision) -> dict[str, Any]:
        return budget.as_dict()

    @staticmethod
    def _retrieval_plan_to_dict(plan: RetrievalPlan) -> dict[str, Any]:
        return plan.as_dict()

    @staticmethod
    def _history_limit_for_budget(budget_level: str) -> int:
        return {"low": 2, "medium": 4, "high": 6}.get(budget_level, 4)

    @staticmethod
    def _summary_limit_for_budget(budget_level: str) -> int:
        return {"low": 600, "medium": 1200, "high": 1800}.get(budget_level, 1200)

    @staticmethod
    def _slice_history_for_budget(history: object, budget_level: str) -> list[dict[str, Any]]:
        if not isinstance(history, list):
            return []
        limit = BrainOrchestrator._history_limit_for_budget(budget_level)
        return [item for item in history[-limit:] if isinstance(item, dict)]

    @staticmethod
    def _summarize_decision_entries(entries: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "count": len(entries),
            "recent": [
                {
                    "decision_type": item.get("decision_type"),
                    "task_type": item.get("task_type"),
                    "reason_code": item.get("reason_code"),
                    "reason": item.get("reason"),
                }
                for item in entries[:3]
            ],
        }

    @staticmethod
    def _summarize_evidence_entries(entries: list[dict[str, Any]]) -> dict[str, Any]:
        latest = entries[0] if entries else {}
        return {
            "count": len(entries),
            "latest": latest.get("evidence", {}) if isinstance(latest, dict) else {},
        }

    def _build_context_budget(
        self,
        *,
        routing_decision: Any,
    ) -> tuple[ContextBudgetDecision, RetrievalPlan]:
        budget = self.context_budget_manager.select_budget(
            task_type=routing_decision.task_type,
            execution_strategy=routing_decision.execution_strategy,
            risk_level=routing_decision.risk_level,
            verification_intensity=routing_decision.verification_intensity,
        )
        retrieval_plan = self.context_budget_manager.build_retrieval_plan(
            task_type=routing_decision.task_type,
            budget=budget,
        )
        return budget, retrieval_plan

    def _build_retrieved_context(
        self,
        *,
        session_id: str,
        task_id: str,
        task_type: str,
        budget: ContextBudgetDecision,
        retrieval_plan: RetrievalPlan,
    ) -> dict[str, Any]:
        context: dict[str, Any] = {}
        limit = budget.max_context_items
        for memory_type in retrieval_plan.load_order:
            if memory_type == "working_memory":
                working_state = self.working_memory.load_session(session_id)
                if memory_type in retrieval_plan.summarized_memory_types:
                    context[memory_type] = {
                        "task_summary": working_state.get("current_task_summary", ""),
                        "execution_strategy": working_state.get("current_execution_strategy", ""),
                        "active_target_files": working_state.get("active_target_files", []),
                        "updated_at": working_state.get("updated_at", ""),
                    }
                else:
                    context[memory_type] = working_state
            elif memory_type == "decision_memory":
                decisions = self.decision_memory.find_decisions(
                    session_id=session_id,
                    task_type=task_type,
                    limit=limit,
                )
                context[memory_type] = (
                    self._summarize_decision_entries(decisions)
                    if memory_type in retrieval_plan.summarized_memory_types
                    else decisions
                )
            elif memory_type == "evidence_memory":
                evidence_entries = self.evidence_memory.get_evidence(
                    session_id=session_id,
                    task_id=task_id or None,
                    limit=limit,
                )
                context[memory_type] = (
                    self._summarize_evidence_entries(evidence_entries)
                    if memory_type in retrieval_plan.summarized_memory_types
                    else evidence_entries
                )
        return context

    def _update_structured_memory(
        self,
        *,
        session_id: str,
        task_id: str,
        run_id: str,
        message: str,
        control_metadata: dict[str, Any],
        control_result: dict[str, Any],
        budget: ContextBudgetDecision,
        retrieval_plan: RetrievalPlan,
        strategy_state: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        routing_decision = control_result["routing_decision"]
        active_target_files = control_metadata.get("target_files", [])
        working_state = self.working_memory.update_session(
            session_id,
            {
                "task_id": task_id,
                "run_id": run_id,
                "current_task_summary": message[:240],
                "current_routing_decision": routing_decision.as_dict(),
                "current_mode": self.current_control_mode.value,
                "current_execution_strategy": routing_decision.execution_strategy,
                "active_target_files": active_target_files if isinstance(active_target_files, list) else [],
                "current_milestones": (
                    strategy_state.get("milestones", [])
                    if isinstance(strategy_state, dict) and isinstance(strategy_state.get("milestones", []), list)
                    else []
                ),
                "context_budget_level": budget.budget_level,
            },
        )
        self._append_runtime_event(
            event_type="runtime.memory.working_updated",
            session_id=session_id,
            task_id=task_id,
            run_id=run_id,
            payload={
                "task_type": routing_decision.task_type,
                "execution_strategy": routing_decision.execution_strategy,
                "active_target_files": working_state.get("active_target_files", []),
                "budget_level": budget.budget_level,
            },
        )
        decision_entry = self.decision_memory.record_decision(
            session_id=session_id,
            task_id=task_id,
            run_id=run_id,
            decision_type="routing_selection",
            task_type=routing_decision.task_type,
            reason_code="routing_selected",
            reason=routing_decision.reasoning,
            metadata={
                "capability_path": routing_decision.preferred_capability_path,
                "execution_strategy": routing_decision.execution_strategy,
                "verification_intensity": routing_decision.verification_intensity,
                "recommended_specialists": routing_decision.recommended_specialists,
            },
        )
        self._append_runtime_event(
            event_type="runtime.memory.decision_recorded",
            session_id=session_id,
            task_id=task_id,
            run_id=run_id,
            payload={
                "decision_type": decision_entry.get("decision_type"),
                "task_type": routing_decision.task_type,
                "reason_code": decision_entry.get("reason_code"),
            },
        )
        evidence_entry = self.evidence_memory.record_evidence(
            session_id=session_id,
            task_id=task_id,
            run_id=run_id,
            task_type=routing_decision.task_type,
            evidence=control_metadata.get("available_evidence", {}),
            metadata={
                "target_files": active_target_files if isinstance(active_target_files, list) else [],
                "verification_plan_present": bool(control_metadata.get("verification_plan")),
            },
        )
        self._append_runtime_event(
            event_type="runtime.memory.evidence_recorded",
            session_id=session_id,
            task_id=task_id,
            run_id=run_id,
            payload={
                "task_type": routing_decision.task_type,
                "evidence": evidence_entry.get("evidence", {}),
            },
        )
        self._append_runtime_event(
            event_type="runtime.context.budget_selected",
            session_id=session_id,
            task_id=task_id,
            run_id=run_id,
            payload=self._budget_to_dict(budget),
        )
        self._append_runtime_event(
            event_type="runtime.context.retrieval_plan",
            session_id=session_id,
            task_id=task_id,
            run_id=run_id,
            payload=self._retrieval_plan_to_dict(retrieval_plan),
        )
        retrieved_context = self._build_retrieved_context(
            session_id=session_id,
            task_id=task_id,
            task_type=routing_decision.task_type,
            budget=budget,
            retrieval_plan=retrieval_plan,
        )
        return {
            "budget": budget,
            "retrieval_plan": retrieval_plan,
            "retrieved_context": retrieved_context,
        }

    def _record_control_outcome_memory(
        self,
        *,
        session_id: str,
        task_id: str,
        run_id: str,
        control_result: dict[str, Any],
        allowed: bool,
    ) -> None:
        routing_decision = control_result["routing_decision"]
        decision_entry = self.decision_memory.record_decision(
            session_id=session_id,
            task_id=task_id,
            run_id=run_id,
            decision_type="execution_allowed" if allowed else str(control_result["blocked_event_type"]).split(".")[-1],
            task_type=routing_decision.task_type,
            reason_code="execution_allowed" if allowed else str(control_result["blocked_reason_code"]),
            reason="control layer allowed execution"
            if allowed
            else str(control_result["blocked_response"]),
            metadata={
                "policy_results": [self._policy_result_to_dict(item) for item in control_result["policy_result"].results],
                "missing_evidence_types": control_result["evidence_result"].missing_evidence_types,
            },
        )
        self._append_runtime_event(
            event_type="runtime.memory.decision_recorded",
            session_id=session_id,
            task_id=task_id,
            run_id=run_id,
            payload={
                "decision_type": decision_entry.get("decision_type"),
                "task_type": routing_decision.task_type,
                "reason_code": decision_entry.get("reason_code"),
            },
        )

    def _emit_control_event(
        self,
        event_type: str,
        *,
        session_id: str,
        task_id: str,
        run_id: str,
        payload: dict[str, Any],
    ) -> None:
        self._append_runtime_event(
            event_type=event_type,
            session_id=session_id,
            task_id=task_id,
            run_id=run_id,
            payload=payload,
        )

    def _build_control_metadata(
        self,
        *,
        message: str,
        metadata: dict[str, Any] | None = None,
        actions: list[dict[str, Any]] | None = None,
        repository_analysis: dict[str, Any] | None = None,
        repo_impact_analysis: dict[str, Any] | None = None,
        verification_plan: dict[str, Any] | None = None,
        engineering_data: dict[str, Any] | None = None,
        policy_summary: object = None,
    ) -> dict[str, Any]:
        combined = dict(metadata or {})
        target_files: list[str] = []
        existing_targets = combined.get("target_files", [])
        if isinstance(existing_targets, list):
            target_files.extend(str(item) for item in existing_targets if isinstance(item, str) and item)

        selected_tools: list[str] = []
        for action in actions or []:
            tool_name = str(action.get("selected_tool", "") or "").strip()
            if tool_name:
                selected_tools.append(tool_name)
            arguments = action.get("tool_arguments", {})
            if isinstance(arguments, dict):
                for key in ("path", "file_path"):
                    value = arguments.get(key)
                    if isinstance(value, str) and value:
                        target_files.append(value)
                paths_value = arguments.get("paths")
                if isinstance(paths_value, list):
                    target_files.extend(str(item) for item in paths_value if isinstance(item, str) and item)

        combined_repository_analysis = repository_analysis if isinstance(repository_analysis, dict) else {}
        combined_repo_impact = repo_impact_analysis if isinstance(repo_impact_analysis, dict) else {}
        combined_engineering = engineering_data if isinstance(engineering_data, dict) else {}
        combined_workspace = combined_engineering.get("workspace_state", {})
        if not isinstance(combined_workspace, dict):
            combined_workspace = {}
        test_results = combined_engineering.get("test_results", {})
        verification_summary = combined_engineering.get("verification_summary", {})

        if "task_type" not in combined:
            if any(tool in MUTATING_TOOLS for tool in selected_tools):
                combined["task_type"] = "code_mutation"
            elif any(tool in VERIFICATION_TOOLS for tool in selected_tools):
                combined["task_type"] = "verification"
            elif selected_tools and all(tool in READ_ONLY_TOOLS for tool in selected_tools):
                combined["task_type"] = "repository_analysis"

        combined["target_files"] = target_files
        combined["repository_analysis"] = combined_repository_analysis
        combined["repo_impact_analysis"] = combined_repo_impact
        combined["workspace_state"] = combined_workspace
        combined["verification_plan"] = verification_plan if isinstance(verification_plan, dict) else {}
        combined["available_evidence"] = {
            "file_evidence": bool(target_files or combined_repository_analysis or combined_repo_impact),
            "runtime_evidence": bool(
                combined_workspace
                or combined.get("runtime_evidence")
                or policy_summary
                or any(bool((action.get("policy_decision") or {}).get("decision")) for action in actions or [])
            ),
            "test_evidence": bool(test_results or verification_summary or verification_plan),
            "dependency_evidence": bool(combined_repo_impact or combined_repository_analysis.get("dependency_graph")),
        }
        return combined

    @staticmethod
    def _compact_history_for_node(history: object, limit: int = 6) -> list[dict[str, Any]]:
        if not isinstance(history, list):
            return []
        compacted: list[dict[str, Any]] = []
        for item in history[-limit:]:
            if not isinstance(item, dict):
                continue
            compacted.append(
                {
                    "role": str(item.get("role", "")),
                    "content": str(item.get("content", ""))[:600],
                }
            )
        return compacted

    def _compact_session_payload_for_node(
        self,
        session_payload: dict[str, Any],
        *,
        history_limit: int = 4,
        summary_limit: int = 1200,
    ) -> dict[str, Any]:
        compact = dict(session_payload)
        compact["history"] = self._compact_history_for_node(compact.get("history", []), limit=history_limit)
        if isinstance(compact.get("summary"), str):
            compact["summary"] = compact["summary"][:summary_limit]
        if isinstance(compact.get("agent_registry"), list):
            compact["agent_registry"] = compact["agent_registry"][:8]
        if isinstance(compact.get("agent_trace"), list):
            compact["agent_trace"] = compact["agent_trace"][-8:]
        return compact

    def _evaluate_control_layer(
        self,
        *,
        session_id: str,
        message: str,
        task_id: str,
        run_id: str,
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        routing_decision = self.capability_router.classify_task(message, metadata)
        target_mode = routing_decision.preferred_mode
        current_mode = self.current_control_mode if task_id or run_id else RuntimeMode.EXPLORE
        if metadata.get("control_boundary") == "action_execution":
            current_mode = RuntimeMode.PLAN
            if routing_decision.task_type in {"simple_query", "repository_analysis", "code_mutation"}:
                target_mode = RuntimeMode.EXECUTE

        requested_action = str(metadata.get("requested_action") or self._requested_action_for_task_type(routing_decision.task_type))
        transition_allowed = can_transition(current_mode, target_mode)
        evidence_result = self.evidence_gate.evaluate_evidence(
            task_type=routing_decision.task_type,
            risk_level=routing_decision.risk_level,
            available_evidence=metadata.get("available_evidence"),
        )
        policy_result = self.policy_engine.evaluate_policies(
            mode=target_mode,
            requested_action=requested_action,
            task_type=routing_decision.task_type,
            risk_level=routing_decision.risk_level,
            metadata=metadata,
            evidence_result=evidence_result,
        )

        if not transition_allowed:
            transition_policy = PolicyResult(
                allowed=False,
                policy_name="ExecutionPolicy",
                reason="requested mode transition is not allowed from current control mode",
                severity="high",
                details={"from_mode": current_mode.value, "to_mode": target_mode.value},
            )
            policy_result = PolicyBundleResult(
                allowed=False,
                results=[transition_policy, *policy_result.results],
                blocking_results=[transition_policy, *policy_result.blocking_results],
            )

        allowed = transition_allowed and policy_result.allowed and (
            evidence_result.enough_evidence or not routing_decision.requires_evidence
        )
        mode_transition = None
        if allowed and target_mode != self.current_control_mode:
            mode_transition = build_mode_transition_event(
                session_id=session_id,
                from_mode=self.current_control_mode,
                to_mode=target_mode,
                reason_code="routing_selected_mode",
                details={
                    "task_type": routing_decision.task_type,
                    "capability_path": routing_decision.preferred_capability_path,
                },
            )

        blocked_event_type = "runtime.control.policy_block"
        blocked_reason_code = "policy_block"
        blocked_reason = "policy blocked the requested execution"
        if not evidence_result.enough_evidence and routing_decision.requires_evidence:
            blocked_event_type = "runtime.control.evidence_gate_block"
            blocked_reason_code = "insufficient_evidence"
            blocked_reason = evidence_result.recommendation.replace("_", " ")
        elif policy_result.blocking_results:
            blocked_reason = policy_result.blocking_results[0].reason

        return {
            "routing_decision": routing_decision,
            "target_mode": target_mode,
            "mode_transition": mode_transition,
            "evidence_result": evidence_result,
            "policy_result": policy_result,
            "allowed": allowed,
            "blocked_event_type": blocked_event_type,
            "blocked_reason_code": blocked_reason_code,
            "blocked_response": f"{CONTROL_LAYER_BLOCK_PREFIX}: {blocked_reason}.",
        }

    def _resolve_node_bin(self) -> str | None:
        selection = self.js_runtime_adapter.select_runtime()
        if selection.runtime_name == "node" and selection.node_available:
            return selection.executable
        configured = os.getenv("NODE_BIN", "").strip()
        if configured:
            return configured
        return shutil.which("node")

    def _build_node_subprocess_env(self) -> dict[str, str]:
        env, selection = self.js_runtime_adapter.build_env()
        env.setdefault("NODE_BIN", self._resolve_node_bin() or "node")
        env["OMINI_JS_RUNTIME_SELECTED"] = selection.runtime_name
        return env

    def _resolve_node_command_context(self, payload: str) -> dict[str, Any]:
        cwd_path = self.paths.root.resolve()
        runner_path = self.paths.js_runner.resolve()
        adapter_path = (self.paths.root / "src" / "queryEngineRunnerAdapter.js").resolve()
        esm_adapter_path = (self.paths.root / "src" / "queryEngineRunnerAdapter.mjs").resolve()
        fusion_brain_path = (self.paths.root / "core" / "brain" / "fusionBrain.js").resolve()
        healthcheck_path = (self.paths.root / "js-runner" / "runtimeHealthcheck.js").resolve()
        dist_query_engine_path = (self.paths.root / "dist" / "QueryEngine.js").resolve()
        build_query_engine_path = (self.paths.root / "build" / "QueryEngine.js").resolve()
        ts_candidates = [
            (self.paths.root / "src" / "QueryEngine.ts").resolve(),
            (self.paths.root / "runtime" / "node" / "QueryEngine.ts").resolve(),
        ]
        command, runtime_selection = self.js_runtime_adapter.build_command(script_path=runner_path, payload=payload)
        env = self._build_node_subprocess_env()
        node_bin = self._resolve_node_bin()
        node_resolved = shutil.which(node_bin) if node_bin and not os.path.isabs(node_bin) else node_bin
        missing_paths = []
        if not runner_path.exists():
            missing_paths.append(str(runner_path))
        if not adapter_path.exists():
            missing_paths.append(str(adapter_path))
        if not fusion_brain_path.exists():
            missing_paths.append(str(fusion_brain_path))

        return {
            "node_bin": node_bin,
            "node_resolved": node_resolved,
            "js_runtime": runtime_selection.as_dict(),
            "cwd": str(cwd_path),
            "cwd_exists": cwd_path.exists(),
            "runner_path": str(runner_path),
            "runner_exists": runner_path.exists(),
            "adapter_path": str(adapter_path),
            "adapter_exists": adapter_path.exists(),
            "esm_adapter_path": str(esm_adapter_path),
            "esm_adapter_exists": esm_adapter_path.exists(),
            "fusion_brain_path": str(fusion_brain_path),
            "fusion_brain_exists": fusion_brain_path.exists(),
            "healthcheck_path": str(healthcheck_path),
            "healthcheck_exists": healthcheck_path.exists(),
            "dist_query_engine_path": str(dist_query_engine_path),
            "dist_query_engine_exists": dist_query_engine_path.exists(),
            "build_query_engine_path": str(build_query_engine_path),
            "build_query_engine_exists": build_query_engine_path.exists(),
            "typescript_candidate_paths": [str(candidate) for candidate in ts_candidates],
            "typescript_candidates_exist": [str(candidate) for candidate in ts_candidates if candidate.exists()],
            "command": command,
            "command_preview": [command[0], command[1], f"<payload:{len(payload)} chars>"],
            "typescript_direct_execution_detected": str(runner_path).endswith(".ts"),
            "compiled_runner_artifact_exists": any(
                path_exists
                for path_exists in (
                    adapter_path.exists(),
                    esm_adapter_path.exists(),
                    dist_query_engine_path.exists(),
                    build_query_engine_path.exists(),
                )
            ),
            "missing_paths": missing_paths,
            "env_preview": {
                "BASE_DIR": env.get("BASE_DIR", ""),
                "NODE_RUNNER_BASE_DIR": env.get("NODE_RUNNER_BASE_DIR", ""),
                "NODE_BIN": env.get("NODE_BIN", ""),
                "OMINI_JS_RUNTIME": env.get("OMINI_JS_RUNTIME", ""),
                "OMINI_JS_RUNTIME_BIN": env.get("OMINI_JS_RUNTIME_BIN", ""),
                "PYTHON_BIN": env.get("PYTHON_BIN", ""),
                "PATH_HEAD": env.get("PATH", "")[:400],
            },
            "subprocess_env": env,
        }

    @staticmethod
    def _truncate_text(value: str, limit: int = 1200) -> str:
        normalized = value.strip()
        if len(normalized) <= limit:
            return normalized
        return normalized[:limit]

    def _classify_node_subprocess_failure(
        self,
        *,
        diagnostics: dict[str, Any],
        returncode: int | None = None,
        stdout: str = "",
        stderr: str = "",
        exception: Exception | None = None,
        timed_out: bool = False,
    ) -> tuple[str, dict[str, Any]]:
        details = {
            "runner_path": diagnostics["runner_path"],
            "adapter_path": diagnostics["adapter_path"],
            "fusion_brain_path": diagnostics["fusion_brain_path"],
            "cwd": diagnostics["cwd"],
            "command_preview": diagnostics["command_preview"],
            "node_bin": diagnostics["node_bin"],
            "node_resolved": diagnostics["node_resolved"],
            "returncode": returncode,
            "stdout": self._truncate_text(stdout),
            "stderr": self._truncate_text(stderr),
            "timed_out": timed_out,
            "exception": repr(exception) if exception else "",
            "typescript_direct_execution_detected": diagnostics["typescript_direct_execution_detected"],
            "typescript_candidates_exist": diagnostics["typescript_candidates_exist"],
            "compiled_runner_artifact_exists": diagnostics["compiled_runner_artifact_exists"],
            "missing_paths": diagnostics["missing_paths"],
            "env_preview": diagnostics["env_preview"],
        }
        combined = f"{stdout}\n{stderr}".lower()

        if not diagnostics["node_resolved"]:
            return "node_not_found", details
        if not diagnostics["runner_exists"]:
            return "runner_not_found", details
        if not diagnostics["cwd_exists"]:
            return "cwd_not_found", details
        if diagnostics["missing_paths"]:
            return "module_resolution_error", details
        if timed_out:
            return "timeout", details
        if exception is not None:
            return "subprocess_exception", details
        if not stdout.strip() and not stderr.strip() and returncode == 0:
            return "empty_stdout", details
        if "err_module_not_found" in combined or "cannot find module" in combined or "module not found" in combined:
            return "module_resolution_error", details
        if "unknown file extension \".ts\"" in combined or "cannot use import statement outside a module" in combined:
            details["typescript_direct_execution_detected"] = True
            return "module_resolution_error", details
        if returncode not in (None, 0):
            return "node_subprocess_failed", details
        return "invalid_json", details

    @staticmethod
    def _runtime_max_parallel_reads() -> int:
        return max(1, int(os.getenv("OMINI_MAX_PARALLEL_READ_STEPS", "2") or "2"))

    @staticmethod
    def _runtime_stale_checkpoint_minutes() -> int:
        return max(1, int(os.getenv("OMINI_STALE_CHECKPOINT_MINUTES", "120") or "120"))

    @staticmethod
    def _runtime_critic_enabled() -> bool:
        return str(os.getenv("OMINI_ENABLE_CRITIC", "true")).strip().lower() != "false"

    @staticmethod
    def _runtime_correction_depth() -> int:
        return max(1, int(os.getenv("OMINI_MAX_CORRECTION_DEPTH", "1") or "1"))

    @staticmethod
    def _plan_signature(actions: list[dict[str, Any]], plan_graph: dict[str, Any] | None = None) -> str:
        payload = json.dumps(
            {
                "actions": actions,
                "plan_graph": plan_graph or {},
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _call_node_query_engine(
        self,
        *,
        message: str,
        memory_store: dict[str, object],
        available_capabilities: list[dict[str, str]],
        session_id: str,
        extra_session: dict[str, Any] | None = None,
    ) -> str:
        if self._selected_runtime_mode() == "fallback":
            self.last_runtime_mode = "fallback"
            self.last_runtime_reason = "configured_fallback_mode"
            self._record_runtime_mode_event(
                session_id=session_id,
                mode="fallback",
                reason_code="configured_fallback_mode",
                details={"message_preview": message[:120]},
            )
            return NODE_FALLBACK_RESPONSE

        diagnostics = self._resolve_node_command_context(payload="")
        if not diagnostics["node_resolved"] or not diagnostics["runner_exists"] or not diagnostics["cwd_exists"]:
            classified_reason, details = self._classify_node_subprocess_failure(
                diagnostics=diagnostics,
            )
            self.last_runtime_mode = "fallback"
            self.last_runtime_reason = classified_reason
            self._record_runtime_mode_event(
                session_id=session_id,
                mode="fallback",
                reason_code=classified_reason,
                details=details,
            )
            return NODE_FALLBACK_RESPONSE

        session_payload = self.session_store.load(session_id)
        session_payload["executor_bridge"] = "python-rust"
        session_payload["runtime_mode"] = self.last_runtime_mode
        session_payload["runtime_reason"] = self.last_runtime_reason
        if extra_session:
            session_payload.update(extra_session)
        context_budget = extra_session.get("context_budget", {}) if isinstance(extra_session, dict) else {}
        budget_level = str(context_budget.get("budget_level", "medium"))
        compact_history = self._compact_history_for_node(
            memory_store.get("history", []),
            limit=self._history_limit_for_budget(budget_level),
        )
        compact_session_payload = self._compact_session_payload_for_node(
            session_payload,
            history_limit=self._history_limit_for_budget(budget_level),
            summary_limit=self._summary_limit_for_budget(budget_level),
        )

        payload = json.dumps(
            {
                "message": message,
                "memory": memory_store.get("user", {}),
                "history": compact_history,
                "summary": self.summarize_history(compact_history),
                "capabilities": available_capabilities,
                "session": compact_session_payload,
            },
            ensure_ascii=False,
        )
        diagnostics = self._resolve_node_command_context(payload=payload)
        self._append_runtime_event(
            event_type="runtime.node.subprocess_diagnostics",
            session_id=session_id,
            task_id="",
            run_id="",
            payload={
                "stage": "preflight",
                **{
                    key: value
                    for key, value in diagnostics.items()
                    if key not in {"command", "subprocess_env"}
                },
            },
        )

        if diagnostics["missing_paths"]:
            classified_reason, details = self._classify_node_subprocess_failure(
                diagnostics=diagnostics,
            )
            self.last_runtime_mode = "fallback"
            self.last_runtime_reason = classified_reason
            self._record_runtime_mode_event(
                session_id=session_id,
                mode="fallback",
                reason_code=classified_reason,
                details=details,
            )
            return NODE_FALLBACK_RESPONSE

        try:
            completed = subprocess.run(
                diagnostics["command"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=SUBPROCESS_TIMEOUT_SECONDS,
                check=False,
                cwd=diagnostics["cwd"],
                env=diagnostics["subprocess_env"],
            )
        except subprocess.TimeoutExpired as error:
            self.last_runtime_mode = "fallback"
            classified_reason, details = self._classify_node_subprocess_failure(
                diagnostics=diagnostics,
                stdout=error.stdout or "",
                stderr=error.stderr or "",
                exception=error,
                timed_out=True,
            )
            self.last_runtime_reason = classified_reason
            self._append_runtime_event(
                event_type="runtime.node.subprocess_diagnostics",
                session_id=session_id,
                task_id="",
                run_id="",
                payload={"stage": "timeout", "reason_code": classified_reason, **details},
            )
            self._record_runtime_mode_event(
                session_id=session_id,
                mode="fallback",
                reason_code=classified_reason,
                details=details,
            )
            return NODE_FALLBACK_RESPONSE
        except Exception as error:
            self.last_runtime_mode = "fallback"
            classified_reason, details = self._classify_node_subprocess_failure(
                diagnostics=diagnostics,
                exception=error,
            )
            self.last_runtime_reason = classified_reason
            self._append_runtime_event(
                event_type="runtime.node.subprocess_diagnostics",
                session_id=session_id,
                task_id="",
                run_id="",
                payload={"stage": "exception", "reason_code": classified_reason, **details},
            )
            self._record_runtime_mode_event(
                session_id=session_id,
                mode="fallback",
                reason_code=classified_reason,
                details=details,
            )
            return NODE_FALLBACK_RESPONSE

        if completed.returncode != 0:
            classified_reason, details = self._classify_node_subprocess_failure(
                diagnostics=diagnostics,
                returncode=completed.returncode,
                stdout=completed.stdout or "",
                stderr=completed.stderr or "",
            )
            self.last_runtime_mode = "fallback"
            self.last_runtime_reason = classified_reason
            self._append_runtime_event(
                event_type="runtime.node.subprocess_diagnostics",
                session_id=session_id,
                task_id="",
                run_id="",
                payload={"stage": "completed", "reason_code": classified_reason, **details},
            )
            self._record_runtime_mode_event(
                session_id=session_id,
                mode="fallback",
                reason_code=classified_reason,
                details=details,
            )
            return NODE_FALLBACK_RESPONSE
        stdout = (completed.stdout or "").strip()
        if not stdout:
            classified_reason, details = self._classify_node_subprocess_failure(
                diagnostics=diagnostics,
                returncode=completed.returncode,
                stdout=completed.stdout or "",
                stderr=completed.stderr or "",
            )
            self.last_runtime_mode = "fallback"
            self.last_runtime_reason = classified_reason
            self._append_runtime_event(
                event_type="runtime.node.subprocess_diagnostics",
                session_id=session_id,
                task_id="",
                run_id="",
                payload={"stage": "completed", "reason_code": classified_reason, **details},
            )
            self._record_runtime_mode_event(
                session_id=session_id,
                mode="fallback",
                reason_code=classified_reason,
                details=details,
            )
            return NODE_FALLBACK_RESPONSE

        try:
            parsed = json.loads(stdout)
        except json.JSONDecodeError as error:
            classified_reason, details = self._classify_node_subprocess_failure(
                diagnostics=diagnostics,
                returncode=completed.returncode,
                stdout=completed.stdout or "",
                stderr=completed.stderr or "",
                exception=error,
            )
            self.last_runtime_mode = "fallback"
            self.last_runtime_reason = classified_reason
            self._append_runtime_event(
                event_type="runtime.node.subprocess_diagnostics",
                session_id=session_id,
                task_id="",
                run_id="",
                payload={"stage": "completed", "reason_code": classified_reason, **details},
            )
            self._record_runtime_mode_event(
                session_id=session_id,
                mode="fallback",
                reason_code=classified_reason,
                details=details,
                )
            return NODE_FALLBACK_RESPONSE

        self._append_runtime_event(
            event_type="runtime.node.subprocess_diagnostics",
            session_id=session_id,
            task_id="",
            run_id="",
            payload={
                "stage": "completed",
                "reason_code": "success",
                "returncode": completed.returncode,
                "stdout": self._truncate_text(completed.stdout or ""),
                "stderr": self._truncate_text(completed.stderr or ""),
                "command_preview": diagnostics["command_preview"],
                "cwd": diagnostics["cwd"],
                "node_bin": diagnostics["node_bin"],
                "node_resolved": diagnostics["node_resolved"],
                "env_preview": diagnostics["env_preview"],
            },
        )

        self._record_runtime_selection_event(parsed, runner="queryEngineRunner.js")
        self._record_engine_selection_event(parsed, session_id=session_id)
        execution_request = parsed.get("execution_request")
        if not isinstance(execution_request, dict):
            response = parsed.get("response")
            normalized = str(response).strip() if isinstance(response, str) else stdout
            if normalized:
                self.last_runtime_mode = "live"
                self.last_runtime_reason = "direct_node_response"
                return normalized
            self.last_runtime_mode = "fallback"
            self.last_runtime_reason = "invalid_node_payload"
            self._record_runtime_mode_event(
                session_id=session_id,
                mode="fallback",
                reason_code="invalid_node_payload",
                details={},
            )
            return NODE_FALLBACK_RESPONSE

        actions = execution_request.get("actions", [])
        if not isinstance(actions, list) or not actions:
            response = parsed.get("response", "")
            normalized = str(response).strip() if isinstance(response, str) else ""
            if normalized:
                self.last_runtime_mode = "live"
                self.last_runtime_reason = "node_response_without_actions"
                return normalized
            self.last_runtime_mode = "fallback"
            self.last_runtime_reason = "invalid_execution_request"
            self._record_runtime_mode_event(
                session_id=session_id,
                mode="fallback",
                reason_code="invalid_execution_request",
                details={},
            )
            return NODE_FALLBACK_RESPONSE

        self.last_runtime_mode = "live"
        self.last_runtime_reason = "node_execution_request"

        task_id = str(execution_request.get("task_id", f"task-{session_id}"))
        run_id = coerce_runtime_run_id(
            run_id=str(execution_request.get("run_id", "")),
            session_id=session_id,
        )
        memory_hints = execution_request.get("memory_hints", {})
        step_results = self._execute_runtime_actions(
            session_id=session_id,
            message=message,
            actions=actions,
            task_id=task_id,
            run_id=run_id,
            provider=execution_request.get("provider", {}),
            intent=str(execution_request.get("intent", "")),
            delegation=execution_request.get("delegation", {}),
            critic_review=execution_request.get("critic_review", {}),
            plan_kind=str(execution_request.get("plan_kind", "linear")),
            plan_graph=execution_request.get("plan_graph"),
            semantic_retrieval=execution_request.get("semantic_retrieval", []),
            plan_hierarchy=execution_request.get("plan_hierarchy"),
            learning_guidance=execution_request.get("learning_guidance", []),
            policy_summary=execution_request.get("policy_summary", []),
            branch_plan=execution_request.get("branch_plan"),
            simulation_summary=execution_request.get("simulation_summary"),
            cooperative_plan=execution_request.get("cooperative_plan"),
            strategy_suggestions=execution_request.get("strategy_suggestions", []),
            execution_tree=execution_request.get("execution_tree"),
            negotiation_summary=execution_request.get("negotiation_summary"),
            strategy_optimization=execution_request.get("strategy_optimization"),
            repository_analysis=execution_request.get("repository_analysis"),
            repo_impact_analysis=execution_request.get("repo_impact_analysis"),
            verification_plan=execution_request.get("verification_plan"),
            verification_selection=execution_request.get("verification_selection"),
            milestone_plan=execution_request.get("milestone_plan"),
            engineering_review=execution_request.get("engineering_review"),
            engineering_workflow=execution_request.get("engineering_workflow"),
            operator_control_enabled=True,
        )
        if isinstance(execution_request.get("semantic_retrieval", []), list) and execution_request.get("semantic_retrieval", []):
            self._append_runtime_event(
                event_type="runtime.vector.retrieval",
                session_id=session_id,
                task_id=task_id,
                run_id=run_id,
                payload={
                    "match_count": len(execution_request.get("semantic_retrieval", [])),
                    "top_match": execution_request.get("semantic_retrieval", [])[0].get("path"),
                },
            )

        self._apply_memory_hints(memory_store, memory_hints)
        self._apply_result_memory_updates(memory_store, step_results)
        self._sync_runtime_memory_store(session_id, memory_store, step_results)

        return self._synthesize_runtime_response(step_results, str(parsed.get("response", "")).strip())

    def _record_runtime_mode_event(
        self,
        *,
        session_id: str,
        mode: str,
        reason_code: str,
        details: dict[str, Any],
    ) -> None:
        self._append_jsonl(
            self.paths.root / ".logs" / "fusion-runtime" / "execution-audit.jsonl",
            {
                "timestamp": self._utc_now(),
                "event_type": "runtime.mode.transition",
                "session_id": session_id,
                "task_id": "",
                "run_id": "",
                "runtime_mode": mode,
                "reason_code": reason_code,
                "details": details,
            },
        )

    def _record_engine_selection_event(
        self,
        result_payload: dict[str, Any] | None,
        *,
        session_id: str = "",
    ) -> None:
        payload = result_payload if isinstance(result_payload, dict) else {}
        metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
        engine_mode = str(metadata.get("engine_mode", "")).strip()
        if not engine_mode:
            return
        engine_reason = str(metadata.get("engine_reason", "")).strip()
        try:
            if self.engine_adoption_store is not None:
                self.engine_adoption_store.record_selection(
                    engine_mode=engine_mode,
                    engine_reason=engine_reason,
                    session_id=session_id,
                )
        except Exception:
            pass
        self.memory_facade.record_event(
            event_type="engine_selection",
            description=f"QueryEngine responded via {engine_mode}",
            metadata={
                "engine_mode": engine_mode,
                "engine_reason": engine_reason,
            },
        )
        promoted_scenario = str(metadata.get("promoted_scenario", "")).strip()
        promotion_phase = str(metadata.get("promotion_phase", "")).strip()
        promotion_rollback_reason = str(metadata.get("promotion_rollback_reason", "")).strip()
        if promoted_scenario and engine_mode == "packaged_upstream":
            self.memory_facade.record_event(
                event_type="engine_promotion",
                description="Request type promoted to packaged_upstream",
                metadata={
                    "promoted_scenario": promoted_scenario,
                    "previous_route": "authority_fallback",
                    "new_route": "packaged_upstream",
                    "phase": promotion_phase or "27",
                },
            )
        if promoted_scenario and promotion_rollback_reason:
            self.memory_facade.record_event(
                event_type="engine_promotion_rollback",
                description="Packaged engine promotion rolled back due to import failures",
                metadata={
                    "promoted_scenario": promoted_scenario,
                    "reason": promotion_rollback_reason,
                    "phase": promotion_phase or "27",
                },
            )

    def _record_runtime_selection_event(self, result_payload: dict[str, Any] | None, *, runner: str) -> None:
        payload = result_payload if isinstance(result_payload, dict) else {}
        metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
        runtime_mode = str(metadata.get("runtime_mode", "")).strip()
        if not runtime_mode:
            return
        runtime_reason = str(metadata.get("runtime_reason", "")).strip()
        self.memory_facade.record_event(
            event_type="runtime_selection",
            description=f"JS runner responded via {runtime_mode}",
            metadata={
                "runtime_mode": runtime_mode,
                "runtime_reason": runtime_reason,
                "runner": runner,
            },
        )

    def _register_run_record(
        self,
        *,
        run_id: str,
        session_id: str,
        goal_id: str | None,
        status: RunStatus,
        last_action: str,
        progress_score: float,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        if not str(run_id or "").strip():
            return
        rid = validate_run_id_for_new_write(run_id)
        self._run_lifecycle.register_run_start(
            run_id=rid,
            session_id=session_id,
            goal_id=goal_id,
            status=status,
            last_action=last_action,
            progress_score=progress_score,
            metadata=metadata,
        )

    def _update_run_status(
        self,
        *,
        run_id: str,
        status: RunStatus,
        last_action: str,
        progress_score: float,
    ) -> None:
        if not str(run_id or "").strip():
            return
        rid = validate_run_id_for_new_write(run_id)
        self._run_lifecycle.update_run_status(
            run_id=rid,
            status=status,
            last_action=last_action,
            progress_score=progress_score,
        )

    @staticmethod
    def _progress_from_step_results(step_results: list[dict[str, Any]]) -> float:
        if not step_results:
            return 0.0
        successes = len([item for item in step_results if isinstance(item, dict) and item.get("ok")])
        return max(0.0, min(1.0, successes / max(1, len(step_results))))

    @staticmethod
    def _coordination_trace_has_governance_hold(trace: dict[str, Any] | None) -> bool:
        if not isinstance(trace, dict):
            return False
        decisions = trace.get("decisions", [])
        if not isinstance(decisions, list):
            return False
        for decision in decisions:
            if not isinstance(decision, dict):
                continue
            if str(decision.get("specialist_type", "")).strip() != "governance":
                continue
            if str(decision.get("verdict", "")).strip() == "hold":
                return True
        return False

    def _await_run_control_clearance(self, *, run_id: str) -> dict[str, Any]:
        """Delegate to governance integration (bounded poll; Phase 30.15)."""
        return self._governance_integration.await_run_control_clearance(run_id=run_id)

    def _control_block_result(
        self,
        *,
        reason_code: str,
        message: str,
        selected_agent: str = "operator_control",
    ) -> dict[str, Any]:
        return {
            "ok": False,
            "selected_tool": "none",
            "selected_agent": selected_agent,
            "error_payload": {
                "kind": reason_code,
                "message": message,
            },
            "evaluation": {
                "decision": "stop_blocked",
                "reason_code": reason_code,
            },
        }

    def _execute_runtime_actions(
        self,
        *,
        session_id: str,
        message: str,
        actions: list[dict[str, Any]],
        task_id: str,
        run_id: str,
        provider: dict[str, Any] | str,
        intent: str,
        delegation: dict[str, Any],
        critic_review: dict[str, Any] | None = None,
        plan_kind: str = "linear",
        plan_graph: dict[str, Any] | None = None,
        semantic_retrieval: object = None,
        plan_hierarchy: dict[str, Any] | None = None,
        learning_guidance: object = None,
        policy_summary: object = None,
        branch_plan: dict[str, Any] | None = None,
        simulation_summary: dict[str, Any] | None = None,
        cooperative_plan: dict[str, Any] | None = None,
        strategy_suggestions: object = None,
        execution_tree: dict[str, Any] | None = None,
        negotiation_summary: dict[str, Any] | None = None,
        strategy_optimization: dict[str, Any] | None = None,
        repository_analysis: dict[str, Any] | None = None,
        repo_impact_analysis: dict[str, Any] | None = None,
        verification_plan: dict[str, Any] | None = None,
        verification_selection: dict[str, Any] | None = None,
        milestone_plan: dict[str, Any] | None = None,
        engineering_review: dict[str, Any] | None = None,
        engineering_workflow: dict[str, Any] | None = None,
        start_index: int = 0,
        operator_control_enabled: bool = False,
    ) -> list[dict[str, Any]]:
        max_steps = min(len(actions), int(os.getenv("OMINI_MAX_STEPS", "6") or "6"))
        step_results: list[dict[str, Any]] = []
        critic_review = critic_review or {}
        graph_state = self._clone_plan_graph(plan_graph)
        tree_state = self._clone_tree(execution_tree)
        plan_signature = self._plan_signature(actions, graph_state)
        branch_state = self._initial_branch_state(branch_plan)
        engineering_data: dict[str, Any] = {
            "repository_analysis": repository_analysis or {},
            "repo_impact_analysis": repo_impact_analysis or {},
            "impact_map": (repo_impact_analysis or {}).get("impact_map", {}),
            "verification_plan": verification_plan or {},
            "verification_selection": verification_selection or {},
            "milestone_plan": milestone_plan or {},
            "milestone_state": MilestoneManager(milestone_plan).initialize_state() if isinstance(milestone_plan, dict) else {},
            "engineering_review": engineering_review or {},
            "engineering_workflow": engineering_workflow or {},
            "workspace_state": {},
            "patch_history": [],
            "patch_sets": [],
            "debug_iterations": [],
            "test_results": {},
            "verification_summary": {},
            "pr_summary": {},
        }
        self._register_run_record(
            run_id=run_id,
            session_id=session_id,
            goal_id=None,
            status=RunStatus.RUNNING,
            last_action="execution_started",
            progress_score=0.0,
            metadata={
                "task_id": task_id,
                "intent": intent,
                "plan_kind": plan_kind,
                "operator_control_enabled": operator_control_enabled,
            },
        )
        planning_decision, operational_plan = self.planning_executor.ensure_plan(
            session_id=session_id,
            task_id=task_id,
            run_id=run_id,
            message=message,
            actions=actions,
            plan_kind=plan_kind,
            branch_plan=branch_plan,
            start_index=start_index,
            engineering_workflow=engineering_workflow,
            advisory_signals=[signal.as_dict() for signal in self.learning_executor.advisory_signals_for_planning(actions=actions)],
        )
        action_lookup = {
            str(action.get("step_id", "")).strip(): action
            for action in actions
            if isinstance(action, dict) and str(action.get("step_id", "")).strip()
        }
        self._append_runtime_event(
            event_type="runtime.planning.classification",
            session_id=session_id,
            task_id=task_id,
            run_id=run_id,
            payload={
                "classification": planning_decision.as_dict(),
                "plan_id": operational_plan.plan_id if operational_plan else None,
            },
        )
        goal_context = self.planning_executor.goal_context_for_plan(operational_plan)
        self._register_run_record(
            run_id=run_id,
            session_id=session_id,
            goal_id=getattr(operational_plan, "goal_id", None),
            status=RunStatus.RUNNING,
            last_action="plan_initialized",
            progress_score=0.0,
            metadata={
                "task_id": task_id,
                "intent": intent,
                "plan_id": getattr(operational_plan, "plan_id", ""),
                "plan_kind": plan_kind,
            },
        )
        if operational_plan is not None and operational_plan.goal_id:
            self.memory_facade.set_active_goal(
                session_id=session_id,
                goal_id=operational_plan.goal_id,
                active_plan_id=operational_plan.plan_id,
                goal_context=goal_context,
            )
            self.memory_facade.record_event(
                event_type="plan_initialized",
                description=planning_decision.summary,
                outcome=operational_plan.status.value,
                progress_score=0.0,
                metadata={
                    "plan_id": operational_plan.plan_id,
                    "task_id": operational_plan.task_id,
                    "goal_id": operational_plan.goal_id,
                    "classification": planning_decision.classification.value,
                },
            )
        control_metadata = self._build_control_metadata(
            message=message,
            actions=actions,
            metadata={
                "control_boundary": "action_execution",
                "requested_action": "test"
                if any(str(action.get("selected_tool", "")) in VERIFICATION_TOOLS for action in actions)
                else "mutate"
                if any(str(action.get("selected_tool", "")) in MUTATING_TOOLS for action in actions)
                else "execute",
            },
            repository_analysis=repository_analysis,
            repo_impact_analysis=repo_impact_analysis,
            verification_plan=verification_plan,
            engineering_data=engineering_data,
            policy_summary=policy_summary,
        )
        control_result = self._evaluate_control_layer(
            session_id=session_id,
            message=message,
            task_id=task_id,
            run_id=run_id,
            metadata=control_metadata,
        )
        context_budget, retrieval_plan = self._build_context_budget(
            routing_decision=control_result["routing_decision"]
        )
        self._update_structured_memory(
            session_id=session_id,
            task_id=task_id,
            run_id=run_id,
            message=message,
            control_metadata=control_metadata,
            control_result=control_result,
            budget=context_budget,
            retrieval_plan=retrieval_plan,
        )
        self._emit_control_event(
            "runtime.control.routing_decision",
            session_id=session_id,
            task_id=task_id,
            run_id=run_id,
            payload={
                "control_mode": self.current_control_mode.value,
                "task_type": control_result["routing_decision"].task_type,
                "capability_path": control_result["routing_decision"].preferred_capability_path,
                "risk_level": control_result["routing_decision"].risk_level,
                "execution_strategy": control_result["routing_decision"].execution_strategy,
                "verification_intensity": control_result["routing_decision"].verification_intensity,
                "recommended_specialists": control_result["routing_decision"].recommended_specialists,
                "delegation_recommended": control_result["routing_decision"].specialist_delegation_recommended,
                "routing_reason": control_result["routing_decision"].reasoning,
                "allowed": control_result["allowed"],
            },
        )
        if not control_result["allowed"]:
            self._record_control_outcome_memory(
                session_id=session_id,
                task_id=task_id,
                run_id=run_id,
                control_result=control_result,
                allowed=False,
            )
            self._emit_control_event(
                str(control_result["blocked_event_type"]),
                session_id=session_id,
                task_id=task_id,
                run_id=run_id,
                payload={
                    "control_mode": self.current_control_mode.value,
                    "task_type": control_result["routing_decision"].task_type,
                    "capability_path": control_result["routing_decision"].preferred_capability_path,
                    "risk_level": control_result["routing_decision"].risk_level,
                    "execution_strategy": control_result["routing_decision"].execution_strategy,
                    "verification_intensity": control_result["routing_decision"].verification_intensity,
                    "recommended_specialists": control_result["routing_decision"].recommended_specialists,
                    "delegation_recommended": control_result["routing_decision"].specialist_delegation_recommended,
                    "routing_reason": control_result["routing_decision"].reasoning,
                    "policy_results": [self._policy_result_to_dict(item) for item in control_result["policy_result"].results],
                    "missing_evidence_types": control_result["evidence_result"].missing_evidence_types,
                    "reason_code": control_result["blocked_reason_code"],
                    "allowed": False,
                },
            )
            blocked = {
                "ok": False,
                "selected_tool": "none",
                "selected_agent": "master_orchestrator",
                "error_payload": {
                    "kind": "control_layer_block",
                    "message": str(control_result["blocked_response"]),
                    "reason_code": str(control_result["blocked_reason_code"]),
                    "policy_results": [self._policy_result_to_dict(item) for item in control_result["policy_result"].results],
                    "missing_evidence_types": control_result["evidence_result"].missing_evidence_types,
                },
                "evaluation": {
                    "decision": "stop_blocked",
                    "reason_code": str(control_result["blocked_reason_code"]),
                    "control_layer": {
                        "routing": control_result["routing_decision"].as_dict(),
                        "evidence": self._evidence_to_dict(control_result["evidence_result"]),
                        "policy": self._bundle_to_dict(control_result["policy_result"]),
                    },
                },
            }
            step_results.append(blocked)
            self._write_checkpoint(
                run_id=run_id,
                task_id=task_id,
                session_id=session_id,
                message=message,
                actions=actions,
                next_step_index=start_index,
                completed_steps=step_results,
                plan_graph=graph_state,
                plan_hierarchy=plan_hierarchy,
                plan_signature=plan_signature,
                status="blocked",
                branch_state=branch_state,
                simulation_summary=simulation_summary,
                cooperative_plan=cooperative_plan,
                strategy_suggestions=strategy_suggestions,
                policy_summary=policy_summary,
                execution_tree=tree_state,
                negotiation_summary=negotiation_summary,
                strategy_optimization=strategy_optimization,
                supervision={"control_layer": blocked["evaluation"]["control_layer"]},
                repository_analysis=repository_analysis,
                engineering_data=engineering_data,
            )
            operational_plan = self.planning_executor.finalize_plan(
                operational_plan,
                status_hint="blocked",
                step_results=step_results,
            )
            self._update_run_status(
                run_id=run_id,
                status=RunStatus.FAILED,
                last_action="control_layer_blocked",
                progress_score=self._progress_from_step_results(step_results),
            )
            return step_results
        if control_result["mode_transition"] is not None:
            self._emit_control_event(
                "runtime.control.mode_transition",
                session_id=session_id,
                task_id=task_id,
                run_id=run_id,
                payload=control_result["mode_transition"],
            )
            self.current_control_mode = control_result["target_mode"]
        self._record_control_outcome_memory(
            session_id=session_id,
            task_id=task_id,
            run_id=run_id,
            control_result=control_result,
            allowed=True,
        )
        self._emit_control_event(
            "runtime.control.execution_allowed",
            session_id=session_id,
            task_id=task_id,
            run_id=run_id,
            payload={
                "control_mode": self.current_control_mode.value,
                "task_type": control_result["routing_decision"].task_type,
                "capability_path": control_result["routing_decision"].preferred_capability_path,
                "risk_level": control_result["routing_decision"].risk_level,
                "execution_strategy": control_result["routing_decision"].execution_strategy,
                "verification_intensity": control_result["routing_decision"].verification_intensity,
                "recommended_specialists": control_result["routing_decision"].recommended_specialists,
                "delegation_recommended": control_result["routing_decision"].specialist_delegation_recommended,
                "routing_reason": control_result["routing_decision"].reasoning,
                "policy_results": [self._policy_result_to_dict(item) for item in control_result["policy_result"].results],
                "missing_evidence_types": control_result["evidence_result"].missing_evidence_types,
                "reason_code": "execution_allowed",
                "allowed": True,
            },
        )
        supervision = self.supervisor.inspect(
            execution_tree=tree_state,
            branch_plan=branch_plan,
            negotiation_summary=negotiation_summary,
            executed_steps=0,
            max_steps=max_steps,
        )
        if critic_review.get("invoked"):
            self._append_runtime_event(
                event_type="runtime.critic.plan",
                session_id=session_id,
                task_id=task_id,
                run_id=run_id,
                payload={
                    "critic_review": critic_review,
                    "plan_kind": plan_kind,
                },
            )
        if plan_kind == "graph" and isinstance(graph_state, dict):
            self._append_runtime_event(
                event_type="runtime.graph.plan",
                session_id=session_id,
                task_id=task_id,
                run_id=run_id,
                payload={
                    "plan_kind": plan_kind,
                    "node_count": len(graph_state.get("nodes", [])),
                },
            )
        if plan_kind == "hierarchical" and isinstance(plan_hierarchy, dict):
            self._append_runtime_event(
                event_type="runtime.goal.plan",
                session_id=session_id,
                task_id=task_id,
                run_id=run_id,
                payload={
                    "root_goal_id": plan_hierarchy.get("root_goal_id"),
                    "subgoal_count": len(plan_hierarchy.get("subgoals", []))
                    if isinstance(plan_hierarchy.get("subgoals", []), list)
                    else 0,
                },
            )
        if isinstance(cooperative_plan, dict):
            self._append_runtime_event(
                event_type="runtime.cooperation.plan",
                session_id=session_id,
                task_id=task_id,
                run_id=run_id,
                payload={
                    "shared_goal_id": cooperative_plan.get("shared_goal_id"),
                    "contribution_count": len(cooperative_plan.get("contributions", [])),
                },
            )
        if isinstance(negotiation_summary, dict):
            self._append_runtime_event(
                event_type="runtime.negotiation.summary",
                session_id=session_id,
                task_id=task_id,
                run_id=run_id,
                payload={
                    "final_decision": negotiation_summary.get("final_decision"),
                    "disagreement_count": negotiation_summary.get("disagreement_count", 0),
                },
            )
        if isinstance(strategy_optimization, dict):
            self._append_runtime_event(
                event_type="runtime.strategy.optimization",
                session_id=session_id,
                task_id=task_id,
                run_id=run_id,
                payload=strategy_optimization,
            )
        if supervision.get("alerts"):
            self._append_runtime_event(
                event_type="runtime.supervision.alert",
                session_id=session_id,
                task_id=task_id,
                run_id=run_id,
                payload=supervision,
            )
        if supervision.get("stop_execution"):
            blocked = {
                "ok": False,
                "selected_tool": "none",
                "selected_agent": "master_orchestrator",
                "error_payload": {
                    "kind": "supervision_stop",
                    "message": "Execution blocked by cognitive supervision.",
                },
                "evaluation": {"decision": "stop_blocked", "reason_code": "supervision_stop"},
            }
            step_results.append(blocked)
            self._write_checkpoint(
                run_id=run_id,
                task_id=task_id,
                session_id=session_id,
                message=message,
                actions=actions,
                next_step_index=start_index,
                completed_steps=step_results,
                plan_graph=graph_state,
                plan_hierarchy=plan_hierarchy,
                plan_signature=plan_signature,
                status="blocked",
                branch_state=branch_state,
                simulation_summary=simulation_summary,
                cooperative_plan=cooperative_plan,
                strategy_suggestions=strategy_suggestions,
                policy_summary=policy_summary,
                execution_tree=tree_state,
                negotiation_summary=negotiation_summary,
                strategy_optimization=strategy_optimization,
                supervision=supervision,
                repository_analysis=repository_analysis,
                engineering_data=engineering_data,
            )
            self._update_run_status(
                run_id=run_id,
                status=RunStatus.FAILED,
                last_action="supervision_stop",
                progress_score=self._progress_from_step_results(step_results),
            )
            return step_results
        if isinstance(simulation_summary, dict) and simulation_summary.get("invoked"):
            self._append_runtime_event(
                event_type="runtime.simulation.review",
                session_id=session_id,
                task_id=task_id,
                run_id=run_id,
                payload=simulation_summary,
            )
            if simulation_summary.get("recommended_decision") == "stop":
                blocked = {
                    "ok": False,
                    "selected_tool": "none",
                    "selected_agent": "critic_agent",
                    "error_payload": {
                        "kind": "simulation_stop",
                        "message": str(simulation_summary.get("summary", "Execution blocked by simulation review.")),
                    },
                    "evaluation": {
                        "decision": "stop_blocked",
                        "reason_code": "simulation_stop",
                    },
                }
                step_results.append(blocked)
                self._write_checkpoint(
                    run_id=run_id,
                    task_id=task_id,
                    session_id=session_id,
                    message=message,
                    actions=actions,
                    next_step_index=start_index,
                    completed_steps=step_results,
                    plan_graph=graph_state,
                    plan_hierarchy=plan_hierarchy,
                    plan_signature=plan_signature,
                    status="blocked",
                    branch_state=branch_state,
                    simulation_summary=simulation_summary,
                    cooperative_plan=cooperative_plan,
                    strategy_suggestions=strategy_suggestions,
                    policy_summary=policy_summary,
                    execution_tree=tree_state,
                    negotiation_summary=negotiation_summary,
                    strategy_optimization=strategy_optimization,
                    supervision=supervision,
                    repository_analysis=repository_analysis,
                    engineering_data=engineering_data,
                )
                self._write_run_summary(
                    session_id=session_id,
                    task_id=task_id,
                    run_id=run_id,
                    message=message,
                    step_results=step_results,
                    plan_kind=plan_kind,
                    plan_hierarchy=plan_hierarchy,
                    reflection={"invoked": False, "reason_code": "simulation_stop"},
                    branch_state=branch_state,
                    cooperative_plan=cooperative_plan,
                    simulation_summary=simulation_summary,
                    strategy_suggestions=strategy_suggestions,
                    fusion_summary=None,
                    policy_summary=policy_summary,
                    execution_tree=tree_state,
                    negotiation_summary=negotiation_summary,
                    strategy_optimization=strategy_optimization,
                    supervision=supervision,
                    execution_state=None,
                    repository_analysis=repository_analysis,
                    engineering_data=engineering_data,
                )
                operational_plan = self.planning_executor.finalize_plan(
                    operational_plan,
                    status_hint="blocked",
                    step_results=step_results,
                )
                self._update_run_status(
                    run_id=run_id,
                    status=RunStatus.FAILED,
                    last_action="simulation_stop",
                    progress_score=self._progress_from_step_results(step_results),
                )
                return step_results
        engineering_data = self._finalize_engineering_data(
            message=message,
            engineering_data=self._collect_engineering_data(engineering_data, step_results),
            step_results=step_results,
        )
        self._write_checkpoint(
            run_id=run_id,
            task_id=task_id,
            session_id=session_id,
            message=message,
            actions=actions,
            next_step_index=start_index,
            completed_steps=step_results,
            plan_graph=graph_state,
            plan_hierarchy=plan_hierarchy,
            plan_signature=plan_signature,
            status="running",
            branch_state=branch_state,
            simulation_summary=simulation_summary,
            cooperative_plan=cooperative_plan,
            strategy_suggestions=strategy_suggestions,
            policy_summary=policy_summary,
            execution_tree=tree_state,
            negotiation_summary=negotiation_summary,
            strategy_optimization=strategy_optimization,
            supervision=supervision,
            repository_analysis=repository_analysis,
            engineering_data=engineering_data,
        )
        executed_steps = 0
        branch_action_ids: set[str] = set()
        continuation_stop_requested = False
        if isinstance(branch_plan, dict) and isinstance(branch_state, dict) and branch_state.get("branches"):
            control_state = self._await_run_control_clearance(run_id=run_id)
            if control_state.get("status") != "running":
                blocked = self._control_block_result(
                    reason_code=str(control_state.get("error") or control_state.get("status") or "operator_control_blocked"),
                    message="Execution paused by operator control.",
                )
                step_results.append(blocked)
                return step_results
            branch_results, branch_action_ids, branch_state, graph_state, tree_state = self._execute_branch_plan(
                session_id=session_id,
                message=message,
                actions=actions,
                task_id=task_id,
                run_id=run_id,
                provider=provider,
                intent=intent,
                delegation=delegation,
                plan_kind=plan_kind,
                semantic_retrieval=semantic_retrieval,
                plan_hierarchy=plan_hierarchy,
                step_results=step_results,
                branch_plan=branch_plan,
                branch_state=branch_state,
                graph_state=graph_state,
                tree_state=tree_state,
            )
            executed_steps += len(branch_results)
            self._write_checkpoint(
                run_id=run_id,
                task_id=task_id,
                session_id=session_id,
                message=message,
                actions=actions,
                next_step_index=min(start_index + executed_steps, len(actions)),
                completed_steps=step_results,
                plan_graph=graph_state,
                plan_hierarchy=plan_hierarchy,
                plan_signature=plan_signature,
                status="running" if all(item.get("ok") for item in branch_results) else "blocked",
                branch_state=branch_state,
                simulation_summary=simulation_summary,
                cooperative_plan=cooperative_plan,
                strategy_suggestions=strategy_suggestions,
                policy_summary=policy_summary,
                execution_tree=tree_state,
                negotiation_summary=negotiation_summary,
                strategy_optimization=strategy_optimization,
                supervision=supervision,
                repository_analysis=repository_analysis,
                engineering_data=engineering_data,
            )
            for branch_result in branch_results:
                tracked_action = branch_result.get("action", {}) if isinstance(branch_result, dict) else {}
                if not isinstance(tracked_action, dict):
                    tracked_action = action_lookup.get(str(branch_result.get("step_id", "")), {})
                operational_plan = self.planning_executor.record_step_result(
                    operational_plan,
                    action=tracked_action,
                    result=branch_result,
                )
                operational_plan, continuation_payload, should_stop = self._handle_continuation_decision(
                    operational_plan=operational_plan,
                    session_id=session_id,
                    task_id=task_id,
                    run_id=run_id,
                    action=tracked_action if isinstance(tracked_action, dict) else {},
                    result=branch_result,
                )
                if continuation_payload is not None:
                    branch_result["continuation_decision"] = continuation_payload
                if should_stop:
                    continuation_stop_requested = True
                    break
            if continuation_stop_requested or (branch_results and not all(item.get("ok") for item in branch_results)):
                operational_plan = self.planning_executor.finalize_plan(
                    operational_plan,
                    status_hint="blocked",
                    step_results=step_results,
                )
                return step_results
        if plan_kind == "graph" and isinstance(graph_state, dict):
            while executed_steps < max_steps:
                control_state = self._await_run_control_clearance(run_id=run_id)
                if control_state.get("status") != "running":
                    blocked = self._control_block_result(
                        reason_code=str(control_state.get("error") or control_state.get("status") or "operator_control_blocked"),
                        message="Execution paused by operator control.",
                    )
                    step_results.append(blocked)
                    break
                batch_stop_requested = False
                ready_parallel, ready_sequential = self._graph_ready_groups(graph_state)
                if not ready_parallel and not ready_sequential:
                    break

                batch_nodes = ready_parallel[: self._runtime_max_parallel_reads()] if ready_parallel else ready_sequential[:1]
                batch_nodes = [node for node in batch_nodes if str(node.get("step_id", "")) not in branch_action_ids]
                if not batch_nodes:
                    break
                batch_actions = [self._action_for_node(actions, node) for node in batch_nodes]
                if any(action is None for action in batch_actions):
                    break

                if len(batch_actions) > 1:
                    self._append_runtime_event(
                        event_type="runtime.parallel.start",
                        session_id=session_id,
                        task_id=task_id,
                        run_id=run_id,
                        payload={
                            "step_ids": [action.get("step_id") for action in batch_actions if isinstance(action, dict)],
                            "parallel_count": len(batch_actions),
                            "plan_kind": plan_kind,
                        },
                    )

                for action in batch_actions:
                    if isinstance(action, dict):
                        operational_plan = self.planning_executor.record_step_started(
                            operational_plan,
                            action=action,
                        )
                batch_results = self._execute_action_batch(
                    actions=[action for action in batch_actions if isinstance(action, dict)],
                    step_results=step_results,
                    semantic_retrieval=semantic_retrieval,
                    learning_guidance=learning_guidance,
                    allow_parallel=len(batch_actions) > 1,
                    session_id=session_id,
                    task_id=task_id,
                    run_id=run_id,
                    operational_plan=operational_plan,
                )

                for action, result in zip(batch_actions, batch_results):
                    executed_steps += 1
                    step_results.append(result)
                    if isinstance(action, dict):
                        operational_plan = self.planning_executor.record_step_result(
                            operational_plan,
                            action=action,
                            result=result,
                        )
                        operational_plan, continuation_payload, should_stop = self._handle_continuation_decision(
                            operational_plan=operational_plan,
                            session_id=session_id,
                            task_id=task_id,
                            run_id=run_id,
                            action=action,
                            result=result,
                        )
                        if continuation_payload is not None:
                            result["continuation_decision"] = continuation_payload
                        if should_stop:
                            batch_stop_requested = True
                            break
                    graph_state = self._mark_graph_outcome(graph_state, action, result)
                    tree_state = self._mark_tree_outcome(tree_state, action, result, retries=len(result.get("correction_events", [])))
                    self._append_runtime_execution_logs(
                        session_id=session_id,
                        message=message,
                        action=action,
                        result=result,
                        task_id=task_id,
                        run_id=run_id,
                        provider=provider,
                        intent=intent,
                        delegates=delegation.get("delegates", []),
                        specialists=delegation.get("specialists", []),
                        plan_kind=plan_kind,
                        semantic_retrieval=semantic_retrieval,
                        plan_hierarchy=plan_hierarchy,
                    )
                    if not result.get("ok"):
                        break

                self._write_checkpoint(
                    run_id=run_id,
                    task_id=task_id,
                    session_id=session_id,
                    message=message,
                    actions=actions,
                    next_step_index=min(start_index + executed_steps, len(actions)),
                    completed_steps=step_results,
                    plan_graph=graph_state,
                    plan_hierarchy=plan_hierarchy,
                    plan_signature=plan_signature,
                    status="blocked" if step_results and not step_results[-1].get("ok") else "running",
                    branch_state=branch_state,
                    simulation_summary=simulation_summary,
                    cooperative_plan=cooperative_plan,
                    strategy_suggestions=strategy_suggestions,
                    policy_summary=policy_summary,
                    execution_tree=tree_state,
                    negotiation_summary=negotiation_summary,
                    strategy_optimization=strategy_optimization,
                    supervision=supervision,
                    repository_analysis=repository_analysis,
                    engineering_data=engineering_data,
                )
                if batch_stop_requested or (step_results and not step_results[-1].get("ok")):
                    break
        else:
            for index, action in enumerate(actions[start_index:max_steps], start=start_index):
                control_state = self._await_run_control_clearance(run_id=run_id)
                if control_state.get("status") != "running":
                    blocked = self._control_block_result(
                        reason_code=str(control_state.get("error") or control_state.get("status") or "operator_control_blocked"),
                        message="Execution paused by operator control.",
                    )
                    step_results.append(blocked)
                    break
                if not isinstance(action, dict):
                    continue
                if str(action.get("step_id", "")) in branch_action_ids:
                    continue

                operational_plan = self.planning_executor.record_step_started(
                    operational_plan,
                    action=action,
                )
                result = self._execute_single_action(
                    action=action,
                    step_results=step_results,
                    semantic_retrieval=semantic_retrieval,
                    learning_guidance=learning_guidance,
                    session_id=session_id,
                    task_id=task_id,
                    run_id=run_id,
                    operational_plan=operational_plan,
                )
                executed_steps += 1
                step_results.append(result)
                operational_plan = self.planning_executor.record_step_result(
                    operational_plan,
                    action=action,
                    result=result,
                )
                operational_plan, continuation_payload, should_stop = self._handle_continuation_decision(
                    operational_plan=operational_plan,
                    session_id=session_id,
                    task_id=task_id,
                    run_id=run_id,
                    action=action,
                    result=result,
                )
                if continuation_payload is not None:
                    result["continuation_decision"] = continuation_payload
                tree_state = self._mark_tree_outcome(tree_state, action, result, retries=len(result.get("correction_events", [])))

                self._append_runtime_execution_logs(
                    session_id=session_id,
                    message=message,
                    action=action,
                    result=result,
                    task_id=task_id,
                    run_id=run_id,
                    provider=provider,
                    intent=intent,
                    delegates=delegation.get("delegates", []),
                    specialists=delegation.get("specialists", []),
                    plan_kind=plan_kind,
                    semantic_retrieval=semantic_retrieval,
                    plan_hierarchy=plan_hierarchy,
                )
                self._write_checkpoint(
                    run_id=run_id,
                    task_id=task_id,
                    session_id=session_id,
                    message=message,
                    actions=actions,
                    next_step_index=index + 1,
                    completed_steps=step_results,
                    plan_graph=graph_state,
                    plan_hierarchy=plan_hierarchy,
                    plan_signature=plan_signature,
                    status="blocked" if not result.get("ok") else "running",
                    branch_state=branch_state,
                    simulation_summary=simulation_summary,
                    cooperative_plan=cooperative_plan,
                    strategy_suggestions=strategy_suggestions,
                    policy_summary=policy_summary,
                    execution_tree=tree_state,
                    negotiation_summary=negotiation_summary,
                    strategy_optimization=strategy_optimization,
                    supervision=supervision,
                    repository_analysis=repository_analysis,
                    engineering_data=engineering_data,
                )

                if should_stop or not result.get("ok"):
                    break

        engineering_data = self._finalize_engineering_data(
            message=message,
            engineering_data=self._collect_engineering_data(engineering_data, step_results),
            step_results=step_results,
        )
        self._write_checkpoint(
            run_id=run_id,
            task_id=task_id,
            session_id=session_id,
            message=message,
            actions=actions,
            next_step_index=min(start_index + len(step_results), len(actions)),
            completed_steps=step_results,
            plan_graph=graph_state,
            plan_hierarchy=plan_hierarchy,
            plan_signature=plan_signature,
            status="completed"
            if (
                (start_index + len(step_results) >= len(actions) or self._graph_complete(graph_state))
                and step_results
                and all(item.get("ok") for item in step_results)
            )
            else "blocked",
            branch_state=branch_state,
            simulation_summary=simulation_summary,
            cooperative_plan=cooperative_plan,
            strategy_suggestions=strategy_suggestions,
            policy_summary=policy_summary,
            execution_tree=tree_state,
            negotiation_summary=negotiation_summary,
            strategy_optimization=strategy_optimization,
            supervision=supervision,
            repository_analysis=repository_analysis,
            engineering_data=engineering_data,
        )
        reflection = self._reflect_on_run(
            message=message,
            step_results=step_results,
            task_id=task_id,
            run_id=run_id,
            session_id=session_id,
            plan_hierarchy=plan_hierarchy,
            learning_guidance=learning_guidance,
            policy_summary=policy_summary,
            branch_state=branch_state,
            cooperative_plan=cooperative_plan,
        )
        if reflection.get("invoked"):
            self._append_runtime_event(
                event_type="runtime.reflection",
                session_id=session_id,
                task_id=task_id,
                run_id=run_id,
                payload=reflection,
            )
            if reflection.get("update_learning"):
                self._record_learning_memory(
                    session_id=session_id,
                    task_id=task_id,
                    run_id=run_id,
                    message=message,
                    outcome="success" if step_results and all(item.get("ok") for item in step_results) else "failure_avoidance",
                    tool_family=str(step_results[0].get("selected_tool", "unknown")) if step_results else "unknown",
                    lesson=str(reflection.get("summary", "")),
                    trigger=str(reflection.get("reason_code", "")),
                    metadata={"plan_kind": plan_kind, "hierarchical": bool(plan_hierarchy)},
                )
        self.checkpoint_store.save(
            run_id,
            {
                "task_id": task_id,
                "session_id": session_id,
                "message": message,
                "status": (
                    "completed"
                    if (
                        min(start_index + len(step_results), len(actions)) >= len(actions)
                        and step_results
                        and all(item.get("ok") for item in step_results)
                    )
                    else "blocked"
                ),
                "next_step_index": min(start_index + len(step_results), len(actions)),
                "completed_steps": step_results,
                "remaining_actions": actions[min(start_index + len(step_results), len(actions)):],
                "total_actions": len(actions),
                "plan_graph": graph_state,
                "plan_hierarchy": plan_hierarchy,
                "plan_signature": plan_signature,
                "reflection_summary": reflection,
                "branch_state": branch_state,
                "simulation_summary": simulation_summary,
                "cooperative_plan": cooperative_plan,
                "strategy_suggestions": strategy_suggestions,
                "policy_summary": policy_summary if isinstance(policy_summary, list) else [],
                "execution_tree": tree_state,
                "negotiation_summary": negotiation_summary,
                "strategy_optimization": strategy_optimization,
                "supervision": supervision,
                "repository_analysis": repository_analysis,
                "engineering_data": engineering_data,
            },
        )
        fusion_summary = self._build_fusion_summary(step_results, cooperative_plan, branch_state, strategy_suggestions)
        execution_state = build_execution_state(
            session_id=session_id,
            task_id=task_id,
            run_id=run_id,
            execution_tree=tree_state,
            branch_state=branch_state,
            cooperative_plan=cooperative_plan,
            negotiation_summary=negotiation_summary,
            simulation_summary=simulation_summary,
            strategy_suggestions=strategy_suggestions if isinstance(strategy_suggestions, list) else [],
            policy_summary=policy_summary if isinstance(policy_summary, list) else [],
            fusion_summary=fusion_summary,
            supervision=supervision,
            repository_analysis=repository_analysis,
            engineering_data=engineering_data,
        )
        self._write_run_summary(
            session_id=session_id,
            task_id=task_id,
            run_id=run_id,
            message=message,
            step_results=step_results,
            plan_kind=plan_kind,
            plan_hierarchy=plan_hierarchy,
            reflection=reflection,
            branch_state=branch_state,
            cooperative_plan=cooperative_plan,
            simulation_summary=simulation_summary,
            strategy_suggestions=strategy_suggestions,
            fusion_summary=fusion_summary,
            policy_summary=policy_summary,
            execution_tree=tree_state,
            negotiation_summary=negotiation_summary,
            strategy_optimization=strategy_optimization,
            supervision=supervision,
            execution_state=execution_state,
            repository_analysis=repository_analysis,
            engineering_data=engineering_data,
        )
        operational_plan = self.planning_executor.finalize_plan(
            operational_plan,
            status_hint="completed" if step_results and all(item.get("ok") for item in step_results) else "blocked",
            step_results=step_results,
        )
        self._completion_service.apply_fusion_terminal_status(run_id=run_id, step_results=step_results)
        operational_summary = self.planning_executor.summary_for_plan(operational_plan)
        if operational_summary is not None:
            final_checkpoint = self.planning_executor.store.load_latest_checkpoint(operational_plan.plan_id) if operational_plan else None
            learning_update = self.learning_executor.ingest_runtime_artifacts(
                plan=operational_plan,
                checkpoint=final_checkpoint,
                summary=operational_summary,
            )
            self._append_runtime_event(
                event_type="runtime.planning.summary",
                session_id=session_id,
                task_id=task_id,
                run_id=run_id,
                payload={
                    **operational_summary.as_dict(),
                    "learning": learning_update,
                },
            )
        return step_results

    def _handle_continuation_decision(
        self,
        *,
        operational_plan: Any,
        session_id: str,
        task_id: str,
        run_id: str,
        action: dict[str, Any],
        result: dict[str, Any],
    ) -> tuple[Any, dict[str, Any] | None, bool]:
        continuation_signals = self.learning_executor.advisory_signals_for_continuation(
            plan=operational_plan,
            result=result,
        )
        goal_context = self.planning_executor.goal_context_for_plan(operational_plan)
        evaluation, decision, updated_plan = self.continuation_executor.evaluate_and_decide(
            plan=operational_plan,
            result=result,
            advisory_signals=continuation_signals,
            coordination_trace=result.get("coordination_trace") if isinstance(result.get("coordination_trace"), dict) else None,
        )
        if decision is None:
            return updated_plan, None, False
        latest_checkpoint = self.planning_executor.store.load_latest_checkpoint(updated_plan.plan_id) if updated_plan else None
        latest_summary = self.planning_executor.store.load_summary(updated_plan.plan_id) if updated_plan else None
        orchestration_update = self.orchestration_executor.orchestrate(
            session_id=session_id,
            task_id=task_id,
            run_id=run_id,
            action=action,
            plan=updated_plan,
            checkpoint=latest_checkpoint,
            summary=latest_summary,
            goal_context=goal_context,
            continuation_decision=decision.as_dict(),
            step_results=[result],
            learning_signals=[signal.as_dict() for signal in continuation_signals],
            engineering_tool=supports_engineering_tool(str(action.get("selected_tool", ""))),
            primary_result=result,
        )
        evolution_update = self.evolution_executor.evaluate(
            learning_update=None,
            orchestration_update=orchestration_update,
            result=result,
            continuation_payload=decision.as_dict(),
            goal=self.planning_executor.goal_for_plan(updated_plan),
        )
        learning_update = self.learning_executor.ingest_runtime_artifacts(
            action=action,
            result=result,
            plan=updated_plan,
            checkpoint=latest_checkpoint,
            summary=latest_summary,
            continuation_evaluation=evaluation.as_dict() if evaluation is not None else None,
            continuation_decision=decision.as_dict(),
        )
        if updated_plan is not None and updated_plan.goal_id and evaluation is not None:
            self.memory_facade.update_progress(evaluation.progress_ratio)
        if updated_plan is not None and updated_plan.goal_id:
            self.memory_facade.record_event(
                event_type="continuation_outcome",
                description=decision.reason_summary,
                outcome=decision.decision_type.value,
                progress_score=evaluation.progress_ratio if evaluation is not None else None,
                evidence_ids=[
                    item
                    for item in [
                        str((result.get("execution_receipt") or {}).get("receipt_id", "")).strip(),
                        str((result.get("repair_receipt") or {}).get("repair_receipt_id", "")).strip(),
                    ]
                    if item
                ],
                metadata={
                    "plan_id": updated_plan.plan_id,
                    "goal_id": updated_plan.goal_id,
                    "reason_code": decision.reason_code,
                    "action_step_id": action.get("step_id"),
                    "coordination_trace_id": str(((result.get("coordination_trace") or {}).get("trace_id", ""))).strip(),
                },
            )
            if decision.decision_type == ContinuationDecisionType.COMPLETE_PLAN:
                self.memory_facade.close_goal_episode(
                    outcome="achieved",
                    description=decision.reason_summary,
                    event_type="goal_resolution",
                    evidence_ids=[
                        item
                        for item in [
                            str((result.get("execution_receipt") or {}).get("receipt_id", "")).strip(),
                            str((result.get("repair_receipt") or {}).get("repair_receipt_id", "")).strip(),
                        ]
                        if item
                    ],
                    metadata={
                        "goal_type": goal_context.intent if goal_context is not None else "",
                        "recommended_route": decision.decision_type.value,
                        "decision_type": decision.decision_type.value,
                        "plan_id": updated_plan.plan_id,
                        "simulation_id": str((decision.metadata or {}).get("simulation_id", "")).strip(),
                    },
                    coordination_trace_id=str(((result.get("coordination_trace") or {}).get("trace_id", ""))).strip() or None,
                )
            elif decision.decision_type == ContinuationDecisionType.ESCALATE_FAILURE:
                self.memory_facade.close_goal_episode(
                    outcome="failed",
                    description=decision.reason_summary,
                    event_type="goal_resolution",
                    evidence_ids=[
                        item
                        for item in [
                            str((result.get("execution_receipt") or {}).get("receipt_id", "")).strip(),
                            str((result.get("repair_receipt") or {}).get("repair_receipt_id", "")).strip(),
                        ]
                        if item
                    ],
                    metadata={
                        "goal_type": goal_context.intent if goal_context is not None else "",
                        "recommended_route": decision.decision_type.value,
                        "decision_type": decision.decision_type.value,
                        "plan_id": updated_plan.plan_id,
                        "simulation_id": str((decision.metadata or {}).get("simulation_id", "")).strip(),
                    },
                    coordination_trace_id=str(((result.get("coordination_trace") or {}).get("trace_id", ""))).strip() or None,
                )
        self._append_runtime_event(
            event_type="runtime.continuation.decision",
            session_id=session_id,
            task_id=task_id,
            run_id=run_id,
            payload={
                "evaluation": evaluation.as_dict() if evaluation is not None else None,
                "decision": decision.as_dict(),
                "orchestration": orchestration_update,
                "evolution": evolution_update,
                "learning": learning_update,
            },
        )
        should_stop = decision.decision_type in {
            ContinuationDecisionType.PAUSE_PLAN,
            ContinuationDecisionType.REBUILD_PLAN,
            ContinuationDecisionType.ESCALATE_FAILURE,
            ContinuationDecisionType.COMPLETE_PLAN,
        }
        if decision.decision_type == ContinuationDecisionType.PAUSE_PLAN:
            self._update_run_status(
                run_id=run_id,
                status=RunStatus.PAUSED,
                last_action=decision.reason_code or "pause_plan",
                progress_score=evaluation.progress_ratio if evaluation is not None else 0.0,
            )
        elif decision.decision_type == ContinuationDecisionType.COMPLETE_PLAN:
            self._update_run_status(
                run_id=run_id,
                status=RunStatus.COMPLETED,
                last_action=decision.reason_code or "complete_plan",
                progress_score=1.0,
            )
        elif decision.decision_type == ContinuationDecisionType.ESCALATE_FAILURE:
            self._update_run_status(
                run_id=run_id,
                status=RunStatus.FAILED,
                last_action=decision.reason_code or "escalate_failure",
                progress_score=evaluation.progress_ratio if evaluation is not None else 0.0,
            )
        decision_payload = decision.as_dict()
        decision_payload["orchestration"] = orchestration_update
        decision_payload["evolution"] = evolution_update
        return updated_plan, decision_payload, should_stop

    @staticmethod
    def _clone_plan_graph(plan_graph: dict[str, Any] | None) -> dict[str, Any] | None:
        if not isinstance(plan_graph, dict):
            return None
        try:
            return json.loads(json.dumps(plan_graph))
        except Exception:
            return None

    @staticmethod
    def _clone_tree(execution_tree: dict[str, Any] | None) -> dict[str, Any] | None:
        if not isinstance(execution_tree, dict):
            return None
        try:
            return json.loads(json.dumps(execution_tree))
        except Exception:
            return None

    @staticmethod
    def _action_for_node(actions: list[dict[str, Any]], node: dict[str, Any]) -> dict[str, Any] | None:
        step_id = str(node.get("step_id", ""))
        for action in actions:
            if isinstance(action, dict) and str(action.get("step_id", "")) == step_id:
                return action
        return None

    @staticmethod
    def _graph_ready_groups(plan_graph: dict[str, Any] | None) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        if not isinstance(plan_graph, dict):
            return [], []
        nodes = plan_graph.get("nodes", [])
        if not isinstance(nodes, list):
            return [], []
        completed = {
            str(node.get("node_id"))
            for node in nodes
            if isinstance(node, dict) and str(node.get("state", "")) == "completed"
        }
        pending = [
            node for node in nodes
            if isinstance(node, dict) and str(node.get("state", "pending")) == "pending"
        ]
        ready = [
            node for node in pending
            if all(str(dep) in completed for dep in node.get("depends_on", []) if dep)
        ]
        parallel = [node for node in ready if bool(node.get("parallel_safe"))]
        sequential = [node for node in ready if not bool(node.get("parallel_safe"))]
        return parallel, sequential

    @staticmethod
    def _graph_complete(plan_graph: dict[str, Any] | None) -> bool:
        if not isinstance(plan_graph, dict):
            return False
        nodes = plan_graph.get("nodes", [])
        return bool(nodes) and all(str(node.get("state", "")) == "completed" for node in nodes if isinstance(node, dict))

    @staticmethod
    def _tree_complete(execution_tree: dict[str, Any] | None) -> bool:
        if not isinstance(execution_tree, dict):
            return False
        nodes = execution_tree.get("nodes", [])
        step_nodes = [node for node in nodes if isinstance(node, dict) and node.get("node_type") == "step"]
        return bool(step_nodes) and all(str(node.get("state", "")) == "completed" for node in step_nodes)

    @staticmethod
    def _mark_tree_outcome(
        execution_tree: dict[str, Any] | None,
        action: dict[str, Any],
        result: dict[str, Any],
        *,
        retries: int = 0,
    ) -> dict[str, Any] | None:
        if not isinstance(execution_tree, dict):
            return execution_tree
        target_step = str(action.get("step_id", ""))
        node_map = {
            str(node.get("node_id")): node
            for node in execution_tree.get("nodes", [])
            if isinstance(node, dict)
        }
        for node in node_map.values():
            if str(node.get("step_id", "")) == target_step:
                node["state"] = "completed" if result.get("ok") else "failed"
                node["retries"] = retries
                parent_id = str(node.get("parent_id") or "")
                while parent_id and parent_id in node_map:
                    parent = node_map[parent_id]
                    child_ids = parent.get("children", [])
                    child_states = [
                        str(node_map.get(str(child_id), {}).get("state", "pending"))
                        for child_id in child_ids
                        if str(child_id) in node_map
                    ]
                    if child_states and all(state == "completed" for state in child_states):
                        parent["state"] = "completed"
                    elif any(state == "failed" for state in child_states):
                        parent["state"] = "partial"
                    else:
                        parent["state"] = "running"
                    parent_id = str(parent.get("parent_id") or "")
                break
        return execution_tree

    @staticmethod
    def _initial_branch_state(branch_plan: dict[str, Any] | None) -> dict[str, Any] | None:
        if not isinstance(branch_plan, dict):
            return None
        branches = branch_plan.get("branches", [])
        if not isinstance(branches, list):
            return None
        return {
            "enabled": bool(branch_plan.get("enabled", True)),
            "merge_mode": str(branch_plan.get("merge_mode", "winner-selection")),
            "branches": [
                {
                    "branch_id": branch.get("branch_id"),
                    "label": branch.get("label"),
                    "safe": bool(branch.get("safe", True)),
                    "state": "pending",
                    "step_ids": branch.get("step_ids", []),
                }
                for branch in branches
                if isinstance(branch, dict)
            ],
            "winner_branch_id": None,
            "pruned_branch_ids": [],
        }

    def _execute_branch_plan(
        self,
        *,
        session_id: str,
        message: str,
        actions: list[dict[str, Any]],
        task_id: str,
        run_id: str,
        provider: dict[str, Any] | str,
        intent: str,
        delegation: dict[str, Any],
        plan_kind: str,
        semantic_retrieval: object,
        plan_hierarchy: dict[str, Any] | None,
        step_results: list[dict[str, Any]],
        branch_plan: dict[str, Any],
        branch_state: dict[str, Any],
        graph_state: dict[str, Any] | None,
        tree_state: dict[str, Any] | None,
    ) -> tuple[list[dict[str, Any]], set[str], dict[str, Any], dict[str, Any] | None, dict[str, Any] | None]:
        results: list[dict[str, Any]] = []
        executed_ids: set[str] = set()
        branches = branch_state.get("branches", []) if isinstance(branch_state, dict) else []
        if not branches:
            return results, executed_ids, branch_state, graph_state, tree_state
        parallel_branch_mode = len(branches) > 1
        if parallel_branch_mode:
            self._append_runtime_event(
                event_type="runtime.parallel.start",
                session_id=session_id,
                task_id=task_id,
                run_id=run_id,
                payload={
                    "branch_ids": [str(branch.get("branch_id", "")) for branch in branches],
                    "parallel_count": len(branches),
                    "plan_kind": plan_kind,
                    "mode": "branch-coordination",
                },
            )

        branch_scores: dict[str, float] = {}
        for branch in branches[: int(branch_plan.get("max_branches", 2) or 2)]:
            branch_id = str(branch.get("branch_id", ""))
            branch_actions = [
                action for action in actions
                if isinstance(action, dict)
                and str(action.get("execution_context", {}).get("branch_id", "")) == branch_id
            ]
            if not branch_actions:
                continue
            self._append_runtime_event(
                event_type="runtime.branch.start",
                session_id=session_id,
                task_id=task_id,
                run_id=run_id,
                payload={"branch_id": branch_id, "step_count": len(branch_actions)},
            )
            batch_results = self._execute_action_batch(
                actions=branch_actions,
                step_results=step_results,
                semantic_retrieval=semantic_retrieval,
                learning_guidance=[],
                allow_parallel=all(action.get("selected_tool") != "write_file" for action in branch_actions),
                session_id=session_id,
                task_id=task_id,
                run_id=run_id,
            )
            if len(branch_actions) > 1:
                self._append_runtime_event(
                    event_type="runtime.parallel.start",
                    session_id=session_id,
                    task_id=task_id,
                    run_id=run_id,
                    payload={
                        "step_ids": [action.get("step_id") for action in branch_actions],
                        "parallel_count": len(branch_actions),
                        "plan_kind": plan_kind,
                        "branch_id": branch_id,
                    },
                )
            for action, result in zip(branch_actions, batch_results):
                executed_ids.add(str(action.get("step_id", "")))
                results.append(result)
                step_results.append(result)
                graph_state = self._mark_graph_outcome(graph_state, action, result)
                tree_state = self._mark_tree_outcome(tree_state, action, result, retries=len(result.get("correction_events", [])))
                self._append_runtime_execution_logs(
                    session_id=session_id,
                    message=message,
                    action=action,
                    result=result,
                    task_id=task_id,
                    run_id=run_id,
                    provider=provider,
                    intent=intent,
                    delegates=delegation.get("delegates", []),
                    specialists=delegation.get("specialists", []),
                    plan_kind=plan_kind,
                    semantic_retrieval=semantic_retrieval,
                    plan_hierarchy=plan_hierarchy,
                )
            branch["state"] = "completed" if batch_results and all(item.get("ok") for item in batch_results) else "failed"
            branch_scores[branch_id] = sum(1.5 if item.get("ok") else -1 for item in batch_results) + sum(
                0.4 for item in batch_results if item.get("selected_tool") == "read_file"
            )
            self._append_runtime_event(
                event_type="runtime.branch.complete",
                session_id=session_id,
                task_id=task_id,
                run_id=run_id,
                payload={"branch_id": branch_id, "score": branch_scores[branch_id], "status": branch["state"]},
            )

        if branch_scores:
            winner_branch_id = max(branch_scores.items(), key=lambda item: item[1])[0]
            pruned = [branch_id for branch_id in branch_scores if branch_id != winner_branch_id]
            branch_state["winner_branch_id"] = winner_branch_id
            branch_state["pruned_branch_ids"] = pruned
            for branch in branches:
                if branch.get("branch_id") in pruned:
                    branch["state"] = "pruned"
            self._append_runtime_event(
                event_type="runtime.branch.decision",
                session_id=session_id,
                task_id=task_id,
                run_id=run_id,
                payload={
                    "winner_branch_id": winner_branch_id,
                    "pruned_branch_ids": pruned,
                    "merge_mode": branch_state.get("merge_mode", "winner-selection"),
                },
            )
        if parallel_branch_mode:
            self._append_runtime_event(
                event_type="runtime.parallel.complete",
                session_id=session_id,
                task_id=task_id,
                run_id=run_id,
                payload={
                    "branch_ids": [str(branch.get("branch_id", "")) for branch in branches],
                    "parallel_count": len(branches),
                    "winner_branch_id": branch_state.get("winner_branch_id"),
                    "mode": "branch-coordination",
                },
            )
        return results, executed_ids, branch_state, graph_state, tree_state

    @staticmethod
    def _mark_graph_outcome(plan_graph: dict[str, Any] | None, action: dict[str, Any], result: dict[str, Any]) -> dict[str, Any] | None:
        if not isinstance(plan_graph, dict):
            return plan_graph
        for node in plan_graph.get("nodes", []):
            if not isinstance(node, dict):
                continue
            if str(node.get("step_id", "")) == str(action.get("step_id", "")):
                node["state"] = "completed" if result.get("ok") else "failed"
                node["last_result"] = {
                    "ok": bool(result.get("ok")),
                    "evaluation": result.get("evaluation"),
                }
        return plan_graph

    def _execute_action_batch(
        self,
        *,
        actions: list[dict[str, Any]],
        step_results: list[dict[str, Any]],
        semantic_retrieval: object,
        learning_guidance: object,
        allow_parallel: bool,
        session_id: str,
        task_id: str,
        run_id: str,
        operational_plan: Any = None,
    ) -> list[dict[str, Any]]:
        if not allow_parallel or len(actions) <= 1:
            return [
                self._execute_single_action(
                    action=action,
                    step_results=step_results,
                    semantic_retrieval=semantic_retrieval,
                    learning_guidance=learning_guidance,
                    session_id=session_id,
                    task_id=task_id,
                    run_id=run_id,
                    operational_plan=operational_plan,
                )
                for action in actions
            ]

        results_by_step: dict[str, dict[str, Any]] = {}
        with ThreadPoolExecutor(max_workers=min(len(actions), self._runtime_max_parallel_reads())) as executor:
            futures = {
                executor.submit(
                    self._execute_single_action,
                    action=action,
                    step_results=step_results,
                    semantic_retrieval=semantic_retrieval,
                    learning_guidance=learning_guidance,
                    session_id=session_id,
                    task_id=task_id,
                    run_id=run_id,
                    operational_plan=operational_plan,
                ): action
                for action in actions
            }
            for future in as_completed(futures):
                action = futures[future]
                results_by_step[str(action.get("step_id", ""))] = future.result()

        return [results_by_step[str(action.get("step_id", ""))] for action in actions]

    def _execute_single_action(
        self,
        *,
        action: dict[str, Any],
        step_results: list[dict[str, Any]],
        semantic_retrieval: object,
        session_id: str,
        task_id: str,
        run_id: str,
        learning_guidance: object = None,
        operational_plan: Any = None,
    ) -> dict[str, Any]:
        return self._execution_dispatch.execute_single_action_with_specialists(
            action=action,
            step_results=step_results,
            semantic_retrieval=semantic_retrieval,
            session_id=session_id,
            task_id=task_id,
            run_id=run_id,
            learning_guidance=learning_guidance,
            operational_plan=operational_plan,
        )

    def _execute_single_action_core(
        self,
        *,
        action: dict[str, Any],
        step_results: list[dict[str, Any]],
        semantic_retrieval: object,
        session_id: str,
        task_id: str,
        run_id: str,
        learning_guidance: object = None,
        operational_plan: Any = None,
    ) -> dict[str, Any]:
        attempts = int(action.get("retry_policy", {}).get("max_attempts", 1) or 1)
        attempts = min(attempts, self._runtime_correction_depth() + 1)
        final_result: dict[str, Any] | None = None
        correction_events: list[dict[str, Any]] = []
        current_action = dict(action)
        current_action["session_id"] = session_id
        current_action["task_id"] = task_id
        current_action["run_id"] = run_id
        if operational_plan is not None and getattr(operational_plan, "goal_id", None):
            current_action["goal_id"] = operational_plan.goal_id
        policy_decision = dict(current_action.get("policy_decision", {}) or {})
        selected_tool = str(current_action.get("selected_tool", "") or "").strip()
        tool_audit = evaluate_tool_governance(
            selected_tool=selected_tool,
            trusted_known_tools=self.trusted_executor.available_tools,
            strict_mode=is_strict_governed_tools_mode(),
        )
        current_action["tool_governance_audit"] = tool_audit.as_dict()
        if not tool_audit.allowed:
            blocked_result: dict[str, Any] = {
                "ok": False,
                "error_payload": {
                    "kind": GOVERNED_TOOLS_STRICT_BLOCK_KIND,
                    "message": (
                        "Tool execution blocked: strict governed-tools mode requires an explicit "
                        f"governed declaration for tool {selected_tool!r}."
                    ),
                    "governance": governance_dict_for_strict_block(),
                    "tool_governance_audit": tool_audit.as_dict(),
                },
            }
            blocked_result["selected_tool"] = current_action.get("selected_tool")
            blocked_result["selected_agent"] = current_action.get("selected_agent")
            blocked_result["evaluation"] = build_strict_block_evaluation(tool_audit=tool_audit)
            blocked_result["correction_events"] = [blocked_result["evaluation"]]
            blocked_result["orchestration"] = None
            return blocked_result

        latest_checkpoint = self.planning_executor.store.load_latest_checkpoint(operational_plan.plan_id) if operational_plan else None
        latest_summary = self.planning_executor.store.load_summary(operational_plan.plan_id) if operational_plan else None
        goal_context = self.planning_executor.goal_context_for_plan(operational_plan)
        planning_signals = [signal.as_dict() for signal in self.learning_executor.advisory_signals_for_planning(actions=[current_action])]
        pre_execution_orchestration = self.orchestration_executor.orchestrate(
            session_id=session_id,
            task_id=task_id,
            run_id=run_id,
            action=current_action,
            plan=operational_plan,
            checkpoint=latest_checkpoint,
            summary=latest_summary,
            goal_context=goal_context,
            step_results=step_results,
            learning_signals=planning_signals,
            engineering_tool=supports_engineering_tool(str(current_action.get("selected_tool", ""))),
        )
        self._append_runtime_event(
            event_type="runtime.orchestration.pre_execution",
            session_id=session_id,
            task_id=task_id,
            run_id=run_id,
            payload=pre_execution_orchestration,
        )

        if policy_decision.get("decision") == "stop":
            blocked_result = {
                "ok": False,
                "error_payload": {
                    "kind": "policy_stop",
                    "message": str(policy_decision.get("operator_message", "Execution blocked by runtime policy.")),
                    "policy": policy_decision,
                },
            }
            blocked_result["selected_tool"] = current_action.get("selected_tool")
            blocked_result["selected_agent"] = current_action.get("selected_agent")
            blocked_result["evaluation"] = {
                "decision": "stop_blocked",
                "reason_code": str(policy_decision.get("reason_code", "policy_stop")),
                "critic": {
                    "invoked": False,
                    "decision": "stop",
                    "reason_code": "policy_stop",
                },
                "learning_guidance": learning_guidance[0] if isinstance(learning_guidance, list) and learning_guidance else None,
            }
            blocked_result["correction_events"] = [blocked_result["evaluation"]]
            blocked_result["orchestration"] = pre_execution_orchestration
            return blocked_result

        for attempt_number in range(1, attempts + 1):
            trusted_execution = self.trusted_executor.execute(
                intent=self._build_execution_intent(
                    action=current_action,
                    session_id=session_id,
                    task_id=task_id,
                    run_id=run_id,
                ),
                current_mode=self.last_runtime_mode,
                retry_count=max(0, attempt_number - 1),
                execute_callback=lambda current_action=current_action: execute_engineering_action(
                    project_root=self.paths.root,
                    action=current_action,
                    timeout_seconds=max(1, int(current_action.get("timeout_ms", SUBPROCESS_TIMEOUT_SECONDS * 1000) / 1000)),
                )
                if supports_engineering_tool(str(current_action.get("selected_tool", "")))
                else execute_action(
                    self.paths.root,
                    current_action,
                    timeout_seconds=max(1, int(current_action.get("timeout_ms", SUBPROCESS_TIMEOUT_SECONDS * 1000) / 1000)),
                ),
            )
            final_result = trusted_execution.result
            if not final_result.get("ok") and self.self_repair_loop.executor.policy.enable_self_repair:
                recurrence_count = self._count_failure_recurrence(
                    action=current_action,
                    result=final_result,
                    step_results=step_results,
                    attempt_number=attempt_number,
                )
                repair_signals = self.learning_executor.advisory_signals_for_repair(
                    action=current_action,
                    result=final_result,
                )
                self_repair_outcome = self.self_repair_loop.inspect_failure(
                    action=current_action,
                    result=final_result,
                    trusted_execution=trusted_execution,
                    retry_count=max(0, attempt_number - 1),
                    recurrence_count=recurrence_count,
                    advisory_signals=repair_signals,
                )
                self._append_runtime_event(
                    event_type="runtime.self_repair.receipt",
                    session_id=session_id,
                    task_id=task_id,
                    run_id=run_id,
                    payload={
                        "selected_tool": current_action.get("selected_tool"),
                        "selected_agent": current_action.get("selected_agent"),
                        "self_repair": self_repair_outcome.as_dict(),
                    },
                )
                if self_repair_outcome.status == RepairStatus.PROMOTED:
                    trusted_execution = self.trusted_executor.execute(
                        intent=self._build_execution_intent(
                            action=current_action,
                            session_id=session_id,
                            task_id=task_id,
                            run_id=run_id,
                        ),
                        current_mode=self.last_runtime_mode,
                        retry_count=max(0, attempt_number - 1),
                        execute_callback=lambda current_action=current_action: execute_engineering_action(
                            project_root=self.paths.root,
                            action=current_action,
                            timeout_seconds=max(1, int(current_action.get("timeout_ms", SUBPROCESS_TIMEOUT_SECONDS * 1000) / 1000)),
                        )
                        if supports_engineering_tool(str(current_action.get("selected_tool", "")))
                        else execute_action(
                            self.paths.root,
                            current_action,
                            timeout_seconds=max(1, int(current_action.get("timeout_ms", SUBPROCESS_TIMEOUT_SECONDS * 1000) / 1000)),
                        ),
                    )
                    final_result = trusted_execution.result
                final_result = self._attach_self_repair_metadata(final_result, self_repair_outcome)
            self._append_runtime_event(
                event_type="runtime.trusted_execution.receipt",
                session_id=session_id,
                task_id=task_id,
                run_id=run_id,
                payload={
                    "receipt": trusted_execution.receipt.as_dict(),
                    "risk": trusted_execution.risk.as_dict(),
                    "preflight": trusted_execution.preflight.as_dict(),
                    "guardrail": trusted_execution.guardrail.as_dict(),
                    "verification": trusted_execution.verification.as_dict(),
                    "selected_tool": current_action.get("selected_tool"),
                    "selected_agent": current_action.get("selected_agent"),
                },
            )
            evaluation = self._evaluate_step(
                current_action,
                final_result,
                attempt_index=attempt_number,
                attempts=attempts,
            )
            critic = self._critic_outcome_review(
                action=current_action,
                result=final_result,
                evaluation=evaluation,
                attempt_index=attempt_number,
                max_attempts=attempts,
            )
            evaluation["critic"] = critic
            evaluation["learning_guidance"] = learning_guidance[0] if isinstance(learning_guidance, list) and learning_guidance else None
            correction_events.append(evaluation)

            if final_result.get("ok"):
                break
            if evaluation["decision"] == "revise_plan":
                revised_action = self._revise_action_from_context(current_action, step_results, semantic_retrieval)
                if revised_action is not None:
                    current_action = revised_action
                    continue
            if evaluation["decision"] != "retry_same_step":
                break

        result = final_result or {
            "ok": False,
            "error_payload": {
                "kind": "execution_failure",
                "message": "Runtime step failed without a result payload",
            },
        }
        result["selected_tool"] = current_action.get("selected_tool")
        result["selected_agent"] = current_action.get("selected_agent")
        result["milestone_id"] = current_action.get("milestone_id")
        result["action"] = current_action
        result["evaluation"] = correction_events[-1] if correction_events else {
            "decision": "stop_failed",
            "reason_code": "missing_result",
        }
        result["correction_events"] = correction_events
        result["learning_signals"] = {
            "repair": [signal.as_dict() for signal in self.learning_executor.advisory_signals_for_repair(action=current_action, result=result)],
        }
        result["orchestration"] = pre_execution_orchestration
        learning_update = self.learning_executor.ingest_runtime_artifacts(
            action=current_action,
            result=result,
        )
        if learning_update["signals"]:
            self._append_runtime_event(
                event_type="runtime.learning.ingested",
                session_id=session_id,
                task_id=task_id,
                run_id=run_id,
                payload=learning_update,
            )
        evolution_update = self.evolution_executor.evaluate(
            learning_update=learning_update,
            orchestration_update=pre_execution_orchestration,
            result=result,
            goal=self.planning_executor.goal_for_plan(operational_plan),
        )
        result["evolution"] = evolution_update
        if evolution_update.get("opportunity") or evolution_update.get("proposal"):
            self._append_runtime_event(
                event_type="runtime.evolution.evaluated",
                session_id=session_id,
                task_id=task_id,
                run_id=run_id,
                payload=evolution_update,
            )
        return result

    @staticmethod
    def _result_from_coordination_trace(trace: dict[str, Any]) -> dict[str, Any] | None:
        decisions = trace.get("decisions", []) if isinstance(trace, dict) else []
        for decision in decisions:
            if not isinstance(decision, dict):
                continue
            if str(decision.get("specialist_type", "")).strip() != "executor":
                continue
            result = decision.get("result")
            if isinstance(result, dict):
                return dict(result)
        return None

    @staticmethod
    def _attach_self_repair_metadata(result: dict[str, Any], self_repair_outcome: Any | None) -> dict[str, Any]:
        if self_repair_outcome is None:
            return result
        enriched = dict(result)
        enriched["self_repair"] = self_repair_outcome.as_dict()
        enriched["repair_receipt"] = self_repair_outcome.receipt.as_dict()
        return enriched

    @staticmethod
    def _count_failure_recurrence(
        *,
        action: dict[str, Any],
        result: dict[str, Any],
        step_results: list[dict[str, Any]],
        attempt_number: int,
    ) -> int:
        error_payload = result.get("error_payload", {}) if isinstance(result.get("error_payload"), dict) else {}
        kind = str(error_payload.get("kind", "")).strip()
        tool = str(action.get("selected_tool", "")).strip()
        recurrence = attempt_number
        for prior in step_results:
            if not isinstance(prior, dict):
                continue
            prior_action = prior.get("action", {}) if isinstance(prior.get("action"), dict) else {}
            prior_error = prior.get("error_payload", {}) if isinstance(prior.get("error_payload"), dict) else {}
            if str(prior_action.get("selected_tool", "")).strip() == tool and str(prior_error.get("kind", "")).strip() == kind:
                recurrence += 1
        return recurrence

    def _critic_outcome_review(
        self,
        *,
        action: dict[str, Any],
        result: dict[str, Any],
        evaluation: dict[str, Any],
        attempt_index: int,
        max_attempts: int,
    ) -> dict[str, Any]:
        if not self._runtime_critic_enabled():
            return {
                "invoked": False,
                "decision": "approve",
                "reason_code": "critic_disabled",
            }

        if result.get("ok") and evaluation.get("decision") == "continue":
            return {
                "invoked": True,
                "decision": "approve",
                "reason_code": "result_grounded",
                "attempt_index": attempt_index,
                "max_attempts": max_attempts,
            }

        if action.get("selected_tool") == "write_file":
            return {
                "invoked": True,
                "decision": "stop",
                "reason_code": "write_path_needs_operator",
                "attempt_index": attempt_index,
                "max_attempts": max_attempts,
            }

        if attempt_index < max_attempts:
            evaluation["decision"] = "retry_same_step"
            evaluation["reason_code"] = "critic_retry"
            return {
                "invoked": True,
                "decision": "retry",
                "reason_code": "critic_retry",
                "attempt_index": attempt_index,
                "max_attempts": max_attempts,
            }

        if evaluation.get("decision") == "revise_plan":
            return {
                "invoked": True,
                "decision": "revise",
                "reason_code": "critic_revision",
                "attempt_index": attempt_index,
                "max_attempts": max_attempts,
            }

        evaluation["decision"] = "stop_failed"
        evaluation["reason_code"] = "critic_stop"
        return {
            "invoked": True,
            "decision": "stop",
            "reason_code": "critic_stop",
            "attempt_index": attempt_index,
            "max_attempts": max_attempts,
        }

    def _append_runtime_event(
        self,
        *,
        event_type: str,
        session_id: str,
        task_id: str,
        run_id: str,
        payload: dict[str, Any],
    ) -> None:
        log_dir = self.paths.root / ".logs" / "fusion-runtime"
        log_dir.mkdir(parents=True, exist_ok=True)
        entry = {
            "timestamp": self._utc_now(),
            "event_type": event_type,
            "session_id": session_id,
            "task_id": task_id,
            "run_id": run_id,
            **payload,
        }
        self._append_jsonl(log_dir / "execution-audit.jsonl", entry)

    def _record_learning_memory(
        self,
        *,
        session_id: str,
        task_id: str,
        run_id: str,
        message: str,
        outcome: str,
        tool_family: str,
        lesson: str,
        trigger: str,
        metadata: dict[str, Any],
    ) -> None:
        learning_path = self.paths.root / ".logs" / "fusion-runtime" / "execution-learning-memory.json"
        learning_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            current = json.loads(learning_path.read_text(encoding="utf-8"))
        except Exception:
            current = {"entries": []}
        entry = {
            "entry_id": f"{task_id}:{run_id}:{len(current.get('entries', [])) + 1}",
            "session_id": session_id,
            "task_id": task_id,
            "run_id": run_id,
            "archetype": self._predict_intent(message),
            "strategy_type": "execution_review",
            "outcome": outcome,
            "lesson": lesson,
            "confidence": 0.75 if outcome == "success" else 0.9,
            "tool_family": tool_family,
            "trigger": trigger,
            "transcript_ref": {"session_id": session_id, "run_id": run_id},
            "metadata": metadata,
            "success_count": 1 if outcome == "success" else 0,
            "failure_count": 1 if outcome == "failure" else 0,
            "avoidance_count": 1 if outcome == "failure_avoidance" else 0,
            "ranking_score": 2.5 if outcome == "success" else 1.2 if outcome == "failure_avoidance" else -1.0,
            "updated_at": self._utc_now(),
        }
        current["entries"] = [entry] + [item for item in current.get("entries", []) if item.get("entry_id") != entry["entry_id"]]
        learning_path.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")
        self._append_runtime_event(
            event_type="runtime.learning_memory.updated",
            session_id=session_id,
            task_id=task_id,
            run_id=run_id,
            payload={"entry": entry},
        )

    def _reflect_on_run(
        self,
        *,
        message: str,
        step_results: list[dict[str, Any]],
        task_id: str,
        run_id: str,
        session_id: str,
        plan_hierarchy: dict[str, Any] | None,
        learning_guidance: object,
        policy_summary: object,
        branch_state: dict[str, Any] | None,
        cooperative_plan: dict[str, Any] | None,
    ) -> dict[str, Any]:
        failures = [item for item in step_results if not item.get("ok")]
        if not failures and not plan_hierarchy and not branch_state:
            return {"invoked": False, "reason_code": "reflection_not_required"}
        summary_parts = []
        if isinstance(plan_hierarchy, dict):
            summary_parts.append(
                f"Executou {len(plan_hierarchy.get('subgoals', []))} subobjetivos sob a meta principal."
            )
        if failures:
            summary_parts.append(
                f"Falhas observadas em {', '.join(str(item.get('selected_tool', 'tool')) for item in failures)}."
            )
        if isinstance(learning_guidance, list) and learning_guidance:
            summary_parts.append(f"Licao reaproveitada: {learning_guidance[0].get('lesson', '')}")
        if isinstance(policy_summary, list) and policy_summary:
            blocked = [item for item in policy_summary if item.get('policy_decision', {}).get('decision') == 'stop']
            if blocked:
                summary_parts.append("A politica bloqueou parte da execucao por seguranca.")
        if isinstance(branch_state, dict) and branch_state.get("winner_branch_id"):
            summary_parts.append(f"Branch vencedor: {branch_state.get('winner_branch_id')}.")
        if isinstance(cooperative_plan, dict):
            summary_parts.append(
                f"Cooperacao registrada com {len(cooperative_plan.get('contributions', []))} contribuicoes."
            )
        return {
            "invoked": True,
            "reason_code": "hierarchical_review" if plan_hierarchy else "execution_quality_review",
            "summary": " ".join(part for part in summary_parts if part).strip(),
            "update_learning": bool(failures or plan_hierarchy or branch_state),
            "message_preview": message[:120],
        }

    def _write_run_summary(
        self,
        *,
        session_id: str,
        task_id: str,
        run_id: str,
        message: str,
        step_results: list[dict[str, Any]],
        plan_kind: str,
        plan_hierarchy: dict[str, Any] | None,
        reflection: dict[str, Any],
        branch_state: dict[str, Any] | None,
        cooperative_plan: dict[str, Any] | None,
        simulation_summary: dict[str, Any] | None,
        strategy_suggestions: object,
        fusion_summary: dict[str, Any] | None,
        policy_summary: object,
        execution_tree: dict[str, Any] | None,
        negotiation_summary: dict[str, Any] | None,
        strategy_optimization: dict[str, Any] | None,
        supervision: dict[str, Any] | None,
        execution_state: dict[str, Any] | None,
        repository_analysis: dict[str, Any] | None = None,
        engineering_data: dict[str, Any] | None = None,
    ) -> None:
        run_summary_path = self.paths.root / ".logs" / "fusion-runtime" / "run-summaries.jsonl"
        summary = {
            "timestamp": self._utc_now(),
            "event_type": "runtime.run.summary",
            "session_id": session_id,
            "task_id": task_id,
            "run_id": run_id,
            "message": message,
            "plan_kind": plan_kind,
            "hierarchy": plan_hierarchy,
            "reflection": reflection,
            "branches": branch_state,
            "execution_tree": execution_tree,
            "cooperation": cooperative_plan,
            "negotiation": negotiation_summary,
            "simulation": simulation_summary,
            "strategy_usage": strategy_suggestions if isinstance(strategy_suggestions, list) else [],
            "strategy_optimization": strategy_optimization,
            "repository_analysis": repository_analysis or {},
            "engineering": engineering_data or {},
            "fusion": fusion_summary,
            "policy_summary": policy_summary if isinstance(policy_summary, list) else [],
            "supervision": supervision,
            "execution_state": execution_state,
            "status": "completed" if step_results and all(item.get("ok") for item in step_results) else "blocked",
            "steps": [
                {
                    "step_id": item.get("action", {}).get("step_id") if isinstance(item.get("action"), dict) else item.get("step_id"),
                    "goal_id": (
                        item.get("action", {}).get("execution_context", {}).get("goal_id")
                        if isinstance(item.get("action"), dict)
                        else None
                    ),
                    "branch_id": (
                        item.get("action", {}).get("execution_context", {}).get("branch_id")
                        if isinstance(item.get("action"), dict)
                        else item.get("branch_id")
                    ),
                    "selected_tool": item.get("selected_tool"),
                    "ok": bool(item.get("ok")),
                }
                for item in step_results
            ],
        }
        self._append_jsonl(run_summary_path, summary)

    @staticmethod
    def _build_fusion_summary(
        step_results: list[dict[str, Any]],
        cooperative_plan: dict[str, Any] | None,
        branch_state: dict[str, Any] | None,
        strategy_suggestions: object,
    ) -> dict[str, Any]:
        contributions = []
        for item in step_results:
            action = item.get("action", {}) if isinstance(item, dict) else {}
            contributions.append(
                {
                    "step_id": action.get("step_id") or item.get("step_id"),
                    "specialist_id": action.get("selected_agent") or item.get("selected_agent"),
                    "branch_id": action.get("execution_context", {}).get("branch_id"),
                    "goal_id": action.get("execution_context", {}).get("goal_id"),
                    "ok": bool(item.get("ok")),
                }
            )
        branch_ids = {item.get("branch_id") for item in contributions if item.get("branch_id")}
        return {
            "contribution_count": len(contributions),
            "specialist_ids": sorted({item.get("specialist_id") for item in contributions if item.get("specialist_id")}),
            "branch_count": len(branch_ids),
            "winner_branch_id": branch_state.get("winner_branch_id") if isinstance(branch_state, dict) else None,
            "strategy_count": len(strategy_suggestions) if isinstance(strategy_suggestions, list) else 0,
            "cooperative_mode": cooperative_plan.get("mode") if isinstance(cooperative_plan, dict) else "single-specialist",
        }

    @staticmethod
    def _collect_engineering_data(
        engineering_data: dict[str, Any],
        step_results: list[dict[str, Any]],
    ) -> dict[str, Any]:
        data = dict(engineering_data or {})
        for item in step_results:
            payload = item.get("result_payload", {}) if isinstance(item, dict) else {}
            tool = str(item.get("selected_tool") or "")
            if tool == "autonomous_debug_loop":
                data["patch_history"] = payload.get("patch_history", [])
                data["patch_sets"] = payload.get("patch_sets", [])
                data["debug_iterations"] = payload.get("iterations", [])
                data["test_results"] = payload.get("test_results", {})
                data["verification_summary"] = payload.get("verification_summary", {})
                if isinstance(payload.get("workspace_state"), dict):
                    data["workspace_state"] = payload.get("workspace_state")
            elif tool == "filesystem_write" and isinstance(payload.get("patch"), dict):
                existing = list(data.get("patch_history", []))
                existing.append({"patch": payload.get("patch"), "review": payload.get("review", {})})
                data["patch_history"] = existing
            elif tool == "filesystem_patch_set" and isinstance(payload.get("patch_set"), dict):
                patch_sets = list(data.get("patch_sets", []))
                patch_sets.append(payload.get("patch_set"))
                data["patch_sets"] = patch_sets
            elif tool == "test_runner" and isinstance(payload, dict):
                data["test_results"] = payload
            elif tool == "verification_runner" and isinstance(payload, dict):
                data["verification_summary"] = payload
        return data

    @staticmethod
    def _finalize_engineering_data(
        *,
        message: str,
        engineering_data: dict[str, Any],
        step_results: list[dict[str, Any]],
    ) -> dict[str, Any]:
        data = dict(engineering_data or {})
        milestone_plan = data.get("milestone_plan", {})
        milestone_state = MilestoneManager(milestone_plan).update_from_step_results(
            data.get("milestone_state", {}),
            step_results,
        ) if isinstance(milestone_plan, dict) and milestone_plan else data.get("milestone_state", {})
        data["milestone_state"] = milestone_state or {}
        verification_summary = data.get("verification_summary", {})
        if not verification_summary and isinstance(data.get("test_results"), dict) and data.get("test_results"):
            verification_summary = {
                "ok": True,
                "verification_modes": ["test-runner"],
                "runs": [{"mode": "test-runner", "status": "passed", "result": data.get("test_results", {})}],
                "merge_readiness": "ready",
            }
        data["verification_summary"] = verification_summary or {}
        data["pr_summary"] = build_pr_summary(
            message=message,
            milestone_state=data.get("milestone_state", {}),
            patch_sets=data.get("patch_sets", []),
            verification_summary=data.get("verification_summary", {}),
            repository_analysis=data.get("repository_analysis", {}),
            impact_analysis=data.get("repo_impact_analysis", {}),
        )
        return data

    @staticmethod
    def _synthesize_runtime_response(step_results: list[dict[str, Any]], fallback_response: str) -> str:
        read_results = [
            result for result in step_results
            if result.get("ok") and result.get("selected_tool") == "read_file"
        ]
        if read_results:
            return summarize_action_result(read_results[-1]).strip()

        successful_parts = [
            summarize_action_result(result)
            for result in step_results
            if result.get("ok")
        ]
        failure = next((result for result in step_results if not result.get("ok")), None)
        body = "\n\n".join(part for part in successful_parts if part).strip()
        if failure:
            failure_text = summarize_action_result(failure).strip()
            if body:
                return f"{body}\n\n{failure_text}".strip()
            return failure_text or fallback_response
        return body or fallback_response

    @staticmethod
    def _apply_memory_hints(memory_store: dict[str, object], memory_hints: object) -> None:
        if not isinstance(memory_hints, dict):
            return
        user = memory_store.setdefault("user", {})
        if not isinstance(user, dict):
            return
        if isinstance(memory_hints.get("new_name"), str) and memory_hints["new_name"].strip():
            user["nome"] = memory_hints["new_name"].strip()
        if isinstance(memory_hints.get("new_work"), str) and memory_hints["new_work"].strip():
            user["trabalho"] = memory_hints["new_work"].strip()

    @staticmethod
    def _apply_result_memory_updates(memory_store: dict[str, object], step_results: list[dict[str, Any]]) -> None:
        user = memory_store.setdefault("user", {})
        if not isinstance(user, dict):
            return

        for result in step_results:
            payload = result.get("result_payload", {}) if isinstance(result, dict) else {}
            file_payload = payload.get("file", {}) if isinstance(payload, dict) else {}
            file_path = file_payload.get("filePath")
            if isinstance(file_path, str) and file_path.strip():
                user["ultimo_arquivo"] = file_path.strip()

    def _sync_runtime_memory_store(
        self,
        session_id: str,
        memory_store: dict[str, object],
        step_results: list[dict[str, Any]],
    ) -> None:
        runtime_store_path = self.paths.root / ".logs" / "fusion-runtime" / "runtime-memory-store.json"
        runtime_store_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            current = json.loads(runtime_store_path.read_text(encoding="utf-8"))
        except Exception:
            current = {"sessions": {}}

        sessions = current.setdefault("sessions", {})
        session_memory = sessions.setdefault(
            session_id,
            {
                "session": {},
                "working": {},
                "persistent": {},
                "semantic": {"candidates": []},
            },
        )

        user = memory_store.get("user", {})
        if isinstance(user, dict):
            persistent = session_memory.setdefault("persistent", {})
            if isinstance(user.get("nome"), str) and user["nome"].strip():
                persistent["nome"] = user["nome"].strip()
            if isinstance(user.get("trabalho"), str) and user["trabalho"].strip():
                persistent["trabalho"] = user["trabalho"].strip()

        recent_artifacts: list[dict[str, str]] = []
        for result in step_results:
            payload = result.get("result_payload", {}) if isinstance(result, dict) else {}
            file_payload = payload.get("file", {}) if isinstance(payload, dict) else {}
            file_path = file_payload.get("filePath")
            if isinstance(file_path, str) and file_path.strip():
                normalized_path = self._normalize_runtime_artifact_path(file_path.strip())
                recent_artifacts.append(
                    {
                        "kind": "file",
                        "path": normalized_path,
                        "preview": str(file_payload.get("content", ""))[:200],
                    }
                )

        working = session_memory.setdefault("working", {})
        if recent_artifacts:
            working["last_artifact"] = recent_artifacts[0]
            working["recent_artifacts"] = (recent_artifacts + list(working.get("recent_artifacts", [])))[:12]
        working["updated_at"] = self._utc_now()

        session_memory.setdefault("session", {})["updated_at"] = self._utc_now()

        try:
            runtime_store_path.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            return

    def _append_runtime_execution_logs(
        self,
        *,
        session_id: str,
        message: str,
        action: dict[str, Any],
        result: dict[str, Any],
        task_id: str,
        run_id: str,
        provider: dict[str, Any] | str,
        intent: str,
        delegates: list[Any],
        specialists: list[Any],
        plan_kind: str,
        semantic_retrieval: object,
        plan_hierarchy: dict[str, Any] | None = None,
    ) -> None:
        log_dir = self.paths.root / ".logs" / "fusion-runtime"
        log_dir.mkdir(parents=True, exist_ok=True)

        transcript_entry = {
            "timestamp": self._utc_now(),
            "event_type": "runtime.step",
            "session_id": session_id,
            "task_id": task_id,
            "run_id": run_id,
            "message": message,
            "step_id": action.get("step_id"),
            "selected_tool": action.get("selected_tool"),
            "selected_agent": action.get("selected_agent"),
            "goal_id": action.get("execution_context", {}).get("goal_id"),
            "parent_goal_id": action.get("execution_context", {}).get("parent_goal_id"),
            "branch_id": action.get("execution_context", {}).get("branch_id"),
            "shared_goal_id": action.get("execution_context", {}).get("shared_goal_id"),
            "ok": bool(result.get("ok")),
            "result": result.get("result_payload"),
            "error": result.get("error_payload"),
            "evaluation": result.get("evaluation"),
            "correction_events": result.get("correction_events", []),
            "plan_kind": plan_kind,
        }
        audit_entry = {
            "timestamp": self._utc_now(),
            "event_type": "runtime.step.audit",
            "intent": intent or "execution",
            "complexity": action.get("execution_context", {}).get("complexity", "unknown"),
            "strategy": action.get("strategy", "real_execution"),
            "selected_tool": action.get("selected_tool"),
            "permission_requirement": action.get("permission_requirement"),
            "provider": provider.get("name") if isinstance(provider, dict) else str(provider or "unknown"),
            "delegates": delegates if isinstance(delegates, list) else [],
            "session_id": session_id,
            "task_id": task_id,
            "run_id": run_id,
            "plan_kind": plan_kind,
            "plan_hierarchy": plan_hierarchy if isinstance(plan_hierarchy, dict) else None,
            "delegated_specialists": specialists if isinstance(specialists, list) else [],
            "semantic_retrieval": semantic_retrieval if isinstance(semantic_retrieval, list) else [],
            "branch_id": action.get("execution_context", {}).get("branch_id"),
            "shared_goal_id": action.get("execution_context", {}).get("shared_goal_id"),
            "step_results": [
                {
                    "ok": bool(result.get("ok")),
                    "step_id": action.get("step_id"),
                    "selected_tool": action.get("selected_tool"),
                    "selected_agent": action.get("selected_agent"),
                    "goal_id": action.get("execution_context", {}).get("goal_id"),
                    "branch_id": action.get("execution_context", {}).get("branch_id"),
                    "evaluation": result.get("evaluation"),
                    "correction_events": result.get("correction_events", []),
                }
            ],
        }

        self._append_jsonl(log_dir / "runtime-transcript.jsonl", transcript_entry)
        self._append_jsonl(log_dir / "execution-audit.jsonl", audit_entry)

    @staticmethod
    def _sanitize_jsonl_file(path: Path) -> None:
        if not path.exists():
            return
        try:
            valid_lines: list[str] = []
            changed = False
            for raw_line in path.read_text(encoding="utf-8").splitlines():
                if not raw_line.strip():
                    changed = True
                    continue
                try:
                    json.loads(raw_line)
                except Exception:
                    changed = True
                    continue
                valid_lines.append(raw_line)
            if changed:
                payload = "\n".join(valid_lines)
                if payload:
                    payload += "\n"
                path.write_text(payload, encoding="utf-8")
        except Exception:
            return

    @staticmethod
    def _append_jsonl(path: Path, entry: dict[str, Any]) -> None:
        try:
            BrainOrchestrator._sanitize_jsonl_file(path)
            with path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(entry, ensure_ascii=False))
                handle.write("\n")
        except Exception:
            return

    @staticmethod
    def _utc_now() -> str:
        from datetime import datetime, timezone

        return datetime.now(timezone.utc).isoformat()

    def _normalize_runtime_artifact_path(self, raw_path: str) -> str:
        candidate = raw_path.replace("\\\\?\\", "")
        lower_candidate = candidate.lower().replace("/", "\\")
        marker = "\\project\\"
        if marker in lower_candidate:
            index = lower_candidate.rfind(marker)
            return candidate[index + len(marker):]
        try:
            return str(Path(candidate).resolve().relative_to(self.paths.root.resolve()))
        except Exception:
            return candidate

    @staticmethod
    def _evaluate_step(
        action: dict[str, Any],
        result: dict[str, Any],
        *,
        attempt_index: int,
        attempts: int,
    ) -> dict[str, Any]:
        if result.get("ok"):
            return {
                "decision": "continue",
                "reason_code": "step_succeeded",
                "attempt_index": attempt_index,
                "max_attempts": attempts,
            }

        message = str(result.get("error_payload", {}).get("message", ""))
        kind = str(result.get("error_payload", {}).get("kind", ""))
        if kind in {
            "permission_denied",
            "preflight_failed",
            "risk_above_policy_ceiling",
            "critical_risk_blocked",
            "high_risk_blocked",
        }:
            decision = "stop_blocked"
            reason_code = kind
        elif kind == "verification_failed":
            decision = "stop_failed"
            reason_code = "verification_failed"
        elif "cannot find" in message.lower() or "nao pode encontrar" in message.lower():
            decision = "revise_plan"
            reason_code = "path_not_found"
        elif attempt_index < attempts:
            decision = "retry_same_step"
            reason_code = "transient_failure"
        else:
            decision = "stop_failed"
            reason_code = kind or "step_failed"

        return {
            "decision": decision,
            "reason_code": reason_code,
            "attempt_index": attempt_index,
            "max_attempts": attempts,
        }

    @staticmethod
    def _revise_action_from_context(
        action: dict[str, Any],
        step_results: list[dict[str, Any]],
        semantic_retrieval: object,
    ) -> dict[str, Any] | None:
        if action.get("selected_tool") != "read_file":
            return None

        semantic_matches = semantic_retrieval if isinstance(semantic_retrieval, list) else []
        for match in semantic_matches:
            candidate_path = match.get("path")
            if isinstance(candidate_path, str) and candidate_path.strip():
                revised = dict(action)
                revised["tool_arguments"] = {
                    **dict(action.get("tool_arguments", {}) or {}),
                    "path": candidate_path.strip(),
                }
                return revised

        for result in reversed(step_results):
            payload = result.get("result_payload", {}) if isinstance(result, dict) else {}
            filenames = payload.get("filenames", []) if isinstance(payload, dict) else []
            if isinstance(filenames, list) and filenames:
                revised = dict(action)
                revised["tool_arguments"] = {
                    **dict(action.get("tool_arguments", {}) or {}),
                    "path": str(filenames[0]),
                }
                return revised
        return None

    def _write_checkpoint(
        self,
        *,
        run_id: str,
        task_id: str,
        session_id: str,
        message: str,
        actions: list[dict[str, Any]],
        next_step_index: int,
        completed_steps: list[dict[str, Any]],
        plan_graph: dict[str, Any] | None,
        plan_hierarchy: dict[str, Any] | None,
        plan_signature: str,
        status: str,
        branch_state: dict[str, Any] | None,
        simulation_summary: dict[str, Any] | None,
        cooperative_plan: dict[str, Any] | None,
        strategy_suggestions: object,
        policy_summary: object = None,
        execution_tree: dict[str, Any] | None = None,
        negotiation_summary: dict[str, Any] | None = None,
        strategy_optimization: dict[str, Any] | None = None,
        supervision: dict[str, Any] | None = None,
        repository_analysis: dict[str, Any] | None = None,
        engineering_data: dict[str, Any] | None = None,
    ) -> None:
        self._session_service.write_checkpoint(
            run_id=run_id,
            task_id=task_id,
            session_id=session_id,
            message=message,
            actions=actions,
            next_step_index=next_step_index,
            completed_steps=completed_steps,
            plan_graph=plan_graph,
            plan_hierarchy=plan_hierarchy,
            plan_signature=plan_signature,
            status=status,
            branch_state=branch_state,
            simulation_summary=simulation_summary,
            cooperative_plan=cooperative_plan,
            strategy_suggestions=strategy_suggestions,
            policy_summary=policy_summary,
            execution_tree=execution_tree,
            negotiation_summary=negotiation_summary,
            strategy_optimization=strategy_optimization,
            supervision=supervision,
            repository_analysis=repository_analysis,
            engineering_data=engineering_data,
        )

    def resume_run(self, run_id: str) -> dict[str, Any]:
        validation = self.checkpoint_store.validate(
            run_id,
            stale_after_minutes=self._runtime_stale_checkpoint_minutes(),
        )
        checkpoint = validation.get("payload", {})
        if not validation.get("ok"):
            reason = "stale_checkpoint" if validation.get("stale") else "checkpoint_signature_mismatch"
            self._append_runtime_event(
                event_type="runtime.checkpoint.resume_blocked",
                session_id=str(checkpoint.get("session_id", DEFAULT_SESSION_ID)),
                task_id=str(checkpoint.get("task_id", "")),
                run_id=run_id,
                payload={"reason_code": reason},
            )
            return {
                "status": "blocked",
                "response": "",
                "run_id": run_id,
                "task_id": checkpoint.get("task_id"),
                "error": reason,
                "step_results": [],
            }

        operational_plan = self.planning_executor.store.find_plan(
            session_id=str(checkpoint.get("session_id", DEFAULT_SESSION_ID)),
            task_id=str(checkpoint.get("task_id", "")),
            run_id=run_id,
        )
        resume_decision = self.planning_executor.resume_decision(operational_plan)
        if resume_decision is not None:
            self._append_runtime_event(
                event_type="runtime.planning.resume_decision",
                session_id=str(checkpoint.get("session_id", DEFAULT_SESSION_ID)),
                task_id=str(checkpoint.get("task_id", "")),
                run_id=run_id,
                payload=resume_decision.as_dict(),
            )
            if resume_decision.decision.value == "manual_intervention_required":
                return {
                    "status": "blocked",
                    "response": "",
                    "run_id": run_id,
                    "task_id": checkpoint.get("task_id"),
                    "error": resume_decision.reason_code,
                    "step_results": [],
                }

        remaining_actions = checkpoint.get("remaining_actions", [])
        if not isinstance(remaining_actions, list) or not remaining_actions:
            return {
                "status": checkpoint.get("status", "completed"),
                "response": "",
                "run_id": run_id,
                "task_id": checkpoint.get("task_id"),
                "step_results": [],
            }

        step_results = self._execute_runtime_actions(
            session_id=str(checkpoint.get("session_id", DEFAULT_SESSION_ID)),
            message=str(checkpoint.get("message", "")),
            actions=remaining_actions,
            task_id=str(checkpoint.get("task_id", "")),
            run_id=run_id,
            provider="resume-runtime",
            intent="execution",
            delegation={},
            critic_review={},
            plan_kind=str((checkpoint.get("plan_graph") or {}).get("mode", "linear")),
            plan_graph=checkpoint.get("plan_graph"),
            semantic_retrieval=[],
            plan_hierarchy=checkpoint.get("plan_hierarchy"),
            learning_guidance=[],
            policy_summary=[],
            branch_plan=checkpoint.get("branch_state"),
            simulation_summary=checkpoint.get("simulation_summary"),
            cooperative_plan=checkpoint.get("cooperative_plan"),
            strategy_suggestions=checkpoint.get("strategy_suggestions"),
            execution_tree=checkpoint.get("execution_tree"),
            negotiation_summary=checkpoint.get("negotiation_summary"),
            strategy_optimization=checkpoint.get("strategy_optimization"),
            repository_analysis=checkpoint.get("repository_analysis"),
            repo_impact_analysis=(checkpoint.get("engineering_data") or {}).get("repo_impact_analysis"),
            verification_plan=(checkpoint.get("engineering_data") or {}).get("verification_plan"),
            verification_selection=(checkpoint.get("engineering_data") or {}).get("verification_selection"),
            milestone_plan=(checkpoint.get("engineering_data") or {}).get("milestone_plan"),
            engineering_review=(checkpoint.get("engineering_data") or {}).get("engineering_review"),
            engineering_workflow=(checkpoint.get("engineering_data") or {}).get("engineering_workflow"),
            start_index=0,
            operator_control_enabled=True,
        )
        return {
            "status": "completed" if step_results and all(item.get("ok") for item in step_results) else "blocked",
            "response": self._synthesize_runtime_response(step_results, ""),
            "run_id": run_id,
            "task_id": checkpoint.get("task_id"),
            "step_results": step_results,
        }

    @staticmethod
    def summarize_history(history: object) -> str:
        if not isinstance(history, list) or len(history) <= 4:
            return ""

        summary_parts: list[str] = []
        for item in history[-4:]:
            if not isinstance(item, dict):
                continue
            role = "Usuario" if item.get("role") == "user" else "Assistente"
            content = str(item.get("content", "")).strip()
            if content:
                summary_parts.append(f"{role}: {content}")
        return "\n".join(summary_parts)

    @staticmethod
    def _merge_recent_history(
        transcript_history: list[dict[str, str]],
        memory_history: list[dict[str, str]],
        history_limit: int,
    ) -> list[dict[str, str]]:
        if transcript_history:
            return transcript_history[-history_limit:]
        return memory_history[-history_limit:]

    @staticmethod
    def _normalize_text(value: str) -> str:
        normalized = re.sub(r"\s+", " ", value.strip().lower())
        return re.sub(r"[?.!,:;]+$", "", normalized).strip()

    def _clean_extracted_name(self, raw_name: str) -> str:
        name = raw_name.strip()
        if not name:
            return ""
        name = re.split(r"\s+e\s+|,|\.", name, maxsplit=1, flags=re.IGNORECASE)[0].strip()
        if len(name) < 2:
            return ""

        invalid_tokens = {"gosto", "prefiro", "quero"}
        normalized = self._normalize_text(name)
        if any(token in normalized.split() for token in invalid_tokens):
            return ""
        return name

    def _extract_user_learning(self, memory_store: dict[str, object], message: str) -> None:
        user = memory_store.setdefault("user", {})
        if not isinstance(user, dict):
            user = {"nome": "", "preferencias": []}
            memory_store["user"] = user

        preferencias = user.get("preferencias", [])
        if not isinstance(preferencias, list):
            preferencias = []
            user["preferencias"] = preferencias

        nome_match = re.search(
            r"\bmeu nome [ée]\s+([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\s'-]{1,60})",
            message,
            flags=re.IGNORECASE,
        )
        if nome_match:
            cleaned_name = self._clean_extracted_name(nome_match.group(1).strip(" .,!?:;"))
            if cleaned_name:
                user["nome"] = cleaned_name

        sou_match = re.search(
            r"\beu sou\s+([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\s'-]{1,60})",
            message,
            flags=re.IGNORECASE,
        )
        if sou_match and not str(user.get("nome", "")).strip():
            possible_identity = self._clean_extracted_name(sou_match.group(1).strip(" .,!?:;"))
            if possible_identity and "um " not in possible_identity.lower() and "uma " not in possible_identity.lower():
                user["nome"] = possible_identity

        pref_match = re.search(r"\bprefiro\s+(.+)$", message, flags=re.IGNORECASE)
        if pref_match:
            preference = pref_match.group(1).strip(" .,!?:;")
            if preference:
                existing = {str(item).lower(): item for item in preferencias}
                if preference.lower() not in existing:
                    preferencias.append(preference)
                user["preferencias"] = preferencias

    def _answer_from_memory(self, memory_store: dict[str, object], message: str) -> str:
        user = memory_store.get("user", {})
        if not isinstance(user, dict):
            return ""

        normalized = self._normalize_text(message)
        nome = str(user.get("nome", "")).strip()
        if normalized in {
            "qual meu nome",
            "qual e meu nome",
            "qual é meu nome",
            "quem sou eu",
            "quem eu sou",
        }:
            if nome:
                return f"Seu nome é {nome}."
            return "Ainda nao sei seu nome."
        return ""

    def _predict_intent(self, message: str) -> str:
        lowered = self._normalize_text(message)
        if any(term in lowered for term in ("devo", " qual e melhor", " o que fazer", " ou ")):
            return "decision"
        if any(term in lowered for term in ("dinheiro", "negocio", "renda", "ganhar dinheiro")):
            return "dinheiro"
        if any(term in lowered for term in ("aprender", "programacao", "por onde comeco", "por onde começo")):
            return "aprendizado"
        if any(term in lowered for term in ("como funciona", "o que e", "o que é", "explique")):
            return "explicacao"
        if any(term in lowered for term in ("quem e voce", "quem é você", "como voce responde")):
            return "pessoal"
        return "conversa"

    def _weighted_capabilities(
        self,
        capabilities: list[dict[str, str]],
        strategy_state: dict[str, Any],
    ) -> list[dict[str, str]]:
        weights = strategy_state.get("capability_weights", {})
        if not isinstance(weights, dict):
            weights = {}
        return sorted(
            capabilities,
            key=lambda item: float(weights.get(str(item.get("name", "")), 1.0)),
            reverse=True,
        )

    def _weighted_capability_names(
        self,
        capabilities: list[str],
        strategy_state: dict[str, Any],
    ) -> list[str]:
        weights = strategy_state.get("capability_weights", {})
        if not isinstance(weights, dict):
            weights = {}
        return sorted(
            [item for item in capabilities if str(item).strip()],
            key=lambda item: float(weights.get(item, 1.0)),
            reverse=True,
        )
