from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.control.governance_wait import (  # noqa: E402
    GOVERNANCE_POLL_INTERVAL_MAX,
    GOVERNANCE_POLL_INTERVAL_MIN,
    GovernanceWaitEndReason,
    GovernanceWaitTick,
    bounded_governance_poll,
    clamp_governance_poll_interval_seconds,
)


class GovernanceWaitTest(unittest.TestCase):
    def test_clamp_respects_lower_and_upper_bound(self) -> None:
        self.assertEqual(clamp_governance_poll_interval_seconds(0.01), GOVERNANCE_POLL_INTERVAL_MIN)
        self.assertEqual(clamp_governance_poll_interval_seconds(9999.0), GOVERNANCE_POLL_INTERVAL_MAX)
        self.assertEqual(clamp_governance_poll_interval_seconds(2.5), 2.5)
        self.assertEqual(clamp_governance_poll_interval_seconds("nope"), 2.0)

    def test_immediate_terminal_no_sleep(self) -> None:
        sleeps: list[float] = []

        def sleep_fn(d: float) -> None:
            sleeps.append(d)

        def tick(_attempt: int, _elapsed: float) -> GovernanceWaitTick:
            return GovernanceWaitTick({"status": "running"})

        r = bounded_governance_poll(
            tick=tick,
            timeout_seconds=30.0,
            poll_interval_seconds=1.0,
            on_deadline_exceeded=lambda: {"status": "failed"},
            sleep_fn=sleep_fn,
            monotonic_fn=lambda: 0.0,
        )
        self.assertEqual(sleeps, [])
        self.assertEqual(r.reason, GovernanceWaitEndReason.TERMINAL)
        self.assertEqual(r.payload, {"status": "running"})
        self.assertEqual(r.attempts, 1)

    def test_polling_interval_and_attempts_until_terminal(self) -> None:
        sleeps: list[float] = []
        clock = [0.0]

        def monotonic_fn() -> float:
            return clock[0]

        def sleep_fn(d: float) -> None:
            sleeps.append(d)
            clock[0] += d

        n = [0]

        def tick(attempt: int, _elapsed: float) -> GovernanceWaitTick:
            n[0] = attempt
            if attempt >= 3:
                return GovernanceWaitTick({"ok": True})
            return GovernanceWaitTick(None)

        r = bounded_governance_poll(
            tick=tick,
            timeout_seconds=100.0,
            poll_interval_seconds=0.5,
            on_deadline_exceeded=lambda: {"bad": True},
            sleep_fn=sleep_fn,
            monotonic_fn=monotonic_fn,
        )
        self.assertEqual(r.reason, GovernanceWaitEndReason.TERMINAL)
        self.assertEqual(r.payload, {"ok": True})
        self.assertEqual(sleeps, [0.5, 0.5])
        self.assertEqual(r.attempts, 3)
        self.assertGreaterEqual(r.elapsed_seconds, 1.0)

    def test_timeout_safety_net_invokes_deadline_handler(self) -> None:
        sleeps: list[float] = []
        clock = [0.0]

        def monotonic_fn() -> float:
            return clock[0]

        def sleep_fn(d: float) -> None:
            sleeps.append(d)
            clock[0] += d

        def tick(_attempt: int, _elapsed: float) -> GovernanceWaitTick:
            return GovernanceWaitTick(None)

        deadline_calls = [0]

        def on_deadline() -> dict[str, object]:
            deadline_calls[0] += 1
            return {"status": "failed", "error": "operator_timeout"}

        r = bounded_governance_poll(
            tick=tick,
            timeout_seconds=0.25,
            poll_interval_seconds=0.1,
            on_deadline_exceeded=on_deadline,
            sleep_fn=sleep_fn,
            monotonic_fn=monotonic_fn,
        )
        self.assertEqual(r.reason, GovernanceWaitEndReason.TIMEOUT)
        self.assertEqual(r.payload["error"], "operator_timeout")
        self.assertEqual(deadline_calls[0], 1)
        self.assertGreaterEqual(len(sleeps), 1)

    def test_near_timeout_terminal_before_deadline_handler(self) -> None:
        """Last tick may return terminal exactly at timeout without invoking safety net."""
        clock = [0.0]

        def monotonic_fn() -> float:
            return clock[0]

        def sleep_fn(d: float) -> None:
            clock[0] += d

        def tick(_attempt: int, elapsed: float) -> GovernanceWaitTick:
            if elapsed >= 0.2:
                return GovernanceWaitTick({"status": "running"})
            return GovernanceWaitTick(None)

        r = bounded_governance_poll(
            tick=tick,
            timeout_seconds=0.5,
            poll_interval_seconds=0.1,
            on_deadline_exceeded=lambda: {"status": "failed", "error": "should_not_use"},
            sleep_fn=sleep_fn,
            monotonic_fn=monotonic_fn,
        )
        self.assertEqual(r.reason, GovernanceWaitEndReason.TERMINAL)
        self.assertEqual(r.payload["status"], "running")


if __name__ == "__main__":
    unittest.main()
