from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

OIL_VERSION = "1.0"

_KNOWN_CONTEXT = frozenset({"user_language", "session_id", "memory_refs", "extensions"})
_KNOWN_EXECUTION = frozenset({"priority", "complexity", "mode", "extensions"})
_KNOWN_TRACE = frozenset({"planner", "specialists", "memory_used", "extensions"})
_KNOWN_ERROR_BODY = frozenset({"code", "message", "recoverable", "extensions"})


def _merge_extensions(data: dict[str, Any], known: frozenset[str]) -> dict[str, Any]:
    merged = dict(data.get("extensions") or {})
    for key, value in data.items():
        if key not in known:
            merged[key] = value
    return merged


@dataclass(slots=True)
class OILContext:
    """Session and retrieval context carried on an OIL request."""

    user_language: str | None = None
    session_id: str | None = None
    memory_refs: list[Any] = field(default_factory=list)
    extensions: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> OILContext:
        if data is None:
            return cls()
        if not isinstance(data, dict):
            raise ValueError("OILContext must be built from a dict")
        extensions = _merge_extensions(data, _KNOWN_CONTEXT)
        return cls(
            user_language=data.get("user_language"),
            session_id=data.get("session_id"),
            memory_refs=list(data.get("memory_refs") or []),
            extensions=extensions,
        )

    def serialize(self) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        if self.user_language is not None:
            payload["user_language"] = self.user_language
        if self.session_id is not None:
            payload["session_id"] = self.session_id
        if self.memory_refs:
            payload["memory_refs"] = list(self.memory_refs)
        if self.extensions:
            payload["extensions"] = dict(self.extensions)
        return payload

    @classmethod
    def deserialize(cls, data: dict[str, Any] | None) -> OILContext:
        return cls.from_dict(data)


@dataclass(slots=True)
class OILExecution:
    """Execution hints for the runtime (non-binding)."""

    priority: str | None = None
    complexity: str | None = None
    mode: str | None = None
    extensions: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> OILExecution:
        if data is None:
            return cls()
        if not isinstance(data, dict):
            raise ValueError("OILExecution must be built from a dict")
        extensions = _merge_extensions(data, _KNOWN_EXECUTION)
        return cls(
            priority=data.get("priority"),
            complexity=data.get("complexity"),
            mode=data.get("mode"),
            extensions=extensions,
        )

    def serialize(self) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        if self.priority is not None:
            payload["priority"] = self.priority
        if self.complexity is not None:
            payload["complexity"] = self.complexity
        if self.mode is not None:
            payload["mode"] = self.mode
        if self.extensions:
            payload["extensions"] = dict(self.extensions)
        return payload

    @classmethod
    def deserialize(cls, data: dict[str, Any] | None) -> OILExecution:
        return cls.from_dict(data)


@dataclass(slots=True)
class OILTrace:
    """Planner / specialist trace metadata on a result."""

    planner: str | None = None
    specialists: list[str] = field(default_factory=list)
    memory_used: bool | None = None
    extensions: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> OILTrace:
        if data is None:
            return cls()
        if not isinstance(data, dict):
            raise ValueError("OILTrace must be built from a dict")
        extensions = _merge_extensions(data, _KNOWN_TRACE)
        return cls(
            planner=data.get("planner"),
            specialists=list(data.get("specialists") or []),
            memory_used=data.get("memory_used"),
            extensions=extensions,
        )

    def serialize(self) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        if self.planner is not None:
            payload["planner"] = self.planner
        if self.specialists:
            payload["specialists"] = list(self.specialists)
        if self.memory_used is not None:
            payload["memory_used"] = self.memory_used
        if self.extensions:
            payload["extensions"] = dict(self.extensions)
        return payload

    @classmethod
    def deserialize(cls, data: dict[str, Any] | None) -> OILTrace:
        return cls.from_dict(data)


@dataclass(slots=True)
class OILErrorDetails:
    """Structured error body for OILError envelopes."""

    code: str
    message: str
    recoverable: bool = False
    extensions: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> OILErrorDetails:
        if not isinstance(data, dict):
            raise ValueError("OILErrorDetails must be built from a dict")
        code = data.get("code")
        message = data.get("message")
        if not isinstance(code, str) or not str(code).strip():
            raise ValueError("OILErrorDetails.code must be a non-empty string")
        if not isinstance(message, str) or not str(message).strip():
            raise ValueError("OILErrorDetails.message must be a non-empty string")
        extensions = _merge_extensions(data, _KNOWN_ERROR_BODY)
        recoverable = bool(data.get("recoverable", False))
        return cls(code=str(code).strip(), message=str(message).strip(), recoverable=recoverable, extensions=extensions)

    def serialize(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "code": self.code,
            "message": self.message,
            "recoverable": self.recoverable,
        }
        if self.extensions:
            payload["extensions"] = dict(self.extensions)
        return payload

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def deserialize(cls, data: dict[str, Any]) -> OILErrorDetails:
        return cls.from_dict(data)
