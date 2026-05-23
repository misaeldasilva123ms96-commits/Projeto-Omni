from __future__ import annotations

from dataclasses import replace
from typing import Any
from uuid import uuid4

from brain.runtime.language.envelopes import (
    OILCommunicationEnvelope,
    OILRuntimeProtocolEnvelope,
    OILRoutingMetadata,
    OILTraceMetadata,
    utc_now_iso,
)
from brain.runtime.language.oil_schema import OILError, OILRequest, OILResult
from brain.runtime.language.types import OIL_VERSION, OILContext


OIL_PROTOCOL_VERSION = "1.0"


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid4()}"


class OILHandoffProtocol:
    """Deterministic construction and relay of OIL communication envelopes."""

    @staticmethod
    def wrap_request(
        request: OILRequest,
        *,
        source: str,
        destination: str,
        correlation_id: str | None = None,
        trace_id: str | None = None,
        capability_path: str | None = None,
        reply_channel: str | None = None,
        extensions: dict[str, Any] | None = None,
    ) -> OILCommunicationEnvelope:
        cid = correlation_id or new_id("corr")
        tid = trace_id or cid
        span = new_id("span")
        return OILCommunicationEnvelope(
            protocol_version=OIL_PROTOCOL_VERSION,
            message_kind="oil_request",
            oil=request.serialize(),
            routing=OILRoutingMetadata(
                source=source,
                destination=destination,
                reply_channel=reply_channel,
                capability_path=capability_path,
            ),
            trace=OILTraceMetadata(
                correlation_id=cid,
                trace_id=tid,
                span_id=span,
                parent_span_id=None,
                hop=0,
            ),
            created_at=utc_now_iso(),
            extensions=dict(extensions or {}),
        )

    @staticmethod
    def wrap_result(
        result: OILResult,
        *,
        source: str,
        destination: str,
        correlation_id: str,
        trace_id: str,
        parent_span_id: str,
        hop: int,
        capability_path: str | None = None,
        extensions: dict[str, Any] | None = None,
    ) -> OILCommunicationEnvelope:
        span = new_id("span")
        return OILCommunicationEnvelope(
            protocol_version=OIL_PROTOCOL_VERSION,
            message_kind="oil_result",
            oil=result.serialize(),
            routing=OILRoutingMetadata(
                source=source,
                destination=destination,
                capability_path=capability_path,
            ),
            trace=OILTraceMetadata(
                correlation_id=correlation_id,
                trace_id=trace_id,
                span_id=span,
                parent_span_id=parent_span_id,
                hop=max(0, int(hop)),
            ),
            created_at=utc_now_iso(),
            extensions=dict(extensions or {}),
        )

    @staticmethod
    def wrap_error(
        error: OILError,
        *,
        source: str,
        destination: str,
        correlation_id: str,
        trace_id: str,
        parent_span_id: str,
        hop: int,
        extensions: dict[str, Any] | None = None,
    ) -> OILCommunicationEnvelope:
        span = new_id("span")
        return OILCommunicationEnvelope(
            protocol_version=OIL_PROTOCOL_VERSION,
            message_kind="oil_error",
            oil=error.serialize(),
            routing=OILRoutingMetadata(source=source, destination=destination),
            trace=OILTraceMetadata(
                correlation_id=correlation_id,
                trace_id=trace_id,
                span_id=span,
                parent_span_id=parent_span_id,
                hop=max(0, int(hop)),
            ),
            created_at=utc_now_iso(),
            extensions=dict(extensions or {}),
        )

    @staticmethod
    def relay(
        envelope: OILCommunicationEnvelope,
        *,
        new_source: str | None = None,
        new_destination: str,
        capability_path: str | None = None,
    ) -> OILCommunicationEnvelope:
        src = new_source if new_source else envelope.routing.destination
        span = new_id("span")
        trace = replace(
            envelope.trace,
            span_id=span,
            parent_span_id=envelope.trace.span_id,
            hop=envelope.trace.hop + 1,
        )
        routing = replace(
            envelope.routing,
            source=src,
            destination=new_destination,
            capability_path=capability_path if capability_path is not None else envelope.routing.capability_path,
        )
        return OILCommunicationEnvelope(
            protocol_version=envelope.protocol_version,
            message_kind=envelope.message_kind,
            oil=dict(envelope.oil),
            routing=routing,
            trace=trace,
            created_at=utc_now_iso(),
            extensions=dict(envelope.extensions),
        )

    @staticmethod
    def unwrap_request(envelope: OILCommunicationEnvelope) -> OILRequest:
        if envelope.message_kind != "oil_request":
            raise ValueError("envelope is not an oil_request")
        return OILRequest.deserialize(envelope.oil)

    @staticmethod
    def unwrap_result(envelope: OILCommunicationEnvelope) -> OILResult:
        if envelope.message_kind != "oil_result":
            raise ValueError("envelope is not an oil_result")
        return OILResult.deserialize(envelope.oil)

    @staticmethod
    def unwrap_error(envelope: OILCommunicationEnvelope) -> OILError:
        if envelope.message_kind != "oil_error":
            raise ValueError("envelope is not an oil_error")
        return OILError.deserialize(envelope.oil)


