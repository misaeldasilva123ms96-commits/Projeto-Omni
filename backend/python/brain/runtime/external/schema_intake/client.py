"""Governed candidate-bound schema fetch and local proposal analysis."""

from __future__ import annotations

from typing import Callable

from brain.runtime.external.config import (
    apis_guru_discovery_enabled,
    apis_guru_schema_intake_enabled,
    external_api_enabled,
    external_discovery_enabled,
    external_schema_intake_enabled,
)
from brain.runtime.external.discovery.models import DiscoveryCandidate
from brain.runtime.external.gateway import (
    EventSink,
    ExternalAPIGateway,
    ExternalGatewayError,
    LocalRateLimiter,
    Resolver,
    Transport,
)
from brain.runtime.external.models import ExternalAPIRequest
from brain.runtime.external.schema_intake.analyzer import analyze_openapi_schema
from brain.runtime.external.schema_intake.models import ProviderDesignProposal
from brain.runtime.external.schema_intake.registry import (
    SCHEMA_INTAKE_API_ID,
    SchemaIntakeError,
    build_schema_intake_registry,
    validate_schema_candidate,
)

GatewayFactory = Callable[[object], ExternalAPIGateway]


class SchemaIntakeClient:
    def __init__(
        self,
        *,
        resolver: Resolver | None = None,
        transport: Transport | None = None,
        event_sink: EventSink | None = None,
        gateway_factory: GatewayFactory | None = None,
    ) -> None:
        self.resolver = resolver
        self.transport = transport
        self.event_sink = event_sink
        self.gateway_factory = gateway_factory
        self.rate_limiter = LocalRateLimiter()

    def _emit(self, event: str, payload: dict[str, object]) -> None:
        if self.event_sink:
            try:
                self.event_sink(event, payload)
            except Exception:
                pass

    @staticmethod
    def _require_gates() -> None:
        gates = (
            (external_api_enabled(), "external_api_disabled"),
            (external_discovery_enabled(), "discovery_disabled"),
            (apis_guru_discovery_enabled(), "discovery_source_disabled"),
            (external_schema_intake_enabled(), "schema_intake_disabled"),
            (apis_guru_schema_intake_enabled(), "schema_intake_source_disabled"),
        )
        for enabled, code in gates:
            if not enabled:
                raise SchemaIntakeError(code)

    def intake(self, candidate: DiscoveryCandidate) -> ProviderDesignProposal:
        path = validate_schema_candidate(candidate)
        self._require_gates()
        registry = build_schema_intake_registry(candidate)
        if self.gateway_factory:
            gateway = self.gateway_factory(registry)
        else:
            gateway = ExternalAPIGateway(
                registry=registry,
                resolver=self.resolver,
                transport=self.transport,
                rate_limiter=self.rate_limiter,
                event_sink=self.event_sink,
            )
        self._emit(
            "external_api.discovery.schema_intake_started",
            {"candidate_id": candidate.candidate_id, "source": candidate.source},
        )
        try:
            response = gateway.execute(
                ExternalAPIRequest(SCHEMA_INTAKE_API_ID, "GET", path),
                global_enabled=True,
                provider_enabled=True,
            )
            proposal = analyze_openapi_schema(candidate, response.data)
        except (ExternalGatewayError, SchemaIntakeError, RecursionError, MemoryError) as exc:
            code = getattr(exc, "code", str(exc))
            self._emit(
                "external_api.discovery.schema_intake_failed",
                {
                    "candidate_id": candidate.candidate_id,
                    "source": candidate.source,
                    "reason": code,
                },
            )
            if isinstance(exc, (RecursionError, MemoryError)):
                raise SchemaIntakeError("schema_complexity_limit_exceeded") from exc
            raise
        self._emit(
            "external_api.discovery.schema_intake_succeeded",
            {
                "candidate_id": candidate.candidate_id,
                "source": candidate.source,
                "detected_version": proposal.detected_openapi_version,
                "operation_count": proposal.operation_count,
                "external_ref_count": proposal.reference_audit.external_refs,
            },
        )
        return proposal
