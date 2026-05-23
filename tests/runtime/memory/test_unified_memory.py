from __future__ import annotations

import os
import shutil
import sys
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.memory.decision_memory import DecisionMemoryStore  # noqa: E402
from brain.memory.evidence_memory import EvidenceMemoryStore  # noqa: E402
from brain.memory.working_memory import WorkingMemoryStore  # noqa: E402
from brain.runtime.language import normalize_input_to_oil_request  # noqa: E402
from brain.runtime.memory import MemoryFacade, UnifiedMemoryLayer  # noqa: E402
from brain.runtime.memory.semantic.models import SemanticFact, utc_now_iso  # noqa: E402
from brain.runtime.transcript_store import TranscriptStore  # noqa: E402


class _StubRunRegistry:
    def get_resolution_summary(self) -> dict:
        return {"resolution_counts": {"running": 2, "completed": 1}}

    def recent_resolution_events(self, limit: int = 5) -> list[dict]:
        return [{"status": "running", "reason": "execution_allowed", "source": "runtime"}][:limit]

    def get(self, run_id: str):
        class _Record:
            def as_dict(self_inner) -> dict:
                return {
                    "run_id": run_id,
                    "status": "running",
                    "last_action": "reasoning_handoff",
                    "progress_score": 0.42,
                }

        return _Record()


class UnifiedMemoryLayerTest(unittest.TestCase):
    @contextmanager
    def temp_workspace(self):
        base = PROJECT_ROOT / ".logs" / "test-unified-memory"
        base.mkdir(parents=True, exist_ok=True)
        path = base / f"unified-{uuid4().hex[:8]}"
        path.mkdir(parents=True, exist_ok=True)
        try:
            yield path
        finally:
            shutil.rmtree(path, ignore_errors=True)

    def test_unified_memory_retrieval_is_ranked_and_bounded(self) -> None:
        with self.temp_workspace() as workspace_root:
            with patch.dict(os.environ, {"OMINI_MEMORY_MIN_CONFIDENCE_FOR_SEMANTIC_RECALL": "0.0"}):
                transcript = TranscriptStore(workspace_root / "backend" / "python" / "transcripts")
                transcript.append_turn("sess-32", "Analise runtime policy", "Ok.")
                transcript.append_turn("sess-32", "Precisamos validar governanca", "Certo.")

                working = WorkingMemoryStore(workspace_root / ".logs" / "fusion-runtime" / "working-memory.json")
                working.update_session(
                    "sess-32",
                    {
                        "current_task_summary": "Analise de runtime governance",
                        "current_execution_strategy": "phased",
                        "context_budget_level": "high",
                    },
                )

                decision = DecisionMemoryStore(workspace_root / ".logs" / "fusion-runtime" / "decision-memory.json")
                decision.record_decision(
                    session_id="sess-32",
                    task_id="task-32",
                    run_id="run-32",
                    decision_type="routing_selection",
                    task_type="repository_analysis",
                    reason_code="routing_selected",
                    reason="governance-sensitive flow",
                    metadata={},
                )
                evidence = EvidenceMemoryStore(workspace_root / ".logs" / "fusion-runtime" / "evidence-memory.json")
                evidence.record_evidence(
                    session_id="sess-32",
                    task_id="task-32",
                    run_id="run-32",
                    task_type="repository_analysis",
                    evidence={"file_evidence": True},
                    metadata={},
                )

                facade = MemoryFacade(workspace_root)
                self.addCleanup(facade.close)
                facade.semantic.upsert_fact(
                    SemanticFact(
                        fact_id="fact-1",
                        subject="analyze",
                        predicate="needs",
                        object_value="governance context",
                        confidence=0.9,
                        source_episode_ids=["ep-1"],
                        goal_types=["execution"],
                        created_at=utc_now_iso(),
                        last_reinforced_at=utc_now_iso(),
                        metadata={},
                    )
                )
                layer = UnifiedMemoryLayer(
                    transcript_store=transcript,
                    memory_facade=facade,
                    working_store=working,
                    decision_store=decision,
                    evidence_store=evidence,
                    run_registry=_StubRunRegistry(),
                )
                oil_request = normalize_input_to_oil_request(
                    "Analise runtime governance com seguranca",
                    session_id="sess-32",
                    run_id="run-32",
                    metadata={"source_component": "tests.memory"},
                )
                bundle = layer.build_reasoning_context(
                    session_id="sess-32",
                    run_id="run-32",
                    query="Analise runtime governance com seguranca",
                    oil_request=oil_request,
                    memory_store={"history": [], "long_term": {"preferred_style": "concise"}},
                    max_items=4,
                )
                payload = bundle.as_dict()
                self.assertEqual(payload["selected_count"], 4)
                self.assertGreaterEqual(payload["total_candidates"], 4)
                self.assertTrue(payload["sources_used"])
                self.assertIn("scoring", payload)
                self.assertIn("context_summary", payload)

    def test_unified_memory_empty_state_is_safe(self) -> None:
        with self.temp_workspace() as workspace_root:
            transcript = TranscriptStore(workspace_root / "backend" / "python" / "transcripts")
            working = WorkingMemoryStore(workspace_root / ".logs" / "fusion-runtime" / "working-memory.json")
            decision = DecisionMemoryStore(workspace_root / ".logs" / "fusion-runtime" / "decision-memory.json")
            evidence = EvidenceMemoryStore(workspace_root / ".logs" / "fusion-runtime" / "evidence-memory.json")
            facade = MemoryFacade(workspace_root)
            self.addCleanup(facade.close)
            layer = UnifiedMemoryLayer(
                transcript_store=transcript,
                memory_facade=facade,
                working_store=working,
                decision_store=decision,
                evidence_store=evidence,
                run_registry=None,
            )
            oil_request = normalize_input_to_oil_request(
                "resuma isso",
                session_id="sess-empty",
                run_id=None,
                metadata={"source_component": "tests.memory"},
            )
            bundle = layer.build_reasoning_context(
                session_id="sess-empty",
                run_id=None,
                query="resuma isso",
                oil_request=oil_request,
                memory_store={"history": [], "long_term": {}},
                max_items=5,
            )
            payload = bundle.as_dict()
            self.assertIsInstance(payload["selected_signals"], list)
            self.assertGreaterEqual(payload["selected_count"], 0)
            self.assertIn("context_summary", payload)


if __name__ == "__main__":
    unittest.main()
