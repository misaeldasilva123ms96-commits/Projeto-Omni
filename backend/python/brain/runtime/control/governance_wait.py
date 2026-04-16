"""Bounded synchronous polling for governance wait paths (Phase 30.15)."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any

# Avoid busy-spin (seconds); matches historical ``max(0.1, poll)`` lower bound.
GOVERNANCE_POLL_INTERVAL_MIN: float = 0.1
# Avoid unbounded sleeps that stall responsiveness (seconds).
GOVERNANCE_POLL_INTERVAL_MAX: float = 60.0


def clamp_governance_poll_interval_seconds(value: float) -> float:
    """Clamp poll interval to a safe, bounded range."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        v = 2.0
    return min(GOVERNANCE_POLL_INTERVAL_MAX, max(GOVERNANCE_POLL_INTERVAL_MIN, v))


class GovernanceWaitEndReason(Enum):
    """How a bounded governance poll loop stopped."""

    TERMINAL = auto()
    """``tick`` returned a terminal payload."""

    TIMEOUT = auto()
    """Deadline exceeded while ``tick`` still requested another poll (safety net)."""


@dataclass(frozen=True, slots=True)
class GovernanceWaitPollResult:
    """Outcome of :func:`bounded_governance_poll`."""

    reason: GovernanceWaitEndReason
    payload: dict[str, Any]
    attempts: int
    elapsed_seconds: float


@dataclass(frozen=True, slots=True)
class GovernanceWaitTick:
    """
    Return from each poll ``tick``.

    ``result`` not ``None`` ends the loop and becomes the poll result payload.
    ``result`` ``None`` means sleep (if under deadline) and call ``tick`` again.
    """

    result: dict[str, Any] | None


def bounded_governance_poll(
    *,
    tick: Callable[[int, float], GovernanceWaitTick],
    timeout_seconds: float,
    poll_interval_seconds: float,
    on_deadline_exceeded: Callable[[], dict[str, Any]],
    sleep_fn: Callable[[float], None] = time.sleep,
    monotonic_fn: Callable[[], float] = time.monotonic,
) -> GovernanceWaitPollResult:
    """
    Invoke ``tick(attempt, elapsed_seconds)`` until it returns a non-``None`` ``result``,
    or until ``timeout_seconds`` elapses (then ``on_deadline_exceeded`` runs once).

    ``tick`` is responsible for normal timeout handling (e.g. operator hold) before the
    runner deadline; ``on_deadline_exceeded`` is a **safety net** if the clock passes
    without ``tick`` returning a terminal dict.
    """
    try:
        max_wait = max(0.0, float(timeout_seconds))
    except (TypeError, ValueError):
        max_wait = 0.0
    interval = clamp_governance_poll_interval_seconds(poll_interval_seconds)
    start = monotonic_fn()
    deadline = start + max_wait
    attempt = 0
    while True:
        attempt += 1
        elapsed = monotonic_fn() - start
        step = tick(attempt, elapsed)
        if step.result is not None:
            return GovernanceWaitPollResult(
                reason=GovernanceWaitEndReason.TERMINAL,
                payload=step.result,
                attempts=attempt,
                elapsed_seconds=elapsed,
            )
        now = monotonic_fn()
        if now >= deadline:
            payload = on_deadline_exceeded()
            return GovernanceWaitPollResult(
                reason=GovernanceWaitEndReason.TIMEOUT,
                payload=payload,
                attempts=attempt,
                elapsed_seconds=now - start,
            )
        sleep_fn(interval)
