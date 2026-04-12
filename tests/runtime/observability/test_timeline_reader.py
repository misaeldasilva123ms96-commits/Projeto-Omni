from __future__ import annotations

import shutil
import sys
import unittest
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / 'backend' / 'python'))

from brain.runtime.memory.working import WorkingMemory  # noqa: E402
from brain.runtime.observability.timeline_reader import TimelineReader  # noqa: E402


class TimelineReaderTest(unittest.TestCase):
    @contextmanager
    def temp_workspace(self):
        base = PROJECT_ROOT / '.logs' / 'test-observability'
        base.mkdir(parents=True, exist_ok=True)
        path = base / f'timeline-reader-{uuid4().hex[:8]}'
        path.mkdir(parents=True, exist_ok=True)
        try:
            yield path
        finally:
            shutil.rmtree(path, ignore_errors=True)

    def test_timeline_reader_survives_partial_json(self) -> None:
        with self.temp_workspace() as workspace_root:
            path = workspace_root / '.logs' / 'fusion-runtime' / 'memory'
            path.mkdir(parents=True, exist_ok=True)
            (path / 'working_memory.json').write_text('{"session_id": ', encoding='utf-8')
            reader = TimelineReader(workspace_root)
            self.assertIsNone(reader.read_state())
            self.assertEqual(reader.read_recent_events(limit=5), [])

    def test_timeline_reader_reads_recent_events(self) -> None:
        with self.temp_workspace() as workspace_root:
            working = WorkingMemory(workspace_root)
            working.start_new_session(session_id='sess-obs', goal_id='goal-1')
            working.record_event(event_type='continuation', description='Continuing safely.', outcome='retry', progress_score=0.5)
            reader = TimelineReader(workspace_root)
            events = reader.read_recent_events(limit=5)
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0].event_type, 'continuation')
