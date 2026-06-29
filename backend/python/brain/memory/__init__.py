"""Hybrid and structured memory layers for the Python orchestrator.

Memory backends:
- jsonl (default): JSONL audit mirror, no external dependencies
- sqlite: SQLite-backed structured memory, opt-in via config

Safe defaults:
  OMINI_MEMORY_BACKEND=jsonl
  OMINI_ENABLE_SQLITE_MEMORY=false
  OMINI_SQLITE_MEMORY_PATH=.omni/memory/omni-memory.sqlite

See docs/memory/sqlite-memory-facade.md for full architecture.
"""

from .jsonl_audit_mirror import JSONLAuditMirror
from .autonomy_session_cleanup import (
    AutonomySessionCleanupResult,
    cleanup_expired_autonomy_session_states_manual,
)
from .memory_facade import MemoryFacade
from .memory_models import (
    MEMORY_BACKEND_JSONL,
    MEMORY_BACKEND_SQLITE,
    SAFE_DEFAULT_BACKEND,
    AutonomySessionStateRecord,
    ConversationRecord,
    DRY_RUN_REPLAN_PLAN_EVIDENCE_EVENT_TYPE,
    DRY_RUN_RETRY_PLAN_EVIDENCE_EVENT_TYPE,
    DryRunReplanPlanEvidenceRecord,
    DryRunRetryPlanEvidenceRecord,
    EpisodeRecord,
    GovernanceEventRecord,
    LearningArtifactRecord,
    MemoryRecord,
    MessageRecord,
    ProviderAttemptRecord,
    RuntimeEventRecord,
    SemanticFactRecord,
    redact_payload,
    utc_now_iso,
)
from .runtime_integration import (
    record_runtime_event,
    record_provider_attempt,
    record_governance_event,
    close as close_runtime_integration,
    reset_for_testing,
)
from .sqlite_adapter import SQLiteAdapter

__all__ = [
    "MemoryFacade",
    "SQLiteAdapter",
    "JSONLAuditMirror",
    "MemoryRecord",
    "ConversationRecord",
    "MessageRecord",
    "EpisodeRecord",
    "SemanticFactRecord",
    "RuntimeEventRecord",
    "ProviderAttemptRecord",
    "GovernanceEventRecord",
    "LearningArtifactRecord",
    "AutonomySessionStateRecord",
    "DryRunReplanPlanEvidenceRecord",
    "DryRunRetryPlanEvidenceRecord",
    "DRY_RUN_REPLAN_PLAN_EVIDENCE_EVENT_TYPE",
    "DRY_RUN_RETRY_PLAN_EVIDENCE_EVENT_TYPE",
    "AutonomySessionCleanupResult",
    "MEMORY_BACKEND_JSONL",
    "MEMORY_BACKEND_SQLITE",
    "SAFE_DEFAULT_BACKEND",
    "redact_payload",
    "utc_now_iso",
    "record_runtime_event",
    "record_provider_attempt",
    "record_governance_event",
    "close_runtime_integration",
    "reset_for_testing",
    "cleanup_expired_autonomy_session_states_manual",
]
