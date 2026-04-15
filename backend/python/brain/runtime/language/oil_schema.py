from __future__ import annotations

from typing import Any

from brain.runtime.language.types import (
    OILContext,
    OILExecution,
    OILErrorDetails,
    OILTrace,
)

_KNOWN_REQUEST = frozenset(
    {
        "oil_version",
        "intent",
        "entities",
        "constraints",
        "context",
        "requested_output",
        "execution",
        "extensions",
    }
)
_KNOWN_RESULT = frozenset(
    {
        "oil_version",
        "result_type",
        "status",
        "data",
        "confidence",
        "trace",
        "extensions",
    }
)
_KNOWN_ERROR = frozenset({"oil_version", "status", "error", "extensions"})


def _merge_top_extensions(data: dict[str, Any], known: frozenset[str]) -> dict[str, Any]:
    merged = dict(data.get("extensions") or {})
    for key, value in data.items():
        if key not in known:
            merged[key] = value
    return merged


class OILRequest:
    """Structured request envelope for Omni Internal Language (OIL)."""

    __slots__ = (
        "oil_version",
        "intent",
        "entities",
        "constraints",
        "context",
        "requested_output",
        "execution",
        "extensions",
    )

    def __init__(
        self,
        *,
        oil_version: str,
        intent: str,
        entities: dict[str, Any] | None = None,
        constraints: dict[str, Any] | None = None,
        context: OILContext | None = None,
        requested_output: str | None = None,
        execution: OILExecution | None = None,
        extensions: dict[str, Any] | None = None,
    ) -> None:
        if not isinstance(oil_version, str) or not oil_version.strip():
            raise ValueError("oil_version must be a non-empty string")
        if not isinstance(intent, str) or not intent.strip():
            raise ValueError("intent must be a non-empty string")
        self.oil_version = oil_version.strip()
        self.intent = intent.strip()
        self.entities = dict(entities or {})
        self.constraints = dict(constraints or {})
        self.context = context if context is not None else OILContext()
        self.requested_output = requested_output
        self.execution = execution if execution is not None else OILExecution()
        self.extensions = dict(extensions or {})

    def serialize(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "oil_version": self.oil_version,
            "intent": self.intent,
            "entities": dict(self.entities),
            "constraints": dict(self.constraints),
            "context": self.context.serialize(),
        }
        if self.requested_output is not None:
            payload["requested_output"] = self.requested_output
        exec_payload = self.execution.serialize()
        if exec_payload:
            payload["execution"] = exec_payload
        if self.extensions:
            payload["extensions"] = dict(self.extensions)
        return payload

    @classmethod
    def deserialize(cls, data: dict[str, Any]) -> OILRequest:
        if not isinstance(data, dict):
            raise ValueError("OILRequest.deserialize requires a dict")
        oil_version = data.get("oil_version")
        intent = data.get("intent")
        if not isinstance(oil_version, str) or not oil_version.strip():
            raise ValueError("oil_version must be a non-empty string")
        if not isinstance(intent, str) or not intent.strip():
            raise ValueError("intent must be a non-empty string")
        entities = data.get("entities")
        if entities is not None and not isinstance(entities, dict):
            raise ValueError("entities must be a dict when present")
        constraints = data.get("constraints")
        if constraints is not None and not isinstance(constraints, dict):
            raise ValueError("constraints must be a dict when present")
        extensions = _merge_top_extensions(data, _KNOWN_REQUEST)
        context_raw = data.get("context")
        if context_raw is not None and not isinstance(context_raw, dict):
            raise ValueError("context must be a dict when present")
        execution_raw = data.get("execution")
        if execution_raw is not None and not isinstance(execution_raw, dict):
            raise ValueError("execution must be a dict when present")
        requested = data.get("requested_output")
        if requested is not None and not isinstance(requested, str):
            raise ValueError("requested_output must be a string when present")
        return cls(
            oil_version=str(oil_version).strip(),
            intent=str(intent).strip(),
            entities=dict(entities or {}),
            constraints=dict(constraints or {}),
            context=OILContext.from_dict(context_raw),
            requested_output=requested if requested is None else str(requested),
            execution=OILExecution.from_dict(execution_raw),
            extensions=extensions,
        )


