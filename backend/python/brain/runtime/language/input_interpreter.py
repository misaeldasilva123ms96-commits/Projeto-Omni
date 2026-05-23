from __future__ import annotations

from dataclasses import asdict
from typing import Any

from brain.runtime.language.intent_registry import FALLBACK_INTENT, INTENTS
from brain.runtime.language.normalizers import (
    IntentCandidate,
    extract_constraints,
    extract_entities,
    extract_requested_output,
    infer_language_hint,
    normalize_whitespace,
)
from brain.runtime.language.oil_schema import OILRequest
from brain.runtime.language.types import OILContext, OILExecution, OIL_VERSION


DEFAULT_EXECUTION = OILExecution(priority="normal", complexity="light", mode="interactive")


def _bounded(value: float) -> float:
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return float(value)


def _detect_intent(text: str) -> tuple[str, float, list[IntentCandidate]]:
    cleaned = normalize_whitespace(text).lower()
    if not cleaned:
        return (FALLBACK_INTENT, 0.0, [IntentCandidate(intent=FALLBACK_INTENT, score=0.0, matched_signals=0)])

    candidates: list[IntentCandidate] = []
    for rule in INTENTS:
        matched = 0
        for pattern in rule.patterns:
            if pattern.search(cleaned):
                matched += 1
        if matched:
            score = rule.base_confidence + (matched - 1) * 0.07
            candidates.append(IntentCandidate(intent=rule.intent, score=_bounded(score), matched_signals=matched))

    if not candidates:
        # Default to ask_question when input looks interrogative; otherwise fallback.
        if cleaned.endswith("?"):
            return ("ask_question", 0.5, [IntentCandidate(intent="ask_question", score=0.5, matched_signals=1)])
        return (FALLBACK_INTENT, 0.35, [IntentCandidate(intent=FALLBACK_INTENT, score=0.35, matched_signals=0)])

    candidates.sort(key=lambda c: c.score, reverse=True)
    best = candidates[0]

    # Penalize ambiguous top-2 ties.
    if len(candidates) > 1 and abs(candidates[0].score - candidates[1].score) < 0.08:
        best = IntentCandidate(intent=best.intent, score=_bounded(best.score - 0.15), matched_signals=best.matched_signals)
        candidates[0] = best

    return (best.intent, best.score, candidates[:5])


class InputInterpreter:
    """Deterministic-first interpreter from user text -> OILRequest (Phase 30.2)."""

    def interpret(
        self,
        text: str,
        *,
        session_id: str | None = None,
        user_language: str | None = None,
        memory_refs: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> OILRequest:
        cleaned = normalize_whitespace(text)
        intent, confidence, candidates = _detect_intent(cleaned)

        entities = extract_entities(cleaned)
        constraints = extract_constraints(cleaned)
        requested_output = extract_requested_output(cleaned, intent=intent)

        lang_hint = infer_language_hint(cleaned, user_language)
        context = OILContext(
            user_language=lang_hint,
            session_id=session_id,
            memory_refs=list(memory_refs or []),
            extensions=dict(metadata or {}),
        )

        extensions: dict[str, Any] = {
            "confidence": _bounded(confidence),
            "intent_candidates": [asdict(c) for c in candidates],
        }
        if not cleaned:
            extensions["reason"] = "empty_input"

        return OILRequest(
            oil_version=OIL_VERSION,
            intent=intent,
            entities=entities,
            constraints=constraints,
            context=context,
            requested_output=requested_output,
            execution=DEFAULT_EXECUTION,
            extensions=extensions,
        )


def interpret_input(
    text: str,
    *,
    session_id: str | None = None,
    user_language: str | None = None,
    memory_refs: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> OILRequest:
    return InputInterpreter().interpret(
        text,
        session_id=session_id,
        user_language=user_language,
        memory_refs=memory_refs,
        metadata=metadata,
    )

