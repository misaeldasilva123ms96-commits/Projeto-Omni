"""Types for the local sandbox policy engine."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class PolicyInput:
    command: str
    cwd: Optional[str] = None
    requested_by: str = "unknown"
    sandbox_mode: str = "local"


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    blocked: bool
    requires_approval: bool
    category: str
    risk_level: str
    reason: str
    matched_rule: Optional[str]
    normalized_command: str
    sandbox_mode: str
