from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import uuid4

from .models import utc_now_iso


class EvolutionApplicationStatus(str, Enum):
    PENDING = "pending"
    APPLYING = "applying"
    APPLIED = "applied"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass(slots=True)
class EvolutionApplicationAttempt:
    application_id: str
    proposal_id: str
    started_at: str
    finished_at: str
    status: str
    execution_mode: str
    patch_summary: dict[str, Any] = field(default_factory=dict)
    target_scope: str = ""
    precheck_result: dict[str, Any] = field(default_factory=dict)
    postcheck_result: dict[str, Any] = field(default_factory=dict)
    rollback_available: bool = False
    rollback_executed: bool = False
    rollback_reason: str | None = None
    governance: dict[str, Any] = field(default_factory=dict)
    extensions: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def build(
        cls,
        *,
        proposal_id: str,
        status: EvolutionApplicationStatus,
        execution_mode: str,
        patch_summary: dict[str, Any],
        target_scope: str,
        precheck_result: dict[str, Any],
        postcheck_result: dict[str, Any] | None = None,
        rollback_available: bool = False,
        rollback_executed: bool = False,
        rollback_reason: str | None = None,
        governance_reason: str,
        governance_source: str,
        governance_severity: str,
        extensions: dict[str, Any] | None = None,
    ) -> "EvolutionApplicationAttempt":
        now = utc_now_iso()
        return cls(
            application_id=f"evo-application-{uuid4().hex}",
            proposal_id=str(proposal_id or "").strip(),
            started_at=now,
            finished_at=now,
            status=status.value,
            execution_mode=str(execution_mode or "governed_sandbox"),
            patch_summary=dict(patch_summary or {}),
            target_scope=str(target_scope or ""),
            precheck_result=dict(precheck_result or {}),
            postcheck_result=dict(postcheck_result or {}),
            rollback_available=bool(rollback_available),
            rollback_executed=bool(rollback_executed),
            rollback_reason=str(rollback_reason).strip() if rollback_reason else None,
            governance={
                "governed": True,
                "reason": str(governance_reason or "").strip(),
                "source": str(governance_source or "").strip(),
                "severity": str(governance_severity or "").strip().lower(),
                "at": now,
            },
            extensions=dict(extensions or {}),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "application_id": self.application_id,
            "proposal_id": self.proposal_id,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "status": self.status,
            "execution_mode": self.execution_mode,
            "patch_summary": dict(self.patch_summary),
            "target_scope": self.target_scope,
            "precheck_result": dict(self.precheck_result),
            "postcheck_result": dict(self.postcheck_result),
            "rollback_available": self.rollback_available,
            "rollback_executed": self.rollback_executed,
            "rollback_reason": self.rollback_reason,
            "governance": dict(self.governance),
            "extensions": dict(self.extensions),
        }


def _sandbox_root(root: Path) -> Path:
    return root / ".logs" / "fusion-runtime" / "evolution" / "sandbox"


def _resolve_target_path(*, root: Path, target_path: str) -> Path:
    candidate = (root / str(target_path or "")).resolve()
    sandbox_root = _sandbox_root(root).resolve()
    try:
        candidate.relative_to(sandbox_root)
    except ValueError as error:
        raise ValueError("target_path must stay inside .logs/fusion-runtime/evolution/sandbox") from error
    return candidate


def build_application_precheck(
    *,
    root: Path,
    proposal_status: str,
    latest_validation: dict[str, Any] | None,
    patch_payload: dict[str, Any] | None,
) -> dict[str, Any]:
    issues: list[str] = []
    payload = dict(patch_payload or {})
    if proposal_status != "approved":
        issues.append("proposal_not_approved")
    if not isinstance(latest_validation, dict):
        issues.append("missing_latest_validation")
    else:
        outcome = str(latest_validation.get("outcome", "")).strip().lower()
        if outcome not in {"valid", "risky"}:
            issues.append("validation_outcome_not_applicable")
    mode = str(payload.get("mode", "")).strip().lower()
    if mode != "text_replace":
        issues.append("unsupported_patch_mode")
    target_path = str(payload.get("target_path", "")).strip()
    if not target_path:
        issues.append("missing_target_path")
    replace_with = payload.get("replace_with", None)
    if not isinstance(replace_with, str):
        issues.append("missing_replace_with")
    if target_path:
        try:
            _resolve_target_path(root=root, target_path=target_path)
        except ValueError:
            issues.append("target_out_of_allowed_scope")
    return {
        "eligible": len(issues) == 0,
        "issues": issues,
        "target_path": target_path,
        "mode": mode,
    }


