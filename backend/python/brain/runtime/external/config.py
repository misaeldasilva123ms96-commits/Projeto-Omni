"""Feature configuration for outbound external API execution."""

from __future__ import annotations

from brain.env import read_env_bool

EXTERNAL_API_ENABLED_ENV = "OMNI_EXTERNAL_API_ENABLED"
OPEN_METEO_ENABLED_ENV = "OMNI_EXTERNAL_OPEN_METEO_ENABLED"
OSM_GEOCODER_ENABLED_ENV = "OMNI_EXTERNAL_NOMINATIM_ENABLED"
FRANKFURTER_ENABLED_ENV = "OMNI_EXTERNAL_FRANKFURTER_ENABLED"
FREE_DICTIONARY_ENABLED_ENV = "OMNI_EXTERNAL_FREE_DICTIONARY_ENABLED"


def external_api_enabled() -> bool:
    """External execution is disabled unless the canonical gate is explicitly true."""
    return read_env_bool(EXTERNAL_API_ENABLED_ENV, False)


def open_meteo_enabled() -> bool:
    return read_env_bool(OPEN_METEO_ENABLED_ENV, False)


def nominatim_enabled() -> bool:
    return read_env_bool(OSM_GEOCODER_ENABLED_ENV, False)


def frankfurter_enabled() -> bool:
    return read_env_bool(FRANKFURTER_ENABLED_ENV, False)


def free_dictionary_enabled() -> bool:
    return read_env_bool(FREE_DICTIONARY_ENABLED_ENV, False)


__all__ = [
    "EXTERNAL_API_ENABLED_ENV",
    "FRANKFURTER_ENABLED_ENV",
    "FREE_DICTIONARY_ENABLED_ENV",
    "OPEN_METEO_ENABLED_ENV",
    "OSM_GEOCODER_ENABLED_ENV",
    "external_api_enabled",
    "frankfurter_enabled",
    "free_dictionary_enabled",
    "nominatim_enabled",
    "open_meteo_enabled",
]
