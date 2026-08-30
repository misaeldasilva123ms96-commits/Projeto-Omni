from __future__ import annotations

from dataclasses import replace

from brain.runtime.external.discovery.models import (
    DiscoveryCandidate,
    SourceProvenance,
    candidate_id,
)
from brain.runtime.external.schema_intake import analyze_openapi_schema
from brain.runtime.external.schema_intake.models import ProviderDesignProposal


def proposal_document() -> dict[str, object]:
    return {
        "openapi": "3.1.2",
        "info": {"title": "Review fixture", "version": "1"},
        "servers": [{"url": "https://api.example.com/v1"}],
        "paths": {
            "/pets": {
                "get": {"operationId": "listPets", "responses": {"200": {}}},
                "head": {"responses": {"200": {}}},
                "post": {"responses": {"201": {}}},
            },
            "/pets/{id}": {
                "delete": {"security": [], "responses": {"204": {}}},
                "patch": {
                    "security": [{}, {"oauth": ["write"]}],
                    "responses": {"200": {}},
                },
            },
        },
        "components": {"securitySchemes": {"oauth": {"type": "oauth2", "flows": {}}}},
    }


def proposal() -> ProviderDesignProposal:
    provenance = SourceProvenance(
        "apis_guru", "https://api.apis.guru/v2/list.json", "2026-08-30T00:00:00Z", False
    )
    identity = candidate_id("apis_guru", "example.com:service")
    candidate = DiscoveryCandidate(
        candidate_id=identity,
        source="apis_guru",
        source_record_id="example.com:service",
        name="Example",
        provider="example.com",
        service="service",
        schema_available=True,
        schema_locator="https://api.apis.guru/v2/specs/example.com/service/1/openapi.json",
        preferred_version="1",
        openapi_version="3.1.2",
        discovered_at="now",
        source_provenance=provenance,
    )
    return analyze_openapi_schema(candidate, proposal_document())


def with_operations(value: ProviderDesignProposal, *operations):
    return replace(
        value,
        operations=tuple(operations),
        operation_count=len(operations),
        operation_details_truncated=False,
    )
