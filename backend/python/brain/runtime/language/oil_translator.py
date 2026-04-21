from __future__ import annotations

from typing import Any

from brain.runtime.language.input_interpreter import InputInterpreter
from brain.runtime.language.oil_models import OILProjection
from brain.runtime.language.reasoning_contract import normalize_input_to_oil_request


def _derive_urgency(raw_text: str, constraints: dict[str, Any]) -> str:
    lowered = str(raw_text or "").lower()
    if constraints.get("urgency") == "high":
        return "high"
    if any(term in lowered for term in ("agora", "urgent", "urgente", "asap", "today", "hoje")):
        return "high"
    if any(term in lowered for term in ("quando puder", "later", "depois")):
        return "low"
    return "medium"


def _derive_execution_bias(intent: str, requested_output: str | None, raw_text: str) -> str:
    lowered = str(raw_text or "").lower()
    if intent in {"analyze", "compare", "plan"}:
        return "deep"
    if requested_output in {"json", "table"} or "rápido" in lowered or "quick" in lowered:
        return "cheap"
    return "balanced"


def _derive_memory_relevance(intent: str, raw_text: str, memory_refs: list[Any]) -> str:
    lowered = str(raw_text or "").lower()
    if memory_refs:
        return "high"
    if intent in {"plan", "analyze", "compare"}:
        return "high"
    if any(term in lowered for term in ("lembra", "memory", "contexto", "context")):
        return "high"
    return "low" if intent not in {"ask_question", "summarize"} else "none"


def translate_to_oil_projection(
    text: str,
    *,
    session_id: str | None = None,
    run_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> tuple[Any, OILProjection]:
    oil_request = normalize_input_to_oil_request(
        text,
        session_id=session_id,
        run_id=run_id,
        metadata=metadata,
    )
    projection = OILProjection(
        user_intent=str(oil_request.intent or "ambiguous_request"),
        entities=dict(oil_request.entities or {}),
        constraints=dict(oil_request.constraints or {}),
        desired_output=str(oil_request.requested_output or "answer"),
        urgency=_derive_urgency(text, dict(oil_request.constraints or {})),
        execution_bias=_derive_execution_bias(str(oil_request.intent or ""), oil_request.requested_output, text),
        memory_relevance=_derive_memory_relevance(
            str(oil_request.intent or ""),
            text,
            list(getattr(oil_request.context, "memory_refs", []) or []),
        ),
        metadata={
            "oil_version": getattr(oil_request, "oil_version", ""),
            "language": getattr(oil_request.context, "user_language", None),
        },
    )
    return oil_request, projection


def oil_summary(projection: OILProjection) -> dict[str, Any]:
    return {
        "user_intent": projection.user_intent,
        "desired_output": projection.desired_output,
        "urgency": projection.urgency,
        "execution_bias": projection.execution_bias,
        "memory_relevance": projection.memory_relevance,
        "entity_keys": sorted(list((projection.entities or {}).keys())),
        "constraint_keys": sorted(list((projection.constraints or {}).keys())),
    }


def interpret_to_oil_projection(
    text: str,
    *,
    session_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> OILProjection:
    interpreter = InputInterpreter()
    request = interpreter.interpret(text, session_id=session_id, metadata=metadata)
    projection = OILProjection(
        user_intent=str(request.intent or "ambiguous_request"),
        entities=dict(request.entities or {}),
        constraints=dict(request.constraints or {}),
        desired_output=str(request.requested_output or "answer"),
        urgency=_derive_urgency(text, dict(request.constraints or {})),
        execution_bias=_derive_execution_bias(str(request.intent or ""), request.requested_output, text),
        memory_relevance=_derive_memory_relevance(
            str(request.intent or ""),
            text,
            list(getattr(request.context, "memory_refs", []) or []),
        ),
        metadata={"oil_version": getattr(request, "oil_version", "")},
    )
    return projection
