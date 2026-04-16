from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4

from brain.runtime.control.governance_taxonomy import (
    GovernanceReason,
    GovernanceSeverity,
    GovernanceSource,
    governance_dict_for_resolution,
    map_legacy_reason_string,
    normalize_governance_source,
)

from .models import utc_now_iso

MAX_TEXT_LEN = 2000


class EvolutionProposalStatus(str, Enum):
    PROPOSED = "proposed"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    DEFERRED = "deferred"


class EvolutionRiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


def _as_clean_text(name: str, value: object, *, max_len: int = MAX_TEXT_LEN) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{name} must be a non-empty string")
    if len(text) > max_len:
        raise ValueError(f"{name} exceeds maximum length ({max_len})")
    return text


def _normalize_governance_triplet(reason: str, source: str, severity: str) -> tuple[str, str, str]:
    normalized_reason = map_legacy_reason_string(reason, fallback=GovernanceReason.UNSAFE_STATE).value
    normalized_source = normalize_governance_source(source).value
    try:
        normalized_severity = GovernanceSeverity(str(severity or "").strip().lower()).value
    except ValueError:
        # Keep alignment with control taxonomy even when caller omits explicit severity.
        normalized_severity = governance_dict_for_resolution(
            reason=normalized_reason,
            decision_source=normalized_source,
        )["severity"]
    return normalized_reason, normalized_source, normalized_severity


