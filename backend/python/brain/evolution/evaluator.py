from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha1
from typing import Any


def _tokenize(text: str) -> list[str]:
    return [token for token in "".join(ch.lower() if ch.isalnum() or ch.isspace() else " " for ch in text).split() if token]


def _jaccard_similarity(left: str, right: str) -> float:
    left_tokens = set(_tokenize(left))
    right_tokens = set(_tokenize(right))
    if not left_tokens or not right_tokens:
        return 0.0
    intersection = len(left_tokens & right_tokens)
    union = len(left_tokens | right_tokens)
    if union == 0:
        return 0.0
    return round(intersection / union, 3)


def _contains_keywords(message: str, response: str) -> float:
    message_tokens = _tokenize(message)
    if not message_tokens:
        return 0.5
    key_tokens = [token for token in message_tokens if len(token) > 3][:6]
    if not key_tokens:
        return 0.6
    hits = sum(1 for token in key_tokens if token in _tokenize(response))
    return round(min(1.0, hits / max(1, len(key_tokens))), 3)


def _history_coherence(response: str, history: list[dict[str, str]]) -> float:
    if not history:
        return 0.75
    recent_context = " ".join(str(item.get("content", "")) for item in history[-4:] if isinstance(item, dict))
    similarity = _jaccard_similarity(recent_context, response)
    return round(min(1.0, 0.55 + similarity * 0.5), 3)


def _completeness(message: str, response: str) -> float:
    message_tokens = set(_tokenize(message))
    response_tokens = set(_tokenize(response))
    if not message_tokens:
        return 0.6
    coverage = len(message_tokens & response_tokens) / max(1, len(message_tokens))
    if "?" in message and len(response_tokens) >= 8:
        coverage += 0.15
    if any(term in message.lower() for term in ("como", "por que", "o que", "devo")) and len(response.split()) >= 12:
        coverage += 0.1
    return round(min(1.0, max(0.0, coverage)), 3)


def _efficiency(message: str, response: str) -> tuple[float, list[str]]:
    flags: list[str] = []
    message_words = len(_tokenize(message))
    response_words = len(_tokenize(response))
    if response_words == 0:
        return 0.0, ["empty_response"]

    ideal_min = max(6, message_words * 2)
    ideal_max = max(18, message_words * 8)
    if response_words < ideal_min:
        flags.append("too_short")
        score = 0.45
    elif response_words > ideal_max:
        flags.append("too_long")
        score = 0.55
    else:
        score = 0.9
    return round(score, 3), flags


@dataclass
class EvaluationResult:
    session_id: str
    turn_id: str
    scores: dict[str, float]
    overall: float
    flags: list[str]
    timestamp: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "turn_id": self.turn_id,
            "scores": self.scores,
            "overall": self.overall,
            "flags": self.flags,
            "timestamp": self.timestamp,
        }


class Evaluator:
    def evaluate(
        self,
        *,
        session_id: str,
        message: str,
        response: str,
        history: list[dict[str, str]],
    ) -> dict[str, Any]:
        relevance = round((_jaccard_similarity(message, response) * 0.55) + (_contains_keywords(message, response) * 0.45), 3)
        coherence = _history_coherence(response, history)
        completeness = _completeness(message, response)
        efficiency, efficiency_flags = _efficiency(message, response)

        flags = list(efficiency_flags)
        if relevance < 0.2:
            flags.append("off_topic")
        if coherence < 0.55:
            flags.append("incoherent_with_history")
        if len(_tokenize(response)) > 0 and len(set(_tokenize(response))) <= max(3, len(_tokenize(response)) // 4):
            flags.append("repeated_pattern")

        overall = round((relevance * 0.35) + (coherence * 0.2) + (completeness * 0.3) + (efficiency * 0.15), 3)
        turn_id = sha1(f"{session_id}:{message}:{response}".encode("utf-8")).hexdigest()[:12]
        result = EvaluationResult(
            session_id=session_id,
            turn_id=turn_id,
            scores={
                "relevance": relevance,
                "coherence": coherence,
                "completeness": completeness,
                "efficiency": efficiency,
            },
            overall=overall,
            flags=sorted(set(flags)),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        return result.to_dict()
