"""Governed tool declaration, registry, and strict-mode enforcement (Phase 30.13).

Default behavior is backward-compatible: tools on the trusted execution surface are
auto-registered as governed except an explicit legacy canary set (``directory_tree``).
Strict mode (``OMINI_GOVERNED_TOOLS_STRICT=true``) blocks any tool that is not present
in the governed registry (empty tool and ``none`` remain exempt).
"""

from __future__ import annotations

import os
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any, TypeVar

from brain.runtime.control.governance_taxonomy import GovernanceReason, GovernanceSeverity, GovernanceSource

STRICT_GOVERNED_TOOLS_ENV = "OMINI_GOVERNED_TOOLS_STRICT"

GOVERNED_TOOLS_STRICT_BLOCK_KIND = "governed_tools_strict_block"

F = TypeVar("F", bound=Callable[..., Any])

_DEFAULT_LEGACY_UNGOVERNED: frozenset[str] = frozenset({"directory_tree"})

_REGISTRY: dict[str, "GovernedToolSpec"] = {}
_SURFACE_SYNCED: bool = False


@dataclass(frozen=True, slots=True)
class GovernedToolSpec:
    tool_name: str
    policy_name: str
    category: str = "general"
    extensions: Mapping[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ToolGovernanceAudit:
    allowed: bool
    governed: bool
    legacy_ungoverned_trusted: bool
    strict_mode: bool
    tool_name: str
    policy_name: str | None
    category: str | None
    extensions: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "governed": self.governed,
            "legacy_ungoverned_trusted": self.legacy_ungoverned_trusted,
            "strict_mode": self.strict_mode,
            "tool_name": self.tool_name,
            "policy_name": self.policy_name,
            "category": self.category,
            "extensions": dict(self.extensions),
        }


