from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, Awaitable, Callable

from brain.registry import describe_agents
from brain.swarm.base_agent import SwarmMessage
from brain.swarm.critic_agent import CriticAgent
from brain.swarm.executor_agent import ExecutorAgent
from brain.swarm.memory_agent import MemoryAgent
from brain.swarm.planner_agent import PlannerAgent
from brain.swarm.router_agent import RouterAgent


SwarmExecutor = Callable[[dict[str, Any]], Awaitable[str]]


class SwarmOrchestrator:
    def __init__(self, log_path: Path) -> None:
        self.log_path = log_path
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.log_path.exists():
            self.log_path.write_text(json.dumps({"events": []}, ensure_ascii=False, indent=2), encoding="utf-8")

    async def run(
        self,
        *,
        message: str,
        session_id: str,
        memory_store: dict[str, Any],
        history: list[dict[str, str]],
        summary: str,
        capabilities: list[dict[str, str]],
        executor: SwarmExecutor,
    ) -> dict[str, Any]:
        queue: asyncio.Queue[SwarmMessage] = asyncio.Queue()
        router = RouterAgent("router_agent", queue)
        planner = PlannerAgent("planner_agent", queue)
        executor_agent = ExecutorAgent("executor_agent", queue)
        critic = CriticAgent("critic_agent", queue)
        memory_agent = MemoryAgent("memory_agent", queue)

        context: dict[str, Any] = {
            "message": message,
            "memory": memory_store.get("user", {}),
            "history": history,
            "summary": summary,
            "capabilities": capabilities,
            "agent_registry": describe_agents(),
        }

        trace: list[dict[str, Any]] = []
        communication_log: list[dict[str, Any]] = []

        router_message = await router.publish(
            to_agent="router_agent",
            message_type="task",
            payload={"message": message},
            session_id=session_id,
        )
        communication_log.append(router_message.to_dict())
        route = await router.receive(router_message, context)
        trace.append(route)
        context["intent"] = route["intent"]
        context["delegates"] = route["delegates"]

        planner_message = await planner.publish(
            to_agent="planner_agent",
            message_type="task",
            payload=route,
            session_id=session_id,
        )
        communication_log.append(planner_message.to_dict())
        plan = await planner.receive(planner_message, context)
        trace.append(plan)
        context["plan"] = plan

        execution_messages: list[SwarmMessage] = []
        for subtask in plan["subtasks"]:
            delegate = str(subtask.get("delegate", "executor_agent"))
            task_message = await executor_agent.publish(
                to_agent=delegate,
                message_type="task",
                payload=subtask,
                session_id=session_id,
            )
            execution_messages.append(task_message)
            communication_log.append(task_message.to_dict())

        execution_results = await asyncio.gather(
            *(executor_agent.receive(item, context) for item in execution_messages)
        )
        trace.extend(execution_results)
        context["execution_results"] = execution_results

        node_response = await executor(
            {
                "message": message,
                "intent": route["intent"],
                "delegates": route["delegates"],
                "plan": plan["subtasks"],
                "agent_registry": describe_agents(),
                "trace": trace,
            }
        )

        critic_message = await critic.publish(
            to_agent="critic_agent",
            message_type="critique",
            payload={"response": node_response},
            session_id=session_id,
        )
        communication_log.append(critic_message.to_dict())
        critique = await critic.receive(critic_message, context)
        trace.append(critique)

        memory_message = await memory_agent.publish(
            to_agent="memory_agent",
            message_type="memory_op",
            payload={"response": critique["response"], "trace": trace},
            session_id=session_id,
        )
        communication_log.append(memory_message.to_dict())
        memory_result = await memory_agent.receive(memory_message, context)
        trace.append(memory_result)

        self._append_log(
            {
                "session_id": session_id,
                "message": message,
                "route": route,
                "plan": plan,
                "communication": communication_log,
                "trace": trace,
            }
        )

        return {
            "response": critique["response"],
            "intent": route["intent"],
            "delegates": route["delegates"],
            "agent_trace": trace,
            "memory_signal": memory_result.get("memory_signal", {}),
        }

    def _append_log(self, event: dict[str, Any]) -> None:
        try:
            raw = self.log_path.read_text(encoding="utf-8").strip()
            parsed = json.loads(raw) if raw else {"events": []}
            events = parsed.get("events", [])
            if not isinstance(events, list):
                events = []
            events.append(event)
            payload = {"events": events[-50:]}
            self.log_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            return
