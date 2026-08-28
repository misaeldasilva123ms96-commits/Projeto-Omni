"""Governed tool adapters for external APIs."""

from __future__ import annotations

from typing import Any

from brain.runtime.external.adapters.open_meteo import (
    WEATHER_TOOL_NAME,
    WeatherForecastInput,
    get_weather_forecast,
)
from brain.runtime.external.gateway import EventSink, ExternalAPIGateway, ExternalGatewayError

EXTERNAL_TOOLS = frozenset({WEATHER_TOOL_NAME})


def supports_external_tool(tool_name: str) -> bool:
    return str(tool_name or "").strip() in EXTERNAL_TOOLS


def execute_external_action(
    *,
    action: dict[str, Any],
    gateway: ExternalAPIGateway,
    event_sink: EventSink | None = None,
) -> dict[str, Any]:
    tool = str(action.get("selected_tool", "") or "").strip()
    if tool != WEATHER_TOOL_NAME:
        return {
            "ok": False,
            "selected_tool": tool,
            "error_payload": {"kind": "unknown_external_tool"},
        }
    arguments = dict(action.get("tool_arguments", {}) or {})
    try:
        value = WeatherForecastInput(
            latitude=arguments.get("latitude"),
            longitude=arguments.get("longitude"),
            forecast_days=arguments.get("forecast_days", 3),
        )
        result = get_weather_forecast(value, gateway=gateway, event_sink=event_sink)
    except (ValueError, ExternalGatewayError) as exc:
        code = str(exc)
        return {
            "ok": False,
            "selected_tool": tool,
            "error_payload": {
                "kind": code,
                "message": "Weather data unavailable.",
            },
        }
    return {
        "ok": True,
        "selected_tool": tool,
        "result_payload": result.as_dict(),
        "runtime_truth": {
            "source": "external_api",
            "provider": "open_meteo",
            "tool": WEATHER_TOOL_NAME,
            "cached": bool(result.provenance.get("cached")),
        },
    }
