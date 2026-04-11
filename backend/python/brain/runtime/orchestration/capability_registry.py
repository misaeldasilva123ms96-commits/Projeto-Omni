from __future__ import annotations

from typing import Any

from .models import CapabilityDescriptor


class CapabilityRegistry:
    def __init__(self) -> None:
        self._capabilities = [
            CapabilityDescriptor(
                capability_id="planning_execution",
                subsystem="planning",
                supported_action_types=["plan", "inspect", "summarize"],
                priority_level=70,
                confidence_score=0.8,
                failure_risk="low",
            ),
            CapabilityDescriptor(
                capability_id="repair_workflow",
                subsystem="self_repair",
                supported_action_types=["repair", "mutate", "verify"],
                priority_level=75,
                confidence_score=0.72,
                failure_risk="medium",
            ),
            CapabilityDescriptor(
                capability_id="continuation_management",
                subsystem="continuation",
                supported_action_types=["continue", "retry", "pause", "rebuild", "escalate", "complete"],
                priority_level=95,
                confidence_score=0.9,
                failure_risk="low",
            ),
            CapabilityDescriptor(
                capability_id="engineering_tool_execution",
                subsystem="engineering_tools",
                supported_action_types=["read", "mutate", "verify", "execute"],
                priority_level=85,
                confidence_score=0.86,
                failure_risk="medium",
            ),
            CapabilityDescriptor(
                capability_id="rust_bridge_execution",
                subsystem="rust_bridge",
                supported_action_types=["read", "mutate", "verify", "execute"],
                priority_level=80,
                confidence_score=0.8,
                failure_risk="medium",
            ),
            CapabilityDescriptor(
                capability_id="memory_access",
                subsystem="memory",
                supported_action_types=["read", "inspect", "analysis"],
                priority_level=65,
                confidence_score=0.78,
                failure_risk="low",
            ),
            CapabilityDescriptor(
                capability_id="analysis_routine",
                subsystem="analysis",
                supported_action_types=["read", "analysis", "inspect"],
                priority_level=68,
                confidence_score=0.76,
                failure_risk="low",
            ),
        ]

    def list_capabilities(self) -> list[CapabilityDescriptor]:
        return list(self._capabilities)

    def get(self, capability_id: str) -> CapabilityDescriptor | None:
        for capability in self._capabilities:
            if capability.capability_id == capability_id:
                return capability
        return None

    def default_for_action(self, *, action_type: str, selected_tool: str, engineering_tool: bool) -> CapabilityDescriptor:
        if engineering_tool:
            return self.get("engineering_tool_execution") or self._capabilities[0]
        if action_type in {"read", "analysis"} and selected_tool in {"filesystem_read", "read_file", "grep_search", "glob_search", "code_search"}:
            return self.get("analysis_routine") or self._capabilities[0]
        return self.get("rust_bridge_execution") or self._capabilities[0]

    def as_dict(self) -> list[dict[str, Any]]:
        return [item.as_dict() for item in self._capabilities]
