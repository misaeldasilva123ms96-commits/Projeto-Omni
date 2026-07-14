from __future__ import annotations

import json
from pathlib import Path

import pytest

from brain.memory.hybrid import (
    LEARNING_SCHEMA_VERSION,
    HybridMemory,
    default_learning_store,
)


@pytest.fixture
def hybrid(tmp_path: Path) -> HybridMemory:
    return HybridMemory(tmp_path / "hybrid_dir")


class TestDefaults:
    def test_learning_schema_version(self):
        assert LEARNING_SCHEMA_VERSION == 2

    def test_default_learning_store_shape(self):
        store = default_learning_store()
        assert store["schema_version"] == 2
        assert store["patterns"] == {}
        assert store["good_decisions"] == []
        assert store["response_styles"] == {}
        assert store["evaluations"] == []
        assert store["capability_usage"] == {}
        assert store["strategy_versions"] == []
        assert store["meta"]["last_updated"] == ""
        assert store["meta"]["current_evolution_version"] == 0


class TestEnsureFiles:
    def test_creates_default_files(self, tmp_path: Path):
        base = tmp_path / "fresh"
        hybrid = HybridMemory(base)
        assert hybrid.user_path.exists()
        assert hybrid.preferences_path.exists()
        assert hybrid.notes_path.exists()
        assert hybrid.learning_path.exists()

    def test_does_not_overwrite_existing(self, tmp_path: Path):
        base = tmp_path / "existing"
        base.mkdir(parents=True, exist_ok=True)
        (base / "user.json").write_text(json.dumps({"nome": "Carlos"}), encoding="utf-8")
        hybrid = HybridMemory(base)
        loaded = json.loads(hybrid.user_path.read_text(encoding="utf-8"))
        assert loaded["nome"] == "Carlos"


class TestSyncFromStore:
    def test_writes_user_data(self, hybrid: HybridMemory):
        store = {
            "user": {"nome": "Ana", "preferencias": ["python", "data"]},
        }
        hybrid.sync_from_store(store)
        user = json.loads(hybrid.user_path.read_text(encoding="utf-8"))
        assert user["nome"] == "Ana"
        prefs = json.loads(hybrid.preferences_path.read_text(encoding="utf-8"))
        assert prefs["preferencias"] == ["python", "data"]

    def test_writes_notes(self, hybrid: HybridMemory):
        store = {
            "user": {"nome": "Joao", "preferencias": ["go"]},
        }
        hybrid.sync_from_store(store)
        notes = hybrid.notes_path.read_text(encoding="utf-8")
        assert "Joao" in notes
        assert "go" in notes

    def test_handles_empty_user(self, hybrid: HybridMemory):
        hybrid.sync_from_store({})
        user = json.loads(hybrid.user_path.read_text(encoding="utf-8"))
        assert user["nome"] == ""


class TestLoadLearning:
    def test_returns_defaults_for_missing_file(self, tmp_path: Path):
        base = tmp_path / "empty"
        hybrid = HybridMemory(base)
        hybrid.learning_path.unlink()
        result = hybrid.load_learning()
        assert result == default_learning_store()

    def test_handles_corrupt_json(self, hybrid: HybridMemory):
        hybrid.learning_path.write_text("{bad", encoding="utf-8")
        result = hybrid.load_learning()
        assert result == default_learning_store()

    def test_loads_saved_data(self, hybrid: HybridMemory):
        learning = hybrid.load_learning()
        learning["patterns"] = {"python": 3}
        hybrid.save_learning(learning)
        loaded = hybrid.load_learning()
        assert loaded["patterns"] == {"python": 3}


