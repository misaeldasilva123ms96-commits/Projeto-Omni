from __future__ import annotations

from brain.swarm.base_agent import BaseAgent, SwarmMessage


class PlannerAgent(BaseAgent):
    async def think(self, message: SwarmMessage, context: dict[str, object]) -> dict[str, object]:
        intent = str(message.payload.get("intent", "conversa"))
        original_message = str(context.get("message", ""))
        return {
            "intent": intent,
            "message": original_message,
            "delegates": list(message.payload.get("delegates", [])),
            "complex": bool(message.payload.get("complex", False)),
        }

    async def act(self, thought: dict[str, object], context: dict[str, object]) -> dict[str, object]:
        message = str(thought["message"])
        intent = str(thought["intent"])
        complex_request = bool(thought["complex"])

        subtasks: list[dict[str, object]] = [
            {
                "id": "context_alignment",
                "delegate": "memory_agent",
                "goal": "alinhar contexto e memoria antes da resposta",
                "kind": "analysis",
            }
        ]

        if complex_request:
            subtasks.append(
                {
                    "id": "plan_outline",
                    "delegate": "planner_agent",
                    "goal": f"quebrar a solicitacao '{message}' em passos menores",
                    "kind": "planning",
                }
            )

        subtasks.append(
            {
                "id": "response_execution",
                "delegate": "executor_agent",
                "goal": f"gerar a melhor resposta util para intent={intent}",
                "kind": "execution",
            }
        )
        subtasks.append(
            {
                "id": "quality_review",
                "delegate": "critic_agent",
                "goal": "avaliar clareza, utilidade e risco da resposta",
                "kind": "review",
            }
        )

        return {
            "intent": intent,
            "subtasks": subtasks,
            "delegate_order": list(dict.fromkeys(str(item["delegate"]) for item in subtasks)),
        }

    async def respond(
        self,
        action_result: dict[str, object],
        thought: dict[str, object],
        context: dict[str, object],
    ) -> dict[str, object]:
        return {
            "agent": self.agent_id,
            "intent": action_result["intent"],
            "subtasks": action_result["subtasks"],
            "delegates": action_result["delegate_order"],
            "summary": f"Planner gerou {len(action_result['subtasks'])} subtarefas",
        }
