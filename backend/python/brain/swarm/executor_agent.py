from __future__ import annotations

from brain.swarm.base_agent import BaseAgent, SwarmMessage


class ExecutorAgent(BaseAgent):
    async def think(self, message: SwarmMessage, context: dict[str, object]) -> dict[str, object]:
        subtask = dict(message.payload)
        return {
            "subtask": subtask,
            "message": str(context.get("message", "")),
            "intent": str(context.get("intent", "conversa")),
            "summary": str(context.get("summary", "")),
        }

    async def act(self, thought: dict[str, object], context: dict[str, object]) -> dict[str, object]:
        subtask = thought["subtask"]
        kind = str(subtask.get("kind", "analysis"))
        goal = str(subtask.get("goal", ""))
        message = str(thought["message"])

        if kind == "planning":
            result = {
                "delegate": "planner_agent",
                "kind": kind,
                "result": f"Plano local: entender '{message}', reduzir escopo e executar a primeira etapa util.",
            }
        elif kind == "analysis":
            result = {
                "delegate": "memory_agent",
                "kind": kind,
                "result": f"Contexto relevante identificado para '{message}'.",
            }
        elif kind == "review":
            result = {
                "delegate": "critic_agent",
                "kind": kind,
                "result": f"Revisao preliminar preparada para o objetivo: {goal}.",
            }
        else:
            result = {
                "delegate": "executor_agent",
                "kind": kind,
                "result": f"Execucao preparada para intent={thought['intent']}.",
            }
        return result

    async def respond(
        self,
        action_result: dict[str, object],
        thought: dict[str, object],
        context: dict[str, object],
    ) -> dict[str, object]:
        return {
            "agent": self.agent_id,
            "delegate": action_result["delegate"],
            "kind": action_result["kind"],
            "result": action_result["result"],
        }
