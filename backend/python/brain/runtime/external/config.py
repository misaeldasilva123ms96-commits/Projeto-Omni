"""Feature configuration for outbound external API execution."""

from __future__ import annotations

from brain.env import read_env, read_env_bool

EXTERNAL_API_ENABLED_ENV = "OMNI_EXTERNAL_API_ENABLED"
OPEN_METEO_ENABLED_ENV = "OMNI_EXTERNAL_OPEN_METEO_ENABLED"
OSM_GEOCODER_ENABLED_ENV = "OMNI_EXTERNAL_NOMINATIM_ENABLED"
OSM_GEOCODER_PUBLIC_API_COMPLIANCE_ACK_ENV = "OMNI_EXTERNAL_NOMINATIM_PUBLIC_API_COMPLIANCE_ACK"
OSM_GEOCODER_SINGLE_INSTANCE_ACK_ENV = "OMNI_EXTERNAL_NOMINATIM_SINGLE_INSTANCE_ACK"
PYTHON_MODE_ENV = "OMNI_PYTHON_MODE"
PYTHON_SERVICE_FALLBACK_ENV = "OMNI_PYTHON_SERVICE_FALLBACK_TO_SUBPROCESS"
FRANKFURTER_ENABLED_ENV = "OMNI_EXTERNAL_FRANKFURTER_ENABLED"
FREE_DICTIONARY_ENABLED_ENV = "OMNI_EXTERNAL_FREE_DICTIONARY_ENABLED"
URLHAUS_ENABLED_ENV = "OMNI_EXTERNAL_URLHAUS_ENABLED"
EXTERNAL_DISCOVERY_ENABLED_ENV = "OMNI_EXTERNAL_DISCOVERY_ENABLED"
APIS_GURU_DISCOVERY_ENABLED_ENV = "OMNI_EXTERNAL_APIS_GURU_DISCOVERY_ENABLED"
PUBLIC_APIS_DISCOVERY_ENABLED_ENV = "OMNI_EXTERNAL_PUBLIC_APIS_DISCOVERY_ENABLED"
EXTERNAL_SCHEMA_INTAKE_ENABLED_ENV = "OMNI_EXTERNAL_SCHEMA_INTAKE_ENABLED"
APIS_GURU_SCHEMA_INTAKE_ENABLED_ENV = "OMNI_EXTERNAL_APIS_GURU_SCHEMA_INTAKE_ENABLED"


def external_api_enabled() -> bool:
    """External execution is disabled unless the canonical gate is explicitly true."""
    return read_env_bool(EXTERNAL_API_ENABLED_ENV, False)


def open_meteo_enabled() -> bool:
    return read_env_bool(OPEN_METEO_ENABLED_ENV, False)


def nominatim_enabled() -> bool:
    return read_env_bool(OSM_GEOCODER_ENABLED_ENV, False)


def nominatim_operational_guard_satisfied() -> bool:
    """Require explicit operator acknowledgements and long-lived service topology."""

    true_values = {"1", "true", "yes", "on"}
    false_values = {"0", "false", "no", "off"}
    compliance_ack = read_env(OSM_GEOCODER_PUBLIC_API_COMPLIANCE_ACK_ENV).casefold()
    single_instance_ack = read_env(OSM_GEOCODER_SINGLE_INSTANCE_ACK_ENV).casefold()
    mode = read_env(PYTHON_MODE_ENV).casefold()
    fallback = read_env(PYTHON_SERVICE_FALLBACK_ENV).casefold()
    return (
        compliance_ack in true_values
        and single_instance_ack in true_values
        and mode == "service"
        and fallback in false_values
    )


def frankfurter_enabled() -> bool:
    return read_env_bool(FRANKFURTER_ENABLED_ENV, False)


def free_dictionary_enabled() -> bool:
    return read_env_bool(FREE_DICTIONARY_ENABLED_ENV, False)


def urlhaus_enabled() -> bool:
    return read_env_bool(URLHAUS_ENABLED_ENV, False)


def external_discovery_enabled() -> bool:
    return read_env_bool(EXTERNAL_DISCOVERY_ENABLED_ENV, False)


def apis_guru_discovery_enabled() -> bool:
    return read_env_bool(APIS_GURU_DISCOVERY_ENABLED_ENV, False)


def public_apis_discovery_enabled() -> bool:
    return read_env_bool(PUBLIC_APIS_DISCOVERY_ENABLED_ENV, False)


def external_schema_intake_enabled() -> bool:
    return read_env_bool(EXTERNAL_SCHEMA_INTAKE_ENABLED_ENV, False)


def apis_guru_schema_intake_enabled() -> bool:
    return read_env_bool(APIS_GURU_SCHEMA_INTAKE_ENABLED_ENV, False)


__all__ = [
    "EXTERNAL_API_ENABLED_ENV",
    "EXTERNAL_DISCOVERY_ENABLED_ENV",
    "APIS_GURU_DISCOVERY_ENABLED_ENV",
    "PUBLIC_APIS_DISCOVERY_ENABLED_ENV",
    "EXTERNAL_SCHEMA_INTAKE_ENABLED_ENV",
    "APIS_GURU_SCHEMA_INTAKE_ENABLED_ENV",
    "FRANKFURTER_ENABLED_ENV",
    "FREE_DICTIONARY_ENABLED_ENV",
    "URLHAUS_ENABLED_ENV",
    "OPEN_METEO_ENABLED_ENV",
    "OSM_GEOCODER_ENABLED_ENV",
    "OSM_GEOCODER_PUBLIC_API_COMPLIANCE_ACK_ENV",
    "OSM_GEOCODER_SINGLE_INSTANCE_ACK_ENV",
    "PYTHON_MODE_ENV",
    "PYTHON_SERVICE_FALLBACK_ENV",
    "external_api_enabled",
    "external_discovery_enabled",
    "apis_guru_discovery_enabled",
    "public_apis_discovery_enabled",
    "external_schema_intake_enabled",
    "apis_guru_schema_intake_enabled",
    "frankfurter_enabled",
    "free_dictionary_enabled",
    "urlhaus_enabled",
    "nominatim_enabled",
    "nominatim_operational_guard_satisfied",
    "open_meteo_enabled",
]
