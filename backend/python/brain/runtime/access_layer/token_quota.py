from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .plan_policy import PlanMode, PlanPolicy, resolve_plan_policy


TOKEN_QUOTA_VERSION = "token_quota_v1"


class InvalidTokenQuotaError(ValueError):
    """Raised when token quota inputs are outside the deterministic contract."""


@dataclass(frozen=True, slots=True)
class TokenQuotaSnapshot:
    plan_mode: PlanMode
    subject_id: str
    usage_date: str
    tokens_in: int
    tokens_out: int
    tokens_total: int
    daily_token_limit: int | None
    quota_remaining: int | None
    quota_exceeded: bool
    input_limit_exceeded: bool
    output_limit_exceeded: bool

    def as_public_dict(self) -> dict[str, Any]:
        return {
            "quota_version": TOKEN_QUOTA_VERSION,
            "plan_mode": self.plan_mode.value,
            "subject_id": self.subject_id,
            "usage_date": self.usage_date,
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
            "tokens_total": self.tokens_total,
            "daily_token_limit": self.daily_token_limit,
            "quota_remaining": self.quota_remaining,
            "quota_exceeded": self.quota_exceeded,
            "input_limit_exceeded": self.input_limit_exceeded,
            "output_limit_exceeded": self.output_limit_exceeded,
        }


def calculate_tokens_total(tokens_in: int, tokens_out: int) -> int:
    _validate_token_count("tokens_in", tokens_in)
    _validate_token_count("tokens_out", tokens_out)
    return tokens_in + tokens_out


def calculate_quota_remaining(
    *,
    daily_token_limit: int | None,
    tokens_total: int,
) -> int | None:
    _validate_daily_limit(daily_token_limit)
    _validate_token_count("tokens_total", tokens_total)
    if daily_token_limit is None:
        return None
    return max(daily_token_limit - tokens_total, 0)


def is_quota_exceeded(
    *,
    daily_token_limit: int | None,
    tokens_total: int,
) -> bool:
    _validate_daily_limit(daily_token_limit)
    _validate_token_count("tokens_total", tokens_total)
    if daily_token_limit is None:
        return False
    return tokens_total > daily_token_limit


def validate_max_input_tokens(tokens_in: int, policy: PlanPolicy) -> bool:
    _validate_token_count("tokens_in", tokens_in)
    return tokens_in <= policy.max_input_tokens


def validate_max_output_tokens(tokens_out: int, policy: PlanPolicy) -> bool:
    _validate_token_count("tokens_out", tokens_out)
    return tokens_out <= policy.max_output_tokens


def build_token_quota_snapshot(
    *,
    plan_mode: str | PlanMode,
    subject_id: str,
    tokens_in: int,
    tokens_out: int,
    usage_date: str,
    policy_overrides: dict[str, Any] | None = None,
) -> TokenQuotaSnapshot:
    policy = resolve_plan_policy(plan_mode, overrides=policy_overrides)
    total = calculate_tokens_total(tokens_in, tokens_out)
    return TokenQuotaSnapshot(
        plan_mode=policy.plan_mode,
        subject_id=str(subject_id or ""),
        usage_date=str(usage_date or ""),
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        tokens_total=total,
        daily_token_limit=policy.daily_token_limit,
        quota_remaining=calculate_quota_remaining(
            daily_token_limit=policy.daily_token_limit,
            tokens_total=total,
        ),
        quota_exceeded=is_quota_exceeded(
            daily_token_limit=policy.daily_token_limit,
            tokens_total=total,
        ),
        input_limit_exceeded=not validate_max_input_tokens(tokens_in, policy),
        output_limit_exceeded=not validate_max_output_tokens(tokens_out, policy),
    )


def build_public_quota_snapshot(
    *,
    plan_mode: str | PlanMode,
    subject_id: str,
    tokens_in: int,
    tokens_out: int,
    usage_date: str,
    policy_overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return build_token_quota_snapshot(
        plan_mode=plan_mode,
        subject_id=subject_id,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        usage_date=usage_date,
        policy_overrides=policy_overrides,
    ).as_public_dict()


def _validate_token_count(name: str, value: int) -> None:
    if not isinstance(value, int) or value < 0:
        raise InvalidTokenQuotaError(f"{name} must be a non-negative integer")


def _validate_daily_limit(value: int | None) -> None:
    if value is not None and (not isinstance(value, int) or value <= 0):
        raise InvalidTokenQuotaError("daily_token_limit must be a positive integer or None")