def _runtime_proto(
    *,
    protocol_type: str,
    source_component: str,
    target_component: str,
    session_id: str | None,
    run_id: str | None,
    trace_id: str,
    intent: str | None,
    payload: dict[str, Any] | None,
    routing: dict[str, Any] | None,
    extensions: dict[str, Any] | None,
    oil_version: str | None,
) -> OILRuntimeProtocolEnvelope:
    return OILRuntimeProtocolEnvelope(
        oil_version=str(oil_version or OIL_VERSION).strip(),
        protocol_type=str(protocol_type).strip(),
        source_component=str(source_component).strip(),
        target_component=str(target_component).strip(),
        trace_id=str(trace_id).strip(),
        timestamp=utc_now_iso(),
        intent=str(intent).strip() if intent else None,
        payload=dict(payload or {}),
        routing=dict(routing or {}),
        session_id=str(session_id).strip() if session_id else None,
        run_id=str(run_id).strip() if run_id else None,
        extensions=dict(extensions or {}),
    )


def build_planner_request(
    *,
    source_component: str,
    target_component: str,
    session_id: str | None,
    run_id: str | None,
    trace_id: str,
    intent: str | None,
    payload: dict[str, Any] | None = None,
    routing: dict[str, Any] | None = None,
    extensions: dict[str, Any] | None = None,
    oil_version: str | None = None,
) -> OILRuntimeProtocolEnvelope:
    return _runtime_proto(
        protocol_type="planner_request",
        source_component=source_component,
        target_component=target_component,
        session_id=session_id,
        run_id=run_id,
        trace_id=trace_id,
        intent=intent,
        payload=payload,
        routing=routing,
        extensions=extensions,
        oil_version=oil_version,
    )


def build_specialist_request(
    *,
    source_component: str,
    target_component: str,
    session_id: str | None,
    run_id: str | None,
    trace_id: str,
    intent: str | None,
    payload: dict[str, Any] | None = None,
    routing: dict[str, Any] | None = None,
    extensions: dict[str, Any] | None = None,
    oil_version: str | None = None,
) -> OILRuntimeProtocolEnvelope:
    return _runtime_proto(
        protocol_type="specialist_request",
        source_component=source_component,
        target_component=target_component,
        session_id=session_id,
        run_id=run_id,
        trace_id=trace_id,
        intent=intent,
        payload=payload,
        routing=routing,
        extensions=extensions,
        oil_version=oil_version,
    )


