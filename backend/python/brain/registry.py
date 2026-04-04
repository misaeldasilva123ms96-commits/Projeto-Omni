from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


CapabilityHandler = Callable[[dict[str, Any]], str]


@dataclass(frozen=True)
class Capability:
    name: str
    description: str
    category: str
    handler: CapabilityHandler


@dataclass(frozen=True)
class AgentProfile:
    id: str
    name: str
    specialty: str
    capabilities: tuple[str, ...]
    priority: int
    active: bool = True


def _generate_idea(input_data: dict[str, Any]) -> str:
    message = str(input_data.get("message", "")).strip().lower()
    preferences = input_data.get("preferences", [])
    likes_tech = any("tecnologia" in str(item).lower() or "ia" in str(item).lower() for item in preferences)
    if "negocio" in message or "ideia" in message:
        if likes_tech:
            return "Voce pode validar um microservico de automacao para pequenos negocios com cobranca recorrente."
        return "Escolha um problema recorrente de um nicho pequeno e crie uma oferta simples para resolver isso."
    return "Comece por um problema pequeno, claro e recorrente que valha a pena resolver."


def _give_advice(input_data: dict[str, Any]) -> str:
    message = str(input_data.get("message", "")).strip().lower()
    if "estudar" in message and "descansar" in message:
        return "Se a energia estiver baixa, descansar primeiro pode melhorar a qualidade do estudo depois."
    if "dinheiro" in message:
        return "Priorize aumentar renda com uma oferta simples antes de buscar algo complexo demais."
    return "Escolha o proximo passo que gere progresso sem aumentar seu desgaste."


def _create_plan(input_data: dict[str, Any]) -> str:
    objective = str(input_data.get("message", "")).strip() or "resolver a tarefa atual"
    return (
        f"Plano rapido para {objective}: "
        "1. entender o objetivo, "
        "2. escolher a melhor estrategia, "
        "3. executar o menor passo util."
    )


def _compare_options(input_data: dict[str, Any]) -> str:
    message = str(input_data.get("message", "")).strip().lower()
    if "python" in message and "rust" in message:
        return "Python acelera iteracao e ecossistema; Rust ganha em performance, previsibilidade e seguranca de baixo nivel."
    return "Compare as opcoes por velocidade de entrega, custo operacional, manutencao e risco tecnico."


CAPABILITIES: dict[str, Capability] = {
    "generate_idea": Capability(
        name="generate_idea",
        description="gera ideias praticas para negocio, projeto ou iniciativa",
        category="strategy",
        handler=_generate_idea,
    ),
    "give_advice": Capability(
        name="give_advice",
        description="fornece conselho contextual e sugestao pratica",
        category="guidance",
        handler=_give_advice,
    ),
    "create_plan": Capability(
        name="create_plan",
        description="quebra um objetivo em passos curtos e executaveis",
        category="planning",
        handler=_create_plan,
    ),
    "compare_options": Capability(
        name="compare_options",
        description="compara opcoes com pros, contras e recomendacao final",
        category="analysis",
        handler=_compare_options,
    ),
}


AGENTS: dict[str, AgentProfile] = {
    "router_agent": AgentProfile(
        id="router_agent",
        name="RouterAgent",
        specialty="roteamento de intents e definicao de fluxo interno",
        capabilities=("give_advice", "create_plan", "compare_options"),
        priority=1,
    ),
    "planner_agent": AgentProfile(
        id="planner_agent",
        name="PlannerAgent",
        specialty="decomposicao de objetivos e criacao de subtarefas",
        capabilities=("create_plan",),
        priority=2,
    ),
    "executor_agent": AgentProfile(
        id="executor_agent",
        name="ExecutorAgent",
        specialty="execucao de tarefas, consolidacao e acao pratica",
        capabilities=("generate_idea", "give_advice", "create_plan", "compare_options"),
        priority=3,
    ),
    "critic_agent": AgentProfile(
        id="critic_agent",
        name="CriticAgent",
        specialty="revisao de qualidade e saneamento da resposta final",
        capabilities=("give_advice",),
        priority=4,
    ),
    "memory_agent": AgentProfile(
        id="memory_agent",
        name="MemoryAgent",
        specialty="consolidacao, busca e persistencia de memoria hibrida",
        capabilities=("create_plan",),
        priority=5,
    ),
}


def list_capabilities() -> list[str]:
    return sorted(CAPABILITIES.keys())


def describe_capabilities() -> list[dict[str, str]]:
    return [
        {
            "name": capability.name,
            "description": capability.description,
            "category": capability.category,
        }
        for capability in CAPABILITIES.values()
    ]


def recommend_capabilities(message: str) -> list[str]:
    lowered = message.lower()
    matches: list[str] = []
    if any(term in lowered for term in ("ideia", "negocio", "negócio", "modelo de negocio", "modelo de negócio")):
        matches.append("generate_idea")
    if any(term in lowered for term in ("conselho", "devo", "dica", "melhorar")):
        matches.append("give_advice")
    if any(term in lowered for term in ("plano", "passo", "como comeco", "como começo")):
        matches.append("create_plan")
    if any(term in lowered for term in ("prós e contras", "pros e contras", " vs ", "comparar", "compare")):
        matches.append("compare_options")
    return matches


def execute_capability(name: str, input_data: dict[str, Any]) -> str:
    capability = CAPABILITIES.get(name)
    if capability is None:
        return ""
    try:
        return capability.handler(input_data).strip()
    except Exception:
        return ""


def list_agents() -> list[str]:
    return sorted(AGENTS.keys())


def get_agent(agent_id: str) -> AgentProfile | None:
    return AGENTS.get(agent_id)


def describe_agents(active_only: bool = True) -> list[dict[str, object]]:
    agents = sorted(AGENTS.values(), key=lambda item: item.priority)
    result: list[dict[str, object]] = []
    for agent in agents:
        if active_only and not agent.active:
            continue
        result.append(
            {
                "id": agent.id,
                "name": agent.name,
                "specialty": agent.specialty,
                "capabilities": list(agent.capabilities),
                "priority": agent.priority,
                "active": agent.active,
            }
        )
    return result


def resolve_agent_ids(intent: str) -> list[str]:
    intent_key = intent.strip().lower()
    if intent_key in {"dinheiro", "decision", "conselho", "comparativo", "planejamento", "ideacao"}:
        return ["router_agent", "planner_agent", "executor_agent", "critic_agent", "memory_agent"]
    if intent_key in {"aprendizado", "explicacao", "pergunta_direta", "saudacao"}:
        return ["router_agent", "planner_agent", "executor_agent", "memory_agent", "critic_agent"]
    return ["router_agent", "executor_agent", "memory_agent", "critic_agent"]