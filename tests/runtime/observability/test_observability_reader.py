from __future__ import annotations

import io
import json
import os
import shutil
import sys
import unittest
from contextlib import contextmanager, redirect_stdout
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / 'backend' / 'python'))

from brain.runtime.goals import GoalFactory, GoalContext, GoalStore  # noqa: E402
from brain.runtime.memory import MemoryFacade  # noqa: E402
from brain.runtime.observability.cli import main as observability_cli_main  # noqa: E402
from brain.runtime.observability.observability_reader import ObservabilityReader  # noqa: E402
from brain.runtime.simulation.models import RouteSimulation, RouteType, SimulationBasis, SimulationResult  # noqa: E402
from brain.runtime.simulation.simulation_store import SimulationStore  # noqa: E402
from brain.runtime.specialists.models import CoordinationTrace  # noqa: E402
from brain.runtime.specialists.specialist_store import SpecialistStore  # noqa: E402


class ObservabilityReaderTest(unittest.TestCase):
    @contextmanager
    def temp_workspace(self):
        base = PROJECT_ROOT / '.logs' / 'test-observability'
        base.mkdir(parents=True, exist_ok=True)
        path = base / f'observability-reader-{uuid4().hex[:8]}'
        path.mkdir(parents=True, exist_ok=True)
        try:
            yield path
        finally:
            shutil.rmtree(path, ignore_errors=True)

    def test_observability_snapshot_aggregates_correctly(self) -> None:
        with self.temp_workspace() as workspace_root:
            with patch.dict(os.environ, {
                'OMINI_MEMORY_MIN_EPISODES_FOR_SEMANTIC_FACT': '1',
                'OMINI_MEMORY_MIN_CONFIDENCE_FOR_SEMANTIC_RECALL': '0.0',
            }):
                goal = GoalFactory().create_goal(description='Tornar runtime legivel.', intent='execution')
                GoalStore(workspace_root).save_goal(goal)
                facade = MemoryFacade(workspace_root)
                self.addCleanup(facade.close)
                facade.set_active_goal(session_id='sess-obs', goal_id=goal.goal_id, active_plan_id='plan-obs', goal_context=GoalContext.from_goal(goal))
                facade.record_event(event_type='continuation', description='Runtime seguindo.', outcome='retry', progress_score=0.5, metadata={'goal_type': 'execution', 'recommended_route': 'retry', 'decision_type': 'retry'})
                facade.close_goal_episode(outcome='retry', description='Episode persisted.', event_type='continuation')
                engine_adoption_path = workspace_root / '.logs' / 'fusion-runtime'
                engine_adoption_path.mkdir(parents=True, exist_ok=True)
                (engine_adoption_path / 'engine_adoption.json').write_text(
                    json.dumps(
                        {
                            'scope': 'session',
                            'session_id': 'sess-obs',
                            'engine_counters': {
                                'packaged_upstream': 8,
                                'authority_fallback': 2,
                                'fallback_by_reason': {
                                    'heavy_execution_request': 1,
                                    'packaged_import_failed': 0,
                                    'fallback_policy_triggered': 1,
                                },
                            },
                        },
                        ensure_ascii=False,
                        indent=2,
                    ),
                    encoding='utf-8',
                )
                control_path = workspace_root / '.logs' / 'fusion-runtime' / 'control'
                control_path.mkdir(parents=True, exist_ok=True)
                (control_path / 'run_registry.json').write_text(
                    json.dumps(
                        {
                            'runs': {
                                'run-obs': {
                                    'run_id': 'run-obs',
                                    'goal_id': goal.goal_id,
                                    'session_id': 'sess-obs',
                                    'status': 'running',
                                    'started_at': '2026-04-12T00:00:00+00:00',
                                    'updated_at': '2026-04-12T00:00:10+00:00',
                                    'last_action': 'execution_started',
                                    'progress_score': 0.25,
                                    'metadata': {'task_id': 'task-obs'},
                                }
                            }
                        },
                        ensure_ascii=False,
                        indent=2,
                    ),
                    encoding='utf-8',
                )
                SimulationStore(workspace_root).append(
                    SimulationResult.build(
                        recommended_route=RouteType.RETRY,
                        routes=[RouteSimulation(route=RouteType.RETRY, estimated_success_rate=0.7, estimated_cost=0.2, constraint_risk=0.1, goal_alignment=0.8, supporting_episodes=[], reasoning='bounded', confidence=0.6)],
                        simulation_basis=SimulationBasis(episodes_consulted=1, semantic_facts_used=[], procedural_pattern_used=None, fallback_to_heuristic=False),
                        goal_id=goal.goal_id,
                    )
                )
                trace = CoordinationTrace.build(goal_id=goal.goal_id, session_id='sess-obs')
                trace.finish('completed')
                SpecialistStore(workspace_root).append_trace(trace)
                reader = ObservabilityReader(workspace_root)
                snapshot = reader.snapshot()
                self.assertIsNotNone(snapshot.goal)
                self.assertEqual(len(snapshot.timeline), 1)
                self.assertIsNotNone(snapshot.latest_simulation)
                self.assertIsNotNone(snapshot.latest_trace)
                self.assertIsNotNone(snapshot.engine_adoption)
                self.assertEqual(len(snapshot.active_runs), 1)
                self.assertEqual(snapshot.active_runs[0]['run_id'], 'run-obs')
                self.assertAlmostEqual(snapshot.engine_adoption['adoption_rate'], 0.8)
                self.assertTrue(snapshot.engine_adoption['promotion_ready'])

    def test_cli_returns_valid_json_for_snapshot(self) -> None:
        with self.temp_workspace() as workspace_root:
            stream = io.StringIO()
            with patch.object(sys, 'argv', ['observability-cli', '--root', str(workspace_root), 'snapshot']):
                with redirect_stdout(stream):
                    result = observability_cli_main()
            self.assertEqual(result, 0)
            payload = json.loads(stream.getvalue())
            self.assertIn('status', payload)
            self.assertIn('snapshot', payload)
            self.assertIn('engine_adoption', payload['snapshot'])
            self.assertIn('active_runs', payload['snapshot'])
