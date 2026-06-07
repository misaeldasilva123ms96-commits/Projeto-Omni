from __future__ import annotations

import asyncio
from typing import Any, Callable

from brain.swarm.swarm_orchestrator import SwarmOrchestrator
from brain.runtime.performance import PerformanceEngine
from brain.runtime.policy.policy_router import PolicyRouter
from brain.runtime.experience import ExperienceStore


class SwarmCoordinator:
    def __init__(
        self,
        swarm_orchestrator: SwarmOrchestrator,
        performance_engine: PerformanceEngine,
        policy_router: PolicyRouter,
        experience_store: ExperienceStore,
    ) -> None:
        self.swarm_orchestrator = swarm_orchestrator
        self.performance_engine = performance_engine
        self.policy_router = policy_router
        self.experience_store = experience_store

    async def run(
        self,
        *,
        message: str,
        session_id: str,
        memory_store: dict[str, Any],
        history: list[dict[str, Any]],
        summary: str,
        capabilities: list[dict[str, str]],
        executor: Callable[..., Any],
        context_session: dict[str, Any],
    ) -> dict[str, Any]:
        result = await self.swarm_orchestrator.run(
            message=message,
            session_id=session_id,
            memory_store=memory_store,
            history=history,
            summary=summary,
            capabilities=capabilities,
            executor=executor,
        )
        return result if isinstance(result, dict) else {}
