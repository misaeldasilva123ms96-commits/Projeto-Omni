from __future__ import annotations

from typing import Any

from brain.swarm.base_agent import BaseAgent, SwarmMessage


class RouterAgent(BaseAgent):
    async def think(self, message: SwarmMessage, context: dict[str, Any]) -> dict[str, Any]:
        raw_message = str(message.payload.get("message", "")).strip().lower()
        history = context.get("history", [])
        history_text = " ".join(
            str(item.get("content", "")).lower()
            for item in history
            if isinstance(item, dict)
        )

        if any(token in raw_message for token in ("devo", " ou ", "qual e melhor", "o que fazer")):
            intent = "decision"
        elif any(token in raw_message for token in ("dinheiro", "negocio", "renda", "ganhar dinheiro")):
            intent = "dinheiro"
        elif any(token in raw_message for token in ("aprender", "programacao", "por onde comeco")) or "aprender" in history_text:
            intent = "aprendizado"
        elif any(token in raw_message for token in ("como funciona", "o que e", "explique")):
            intent = "explicacao"
        elif any(token in raw_message for token in ("quem e voce", "como voce responde")):
            intent = "pessoal"
        else:
            intent = "conversa"

        complex_request = len(raw_message.split()) > 8 or intent in {"decision", "dinheiro", "aprendizado"}
        return {
            "intent": intent,
            "complex": complex_request,
            "message": message.payload.get("message", ""),
        }

    async def act(self, thought: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        delegates_by_intent = {
            "dinheiro": ["planner_agent", "executor_agent", "critic_agent", "memory_agent"],
            "aprendizado": ["planner_agent", "executor_agent", "memory_agent", "critic_agent"],
            "decision": ["planner_agent", "executor_agent", "critic_agent", "memory_agent"],
            "explicacao": ["executor_agent", "critic_agent", "memory_agent"],
            "pessoal": ["executor_agent", "critic_agent", "memory_agent"],
            "conversa": ["executor_agent", "memory_agent", "critic_agent"],
        }
        return {
            "intent": thought["intent"],
            "complex": thought["complex"],
            "delegates": delegates_by_intent.get(thought["intent"], ["executor_agent", "critic_agent"]),
        }

    async def respond(
        self,
        action_result: dict[str, Any],
        thought: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "agent": self.agent_id,
            "intent": action_result["intent"],
            "complex": action_result["complex"],
            "delegates": action_result["delegates"],
            "summary": f"Router definiu intent={action_result['intent']} e delegates={','.join(action_result['delegates'])}",
        }
