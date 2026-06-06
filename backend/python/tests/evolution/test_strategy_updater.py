import json
import pytest

from brain.evolution.strategy_updater import StrategyUpdater, default_strategy_state


@pytest.fixture
def updater(temp_dir):
    return StrategyUpdater(temp_dir / "evolution")


class TestDefaultStrategyState:
    def test_returns_dict_with_expected_keys(self):
        state = default_strategy_state()
        assert "schema_version" in state
        assert "version" in state
        assert "capability_weights" in state
        assert "decision_thresholds" in state
        assert "memory_rules" in state
        assert "orchestrator_hints" in state
        assert state["version"] == 0
        assert state["schema_version"] == 1

    def test_capability_weights_defaults(self):
        state = default_strategy_state()
        assert state["capability_weights"]["generate_idea"] == 1.0
        assert state["capability_weights"]["give_advice"] == 1.0
        assert state["capability_weights"]["create_plan"] == 1.0


class TestStrategyUpdater:
    def test_initializes_files(self, updater):
        assert updater.state_path.exists()
        assert updater.log_path.exists()

        state = json.loads(updater.state_path.read_text(encoding="utf-8"))
        assert state["version"] == 0

    def test_load_current_state_returns_empty_on_empty(self, updater):
        updater.state_path.write_text("", encoding="utf-8")
        state = updater.load_current_state()
        assert state == {}

    def test_load_current_state_returns_default_on_corrupt(self, updater):
        updater.state_path.write_text("not-json", encoding="utf-8")
        state = updater.load_current_state()
        assert state["version"] == 0

    def test_propose_update_raise_priority(self, updater):
        analysis = {
            "recommended_adjustments": [
                {"action": "raise_priority", "reason": "complex queries need planning"},
            ],
            "underused_capabilities": [],
            "weak_patterns": [],
        }
        proposal = updater.propose_update(analysis, 0.65)
        assert proposal["proposed_state"]["capability_weights"]["create_plan"] > 1.0
        assert proposal["proposed_state"]["capability_weights"]["give_advice"] > 1.0
        assert proposal["estimated_score_gain"] > 0.0

    def test_propose_update_underused(self, updater):
        analysis = {
            "recommended_adjustments": [],
            "underused_capabilities": ["generate_idea"],
            "weak_patterns": [],
        }
        proposal = updater.propose_update(analysis, 0.65)
        assert proposal["proposed_state"]["capability_weights"]["generate_idea"] < 1.0

    def test_propose_update_weak_patterns(self, updater):
        analysis = {
            "recommended_adjustments": [],
            "underused_capabilities": [],
            "weak_patterns": ["repetitive_responses"],
        }
        proposal = updater.propose_update(analysis, 0.65)
        assert proposal["proposed_state"]["memory_rules"]["history_limit"] > 6

    def test_propose_update_no_adjustments(self, updater):
        analysis = {
            "recommended_adjustments": [],
            "underused_capabilities": [],
            "weak_patterns": [],
        }
        proposal = updater.propose_update(analysis, 0.65)
        assert proposal["estimated_score_gain"] == 0.0
        assert "No significant adjustments" in proposal["proposed_state"]["justification"]

    def test_apply_update_increments_version(self, updater):
        analysis = {
            "recommended_adjustments": [],
            "underused_capabilities": [],
            "weak_patterns": [],
        }
        proposal = updater.propose_update(analysis, 0.70)
        new_state = updater.apply_update(proposal)
        assert new_state["version"] == 1

        loaded = json.loads(updater.state_path.read_text(encoding="utf-8"))
        assert loaded["version"] == 1

    def test_apply_update_creates_snapshot(self, updater):
        analysis = {
            "recommended_adjustments": [{"action": "raise_priority", "reason": "test"}],
            "underused_capabilities": [],
            "weak_patterns": [],
        }
        proposal = updater.propose_update(analysis, 0.70)
        updater.apply_update(proposal)
        snapshot = updater.snapshots_dir / "strategy_v1.json"
        assert snapshot.exists()

    def test_rollback_restores_snapshot(self, updater):
        analysis1 = {"recommended_adjustments": [], "underused_capabilities": [], "weak_patterns": []}
        proposal1 = updater.propose_update(analysis1, 0.50)
        updater.apply_update(proposal1)

        state_v1 = json.loads(updater.state_path.read_text(encoding="utf-8"))
        assert state_v1["version"] == 1

        updater.rollback(1)
        state_v1 = json.loads(updater.state_path.read_text(encoding="utf-8"))
        assert state_v1["version"] == 1

    def test_rollback_missing_version_raises(self, updater):
        with pytest.raises(FileNotFoundError):
            updater.rollback(999)

    def test_two_updates_produce_two_snapshots(self, updater):
        analysis = {"recommended_adjustments": [], "underused_capabilities": [], "weak_patterns": []}

        proposal1 = updater.propose_update(analysis, 0.50)
        updater.apply_update(proposal1)

        proposal2 = updater.propose_update(analysis, 0.60)
        updater.apply_update(proposal2)

        assert (updater.snapshots_dir / "strategy_v1.json").exists()
        assert (updater.snapshots_dir / "strategy_v2.json").exists()

    def test_log_tracks_changes(self, updater):
        analysis = {"recommended_adjustments": [], "underused_capabilities": [], "weak_patterns": []}
        proposal = updater.propose_update(analysis, 0.55)
        updater.apply_update(proposal)

        log = json.loads(updater.log_path.read_text(encoding="utf-8"))
        assert len(log["changes"]) == 1
        assert log["changes"][0]["version"] == 1
