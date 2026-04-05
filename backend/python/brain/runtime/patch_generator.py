from __future__ import annotations

import difflib
import hashlib
import os
import shutil
import time
from pathlib import Path
from typing import Any


def build_patch(*, workspace_root: Path, file_path: str, new_content: str, confidence_score: float = 0.5) -> dict[str, Any]:
    target = (workspace_root / file_path).resolve()
    original_content = target.read_text(encoding="utf-8") if target.exists() else ""
    original_hash = hashlib.sha256(original_content.encode("utf-8")).hexdigest()
    diff = "\n".join(
        difflib.unified_diff(
            original_content.splitlines(),
            new_content.splitlines(),
            fromfile=file_path,
            tofile=file_path,
            lineterm="",
        )
    )
    return {
        "file_path": file_path,
        "original_content_hash": original_hash,
        "patch_diff": diff,
        "confidence_score": max(0.0, min(1.0, float(confidence_score))),
        "original_content": original_content,
        "new_content": new_content,
    }


def apply_patch(*, workspace_root: Path, patch: dict[str, Any]) -> dict[str, Any]:
    file_path = str(patch.get("file_path", ""))
    target = (workspace_root / file_path).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    current_content = target.read_text(encoding="utf-8") if target.exists() else ""
    current_hash = hashlib.sha256(current_content.encode("utf-8")).hexdigest()
    if current_hash != patch.get("original_content_hash"):
      return {
          "ok": False,
          "error": "content_hash_mismatch",
          "file_path": file_path,
      }
    target.write_text(str(patch.get("new_content", "")), encoding="utf-8")
    _refresh_python_artifacts(target)
    return {
        "ok": True,
        "file_path": file_path,
    }


def rollback_patch(*, workspace_root: Path, patch: dict[str, Any]) -> None:
    target = (workspace_root / str(patch.get("file_path", ""))).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(str(patch.get("original_content", "")), encoding="utf-8")
    _refresh_python_artifacts(target)


def review_patch_risk(*, patch: dict[str, Any]) -> dict[str, Any]:
    file_path = str(patch.get("file_path", ""))
    diff = str(patch.get("patch_diff", ""))
    warnings: list[str] = []
    if file_path.endswith(("package-lock.json", "Cargo.lock", ".env")):
        warnings.append("sensitive_or_generated_file")
    if diff.count("\n+") > 120 or diff.count("\n-") > 120:
        warnings.append("large_patch")
    if "rm -rf" in diff or "Remove-Item" in diff:
        warnings.append("destructive_command_pattern")
    return {
        "accepted": len(warnings) == 0,
        "risk_level": "high" if warnings else "low",
        "warnings": warnings,
    }


def _refresh_python_artifacts(target: Path) -> None:
    future_timestamp = time.time() + 2
    os.utime(target, (future_timestamp, future_timestamp))
    pycache_dir = target.parent / "__pycache__"
    if pycache_dir.exists():
        shutil.rmtree(pycache_dir, ignore_errors=True)
