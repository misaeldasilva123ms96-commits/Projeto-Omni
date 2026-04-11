from __future__ import annotations

import json
from pathlib import Path

from .models import OrchestrationContext, OrchestrationDecision, OrchestrationResult


class OrchestrationStore:
    def __init__(self, root: Path) -> None:
        self.base_dir = root / ".logs" / "fusion-runtime" / "orchestration"
        self.context_dir = self.base_dir / "context"
        self.decisions_dir = self.base_dir / "decisions"
        self.routes_dir = self.base_dir / "routes"
        self.results_dir = self.base_dir / "results"
        self.context_dir.mkdir(parents=True, exist_ok=True)
        self.decisions_dir.mkdir(parents=True, exist_ok=True)
        self.routes_dir.mkdir(parents=True, exist_ok=True)
        self.results_dir.mkdir(parents=True, exist_ok=True)

    def append_context(self, context: OrchestrationContext) -> None:
        self._append_jsonl(self.context_dir / f"{context.plan_id or 'runtime'}.jsonl", context.as_dict())

    def append_decision(self, decision: OrchestrationDecision) -> None:
        payload = decision.as_dict()
        self._append_jsonl(self.decisions_dir / f"{decision.plan_id or 'runtime'}.jsonl", payload)
        self._append_jsonl(self.routes_dir / f"{decision.plan_id or 'runtime'}.jsonl", payload)

    def append_result(self, result: OrchestrationResult) -> None:
        self._append_jsonl(self.results_dir / f"{result.context_id}.jsonl", result.as_dict())

    @staticmethod
    def _append_jsonl(path: Path, payload: dict[str, object]) -> None:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False))
            handle.write("\n")
