"""Deterministic description of capabilities already present in the Omni runtime."""

from __future__ import annotations

import hashlib
from dataclasses import fields

from brain.runtime.external.approval.manifest import canonical_json_bytes
from brain.runtime.external.models import (
    AuthenticationType,
    ExternalAPIDefinition,
    ExternalAPIRequest,
    SafePathTemplate,
)

from .models import RuntimeCapabilityProfile

RUNTIME_CAPABILITY_PROFILE_VERSION = "external-api-runtime-capabilities-v1"


def build_runtime_capability_profile() -> RuntimeCapabilityProfile:
    return RuntimeCapabilityProfile(
        RUNTIME_CAPABILITY_PROFILE_VERSION,
        "supported",
        "supported_after_safe_adapter_construction",
        "supported",
        "unsupported",
        "unsupported",
        "unsupported",
        "unsupported",
        "unsupported",
        "limited",
        "supported",
        "unsupported",
        "unsupported",
        "unsupported",
        "supported",
        "supported",
        "unsupported",
        "deny",
        "GET",
        tuple(item.name for item in fields(ExternalAPIRequest)),
        tuple(item.name for item in fields(ExternalAPIDefinition)),
        tuple(item.value for item in AuthenticationType),
        tuple(item.value for item in SafePathTemplate),
    )


def runtime_capability_profile_sha256(profile: RuntimeCapabilityProfile) -> str:
    return hashlib.sha256(canonical_json_bytes(profile.as_dict())).hexdigest()
