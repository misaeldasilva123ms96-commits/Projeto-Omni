"""Governed Autonomy Controller for Omni runtime decisions.

Decides what Omni should do next — CONTINUE, RETRY, REPLAN, PAUSE,
ESCALATE_TO_MISAEL, or ABORT_SAFE — based on policy evaluation of
runtime context.

No autonomous write action is executed. All decisions are advisory only.
SELF_REPAIR and SWITCH_PROVIDER are defined but disabled in this branch.
"""

from .autonomy_controller import AutonomyController
from .autonomy_escalation import EscalationReport, build_escalation_report
from .autonomy_models import (
    ADVISORY_ONLY_DECISIONS,
    DECISION_RISK_MAP,
    DISABLED_DECISIONS,
    AutonomyContext,
    AutonomyDecision,
    DecisionType,
)
from .autonomy_policy import evaluate_policy
from .autonomy_receipt import AutonomyReceipt, AutonomyReceiptLog, build_receipt
from .autonomy_session_state import AutonomySessionState
from .autonomy_session_tracker import AutonomySessionTracker
from .dry_run_retry_models import DryRunRetryPlan
from .dry_run_retry_planner import DryRunRetryPlanner, build_dry_run_retry_plan
from .evidence_view import build_autonomy_evidence_payload
from .error_progress_models import ErrorFingerprint, ProgressTrackerOutput, StrategyAttempt
from .error_progress_tracker import SmartErrorProgressTracker

__all__ = [
    "AutonomyController",
    "AutonomyContext",
    "AutonomyDecision",
    "AutonomyReceipt",
    "AutonomyReceiptLog",
    "AutonomySessionState",
    "AutonomySessionTracker",
    "DryRunRetryPlan",
    "DryRunRetryPlanner",
    "build_dry_run_retry_plan",
    "build_autonomy_evidence_payload",
    "ErrorFingerprint",
    "ProgressTrackerOutput",
    "SmartErrorProgressTracker",
    "StrategyAttempt",
    "EscalationReport",
    "DecisionType",
    "ADVISORY_ONLY_DECISIONS",
    "DECISION_RISK_MAP",
    "DISABLED_DECISIONS",
    "evaluate_policy",
    "build_receipt",
    "build_escalation_report",
]
