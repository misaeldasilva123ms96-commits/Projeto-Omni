"""Exact, candidate-scoped APIs.guru schema network authority."""

from __future__ import annotations

from urllib.parse import unquote, urlsplit

from brain.runtime.external.discovery.models import DiscoveryCandidate, candidate_id
from brain.runtime.external.discovery.parsers import _schema_locator
from brain.runtime.external.models import ExternalAPIDefinition, RedirectPolicy
from brain.runtime.external.registry import ExternalAPIRegistry

SCHEMA_INTAKE_API_ID = "discovery_apis_guru_schema_intake"
MAX_SCHEMA_BYTES = 8 * 1024 * 1024


class SchemaIntakeError(RuntimeError):
    pass


def validate_schema_candidate(candidate: DiscoveryCandidate) -> str:
    if candidate.source != "apis_guru":
        raise SchemaIntakeError("schema_intake_source_not_supported")
    if (
        candidate.trust != "discovery_only"
        or candidate.review_state != "manual_review_required"
        or candidate.execution_authorized
        or candidate.registration_authorized
        or candidate.network_authority
    ):
        raise SchemaIntakeError("candidate_authority_invalid")
    if candidate.candidate_id != candidate_id(candidate.source, candidate.source_record_id):
        raise SchemaIntakeError("candidate_identity_invalid")
    if (
        not candidate.schema_available
        or not candidate.schema_locator
        or not candidate.preferred_version
    ):
        raise SchemaIntakeError("schema_unavailable")
    if _schema_locator(candidate.schema_locator) != candidate.schema_locator:
        raise SchemaIntakeError("schema_locator_invalid")
    parsed = urlsplit(candidate.schema_locator)
    raw_path = parsed.path
    lowered = raw_path.casefold()
    if any(token in lowered for token in ("%2f", "%5c", "%2e")):
        raise SchemaIntakeError("schema_locator_invalid")
    parts = unquote(raw_path).split("/")
    expected = ["", "v2", "specs", candidate.provider]
    if candidate.service:
        expected.append(candidate.service)
    expected.extend([candidate.preferred_version, parts[-1]])
    if parts != expected:
        raise SchemaIntakeError("candidate_schema_identity_mismatch")
    return raw_path


def build_schema_intake_registry(candidate: DiscoveryCandidate) -> ExternalAPIRegistry:
    path = validate_schema_candidate(candidate)
    registry = ExternalAPIRegistry()
    registry.register(
        ExternalAPIDefinition(
            api_id=SCHEMA_INTAKE_API_ID,
            name="APIs.guru exact schema intake",
            description="Candidate-scoped review-only OpenAPI JSON intake",
            base_url="https://api.apis.guru",
            allowed_hosts=frozenset({"api.apis.guru"}),
            allowed_methods=frozenset({"GET"}),
            allowed_paths=frozenset({path}),
            max_response_bytes=MAX_SCHEMA_BYTES,
            redirect_policy=RedirectPolicy.DENY,
            cache_ttl_seconds=None,
            max_attempts=1,
            rate_limit_requests=1,
            rate_limit_window_seconds=60,
            enabled=True,
            provenance="APIs.guru mirrored schema; structural review only",
        )
    )
    return registry