def execute_controlled_patch_application(
    *,
    root: Path,
    proposal_id: str,
    patch_payload: dict[str, Any],
    execution_mode: str = "governed_sandbox",
) -> EvolutionApplicationAttempt:
    precheck = build_application_precheck(
        root=root,
        proposal_status="approved",
        latest_validation={"outcome": "valid"},
        patch_payload=patch_payload,
    )
    # Precheck is expected to be validated by service eligibility gate.
    target_path = str(precheck.get("target_path", ""))
    target = _resolve_target_path(root=root, target_path=target_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    original = target.read_text(encoding="utf-8") if target.exists() else ""
    replace_with = str(patch_payload.get("replace_with", ""))
    expected_contains = str(patch_payload.get("postcheck_contains", "")).strip()
    target.write_text(replace_with, encoding="utf-8")
    content = target.read_text(encoding="utf-8")
    post_ok = expected_contains in content if expected_contains else content == replace_with
    if post_ok:
        return EvolutionApplicationAttempt.build(
            proposal_id=proposal_id,
            status=EvolutionApplicationStatus.APPLIED,
            execution_mode=execution_mode,
            patch_summary={
                "mode": "text_replace",
                "target_path": target_path,
                "bytes_written": len(replace_with.encode("utf-8")),
            },
            target_scope=target_path,
            precheck_result=precheck,
            postcheck_result={"ok": True, "expected_contains": expected_contains or None},
            rollback_available=True,
            rollback_executed=False,
            governance_reason="application_applied",
            governance_source="system_application",
            governance_severity="normal",
            extensions={"rollback_snapshot": original},
        )
    target.write_text(original, encoding="utf-8")
    return EvolutionApplicationAttempt.build(
        proposal_id=proposal_id,
        status=EvolutionApplicationStatus.ROLLED_BACK,
        execution_mode=execution_mode,
        patch_summary={
            "mode": "text_replace",
            "target_path": target_path,
            "bytes_written": len(replace_with.encode("utf-8")),
        },
        target_scope=target_path,
        precheck_result=precheck,
        postcheck_result={"ok": False, "expected_contains": expected_contains or None, "error": "postcheck_failed"},
        rollback_available=True,
        rollback_executed=True,
        rollback_reason="postcheck_failed",
        governance_reason="rollback_executed",
        governance_source="system_application",
        governance_severity="warning",
        extensions={"rollback_snapshot": original},
    )


def execute_explicit_rollback(
    *,
    root: Path,
    proposal_id: str,
    application_id: str,
    rollback_snapshot: str,
    target_path: str,
    decision_source: str,
    rollback_reason: str,
) -> EvolutionApplicationAttempt:
    target = _resolve_target_path(root=root, target_path=target_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(str(rollback_snapshot), encoding="utf-8")
    return EvolutionApplicationAttempt.build(
        proposal_id=proposal_id,
        status=EvolutionApplicationStatus.ROLLED_BACK,
        execution_mode="explicit_rollback",
        patch_summary={"target_path": target_path},
        target_scope=target_path,
        precheck_result={"ok": True, "source_application_id": application_id},
        postcheck_result={"ok": True},
        rollback_available=True,
        rollback_executed=True,
        rollback_reason=rollback_reason,
        governance_reason="rollback_executed",
        governance_source=decision_source,
        governance_severity="warning",
        extensions={"source_application_id": application_id},
    )
