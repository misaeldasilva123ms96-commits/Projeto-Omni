"""Phase 37 — bounded specialist role identifiers (distinct from goal-action SpecialistCoordinator)."""

from __future__ import annotations

from enum import Enum


class SpecialistRuntimeRole(str, Enum):
    """Governed runtime roles for chat-path coordination (structured transforms, not separate LLM personas)."""

    PLANNER = "planner"
    EXECUTOR = "executor"
    VALIDATOR = "validator"
    CRITIC = "critic"


ROLE_ORDER: tuple[SpecialistRuntimeRole, ...] = (
    SpecialistRuntimeRole.PLANNER,
    SpecialistRuntimeRole.EXECUTOR,
    SpecialistRuntimeRole.VALIDATOR,
    SpecialistRuntimeRole.CRITIC,
)
