from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from brain.evolution.evaluator import Evaluator
from brain.evolution.strategy_updater import StrategyUpdater
from brain.memory.hybrid import HybridMemory
from brain.memory.store import (
    DEFAULT_HISTORY_LIMIT,
    append_history,
    load_memory_store,
    save_memory_store,
)
from brain.registry import describe_agents, describe_capabilities, recommend_capabilities
from brain.runtime.checkpoint_store import CheckpointStore
from brain.runtime.session_store import SessionStore
from brain.runtime.rust_executor_bridge import execute_action, summarize_action_result
from brain.runtime.transcript_store import TranscriptStore
from brain.swarm.swarm_orchestrator import SwarmOrchestrator


SAFE_FALLBACK_RESPONSE = "Nao consegui processar isso ainda, mas estou aprendendo."
SUBPROCESS_TIMEOUT_SECONDS = 60
DEFAULT_SESSION_ID = "python-session"


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
    def __init__(self, paths: BrainPaths) -> None:
        self.paths = paths
        self.hybrid_memory = HybridMemory(paths.memory_dir)
        self.transcript_store = TranscriptStore(paths.transcripts_dir)
        self.checkpoint_store = CheckpointStore(paths.root)
        self.session_store = SessionStore(paths.sessions_dir)
        self.swarm_orchestrator = SwarmOrchestrator(paths.swarm_log)
        self.evaluator = Evaluator()
        self.strategy_updater = StrategyUpdater(paths.evolution_dir)

    def run(self, message: str) -> str:
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
            return SAFE_FALLBACK_RESPONSE

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
        suggested_capabilities = self._weighted_capability_names(
            recommend_capabilities(message),
            strategy_state,
        )
        predicted_intent = self._predict_intent(message)
        summary = self.summarize_history(memory_store.get("history", []))
        direct_response = self._answer_from_memory(memory_store, message)

        swarm_result: dict[str, Any] = {
            "response": direct_response,
            "intent": predicted_intent,
            "delegates": [],
            "agent_trace": [],
            "memory_signal": {},
        }

        if not direct_response:
            swarm_result = asyncio.run(
                self.swarm_orchestrator.run(
                    message=message,
                    session_id=session_id,
                    memory_store=memory_store,
                    history=memory_store.get("history", []),
                    summary=summary,
                    capabilities=available_capabilities,
                    executor=lambda payload: self._async_node_execution(
                        message=message,
                        memory_store=memory_store,
                        available_capabilities=available_capabilities,
                        session_id=session_id,
                        swarm_payload=payload,
                    ),
                )
            )

        response = str(swarm_result.get("response", "")).strip() or SAFE_FALLBACK_RESPONSE

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
    ) -> str:
        return self._call_node_query_engine(
            message=message,
            memory_store=memory_store,
            available_capabilities=available_capabilities,
            session_id=session_id,
            extra_session={
                "swarm_request": swarm_payload,
            },
        )

    def _session_id(self) -> str:
        configured = os.getenv("AI_SESSION_ID", "").strip()
        return configured or DEFAULT_SESSION_ID

    def _resolve_node_bin(self) -> str | None:
        configured = os.getenv("NODE_BIN", "").strip()
        if configured:
            return configured
        return shutil.which("node")

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
        node_bin = self._resolve_node_bin()
        if not node_bin or not self.paths.js_runner.exists():
            return ""

        session_payload = self.session_store.load(session_id)
        session_payload["executor_bridge"] = "python-rust"
        session_payload["runtime_mode"] = os.getenv("OMINI_EXECUTION_MODE", "auto")
        if extra_session:
            session_payload.update(extra_session)

        payload = json.dumps(
            {
                "message": message,
                "memory": memory_store.get("user", {}),
                "history": memory_store.get("history", []),
                "summary": self.summarize_history(memory_store.get("history", [])),
                "capabilities": available_capabilities,
                "session": session_payload,
            },
            ensure_ascii=False,
        )

        try:
            completed = subprocess.run(
                [node_bin, str(self.paths.js_runner), payload],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=SUBPROCESS_TIMEOUT_SECONDS,
                check=False,
                cwd=str(self.paths.root),
            )
        except Exception:
            return ""

        if completed.returncode != 0:
            return ""
        stdout = (completed.stdout or "").strip()
        if not stdout:
            return ""

        try:
            parsed = json.loads(stdout)
        except json.JSONDecodeError:
            return stdout

        execution_request = parsed.get("execution_request")
        if not isinstance(execution_request, dict):
            response = parsed.get("response")
            return str(response).strip() if isinstance(response, str) else stdout

        actions = execution_request.get("actions", [])
        if not isinstance(actions, list) or not actions:
            response = parsed.get("response", "")
            return str(response).strip() if isinstance(response, str) else ""

        task_id = str(execution_request.get("task_id", f"task-{session_id}"))
        run_id = str(execution_request.get("run_id", f"run-{session_id}"))
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
        start_index: int = 0,
    ) -> list[dict[str, Any]]:
        max_steps = min(len(actions), int(os.getenv("OMINI_MAX_STEPS", "6") or "6"))
        step_results: list[dict[str, Any]] = []
        critic_review = critic_review or {}
        graph_state = self._clone_plan_graph(plan_graph)
        plan_signature = self._plan_signature(actions, graph_state)
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
        )
        executed_steps = 0
        if plan_kind == "graph" and isinstance(graph_state, dict):
            while executed_steps < max_steps:
                ready_parallel, ready_sequential = self._graph_ready_groups(graph_state)
                if not ready_parallel and not ready_sequential:
                    break

                batch_nodes = ready_parallel[: self._runtime_max_parallel_reads()] if ready_parallel else ready_sequential[:1]
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

                batch_results = self._execute_action_batch(
                    actions=[action for action in batch_actions if isinstance(action, dict)],
                    step_results=step_results,
                    semantic_retrieval=semantic_retrieval,
                    learning_guidance=learning_guidance,
                    allow_parallel=len(batch_actions) > 1,
                )

                for action, result in zip(batch_actions, batch_results):
                    executed_steps += 1
                    step_results.append(result)
                    graph_state = self._mark_graph_outcome(graph_state, action, result)
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
                )
                if step_results and not step_results[-1].get("ok"):
                    break
        else:
            for index, action in enumerate(actions[start_index:max_steps], start=start_index):
                if not isinstance(action, dict):
                    continue

                result = self._execute_single_action(
                    action=action,
                    step_results=step_results,
                    semantic_retrieval=semantic_retrieval,
                    learning_guidance=learning_guidance,
                )
                executed_steps += 1
                step_results.append(result)

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
                )

                if not result.get("ok"):
                    break

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
            },
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
        )
        return step_results

    @staticmethod
    def _clone_plan_graph(plan_graph: dict[str, Any] | None) -> dict[str, Any] | None:
        if not isinstance(plan_graph, dict):
            return None
        try:
            return json.loads(json.dumps(plan_graph))
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
    ) -> list[dict[str, Any]]:
        if not allow_parallel or len(actions) <= 1:
            return [
                self._execute_single_action(
                    action=action,
                    step_results=step_results,
                    semantic_retrieval=semantic_retrieval,
                    learning_guidance=learning_guidance,
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
        learning_guidance: object = None,
    ) -> dict[str, Any]:
        attempts = int(action.get("retry_policy", {}).get("max_attempts", 1) or 1)
        attempts = min(attempts, self._runtime_correction_depth() + 1)
        final_result: dict[str, Any] | None = None
        correction_events: list[dict[str, Any]] = []
        current_action = dict(action)
        policy_decision = dict(current_action.get("policy_decision", {}) or {})

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
            return blocked_result

        for attempt_number in range(1, attempts + 1):
            final_result = execute_action(
                self.paths.root,
                current_action,
                timeout_seconds=max(1, int(current_action.get("timeout_ms", SUBPROCESS_TIMEOUT_SECONDS * 1000) / 1000)),
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
        result["evaluation"] = correction_events[-1] if correction_events else {
            "decision": "stop_failed",
            "reason_code": "missing_result",
        }
        result["correction_events"] = correction_events
        return result

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
    ) -> dict[str, Any]:
        failures = [item for item in step_results if not item.get("ok")]
        if not failures and not plan_hierarchy:
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
        return {
            "invoked": True,
            "reason_code": "hierarchical_review" if plan_hierarchy else "execution_quality_review",
            "summary": " ".join(part for part in summary_parts if part).strip(),
            "update_learning": bool(failures or plan_hierarchy),
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
            "status": "completed" if step_results and all(item.get("ok") for item in step_results) else "blocked",
            "steps": [
                {
                    "step_id": item.get("action", {}).get("step_id") if isinstance(item.get("action"), dict) else item.get("step_id"),
                    "goal_id": (
                        item.get("action", {}).get("execution_context", {}).get("goal_id")
                        if isinstance(item.get("action"), dict)
                        else None
                    ),
                    "selected_tool": item.get("selected_tool"),
                    "ok": bool(item.get("ok")),
                }
                for item in step_results
            ],
        }
        self._append_jsonl(run_summary_path, summary)

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
            "step_results": [
                {
                    "ok": bool(result.get("ok")),
                    "step_id": action.get("step_id"),
                    "selected_tool": action.get("selected_tool"),
                    "selected_agent": action.get("selected_agent"),
                    "goal_id": action.get("execution_context", {}).get("goal_id"),
                    "evaluation": result.get("evaluation"),
                    "correction_events": result.get("correction_events", []),
                }
            ],
        }

        self._append_jsonl(log_dir / "runtime-transcript.jsonl", transcript_entry)
        self._append_jsonl(log_dir / "execution-audit.jsonl", audit_entry)

    @staticmethod
    def _append_jsonl(path: Path, entry: dict[str, Any]) -> None:
        try:
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
        if kind == "permission_denied":
            decision = "stop_blocked"
            reason_code = "permission_denied"
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
    ) -> None:
        remaining_actions = actions[next_step_index:] if next_step_index < len(actions) else []
        self.checkpoint_store.save(
            run_id,
            {
                "task_id": task_id,
                "session_id": session_id,
                "message": message,
                "status": status,
                "next_step_index": next_step_index,
                "completed_steps": completed_steps,
                "remaining_actions": remaining_actions,
                "total_actions": len(actions),
                "plan_graph": plan_graph,
                "plan_hierarchy": plan_hierarchy,
                "plan_signature": plan_signature,
            },
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
            start_index=0,
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
