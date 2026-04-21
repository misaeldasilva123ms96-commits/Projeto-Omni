from __future__ import annotations

from typing import Iterable

from brain.runtime.engineering_tools import ENGINEERING_TOOLS
from brain.runtime.tooling.tool_metadata import ToolMetadata, conservative_tool_metadata


_TOOL_METADATA: dict[str, ToolMetadata] = {
    "read_file": ToolMetadata(
        name="read_file",
        category="filesystem",
        description="reads file contents from the workspace",
        input_schema_hint="{'path': str}",
        risk_level="low",
        estimated_cost="low",
        latency_class="fast",
        deterministic=True,
        requires_network=False,
        requires_auth=False,
        safe_fallback_available=True,
    ),
    "filesystem_read": ToolMetadata(
        name="filesystem_read",
        category="filesystem",
        description="reads file contents through the filesystem bridge",
        input_schema_hint="{'path': str}",
        risk_level="low",
        estimated_cost="low",
        latency_class="fast",
        deterministic=True,
        requires_network=False,
        requires_auth=False,
        safe_fallback_available=True,
    ),
    "glob_search": ToolMetadata(
        name="glob_search",
        category="search",
        description="finds files by pattern in the workspace",
        input_schema_hint="{'pattern': str}",
        risk_level="low",
        estimated_cost="low",
        latency_class="fast",
        deterministic=True,
        requires_network=False,
        requires_auth=False,
        safe_fallback_available=True,
    ),
    "grep_search": ToolMetadata(
        name="grep_search",
        category="search",
        description="searches text patterns in repository files",
        input_schema_hint="{'pattern': str}",
        risk_level="low",
        estimated_cost="low",
        latency_class="fast",
        deterministic=True,
        requires_network=False,
        requires_auth=False,
        safe_fallback_available=True,
    ),
    "code_search": ToolMetadata(
        name="code_search",
        category="search",
        description="searches semantically relevant code symbols or snippets",
        input_schema_hint="{'query': str}",
        risk_level="low",
        estimated_cost="medium",
        latency_class="fast",
        deterministic=False,
        requires_network=False,
        requires_auth=False,
        safe_fallback_available=True,
    ),
    "shell_command": ToolMetadata(
        name="shell_command",
        category="execution",
        description="executes shell commands in the workspace",
        input_schema_hint="{'command': str}",
        risk_level="high",
        estimated_cost="medium",
        latency_class="variable",
        deterministic=False,
        requires_network=False,
        requires_auth=False,
        safe_fallback_available=False,
    ),
    "test_runner": ToolMetadata(
        name="test_runner",
        category="verification",
        description="runs validation or test commands",
        input_schema_hint="{'command': str}",
        risk_level="medium",
        estimated_cost="medium",
        latency_class="slow",
        deterministic=False,
        requires_network=False,
        requires_auth=False,
        safe_fallback_available=True,
    ),
    "verification_runner": ToolMetadata(
        name="verification_runner",
        category="verification",
        description="runs focused verification flows",
        input_schema_hint="{'command': str}",
        risk_level="medium",
        estimated_cost="medium",
        latency_class="slow",
        deterministic=False,
        requires_network=False,
        requires_auth=False,
        safe_fallback_available=True,
    ),
}

for engineering_tool in ENGINEERING_TOOLS:
    _TOOL_METADATA.setdefault(
        engineering_tool,
        ToolMetadata(
            name=engineering_tool,
            category="engineering",
            description=f"engineering tool {engineering_tool}",
            input_schema_hint="opaque_dict",
            risk_level="medium",
            estimated_cost="medium",
            latency_class="variable",
            deterministic=False,
            requires_network=False,
            requires_auth=False,
            safe_fallback_available=True,
        ),
    )

_CAPABILITY_METADATA: dict[str, ToolMetadata] = {
    "analysis_routine": ToolMetadata(
        name="analysis_routine",
        category="analysis",
        description="repository and context analysis capability",
        input_schema_hint="{'action_type': str, 'selected_tool': str}",
        risk_level="low",
        estimated_cost="low",
        latency_class="fast",
        deterministic=False,
        requires_network=False,
        requires_auth=False,
        safe_fallback_available=True,
    ),
    "engineering_tool_execution": ToolMetadata(
        name="engineering_tool_execution",
        category="execution",
        description="engineering workflow execution capability",
        input_schema_hint="{'action_type': str, 'selected_tool': str}",
        risk_level="medium",
        estimated_cost="medium",
        latency_class="variable",
        deterministic=False,
        requires_network=False,
        requires_auth=False,
        safe_fallback_available=True,
    ),
    "rust_bridge_execution": ToolMetadata(
        name="rust_bridge_execution",
        category="bridge",
        description="Rust bridge execution capability",
        input_schema_hint="{'action_type': str, 'selected_tool': str}",
        risk_level="medium",
        estimated_cost="medium",
        latency_class="variable",
        deterministic=False,
        requires_network=False,
        requires_auth=False,
        safe_fallback_available=True,
    ),
}


def get_tool_metadata(name: str) -> ToolMetadata:
    key = str(name or "").strip()
    if not key:
        return conservative_tool_metadata("unknown_tool")
    return _TOOL_METADATA.get(key, conservative_tool_metadata(key))


def get_capability_metadata(capability_id: str) -> ToolMetadata:
    key = str(capability_id or "").strip()
    if not key:
        return conservative_tool_metadata("unknown_capability", category="capability")
    return _CAPABILITY_METADATA.get(key, conservative_tool_metadata(key, category="capability"))


def describe_tool_metadata(names: Iterable[str]) -> list[dict[str, object]]:
    return [get_tool_metadata(name).as_dict() for name in names]
