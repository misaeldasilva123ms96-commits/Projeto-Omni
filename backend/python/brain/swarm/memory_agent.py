from __future__ import annotations

from brain.swarm.base_agent import BaseAgent, SwarmMessage


class MemoryAgent(BaseAgent):
    async def think(self, message: SwarmMessage, context: dict[str, object]) -> dict[str, object]:
        user = context.get("memory", {})
        history = context.get("history", [])
        return {
            "message_type": message.type,
            "user": user if isinstance(user, dict) else {},
            "history_size": len(history) if isinstance(history, list) else 0,
            "summary": str(context.get("summary", "")),
        }

    async def act(self, thought: dict[str, object], context: dict[str, object]) -> dict[str, object]:
        user = thought["user"] if isinstance(thought["user"], dict) else {}
        nome = str(user.get("nome", "")).strip()
        preferencias = user.get("preferencias", [])
        if not isinstance(preferencias, list):
            preferencias = []

        memory_signal = {
            "known_name": nome,
            "preferences": [str(item).strip() for item in preferencias if str(item).strip()],
            "history_size": thought["history_size"],
            "summary": thought["summary"],
        }
        return {
            "memory_signal": memory_signal,
            "result": "Memoria consolidada para a sessao atual.",
        }

    async def respond(
        self,
        action_result: dict[str, object],
        thought: dict[str, object],
        context: dict[str, object],
    ) -> dict[str, object]:
        return {
            "agent": self.agent_id,
            "memory_signal": action_result["memory_signal"],
            "summary": action_result["result"],
        }
