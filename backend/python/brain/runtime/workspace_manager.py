from __future__ import annotations

import hashlib
import shutil
from pathlib import Path
from typing import Any
from uuid import uuid4


class WorkspaceManager:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def create_task_workspace(self, *, run_id: str, source_root: Path | None = None) -> dict[str, Any]:
        source = (source_root or self.root).resolve()
        base_root = (source.parent / ".omini-task-workspaces").resolve()
        base_root.mkdir(parents=True, exist_ok=True)
        task_root = (base_root / f"omini-{run_id}-{uuid4().hex[:8]}").resolve()
        shutil.copytree(source, task_root, dirs_exist_ok=True)
        return {
            "run_id": run_id,
            "source_root": str(source),
            "workspace_root": str(task_root),
            "snapshot": self.snapshot_workspace(task_root),
        }

    def snapshot_workspace(self, workspace_root: Path) -> dict[str, Any]:
        files: list[dict[str, Any]] = []
        for file_path in workspace_root.rglob("*"):
            if not file_path.is_file():
                continue
            relative_path = file_path.relative_to(workspace_root)
            if any(part in {".git", ".logs", "node_modules", "__pycache__", "target", "dist"} for part in relative_path.parts):
                continue
            files.append(
                {
                    "path": str(relative_path).replace("\\", "/"),
                    "sha256": self._hash_file(file_path),
                }
            )
        return {
            "file_count": len(files),
            "files": files[:2000],
        }

    def rollback_files(self, workspace_root: Path, backups: dict[str, str]) -> None:
        for relative_path, original_content in backups.items():
            target = workspace_root / relative_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(original_content, encoding="utf-8")

    @staticmethod
    def _hash_file(file_path: Path) -> str:
        digest = hashlib.sha256()
        digest.update(file_path.read_bytes())
        return digest.hexdigest()
