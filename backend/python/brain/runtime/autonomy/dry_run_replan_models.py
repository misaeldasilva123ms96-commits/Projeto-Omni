"""Dry-run REPLAN planning contracts.

The model is metadata-only and advisory. It does not rewrite prompts or
execute replan actions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


PLAN_TYPE_DRY_RUN_REPLAN = "dry_run_replan"
MAX_SAFE_TEXT_LENGTH = 240
MAX_BLOCK_REASONS = 12

_FORBIDDEN_MARKERS = (
    "raw_prompt",
    "rewritten_prompt",
    "rewritten prompt",
    "prompt rewrite",
    "rewrite prompt",
    "raw_response",
    "raw_provider_payload",
    "raw_receipt",
    "traceback",
    "stack trace",
    "stdout",
    "stderr",
    "command args",
    "api_key",
    "token",
    "secret",
    "password",
    "credential",
    ".env",
    "provider_payload",
    "execute",
    "run command",
    "write file",
    "patch code",
)

_SAFE_CATEGORY_ALLOWLIST = {
    "secret_detected",
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class DryRunReplanPlan:
    plan_id: str
    would_replan: bool
    replan_reason: str = ""
    blocked: bool = False
    block_reasons: list[str] = field(default_factory=list)
    replan_eligibility_score: float = 0.0
    risk_level: str = ""
    source_decision: str = ""
    fingerprint_id: str = ""
    stagnation_score: int = 0
    progress_score: int = 0
    repeated_strategy_count: int = 0
    suggested_strategy: str = ""
    evidence_summary: str = ""
    created_at: str = field(default_factory=utc_now_iso)
    plan_type: str = PLAN_TYPE_DRY_RUN_REPLAN
    advisory: bool = True

    def __post_init__(self) -> None:
        self.plan_type = PLAN_TYPE_DRY_RUN_REPLAN
        self.advisory = True
        self.plan_id = safe_replan_text(self.plan_id, max_length=64)
        self.replan_reason = safe_replan_text(self.replan_reason)
        self.block_reasons = [
            safe_replan_text(reason, max_length=64)
            for reason in self.block_reasons[:MAX_BLOCK_REASONS]
        ]
        self.replan_eligibility_score = _bounded_score(self.replan_eligibility_score)
        self.risk_level = safe_replan_text(self.risk_level, max_length=24)
        self.source_decision = safe_replan_text(self.source_decision, max_length=48)
        self.fingerprint_id = safe_replan_text(self.fingerprint_id, max_length=64)
        self.stagnation_score = _safe_nonnegative_int(self.stagnation_score)
        self.progress_score = _safe_nonnegative_int(self.progress_score)
        self.repeated_strategy_count = _safe_nonnegative_int(self.repeated_strategy_count)
        self.suggested_strategy = safe_replan_text(self.suggested_strategy, max_length=64)
        self.evidence_summary = safe_replan_text(self.evidence_summary)
        self.created_at = safe_replan_text(self.created_at, max_length=64)

    def as_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "plan_type": PLAN_TYPE_DRY_RUN_REPLAN,
            "advisory": True,
            "would_replan": bool(self.would_replan),
            "replan_reason": self.replan_reason,
            "blocked": bool(self.blocked),
            "block_reasons": list(self.block_reasons),
            "replan_eligibility_score": self.replan_eligibility_score,
            "risk_level": self.risk_level,
            "source_decision": self.source_decision,
            "fingerprint_id": self.fingerprint_id,
            "stagnation_score": self.stagnation_score,
            "progress_score": self.progress_score,
            "repeated_strategy_count": self.repeated_strategy_count,
            "suggested_strategy": self.suggested_strategy,
            "evidence_summary": self.evidence_summary,
            "created_at": self.created_at,
        }


def safe_replan_text(value: Any, *, max_length: int = MAX_SAFE_TEXT_LENGTH) -> str:
    text = str(value or "")
    text = text.replace("\r", " ").replace("\n", " ").strip()
    lower = text.lower()
    if lower not in _SAFE_CATEGORY_ALLOWLIST and any(marker in lower for marker in _FORBIDDEN_MARKERS):
        text = "[redacted]"
    if len(text) > max_length:
        text = text[: max(0, max_length - 3)].rstrip() + "..."
    return text


def _bounded_score(value: Any) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return 0.0
    if score < 0:
        return 0.0
    if score > 1:
        return 1.0
    return round(score, 3)


def _safe_nonnegative_int(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0
