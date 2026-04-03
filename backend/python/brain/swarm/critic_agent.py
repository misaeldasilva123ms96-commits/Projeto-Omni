from __future__ import annotations

from brain.swarm.base_agent import BaseAgent, SwarmMessage


class CriticAgent(BaseAgent):
    async def think(self, message: SwarmMessage, context: dict[str, object]) -> dict[str, object]:
        candidate_response = str(message.payload.get("response", "")).strip()
        return {
            "response": candidate_response,
            "intent": str(context.get("intent", "conversa")),
            "message": str(context.get("message", "")),
        }

    async def act(self, thought: dict[str, object], context: dict[str, object]) -> dict[str, object]:
        response = str(thought["response"]).strip()
        score = 0.55
        issues: list[str] = []

        if not response:
            issues.append("resposta vazia")
            score = 0.1
        elif len(response.split()) < 8:
            issues.append("resposta curta demais")
            score = 0.45
        else:
            score = 0.86

        if "Nao consegui processar" in response:
            issues.append("fallback detectado")
            score = min(score, 0.3)

        return {
            "response": response,
            "score": score,
            "issues": issues,
            "approved": score >= 0.4,
        }

    async def respond(
        self,
        action_result: dict[str, object],
        thought: dict[str, object],
        context: dict[str, object],
    ) -> dict[str, object]:
        response = str(action_result["response"]).strip()
        if not action_result["approved"] and response:
            response = f"{response}\n\nProximo passo: refine o objetivo ou detalhe melhor o contexto."
        return {
            "agent": self.agent_id,
            "approved": action_result["approved"],
            "score": action_result["score"],
            "issues": action_result["issues"],
            "response": response,
            "summary": f"Critic validou resposta com score={action_result['score']:.2f}",
        }