class TestMigrateLearning:
    def test_migrate_v1_to_v2(self, hybrid: HybridMemory):
        v1 = {
            "schema_version": 1,
            "patterns": {"test": 1},
            "good_decisions": [{"intent": "test"}],
            "response_styles": {"test": {"last_message": "hi"}},
        }
        hybrid.learning_path.write_text(json.dumps(v1), encoding="utf-8")
        loaded = hybrid.load_learning()
        assert loaded["schema_version"] == 2
        assert loaded["patterns"] == {"test": 1}
        assert loaded["good_decisions"] == [{"intent": "test"}]
        assert loaded["response_styles"] == {"test": {"last_message": "hi"}}
        assert isinstance(loaded["meta"], dict)
        assert loaded["meta"]["last_updated"] != ""

    def test_v2_passes_through(self, hybrid: HybridMemory):
        store = default_learning_store()
        store["patterns"] = {"existing": 5}
        hybrid.learning_path.write_text(json.dumps(store), encoding="utf-8")
        loaded = hybrid.load_learning()
        assert loaded["schema_version"] == 2
        assert loaded["patterns"] == {"existing": 5}

    def test_no_schema_version_defaults_v1(self, hybrid: HybridMemory):
        hybrid.learning_path.write_text(json.dumps({"patterns": {"x": 1}}), encoding="utf-8")
        loaded = hybrid.load_learning()
        assert loaded["schema_version"] == 2
        assert loaded["patterns"] == {"x": 1}

    def test_non_dict_meta_is_replaced(self, hybrid: HybridMemory):
        store = default_learning_store()
        store["meta"] = "bad"
        hybrid.learning_path.write_text(json.dumps(store), encoding="utf-8")
        loaded = hybrid.load_learning()
        assert isinstance(loaded["meta"], dict)


class TestRecordLearning:
    def test_updates_patterns(self, hybrid: HybridMemory):
        hybrid.record_learning(
            message="ola",
            response="oi",
            intent="greeting",
            capabilities=[],
        )
        learning = hybrid.load_learning()
        assert learning["patterns"].get("greeting") == 1

    def test_updates_response_styles(self, hybrid: HybridMemory):
        hybrid.record_learning(
            message="hello",
            response="hi there",
            intent="greeting",
            capabilities=["speak"],
        )
        learning = hybrid.load_learning()
        style = learning["response_styles"]["greeting"]
        assert style["last_message"] == "hello"
        assert style["last_response"] == "hi there"
        assert style["capabilities"] == ["speak"]

    def test_increments_pattern_count(self, hybrid: HybridMemory):
        for _ in range(3):
            hybrid.record_learning(
                message="hi",
                response="hey",
                intent="greeting",
                capabilities=[],
            )
        learning = hybrid.load_learning()
        assert learning["patterns"]["greeting"] == 3

    def test_tracks_capability_usage(self, hybrid: HybridMemory):
        hybrid.record_learning(
            message="m",
            response="r",
            intent="t",
            capabilities=["search", "summarize"],
        )
        learning = hybrid.load_learning()
        assert learning["capability_usage"]["search"] == 1
        assert learning["capability_usage"]["summarize"] == 1

    def test_truncates_good_decisions(self, hybrid: HybridMemory):
        for i in range(50):
            hybrid.record_learning(
                message=str(i),
                response=str(i),
                intent="t",
                capabilities=[],
            )
        learning = hybrid.load_learning()
        assert len(learning["good_decisions"]) == 40


class TestRecordEvaluation:
    def test_appends_evaluation(self, hybrid: HybridMemory):
        hybrid.record_evaluation({"score": 0.9})
        learning = hybrid.load_learning()
        assert len(learning["evaluations"]) == 1
        assert learning["evaluations"][0]["score"] == 0.9

    def test_truncates_at_200(self, hybrid: HybridMemory):
        for i in range(210):
            hybrid.record_evaluation({"idx": i})
        learning = hybrid.load_learning()
        assert len(learning["evaluations"]) == 200


class TestRecordStrategyVersion:
    def test_appends_version(self, hybrid: HybridMemory):
        hybrid.record_strategy_version({"version": 1, "desc": "initial"})
        learning = hybrid.load_learning()
        assert len(learning["strategy_versions"]) == 1
        assert learning["strategy_versions"][0]["version"] == 1

    def test_truncates_at_50(self, hybrid: HybridMemory):
        for i in range(60):
            hybrid.record_strategy_version({"version": i})
        learning = hybrid.load_learning()
        assert len(learning["strategy_versions"]) == 50

    def test_updates_meta_version(self, hybrid: HybridMemory):
        hybrid.record_strategy_version({"version": 7})
        learning = hybrid.load_learning()
        assert learning["meta"]["current_evolution_version"] == 7