def build_memory_lookup(
    *,
    source_component: str,
    target_component: str,
    session_id: str | None,
    run_id: str | None,
    trace_id: str,
    intent: str | None,
    payload: dict[str, Any] | None = None,
    routing: dict[str, Any] | None = None,
    extensions: dict[str, Any] | None = None,
    oil_version: str | None = None,
) -> OILRuntimeProtocolEnvelope:
    return _runtime_proto(
        protocol_type="memory_lookup",
        source_component=source_component,
        target_component=target_component,
        session_id=session_id,
        run_id=run_id,
        trace_id=trace_id,
        intent=intent,
        payload=payload,
        routing=routing,
        extensions=extensions,
        oil_version=oil_version,
    )


def build_tool_execution(
    *,
    source_component: str,
    target_component: str,
    session_id: str | None,
    run_id: str | None,
    trace_id: str,
    intent: str | None,
    payload: dict[str, Any] | None = None,
    routing: dict[str, Any] | None = None,
    extensions: dict[str, Any] | None = None,
    oil_version: str | None = None,
) -> OILRuntimeProtocolEnvelope:
    return _runtime_proto(
        protocol_type="tool_execution",
        source_component=source_component,
        target_component=target_component,
        session_id=session_id,
        run_id=run_id,
        trace_id=trace_id,
        intent=intent,
        payload=payload,
        routing=routing,
        extensions=extensions,
        oil_version=oil_version,
    )


def build_planner_result(
    *,
    source_component: str,
    target_component: str,
    session_id: str | None,
    run_id: str | None,
    trace_id: str,
    intent: str | None,
    payload: dict[str, Any] | None = None,
    routing: dict[str, Any] | None = None,
    extensions: dict[str, Any] | None = None,
    oil_version: str | None = None,
) -> OILRuntimeProtocolEnvelope:
    return _runtime_proto(
        protocol_type="planner_result",
        source_component=source_component,
        target_component=target_component,
        session_id=session_id,
        run_id=run_id,
        trace_id=trace_id,
        intent=intent,
        payload=payload,
        routing=routing,
        extensions=extensions,
        oil_version=oil_version,
    )


def build_specialist_result(
    *,
    source_component: str,
    target_component: str,
    session_id: str | None,
    run_id: str | None,
    trace_id: str,
    intent: str | None,
    payload: dict[str, Any] | None = None,
    routing: dict[str, Any] | None = None,
    extensions: dict[str, Any] | None = None,
    oil_version: str | None = None,
) -> OILRuntimeProtocolEnvelope:
    return _runtime_proto(
        protocol_type="specialist_result",
        source_component=source_component,
        target_component=target_component,
        session_id=session_id,
        run_id=run_id,
        trace_id=trace_id,
        intent=intent,
        payload=payload,
        routing=routing,
        extensions=extensions,
        oil_version=oil_version,
    )


def build_memory_result(
    *,
    source_component: str,
    target_component: str,
    session_id: str | None,
    run_id: str | None,
    trace_id: str,
    intent: str | None,
    payload: dict[str, Any] | None = None,
    routing: dict[str, Any] | None = None,
    extensions: dict[str, Any] | None = None,
    oil_version: str | None = None,
) -> OILRuntimeProtocolEnvelope:
    return _runtime_proto(
        protocol_type="memory_result",
        source_component=source_component,
        target_component=target_component,
        session_id=session_id,
        run_id=run_id,
        trace_id=trace_id,
        intent=intent,
        payload=payload,
        routing=routing,
        extensions=extensions,
        oil_version=oil_version,
    )


def build_tool_result(
    *,
    source_component: str,
    target_component: str,
    session_id: str | None,
    run_id: str | None,
    trace_id: str,
    intent: str | None,
    payload: dict[str, Any] | None = None,
    routing: dict[str, Any] | None = None,
    extensions: dict[str, Any] | None = None,
    oil_version: str | None = None,
) -> OILRuntimeProtocolEnvelope:
    return _runtime_proto(
        protocol_type="tool_result",
        source_component=source_component,
        target_component=target_component,
        session_id=session_id,
        run_id=run_id,
        trace_id=trace_id,
        intent=intent,
        payload=payload,
        routing=routing,
        extensions=extensions,
        oil_version=oil_version,
    )


