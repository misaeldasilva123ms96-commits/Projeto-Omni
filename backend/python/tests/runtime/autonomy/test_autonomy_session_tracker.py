"""Tests for the AutonomySessionTracker.

Covers session state creation, repeated errors, new errors, stagnation,
progress detection, safe fallback handling, provider failures, and
sanitization.
"""

from __future__ import annotations

import unittest
from typing import Any

from brain.runtime.autonomy import (
    AutonomyContext,
    AutonomyDecision,
    AutonomySessionState,
    AutonomySessionTracker,
    DecisionType,
)


class TrackerCreateTest(unittest.TestCase):
    def test_new_session_creates_state(self) -> None:
        tracker = AutonomySessionTracker()
        state = tracker.get_or_create("s1")
        self.assertIsInstance(state, AutonomySessionState)
        self.assertEqual(state.session_id, "s1")
        self.assertEqual(state.current_error_count, 0)
        self.assertEqual(state.stagnant_attempts, 0)
        self.assertEqual(len(state.distinct_error_types), 0)
        self.assertEqual(state.progressive_cycles, 0)

    def test_get_or_create_returns_same(self) -> None:
        tracker = AutonomySessionTracker()
        state1 = tracker.get_or_create("s1")
        state2 = tracker.get_or_create("s1")
        self.assertIs(state1, state2)

    def test_multiple_sessions_independent(self) -> None:
        tracker = AutonomySessionTracker()
        s1 = tracker.get_or_create("s1")
        s2 = tracker.get_or_create("s2")
        self.assertIsNot(s1, s2)
        self.assertEqual(s1.session_id, "s1")
        self.assertEqual(s2.session_id, "s2")

    def test_all_sessions_returns_all(self) -> None:
        tracker = AutonomySessionTracker()
        tracker.get_or_create("s1")
        tracker.get_or_create("s2")
        sessions = tracker.all_sessions()
        self.assertIn("s1", sessions)
        self.assertIn("s2", sessions)

    def test_get_state_returns_none_for_unknown(self) -> None:
        tracker = AutonomySessionTracker()
        self.assertIsNone(tracker.get_state("unknown"))


class RepeatedErrorTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tracker = AutonomySessionTracker()
        self.base_ctx = AutonomyContext(
            session_id="s1",
            error_type="timeout",
        )
        self.base_ctx.metadata["runtime_mode"] = "standard"
        self.base_ctx.metadata["response_length"] = 10
        self.decision = AutonomyDecision(
            decision=DecisionType.RETRY,
            reason="test",
        )

    def test_repeated_error_increments_current_error_count(self) -> None:
        self.tracker.update("s1", self.base_ctx, self.decision)
        state = self.tracker.update("s1", self.base_ctx, self.decision)
        self.assertEqual(state.current_error_count, 2)

    def test_repeated_error_increments_stagnant_attempts(self) -> None:
        self.tracker.update("s1", self.base_ctx, self.decision)
        state = self.tracker.update("s1", self.base_ctx, self.decision)
        self.assertEqual(state.stagnant_attempts, 1)

    def test_repeated_error_tracks_distinct_types_once(self) -> None:
        self.tracker.update("s1", self.base_ctx, self.decision)
        state = self.tracker.update("s1", self.base_ctx, self.decision)
        self.assertEqual(len(state.distinct_error_types), 1)
        self.assertIn("timeout", state.distinct_error_types)


class NewErrorResetsStagnationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tracker = AutonomySessionTracker()
        self.decision = AutonomyDecision(
            decision=DecisionType.RETRY,
            reason="test",
        )

    def _make_ctx(self, error_type: str, **meta: Any) -> AutonomyContext:
        ctx = AutonomyContext(session_id="s1", error_type=error_type)
        ctx.metadata["runtime_mode"] = meta.get("runtime_mode", "standard")
        ctx.metadata["response_length"] = meta.get("response_length", 10)
        return ctx

    def test_new_error_resets_stagnant_attempts(self) -> None:
        ctx1 = self._make_ctx("timeout")
        ctx2 = self._make_ctx("rate_limit")
        self.tracker.update("s1", ctx1, self.decision)
        state = self.tracker.update("s1", ctx2, self.decision)
        self.assertEqual(state.stagnant_attempts, 0)
        self.assertEqual(state.current_error_count, 2)

    def test_new_error_tracks_additional_distinct_type(self) -> None:
        ctx1 = self._make_ctx("timeout")
        ctx2 = self._make_ctx("rate_limit")
        self.tracker.update("s1", ctx1, self.decision)
        state = self.tracker.update("s1", ctx2, self.decision)
        self.assertEqual(len(state.distinct_error_types), 2)
        self.assertIn("timeout", state.distinct_error_types)
        self.assertIn("rate_limit", state.distinct_error_types)

    def test_new_error_counts_as_progress(self) -> None:
        ctx1 = self._make_ctx("timeout", response_length=0)
        ctx2 = self._make_ctx("rate_limit", response_length=10)
        self.tracker.update("s1", ctx1, self.decision)
        state = self.tracker.update("s1", ctx2, self.decision)
        self.assertEqual(state.progressive_cycles, 1)


class StagnationDetectionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tracker = AutonomySessionTracker()
        self.decision = AutonomyDecision(
            decision=DecisionType.RETRY,
            reason="test",
        )

    def test_repeated_same_error_is_stagnation(self) -> None:
        ctx = AutonomyContext(session_id="s1", error_type="timeout")
        ctx.metadata["runtime_mode"] = "standard"
        ctx.metadata["response_length"] = 10
        self.tracker.update("s1", ctx, self.decision)
        state = self.tracker.update("s1", ctx, self.decision)
        self.assertEqual(state.stagnant_attempts, 1)

    def test_same_provider_failure_repeated_is_stagnation(self) -> None:
        ctx1 = AutonomyContext(session_id="s1", error_type="provider_error")
        ctx1.metadata["runtime_mode"] = "provider_failure"
        ctx1.metadata["provider_failure_type"] = "openai"
        ctx1.metadata["response_length"] = 0
        self.tracker.update("s1", ctx1, self.decision)

        ctx2 = AutonomyContext(session_id="s1", error_type="provider_error")
        ctx2.metadata["runtime_mode"] = "provider_failure"
        ctx2.metadata["provider_failure_type"] = "openai"
        ctx2.metadata["response_length"] = 0
        state = self.tracker.update("s1", ctx2, self.decision)
        self.assertEqual(state.stagnant_attempts, 1)

    def test_same_runtime_mode_failure_repeated(self) -> None:
        ctx1 = AutonomyContext(session_id="s1", error_type="node_error")
        ctx1.metadata["runtime_mode"] = "node_fallback"
        ctx1.metadata["response_length"] = 0
        self.tracker.update("s1", ctx1, self.decision)

        ctx2 = AutonomyContext(session_id="s1", error_type="node_error")
        ctx2.metadata["runtime_mode"] = "node_fallback"
        ctx2.metadata["response_length"] = 0
        state = self.tracker.update("s1", ctx2, self.decision)
        self.assertEqual(state.stagnant_attempts, 1)

    def test_safe_fallback_response_repeated_is_stagnation(self) -> None:
        ctx1 = AutonomyContext(session_id="s1", no_safe_next_action=True)
        ctx1.metadata["runtime_mode"] = "safe_fallback"
        ctx1.metadata["response_length"] = 0
        self.tracker.update("s1", ctx1, self.decision)

        ctx2 = AutonomyContext(session_id="s1", no_safe_next_action=True)
        ctx2.metadata["runtime_mode"] = "safe_fallback"
        ctx2.metadata["response_length"] = 0
        state = self.tracker.update("s1", ctx2, self.decision)
        self.assertEqual(state.stagnant_attempts, 1)


class ProgressDetectionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tracker = AutonomySessionTracker()
        self.decision = AutonomyDecision(
            decision=DecisionType.RETRY,
            reason="progress",
        )

    def test_error_type_change_is_progress(self) -> None:
        ctx1 = AutonomyContext(session_id="s1", error_type="timeout")
        ctx1.metadata["runtime_mode"] = "standard"
        ctx1.metadata["response_length"] = 0
        self.tracker.update("s1", ctx1, self.decision)

        ctx2 = AutonomyContext(session_id="s1", error_type="rate_limit")
        ctx2.metadata["runtime_mode"] = "standard"
        ctx2.metadata["response_length"] = 10
        state = self.tracker.update("s1", ctx2, self.decision)
        self.assertEqual(state.progressive_cycles, 1)
        self.assertEqual(state.stagnant_attempts, 0)

    def test_runtime_mode_improvement_is_progress(self) -> None:
        ctx1 = AutonomyContext(session_id="s1", error_type="provider_failure")
        ctx1.metadata["runtime_mode"] = "provider_failure"
        ctx1.metadata["response_length"] = 0
        self.tracker.update("s1", ctx1, self.decision)

        ctx2 = AutonomyContext(session_id="s1")
        ctx2.metadata["runtime_mode"] = "standard"
        ctx2.metadata["response_length"] = 50
        state = self.tracker.update("s1", ctx2, self.decision)
        self.assertEqual(state.progressive_cycles, 1)

    def test_fallback_disappears_is_progress(self) -> None:
        ctx1 = AutonomyContext(session_id="s1", error_type="safe_fallback")
        ctx1.metadata["runtime_mode"] = "safe_fallback"
        ctx1.metadata["response_length"] = 0
        ctx1.no_safe_next_action = True
        self.tracker.update("s1", ctx1, self.decision)

        ctx2 = AutonomyContext(session_id="s1")
        ctx2.metadata["runtime_mode"] = "standard"
        ctx2.metadata["response_length"] = 50
        state = self.tracker.update("s1", ctx2, self.decision)
        self.assertEqual(state.progressive_cycles, 1)

    def test_provider_failure_disappears_is_progress(self) -> None:
        ctx1 = AutonomyContext(session_id="s1", error_type="provider_error")
        ctx1.metadata["runtime_mode"] = "provider_failure"
        ctx1.metadata["provider_failure_type"] = "openai"
        ctx1.metadata["response_length"] = 0
        self.tracker.update("s1", ctx1, self.decision)

        ctx2 = AutonomyContext(session_id="s1")
        ctx2.metadata["runtime_mode"] = "standard"
        ctx2.metadata["response_length"] = 50
        state = self.tracker.update("s1", ctx2, self.decision)
        self.assertEqual(state.progressive_cycles, 1)

    def test_nonzero_response_after_zero_is_progress(self) -> None:
        ctx1 = AutonomyContext(session_id="s1", error_type="timeout")
        ctx1.metadata["runtime_mode"] = "standard"
        ctx1.metadata["response_length"] = 0
        self.tracker.update("s1", ctx1, self.decision)

        ctx2 = AutonomyContext(session_id="s1")
        ctx2.metadata["runtime_mode"] = "standard"
        ctx2.metadata["response_length"] = 100
        state = self.tracker.update("s1", ctx2, self.decision)
        self.assertEqual(state.progressive_cycles, 1)

    def test_safe_fallback_no_longer_present_is_progress(self) -> None:
        ctx1 = AutonomyContext(session_id="s1", no_safe_next_action=True)
        ctx1.metadata["runtime_mode"] = "safe_fallback"
        ctx1.metadata["response_length"] = 0
        self.tracker.update("s1", ctx1, self.decision)

        ctx2 = AutonomyContext(session_id="s1")
        ctx2.metadata["runtime_mode"] = "standard"
        ctx2.metadata["response_length"] = 50
        state = self.tracker.update("s1", ctx2, self.decision)
        self.assertEqual(state.progressive_cycles, 1)


class ResetTest(unittest.TestCase):
    def test_reset_session(self) -> None:
        tracker = AutonomySessionTracker()
        tracker.get_or_create("s1")
        tracker.reset("s1")
        self.assertIsNone(tracker.get_state("s1"))

    def test_reset_all(self) -> None:
        tracker = AutonomySessionTracker()
        tracker.get_or_create("s1")
        tracker.get_or_create("s2")
        tracker.reset_all()
        self.assertEqual(len(tracker.all_sessions()), 0)

    def test_reset_unknown_session(self) -> None:
        tracker = AutonomySessionTracker()
        tracker.reset("unknown")
        self.assertEqual(len(tracker.all_sessions()), 0)


class SanitizationTest(unittest.TestCase):
    def test_session_state_no_raw_prompt(self) -> None:
        state = AutonomySessionState(session_id="s1")
        as_text = str(state)
        self.assertNotIn("raw_prompt", as_text)
        self.assertNotIn("raw_response", as_text)

    def test_session_state_no_api_keys(self) -> None:
        state = AutonomySessionState(session_id="s1")
        as_text = str(state)
        for secret in ("api_key", "auth_token", "password"):
            self.assertNotIn(secret, as_text)

    def test_session_state_no_credentials(self) -> None:
        state = AutonomySessionState(session_id="s1")
        as_text = str(state)
        self.assertNotIn("credential", as_text)

    def test_tracker_does_not_store_raw_data(self) -> None:
        tracker = AutonomySessionTracker()
        ctx = AutonomyContext(session_id="s1", error_type="timeout")
        ctx.metadata["runtime_mode"] = "standard"
        ctx.metadata["response_length"] = 10
        decision = AutonomyDecision(
            decision=DecisionType.RETRY,
            reason="test",
        )
        tracker.update("s1", ctx, decision)
        state = tracker.get_state("s1")
        self.assertIsNotNone(state)
        if state:
            as_text = str(state)
            self.assertNotIn("api_key", as_text)
            self.assertNotIn("auth_token", as_text)
            self.assertNotIn("raw_prompt", as_text)
            self.assertNotIn("raw_response", as_text)


class TrackerFailureSafetyTest(unittest.TestCase):
    def test_tracker_creation_does_not_raise(self) -> None:
        try:
            _ = AutonomySessionTracker()
        except Exception:
            self.fail("Tracker creation raised unexpectedly")

    def test_get_or_create_nonexistent(self) -> None:
        tracker = AutonomySessionTracker()
        state = tracker.get_or_create("new")
        self.assertIsNotNone(state)


if __name__ == "__main__":
    unittest.main()
