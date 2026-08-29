"""Server-owned credential resolution for governed external providers."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Protocol

URLHAUS_CREDENTIAL_ID = "urlhaus_auth_key"


@dataclass(frozen=True, slots=True)
class CredentialSpec:
    credential_id: str
    environment_name: str
    header_name: str


@dataclass(frozen=True, slots=True)
class ResolvedCredential:
    header_name: str
    secret: str


class CredentialResolver(Protocol):
    def resolve(self, credential_id: str) -> ResolvedCredential: ...


_SPECS = {
    URLHAUS_CREDENTIAL_ID: CredentialSpec(
        URLHAUS_CREDENTIAL_ID, "OMNI_EXTERNAL_URLHAUS_AUTH_KEY", "Auth-Key"
    )
}
_PLACEHOLDERS = {"changeme", "placeholder", "your-key-here", "your_auth_key"}


class EnvironmentCredentialResolver:
    """Resolves only maintainer-declared IDs, at execution time for rotation."""

    def resolve(self, credential_id: str) -> ResolvedCredential:
        spec = _SPECS.get(credential_id)
        if spec is None:
            raise ValueError("credential_unavailable")
        value = os.environ.get(spec.environment_name)
        if value is None or not value.strip():
            raise ValueError("credential_unavailable")
        if (
            len(value) > 512
            or any(character in value for character in ("\r", "\n", "\x00"))
            or value.strip().lower() in _PLACEHOLDERS
        ):
            raise ValueError("credential_invalid")
        return ResolvedCredential(spec.header_name, value)
