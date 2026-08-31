"""Explicit typed bindings between governed tool results and later actions."""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class ToolBindingType(StrEnum):
    GEOCODE_UNIQUE_CANDIDATE_TO_WEATHER = "geocode_unique_candidate_to_weather"


@dataclass(frozen=True, slots=True)
class ToolOutputBinding:
    binding_type: ToolBindingType
    source_step_id: str
    source_tool: str = "geocode_place"
    target_tool: str = "weather_forecast"
    target_arguments: tuple[str, ...] = ("latitude", "longitude")

    @classmethod
    def parse(cls, value: object) -> ToolOutputBinding:
        if not isinstance(value, dict):
            raise ValueError("unknown_binding_type")
        if set(value) != {"type", "source_step_id"}:
            raise ValueError("binding_declaration_invalid")
        try:
            binding_type = ToolBindingType(str(value.get("type", "")))
        except ValueError as exc:
            raise ValueError("unknown_binding_type") from exc
        source_step_id = str(value.get("source_step_id", "") or "").strip()
        if not source_step_id:
            raise ValueError("binding_source_not_found")
        return cls(binding_type=binding_type, source_step_id=source_step_id)


@dataclass(frozen=True, slots=True)
class BindingResolution:
    action: dict[str, Any] | None
    provenance: dict[str, object]
    error: str | None = None


def _step_id(result: dict[str, Any]) -> str:
    direct = str(result.get("step_id", "") or "").strip()
    if direct:
        return direct
    action = result.get("action")
    return str(action.get("step_id", "") or "").strip() if isinstance(action, dict) else ""


def _coordinate(value: object, *, minimum: float, maximum: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("binding_source_invalid")
    number = float(value)
    if not math.isfinite(number) or not minimum <= number <= maximum:
        raise ValueError("binding_source_invalid")
    return number


def resolve_tool_output_binding(
    action: dict[str, Any], step_results: list[dict[str, Any]]
) -> BindingResolution:
    raw_binding = action.get("argument_binding")
    if raw_binding is None:
        return BindingResolution(action=dict(action), provenance={})
    try:
        binding = ToolOutputBinding.parse(raw_binding)
    except ValueError as exc:
        return BindingResolution(action=None, provenance={}, error=str(exc))
    provenance: dict[str, object] = {
        "type": binding.binding_type.value,
        "source_step_id": binding.source_step_id,
        "source_tool": binding.source_tool,
        "target_tool": binding.target_tool,
        "bound_fields": list(binding.target_arguments),
        "resolved": False,
    }
    target_step_id = str(action.get("step_id", "") or "").strip()
    if target_step_id and target_step_id == binding.source_step_id:
        return BindingResolution(None, provenance, "binding_cycle_denied")
    if str(action.get("selected_tool", "") or "").strip() != binding.target_tool:
        return BindingResolution(None, provenance, "binding_target_invalid")
    arguments = dict(action.get("tool_arguments", {}) or {})
    if any(field in arguments for field in binding.target_arguments):
        return BindingResolution(None, provenance, "binding_argument_conflict")
    matches = [result for result in step_results if _step_id(result) == binding.source_step_id]
    if not matches:
        return BindingResolution(None, provenance, "binding_source_not_found")
    if len(matches) != 1:
        return BindingResolution(None, provenance, "binding_source_ambiguous_identity")
    source = matches[0]
    if not source.get("ok"):
        return BindingResolution(None, provenance, "dependency_failed")
    if str(source.get("selected_tool", "") or "") != binding.source_tool:
        return BindingResolution(None, provenance, "binding_source_invalid")
    truth = source.get("runtime_truth")
    if not isinstance(truth, dict) or (
        truth.get("source") != "external_api"
        or truth.get("provider") != "nominatim"
        or truth.get("tool") != binding.source_tool
    ):
        return BindingResolution(None, provenance, "binding_source_invalid")
    payload = source.get("result_payload")
    if not isinstance(payload, dict):
        return BindingResolution(None, provenance, "binding_source_invalid")
    if payload.get("resolution") == "ambiguous":
        return BindingResolution(None, provenance, "binding_source_ambiguous")
    candidates = payload.get("candidates")
    if payload.get("resolution") != "unique" or not isinstance(candidates, (list, tuple)):
        return BindingResolution(None, provenance, "binding_source_invalid")
    if len(candidates) != 1 or not isinstance(candidates[0], dict):
        return BindingResolution(None, provenance, "binding_source_invalid")
    try:
        latitude = _coordinate(candidates[0].get("latitude"), minimum=-90.0, maximum=90.0)
        longitude = _coordinate(candidates[0].get("longitude"), minimum=-180.0, maximum=180.0)
    except ValueError as exc:
        return BindingResolution(None, provenance, str(exc))
    resolved_action = dict(action)
    resolved_action["tool_arguments"] = {
        **arguments,
        "latitude": latitude,
        "longitude": longitude,
    }
    provenance["resolved"] = True
    resolved_action["binding_provenance"] = provenance
    return BindingResolution(resolved_action, provenance)


__all__ = [
    "BindingResolution",
    "ToolBindingType",
    "ToolOutputBinding",
    "resolve_tool_output_binding",
]
