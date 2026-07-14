from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.debug_loop_controller import DebugLoopController  # noqa: E402
from brain.runtime.engineering_tools import execute_engineering_action  # noqa: E402
from brain.runtime.patch_generator import apply_patch, build_patch, rollback_patch  # noqa: E402
from brain.runtime.patch_set_manager import build_patch_set, review_patch_set  # noqa: E402
from brain.runtime.workspace_manager import WorkspaceManager  # noqa: E402
from brain.runtime.workspace_paths import WorkspacePathError  # noqa: E402


class WorkspacePathContainmentTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory(prefix="omni-workspace-containment-")
        self.base_root = Path(self.temp_dir.name)
        self.workspace_root = self.base_root / "workspace"
        self.workspace_root.mkdir()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_approved_write_stays_inside_workspace(self) -> None:
        result = self._execute(
            "write_file",
            {"path": "pkg/new.txt", "content": "safe"},
            approval_state="approved",
        )

        self.assertTrue(result["ok"])
        self.assertEqual((self.workspace_root / "pkg" / "new.txt").read_text(encoding="utf-8"), "safe")

    def test_approved_write_rejects_parent_traversal_without_side_effects(self) -> None:
        outside_file = self.base_root / "escaped.txt"

        result = self._execute(
            "write_file",
            {"path": "../escaped.txt", "content": "escaped"},
            approval_state="approved",
        )

        self.assert_path_blocked(result)
        self.assertFalse(outside_file.exists())
        self.assertNotIn(str(self.base_root), str(result))

    def test_approved_write_rejects_absolute_path_even_inside_workspace(self) -> None:
        target = self.workspace_root / "absolute.txt"

        result = self._execute(
            "write_file",
            {"path": str(target), "content": "escaped"},
            approval_state="approved",
        )

        self.assert_path_blocked(result)
        self.assertFalse(target.exists())

    def test_patch_set_rejects_traversal_before_build_or_apply(self) -> None:
        outside_file = self.base_root / "patch-set-escaped.txt"

        result = self._execute(
            "filesystem_patch_set",
            {
                "file_updates": [
                    {"file_path": "safe.txt", "new_content": "safe"},
                    {"file_path": "../patch-set-escaped.txt", "new_content": "escaped"},
                ]
            },
            approval_state="approved",
        )

        self.assert_path_blocked(result)
        self.assertFalse((self.workspace_root / "safe.txt").exists())
        self.assertFalse(outside_file.exists())

    def test_glob_search_rejects_parent_search_root_and_pattern(self) -> None:
        result = self._execute("glob_search", {"path": "..", "pattern": "*.txt"})
        self.assert_path_blocked(result)

        pattern_result = self._execute("glob_search", {"path": ".", "pattern": "../*.txt"})
        self.assertFalse(pattern_result["ok"])
        self.assertEqual(pattern_result["error_payload"]["kind"], "invalid_glob_pattern")

    def test_glob_search_accepts_relative_paths_inside_workspace(self) -> None:
        package_dir = self.workspace_root / "pkg"
        package_dir.mkdir()
        (package_dir / "example.txt").write_text("safe", encoding="utf-8")

        result = self._execute("glob_search", {"path": "pkg", "pattern": "*.txt"})

        self.assertTrue(result["ok"])
        self.assertEqual(result["result_payload"]["filenames"], ["pkg/example.txt"])

    @unittest.skipUnless(os.name == "nt", "Windows-specific path semantics")
    def test_windows_device_and_alternate_data_stream_paths_are_rejected(self) -> None:
        for file_path in ("NUL", "pkg/file.txt:secret", "pkg/trailing. "):
            with self.subTest(file_path=file_path):
                result = self._execute(
                    "write_file",
                    {"path": file_path, "content": "escaped"},
                    approval_state="approved",
                )
                self.assertFalse(result["ok"])
                self.assertEqual(result["error_payload"]["kind"], "invalid_workspace_path")

    def test_symlink_escape_is_rejected_for_read_write_and_glob(self) -> None:
        outside_dir = self.base_root / "outside"
        outside_dir.mkdir()
        (outside_dir / "secret.txt").write_text("secret", encoding="utf-8")
        link = self.workspace_root / "linked-outside"
        try:
            os.symlink(outside_dir, link, target_is_directory=True)
        except (OSError, NotImplementedError) as error:
            if os.name != "nt":
                self.skipTest(f"symlink creation unavailable: {type(error).__name__}")
            completed = subprocess.run(
                ["cmd", "/d", "/c", "mklink", "/J", str(link), str(outside_dir)],
                capture_output=True,
                text=True,
                check=False,
            )
            if completed.returncode != 0:
                self.skipTest("symlink and junction creation unavailable")

        read_result = self._execute("read_file", {"path": "linked-outside/secret.txt"})
        self.assert_path_blocked(read_result)

        write_result = self._execute(
            "write_file",
            {"path": "linked-outside/new.txt", "content": "escaped"},
            approval_state="approved",
        )
        self.assert_path_blocked(write_result)
        self.assertFalse((outside_dir / "new.txt").exists())

        glob_result = self._execute("glob_search", {"path": "linked-outside", "pattern": "*.txt"})
        self.assert_path_blocked(glob_result)

        nested_glob_result = self._execute("glob_search", {"path": ".", "pattern": "linked-outside/*.txt"})
        self.assertTrue(nested_glob_result["ok"])
        self.assertEqual(nested_glob_result["result_payload"]["filenames"], [])

        code_search_result = self._execute("code_search", {"pattern": "secret"})
        self.assertTrue(code_search_result["ok"])
        self.assertEqual(code_search_result["result_payload"]["matches"], [])

        tree_result = self._execute("directory_tree", {"max_depth": 3})
        self.assertTrue(tree_result["ok"])
        self.assertNotIn("linked-outside", str(tree_result["result_payload"]))

        snapshot = WorkspaceManager(self.workspace_root).snapshot_workspace(self.workspace_root)
        self.assertNotIn("linked-outside", str(snapshot))

    def test_forged_patch_payload_cannot_bypass_apply_or_rollback(self) -> None:
        outside_file = self.base_root / "forged.txt"
        forged_patch = {
            "file_path": "../forged.txt",
            "original_content_hash": "",
            "original_content": "",
            "new_content": "escaped",
        }

        apply_result = apply_patch(workspace_root=self.workspace_root, patch=forged_patch)
        rollback_result = rollback_patch(workspace_root=self.workspace_root, patch=forged_patch)

        self.assertFalse(apply_result["ok"])
        self.assertEqual(apply_result["error"], "path_outside_workspace")
        self.assertFalse(rollback_result["ok"])
        self.assertEqual(rollback_result["error"], "path_outside_workspace")
        self.assertFalse(outside_file.exists())

    def test_patch_builder_and_patch_set_fail_closed_on_traversal(self) -> None:
        with self.assertRaises(WorkspacePathError):
            build_patch(
                workspace_root=self.workspace_root,
                file_path="../escaped.txt",
                new_content="escaped",
            )

        patch_set = build_patch_set(
            workspace_root=self.workspace_root,
            file_updates=[{"file_path": "../escaped.txt", "new_content": "escaped"}],
        )
        review = review_patch_set(patch_set=patch_set)
        self.assertIn("patch_set_build_failed", patch_set["error"])
        self.assertFalse(review["accepted"])

    def test_workspace_manager_rollback_rejects_traversal(self) -> None:
        outside_file = self.base_root / "rollback-escaped.txt"
        manager = WorkspaceManager(self.workspace_root)

        with self.assertRaises(WorkspacePathError):
            manager.rollback_files(self.workspace_root, {"../rollback-escaped.txt": "escaped"})

        self.assertFalse(outside_file.exists())

    def test_debug_loop_skips_repository_candidates_outside_workspace(self) -> None:
        outside_file = self.base_root / "outside_candidate.py"
        original_content = "def add(a, b):\n    return a - b\n"
        outside_file.write_text(original_content, encoding="utf-8")
        controller = DebugLoopController(self.workspace_root)

        proposed_patch = controller._propose_fix(
            task_message="fix the failed assertion",
            failure_output="AssertionError: failed",
            repository_analysis={"file_index": [{"path": "../outside_candidate.py"}]},
        )

        self.assertIsNone(proposed_patch)
        self.assertEqual(outside_file.read_text(encoding="utf-8"), original_content)

    def _execute(self, tool: str, arguments: dict, *, approval_state: str = "") -> dict:
        action = {
            "selected_tool": tool,
            "tool_arguments": arguments,
        }
        if approval_state:
            action["approval_state"] = approval_state
        return execute_engineering_action(project_root=self.workspace_root, action=action)

    def assert_path_blocked(self, result: dict) -> None:
        self.assertFalse(result["ok"])
        self.assertEqual(result["error_payload"]["kind"], "path_outside_workspace")


if __name__ == "__main__":
    unittest.main()
