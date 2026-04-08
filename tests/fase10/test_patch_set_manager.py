from __future__ import annotations

import shutil
import sys
import unittest
from pathlib import Path
from uuid import uuid4


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.patch_set_manager import (  # noqa: E402
    apply_patch_set,
    build_patch_set,
    review_patch_set,
    rollback_patch_set,
    summarize_patch_set,
)


class PatchSetManagerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_root = PROJECT_ROOT / ".phase9-temp" / f"fase2-patchset-{uuid4().hex[:8]}"
        shutil.rmtree(self.temp_root, ignore_errors=True)
        (self.temp_root / "pkg").mkdir(parents=True, exist_ok=True)
        (self.temp_root / "pkg" / "mod.py").write_text("VALUE = 1\n", encoding="utf-8")
        (self.temp_root / "pkg" / "__init__.py").write_text("", encoding="utf-8")

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_root, ignore_errors=True)

    def test_build_and_summarize_patch_set(self) -> None:
        patch_set = build_patch_set(
            workspace_root=self.temp_root,
            file_updates=[
                {"file_path": "pkg/mod.py", "new_content": "VALUE = 2\n", "confidence_score": 0.9},
                {"file_path": "pkg/__init__.py", "new_content": "from .mod import VALUE\n"},
            ],
            dependency_notes=["pkg exports VALUE"],
            verification_plan={"verification_modes": ["targeted-tests"]},
        )

        self.assertEqual(len(patch_set["affected_files"]), 2)
        self.assertEqual(patch_set["risk_level"], "medium")
        summary = summarize_patch_set(patch_set=patch_set)
        self.assertEqual(summary["patch_set_id"], patch_set["patch_set_id"])
        self.assertEqual(summary["verification_plan"]["verification_modes"], ["targeted-tests"])

    def test_apply_and_rollback_patch_set(self) -> None:
        patch_set = build_patch_set(
            workspace_root=self.temp_root,
            file_updates=[
                {"file_path": "pkg/mod.py", "new_content": "VALUE = 2\n", "confidence_score": 0.9},
            ],
        )
        review = review_patch_set(patch_set=patch_set)
        self.assertTrue(review["accepted"])

        applied = apply_patch_set(workspace_root=self.temp_root, patch_set=patch_set)
        self.assertTrue(applied["ok"])
        self.assertIn("VALUE = 2", (self.temp_root / "pkg" / "mod.py").read_text(encoding="utf-8"))

        rolled_back = rollback_patch_set(workspace_root=self.temp_root, patch_set=patch_set)
        self.assertTrue(rolled_back["ok"])
        self.assertIn("VALUE = 1", (self.temp_root / "pkg" / "mod.py").read_text(encoding="utf-8"))

    def test_apply_returns_descriptive_error_on_hash_mismatch(self) -> None:
        patch_set = build_patch_set(
            workspace_root=self.temp_root,
            file_updates=[{"file_path": "pkg/mod.py", "new_content": "VALUE = 2\n"}],
        )
        (self.temp_root / "pkg" / "mod.py").write_text("VALUE = 999\n", encoding="utf-8")
        result = apply_patch_set(workspace_root=self.temp_root, patch_set=patch_set)
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "content_hash_mismatch")


if __name__ == "__main__":
    unittest.main()
