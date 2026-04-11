from __future__ import annotations

import shutil
import sys
import threading
import unittest
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4


PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.goals import GoalFactory, GoalStatus, GoalStore  # noqa: E402


class GoalStoreTest(unittest.TestCase):
    @contextmanager
    def temp_workspace(self):
        base = PROJECT_ROOT / ".logs" / "test-goals-store"
        base.mkdir(parents=True, exist_ok=True)
        path = base / f"phase21-store-{uuid4().hex[:8]}"
        path.mkdir(parents=True, exist_ok=True)
        try:
            yield path
        finally:
            shutil.rmtree(path, ignore_errors=True)

    def test_goal_store_save_load_and_update_status(self) -> None:
        with self.temp_workspace() as workspace_root:
            store = GoalStore(workspace_root)
            goal = GoalFactory().infer_from_task("Validar persistencia do objetivo.")
            store.save_goal(goal)

            loaded = store.get_by_id(goal.goal_id)
            assert loaded is not None
            self.assertEqual(loaded.goal_id, goal.goal_id)

            updated = store.update_status(goal.goal_id, GoalStatus.ACHIEVED)
            assert updated is not None
            self.assertEqual(updated.status, GoalStatus.ACHIEVED)

            reloaded = GoalStore(workspace_root).get_by_id(goal.goal_id)
            assert reloaded is not None
            self.assertEqual(reloaded.status, GoalStatus.ACHIEVED)

    def test_goal_store_is_concurrency_safe_for_simple_access(self) -> None:
        with self.temp_workspace() as workspace_root:
            store = GoalStore(workspace_root)
            factory = GoalFactory()

            def worker(index: int) -> None:
                goal = factory.infer_from_task(f"Tarefa concorrente {index}")
                store.save_goal(goal)

            threads = [threading.Thread(target=worker, args=(index,)) for index in range(8)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()

            active_goals = store.get_active_goals()
            self.assertGreaterEqual(len(active_goals), 8)
            self.assertTrue((workspace_root / ".logs" / "fusion-runtime" / "goals" / "goal_store.json").exists())


if __name__ == "__main__":
    unittest.main()
