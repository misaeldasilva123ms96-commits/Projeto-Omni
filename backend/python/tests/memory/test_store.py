from __future__ import annotations

import json
from pathlib import Path

import pytest

from brain.memory.store import (
    DEFAULT_HISTORY_LIMIT,
    append_history,
    default_memory_store,
    load_memory_store,
    save_memory_store,
)


class TestDefaults:
    def test_default_history_limit(self):
        assert DEFAULT_HISTORY_LIMIT == 6

    def test_default_memory_store_shape(self):
        store = default_memory_store()
        assert isinstance(store, dict)
        assert store["history"] == []
        assert store["user"]["nome"] == ""
        assert store["user"]["preferencias"] == []
        assert store["long_term"] == {}


class TestLoad:
    def test_file_not_found_returns_default(self, tmp_path: Path):
        path = tmp_path / "nonexistent.json"
        result = load_memory_store(path)
        assert result == default_memory_store()

    def test_corrupt_json_returns_default(self, tmp_path: Path):
        path = tmp_path / "memory.json"
        path.write_text("not json", encoding="utf-8")
        result = load_memory_store(path)
        assert result == default_memory_store()

    def test_empty_file_returns_default(self, tmp_path: Path):
        path = tmp_path / "memory.json"
        path.write_text("", encoding="utf-8")
        result = load_memory_store(path)
        assert result == default_memory_store()

    def test_load_round_trip(self, tmp_path: Path):
        path = tmp_path / "memory.json"
        original = default_memory_store()
        original["user"]["nome"] = "Maria"
        original["user"]["preferencias"] = ["python", "ia"]
        original["history"] = [
            {"role": "user", "content": "ola"},
            {"role": "assistant", "content": "oi"},
        ]
        save_memory_store(path, original)
        loaded = load_memory_store(path)
        assert loaded["user"]["nome"] == "Maria"
        assert loaded["user"]["preferencias"] == ["python", "ia"]
        assert len(loaded["history"]) == 2

    def test_cleans_invalid_history_entries(self, tmp_path: Path):
        path = tmp_path / "memory.json"
        data = default_memory_store()
        data["history"] = [
            {"role": "user", "content": "valid"},
            {"role": "invalid", "content": "bad role"},
            {"role": "assistant", "content": ""},
            {"role": "user", "content": "  "},
            "not a dict",
        ]
        save_memory_store(path, data)
        loaded = load_memory_store(path)
        assert len(loaded["history"]) == 1
        assert loaded["history"][0]["content"] == "valid"

    def test_load_applies_history_limit(self, tmp_path: Path):
        path = tmp_path / "memory.json"
        data = default_memory_store()
        data["history"] = [{"role": "user", "content": str(i)} for i in range(10)]
        save_memory_store(path, data)
        loaded = load_memory_store(path, history_limit=3)
        assert len(loaded["history"]) == 3
        assert loaded["history"][0]["content"] == "7"

    def test_load_strips_content(self, tmp_path: Path):
        path = tmp_path / "memory.json"
        path.write_text(
            json.dumps({"history": [{"role": "user", "content": "  hello  "}]}),
            encoding="utf-8",
        )
        loaded = load_memory_store(path)
        assert loaded["history"][0]["content"] == "hello"

    def test_non_dict_parsed_returns_default(self, tmp_path: Path):
        path = tmp_path / "memory.json"
        path.write_text("[]", encoding="utf-8")
        result = load_memory_store(path)
        assert result == default_memory_store()

    def test_non_list_history_defaults_empty(self, tmp_path: Path):
        path = tmp_path / "memory.json"
        path.write_text(json.dumps({"history": "bad"}), encoding="utf-8")
        loaded = load_memory_store(path)
        assert loaded["history"] == []

    def test_non_dict_user_defaults(self, tmp_path: Path):
        path = tmp_path / "memory.json"
        path.write_text(json.dumps({"user": "bad"}), encoding="utf-8")
        loaded = load_memory_store(path)
        assert loaded["user"]["nome"] == ""
        assert loaded["user"]["preferencias"] == []


class TestSave:
    def test_save_writes_valid_json(self, tmp_path: Path):
        path = tmp_path / "memory.json"
        store = default_memory_store()
        store["history"] = [{"role": "user", "content": "test"}]
        save_memory_store(path, store)
        assert path.exists()
        raw = json.loads(path.read_text(encoding="utf-8"))
        assert raw["history"][0]["content"] == "test"

    def test_save_cleans_invalid_history(self, tmp_path: Path):
        path = tmp_path / "memory.json"
        store = default_memory_store()
        store["history"] = [
            {"role": "user", "content": "valid"},
            {"role": "unknown", "content": "bad"},
            "not dict",
        ]
        result = save_memory_store(path, store)
        assert len(result["history"]) == 1
        assert result["history"][0]["content"] == "valid"

    def test_save_applies_limit(self, tmp_path: Path):
        path = tmp_path / "memory.json"
        store = default_memory_store()
        store["history"] = [{"role": "user", "content": str(i)} for i in range(10)]
        result = save_memory_store(path, store, history_limit=2)
        assert len(result["history"]) == 2
        assert result["history"][0]["content"] == "8"

    def test_save_handles_non_dict_user(self, tmp_path: Path):
        path = tmp_path / "memory.json"
        store = {"history": [], "user": None, "long_term": {}}
        result = save_memory_store(path, store)
        assert result["user"]["nome"] == ""
        assert result["user"]["preferencias"] == []

    def test_save_strips_user_fields(self, tmp_path: Path):
        path = tmp_path / "memory.json"
        store = default_memory_store()
        store["user"] = {"nome": "  Ana  ", "preferencias": ["  rust  ", ""]}
        result = save_memory_store(path, store)
        assert result["user"]["nome"] == "Ana"
        assert result["user"]["preferencias"] == ["rust"]


class TestAppendHistory:
    def test_append_adds_entry(self):
        store = default_memory_store()
        append_history(store, "user", "hello")
        assert len(store["history"]) == 1
        assert store["history"][0]["content"] == "hello"

    def test_append_truncates_at_limit(self):
        store = default_memory_store()
        for i in range(7):
            append_history(store, "user", str(i), history_limit=6)
        assert len(store["history"]) == 6
        assert store["history"][0]["content"] == "1"
        assert store["history"][-1]["content"] == "6"

    def test_append_empty_content_does_not_add(self):
        store = default_memory_store()
        append_history(store, "user", "")
        assert len(store["history"]) == 0
        append_history(store, "user", "  ")
        assert len(store["history"]) == 0

    def test_append_strips_content(self):
        store = default_memory_store()
        append_history(store, "user", "  text  ")
        assert store["history"][0]["content"] == "text"

    def test_append_handles_non_list_history(self):
        store: dict = {"history": "bad", "user": {}, "long_term": {}}
        append_history(store, "user", "works")
        assert len(store["history"]) == 1
