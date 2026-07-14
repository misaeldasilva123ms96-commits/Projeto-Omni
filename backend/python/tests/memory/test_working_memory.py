from __future__ import annotations

import json
from pathlib import Path

import pytest

from brain.memory.working_memory import WorkingMemoryStore


@pytest.fixture
def store(tmp_path: Path) -> WorkingMemoryStore:
    return WorkingMemoryStore(tmp_path / "working.json")


class TestUpdateSession:
    def test_creates_new_session(self, store: WorkingMemoryStore):
        result = store.update_session("sess-1", {"key": "value"})
        assert result["key"] == "value"
        assert "updated_at" in result

    def test_merges_with_existing(self, store: WorkingMemoryStore):
        store.update_session("sess-1", {"nome": "Ana"})
        result = store.update_session("sess-1", {"idade": 30})
        assert result["nome"] == "Ana"
        assert result["idade"] == 30

    def test_overwrites_existing_keys(self, store: WorkingMemoryStore):
        store.update_session("sess-1", {"nome": "Ana"})
        result = store.update_session("sess-1", {"nome": "Maria"})
        assert result["nome"] == "Maria"

    def test_sets_updated_at(self, store: WorkingMemoryStore):
        result = store.update_session("sess-1", {"x": 1})
        assert isinstance(result["updated_at"], str)
        assert len(result["updated_at"]) > 10


class TestLoadSession:
    def test_returns_correct_data(self, store: WorkingMemoryStore):
        store.update_session("sess-1", {"a": 1})
        store.update_session("sess-2", {"b": 2})
        loaded = store.load_session("sess-1")
        assert loaded["a"] == 1
        assert "b" not in loaded

    def test_unknown_session_returns_empty(self, store: WorkingMemoryStore):
        loaded = store.load_session("nonexistent")
        assert loaded == {}

    def test_missing_file_returns_empty(self, tmp_path: Path):
        s = WorkingMemoryStore(tmp_path / "missing.json")
        loaded = s.load_session("any")
        assert loaded == {}

    def test_corrupt_file_returns_default(self, tmp_path: Path):
        p = tmp_path / "corrupt.json"
        p.write_text("{{{", encoding="utf-8")
        s = WorkingMemoryStore(p)
        loaded = s.load_session("any")
        assert loaded == {}
