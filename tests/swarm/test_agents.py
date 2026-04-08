from __future__ import annotations

import asyncio
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.swarm.base_agent import SwarmMessage  # noqa: E402
from brain.swarm.critic_agent import CriticAgent  # noqa: E402
from brain.swarm.executor_agent import ExecutorAgent  # noqa: E402
from brain.swarm.memory_agent import MemoryAgent  # noqa: E402
from brain.swarm.planner_agent import PlannerAgent  # noqa: E402
from brain.swarm.router_agent import RouterAgent  # noqa: E402


def message(*, payload: dict[str, object], message_type: str = "task") -> SwarmMessage:
    return SwarmMessage(
        from_agent="test",
        to_agent="target",
        type=message_type,
        payload=payload,
        timestamp="2026-04-08T00:00:00Z",
        session_id="phase2-swarm",
    )


class SwarmAgentsTest(unittest.TestCase):
    def test_router_agent_routes_valid_and_invalid_input(self) -> None:
        agent = RouterAgent("router_agent", asyncio.Queue())
        result = asyncio.run(
            agent.receive(
                message(payload={"message": "devo aprender programacao ou design?"}),
                {"history": []},
            )
        )
        self.assertEqual(result["intent"], "decision")
        self.assertIn("planner_agent", result["delegates"])

        empty = asyncio.run(agent.receive(message(payload={}), {"history": []}))
        self.assertEqual(empty["intent"], "conversa")

    def test_planner_agent_generates_subtasks(self) -> None:
        agent = PlannerAgent("planner_agent", asyncio.Queue())
        result = asyncio.run(
            agent.receive(
                message(payload={"intent": "analysis", "delegates": ["executor_agent"], "complex": True}),
                {"message": "analise o repositorio"},
            )
        )
        self.assertGreaterEqual(len(result["subtasks"]), 3)
        self.assertIn("executor_agent", result["delegates"])

    def test_executor_agent_handles_simple_inputs(self) -> None:
        agent = ExecutorAgent("executor_agent", asyncio.Queue())
        result = asyncio.run(
            agent.receive(
                message(payload={"kind": "review", "goal": "avaliar risco"}),
                {"message": "avalie", "intent": "analysis", "summary": ""},
            )
        )
        self.assertEqual(result["delegate"], "critic_agent")
        self.assertIn("Revisao", result["result"])

        default_result = asyncio.run(
            agent.receive(message(payload={}), {"message": "oi", "intent": "conversa", "summary": ""})
        )
        self.assertEqual(default_result["kind"], "analysis")

    def test_critic_agent_flags_empty_response(self) -> None:
        agent = CriticAgent("critic_agent", asyncio.Queue())
        result = asyncio.run(
            agent.receive(message(payload={"response": ""}, message_type="critique"), {"message": "oi"})
        )
        self.assertFalse(result["approved"])
        self.assertIn("resposta vazia", result["issues"])

    def test_memory_agent_builds_signal(self) -> None:
        agent = MemoryAgent("memory_agent", asyncio.Queue())
        result = asyncio.run(
            agent.receive(
                message(payload={"response": "ok"}, message_type="memory_op"),
                {
                    "memory": {"nome": "Misael", "preferencias": ["python"]},
                    "history": [{"content": "oi"}],
                    "summary": "contexto",
                },
            )
        )
        self.assertEqual(result["memory_signal"]["known_name"], "Misael")
        self.assertEqual(result["memory_signal"]["preferences"], ["python"])


if __name__ == "__main__":
    unittest.main()
