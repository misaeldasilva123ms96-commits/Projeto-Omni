"""Runtime Truth evidence for autonomous repair planning."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Optional

REPAIR_PLANNER_EVIDENCE_VERSION = "1.0"
REPAIR_PLANNER_EVENT_TYPE = "sandbox.repair_planner.plan"


@dataclass(frozen=True)
class AutonomousRepairPlannerEvidence:
    event_type: str
    evidence_version: str
    planner_mode: str
    requested_by: str
    related_phase: Optional[str]
    related_pr: Optional[str]
    target_branch: Optional[str]
    base_branch: str
    failure_classification: Optional[str]
    normalized_failure_classification: str
    repair_category: str
    repair_complexity: str
    risk_level: str
    planned: bool
    blocked: bool
    dry_run: bool
    proposed_steps_count: int
    suspected_files_count: int
    validation_commands_count: int
    code_edited: bool
    files_written: bool
    git_mutated: bool
    pr_created: bool
    pr_merged: bool
    network_used: bool
    provider_called: bool
    agent_called: bool
    mcp_used: bool
    vault_written: bool
    main_modified: bool
    secrets_detected: bool
    governance_decision: str
    human_intervention_required: bool
    escalation_reason: Optional[str]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def build_repair_planner_evidence(
    *,
    planner_mode: str,
    requested_by: str,
    related_phase: str | None,
    related_pr: str | None,
    target_branch: str | None,
    base_branch: str,
    failure_classification: str | None,
    normalized_failure_classification: str,
    repair_category: str,
    repair_complexity: str,
    risk_level: str,
    planned: bool,
    blocked: bool,
    dry_run: bool,
    proposed_steps_count: int,
    suspected_files_count: int,
    validation_commands_count: int,
    secrets_detected: bool,
    human_intervention_required: bool,
    escalation_reason: str | None,
) -> AutonomousRepairPlannerEvidence:
    return AutonomousRepairPlannerEvidence(
        event_type=REPAIR_PLANNER_EVENT_TYPE,
        evidence_version=REPAIR_PLANNER_EVIDENCE_VERSION,
        planner_mode=planner_mode,
        requested_by=requested_by,
        related_phase=related_phase,
        related_pr=related_pr,
        target_branch=target_branch,
        base_branch=base_branch,
        failure_classification=failure_classification,
        normalized_failure_classification=normalized_failure_classification,
        repair_category=repair_category,
        repair_complexity=repair_complexity,
        risk_level=risk_level,
        planned=planned,
        blocked=blocked,
        dry_run=dry_run,
        proposed_steps_count=proposed_steps_count,
        suspected_files_count=suspected_files_count,
        validation_commands_count=validation_commands_count,
        code_edited=False,
        files_written=False,
        git_mutated=False,
        pr_created=False,
        pr_merged=False,
        network_used=False,
        provider_called=False,
        agent_called=False,
        mcp_used=False,
        vault_written=False,
        main_modified=False,
        secrets_detected=secrets_detected,
        governance_decision=_governance_decision(
            blocked=blocked,
            dry_run=dry_run,
            planned=planned,
            secrets_detected=secrets_detected,
            human_intervention_required=human_intervention_required,
        ),
        human_intervention_required=human_intervention_required,
        escalation_reason=escalation_reason,
    )


def _governance_decision(
    *,
    blocked: bool,
    dry_run: bool,
    planned: bool,
    secrets_detected: bool,
    human_intervention_required: bool,
) -> str:
    if blocked or secrets_detected:
        return "blocked"
    if human_intervention_required:
        return "requires_human_intervention"
    if dry_run:
        return "dry_run"
    if planned:
        return "repair_plan_created"
    return "blocked"
