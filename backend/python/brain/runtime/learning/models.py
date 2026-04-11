from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_iso_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


class LearningSourceType(str, Enum):
    EXECUTION_RECEIPT = "execution_receipt"
    REPAIR_RECEIPT = "repair_receipt"
    PLAN_CHECKPOINT = "plan_checkpoint"
    OPERATIONAL_SUMMARY = "operational_summary"
    CONTINUATION_DECISION = "continuation_decision"
    CONTINUATION_EVALUATION = "continuation_evaluation"


class LearningSignalType(str, Enum):
    PREFERRED_REPAIR_STRATEGY = "preferred_repair_strategy"
    DISCOURAGED_RETRY_PATTERN = "discouraged_retry_pattern"
    PREFERRED_CONTINUATION_DECISION = "preferred_continuation_decision"
    HIGH_RISK_RECURRENCE_ALERT = "high_risk_recurrence_alert"
    RESUME_CONFIDENCE_HINT = "resume_confidence_hint"
    STEP_TEMPLATE_SUCCESS_HINT = "step_template_success_hint"


@dataclass(slots=True)
class LearningEvidence:
    evidence_id: str
    source_type: LearningSourceType
    source_artifact_id: str
    session_id: str | None
    task_id: str | None
    plan_id: str | None
    step_id: str | None
    action_type: str
    capability: str
    subsystem: str
    outcome_class: str
    success: bool
    failure_class: str = ""
    retry_count: int = 0
    repair_attempted: bool = False
    repair_promoted: bool = False
    continuation_decision_type: str = ""
    timestamp: str = field(default_factory=utc_now_iso)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def build(
        cls,
        *,
        source_type: LearningSourceType,
        source_artifact_id: str,
        session_id: str | None,
        task_id: str | None,
        plan_id: str | None,
        step_id: str | None,
        action_type: str,
        capability: str,
        subsystem: str,
        outcome_class: str,
        success: bool,
        failure_class: str = "",
        retry_count: int = 0,
        repair_attempted: bool = False,
        repair_promoted: bool = False,
        continuation_decision_type: str = "",
        timestamp: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> "LearningEvidence":
        return cls(
            evidence_id=f"learning-evidence-{uuid4()}",
            source_type=source_type,
            source_artifact_id=source_artifact_id,
            session_id=session_id,
            task_id=task_id,
            plan_id=plan_id,
            step_id=step_id,
            action_type=action_type,
            capability=capability,
            subsystem=subsystem,
            outcome_class=outcome_class,
            success=success,
            failure_class=failure_class,
            retry_count=retry_count,
            repair_attempted=repair_attempted,
            repair_promoted=repair_promoted,
            continuation_decision_type=continuation_decision_type,
            timestamp=timestamp or utc_now_iso(),
            metadata=metadata or {},
        )

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["source_type"] = self.source_type.value
        return payload


@dataclass(slots=True)
class PatternRecord:
    pattern_key: str
    category: str
    success_count: int = 0
    failure_count: int = 0
    total_count: int = 0
    success_ratio: float = 0.0
    recurrence_count: int = 0
    first_seen: str = field(default_factory=utc_now_iso)
    last_seen: str = field(default_factory=utc_now_iso)
    recent_timestamps: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def build(cls, *, pattern_key: str, category: str, metadata: dict[str, Any] | None = None) -> "PatternRecord":
        return cls(pattern_key=pattern_key, category=category, metadata=metadata or {})

    def register_outcome(self, *, success: bool, timestamp: str, metadata: dict[str, Any] | None = None) -> None:
        self.total_count += 1
        self.recurrence_count += 1
        if success:
            self.success_count += 1
        else:
            self.failure_count += 1
        self.success_ratio = self.success_count / self.total_count if self.total_count else 0.0
        if not self.first_seen:
            self.first_seen = timestamp
        self.last_seen = timestamp
        self.recent_timestamps = [*self.recent_timestamps[-9:], timestamp]
        if metadata:
            merged = dict(self.metadata)
            merged.update(metadata)
            self.metadata = merged

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "PatternRecord":
        return cls(
            pattern_key=str(payload.get("pattern_key", "")),
            category=str(payload.get("category", "")),
            success_count=int(payload.get("success_count", 0) or 0),
            failure_count=int(payload.get("failure_count", 0) or 0),
            total_count=int(payload.get("total_count", 0) or 0),
            success_ratio=float(payload.get("success_ratio", 0.0) or 0.0),
            recurrence_count=int(payload.get("recurrence_count", 0) or 0),
            first_seen=str(payload.get("first_seen", utc_now_iso())),
            last_seen=str(payload.get("last_seen", utc_now_iso())),
            recent_timestamps=[str(item) for item in payload.get("recent_timestamps", []) if str(item).strip()],
            metadata=dict(payload.get("metadata", {}) or {}),
        )


@dataclass(slots=True)
class StrategyRanking:
    ranking_id: str
    strategy_key: str
    category: str
    score: float
    confidence: float
    evidence_count: int
    recommendation: str
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def build(
        cls,
        *,
        strategy_key: str,
        category: str,
        score: float,
        confidence: float,
        evidence_count: int,
        recommendation: str,
        metadata: dict[str, Any] | None = None,
    ) -> "StrategyRanking":
        return cls(
            ranking_id=f"strategy-ranking-{uuid4()}",
            strategy_key=strategy_key,
            category=category,
            score=score,
            confidence=confidence,
            evidence_count=evidence_count,
            recommendation=recommendation,
            metadata=metadata or {},
        )

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class LearningPolicy:
    enabled: bool = True
    min_pattern_samples: int = 3
    max_signal_weight: float = 0.30
    allow_policy_hints: bool = True
    allow_strategy_ranking: bool = True
    stale_pattern_days: int = 30

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class LearningSignal:
    signal_id: str
    signal_type: LearningSignalType
    source_pattern_key: str
    confidence: float
    weight: float
    recommendation: str
    evidence_summary: dict[str, Any]
    timestamp: str
    advisory: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def build(
        cls,
        *,
        signal_type: LearningSignalType,
        source_pattern_key: str,
        confidence: float,
        weight: float,
        recommendation: str,
        evidence_summary: dict[str, Any],
        advisory: bool = True,
        metadata: dict[str, Any] | None = None,
    ) -> "LearningSignal":
        return cls(
            signal_id=f"learning-signal-{uuid4()}",
            signal_type=signal_type,
            source_pattern_key=source_pattern_key,
            confidence=confidence,
            weight=weight,
            recommendation=recommendation,
            evidence_summary=evidence_summary,
            timestamp=utc_now_iso(),
            advisory=advisory,
            metadata=metadata or {},
        )

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["signal_type"] = self.signal_type.value
        return payload


@dataclass(slots=True)
class LearningSnapshot:
    snapshot_id: str
    timestamp: str
    pattern_count: int
    signal_count: int
    statistics: dict[str, Any]

    @classmethod
    def build(cls, *, pattern_count: int, signal_count: int, statistics: dict[str, Any]) -> "LearningSnapshot":
        return cls(
            snapshot_id=f"learning-snapshot-{uuid4()}",
            timestamp=utc_now_iso(),
            pattern_count=pattern_count,
            signal_count=signal_count,
            statistics=statistics,
        )

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)
