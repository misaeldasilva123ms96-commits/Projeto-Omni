"""Read-only URLhaus lookup; the supplied target is never fetched or resolved."""

from __future__ import annotations

import ipaddress
from dataclasses import asdict, dataclass
from urllib.parse import urlsplit, urlunsplit

from brain.runtime.external.config import urlhaus_enabled
from brain.runtime.external.gateway import EventSink, ExternalAPIGateway, ExternalGatewayError
from brain.runtime.external.models import ExternalAPIRequest

URLHAUS_API_ID = "urlhaus"
URL_REPUTATION_TOOL_NAME = "url_reputation_check"


@dataclass(frozen=True, slots=True)
class URLReputationInput:
    url: str

    def normalized(self) -> str:
        raw = str(self.url or "")
        if not 1 <= len(raw) <= 2048 or raw != raw.strip():
            raise ValueError("invalid_url")
        if any(ord(character) < 32 or ord(character) == 127 for character in raw):
            raise ValueError("invalid_url")
        parsed = urlsplit(raw)
        if parsed.scheme.lower() not in {"http", "https"}:
            raise ValueError("url_scheme_not_allowed")
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("url_credentials_not_allowed")
        host = str(parsed.hostname or "").lower().rstrip(".")
        if not host:
            raise ValueError("invalid_url")
        if host == "localhost" or host.endswith((".localhost", ".local")) or "." not in host:
            raise ValueError("internal_url_not_allowed")
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            address = None
        if address is not None and not address.is_global:
            raise ValueError("internal_url_not_allowed")
        try:
            normalized_host = host.encode("idna").decode("ascii")
        except UnicodeError:
            raise ValueError("invalid_url") from None
        try:
            port = parsed.port
        except ValueError:
            raise ValueError("invalid_url") from None
        if port is not None and not 1 <= port <= 65535:
            raise ValueError("invalid_url")
        netloc = normalized_host
        if port and not (
            (parsed.scheme.lower() == "http" and port == 80)
            or (parsed.scheme.lower() == "https" and port == 443)
        ):
            netloc = f"{normalized_host}:{port}"
        return urlunsplit((parsed.scheme.lower(), netloc, parsed.path or "/", parsed.query, ""))


@dataclass(frozen=True, slots=True)
class URLReputationResult:
    status: str
    classification: str | None
    url_status: str | None
    threat: str | None
    date_added: str | None
    tags: list[str]
    provider: str
    provenance: dict[str, object]

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def _bounded(value: object, limit: int) -> str | None:
    return value.strip()[:limit] if isinstance(value, str) and value.strip() else None


def normalize_urlhaus_response(data: object, provenance: dict[str, object]) -> URLReputationResult:
    if not isinstance(data, dict):
        raise ExternalGatewayError("provider_schema_error")
    query_status = data.get("query_status")
    if query_status == "no_results":
        return URLReputationResult("not_listed", None, None, None, None, [], "URLhaus", provenance)
    if query_status != "ok":
        raise ExternalGatewayError("provider_schema_error")
    url_status = _bounded(data.get("url_status"), 100)
    threat = _bounded(data.get("threat"), 200)
    date_added = _bounded(data.get("date_added"), 100)
    if not url_status or not threat:
        raise ExternalGatewayError("provider_schema_error")
    raw_tags = data.get("tags", [])
    if not isinstance(raw_tags, list):
        raise ExternalGatewayError("provider_schema_error")
    tags = [item for item in (_bounded(tag, 100) for tag in raw_tags[:20]) if item]
    return URLReputationResult(
        "listed",
        "known_malware_url",
        url_status,
        threat,
        date_added,
        tags,
        "URLhaus",
        provenance,
    )


def check_url_reputation(
    value: URLReputationInput,
    *,
    gateway: ExternalAPIGateway,
    global_enabled: bool | None = None,
    provider_enabled: bool | None = None,
    event_sink: EventSink | None = None,
) -> URLReputationResult:
    normalized_url = value.normalized()
    response = gateway.execute(
        ExternalAPIRequest(
            api_id=URLHAUS_API_ID,
            method="POST",
            path="/v1/url/",
            form_fields={"url": normalized_url},
        ),
        global_enabled=global_enabled,
        provider_enabled=urlhaus_enabled() if provider_enabled is None else provider_enabled,
        event_sink=event_sink,
    )
    return normalize_urlhaus_response(response.data, dict(response.provenance))
