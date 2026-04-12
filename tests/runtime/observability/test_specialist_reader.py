from __future__ import annotations

import json
import shutil
import sys
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / 'backend' / 'python'))

from brain.runtime.observability.specialist_reader import SpecialistReader  # noqa: E402


class SpecialistReaderTest(unittest.TestCase):
    @contextmanager
    def temp_workspace(self):
        base = PROJECT_ROOT / '.logs' / 'test-observability'
        base.mkdir(parents=True, exist_ok=True)
        path = base / f'specialist-reader-{uuid4().hex[:8]}'
        path.mkdir(parents=True, exist_ok=True)
        try:
            yield path
        finally:
            shutil.rmtree(path, ignore_errors=True)

    def test_specialist_reader_tolerates_invalid_jsonl_lines(self) -> None:
        with self.temp_workspace() as workspace_root:
            log_dir = workspace_root / '.logs' / 'fusion-runtime' / 'specialists'
            log_dir.mkdir(parents=True, exist_ok=True)
            path = log_dir / 'coordination_log.jsonl'
            path.write_text(
                '\n'.join([
                    'not-json',
                    json.dumps({'trace_id': 'trace-1', 'decisions': [], 'governance_verdicts': [], 'final_outcome': 'ok', 'started_at': 't'}),
                    '{"trace_id": "truncated"',
                ]),
                encoding='utf-8',
            )
            reader = SpecialistReader(workspace_root)
            traces = reader.read_recent_traces(limit=5)
            self.assertEqual(len(traces), 1)
            self.assertEqual(traces[0].trace_id, 'trace-1')

    def test_specialist_reader_reads_recent_traces_without_read_text(self) -> None:
        with self.temp_workspace() as workspace_root:
            log_dir = workspace_root / '.logs' / 'fusion-runtime' / 'specialists'
            log_dir.mkdir(parents=True, exist_ok=True)
            path = log_dir / 'coordination_log.jsonl'
            path.write_text('\n'.join(json.dumps({'trace_id': f'trace-{index}', 'decisions': [], 'governance_verdicts': [], 'final_outcome': 'ok', 'started_at': 't'}) for index in range(20)), encoding='utf-8')
            reader = SpecialistReader(workspace_root)
            with patch('pathlib.Path.read_text', side_effect=AssertionError('full read not allowed')):
                traces = reader.read_recent_traces(limit=3)
            self.assertEqual([trace.trace_id for trace in traces], ['trace-17', 'trace-18', 'trace-19'])
