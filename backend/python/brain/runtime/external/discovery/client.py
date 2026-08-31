"""Governed loading and normalization of closed discovery sources."""

from __future__ import annotations

from datetime import UTC, datetime

from brain.runtime.external.config import (
    apis_guru_discovery_enabled,
    external_api_enabled,
    external_discovery_enabled,
    public_apis_discovery_enabled,
)
from brain.runtime.external.discovery.models import DiscoveryCandidate, SourceProvenance
from brain.runtime.external.discovery.parsers import (
    decode_public_apis_content,
    parse_apis_guru,
    parse_public_apis,
)
from brain.runtime.external.discovery.sources import APIS_GURU_ID, PUBLIC_APIS_ID
from brain.runtime.external.gateway import EventSink, ExternalAPIGateway, ExternalGatewayError
from brain.runtime.external.models import ExternalAPIRequest


class DiscoveryClient:
    def __init__(self, gateway: ExternalAPIGateway, *, event_sink: EventSink | None = None) -> None:
        self.gateway = gateway
        self.event_sink = event_sink

    def _emit(self, event: str, payload: dict[str, object]) -> None:
        if self.event_sink:
            try:
                self.event_sink(event, payload)
            except Exception:
                pass

    def load(self, source: str) -> tuple[DiscoveryCandidate, ...]:
        normalized = str(source).strip().lower().replace("-", "_")
        if not external_api_enabled():
            raise ExternalGatewayError("external_api_disabled")
        if not external_discovery_enabled():
            raise ExternalGatewayError("discovery_disabled")
        fetched_at = datetime.now(UTC).isoformat()
        try:
            if normalized == "apis_guru":
                if not apis_guru_discovery_enabled():
                    raise ExternalGatewayError("discovery_source_disabled")
                response = self.gateway.execute(
                    ExternalAPIRequest(APIS_GURU_ID, "GET", "/v2/list.json"),
                    global_enabled=True,
                    provider_enabled=True,
                )
                provenance = SourceProvenance(
                    "apis_guru",
                    "https://api.apis.guru/v2/list.json",
                    fetched_at,
                    bool(response.provenance.get("cached")),
                )
                candidates = parse_apis_guru(response.data, provenance, discovered_at=fetched_at)
            elif normalized == "public_apis":
                if not public_apis_discovery_enabled():
                    raise ExternalGatewayError("discovery_source_disabled")
                response = self.gateway.execute(
                    ExternalAPIRequest(
                        PUBLIC_APIS_ID,
                        "GET",
                        "/repos/public-apis/public-apis/contents/README.md",
                        query={"ref": "master"},
                        headers={"Accept": "application/vnd.github+json"},
                    ),
                    global_enabled=True,
                    provider_enabled=True,
                )
                markdown, revision = decode_public_apis_content(response.data)
                provenance = SourceProvenance(
                    "public_apis",
                    "https://api.github.com/repos/public-apis/public-apis/contents/"
                    "README.md?ref=master",
                    fetched_at,
                    bool(response.provenance.get("cached")),
                    revision,
                )
                candidates = parse_public_apis(markdown, provenance, discovered_at=fetched_at)
            else:
                raise ValueError("unknown discovery source")
        except Exception:
            self._emit("external_api.discovery.catalog_failed", {"source": normalized})
            raise
        issues = sum(len(candidate.issues) for candidate in candidates)
        self._emit(
            "external_api.discovery.catalog_loaded",
            {
                "source": normalized,
                "candidate_count": len(candidates),
                "cached": provenance.cached,
                "issues_count": issues,
            },
        )
        return candidates
