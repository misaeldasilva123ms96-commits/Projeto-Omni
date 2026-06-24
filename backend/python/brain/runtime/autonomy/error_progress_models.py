"""Smart Error Progress Tracker models.

Defines the data contracts for error fingerprinting, progress/stagnation
classification, and strategy tracking used by the advisory Autonomy
Controller. All fields are derived from safe metadata only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


_FINGERPRINT_SEPARATOR = "|||"


@dataclass(frozen=True, slots=True)
class ErrorFingerprint:
    error_type: str = ""
    failure_class: str = ""
    failure_reason_category: str = ""
    runtime_mode: str = ""
    provider_failure_type: str = ""
    tool_category: str = ""
    governance_decision: str = ""
    protected_file_flag: bool = False
    secret_detected_flag: bool = False

    @property
    def fingerprint_id(self) -> str:
        raw = _FINGERPRINT_SEPARATOR.join([
            self.error_type or "",
            self.failure_class or "",
            self.failure_reason_category or "",
            self.runtime_mode or "",
            self.provider_failure_type or "",
            self.tool_category or "",
            self.governance_decision or "",
            "1" if self.protected_file_flag else "0",
            "1" if self.secret_detected_flag else "0",
        ])
        return sha256(raw.encode("utf-8")).hexdigest()[:12]

    def is_empty(self) -> bool:
        return not any([
            self.error_type,
            self.failure_class,
            self.failure_reason_category,
            self.runtime_mode,
            self.provider_failure_type,
            self.tool_category,
            self.governance_decision,
            self.protected_file_flag,
            self.secret_detected_flag,
        ])

    def as_dict(self) -> dict[str, Any]:
        return {
            "fingerprint_id": self.fingerprint_id,
            "error_type": self.error_type,
            "failure_class": self.failure_class,
            "failure_reason_category": self.failure_reason_category,
            "runtime_mode": self.runtime_mode,
            "provider_failure_type": self.provider_failure_type,
            "tool_category": self.tool_category,
            "governance_decision": self.governance_decision,
            "protected_file_flag": self.protected_file_flag,
            "secret_detected_flag": self.secret_detected_flag,
        }


@dataclass(slots=True)
class StrategyAttempt:
    strategy_name: str
    fingerprint_id: str = ""
    timestamp: str = field(default_factory=_utc_now)

    def as_dict(self) -> dict[str, Any]:
        return {
            "strategy_name": self.strategy_name,
            "fingerprint_id": self.fingerprint_id,
            "timestamp": self.timestamp,
        }


@dataclass(slots=True)
class ProgressTrackerOutput:
    fingerprint_id: str = ""
    is_new_error: bool = False
    is_repeated_error: bool = False
    progress_score: int = 0
    stagnation_score: int = 0
    stagnant_attempts: int = 0
    distinct_error_count: int = 0
    strategies_attempted: list[str] = field(default_factory=list)
    repeated_strategy_count: int = 0
    recommended_decision_hint: str = ""
    evidence_summary: str = ""

    @property
    def is_progress(self) -> bool:
        return self.progress_score > self.stagnation_score

    @property
    def is_stagnation(self) -> bool:
        return self.stagnation_score > self.progress_score

    def as_dict(self) -> dict[str, Any]:
        return {
            "fingerprint_id": self.fingerprint_id,
            "is_new_error": self.is_new_error,
            "is_repeated_error": self.is_repeated_error,
            "progress_score": self.progress_score,
            "stagnation_score": self.stagnation_score,
            "is_progress": self.is_progress,
            "is_stagnation": self.is_stagnation,
            "stagnant_attempts": self.stagnant_attempts,
            "distinct_error_count": self.distinct_error_count,
            "strategies_attempted": self.strategies_attempted,
            "repeated_strategy_count": self.repeated_strategy_count,
            "recommended_decision_hint": self.recommended_decision_hint,
            "evidence_summary": self.evidence_summary,
        }
