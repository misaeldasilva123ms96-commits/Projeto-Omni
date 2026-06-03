from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .plan_policy import ProviderMode
from .provider_router import ProviderRoutingDecision


PROVIDER_REGISTRY_VERSION = "provider_registry_v1"


class UnknownProviderFamilyError(ValueError):
    """Raised when a provider family is not registered."""


@dataclass(frozen=True, slots=True)
class ProviderAdapterMetadata:
    provider_family: str
    adapter_id: str
    display_name: str
    provider_mode: ProviderMode
    supports_streaming: bool
    supports_tools: bool
    supports_files: bool
    supports_long_context: bool
    supports_sensitive_tools: bool
    is_experimental: bool
    is_user_key_required: bool
    is_managed: bool
    is_internal: bool
    default_enabled: bool
    public_description: str

    def as_public_dict(self) -> dict[str, Any]:
        return {
            "registry_version": PROVIDER_REGISTRY_VERSION,
            "provider_family": self.provider_family,
            "adapter_id": self.adapter_id,
            "display_name": self.display_name,
            "provider_mode": self.provider_mode.value,
            "supports_streaming": self.supports_streaming,
            "supports_tools": self.supports_tools,
            "supports_files": self.supports_files,
            "supports_long_context": self.supports_long_context,
            "supports_sensitive_tools": self.supports_sensitive_tools,
            "is_experimental": self.is_experimental,
            "is_user_key_required": self.is_user_key_required,
            "is_managed": self.is_managed,
            "is_internal": self.is_internal,
            "default_enabled": self.default_enabled,
            "public_description": self.public_description,
        }


PROVIDER_ADAPTERS: Mapping[str, ProviderAdapterMetadata] = {
    "experimental_free_provider": ProviderAdapterMetadata(
        provider_family="experimental_free_provider",
        adapter_id="experimental_free_adapter",
        display_name="Experimental Free Provider",
        provider_mode=ProviderMode.EXPERIMENTAL_FREE,
        supports_streaming=False,
        supports_tools=False,
        supports_files=False,
        supports_long_context=False,
        supports_sensitive_tools=False,
        is_experimental=True,
        is_user_key_required=False,
        is_managed=False,
        is_internal=False,
        default_enabled=True,
        public_description="Experimental access for free plan quota-limited requests.",
    ),
    "user_supplied_provider": ProviderAdapterMetadata(
        provider_family="user_supplied_provider",
        adapter_id="user_supplied_adapter",
        display_name="User Supplied Provider",
        provider_mode=ProviderMode.USER_KEY,
        supports_streaming=True,
        supports_tools=True,
        supports_files=True,
        supports_long_context=False,
        supports_sensitive_tools=False,
        is_experimental=False,
        is_user_key_required=True,
        is_managed=False,
        is_internal=False,
        default_enabled=True,
        public_description="Contract adapter for user-supplied provider access.",
    ),
    "managed_provider": ProviderAdapterMetadata(
        provider_family="managed_provider",
        adapter_id="managed_adapter",
        display_name="Managed Provider",
        provider_mode=ProviderMode.MANAGED,
        supports_streaming=True,
        supports_tools=True,
        supports_files=True,
        supports_long_context=True,
        supports_sensitive_tools=True,
        is_experimental=False,
        is_user_key_required=False,
        is_managed=True,
        is_internal=False,
        default_enabled=True,
        public_description="Contract adapter for managed provider access.",
    ),
    "internal_provider": ProviderAdapterMetadata(
        provider_family="internal_provider",
        adapter_id="internal_adapter",
        display_name="Internal Provider",
        provider_mode=ProviderMode.INTERNAL,
        supports_streaming=True,
        supports_tools=True,
        supports_files=True,
        supports_long_context=True,
        supports_sensitive_tools=True,
        is_experimental=False,
        is_user_key_required=False,
        is_managed=False,
        is_internal=True,
        default_enabled=True,
        public_description="Contract adapter for trusted internal access.",
    ),
}


def list_provider_adapters() -> list[ProviderAdapterMetadata]:
    return [PROVIDER_ADAPTERS[key] for key in sorted(PROVIDER_ADAPTERS)]


def list_public_provider_adapters() -> list[dict[str, Any]]:
    return [adapter.as_public_dict() for adapter in list_provider_adapters()]


def get_provider_adapter(provider_family: str) -> ProviderAdapterMetadata:
    family = str(provider_family or "").strip()
    try:
        return PROVIDER_ADAPTERS[family]
    except KeyError as exc:
        raise UnknownProviderFamilyError(f"Unknown provider family: {family or '<empty>'}") from exc


def build_public_provider_adapter_snapshot(provider_family: str) -> dict[str, Any]:
    return get_provider_adapter(provider_family).as_public_dict()


def validate_router_decision_adapter(decision: ProviderRoutingDecision | Mapping[str, Any]) -> bool:
    family = _decision_value(decision, "selected_provider_family")
    adapter = get_provider_adapter(str(family or ""))
    provider_mode = _decision_value(decision, "provider_mode")
    if isinstance(provider_mode, ProviderMode):
        provider_mode_value = provider_mode.value
    else:
        provider_mode_value = str(provider_mode or "")
    return adapter.provider_mode.value == provider_mode_value


def _decision_value(decision: ProviderRoutingDecision | Mapping[str, Any], key: str) -> Any:
    if isinstance(decision, ProviderRoutingDecision):
        return getattr(decision, key)
    return decision.get(key)
