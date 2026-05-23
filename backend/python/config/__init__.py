"""Centralized provider secret configuration."""

from .provider_registry import PROVIDERS, get_available_providers, providers_capability
from .secrets_manager import (
    SecretError,
    build_controlled_os_environ_base,
    describe_configuration,
    describe_configuration_safe,
    get_secret,
    merge_provider_credentials,
)

__all__ = [
    "PROVIDERS",
    "SecretError",
    "build_controlled_os_environ_base",
    "describe_configuration",
    "describe_configuration_safe",
    "get_available_providers",
    "get_secret",
    "merge_provider_credentials",
    "providers_capability",
]