def is_strict_governed_tools_mode() -> bool:
    raw = str(os.getenv(STRICT_GOVERNED_TOOLS_ENV, "") or "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def register_governed_tool(spec: GovernedToolSpec, *, overwrite: bool = False) -> None:
    name = str(spec.tool_name or "").strip()
    if not name or name == "none":
        return
    if name in _REGISTRY and not overwrite:
        return
    _REGISTRY[name] = GovernedToolSpec(
        tool_name=name,
        policy_name=str(spec.policy_name or "").strip() or "unspecified",
        category=str(spec.category or "").strip() or "general",
        extensions=dict(spec.extensions or {}),
    )


def governed_tool(
    *,
    tool_name: str,
    policy_name: str,
    category: str = "general",
    **extensions: Any,
) -> Callable[[F], F]:
    """Declare governance metadata for a tool (anchor function is not used at runtime)."""

    def decorator(fn: F) -> F:
        register_governed_tool(
            GovernedToolSpec(
                tool_name=tool_name,
                policy_name=policy_name,
                category=category,
                extensions={"declaration": "decorator", **extensions},
            ),
            overwrite=True,
        )
        return fn

    return decorator


def get_governed_tool_metadata(tool_name: str) -> GovernedToolSpec | None:
    name = str(tool_name or "").strip()
    if not name:
        return None
    return _REGISTRY.get(name)


def is_governed_tool(tool_name: str) -> bool:
    return get_governed_tool_metadata(tool_name) is not None


def list_governed_tools() -> list[GovernedToolSpec]:
    return sorted(_REGISTRY.values(), key=lambda s: s.tool_name)


def list_governed_tools_as_dicts() -> list[dict[str, Any]]:
    return [
        {
            "tool_name": s.tool_name,
            "policy_name": s.policy_name,
            "category": s.category,
            "extensions": dict(s.extensions),
        }
        for s in list_governed_tools()
    ]


def validate_tool_governance(tool_name: str) -> dict[str, Any]:
    meta = get_governed_tool_metadata(tool_name)
    return {
        "tool_name": str(tool_name or "").strip(),
        "governed": meta is not None,
        "strict_mode": is_strict_governed_tools_mode(),
        "metadata": meta.extensions if meta is not None else {},
    }


def sync_governed_tools_from_trusted_executor_surface(
    available_tools: Iterable[str],
    *,
    legacy_ungoverned: frozenset[str] | None = None,
    force: bool = False,
) -> None:
    """Register governed metadata for trusted tools (skips legacy canary names)."""
    global _SURFACE_SYNCED
    if _SURFACE_SYNCED and not force:
        return
    legacy = legacy_ungoverned if legacy_ungoverned is not None else _DEFAULT_LEGACY_UNGOVERNED
    for raw in available_tools:
        name = str(raw or "").strip()
        if not name or name == "none" or name in legacy:
            continue
        register_governed_tool(
            GovernedToolSpec(
                tool_name=name,
                policy_name="trusted_execution_surface",
                category="auto_registered",
                extensions={"source": "trusted_executor_surface_sync"},
            ),
            overwrite=False,
        )
    _SURFACE_SYNCED = True


def reset_governed_tool_registry_for_tests() -> None:
    """Clear registry and sync flag (unit tests only)."""
    global _SURFACE_SYNCED
    _REGISTRY.clear()
    _SURFACE_SYNCED = False


def evaluate_tool_governance(
    *,
    selected_tool: str,
    trusted_known_tools: set[str],
    strict_mode: bool | None = None,
) -> ToolGovernanceAudit:
    name = str(selected_tool or "").strip()
    strict = is_strict_governed_tools_mode() if strict_mode is None else bool(strict_mode)
    if not name or name == "none":
        return ToolGovernanceAudit(
            allowed=True,
            governed=False,
            legacy_ungoverned_trusted=False,
            strict_mode=strict,
            tool_name=name,
            policy_name=None,
            category=None,
            extensions={"note": "no_tool_selected"},
        )
    meta = get_governed_tool_metadata(name)
    governed = meta is not None
    in_trusted = name in trusted_known_tools
    legacy = in_trusted and not governed
    if governed and meta is not None:
        return ToolGovernanceAudit(
            allowed=True,
            governed=True,
            legacy_ungoverned_trusted=False,
            strict_mode=strict,
            tool_name=name,
            policy_name=meta.policy_name,
            category=meta.category,
            extensions=dict(meta.extensions),
        )
    if strict:
        return ToolGovernanceAudit(
            allowed=False,
            governed=False,
            legacy_ungoverned_trusted=legacy,
            strict_mode=True,
            tool_name=name,
            policy_name=None,
            category=None,
            extensions={"note": "strict_mode_requires_governed_declaration"},
        )
    return ToolGovernanceAudit(
        allowed=True,
        governed=False,
        legacy_ungoverned_trusted=legacy,
        strict_mode=False,
        tool_name=name,
        policy_name=None,
        category=None,
        extensions={"note": "legacy_ungoverned" if legacy else "outside_trusted_tool_surface"},
    )


def governance_dict_for_strict_block() -> dict[str, str]:
    return {
        "reason": GovernanceReason.POLICY_BLOCK.value,
        "source": GovernanceSource.POLICY.value,
        "severity": GovernanceSeverity.WARNING.value,
    }


def build_strict_block_evaluation(*, tool_audit: ToolGovernanceAudit) -> dict[str, Any]:
    return {
        "decision": "governed_tools_strict_blocked",
        "reason_code": GOVERNED_TOOLS_STRICT_BLOCK_KIND,
        "tool_governance_audit": tool_audit.as_dict(),
        "critic": {
            "invoked": False,
            "decision": "stop",
            "reason_code": GOVERNED_TOOLS_STRICT_BLOCK_KIND,
        },
        "learning_guidance": None,
    }


@governed_tool(tool_name="read_file", policy_name="trusted_read", category="filesystem")
def _declare_read_file_governed() -> None:
    """Explicit governed declaration anchor (Phase 30.13)."""
    return None


@governed_tool(tool_name="write_file", policy_name="trusted_write", category="filesystem")
def _declare_write_file_governed() -> None:
    return None