def runtime_protocol_to_legacy_dict(proto: OILRuntimeProtocolEnvelope) -> dict[str, Any]:
    """Flatten runtime protocol into a legacy-friendly dict (additive fields, no breaking keys)."""
    return {
        "type": proto.protocol_type,
        "from": proto.source_component,
        "to": proto.target_component,
        "session": proto.session_id,
        "run": proto.run_id,
        "trace": proto.trace_id,
        "intent": proto.intent,
        "body": dict(proto.payload),
        "routing": dict(proto.routing),
        "_oil_version": proto.oil_version,
        "_timestamp": proto.timestamp,
    }


def runtime_protocol_from_legacy_dict(data: dict[str, Any]) -> OILRuntimeProtocolEnvelope:
    """Rebuild runtime protocol from canonical serialization or legacy shim dict."""
    if not isinstance(data, dict):
        raise ValueError("runtime_protocol_from_legacy_dict requires a dict")
    if isinstance(data.get("_oil_runtime_protocol"), dict):
        return OILRuntimeProtocolEnvelope.from_dict(data["_oil_runtime_protocol"])
    if "oil_version" in data and "protocol_type" in data:
        return OILRuntimeProtocolEnvelope.from_dict(data)
    return OILRuntimeProtocolEnvelope.from_dict(
        {
            "oil_version": str(data.get("_oil_version") or OIL_VERSION),
            "protocol_type": str(data.get("type") or data.get("protocol_type") or ""),
            "source_component": str(data.get("from") or data.get("source_component") or ""),
            "target_component": str(data.get("to") or data.get("target_component") or ""),
            "session_id": data.get("session") or data.get("session_id"),
            "run_id": data.get("run") or data.get("run_id"),
            "trace_id": str(data.get("trace") or data.get("trace_id") or ""),
            "timestamp": str(data.get("_timestamp") or utc_now_iso()),
            "intent": data.get("intent"),
            "payload": dict(data.get("body") or data.get("payload") or {}),
            "routing": dict(data.get("routing") or {}),
            "extensions": dict(data.get("extensions") or {}),
        }
    )


def runtime_protocol_to_oil_request(proto: OILRuntimeProtocolEnvelope) -> OILRequest:
    """Map internal runtime protocol into a Phase 30.1 OILRequest (OIL-compatible)."""
    body = dict(proto.payload)
    entities = dict(body.get("entities") or {})
    constraints = dict(body.get("constraints") or {})
    if not entities and body:
        entities = {"runtime_payload": body}
    ctx_ext: dict[str, Any] = {"protocol_type": proto.protocol_type, "routing": dict(proto.routing)}
    if proto.run_id:
        ctx_ext["run_id"] = proto.run_id
    return OILRequest(
        oil_version=proto.oil_version,
        intent=str(proto.intent or "ambiguous_request").strip(),
        entities=entities,
        constraints=constraints,
        context=OILContext(session_id=proto.session_id, extensions=ctx_ext),
        requested_output=body.get("requested_output") if isinstance(body.get("requested_output"), str) else None,
        extensions={"trace_id": proto.trace_id, "timestamp": proto.timestamp, **dict(proto.extensions)},
    )


def runtime_protocol_to_communication_envelope(
    proto: OILRuntimeProtocolEnvelope,
    *,
    correlation_id: str | None = None,
) -> OILCommunicationEnvelope:
    """Bridge runtime protocol -> transport envelope wrapping an OILRequest."""
    req = runtime_protocol_to_oil_request(proto)
    return OILHandoffProtocol.wrap_request(
        req,
        source=proto.source_component,
        destination=proto.target_component,
        correlation_id=correlation_id or proto.trace_id,
        extensions={"runtime_protocol_type": proto.protocol_type},
    )
