from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
from typing import Any


PLAN_POLICY_VERSION = "plan_policy_v1"

_PUBLIC_FIELDS = {
    "plan_mode",
    "daily_token_limit",
    "max_input_tokens",
    "max_output_tokens",
    "max_context_tokens",
    "files_enabled",
    "tools_enabled",
    "sensitive_tools_enabled",
    "long_memory_enabled",
    "provider_mode",
}


class PlanMode(str, Enum):
    FREE = "free"
    BYOK = "byok"
    PRO = "pro"
    INTERNAL = "internal"


class ProviderMode(str, Enum):
    EXPERIMENTAL_FREE = "experimental_free"
    USER_KEY = "user_key"
    MANAGED = "managed"
    INTERNAL = "internal"


class ToolAccessMode(str, Enum):
    DISABLED = "disabled"
    CONTROLLED = "controlled"
    ENABLED = "enabled"


class UnknownPlanModeError(ValueError):
    """Raised when a caller requests an unsupported plan mode."""


class InvalidPlanPolicyError(ValueError):
    """Raised when policy values do not satisfy the contract."""


@dataclass(frozen=True, slots=True)
class PlanPolicy:
    plan_mode: PlanMode
    daily_token_limit: int | None
    max_input_tokens: int
    max_output_tokens: int
    max_context_tokens: int
    files_enabled: bool
    tools_enabled: bool | ToolAccessMode
    sensitive_tools_enabled: bool | ToolAccessMode
    long_memory_enabled: bool
    provider_mode: ProviderMode

    def __post_init__(self) -> None:
        _validate_policy(self)

    def as_public_dict(self) -> dict[str, Any]:
        """Return a stable public policy shape without provider secrets."""
        return {
            "policy_version": PLAN_POLICY_VERSION,
            "plan_mode": self.plan_mode.value,
            "daily_token_limit": self.daily_token_limit,
            "max_input_tokens": self.max_input_tokens,
            "max_output_tokens": self.max_output_tokens,
            "max_context_tokens": self.max_context_tokens,
            "files_enabled": self.files_enabled,
            "tools_enabled": _public_access_value(self.tools_enabled),
            "sensitive_tools_enabled": _public_access_value(self.sensitive_tools_enabled),
            "long_memory_enabled": self.long_memory_enabled,
            "provider_mode": self.provider_mode.value,
        }


def resolve_plan_policy(
    plan_mode: str | PlanMode,
    *,
    overrides: dict[str, Any] | None = None,
) -> PlanPolicy:
    mode = _coerce_plan_mode(plan_mode)
    policy = DEFAULT_PLAN_POLICIES[mode]
    if not overrides:
        return policy
    return replace(policy, **_coerce_overrides(overrides))


def build_public_plan_policy(
    plan_mode: str | PlanMode,
    *,
    overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return resolve_plan_policy(plan_mode, overrides=overrides).as_public_dict()


def _coerce_plan_mode(plan_mode: str | PlanMode) -> PlanMode:
    if isinstance(plan_mode, PlanMode):
        return plan_mode
    raw = str(plan_mode or "").strip().lower()
    try:
        return PlanMode(raw)
    except ValueError as exc:
        raise UnknownPlanModeError(f"Unknown plan mode: {raw or '<empty>'}") from exc


def _coerce_overrides(overrides: dict[str, Any]) -> dict[str, Any]:
    allowed = _PUBLIC_FIELDS - {"plan_mode", "provider_mode"}
    unknown = sorted(set(overrides) - allowed)
    if unknown:
        joined = ", ".join(unknown)
        raise InvalidPlanPolicyError(f"Unsupported plan policy override field(s): {joined}")

    coerced = dict(overrides)
    for key in ("tools_enabled", "sensitive_tools_enabled"):
        if key in coerced:
            coerced[key] = _coerce_access_mode(coerced[key])
    return coerced


def _coerce_access_mode(value: Any) -> bool | ToolAccessMode:
    if isinstance(value, bool):
        return value
    if isinstance(value, ToolAccessMode):
        return value
    raw = str(value or "").strip().lower()
    try:
        return ToolAccessMode(raw)
    except ValueError as exc:
        raise InvalidPlanPolicyError(f"Unsupported tool access mode: {raw or '<empty>'}") from exc


def _public_access_value(value: bool | ToolAccessMode) -> bool | str:
    if isinstance(value, ToolAccessMode):
        return value.value
    return bool(value)


def _validate_policy(policy: PlanPolicy) -> None:
    for field_name in ("max_input_tokens", "max_output_tokens", "max_context_tokens"):
        value = getattr(policy, field_name)
        if not isinstance(value, int) or value <= 0:
            raise InvalidPlanPolicyError(f"{field_name} must be a positive integer")
    if policy.daily_token_limit is not None and (
        not isinstance(policy.daily_token_limit, int) or policy.daily_token_limit <= 0
    ):
        raise InvalidPlanPolicyError("daily_token_limit must be a positive integer or None")
    if policy.max_context_tokens < policy.max_input_tokens:
        raise InvalidPlanPolicyError("max_context_tokens must be at least max_input_tokens")
    _coerce_access_mode(policy.tools_enabled)
    _coerce_access_mode(policy.sensitive_tools_enabled)


DEFAULT_PLAN_POLICIES: dict[PlanMode, PlanPolicy] = {
    PlanMode.FREE: PlanPolicy(
        plan_mode=PlanMode.FREE,
        daily_token_limit=15000,
        max_input_tokens=3000,
        max_output_tokens=1500,
        max_context_tokens=6000,
        files_enabled=False,
        tools_enabled=False,
        sensitive_tools_enabled=False,
        long_memory_enabled=False,
        provider_mode=ProviderMode.EXPERIMENTAL_FREE,
    ),
    PlanMode.BYOK: PlanPolicy(
        plan_mode=PlanMode.BYOK,
        daily_token_limit=None,
        max_input_tokens=8000,
        max_output_tokens=4000,
        max_context_tokens=16000,
        files_enabled=True,
        tools_enabled=ToolAccessMode.CONTROLLED,
        sensitive_tools_enabled=False,
        long_memory_enabled=False,
        provider_mode=ProviderMode.USER_KEY,
    ),
    PlanMode.PRO: PlanPolicy(
        plan_mode=PlanMode.PRO,
        daily_token_limit=250000,
        max_input_tokens=16000,
        max_output_tokens=8000,
        max_context_tokens=64000,
        files_enabled=True,
        tools_enabled=ToolAccessMode.CONTROLLED,
        sensitive_tools_enabled=ToolAccessMode.CONTROLLED,
        long_memory_enabled=True,
        provider_mode=ProviderMode.MANAGED,
    ),
    PlanMode.INTERNAL: PlanPolicy(
        plan_mode=PlanMode.INTERNAL,
        daily_token_limit=None,
        max_input_tokens=64000,
        max_output_tokens=16000,
        max_context_tokens=256000,
        files_enabled=True,
        tools_enabled=ToolAccessMode.CONTROLLED,
        sensitive_tools_enabled=ToolAccessMode.CONTROLLED,
        long_memory_enabled=True,
        provider_mode=ProviderMode.INTERNAL,
    ),
}
