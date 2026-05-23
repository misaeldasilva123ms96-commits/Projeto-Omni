from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from .access_snapshot_boundary import (
    APPROVED_ACCESS_SNAPSHOT_ENVELOPE_KEYS,
    APPROVED_ACCESS_SNAPSHOT_KEYS,
)
from .provider_registry import build_public_provider_adapter_snapshot


PUTER_CLIENT_ADAPTER_CONTRACT_VERSION = "puter_client_adapter_contract_v1"
PUTER_CLIENT_ADAPTER_ID = "puter_client_adapter"
PUTER_CLIENT_PROVIDER_FAMILY = "experimental_free_provider"
PUTER_CLIENT_PROVIDER_MODE = "experimental_free"

PUTER_CLIENT_ADAPTER_PUBLIC_KEYS = frozenset(
    {
        "contract_version",
        "adapter_id",
        "provider_family",
        "provider_mode",
        "is_experimental",
        "default_enabled",
        "requires_browser_runtime",
        "requires_user_session",
        "supports_streaming",
        "supports_tools",
        "supports_files",
        "supports_long_context",
        "supports_sensitive_tools",
        "public_description",
    }
)

PUTER_CLIENT_ADAPTER_SELECTION_KEYS = frozenset(
    PUTER_CLIENT_ADAPTER_PUBLIC_KEYS
    | {
        "selection_allowed",
        "denied",
        "reason",
    }
)

_UNSAFE_REQUEST_OPTION_KEYS = frozenset(
    {
        "access_token",
        "api_key",
        "credential",
        "env",
        "env_var",
        "file",
        "files",
        "function_call",
        "key",
        "password",
        "provider_payload",
        "raw_provider_payload",
        "secret",
        "tool",
        "tools",
        "token",
    }
)


@dataclass(frozen=True, slots=True)
class PuterClientAdapterContract:
    adapter_id: str
    provider_family: str
    provider_mode: str
    is_experimental: bool
    default_enabled: bool
    requires_browser_runtime: bool
    requires_user_session: bool
    supports_streaming: bool
    supports_tools: bool
    supports_files: bool
    supports_long_context: bool
    supports_sensitive_tools: bool
    public_description: str

    def as_public_dict(self) -> dict[str, Any]:
        return {
            "contract_version": PUTER_CLIENT_ADAPTER_CONTRACT_VERSION,
            "adapter_id": self.adapter_id,
            "provider_family": self.provider_family,
            "provider_mode": self.provider_mode,
            "is_experimental": self.is_experimental,
            "default_enabled": self.default_enabled,
            "requires_browser_runtime": self.requires_browser_runtime,
            "requires_user_session": self.requires_user_session,
            "supports_streaming": self.supports_streaming,
            "supports_tools": self.supports_tools,
            "supports_files": self.supports_files,
            "supports_long_context": self.supports_long_context,
            "supports_sensitive_tools": self.supports_sensitive_tools,
            "public_description": self.public_description,
        }


PUTER_CLIENT_ADAPTER_CONTRACT = PuterClientAdapterContract(
    adapter_id=PUTER_CLIENT_ADAPTER_ID,
    provider_family=PUTER_CLIENT_PROVIDER_FAMILY,
    provider_mode=PUTER_CLIENT_PROVIDER_MODE,
    is_experimental=True,
    default_enabled=False,
    requires_browser_runtime=True,
    requires_user_session=True,
    supports_streaming=False,
    supports_tools=False,
    supports_files=False,
    supports_long_context=False,
    supports_sensitive_tools=False,
    public_description=(
        "Disabled-by-default experimental browser client adapter contract for "
        "Free mode access."
    ),
)


def build_public_puter_client_adapter_contract() -> dict[str, Any]:
    """Return the public-safe Puter client adapter contract metadata."""

    provider = build_public_provider_adapter_snapshot(PUTER_CLIENT_PROVIDER_FAMILY)
    if provider.get("provider_mode") != PUTER_CLIENT_PROVIDER_MODE:
        return _selection_dict(selection_allowed=False, reason="provider_registry_mismatch")
    return PUTER_CLIENT_ADAPTER_CONTRACT.as_public_dict()


def build_public_puter_client_adapter_selection(
    access_snapshot_response: Mapping[str, Any],
    *,
    experimental_feature_enabled: bool = False,
    request_options: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Evaluate whether the disabled-by-default Puter contract may be selected.

    The function is deterministic and performs no browser, network, provider, or
    credential work. Callers must pass a response produced by
    AccessSnapshotBoundary; public request payloads are not authoritative here.
    """

    unsafe_keys = _unsafe_request_option_keys(request_options)
    if unsafe_keys:
        return _selection_dict(selection_allowed=False, reason="unsafe_request_options")

    if not experimental_feature_enabled:
        return _selection_dict(selection_allowed=False, reason="feature_disabled")

    snapshot = _safe_access_snapshot(access_snapshot_response)
    if snapshot is None:
        return _selection_dict(selection_allowed=False, reason="invalid_access_snapshot")

    if not bool(access_snapshot_response.get("ok", False)):
        return _selection_dict(
            selection_allowed=False,
            reason=str(access_snapshot_response.get("reason") or "routing_denied"),
        )

    if not bool(snapshot.get("routing_allowed", False)):
        return _selection_dict(
            selection_allowed=False,
            reason=str(snapshot.get("decision_reason") or "routing_denied"),
        )

    if snapshot.get("plan_mode") != "free":
        return _selection_dict(selection_allowed=False, reason="not_free_mode")

    if snapshot.get("provider_mode") != PUTER_CLIENT_PROVIDER_MODE:
        return _selection_dict(selection_allowed=False, reason="provider_mode_not_allowed")

    if snapshot.get("selected_provider_family") != PUTER_CLIENT_PROVIDER_FAMILY:
        return _selection_dict(selection_allowed=False, reason="provider_family_not_allowed")

    return _selection_dict(selection_allowed=True, reason="selection_allowed")


def _selection_dict(*, selection_allowed: bool, reason: str) -> dict[str, Any]:
    contract = PUTER_CLIENT_ADAPTER_CONTRACT.as_public_dict()
    return {
        **contract,
        "selection_allowed": selection_allowed,
        "denied": not selection_allowed,
        "reason": reason if not selection_allowed else "selection_allowed",
    }


def _safe_access_snapshot(access_snapshot_response: Mapping[str, Any]) -> Mapping[str, Any] | None:
    if not isinstance(access_snapshot_response, Mapping):
        return None
    if set(access_snapshot_response.keys()) != APPROVED_ACCESS_SNAPSHOT_ENVELOPE_KEYS:
        return None
    snapshot = access_snapshot_response.get("access_snapshot")
    if not isinstance(snapshot, Mapping):
        return None
    if set(snapshot.keys()) != APPROVED_ACCESS_SNAPSHOT_KEYS:
        return None
    return snapshot


def _unsafe_request_option_keys(request_options: Mapping[str, Any] | None) -> tuple[str, ...]:
    if request_options is None:
        return ()
    if not isinstance(request_options, Mapping):
        return ("request_options",)

    unsafe = []
    for key in request_options:
        normalized_key = str(key or "").strip().lower()
        if normalized_key in _UNSAFE_REQUEST_OPTION_KEYS:
            unsafe.append(normalized_key)
        else:
            unsafe.append(normalized_key)
    return tuple(sorted(unsafe))
