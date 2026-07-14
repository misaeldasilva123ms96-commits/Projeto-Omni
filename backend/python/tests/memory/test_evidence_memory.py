from __future__ import annotations

import json
from pathlib import Path

import pytest

from brain.memory.evidence_memory import EvidenceMemoryStore


@pytest.fixture
def store(tmp_path: Path) -> EvidenceMemoryStore:
    return EvidenceMemoryStore(tmp_path / "evidence.json")


class TestRecordEvidence:
    def test_creates_entry_with_correct_structure(self, store: EvidenceMemoryStore):
        entry = store.record_evidence(
            session_id="sess-1",
            task_id="task-1",
            run_id="run-1",
            task_type="analysis",
            evidence={"file_evidence": True, "runtime_evidence": False},
        )
        assert entry["session_id"] == "sess-1"
        assert entry["task_id"] == "task-1"
        assert entry["run_id"] == "run-1"
        assert entry["task_type"] == "analysis"
        assert "entry_id" in entry
        assert "timestamp" in entry
        assert entry["evidence"]["file_evidence"] is True
        assert entry["evidence"]["runtime_evidence"] is False
        assert entry["metadata"] == {}

    def test_evidence_boolean_extraction(self, store: EvidenceMemoryStore):
        entry = store.record_evidence(
            session_id="s",
            task_id="t",
            run_id="r",
            task_type="t",
            evidence={"file_evidence": 1, "runtime_evidence": "yes", "test_evidence": None},
        )
        assert entry["evidence"]["file_evidence"] is True
        assert entry["evidence"]["runtime_evidence"] is True
        assert entry["evidence"]["test_evidence"] is False
        assert entry["evidence"]["dependency_evidence"] is False


class TestGetEvidence:
    def test_filters_by_session_id(self, store: EvidenceMemoryStore):
        store.record_evidence(
            session_id="s-1", task_id="t-1", run_id="r-1", task_type="t", evidence={}
        )
        store.record_evidence(
            session_id="s-2", task_id="t-1", run_id="r-1", task_type="t", evidence={}
        )
        results = store.get_evidence(session_id="s-1")
        assert len(results) == 1
        assert results[0]["session_id"] == "s-1"

    def test_filters_by_task_id(self, store: EvidenceMemoryStore):
        store.record_evidence(session_id="s", task_id="a", run_id="r", task_type="t", evidence={})
        store.record_evidence(session_id="s", task_id="b", run_id="r", task_type="t", evidence={})
        results = store.get_evidence(session_id="s", task_id="a")
        assert len(results) == 1
        assert results[0]["task_id"] == "a"

    def test_returns_most_recent_first(self, store: EvidenceMemoryStore):
        for i in range(3):
            store.record_evidence(
                session_id="s", task_id="t", run_id=f"r-{i}", task_type="t", evidence={}
            )
        results = store.get_evidence(session_id="s")
        assert len(results) == 3
        assert results[0]["run_id"] == "r-2"
        assert results[-1]["run_id"] == "r-0"

    def test_respects_limit(self, store: EvidenceMemoryStore):
        for i in range(10):
            store.record_evidence(
                session_id="s", task_id="t", run_id=f"r-{i}", task_type="t", evidence={}
            )
        results = store.get_evidence(session_id="s", limit=3)
        assert len(results) == 3

    def test_no_matches_returns_empty(self, store: EvidenceMemoryStore):
        results = store.get_evidence(session_id="nonexistent")
        assert results == []

    def test_truncates_at_200(self, store: EvidenceMemoryStore):
        for i in range(210):
            store.record_evidence(
                session_id="s", task_id="t", run_id=f"r-{i}", task_type="t", evidence={}
            )
        results = store.get_evidence(session_id="s", limit=500)
        assert len(results) == 200
