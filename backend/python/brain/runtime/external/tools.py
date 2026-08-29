"""Governed tool adapters for external APIs."""

from __future__ import annotations

from typing import Any

from brain.runtime.external.adapters.nominatim import (
    GEOCODE_TOOL_NAME,
    GeocodePlaceInput,
    get_geocode_place,
)
from brain.runtime.external.adapters.open_meteo import (
    WEATHER_TOOL_NAME,
    WeatherForecastInput,
    get_weather_forecast,
)
from brain.runtime.external.gateway import EventSink, ExternalAPIGateway, ExternalGatewayError
from brain.runtime.external.adapters.frankfurter import (
    CURRENCY_TOOL_NAME,
    CurrencyConvertInput,
    convert_currency,
)
from brain.runtime.external.adapters.free_dictionary import (
    DICTIONARY_TOOL_NAME,
    DictionaryLookupInput,
    lookup_dictionary,
)

EXTERNAL_TOOLS = frozenset(
    {WEATHER_TOOL_NAME, GEOCODE_TOOL_NAME, CURRENCY_TOOL_NAME, DICTIONARY_TOOL_NAME}
)


def supports_external_tool(tool_name: str) -> bool:
    return str(tool_name or "").strip() in EXTERNAL_TOOLS


def execute_external_action(
    *,
    action: dict[str, Any],
    gateway: ExternalAPIGateway,
    event_sink: EventSink | None = None,
) -> dict[str, Any]:
    tool = str(action.get("selected_tool", "") or "").strip()
    if tool not in EXTERNAL_TOOLS:
        return {
            "ok": False,
            "selected_tool": tool,
            "error_payload": {"kind": "unknown_external_tool"},
        }
    arguments = dict(action.get("tool_arguments", {}) or {})
    try:
        if tool == WEATHER_TOOL_NAME:
            value = WeatherForecastInput(
                latitude=arguments.get("latitude"),
                longitude=arguments.get("longitude"),
                forecast_days=arguments.get("forecast_days", 3),
            )
            result = get_weather_forecast(value, gateway=gateway, event_sink=event_sink)
            provider = "open_meteo"
        elif tool == GEOCODE_TOOL_NAME:
            geocode_value = GeocodePlaceInput(
                place_name=arguments.get("place_name"),
                state_or_region=arguments.get("state_or_region"),
                country_code=arguments.get("country_code"),
            )
            result = get_geocode_place(geocode_value, gateway=gateway, event_sink=event_sink)
            provider = "nominatim"
        elif tool == CURRENCY_TOOL_NAME:
            result = convert_currency(
                CurrencyConvertInput(
                    amount=arguments.get("amount"),
                    from_currency=arguments.get("from_currency"),
                    to_currency=arguments.get("to_currency"),
                ),
                gateway=gateway,
                event_sink=event_sink,
            )
            provider = "frankfurter"
        else:
            result = lookup_dictionary(
                DictionaryLookupInput(word=arguments.get("word")),
                gateway=gateway,
                event_sink=event_sink,
            )
            provider = "free_dictionary"
    except (ValueError, ExternalGatewayError) as exc:
        code = str(exc)
        return {
            "ok": False,
            "selected_tool": tool,
            "error_payload": {
                "kind": code,
                "message": {
                    WEATHER_TOOL_NAME: "Weather data unavailable.",
                    GEOCODE_TOOL_NAME: "Location data unavailable.",
                    CURRENCY_TOOL_NAME: "Currency conversion unavailable.",
                    DICTIONARY_TOOL_NAME: "Definition unavailable.",
                }[tool],
            },
        }
    return {
        "ok": True,
        "selected_tool": tool,
        "result_payload": result.as_dict(),
        "runtime_truth": {
            "source": (
                "local_computation"
                if result.provenance.get("source_type") == "local_compute"
                else "external_api"
            ),
            "provider": (
                "local" if result.provenance.get("source_type") == "local_compute" else provider
            ),
            "tool": tool,
            "cached": bool(result.provenance.get("cached")),
        },
    }
