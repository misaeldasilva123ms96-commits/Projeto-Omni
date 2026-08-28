"""Governed Open-Meteo development/evaluation weather pilot."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from brain.runtime.external.config import open_meteo_enabled
from brain.runtime.external.gateway import EventSink, ExternalAPIGateway, ExternalGatewayError
from brain.runtime.external.models import ExternalAPIRequest

OPEN_METEO_API_ID = "open_meteo"
WEATHER_TOOL_NAME = "weather_forecast"
CURRENT_FIELDS = (
    "temperature_2m",
    "apparent_temperature",
    "precipitation",
    "weather_code",
    "wind_speed_10m",
)
DAILY_FIELDS = (
    "weather_code",
    "temperature_2m_max",
    "temperature_2m_min",
    "precipitation_sum",
)


@dataclass(frozen=True, slots=True)
class WeatherForecastInput:
    latitude: float
    longitude: float
    forecast_days: int = 3

    def __post_init__(self) -> None:
        if isinstance(self.latitude, bool) or not isinstance(self.latitude, (int, float)):
            raise ValueError("invalid_latitude")
        if isinstance(self.longitude, bool) or not isinstance(self.longitude, (int, float)):
            raise ValueError("invalid_longitude")
        if isinstance(self.forecast_days, bool) or not isinstance(self.forecast_days, int):
            raise ValueError("invalid_forecast_days")
        if not -90 <= float(self.latitude) <= 90:
            raise ValueError("invalid_latitude")
        if not -180 <= float(self.longitude) <= 180:
            raise ValueError("invalid_longitude")
        if not 1 <= self.forecast_days <= 7:
            raise ValueError("invalid_forecast_days")


@dataclass(frozen=True, slots=True)
class WeatherForecastResult:
    location: dict[str, float]
    timezone: str
    current: dict[str, Any]
    daily: dict[str, list[Any]]
    provider: str
    provenance: dict[str, object]

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def build_open_meteo_request(value: WeatherForecastInput) -> ExternalAPIRequest:
    return ExternalAPIRequest(
        api_id=OPEN_METEO_API_ID,
        method="GET",
        path="/v1/forecast",
        query={
            "latitude": float(value.latitude),
            "longitude": float(value.longitude),
            "forecast_days": value.forecast_days,
            "current": CURRENT_FIELDS,
            "daily": DAILY_FIELDS,
            "timezone": "auto",
        },
    )


def normalize_open_meteo_response(
    data: object, provenance: dict[str, object]
) -> WeatherForecastResult:
    if not isinstance(data, dict):
        raise ExternalGatewayError("provider_schema_error")
    latitude = data.get("latitude")
    longitude = data.get("longitude")
    timezone = data.get("timezone")
    current = data.get("current")
    daily = data.get("daily")
    if (
        isinstance(latitude, bool)
        or not isinstance(latitude, (int, float))
        or isinstance(longitude, bool)
        or not isinstance(longitude, (int, float))
        or not isinstance(timezone, str)
        or not timezone
        or not isinstance(current, dict)
        or not isinstance(daily, dict)
    ):
        raise ExternalGatewayError("provider_schema_error")
    if any(field not in current for field in CURRENT_FIELDS):
        raise ExternalGatewayError("provider_schema_error")
    if "time" not in current or any(field not in daily for field in ("time", *DAILY_FIELDS)):
        raise ExternalGatewayError("provider_schema_error")
    if not isinstance(current["time"], str) or any(
        isinstance(current[field], bool) or not isinstance(current[field], (int, float))
        for field in CURRENT_FIELDS
    ):
        raise ExternalGatewayError("provider_schema_error")
    daily_values = {field: daily[field] for field in ("time", *DAILY_FIELDS)}
    if any(not isinstance(value, list) for value in daily_values.values()):
        raise ExternalGatewayError("provider_schema_error")
    lengths = {len(value) for value in daily_values.values()}
    if len(lengths) != 1:
        raise ExternalGatewayError("provider_schema_error")
    if any(not isinstance(item, str) for item in daily_values["time"]):
        raise ExternalGatewayError("provider_schema_error")
    if any(
        isinstance(item, bool) or not isinstance(item, (int, float))
        for field in DAILY_FIELDS
        for item in daily_values[field]
    ):
        raise ExternalGatewayError("provider_schema_error")
    return WeatherForecastResult(
        location={"latitude": float(latitude), "longitude": float(longitude)},
        timezone=timezone,
        current={field: current[field] for field in ("time", *CURRENT_FIELDS)},
        daily=daily_values,
        provider="Open-Meteo",
        provenance=provenance,
    )


def get_weather_forecast(
    value: WeatherForecastInput,
    *,
    gateway: ExternalAPIGateway,
    global_enabled: bool | None = None,
    provider_enabled: bool | None = None,
    event_sink: EventSink | None = None,
) -> WeatherForecastResult:
    response = gateway.execute(
        build_open_meteo_request(value),
        global_enabled=global_enabled,
        provider_enabled=open_meteo_enabled() if provider_enabled is None else provider_enabled,
        event_sink=event_sink,
    )
    return normalize_open_meteo_response(response.data, dict(response.provenance))
