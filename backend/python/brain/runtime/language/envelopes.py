from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


_KNOWN_ROUTING = frozenset(
    {"source", "destination", "reply_channel", "capability_path", "extensions"}
)
_KNOWN_TRACE = frozenset(
    {"correlation_id", "trace_id", "span_id", "parent_span_id", "hop", "extensions"}
)
_KNOWN_ENVELOPE = frozenset(
    {
        "protocol_version",
        "message_kind",
        "oil",
        "routing",
        "trace",
        "created_at",
        "extensions",
    }
)

_KNOWN_RUNTIME_PROTOCOL = frozenset(
    {
        "oil_version",
        "protocol_type",
        "source_component",
        "target_component",
        "session_id",
        "run_id",
        "trace_id",
        "timestamp",
        "intent",
        "payload",
        "routing",
        "extensions",
    }
)


def _merge_extensions(data: dict[str, Any], known: frozenset[str]) -> dict[str, Any]:
    merged = dict(data.get("extensions") or {})
    for key, value in data.items():
        if key not in known:
            merged[key] = value
    return merged


@dataclass(slots=True)
class OILRoutingMetadata:
    """Where an OIL message is coming from and where it should go next."""

    source: str
    destination: str
    reply_channel: str | None = None
    capability_path: str | None = None
    extensions: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> OILRoutingMetadata:
        if data is None:
            return cls(source="unknown", destination="unknown")
        if not isinstance(data, dict):
            raise ValueError("OILRoutingMetadata expects a dict")
        extensions = _merge_extensions(data, _KNOWN_ROUTING)
        source = data.get("source")
        destination = data.get("destination")
        if not isinstance(source, str) or not source.strip():
            raise ValueError("routing.source must be a non-empty string")
        if not isinstance(destination, str) or not destination.strip():
            raise ValueError("routing.destination must be a non-empty string")
        return cls(
            source=source.strip(),
            destination=destination.strip(),
            reply_channel=str(data["reply_channel"]).strip() if data.get("reply_channel") else None,
            capability_path=str(data["capability_path"]).strip() if data.get("capability_path") else None,
            extensions=extensions,
        )

    def serialize(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "source": self.source,
            "destination": self.destination,
        }
        if self.reply_channel:
            payload["reply_channel"] = self.reply_channel
        if self.capability_path:
            payload["capability_path"] = self.capability_path
        if self.extensions:
            payload["extensions"] = dict(self.extensions)
        return payload

    @classmethod
    def deserialize(cls, data: dict[str, Any] | None) -> OILRoutingMetadata:
        return cls.from_dict(data)


@dataclass(slots=True)
class OILTraceMetadata:
    """Correlation and span metadata for runtime handoffs (JSON-safe)."""

    correlation_id: str
    trace_id: str
    span_id: str
    parent_span_id: str | None = None
    hop: int = 0
    extensions: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> OILTraceMetadata:
        if data is None:
            raise ValueError("OILTraceMetadata requires a dict")
        if not isinstance(data, dict):
            raise ValueError("OILTraceMetadata expects a dict")
        extensions = _merge_extensions(data, _KNOWN_TRACE)
        correlation_id = data.get("correlation_id")
        trace_id = data.get("trace_id")
        span_id = data.get("span_id")
        for label, raw in (
            ("correlation_id", correlation_id),
            ("trace_id", trace_id),
            ("span_id", span_id),
        ):
            if not isinstance(raw, str) or not raw.strip():
                raise ValueError(f"trace.{label} must be a non-empty string")
        hop = data.get("hop", 0)
        if not isinstance(hop, int) or hop < 0:
            raise ValueError("trace.hop must be a non-negative int")
        parent = data.get("parent_span_id")
        if parent is not None and (not isinstance(parent, str) or not parent.strip()):
            raise ValueError("trace.parent_span_id must be a non-empty string when present")
        return cls(
            correlation_id=str(correlation_id).strip(),
            trace_id=str(trace_id).strip(),
            span_id=str(span_id).strip(),
            parent_span_id=str(parent).strip() if parent else None,
            hop=int(hop),
            extensions=extensions,
        )

    def serialize(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "correlation_id": self.correlation_id,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "hop": self.hop,
        }
        if self.parent_span_id:
            payload["parent_span_id"] = self.parent_span_id
        if self.extensions:
            payload["extensions"] = dict(self.extensions)
        return payload

    @classmethod
    def deserialize(cls, data: dict[str, Any] | None) -> OILTraceMetadata:
        return cls.from_dict(data)


