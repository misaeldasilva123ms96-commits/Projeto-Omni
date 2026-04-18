"""Centralized provider secret configuration (read surface + Node env normalization)."""

from .secrets_manager import SecretLookup, apply_runtime_provider_secrets, configured, describe_configuration_safe, get_secret
from .providers import LOGICAL_IDS, PROVIDERS, spec_for

__all__ = [
    "LOGICAL_IDS",
    "PROVIDERS",
    "SecretLookup",
    "apply_runtime_provider_secrets",
    "configured",
    "describe_configuration_safe",
    "get_secret",
    "spec_for",
]
