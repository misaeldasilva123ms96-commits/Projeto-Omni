"""Centralized provider secret configuration."""

from .secrets_manager import (
    SecretError,
    build_controlled_os_environ_base,
    describe_configuration,
    describe_configuration_safe,
    get_secret,
    merge_provider_credentials,
)

__all__ = [
    "SecretError",
    "build_controlled_os_environ_base",
    "describe_configuration",
    "describe_configuration_safe",
    "get_secret",
    "merge_provider_credentials",
]
