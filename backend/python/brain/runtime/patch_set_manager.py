from __future__ import annotations

import logging
from hashlib import sha256
from pathlib import Path
from typing import Any
from uuid import uuid4

from brain.runtime.patch_generator import apply_patch, build_patch, review_patch_risk, rollback_patch

LOGGER = logging.getLogger(__name__)


def build_patch_set(
    *,
    workspace_root: Path,
    file_updates: list[dict[str, Any]],
    dependency_notes: list[str] | None = None,
    verification_plan: dict[str, Any] | None = None,
) -> dict[str, Any]:
    try:
        patches = []
        affected_files: list[str] = []
        for update in file_updates:
            file_path = str(update.get("file_path", "")).strip()
            if not file_path:
                continue
            patches.append(
                build_patch(
                    workspace_root=workspace_root,
                    file_path=file_path,
                    new_content=str(update.get("new_content", "")),
                    confidence_score=float(update.get("confidence_score", 0.6) or 0.6),
                )
            )
            affected_files.append(file_path)
        risk_level = "high" if len(affected_files) >= 5 else "medium" if len(affected_files) >= 2 else "low"
        return {
            "patch_set_id": f"patchset-{uuid4().hex[:10]}",
            "affected_files": affected_files,
            "dependency_notes": dependency_notes or [],
            "risk_level": risk_level,
            "verification_plan": verification_plan or {},
            "patches": patches,
        }
    except Exception as error:
        LOGGER.exception("failed to build patch set")
        return {
            "patch_set_id": f"patchset-{uuid4().hex[:10]}",
            "affected_files": [],
            "dependency_notes": dependency_notes or [],
            "risk_level": "high",
            "verification_plan": verification_plan or {},
            "patches": [],
            "error": f"patch_set_build_failed: {error}",
        }


def review_patch_set(*, patch_set: dict[str, Any]) -> dict[str, Any]:
    try:
        warnings: list[str] = []
        for patch in patch_set.get("patches", []):
            review = review_patch_risk(patch=patch)
            if not review.get("accepted"):
                warnings.extend(review.get("warnings", []))
        if len(patch_set.get("affected_files", [])) >= 5:
            warnings.append("wide_patch_set")
        if patch_set.get("error"):
            warnings.append("patch_set_build_failed")
        return {
            "accepted": len(warnings) == 0,
            "risk_level": patch_set.get("risk_level", "medium"),
            "warnings": sorted(set(warnings)),
        }
    except Exception as error:
        LOGGER.exception("failed to review patch set")
        return {
            "accepted": False,
            "risk_level": "high",
            "warnings": [f"patch_set_review_failed:{error}"],
        }


def apply_patch_set(*, workspace_root: Path, patch_set: dict[str, Any]) -> dict[str, Any]:
    applied: list[str] = []
    try:
        for patch in patch_set.get("patches", []):
            result = apply_patch(workspace_root=workspace_root, patch=patch)
            if not result.get("ok"):
                rollback_patch_set(workspace_root=workspace_root, patch_set=patch_set, applied_files=applied)
                return {
                    "ok": False,
                    "patch_set_id": patch_set.get("patch_set_id"),
                    "error": result.get("error"),
                    "applied_files": applied,
                }
            applied.append(str(patch.get("file_path", "")))
        return {
            "ok": True,
            "patch_set_id": patch_set.get("patch_set_id"),
            "applied_files": applied,
            "verification_plan": patch_set.get("verification_plan", {}),
        }
    except Exception as error:
        LOGGER.exception("failed to apply patch set")
        rollback_patch_set(workspace_root=workspace_root, patch_set=patch_set, applied_files=applied)
        return {
            "ok": False,
            "patch_set_id": patch_set.get("patch_set_id"),
            "error": f"patch_set_apply_failed: {error}",
            "applied_files": applied,
        }


def rollback_patch_set(*, workspace_root: Path, patch_set: dict[str, Any], applied_files: list[str] | None = None) -> dict[str, Any]:
    applied_set = set(applied_files or patch_set.get("affected_files", []))
    rolled_back = []
    try:
        for patch in reversed(patch_set.get("patches", [])):
            if str(patch.get("file_path", "")) not in applied_set:
                continue
            rollback_patch(workspace_root=workspace_root, patch=patch)
            rolled_back.append(str(patch.get("file_path", "")))
        return {
            "ok": True,
            "patch_set_id": patch_set.get("patch_set_id"),
            "rolled_back_files": rolled_back,
        }
    except Exception as error:
        LOGGER.exception("failed to rollback patch set")
        return {
            "ok": False,
            "patch_set_id": patch_set.get("patch_set_id"),
            "rolled_back_files": rolled_back,
            "error": f"patch_set_rollback_failed: {error}",
        }


def summarize_patch_set(*, patch_set: dict[str, Any]) -> dict[str, Any]:
    digest = sha256("|".join(sorted(patch_set.get("affected_files", []))).encode("utf-8")).hexdigest()
    return {
        "patch_set_id": patch_set.get("patch_set_id"),
        "affected_files": patch_set.get("affected_files", []),
        "risk_level": patch_set.get("risk_level", "medium"),
        "verification_plan": patch_set.get("verification_plan", {}),
        "digest": digest,
    }
