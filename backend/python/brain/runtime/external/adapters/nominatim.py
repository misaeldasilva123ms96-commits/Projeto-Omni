"""Governed Nominatim settlement-geocoding development pilot."""

from __future__ import annotations

import math
import re
import unicodedata
from dataclasses import asdict, dataclass

from brain.runtime.external.config import nominatim_enabled
from brain.runtime.external.gateway import EventSink, ExternalAPIGateway, ExternalGatewayError
from brain.runtime.external.models import ExternalAPIRequest

OSM_GEOCODER_API_ID = "nominatim"
GEOCODE_TOOL_NAME = "geocode_place"
OSM_GEOCODER_USER_AGENT = (
    "Projeto-Omni-Geocoder/1.0 " "(+https://github.com/misaeldasilva123ms96-commits/Projeto-Omni)"
)
_COUNTRY_CODE = re.compile(r"^[A-Za-z]{2}$")


def _emit(event_sink: EventSink | None, event: str, payload: dict[str, object]) -> None:
    if not event_sink:
        return
    try:
        event_sink(event, payload)
    except Exception:
        return


def _normalize_text(value: object, *, field: str, minimum: int, maximum: int) -> str:
    if not isinstance(value, str):
        raise ValueError(f"invalid_{field}")
    if any(unicodedata.category(char) == "Cc" for char in value):
        raise ValueError(f"invalid_{field}")
    normalized = " ".join(unicodedata.normalize("NFC", value).split())
    if not minimum <= len(normalized) <= maximum:
        raise ValueError(f"invalid_{field}")
    return normalized


@dataclass(frozen=True, slots=True)
class GeocodePlaceInput:
    place_name: str
    state_or_region: str | None = None
    country_code: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "place_name",
            _normalize_text(self.place_name, field="place_name", minimum=2, maximum=100),
        )
        if self.state_or_region is not None and not isinstance(self.state_or_region, str):
            raise ValueError("invalid_state_or_region")
        if self.state_or_region is not None and not self.state_or_region.strip():
            object.__setattr__(self, "state_or_region", None)
        elif self.state_or_region is not None:
            object.__setattr__(
                self,
                "state_or_region",
                _normalize_text(
                    self.state_or_region,
                    field="state_or_region",
                    minimum=1,
                    maximum=100,
                ),
            )
        if self.country_code is not None and not isinstance(self.country_code, str):
            raise ValueError("invalid_country_code")
        if self.country_code is not None and not self.country_code.strip():
            object.__setattr__(self, "country_code", None)
        elif self.country_code is not None:
            if not isinstance(self.country_code, str) or not _COUNTRY_CODE.fullmatch(
                self.country_code
            ):
                raise ValueError("invalid_country_code")
            object.__setattr__(self, "country_code", self.country_code.lower())


@dataclass(frozen=True, slots=True)
class GeocodeCandidate:
    display_name: str
    latitude: float
    longitude: float
    country_code: str
    category: str
    type: str
    importance: float | None
    state_or_region: str | None = None


@dataclass(frozen=True, slots=True)
class GeocodePlaceResult:
    query: dict[str, str]
    candidates: tuple[GeocodeCandidate, ...]
    resolution: str
    provider: str
    provenance: dict[str, object]

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def build_nominatim_request(value: GeocodePlaceInput) -> ExternalAPIRequest:
    parts = [value.place_name]
    if value.state_or_region:
        parts.append(value.state_or_region)
    query: dict[str, str | int] = {
        "q": ", ".join(parts),
        "format": "jsonv2",
        "addressdetails": 1,
        "limit": 3,
        "featureType": "settlement",
        "accept-language": "pt-BR,pt,en",
    }
    if value.country_code:
        query["countrycodes"] = value.country_code
    return ExternalAPIRequest(
        api_id=OSM_GEOCODER_API_ID,
        method="GET",
        path="/search",
        query=query,
        headers={"User-Agent": OSM_GEOCODER_USER_AGENT},
    )


def _number(value: object, *, minimum: float, maximum: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        raise ExternalGatewayError("provider_schema_error")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ExternalGatewayError("provider_schema_error") from exc
    if not math.isfinite(number) or not minimum <= number <= maximum:
        raise ExternalGatewayError("provider_schema_error")
    return number


def normalize_nominatim_response(
    data: object,
    *,
    value: GeocodePlaceInput,
    provenance: dict[str, object],
) -> GeocodePlaceResult:
    if not isinstance(data, list):
        raise ExternalGatewayError("provider_schema_error")
    if not data:
        raise ExternalGatewayError("location_not_found")
    candidates: list[GeocodeCandidate] = []
    for raw in data[:3]:
        if not isinstance(raw, dict):
            raise ExternalGatewayError("provider_schema_error")
        display_name = raw.get("display_name")
        category = raw.get("class")
        result_type = raw.get("type")
        address = raw.get("address")
        if (
            not isinstance(display_name, str)
            or not display_name.strip()
            or not isinstance(category, str)
            or not category
            or not isinstance(result_type, str)
            or not result_type
            or not isinstance(address, dict)
            or not isinstance(address.get("country_code"), str)
            or not _COUNTRY_CODE.fullmatch(str(address.get("country_code")))
        ):
            raise ExternalGatewayError("provider_schema_error")
        importance_raw = raw.get("importance")
        importance = (
            None if importance_raw is None else _number(importance_raw, minimum=0.0, maximum=1.0)
        )
        state = address.get("state") or address.get("region")
        if state is not None and not isinstance(state, str):
            raise ExternalGatewayError("provider_schema_error")
        candidates.append(
            GeocodeCandidate(
                display_name=display_name.strip()[:300],
                latitude=_number(raw.get("lat"), minimum=-90.0, maximum=90.0),
                longitude=_number(raw.get("lon"), minimum=-180.0, maximum=180.0),
                country_code=str(address["country_code"]).lower(),
                category=category[:80],
                type=result_type[:80],
                importance=importance,
                state_or_region=state.strip()[:100] if state else None,
            )
        )
    return GeocodePlaceResult(
        query={
            "place_name": value.place_name,
            **({"state_or_region": value.state_or_region} if value.state_or_region else {}),
            **({"country_code": value.country_code} if value.country_code else {}),
        },
        candidates=tuple(candidates),
        resolution="unique" if len(candidates) == 1 else "ambiguous",
        provider="Nominatim / OpenStreetMap",
        provenance=provenance,
    )


def get_geocode_place(
    value: GeocodePlaceInput,
    *,
    gateway: ExternalAPIGateway,
    global_enabled: bool | None = None,
    provider_enabled: bool | None = None,
    event_sink: EventSink | None = None,
) -> GeocodePlaceResult:
    response = gateway.execute(
        build_nominatim_request(value),
        global_enabled=global_enabled,
        provider_enabled=nominatim_enabled() if provider_enabled is None else provider_enabled,
        event_sink=event_sink,
    )
    try:
        result = normalize_nominatim_response(
            response.data,
            value=value,
            provenance=dict(response.provenance),
        )
    except ExternalGatewayError as exc:
        _emit(
            event_sink,
            "external_api.request_failed",
            {"api_id": OSM_GEOCODER_API_ID, "tool": GEOCODE_TOOL_NAME, "reason": exc.code},
        )
        raise
    _emit(
        event_sink,
        "external_api.geocode_normalized",
        {
            "api_id": OSM_GEOCODER_API_ID,
            "tool": GEOCODE_TOOL_NAME,
            "candidate_count": len(result.candidates),
            "resolution": result.resolution,
            "cached": bool(result.provenance.get("cached")),
        },
    )
    return result
