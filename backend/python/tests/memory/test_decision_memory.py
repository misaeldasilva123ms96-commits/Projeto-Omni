from __future__ import annotations

import json
from pathlib import Path

import pytest

from brain.memory.decision_memory import DecisionMemoryStore


@pytest.fixture
def store(tmp_path: Path) -> DecisionMemoryStore:
    return DecisionMemoryStore(tmp_path / "decisions.json")


class TestRecordDecision:
    def test_creates_entry_with_correct_structure(self, store: DecisionMemoryStore):
        entry = store.record_decision(
            session_id="sess-1",
            task_id="task-1",
            run_id="run-1",
            decision_type="approve",
            reason="all checks passed",
            task_type="verification",
            reason_code="OK",
        )
        assert entry["session_id"] == "sess-1"
        assert entry["task_id"] == "task-1"
        assert entry["run_id"] == "run-1"
        assert entry["decision_type"] == "approve"
        assert entry["reason"] == "all checks passed"
        assert entry["task_type"] == "verification"
        assert entry["reason_code"] == "OK"
        assert "entry_id" in entry
        assert "timestamp" in entry
        assert entry["metadata"] == {}

    def test_default_task_type_and_reason_code(self, store: DecisionMemoryStore):
        entry = store.record_decision(
            session_id="s",
            task_id="t",
            run_id="r",
            decision_type="retry",
            reason="timeout",
        )
        assert entry["task_type"] == ""
        assert entry["reason_code"] == ""


class TestFindDecisions:
    def test_filters_by_session_id(self, store: DecisionMemoryStore):
        store.record_decision(
            session_id="s-1", task_id="t", run_id="r", decision_type="a", reason="x"
        )
        store.record_decision(
            session_id="s-2", task_id="t", run_id="r", decision_type="a", reason="x"
        )
        results = store.find_decisions(session_id="s-1")
        assert len(results) == 1

    def test_filters_by_task_type(self, store: DecisionMemoryStore):
        store.record_decision(
            session_id="s",
            task_id="t",
            run_id="r",
            decision_type="a",
            reason="x",
            task_type="build",
        )
        store.record_decision(
            session_id="s", task_id="t", run_id="r", decision_type="a", reason="x", task_type="test"
        )
        results = store.find_decisions(session_id="s", task_type="build")
        assert len(results) == 1

    def test_filters_by_decision_type(self, store: DecisionMemoryStore):
        store.record_decision(
            session_id="s", task_id="t", run_id="r", decision_type="approve", reason="x"
        )
        store.record_decision(
            session_id="s", task_id="t", run_id="r", decision_type="reject", reason="x"
        )
        results = store.find_decisions(session_id="s", decision_type="approve")
        assert len(results) == 1

    def test_filters_by_reason_code(self, store: DecisionMemoryStore):
        store.record_decision(
            session_id="s", task_id="t", run_id="r", decision_type="a", reason="x", reason_code="OK"
        )
        store.record_decision(
            session_id="s",
            task_id="t",
            run_id="r",
            decision_type="a",
            reason="x",
            reason_code="FAIL",
        )
        results = store.find_decisions(session_id="s", reason_code="OK")
        assert len(results) == 1

    def test_combined_filters(self, store: DecisionMemoryStore):
        store.record_decision(
            session_id="s",
            task_id="t",
            run_id="r",
            decision_type="a",
            reason="x",
            task_type="build",
            reason_code="OK",
        )
        store.record_decision(
            session_id="s",
            task_id="t",
            run_id="r",
            decision_type="b",
            reason="x",
            task_type="build",
            reason_code="OK",
        )
        results = store.find_decisions(
            session_id="s", task_type="build", decision_type="a", reason_code="OK"
        )
        assert len(results) == 1

    def test_no_matches_returns_empty(self, store: DecisionMemoryStore):
        results = store.find_decisions(session_id="nonexistent")
        assert results == []

    def test_returns_most_recent_first(self, store: DecisionMemoryStore):
        for i in range(3):
            store.record_decision(
                session_id="s", task_id="t", run_id=f"r-{i}", decision_type="a", reason="x"
            )
        results = store.find_decisions(session_id="s")
        assert results[0]["run_id"] == "r-2"
        assert results[-1]["run_id"] == "r-0"

    def test_respects_limit(self, store: DecisionMemoryStore):
        for i in range(10):
            store.record_decision(
                session_id="s", task_id="t", run_id=f"r-{i}", decision_type="a", reason="x"
            )
        results = store.find_decisions(session_id="s", limit=3)
        assert len(results) == 3

    def test_truncates_at_200(self, store: DecisionMemoryStore):
        for i in range(210):
            store.record_decision(
                session_id="s", task_id="t", run_id=f"r-{i}", decision_type="a", reason="x"
            )
        results = store.find_decisions(session_id="s", limit=500)
        assert len(results) == 200