@dataclass(slots=True)
class EvolutionProposalRecord:
    proposal_id: str
    title: str
    summary: str
    target_area: str
    proposal_type: str
    rationale: str
    requested_change: str
    expected_benefit: str
    risk_level: str
    status: str
    created_at: str
    updated_at: str
    governance: dict[str, Any] = field(default_factory=dict)
    validation: dict[str, Any] = field(default_factory=dict)
    latest_validation: dict[str, Any] | None = None
    validation_history: list[dict[str, Any]] = field(default_factory=list)
    latest_application: dict[str, Any] | None = None
    application_history: list[dict[str, Any]] = field(default_factory=list)
    extensions: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def build(
        cls,
        *,
        title: str,
        summary: str,
        target_area: str,
        proposal_type: str,
        rationale: str,
        requested_change: str,
        expected_benefit: str,
        risk_level: str,
        governance_reason: str = GovernanceReason.GOVERNANCE_HOLD.value,
        governance_source: str = GovernanceSource.GOVERNANCE.value,
        governance_severity: str = GovernanceSeverity.WARNING.value,
        validation: dict[str, Any] | None = None,
        extensions: dict[str, Any] | None = None,
    ) -> "EvolutionProposalRecord":
        risk = EvolutionRiskLevel(_as_clean_text("risk_level", risk_level, max_len=24).lower()).value
        now = utc_now_iso()
        reason, source, severity = _normalize_governance_triplet(
            governance_reason,
            governance_source,
            governance_severity,
        )
        return cls(
            proposal_id=f"evo-proposal-{uuid4().hex}",
            title=_as_clean_text("title", title, max_len=200),
            summary=_as_clean_text("summary", summary),
            target_area=_as_clean_text("target_area", target_area, max_len=120),
            proposal_type=_as_clean_text("proposal_type", proposal_type, max_len=120),
            rationale=_as_clean_text("rationale", rationale),
            requested_change=_as_clean_text("requested_change", requested_change),
            expected_benefit=_as_clean_text("expected_benefit", expected_benefit),
            risk_level=risk,
            status=EvolutionProposalStatus.PROPOSED.value,
            created_at=now,
            updated_at=now,
            governance={
                "governed": True,
                "reason": reason,
                "source": source,
                "severity": severity,
                "history": [
                    {
                        "at": now,
                        "status": EvolutionProposalStatus.PROPOSED.value,
                        "reason": reason,
                        "source": source,
                        "severity": severity,
                    }
                ],
            },
            validation=dict(validation or {"shape_valid": True, "checked_at": now, "errors": []}),
            latest_validation=None,
            validation_history=[],
            latest_application=None,
            application_history=[],
            extensions=dict(extensions or {}),
        )

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "EvolutionProposalRecord":
        proposal_id = _as_clean_text("proposal_id", payload.get("proposal_id"), max_len=120)
        status = EvolutionProposalStatus(
            _as_clean_text("status", payload.get("status"), max_len=32).lower()
        ).value
        risk = EvolutionRiskLevel(_as_clean_text("risk_level", payload.get("risk_level"), max_len=24).lower()).value
        governance = dict(payload.get("governance", {}) or {})
        validation = dict(payload.get("validation", {}) or {})
        latest_validation = payload.get("latest_validation", None)
        validation_history = [
            dict(item)
            for item in (payload.get("validation_history", []) or [])
            if isinstance(item, dict)
        ]
        latest_application = payload.get("latest_application", None)
        application_history = [
            dict(item)
            for item in (payload.get("application_history", []) or [])
            if isinstance(item, dict)
        ]
        extensions = dict(payload.get("extensions", {}) or {})
        reason, source, severity = _normalize_governance_triplet(
            str(governance.get("reason", GovernanceReason.UNSAFE_STATE.value)),
            str(governance.get("source", GovernanceSource.RUNTIME.value)),
            str(governance.get("severity", GovernanceSeverity.NORMAL.value)),
        )
        governance["governed"] = bool(governance.get("governed", True))
        governance["reason"] = reason
        governance["source"] = source
        governance["severity"] = severity
        if not isinstance(governance.get("history"), list):
            governance["history"] = []
        return cls(
            proposal_id=proposal_id,
            title=_as_clean_text("title", payload.get("title"), max_len=200),
            summary=_as_clean_text("summary", payload.get("summary")),
            target_area=_as_clean_text("target_area", payload.get("target_area"), max_len=120),
            proposal_type=_as_clean_text("proposal_type", payload.get("proposal_type"), max_len=120),
            rationale=_as_clean_text("rationale", payload.get("rationale")),
            requested_change=_as_clean_text("requested_change", payload.get("requested_change")),
            expected_benefit=_as_clean_text("expected_benefit", payload.get("expected_benefit")),
            risk_level=risk,
            status=status,
            created_at=_as_clean_text("created_at", payload.get("created_at"), max_len=80),
            updated_at=_as_clean_text("updated_at", payload.get("updated_at"), max_len=80),
            governance=governance,
            validation=validation,
            latest_validation=dict(latest_validation) if isinstance(latest_validation, dict) else None,
            validation_history=validation_history,
            latest_application=dict(latest_application) if isinstance(latest_application, dict) else None,
            application_history=application_history,
            extensions=extensions,
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            "title": self.title,
            "summary": self.summary,
            "target_area": self.target_area,
            "proposal_type": self.proposal_type,
            "rationale": self.rationale,
            "requested_change": self.requested_change,
            "expected_benefit": self.expected_benefit,
            "risk_level": self.risk_level,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "governance": dict(self.governance),
            "validation": dict(self.validation),
            "latest_validation": dict(self.latest_validation) if isinstance(self.latest_validation, dict) else None,
            "validation_history": [dict(item) for item in self.validation_history],
            "latest_application": dict(self.latest_application) if isinstance(self.latest_application, dict) else None,
            "application_history": [dict(item) for item in self.application_history],
            "extensions": dict(self.extensions),
        }

    def append_validation_result(self, validation_result: dict[str, Any]) -> None:
        """Append-only validation history with latest pointer update."""
        entry = dict(validation_result or {})
        if not entry:
            raise ValueError("validation_result must be a non-empty object")
        self.validation_history = [*self.validation_history, entry][-100:]
        self.latest_validation = dict(entry)
        self.updated_at = utc_now_iso()

    def append_application_attempt(self, application_attempt: dict[str, Any]) -> None:
        """Append-only application history with latest pointer update."""
        entry = dict(application_attempt or {})
        if not entry:
            raise ValueError("application_attempt must be a non-empty object")
        self.application_history = [*self.application_history, entry][-100:]
        self.latest_application = dict(entry)
        self.updated_at = utc_now_iso()

    def transition_status(
        self,
        *,
        next_status: EvolutionProposalStatus,
        governance_reason: str,
        governance_source: str,
        governance_severity: str | None = None,
    ) -> None:
        self.status = next_status.value
        self.updated_at = utc_now_iso()
        reason, source, severity = _normalize_governance_triplet(
            governance_reason,
            governance_source,
            str(governance_severity or ""),
        )
        self.governance = dict(self.governance)
        self.governance["governed"] = True
        self.governance["reason"] = reason
        self.governance["source"] = source
        self.governance["severity"] = severity
        history = self.governance.get("history")
        if not isinstance(history, list):
            history = []
        history.append(
            {
                "at": self.updated_at,
                "status": self.status,
                "reason": reason,
                "source": source,
                "severity": severity,
            }
        )
        self.governance["history"] = history[-50:]
