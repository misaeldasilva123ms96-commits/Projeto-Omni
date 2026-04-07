from __future__ import annotations

import json
import os
import subprocess
import sys
import shutil
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4


PROJECT_ROOT = Path(__file__).resolve().parents[2]

sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.orchestrator import BrainOrchestrator, BrainPaths  # noqa: E402
from brain.runtime.debug_loop_controller import DebugLoopController  # noqa: E402
from brain.runtime.patch_generator import apply_patch, build_patch, review_patch_risk  # noqa: E402
from brain.runtime.patch_set_manager import apply_patch_set, build_patch_set, rollback_patch_set  # noqa: E402
from brain.runtime.rust_executor_bridge import execute_action  # noqa: E402
from brain.runtime.task_service import TaskService  # noqa: E402
from brain.runtime.workspace_manager import WorkspaceManager  # noqa: E402


class Phase2RuntimeTest(unittest.TestCase):
    def run_main(self, prompt: str, session_id: str) -> str:
        env = os.environ.copy()
        env["AI_SESSION_ID"] = session_id
        env["BASE_DIR"] = str(PROJECT_ROOT)
        env["PYTHON_BASE_DIR"] = str(PROJECT_ROOT / "backend" / "python")
        completed = subprocess.run(
            ["python", "backend/python/main.py", prompt],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=180,
            env=env,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        return completed.stdout.strip()

    def build_orchestrator(self) -> BrainOrchestrator:
        os.environ["BASE_DIR"] = str(PROJECT_ROOT)
        os.environ["PYTHON_BASE_DIR"] = str(PROJECT_ROOT / "backend" / "python")
        return BrainOrchestrator(BrainPaths.from_entrypoint(PROJECT_ROOT / "backend" / "python" / "brain" / "runtime" / "main.py"))

    def make_temp_python_repo(self) -> Path:
        base_temp = PROJECT_ROOT / ".phase9-temp"
        base_temp.mkdir(parents=True, exist_ok=True)
        temp_root = base_temp / f"omini-phase9-{uuid4().hex[:8]}"
        shutil.rmtree(temp_root, ignore_errors=True)
        temp_root.mkdir(parents=True, exist_ok=True)
        (temp_root / "mathlib").mkdir(parents=True, exist_ok=True)
        (temp_root / "tests").mkdir(parents=True, exist_ok=True)
        (temp_root / "mathlib" / "__init__.py").write_text("", encoding="utf-8")
        (temp_root / "mathlib" / "ops.py").write_text(
            "def add(a, b):\n    return a - b\n",
            encoding="utf-8",
        )
        (temp_root / "tests" / "test_ops.py").write_text(
            "import unittest\nfrom mathlib.ops import add\n\n\nclass OpsTest(unittest.TestCase):\n    def test_add(self):\n        self.assertEqual(add(2, 3), 5)\n\n\nif __name__ == '__main__':\n    unittest.main()\n",
            encoding="utf-8",
        )
        return temp_root

    def test_real_query_to_execution_path_reads_package(self) -> None:
        output = self.run_main("leia package.json", "phase2-read")
        self.assertIn('"name": "omini-runner"', output)

    def test_memory_update_and_retrieval_work_in_live_path(self) -> None:
        learn_output = self.run_main(
            "meu nome Ã© Misael e eu trabalho com inteligÃªncia artificial",
            "phase2-memory",
        )
        normalized_learn_output = learn_output.lower()
        self.assertTrue(
            "registrar seu nome" in normalized_learn_output or "seu nome" in normalized_learn_output,
            learn_output,
        )

        recall_output = self.run_main("qual Ã© meu nome?", "phase2-memory")
        self.assertIn("Misael", recall_output)

    def test_multistep_execution_loop_runs_more_than_one_step(self) -> None:
        list_result = execute_action(
            PROJECT_ROOT,
            {
                "action_id": "multi-1",
                "step_id": "multi-list",
                "strategy": "real_execution",
                "selected_tool": "glob_search",
                "selected_agent": "researcher_agent",
                "permission_requirement": "allow_read_only",
                "approval_state": "approved",
                "execution_context": {"project_root": "../..", "runtime_mode": "python-rust-cargo"},
                "tool_arguments": {"pattern": "**/*", "path": "."},
                "transcript_link": {"session_id": "phase3-multistep"},
                "memory_update_hints": {},
            },
            timeout_seconds=60,
        )
        read_result = execute_action(
            PROJECT_ROOT,
            {
                "action_id": "multi-2",
                "step_id": "multi-read",
                "strategy": "real_execution",
                "selected_tool": "read_file",
                "selected_agent": "researcher_agent",
                "permission_requirement": "allow_read_only",
                "approval_state": "approved",
                "execution_context": {"project_root": "../..", "runtime_mode": "python-rust-cargo"},
                "tool_arguments": {"path": "package.json", "limit": 120},
                "transcript_link": {"session_id": "phase3-multistep"},
                "memory_update_hints": {},
            },
            timeout_seconds=60,
        )
        self.assertTrue(list_result.get("ok"))
        self.assertTrue(read_result.get("ok"))
        self.assertIn("omini-runner", json.dumps(read_result.get("result_payload", {})))

    def test_permission_failure_inside_multistep_stops_safely(self) -> None:
        blocked_path = PROJECT_ROOT / "tests" / "fusion" / "blocked-output.txt"
        if blocked_path.exists():
            blocked_path.unlink()

        list_result = execute_action(
            PROJECT_ROOT,
            {
                "action_id": "phase3-list",
                "step_id": "phase3-list",
                "strategy": "real_execution",
                "selected_tool": "glob_search",
                "selected_agent": "researcher_agent",
                "permission_requirement": "allow_read_only",
                "approval_state": "approved",
                "execution_context": {"project_root": "../..", "runtime_mode": "python-rust-cargo"},
                "tool_arguments": {"pattern": "**/*", "path": "."},
                "transcript_link": {"session_id": "phase3-permission"},
                "memory_update_hints": {},
            },
            timeout_seconds=60,
        )
        write_result = execute_action(
            PROJECT_ROOT,
            {
                "action_id": "phase3-write",
                "step_id": "phase3-write",
                "strategy": "real_execution",
                "selected_tool": "write_file",
                "selected_agent": "coder_agent",
                "permission_requirement": "explicit_approval_required",
                "approval_state": "pending",
                "execution_context": {"project_root": "../..", "runtime_mode": "python-rust-cargo"},
                "tool_arguments": {"path": "tests/fusion/blocked-output.txt", "content": "blocked"},
                "transcript_link": {"session_id": "phase3-permission"},
                "memory_update_hints": {},
            },
            timeout_seconds=60,
        )
        self.assertTrue(list_result.get("ok"))
        self.assertEqual(write_result.get("error_payload", {}).get("kind"), "permission_denied")
        self.assertFalse(blocked_path.exists())

    def test_memory_retrieval_affects_followup_plan(self) -> None:
        output = self.run_main("leia package.json", "phase3-memory-artifact")
        self.assertIn('"name": "omini-runner"', output)

    def test_semantic_retrieval_affects_runtime_context_selection(self) -> None:
        self.run_main("leia package.json", "phase4-semantic")
        output = self.run_main("analise o arquivo sobre schema validation", "phase4-semantic")
        self.assertTrue(
            '"name": "omini-runner"' in output or "Hybrid AI Agent Runtime" in output,
            output,
        )

    def test_permission_enforcement_blocks_write_without_approval(self) -> None:
        result = execute_action(
            PROJECT_ROOT,
            {
                "action_id": "perm-1",
                "step_id": "perm-step",
                "strategy": "real_execution",
                "selected_tool": "write_file",
                "selected_agent": "coder_agent",
                "permission_requirement": "explicit_approval_required",
                "approval_state": "pending",
                "execution_context": {"project_root": "../..", "runtime_mode": "python-rust-cargo"},
                "tool_arguments": {"path": "tests/fusion/blocked-output.txt", "content": "blocked"},
                "transcript_link": {"session_id": "perm-session"},
                "memory_update_hints": {},
            },
            timeout_seconds=60,
        )
        self.assertFalse(result.get("ok"))
        self.assertEqual(result.get("error_payload", {}).get("kind"), "permission_denied")

    def test_runtime_transcript_and_audit_are_written(self) -> None:
        self.run_main("leia package.json", "phase2-audit")

        runtime_transcript = PROJECT_ROOT / ".logs" / "fusion-runtime" / "runtime-transcript.jsonl"
        execution_audit = PROJECT_ROOT / ".logs" / "fusion-runtime" / "execution-audit.jsonl"

        self.assertTrue(runtime_transcript.exists())
        self.assertTrue(execution_audit.exists())

        transcript_entries = [json.loads(line) for line in runtime_transcript.read_text(encoding="utf-8").splitlines() if line.strip()]
        audit_entries = [json.loads(line) for line in execution_audit.read_text(encoding="utf-8").splitlines() if line.strip()]
        transcript_tail = next(entry for entry in reversed(transcript_entries) if entry.get("event_type") == "runtime.step")
        audit_tail = next(entry for entry in reversed(audit_entries) if entry.get("event_type") == "runtime.step.audit")

        self.assertIn(transcript_tail.get("selected_tool"), {"read_file", "glob_search"})
        self.assertIn(audit_tail.get("step_results", [{}])[0].get("selected_tool"), {"read_file", "glob_search"})
        self.assertIn("step_results", audit_tail)

    def test_checkpoint_creation_and_resume_work(self) -> None:
        previous_max_steps = os.environ.get("OMINI_MAX_STEPS")
        try:
            os.environ["OMINI_MAX_STEPS"] = "1"
            orchestrator = self.build_orchestrator()
            os.environ["AI_SESSION_ID"] = "phase4-resume"
            run_id = "run-phase4-checkpoint"
            task_id = "task-phase4-checkpoint"
            actions = [
                {
                    "action_id": "phase4-list",
                    "step_id": "phase4-list",
                    "strategy": "real_execution",
                    "selected_tool": "glob_search",
                    "selected_agent": "researcher_agent",
                    "permission_requirement": "allow_read_only",
                    "approval_state": "approved",
                    "execution_context": {"project_root": "../..", "runtime_mode": "python-rust-cargo"},
                    "tool_arguments": {"pattern": "**/*", "path": "."},
                    "transcript_link": {"session_id": "phase4-resume"},
                    "memory_update_hints": {},
                },
                {
                    "action_id": "phase4-read",
                    "step_id": "phase4-read",
                    "strategy": "real_execution",
                    "selected_tool": "read_file",
                    "selected_agent": "researcher_agent",
                    "permission_requirement": "allow_read_only",
                    "approval_state": "approved",
                    "execution_context": {"project_root": "../..", "runtime_mode": "python-rust-cargo"},
                    "tool_arguments": {"path": "package.json", "limit": 120},
                    "transcript_link": {"session_id": "phase4-resume"},
                    "memory_update_hints": {},
                },
            ]
            partial_results = orchestrator._execute_runtime_actions(
                session_id="phase4-resume",
                message="liste os arquivos e leia package.json",
                actions=actions,
                task_id=task_id,
                run_id=run_id,
                provider="test-runtime",
                intent="execution",
                delegation={},
                semantic_retrieval=[],
            )
            self.assertEqual(len(partial_results), 1)
            self.assertTrue(partial_results[0].get("ok"))

            checkpoint_dir = PROJECT_ROOT / ".logs" / "fusion-runtime" / "checkpoints"
            checkpoint_file = checkpoint_dir / f"{run_id}.json"
            self.assertTrue(checkpoint_file.exists())
            checkpoint_payload = json.loads(checkpoint_file.read_text(encoding="utf-8"))
            self.assertEqual(checkpoint_payload.get("status"), "blocked")
            self.assertGreater(len(checkpoint_payload.get("remaining_actions", [])), 0)

            resumed = orchestrator.resume_run(run_id)
            self.assertEqual(resumed.get("run_id"), run_id)
            self.assertIn('"name": "omini-runner"', resumed.get("response", ""))
        finally:
            os.environ.pop("AI_SESSION_ID", None)
            if previous_max_steps is None:
                os.environ.pop("OMINI_MAX_STEPS", None)
            else:
                os.environ["OMINI_MAX_STEPS"] = previous_max_steps

    def test_task_service_exposes_product_ready_boundaries(self) -> None:
        service = TaskService(PROJECT_ROOT / "backend" / "python" / "brain" / "runtime" / "main.py")
        executed = service.execute_task(
            user_id="user-phase4",
            session_id="service-session",
            message="leia package.json",
        )
        self.assertEqual(executed.get("status"), "completed")
        self.assertEqual(executed.get("user_id"), "user-phase4")
        self.assertEqual(executed.get("session_id"), "service-session")
        self.assertIn("task_id", executed)
        self.assertIn("links", executed)
        self.assertIn('"name": "omini-runner"', executed.get("response", ""))

    def test_observability_records_task_and_run_ids(self) -> None:
        self.run_main("leia package.json", "phase4-observability")
        execution_audit = PROJECT_ROOT / ".logs" / "fusion-runtime" / "execution-audit.jsonl"
        audit_tail = json.loads(execution_audit.read_text(encoding="utf-8").strip().splitlines()[-1])
        self.assertIn("event_type", audit_tail)
        self.assertIn("task_id", audit_tail)
        self.assertIn("run_id", audit_tail)

    def test_graph_plan_parallel_read_execution_path(self) -> None:
        orchestrator = self.build_orchestrator()
        run_id = "run-phase5-graph"
        actions = [
            {
                "action_id": "phase5-list",
                "step_id": "phase5-list",
                "strategy": "real_execution",
                "selected_tool": "glob_search",
                "selected_agent": "researcher_agent",
                "permission_requirement": "allow_read_only",
                "approval_state": "approved",
                "execution_context": {"project_root": "../..", "runtime_mode": "python-rust-cargo"},
                "tool_arguments": {"pattern": "**/*", "path": "."},
                "retry_policy": {"max_attempts": 1},
                "transcript_link": {"session_id": "phase5-graph"},
                "memory_update_hints": {},
            },
            {
                "action_id": "phase5-read",
                "step_id": "phase5-read",
                "strategy": "real_execution",
                "selected_tool": "read_file",
                "selected_agent": "researcher_agent",
                "permission_requirement": "allow_read_only",
                "approval_state": "approved",
                "execution_context": {"project_root": "../..", "runtime_mode": "python-rust-cargo"},
                "tool_arguments": {"path": "package.json", "limit": 40},
                "retry_policy": {"max_attempts": 1},
                "transcript_link": {"session_id": "phase5-graph"},
                "memory_update_hints": {},
            },
        ]
        plan_graph = {
            "version": 1,
            "mode": "parallel-read",
            "nodes": [
                {"node_id": "phase5-list", "step_id": "phase5-list", "depends_on": [], "parallel_safe": True, "state": "pending"},
                {"node_id": "phase5-read", "step_id": "phase5-read", "depends_on": [], "parallel_safe": True, "state": "pending"},
            ],
        }
        results = orchestrator._execute_runtime_actions(
            session_id="phase5-graph",
            message='liste os arquivos e busque "name"',
            actions=actions,
            task_id="task-phase5-graph",
            run_id=run_id,
            provider="test-runtime",
            intent="execution",
            delegation={"delegates": ["task_planner", "researcher_agent"], "specialists": ["researcher_agent"]},
            critic_review={"invoked": True, "decision": "approve"},
            plan_kind="graph",
            plan_graph=plan_graph,
            semantic_retrieval=[],
        )
        self.assertEqual(len(results), 2)
        self.assertTrue(all(item.get("ok") for item in results))

    def test_critic_influences_failure_handling(self) -> None:
        orchestrator = self.build_orchestrator()
        results = orchestrator._execute_runtime_actions(
            session_id="phase5-critic",
            message="leia um arquivo inexistente",
            actions=[
                {
                    "action_id": "phase5-missing",
                    "step_id": "phase5-missing",
                    "strategy": "real_execution",
                    "selected_tool": "read_file",
                    "selected_agent": "researcher_agent",
                    "permission_requirement": "allow_read_only",
                    "approval_state": "approved",
                    "execution_context": {"project_root": "../..", "runtime_mode": "python-rust-cargo"},
                    "tool_arguments": {"path": "missing-file.txt", "limit": 10},
                    "retry_policy": {"max_attempts": 2},
                    "transcript_link": {"session_id": "phase5-critic"},
                    "memory_update_hints": {},
                }
            ],
            task_id="task-phase5-critic",
            run_id="run-phase5-critic",
            provider="test-runtime",
            intent="execution",
            delegation={},
            critic_review={"invoked": True, "decision": "approve"},
            plan_kind="linear",
            plan_graph=None,
            semantic_retrieval=[],
        )
        self.assertEqual(len(results), 1)
        self.assertFalse(results[0].get("ok"))
        self.assertIn("critic", results[0].get("evaluation", {}))

    def test_stale_checkpoint_detection_blocks_resume(self) -> None:
        orchestrator = self.build_orchestrator()
        run_id = "run-phase5-stale"
        orchestrator.checkpoint_store.save(
            run_id,
            {
                "task_id": "task-phase5-stale",
                "session_id": "phase5-stale",
                "message": "stale resume",
                "status": "blocked",
                "next_step_index": 0,
                "completed_steps": [],
                "remaining_actions": [],
                "total_actions": 0,
                "plan_signature": "stale-signature",
                "updated_at": (datetime.now(timezone.utc) - timedelta(hours=5)).isoformat(),
            },
        )
        resumed = orchestrator.resume_run(run_id)
        self.assertEqual(resumed.get("status"), "blocked")
        self.assertEqual(resumed.get("error"), "stale_checkpoint")

    def test_task_service_status_boundary(self) -> None:
        service = TaskService(PROJECT_ROOT / "backend" / "python" / "brain" / "runtime" / "main.py")
        run_id = "run-phase5-status"
        service.orchestrator.checkpoint_store.save(
            run_id,
            {
                "task_id": "task-phase5-status",
                "session_id": "service-session",
                "message": "status",
                "status": "running",
                "next_step_index": 1,
                "completed_steps": [],
                "remaining_actions": [],
                "total_actions": 3,
                "plan_signature": "status-signature",
            },
        )
        status = service.task_status(run_id=run_id)
        self.assertEqual(status.get("status"), "running")
        self.assertEqual(status.get("task_id"), "task-phase5-status")

    def test_observability_includes_parallel_and_critic_events(self) -> None:
        self.run_main('compare duas abordagens: liste os arquivos e busque "name"', "phase5-observability")
        execution_audit = PROJECT_ROOT / ".logs" / "fusion-runtime" / "execution-audit.jsonl"
        entries = [
            json.loads(line)
            for line in execution_audit.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        relevant = [entry for entry in entries if entry.get("session_id") == "phase5-observability"][-40:]
        event_types = {entry.get("event_type") for entry in relevant}
        self.assertIn("runtime.parallel.start", event_types)
        self.assertIn("runtime.step.audit", event_types)

    def test_hierarchical_plan_execution_and_learning_memory(self) -> None:
        orchestrator = self.build_orchestrator()
        run_id = "run-phase6-hierarchy"
        actions = [
            {
                "action_id": "phase6-list",
                "step_id": "phase6-list",
                "strategy": "real_execution",
                "selected_tool": "glob_search",
                "selected_agent": "researcher_agent",
                "permission_requirement": "allow_read_only",
                "approval_state": "approved",
                "policy_decision": {"decision": "allow", "reason_code": "policy_allows_execution"},
                "execution_context": {"project_root": "../..", "runtime_mode": "python-rust-cargo", "goal_id": "goal:inspect", "parent_goal_id": "goal:root"},
                "tool_arguments": {"pattern": "**/*", "path": "."},
                "retry_policy": {"max_attempts": 1},
                "transcript_link": {"session_id": "phase6-hierarchy"},
                "memory_update_hints": {},
            },
            {
                "action_id": "phase6-read",
                "step_id": "phase6-read",
                "strategy": "real_execution",
                "selected_tool": "read_file",
                "selected_agent": "researcher_agent",
                "permission_requirement": "allow_read_only",
                "approval_state": "approved",
                "policy_decision": {"decision": "allow", "reason_code": "policy_allows_execution"},
                "execution_context": {"project_root": "../..", "runtime_mode": "python-rust-cargo", "goal_id": "goal:synthesize", "parent_goal_id": "goal:root"},
                "tool_arguments": {"path": "package.json", "limit": 40},
                "retry_policy": {"max_attempts": 1},
                "transcript_link": {"session_id": "phase6-hierarchy"},
                "memory_update_hints": {},
            },
        ]
        plan_hierarchy = {
            "version": 1,
            "mode": "hierarchical",
            "root_goal_id": "goal:root",
            "subgoals": [
                {"goal_id": "goal:inspect", "parent_goal_id": "goal:root", "step_ids": ["phase6-list"]},
                {"goal_id": "goal:synthesize", "parent_goal_id": "goal:root", "step_ids": ["phase6-read"]},
            ],
        }
        results = orchestrator._execute_runtime_actions(
            session_id="phase6-hierarchy",
            message="liste os arquivos, depois leia package.json e analise por partes",
            actions=actions,
            task_id="task-phase6-hierarchy",
            run_id=run_id,
            provider="test-runtime",
            intent="analysis",
            delegation={"delegates": ["task_planner", "researcher_agent"], "specialists": ["researcher_agent", "reviewer_agent"]},
            critic_review={"invoked": True, "decision": "approve"},
            plan_kind="hierarchical",
            plan_graph={"version": 1, "mode": "hierarchical", "nodes": []},
            plan_hierarchy=plan_hierarchy,
            semantic_retrieval=[],
            learning_guidance=[{"lesson": "prefer read-only inspection first"}],
            policy_summary=[],
        )
        self.assertEqual(len(results), 2)
        self.assertTrue(all(item.get("ok") for item in results))

        learning_path = PROJECT_ROOT / ".logs" / "fusion-runtime" / "execution-learning-memory.json"
        self.assertTrue(learning_path.exists())
        learning_entries = json.loads(learning_path.read_text(encoding="utf-8")).get("entries", [])
        self.assertTrue(any(entry.get("run_id") == run_id for entry in learning_entries))

        checkpoint = orchestrator.checkpoint_store.load(run_id)
        self.assertEqual(checkpoint.get("plan_hierarchy", {}).get("root_goal_id"), "goal:root")
        self.assertIn("reflection_summary", checkpoint)

    def test_policy_stop_and_run_summary_are_operator_visible(self) -> None:
        orchestrator = self.build_orchestrator()
        run_id = "run-phase6-policy"
        results = orchestrator._execute_runtime_actions(
            session_id="phase6-policy",
            message="escreva no arquivo sem aprovacao",
            actions=[
                {
                    "action_id": "phase6-write",
                    "step_id": "phase6-write",
                    "strategy": "real_execution",
                    "selected_tool": "write_file",
                    "selected_agent": "coder_agent",
                    "permission_requirement": "explicit_approval_required",
                    "approval_state": "pending",
                    "policy_decision": {
                        "decision": "stop",
                        "reason_code": "missing_approval",
                        "operator_message": "A acao exige aprovacao explicita antes da execucao.",
                    },
                    "execution_context": {"project_root": "../..", "runtime_mode": "python-rust-cargo", "goal_id": "goal:root"},
                    "tool_arguments": {"path": "tests/fusion/blocked-output.txt", "content": "blocked"},
                    "retry_policy": {"max_attempts": 1},
                    "transcript_link": {"session_id": "phase6-policy"},
                    "memory_update_hints": {},
                }
            ],
            task_id="task-phase6-policy",
            run_id=run_id,
            provider="test-runtime",
            intent="execution",
            delegation={},
            critic_review={"invoked": True, "decision": "approve"},
            plan_kind="linear",
            plan_graph=None,
            plan_hierarchy=None,
            semantic_retrieval=[],
            learning_guidance=[],
            policy_summary=[{"step_id": "phase6-write", "policy_decision": {"decision": "stop", "reason_code": "missing_approval"}}],
        )
        self.assertEqual(len(results), 1)
        self.assertFalse(results[0].get("ok"))
        self.assertEqual(results[0].get("error_payload", {}).get("kind"), "policy_stop")

        task_service = TaskService(PROJECT_ROOT / "backend" / "python" / "brain" / "runtime" / "main.py")
        status = task_service.task_status(run_id=run_id)
        self.assertEqual(status.get("status"), "blocked")
        self.assertIn("operator_links", status)

        run_summary = PROJECT_ROOT / ".logs" / "fusion-runtime" / "run-summaries.jsonl"
        self.assertTrue(run_summary.exists())
        entries = [json.loads(line) for line in run_summary.read_text(encoding="utf-8").splitlines() if line.strip()]
        self.assertTrue(any(entry.get("run_id") == run_id for entry in entries))

    def test_branch_execution_simulation_and_operator_intelligence(self) -> None:
        orchestrator = self.build_orchestrator()
        run_id = "run-phase7-branches"
        actions = [
            {
                "action_id": "phase7-list",
                "step_id": "phase7-list",
                "strategy": "real_execution",
                "selected_tool": "glob_search",
                "selected_agent": "researcher_agent",
                "permission_requirement": "allow_read_only",
                "approval_state": "approved",
                "policy_decision": {"decision": "allow", "reason_code": "policy_allows_execution"},
                "execution_context": {"project_root": "../..", "runtime_mode": "python-rust-cargo", "goal_id": "goal:inspect", "branch_id": "branch:list-first", "shared_goal_id": "shared-goal:root"},
                "tool_arguments": {"pattern": "**/*", "path": "."},
                "retry_policy": {"max_attempts": 1},
                "transcript_link": {"session_id": "phase7-branches"},
                "memory_update_hints": {},
            },
            {
                "action_id": "phase7-read-a",
                "step_id": "phase7-read-a",
                "strategy": "real_execution",
                "selected_tool": "read_file",
                "selected_agent": "researcher_agent",
                "permission_requirement": "allow_read_only",
                "approval_state": "approved",
                "policy_decision": {"decision": "allow", "reason_code": "policy_allows_execution"},
                "execution_context": {"project_root": "../..", "runtime_mode": "python-rust-cargo", "goal_id": "goal:synthesize", "branch_id": "branch:list-first", "shared_goal_id": "shared-goal:root"},
                "tool_arguments": {"path": "package.json", "limit": 40},
                "retry_policy": {"max_attempts": 1},
                "transcript_link": {"session_id": "phase7-branches"},
                "memory_update_hints": {},
            },
            {
                "action_id": "phase7-grep",
                "step_id": "phase7-grep",
                "strategy": "real_execution",
                "selected_tool": "grep_search",
                "selected_agent": "researcher_agent",
                "permission_requirement": "allow_read_only",
                "approval_state": "approved",
                "policy_decision": {"decision": "allow", "reason_code": "policy_allows_execution"},
                "execution_context": {"project_root": "../..", "runtime_mode": "python-rust-cargo", "goal_id": "goal:inspect", "branch_id": "branch:search-first", "shared_goal_id": "shared-goal:root"},
                "tool_arguments": {"pattern": "name", "path": ".", "output_mode": "content", "head_limit": 10},
                "retry_policy": {"max_attempts": 1},
                "transcript_link": {"session_id": "phase7-branches"},
                "memory_update_hints": {},
            },
            {
                "action_id": "phase7-read-b",
                "step_id": "phase7-read-b",
                "strategy": "real_execution",
                "selected_tool": "read_file",
                "selected_agent": "researcher_agent",
                "permission_requirement": "allow_read_only",
                "approval_state": "approved",
                "policy_decision": {"decision": "allow", "reason_code": "policy_allows_execution"},
                "execution_context": {"project_root": "../..", "runtime_mode": "python-rust-cargo", "goal_id": "goal:synthesize", "branch_id": "branch:search-first", "shared_goal_id": "shared-goal:root"},
                "tool_arguments": {"path": "package.json", "limit": 20},
                "retry_policy": {"max_attempts": 1},
                "transcript_link": {"session_id": "phase7-branches"},
                "memory_update_hints": {},
            },
        ]
        plan_graph = {
            "version": 1,
            "mode": "branch-aware",
            "nodes": [
                {"node_id": "phase7-list", "step_id": "phase7-list", "depends_on": [], "parallel_safe": True, "state": "pending", "branch_id": "branch:list-first"},
                {"node_id": "phase7-read-a", "step_id": "phase7-read-a", "depends_on": [], "parallel_safe": True, "state": "pending", "branch_id": "branch:list-first"},
                {"node_id": "phase7-grep", "step_id": "phase7-grep", "depends_on": [], "parallel_safe": True, "state": "pending", "branch_id": "branch:search-first"},
                {"node_id": "phase7-read-b", "step_id": "phase7-read-b", "depends_on": [], "parallel_safe": True, "state": "pending", "branch_id": "branch:search-first"},
            ],
        }
        branch_plan = {
            "enabled": True,
            "merge_mode": "winner-selection",
            "max_branches": 2,
            "branches": [
                {"branch_id": "branch:list-first", "safe": True, "step_ids": ["phase7-list", "phase7-read-a"]},
                {"branch_id": "branch:search-first", "safe": True, "step_ids": ["phase7-grep", "phase7-read-b"]},
            ],
        }
        simulation_summary = {
            "invoked": True,
            "recommended_decision": "proceed",
            "summary": "Simulation approved bounded read-only branch exploration.",
        }
        cooperative_plan = {
            "shared_goal_id": "shared-goal:root",
            "mode": "cooperative-shared-goal",
            "contributions": [
                {"specialist_id": "task_planner", "role": "planner"},
                {"specialist_id": "researcher_agent", "role": "researcher"},
                {"specialist_id": "reviewer_agent", "role": "reviewer"},
            ],
        }
        strategy_suggestions = [{"strategy_type": "parallel_read_branching", "lesson": "Prefer safe parallel branches."}]

        results = orchestrator._execute_runtime_actions(
            session_id="phase7-branches",
            message='compare duas abordagens: liste os arquivos, busque "name" e analise package.json',
            actions=actions,
            task_id="task-phase7-branches",
            run_id=run_id,
            provider="test-runtime",
            intent="analysis",
            delegation={"delegates": ["task_planner", "researcher_agent", "reviewer_agent"], "specialists": ["researcher_agent", "reviewer_agent"]},
            critic_review={"invoked": True, "decision": "approve"},
            plan_kind="graph",
            plan_graph=plan_graph,
            branch_plan=branch_plan,
            simulation_summary=simulation_summary,
            cooperative_plan=cooperative_plan,
            semantic_retrieval=[],
            plan_hierarchy={"root_goal_id": "goal:root", "subgoals": [{"goal_id": "goal:inspect"}, {"goal_id": "goal:synthesize"}]},
            learning_guidance=[],
            strategy_suggestions=strategy_suggestions,
            policy_summary=[],
        )
        self.assertEqual(len(results), 4)
        self.assertTrue(all(item.get("ok") for item in results))
        checkpoint = orchestrator.checkpoint_store.load(run_id)
        self.assertEqual(checkpoint.get("branch_state", {}).get("winner_branch_id") in {"branch:list-first", "branch:search-first"}, True)
        self.assertIn("simulation_summary", checkpoint)
        self.assertIn("cooperative_plan", checkpoint)

        service = TaskService(PROJECT_ROOT / "backend" / "python" / "brain" / "runtime" / "main.py")
        branches = service.inspect_branches(run_id=run_id)
        self.assertIn("branch_state", branches)
        contributions = service.inspect_contributions(run_id=run_id)
        self.assertEqual(contributions.get("cooperative_plan", {}).get("mode"), "cooperative-shared-goal")
        intelligence = service.inspect_run_intelligence(run_id=run_id)
        self.assertEqual(intelligence.get("run_summary", {}).get("run_id"), run_id)
        self.assertIn("fusion", intelligence.get("run_summary", {}))

    def test_simulation_can_stop_execution_before_action(self) -> None:
        orchestrator = self.build_orchestrator()
        results = orchestrator._execute_runtime_actions(
            session_id="phase7-simulation-stop",
            message="escreva em arquivo sensivel sem aprovacao",
            actions=[
                {
                    "action_id": "phase7-write",
                    "step_id": "phase7-write",
                    "strategy": "real_execution",
                    "selected_tool": "write_file",
                    "selected_agent": "coder_agent",
                    "permission_requirement": "explicit_approval_required",
                    "approval_state": "pending",
                    "policy_decision": {"decision": "stop", "reason_code": "missing_approval", "operator_message": "Aprovacao necessaria."},
                    "execution_context": {"project_root": "../..", "runtime_mode": "python-rust-cargo"},
                    "tool_arguments": {"path": "tests/fusion/blocked-output.txt", "content": "blocked"},
                    "retry_policy": {"max_attempts": 1},
                    "transcript_link": {"session_id": "phase7-simulation-stop"},
                    "memory_update_hints": {},
                }
            ],
            task_id="task-phase7-simulation-stop",
            run_id="run-phase7-simulation-stop",
            provider="test-runtime",
            intent="execution",
            delegation={},
            critic_review={"invoked": True, "decision": "approve"},
            plan_kind="linear",
            plan_graph=None,
            branch_plan=None,
            simulation_summary={"invoked": True, "recommended_decision": "stop", "summary": "Simulation found blockers: write_requires_approval."},
            cooperative_plan=None,
            semantic_retrieval=[],
            plan_hierarchy=None,
            learning_guidance=[],
            strategy_suggestions=[],
            policy_summary=[{"step_id": "phase7-write", "policy_decision": {"decision": "stop"}}],
        )
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].get("error_payload", {}).get("kind"), "simulation_stop")

    def test_execution_tree_negotiation_and_operator_state(self) -> None:
        orchestrator = self.build_orchestrator()
        run_id = "run-phase8-tree"
        actions = [
            {
                "action_id": "phase8-list",
                "step_id": "phase8-list",
                "strategy": "real_execution",
                "selected_tool": "glob_search",
                "selected_agent": "researcher_agent",
                "permission_requirement": "allow_read_only",
                "approval_state": "approved",
                "policy_decision": {"decision": "allow", "reason_code": "policy_allows_execution"},
                "execution_context": {"project_root": "../..", "runtime_mode": "python-rust-cargo", "goal_id": "goal:inspect", "branch_id": "branch:list-first", "shared_goal_id": "shared-goal:root"},
                "tool_arguments": {"pattern": "**/*", "path": "."},
                "retry_policy": {"max_attempts": 1},
                "transcript_link": {"session_id": "phase8-tree"},
                "memory_update_hints": {},
            },
            {
                "action_id": "phase8-read",
                "step_id": "phase8-read",
                "strategy": "real_execution",
                "selected_tool": "read_file",
                "selected_agent": "researcher_agent",
                "permission_requirement": "allow_read_only",
                "approval_state": "approved",
                "policy_decision": {"decision": "allow", "reason_code": "policy_allows_execution"},
                "execution_context": {"project_root": "../..", "runtime_mode": "python-rust-cargo", "goal_id": "goal:synthesize", "branch_id": "branch:list-first", "shared_goal_id": "shared-goal:root"},
                "tool_arguments": {"path": "package.json", "limit": 40},
                "retry_policy": {"max_attempts": 1},
                "transcript_link": {"session_id": "phase8-tree"},
                "memory_update_hints": {},
            },
        ]
        execution_tree = {
            "version": 1,
            "root_node_id": "tree:root",
            "nodes": [
                {"node_id": "tree:root", "parent_id": None, "branch_id": None, "state": "pending", "retries": 0, "owner_agent": "master_orchestrator", "node_type": "goal", "children": ["tree:branch:list-first"]},
                {"node_id": "tree:branch:list-first", "parent_id": "tree:root", "branch_id": "branch:list-first", "state": "pending", "retries": 0, "owner_agent": "task_planner", "node_type": "branch", "children": ["tree:phase8-list", "tree:phase8-read"]},
                {"node_id": "tree:phase8-list", "parent_id": "tree:branch:list-first", "branch_id": "branch:list-first", "step_id": "phase8-list", "state": "pending", "retries": 0, "owner_agent": "researcher_agent", "node_type": "step", "children": []},
                {"node_id": "tree:phase8-read", "parent_id": "tree:branch:list-first", "branch_id": "branch:list-first", "step_id": "phase8-read", "state": "pending", "retries": 0, "owner_agent": "researcher_agent", "node_type": "step", "children": []},
            ],
        }
        negotiation_summary = {
            "invoked": True,
            "final_decision": "proceed",
            "disagreement_count": 1,
            "turns": [
                {"agent_id": "task_planner", "stance": "proposal"},
                {"agent_id": "critic_agent", "stance": "critic-approve"},
            ],
        }
        strategy_optimization = {
            "invoked": True,
            "preferred_plan_mode": "tree",
            "step_biases": ["prefer_read_only_first"],
        }
        results = orchestrator._execute_runtime_actions(
            session_id="phase8-tree",
            message='compare arquitetura e package.json por arvore',
            actions=actions,
            task_id="task-phase8-tree",
            run_id=run_id,
            provider="test-runtime",
            intent="analysis",
            delegation={"delegates": ["task_planner", "researcher_agent", "critic_agent"], "specialists": ["researcher_agent", "critic_agent"]},
            critic_review={"invoked": True, "decision": "approve"},
            plan_kind="graph",
            plan_graph={"version": 1, "mode": "tree", "nodes": []},
            branch_plan={"enabled": True, "max_branches": 1, "merge_mode": "winner-selection", "branches": [{"branch_id": "branch:list-first", "safe": True, "step_ids": ["phase8-list", "phase8-read"]}]},
            simulation_summary={"invoked": True, "recommended_decision": "proceed", "summary": "Safe to execute.", "estimated_cost": 2.0, "confidence_estimate": 0.82},
            cooperative_plan={"shared_goal_id": "shared-goal:root", "mode": "cooperative-shared-goal", "contributions": [{"specialist_id": "task_planner"}, {"specialist_id": "researcher_agent"}]},
            semantic_retrieval=[],
            plan_hierarchy={"root_goal_id": "goal:root", "subgoals": [{"goal_id": "goal:inspect"}, {"goal_id": "goal:synthesize"}]},
            learning_guidance=[],
            strategy_suggestions=[{"strategy_type": "parallel_read_branching", "lesson": "Prefer read-only first"}],
            execution_tree=execution_tree,
            negotiation_summary=negotiation_summary,
            strategy_optimization=strategy_optimization,
            policy_summary=[],
        )
        self.assertEqual(len(results), 2)
        self.assertTrue(all(item.get("ok") for item in results))
        checkpoint = orchestrator.checkpoint_store.load(run_id)
        self.assertIn("execution_tree", checkpoint)
        self.assertIn("negotiation_summary", checkpoint)
        self.assertIn("supervision", checkpoint)
        self.assertEqual(checkpoint.get("strategy_optimization", {}).get("preferred_plan_mode"), "tree")

        service = TaskService(PROJECT_ROOT / "backend" / "python" / "brain" / "runtime" / "main.py")
        tree_view = service.inspect_execution_state(run_id=run_id)
        self.assertIn("execution_tree", tree_view)
        negotiation_view = service.inspect_negotiation(run_id=run_id)
        self.assertEqual(negotiation_view.get("negotiation_summary", {}).get("final_decision"), "proceed")
        supervision_view = service.inspect_supervision(run_id=run_id)
        self.assertIn("supervision", supervision_view)
        intelligence = service.inspect_run_intelligence(run_id=run_id)
        self.assertIn("execution_state", intelligence.get("run_summary", {}))

    def test_supervision_stops_runaway_tree(self) -> None:
        orchestrator = self.build_orchestrator()
        actions = []
        tree_nodes = [{"node_id": "tree:root", "parent_id": None, "branch_id": None, "state": "pending", "retries": 0, "owner_agent": "master_orchestrator", "node_type": "goal", "children": []}]
        for index in range(30):
            step_id = f"phase8-runaway-{index}"
            actions.append(
                {
                    "action_id": step_id,
                    "step_id": step_id,
                    "strategy": "real_execution",
                    "selected_tool": "glob_search",
                    "selected_agent": "researcher_agent",
                    "permission_requirement": "allow_read_only",
                    "approval_state": "approved",
                    "policy_decision": {"decision": "allow", "reason_code": "policy_allows_execution"},
                    "execution_context": {"project_root": "../..", "runtime_mode": "python-rust-cargo"},
                    "tool_arguments": {"pattern": "**/*", "path": "."},
                    "retry_policy": {"max_attempts": 1},
                    "transcript_link": {"session_id": "phase8-runaway"},
                    "memory_update_hints": {},
                }
            )
            tree_nodes.append({"node_id": f"tree:{step_id}", "parent_id": "tree:root", "branch_id": None, "step_id": step_id, "state": "pending", "retries": 0, "owner_agent": "researcher_agent", "node_type": "step", "children": []})

        results = orchestrator._execute_runtime_actions(
            session_id="phase8-runaway",
            message="analise em arvore gigante",
            actions=actions,
            task_id="task-phase8-runaway",
            run_id="run-phase8-runaway",
            provider="test-runtime",
            intent="analysis",
            delegation={},
            critic_review={"invoked": True, "decision": "approve"},
            plan_kind="graph",
            plan_graph={"version": 1, "mode": "tree", "nodes": []},
            branch_plan=None,
            simulation_summary=None,
            cooperative_plan=None,
            semantic_retrieval=[],
            plan_hierarchy=None,
            learning_guidance=[],
            strategy_suggestions=[],
            execution_tree={"version": 1, "root_node_id": "tree:root", "nodes": tree_nodes},
            negotiation_summary={"invoked": True, "turns": []},
            strategy_optimization={},
            policy_summary=[],
        )
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].get("error_payload", {}).get("kind"), "supervision_stop")

    def test_patch_generation_produces_valid_diff(self) -> None:
        repo_root = self.make_temp_python_repo()
        patch = build_patch(
            workspace_root=repo_root,
            file_path="mathlib/ops.py",
            new_content="def add(a, b):\n    return a + b\n",
            confidence_score=0.91,
        )
        self.assertEqual(patch.get("file_path"), "mathlib/ops.py")
        self.assertIn("--- mathlib/ops.py", patch.get("patch_diff", ""))
        self.assertIn("+++ mathlib/ops.py", patch.get("patch_diff", ""))
        self.assertIn("+    return a + b", patch.get("patch_diff", ""))
        applied = apply_patch(workspace_root=repo_root, patch=patch)
        self.assertTrue(applied.get("ok"))
        self.assertIn("return a + b", (repo_root / "mathlib" / "ops.py").read_text(encoding="utf-8"))

    def test_workspace_isolation_snapshot_works(self) -> None:
        repo_root = self.make_temp_python_repo()
        manager = WorkspaceManager(repo_root)
        workspace = manager.create_task_workspace(run_id="phase9-workspace", source_root=repo_root)
        workspace_root = Path(workspace["workspace_root"])
        self.assertTrue((workspace_root / "mathlib" / "ops.py").exists())
        self.assertNotEqual(str(workspace_root), str(repo_root))
        snapshot = workspace.get("snapshot", {})
        self.assertGreater(snapshot.get("file_count", 0), 0)

    def test_code_review_detects_risky_patch(self) -> None:
        repo_root = self.make_temp_python_repo()
        patch = build_patch(
            workspace_root=repo_root,
            file_path=".env",
            new_content="SECRET=changed\n",
            confidence_score=0.2,
        )
        review = review_patch_risk(patch=patch)
        self.assertFalse(review.get("accepted"))
        self.assertIn("sensitive_or_generated_file", review.get("warnings", []))

    def test_autonomous_debug_loop_fixes_failing_test_case(self) -> None:
        repo_root = self.make_temp_python_repo()
        controller = DebugLoopController(repo_root)
        result = controller.run(
            task_message="corrija os testes com seguranca",
            test_command=[sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"],
            max_iterations=2,
            repository_analysis={
                "file_index": [
                    {"path": "mathlib/ops.py", "language": "python"},
                    {"path": "tests/test_ops.py", "language": "python"},
                ]
            },
        )
        self.assertEqual(result.get("status"), "success")
        self.assertGreater(len(result.get("patch_history", [])), 0)
        self.assertGreater(len(result.get("iterations", [])), 0)
        self.assertIn("return a + b", (repo_root / "mathlib" / "ops.py").read_text(encoding="utf-8"))

    def test_engineering_workflow_and_operator_inspection_are_persisted(self) -> None:
        repo_root = self.make_temp_python_repo()
        orchestrator = self.build_orchestrator()
        run_id = "run-phase9-engineering"
        repository_analysis = {
            "root": str(repo_root),
            "repository_map": {"entry_points": ["mathlib/ops.py"]},
            "file_index": [
                {"path": "mathlib/ops.py", "language": "python"},
                {"path": "tests/test_ops.py", "language": "python"},
            ],
        }
        results = orchestrator._execute_runtime_actions(
            session_id="phase9-engineering",
            message="corrija os testes do workspace temporario",
            actions=[
                {
                    "action_id": "phase9-debug",
                    "step_id": "phase9-debug",
                    "strategy": "engineering_execution",
                    "selected_tool": "autonomous_debug_loop",
                    "selected_agent": "coder_agent",
                    "permission_requirement": "explicit_approval_required",
                    "approval_state": "approved",
                    "policy_decision": {"decision": "allow", "reason_code": "policy_allows_execution"},
                    "execution_context": {"project_root": str(repo_root), "runtime_mode": "python-rust-cargo", "goal_id": "goal:engineering"},
                    "tool_arguments": {
                        "workspace_root": str(repo_root),
                        "task_message": "corrija os testes do workspace temporario",
                        "test_command": [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"],
                        "max_iterations": 2,
                        "repository_analysis": repository_analysis,
                    },
                    "retry_policy": {"max_attempts": 1},
                    "transcript_link": {"session_id": "phase9-engineering"},
                    "memory_update_hints": {},
                }
            ],
            task_id="task-phase9-engineering",
            run_id=run_id,
            provider="test-runtime",
            intent="engineering",
            delegation={"delegates": ["task_planner", "coder_agent", "reviewer_agent"], "specialists": ["coder_agent", "reviewer_agent"]},
            critic_review={"invoked": True, "decision": "approve"},
            plan_kind="hierarchical",
            plan_graph={"version": 1, "mode": "engineering", "nodes": []},
            semantic_retrieval=[],
            plan_hierarchy={"root_goal_id": "goal:engineering", "subgoals": [{"goal_id": "goal:repo"}, {"goal_id": "goal:debug"}]},
            learning_guidance=[],
            policy_summary=[],
            execution_tree={"version": 1, "root_node_id": "tree:root", "nodes": []},
            negotiation_summary={"invoked": True, "final_decision": "proceed", "turns": []},
            strategy_optimization={"invoked": True, "preferred_plan_mode": "tree"},
            repository_analysis=repository_analysis,
            engineering_review={"invoked": True, "risk_level": "medium"},
            engineering_workflow={"mode": "autonomous-debug"},
        )
        self.assertEqual(len(results), 1)
        self.assertTrue(results[0].get("ok"))
        payload = results[0].get("result_payload", {})
        self.assertEqual(payload.get("status"), "success")

        service = TaskService(PROJECT_ROOT / "backend" / "python" / "brain" / "runtime" / "main.py")
        repo_view = service.inspect_repository_analysis(run_id=run_id)
        self.assertEqual(repo_view.get("repository_analysis", {}).get("root"), str(repo_root))
        patch_view = service.inspect_patch_history(run_id=run_id)
        self.assertGreater(len(patch_view.get("patch_history", [])), 0)
        debug_view = service.inspect_debug_iterations(run_id=run_id)
        self.assertGreater(len(debug_view.get("debug_iterations", [])), 0)
        workspace_view = service.inspect_workspace_state(run_id=run_id)
        self.assertIn("workspace_state", workspace_view)

    def test_patch_set_apply_and_rollback_work_for_multi_file_changes(self) -> None:
        repo_root = self.make_temp_python_repo()
        patch_set = build_patch_set(
            workspace_root=repo_root,
            file_updates=[
                {
                    "file_path": "mathlib/ops.py",
                    "new_content": "def add(a, b):\n    return a + b\n",
                    "confidence_score": 0.9,
                },
                {
                    "file_path": "mathlib/__init__.py",
                    "new_content": "from .ops import add\n",
                    "confidence_score": 0.85,
                },
            ],
            dependency_notes=["mathlib exports add"],
            verification_plan={"verification_modes": ["targeted-tests"]},
        )
        applied = apply_patch_set(workspace_root=repo_root, patch_set=patch_set)
        self.assertTrue(applied.get("ok"))
        self.assertEqual(len(patch_set.get("affected_files", [])), 2)
        self.assertIn("return a + b", (repo_root / "mathlib" / "ops.py").read_text(encoding="utf-8"))
        rollback = rollback_patch_set(workspace_root=repo_root, patch_set=patch_set)
        self.assertTrue(rollback.get("ok"))
        self.assertIn("return a - b", (repo_root / "mathlib" / "ops.py").read_text(encoding="utf-8"))

    def test_large_task_checkpoint_and_operator_inspection_include_milestones_and_pr_summary(self) -> None:
        orchestrator = self.build_orchestrator()
        run_id = "run-phase10-large-task"
        repository_analysis = {
            "root": str(PROJECT_ROOT),
            "repository_map": {"entry_points": ["package.json"], "frameworks": ["react-vite", "python-runtime"]},
            "language_profile": {"dominant_language": "javascript"},
            "file_index": [
                {"path": "package.json", "language": "json"},
                {"path": "tests/fusion/fusion-brain.test.js", "language": "javascript"},
            ],
        }
        repo_impact_analysis = {
            "impact_map": {"likely_affected_modules": ["package.json"], "candidate_count": 1},
            "module_change_candidates": [{"path": "package.json", "language": "json", "score": 5}],
            "test_selection_candidates": [{"path": "tests/fusion/fusion-brain.test.js", "language": "javascript", "score": 2}],
            "integration_risk_summary": {"risk_level": "medium", "flags": ["hotspot-coupling"]},
        }
        verification_plan = {
            "verification_modes": ["targeted-tests", "dependency-health"],
            "targeted_tests": ["tests/fusion/fusion-brain.test.js"],
        }
        milestone_plan = {
            "milestone_tree": {
                "root_milestone_id": "milestone:analysis",
                "milestones": [
                    {"milestone_id": "milestone:analysis", "title": "Analyze", "step_ids": ["phase10-tree"], "state": "pending", "blockers": [], "progress": 0},
                    {"milestone_id": "milestone:verify", "title": "Verify", "step_ids": ["phase10-verify"], "state": "pending", "blockers": [], "progress": 0},
                ],
            }
        }
        results = orchestrator._execute_runtime_actions(
            session_id="phase10-large-task",
            message="planeje e valide uma mudanca grande no repositorio",
            actions=[
                {
                    "action_id": "phase10-tree",
                    "step_id": "phase10-tree",
                    "strategy": "engineering_execution",
                    "selected_tool": "directory_tree",
                    "selected_agent": "researcher_agent",
                    "permission_requirement": "allow_read_only",
                    "approval_state": "approved",
                    "policy_decision": {"decision": "allow", "reason_code": "policy_allows_execution"},
                    "execution_context": {"project_root": "../..", "runtime_mode": "python-rust-cargo", "goal_id": "goal:large-engineering"},
                    "tool_arguments": {"workspace_root": str(PROJECT_ROOT), "max_depth": 2},
                    "retry_policy": {"max_attempts": 1},
                    "transcript_link": {"session_id": "phase10-large-task"},
                    "memory_update_hints": {},
                    "milestone_id": "milestone:analysis",
                },
                {
                    "action_id": "phase10-verify",
                    "step_id": "phase10-verify",
                    "strategy": "engineering_execution",
                    "selected_tool": "verification_runner",
                    "selected_agent": "test_selection_specialist",
                    "permission_requirement": "allow_read_only",
                    "approval_state": "approved",
                    "policy_decision": {"decision": "allow", "reason_code": "policy_allows_execution"},
                    "execution_context": {"project_root": "../..", "runtime_mode": "python-rust-cargo", "goal_id": "goal:large-engineering"},
                    "tool_arguments": {"workspace_root": str(PROJECT_ROOT), "plan": verification_plan},
                    "retry_policy": {"max_attempts": 1},
                    "transcript_link": {"session_id": "phase10-large-task"},
                    "memory_update_hints": {},
                    "milestone_id": "milestone:verify",
                },
            ],
            task_id="task-phase10-large-task",
            run_id=run_id,
            provider="test-runtime",
            intent="engineering",
            delegation={"delegates": ["task_planner", "researcher_agent", "test_selection_specialist"], "specialists": ["researcher_agent", "test_selection_specialist"]},
            critic_review={"invoked": True, "decision": "approve"},
            plan_kind="hierarchical",
            plan_graph={"version": 1, "mode": "engineering", "nodes": []},
            semantic_retrieval=[],
            plan_hierarchy={"root_goal_id": "goal:large-engineering", "subgoals": [{"goal_id": "goal:analysis"}, {"goal_id": "goal:verification"}]},
            learning_guidance=[],
            policy_summary=[],
            execution_tree={"version": 1, "root_node_id": "tree:root", "nodes": []},
            negotiation_summary={"invoked": True, "final_decision": "proceed", "turns": []},
            strategy_optimization={"invoked": True, "preferred_plan_mode": "tree"},
            repository_analysis=repository_analysis,
            repo_impact_analysis=repo_impact_analysis,
            verification_plan=verification_plan,
            verification_selection={"targeted_tests": ["tests/fusion/fusion-brain.test.js"]},
            milestone_plan=milestone_plan,
            engineering_review={"invoked": True, "risk_level": "medium"},
            engineering_workflow={"mode": "large-project-engineering"},
        )
        self.assertEqual(len(results), 2)
        self.assertTrue(all(item.get("ok") for item in results))

        service = TaskService(PROJECT_ROOT / "backend" / "python" / "brain" / "runtime" / "main.py")
        milestones = service.inspect_milestones(run_id=run_id)
        self.assertEqual(milestones.get("milestone_state", {}).get("completed_milestones"), 2)
        verification = service.inspect_verification(run_id=run_id)
        self.assertEqual(verification.get("verification_summary", {}).get("ok"), True)
        pr_summary = service.inspect_pr_summary(run_id=run_id)
        self.assertIn("merge_readiness", pr_summary.get("pr_summary", {}))
        intelligence = service.inspect_run_intelligence(run_id=run_id)
        run_summary = intelligence.get("run_summary", {})
        self.assertIn("engineering", run_summary)
        self.assertIn("execution_state", run_summary)
        self.assertIn("milestone_state", run_summary.get("engineering", {}))


if __name__ == "__main__":
    unittest.main()

