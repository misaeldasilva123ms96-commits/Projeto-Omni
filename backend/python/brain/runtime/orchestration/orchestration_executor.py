from __future__ import annotations

from pathlib import Path
from typing import Any

from .capability_registry import CapabilityRegistry
from .conflict_resolver import ConflictResolver
from .context_builder import OrchestrationContextBuilder
from .models import OrchestrationPolicy
from .orchestration_policy import DeterministicOrchestrationPolicy
from .orchestration_store import OrchestrationStore
from .result_synthesizer import ResultSynthesizer
from .route_selector import RouteSelector


class OrchestrationExecutor:
    def __init__(self, root: Path, *, policy: OrchestrationPolicy | None = None) -> None:
        self.root = root
        self.policy = policy or DeterministicOrchestrationPolicy.from_env()
        self.registry = CapabilityRegistry()
        self.context_builder = OrchestrationContextBuilder()
        self.selector = RouteSelector(self.registry)
        self.resolver = ConflictResolver()
        self.synthesizer = ResultSynthesizer()
        self.store = OrchestrationStore(root)

    def orchestrate(
        self,
        *,
        session_id: str | None,
        task_id: str | None,
        run_id: str | None,
        action: dict[str, Any],
        plan: Any = None,
        checkpoint: Any = None,
        summary: Any = None,
        continuation_decision: dict[str, Any] | None = None,
        step_results: list[dict[str, Any]] | None = None,
        learning_signals: list[dict[str, Any]] | None = None,
        engineering_tool: bool = False,
        primary_result: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        context = self.context_builder.build(
            session_id=session_id,
            task_id=task_id,
            run_id=run_id,
            action=action,
            plan=plan,
            checkpoint=checkpoint,
            summary=summary,
            continuation_decision=continuation_decision,
            step_results=step_results,
            learning_signals=learning_signals,
        )
        decision = self.selector.select(
            context=context,
            policy=self.policy,
            engineering_tool=engineering_tool,
        )
        resolution = self.resolver.resolve(
            context=context,
            decision=decision,
        )
        result = self.synthesizer.synthesize(
            context=context,
            decision=decision,
            resolution=resolution,
            primary_result=primary_result,
        )
        self.store.append_context(context)
        self.store.append_decision(decision)
        self.store.append_result(result)
        return {
            "context": context.as_dict(),
            "decision": decision.as_dict(),
            "resolution": resolution.as_dict(),
            "result": result.as_dict(),
            "capabilities": self.registry.as_dict(),
            "policy": self.policy.as_dict(),
        }
