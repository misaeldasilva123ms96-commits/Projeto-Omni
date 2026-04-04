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

        if raw_message.startswith(("olá", "ola", "oi", "bom dia", "boa tarde", "boa noite")) and any(
            token in raw_message for token in ("funcionando", "tudo bem", "pode me ajudar")
        ):
            intent = "pergunta_direta"
        elif raw_message.startswith(("olá", "ola", "oi", "bom dia", "boa tarde", "boa noite")):
            intent = "saudacao"
        elif any(token in raw_message for token in ("prós e contras", "pros e contras", " vs ", " versus ", "compare", "comparar", "analise ", "analisa ")):
            intent = "comparativo"
        elif any(token in raw_message for token in ("plano de negócios", "plano de negocios", "plano de negócio", "plano de negocio", "crie um plano", "modelo de negócio", "modelo de negocio")):
            intent = "planejamento"
        elif any(token in raw_message for token in ("ideias de startup", "ideias inovadoras", "me dê 3 ideias", "me de 3 ideias")):
            intent = "ideacao"
        elif any(token in raw_message for token in ("devo", " ou ", "qual e melhor", "o que fazer")):
            intent = "decision"
        elif any(token in raw_message for token in ("dinheiro", "negocio", "negócio", "renda", "ganhar dinheiro")):
            intent = "dinheiro"
        elif any(token in raw_message for token in ("aprender", "programacao", "programação", "por onde comeco")) or "aprender" in history_text:
            intent = "aprendizado"
        elif any(token in raw_message for token in ("como funciona", "o que e", "o que é", "explique")):
            intent = "explicacao"
        elif any(token in raw_message for token in ("quem e voce", "quem é você", "como voce responde", "como você responde")):
            intent = "pessoal"
        elif "?" in raw_message:
            intent = "pergunta_direta"
        else:
            intent = "conversa"

        complex_request = len(raw_message.split()) > 8 or intent in {"decision", "dinheiro", "aprendizado", "comparativo", "planejamento", "ideacao"}
        return {
            "intent": intent,
            "complex": complex_request,
            "message": message.payload.get("message", ""),
        }

    async def act(self, thought: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        delegates_by_intent = {
            "saudacao": ["executor_agent", "critic_agent", "memory_agent"],
            "pergunta_direta": ["executor_agent", "critic_agent", "memory_agent"],
            "comparativo": ["planner_agent", "executor_agent", "critic_agent", "memory_agent"],
            "planejamento": ["planner_agent", "executor_agent", "critic_agent", "memory_agent"],
            "ideacao": ["planner_agent", "executor_agent", "critic_agent", "memory_agent"],
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