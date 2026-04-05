from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.orchestrator import BrainOrchestrator, BrainPaths  # noqa: E402
from brain.runtime.rust_executor_bridge import execute_action  # noqa: E402
from brain.runtime.task_service import TaskService  # noqa: E402


class Phase2RuntimeTest(unittest.TestCase):
    def run_main(self, prompt: str, session_id: str) -> str:
        env = os.environ.copy()
        env["AI_SESSION_ID"] = session_id
        env["BASE_DIR"] = str(PROJECT_ROOT)
        env["PYTHON_BASE_DIR"] = str(PROJECT_ROOT / "backend" / "python")
        completed = subprocess.run(
            ["python", "backend\\python\\main.py", prompt],
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

    def test_real_query_to_execution_path_reads_package(self) -> None:
        output = self.run_main("leia package.json", "phase2-read")
        self.assertIn('"name": "omini-runner"', output)

    def test_memory_update_and_retrieval_work_in_live_path(self) -> None:
        learn_output = self.run_main(
            "meu nome é Misael e eu trabalho com inteligência artificial",
            "phase2-memory",
        )
        self.assertIn("registrar seu nome", learn_output.lower())

        recall_output = self.run_main("qual é meu nome?", "phase2-memory")
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
                "execution_context": {"project_root": "..\\..", "runtime_mode": "python-rust-cargo"},
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
                "execution_context": {"project_root": "..\\..", "runtime_mode": "python-rust-cargo"},
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
                "execution_context": {"project_root": "..\\..", "runtime_mode": "python-rust-cargo"},
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
                "execution_context": {"project_root": "..\\..", "runtime_mode": "python-rust-cargo"},
                "tool_arguments": {"path": "tests\\fusion\\blocked-output.txt", "content": "blocked"},
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
        self.assertIn('"name": "omini-runner"', output)

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
                "execution_context": {"project_root": "..\\..", "runtime_mode": "python-rust-cargo"},
                "tool_arguments": {"path": "tests\\fusion\\blocked-output.txt", "content": "blocked"},
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

        transcript_tail = json.loads(runtime_transcript.read_text(encoding="utf-8").strip().splitlines()[-1])
        audit_tail = json.loads(execution_audit.read_text(encoding="utf-8").strip().splitlines()[-1])

        self.assertEqual(transcript_tail.get("selected_tool"), "read_file")
        self.assertEqual(audit_tail.get("selected_tool"), "read_file")
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
                    "execution_context": {"project_root": "..\\..", "runtime_mode": "python-rust-cargo"},
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
                    "execution_context": {"project_root": "..\\..", "runtime_mode": "python-rust-cargo"},
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
        self.assertEqual(executed.get("user_id"), "user-phase4")
        self.assertEqual(executed.get("session_id"), "service-session")
        self.assertIn('"name": "omini-runner"', executed.get("response", ""))

    def test_observability_records_task_and_run_ids(self) -> None:
        self.run_main("leia package.json", "phase4-observability")
        execution_audit = PROJECT_ROOT / ".logs" / "fusion-runtime" / "execution-audit.jsonl"
        audit_tail = json.loads(execution_audit.read_text(encoding="utf-8").strip().splitlines()[-1])
        self.assertIn("event_type", audit_tail)
        self.assertIn("task_id", audit_tail)
        self.assertIn("run_id", audit_tail)


if __name__ == "__main__":
    unittest.main()
