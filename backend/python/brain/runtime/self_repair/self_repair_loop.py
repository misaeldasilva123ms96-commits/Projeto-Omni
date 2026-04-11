from __future__ import annotations

from pathlib import Path
from typing import Any

from .failure_analyzer import FailureAnalyzer
from .models import RepairOutcome, RepairStatus, SelfRepairPolicy
from .repair_executor import SelfRepairExecutor


class SelfRepairLoop:
    def __init__(self, *, workspace_root: Path, policy: SelfRepairPolicy) -> None:
        self.analyzer = FailureAnalyzer()
        self.executor = SelfRepairExecutor(workspace_root=workspace_root, policy=policy)

    def inspect_failure(
        self,
        *,
        action: dict[str, Any],
        result: dict[str, Any],
        trusted_execution: Any | None,
        retry_count: int,
        recurrence_count: int,
    ) -> RepairOutcome:
        evidence = self.analyzer.build_evidence(
            action=action,
            result=result,
            trusted_execution=trusted_execution,
            retry_count=retry_count,
            recurrence_count=recurrence_count,
        )
        return self.executor.handle_failure(evidence=evidence)

    @staticmethod
    def next_decision(outcome: RepairOutcome) -> str:
        if outcome.status == RepairStatus.PROMOTED:
            return "retry_action_after_repair"
        if outcome.status == RepairStatus.VALIDATED:
            return "operator_review_required"
        return "preserve_failure"