@dataclass(slots=True)
class OILCommunicationEnvelope:
    """Transport wrapper for OIL payloads between runtime components (Phase 30.3)."""

    protocol_version: str
    message_kind: str
    oil: dict[str, Any]
    routing: OILRoutingMetadata
    trace: OILTraceMetadata
    created_at: str | None = None
    extensions: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> OILCommunicationEnvelope:
        if not isinstance(data, dict):
            raise ValueError("OILCommunicationEnvelope expects a dict")
        extensions = _merge_extensions(data, _KNOWN_ENVELOPE)
        protocol_version = data.get("protocol_version")
        message_kind = data.get("message_kind")
        oil = data.get("oil")
        if not isinstance(protocol_version, str) or not protocol_version.strip():
            raise ValueError("protocol_version must be a non-empty string")
        if not isinstance(message_kind, str) or not message_kind.strip():
            raise ValueError("message_kind must be a non-empty string")
        if message_kind not in {"oil_request", "oil_result", "oil_error"}:
            raise ValueError("message_kind must be oil_request, oil_result, or oil_error")
        if not isinstance(oil, dict):
            raise ValueError("oil must be a dict")
        created_at = data.get("created_at")
        if created_at is not None and (not isinstance(created_at, str) or not created_at.strip()):
            raise ValueError("created_at must be a non-empty string when present")
        return cls(
            protocol_version=str(protocol_version).strip(),
            message_kind=str(message_kind).strip(),
            oil=dict(oil),
            routing=OILRoutingMetadata.from_dict(data.get("routing")),
            trace=OILTraceMetadata.from_dict(data.get("trace")),
            created_at=str(created_at).strip() if created_at else None,
            extensions=extensions,
        )

    def serialize(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "protocol_version": self.protocol_version,
            "message_kind": self.message_kind,
            "oil": dict(self.oil),
            "routing": self.routing.serialize(),
            "trace": self.trace.serialize(),
            "created_at": self.created_at or utc_now_iso(),
        }
        if self.extensions:
            payload["extensions"] = dict(self.extensions)
        return payload

    @classmethod
    def deserialize(cls, data: dict[str, Any]) -> OILCommunicationEnvelope:
        return cls.from_dict(data)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class OILRuntimeProtocolEnvelope:
    """OIL-compatible internal runtime envelope (Phase 30.3 — component handoffs)."""

    oil_version: str
    protocol_type: str
    source_component: str
    target_component: str
    trace_id: str
    timestamp: str
    payload: dict[str, Any]
    routing: dict[str, Any] = field(default_factory=dict)
    session_id: str | None = None
    run_id: str | None = None
    intent: str | None = None
    extensions: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> OILRuntimeProtocolEnvelope:
        if not isinstance(data, dict):
            raise ValueError("OILRuntimeProtocolEnvelope expects a dict")
        extensions = _merge_extensions(data, _KNOWN_RUNTIME_PROTOCOL)
        oil_version = data.get("oil_version")
        protocol_type = data.get("protocol_type")
        source_component = data.get("source_component")
        target_component = data.get("target_component")
        trace_id = data.get("trace_id")
        timestamp = data.get("timestamp")
        payload = data.get("payload")
        routing = data.get("routing")
        for label, raw in (
            ("oil_version", oil_version),
            ("protocol_type", protocol_type),
            ("source_component", source_component),
            ("target_component", target_component),
            ("trace_id", trace_id),
            ("timestamp", timestamp),
        ):
            if not isinstance(raw, str) or not raw.strip():
                raise ValueError(f"{label} must be a non-empty string")
        if payload is None:
            payload = {}
        if not isinstance(payload, dict):
            raise ValueError("payload must be a dict")
        if routing is None:
            routing = {}
        if not isinstance(routing, dict):
            raise ValueError("routing must be a dict when present")
        session_id = data.get("session_id")
        run_id = data.get("run_id")
        intent = data.get("intent")
        return cls(
            oil_version=str(oil_version).strip(),
            protocol_type=str(protocol_type).strip(),
            source_component=str(source_component).strip(),
            target_component=str(target_component).strip(),
            trace_id=str(trace_id).strip(),
            timestamp=str(timestamp).strip(),
            payload=dict(payload),
            routing=dict(routing),
            session_id=str(session_id).strip() if session_id else None,
            run_id=str(run_id).strip() if run_id else None,
            intent=str(intent).strip() if intent else None,
            extensions=extensions,
        )

    def serialize(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "oil_version": self.oil_version,
            "protocol_type": self.protocol_type,
            "source_component": self.source_component,
            "target_component": self.target_component,
            "session_id": self.session_id,
            "run_id": self.run_id,
            "trace_id": self.trace_id,
            "timestamp": self.timestamp,
            "intent": self.intent,
            "payload": dict(self.payload),
            "routing": dict(self.routing),
        }
        if self.extensions:
            out["extensions"] = dict(self.extensions)
        return out

    @classmethod
    def deserialize(cls, data: dict[str, Any]) -> OILRuntimeProtocolEnvelope:
        return cls.from_dict(data)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)
