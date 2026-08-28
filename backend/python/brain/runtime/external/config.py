"""Feature configuration for outbound external API execution."""

from __future__ import annotations

from brain.env import read_env_bool

EXTERNAL_API_ENABLED_ENV = "OMNI_EXTERNAL_API_ENABLED"
OPEN_METEO_ENABLED_ENV = "OMNI_EXTERNAL_OPEN_METEO_ENABLED"


def external_api_enabled() -> bool:
    """External execution is disabled unless the canonical gate is explicitly true."""
    return read_env_bool(EXTERNAL_API_ENABLED_ENV, False)


def open_meteo_enabled() -> bool:
    return read_env_bool(OPEN_METEO_ENABLED_ENV, False)


__all__ = [
    "EXTERNAL_API_ENABLED_ENV",
    "OPEN_METEO_ENABLED_ENV",
    "external_api_enabled",
    "open_meteo_enabled",
]