class OILResult:
    """Structured success / outcome envelope for OIL."""

    __slots__ = ("oil_version", "result_type", "status", "data", "confidence", "trace", "extensions")

    def __init__(
        self,
        *,
        oil_version: str,
        result_type: str,
        status: str,
        data: dict[str, Any] | None = None,
        confidence: float | None = None,
        trace: OILTrace | None = None,
        extensions: dict[str, Any] | None = None,
    ) -> None:
        if not isinstance(oil_version, str) or not oil_version.strip():
            raise ValueError("oil_version must be a non-empty string")
        if not isinstance(result_type, str) or not result_type.strip():
            raise ValueError("result_type must be a non-empty string")
        if not isinstance(status, str) or not status.strip():
            raise ValueError("status must be a non-empty string")
        self.oil_version = oil_version.strip()
        self.result_type = result_type.strip()
        self.status = status.strip()
        self.data = dict(data or {})
        self.confidence = confidence
        self.trace = trace if trace is not None else OILTrace()
        self.extensions = dict(extensions or {})

    def serialize(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "oil_version": self.oil_version,
            "result_type": self.result_type,
            "status": self.status,
            "data": dict(self.data),
        }
        if self.confidence is not None:
            payload["confidence"] = self.confidence
        trace_payload = self.trace.serialize()
        if trace_payload:
            payload["trace"] = trace_payload
        if self.extensions:
            payload["extensions"] = dict(self.extensions)
        return payload

    @classmethod
    def deserialize(cls, data: dict[str, Any]) -> OILResult:
        if not isinstance(data, dict):
            raise ValueError("OILResult.deserialize requires a dict")
        oil_version = data.get("oil_version")
        result_type = data.get("result_type")
        status = data.get("status")
        if not isinstance(oil_version, str) or not oil_version.strip():
            raise ValueError("oil_version must be a non-empty string")
        if not isinstance(result_type, str) or not result_type.strip():
            raise ValueError("result_type must be a non-empty string")
        if not isinstance(status, str) or not status.strip():
            raise ValueError("status must be a non-empty string")
        raw_data = data.get("data")
        if raw_data is None:
            raw_data = {}
        if not isinstance(raw_data, dict):
            raise ValueError("data must be a dict")
        confidence = data.get("confidence")
        if confidence is not None and not isinstance(confidence, (int, float)):
            raise ValueError("confidence must be a number when present")
        trace_raw = data.get("trace")
        if trace_raw is not None and not isinstance(trace_raw, dict):
            raise ValueError("trace must be a dict when present")
        extensions = _merge_top_extensions(data, _KNOWN_RESULT)
        return cls(
            oil_version=str(oil_version).strip(),
            result_type=str(result_type).strip(),
            status=str(status).strip(),
            data=dict(raw_data),
            confidence=float(confidence) if confidence is not None else None,
            trace=OILTrace.from_dict(trace_raw),
            extensions=extensions,
        )


class OILError:
    """Structured error envelope for OIL."""

    __slots__ = ("oil_version", "status", "error", "extensions")

    def __init__(
        self,
        *,
        oil_version: str,
        error: OILErrorDetails,
        status: str = "error",
        extensions: dict[str, Any] | None = None,
    ) -> None:
        if not isinstance(oil_version, str) or not oil_version.strip():
            raise ValueError("oil_version must be a non-empty string")
        if not isinstance(status, str) or not status.strip():
            raise ValueError("status must be a non-empty string")
        self.oil_version = oil_version.strip()
        self.status = status.strip()
        self.error = error
        self.extensions = dict(extensions or {})

    def serialize(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "oil_version": self.oil_version,
            "status": self.status,
            "error": self.error.serialize(),
        }
        if self.extensions:
            payload["extensions"] = dict(self.extensions)
        return payload

    @classmethod
    def deserialize(cls, data: dict[str, Any]) -> OILError:
        if not isinstance(data, dict):
            raise ValueError("OILError.deserialize requires a dict")
        oil_version = data.get("oil_version")
        if not isinstance(oil_version, str) or not oil_version.strip():
            raise ValueError("oil_version must be a non-empty string")
        status = data.get("status", "error")
        if not isinstance(status, str) or not status.strip():
            raise ValueError("status must be a non-empty string")
        err = data.get("error")
        if not isinstance(err, dict):
            raise ValueError("error must be a dict")
        extensions = _merge_top_extensions(data, _KNOWN_ERROR)
        return cls(
            oil_version=str(oil_version).strip(),
            status=str(status).strip(),
            error=OILErrorDetails.from_dict(err),
            extensions=extensions,
        )
