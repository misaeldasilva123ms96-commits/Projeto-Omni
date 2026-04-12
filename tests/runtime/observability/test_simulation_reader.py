from __future__ import annotations

import json
import shutil
import sys
import unittest
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / 'backend' / 'python'))

from brain.runtime.observability.simulation_reader import SimulationReader  # noqa: E402


class SimulationReaderTest(unittest.TestCase):
    @contextmanager
    def temp_workspace(self):
        base = PROJECT_ROOT / '.logs' / 'test-observability'
        base.mkdir(parents=True, exist_ok=True)
        path = base / f'simulation-reader-{uuid4().hex[:8]}'
        path.mkdir(parents=True, exist_ok=True)
        try:
            yield path
        finally:
            shutil.rmtree(path, ignore_errors=True)

    def test_simulation_reader_reads_recent_simulations_safely(self) -> None:
        with self.temp_workspace() as workspace_root:
            log_dir = workspace_root / '.logs' / 'fusion-runtime' / 'simulation'
            log_dir.mkdir(parents=True, exist_ok=True)
            path = log_dir / 'simulation_log.jsonl'
            path.write_text(
                '\n'.join([
                    json.dumps({'simulation_id': 'sim-1', 'goal_id': 'goal-1', 'recommended_route': 'retry', 'simulated_at': 't1', 'routes': [], 'simulation_basis': {}, 'metadata': {}}),
                    '{"simulation_id": "bad"',
                    json.dumps({'simulation_id': 'sim-2', 'goal_id': 'goal-1', 'recommended_route': 'repair', 'simulated_at': 't2', 'routes': [], 'simulation_basis': {}, 'metadata': {}}),
                ]),
                encoding='utf-8',
            )
            reader = SimulationReader(workspace_root)
            sims = reader.read_recent_simulations(limit=5, goal_id='goal-1')
            self.assertEqual([item.simulation_id for item in sims], ['sim-1', 'sim-2'])
            self.assertEqual(reader.read_latest_simulation(goal_id='goal-1').simulation_id, 'sim-2')
