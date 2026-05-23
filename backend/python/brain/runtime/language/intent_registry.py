from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Pattern


@dataclass(frozen=True, slots=True)
class IntentRule:
    intent: str
    patterns: tuple[Pattern[str], ...]
    base_confidence: float


FALLBACK_INTENT = "ambiguous_request"


def _rx(pattern: str) -> Pattern[str]:
    return re.compile(pattern, re.IGNORECASE | re.UNICODE)


INTENTS: tuple[IntentRule, ...] = (
    IntentRule(
        intent="summarize",
        patterns=(
            _rx(r"\b(summarize|summary|tl;dr)\b"),
            _rx(r"\b(resuma|resumir|resumo|sumarize)\b"),
        ),
        base_confidence=0.85,
    ),
    IntentRule(
        intent="generate_business_idea",
        patterns=(
            _rx(r"\b(business idea|startup idea|saas idea)\b"),
            _rx(r"\b(ideia de (neg[óo]cio|startup)|crie uma ideia)\b"),
            _rx(r"\b(ganhar dinheiro|renda extra)\b"),
        ),
        base_confidence=0.8,
    ),
    IntentRule(
        intent="compare",
        patterns=(
            _rx(r"\b(compare|vs\.?|versus)\b"),
            _rx(r"\b(compar(e|ar)|diferen[çc]a entre|qual (é|e) melhor)\b"),
        ),
        base_confidence=0.75,
    ),
    IntentRule(
        intent="plan",
        patterns=(
            _rx(r"\b(plan|roadmap|steps|step-by-step)\b"),
            _rx(r"\b(plano|roteiro|passo a passo|etapas)\b"),
        ),
        base_confidence=0.75,
    ),
    IntentRule(
        intent="extract",
        patterns=(
            _rx(r"\b(extract|parse|pull out)\b"),
            _rx(r"\b(extraia|extrair|identifique|liste)\b"),
        ),
        base_confidence=0.7,
    ),
    IntentRule(
        intent="classify",
        patterns=(
            _rx(r"\b(classify|categorize|label)\b"),
            _rx(r"\b(classifique|categorize|rotule)\b"),
        ),
        base_confidence=0.7,
    ),
    IntentRule(
        intent="analyze",
        patterns=(
            _rx(r"\b(analyze|analysis)\b"),
            _rx(r"\b(analis(e|ar)|an[áa]lise)\b"),
        ),
        base_confidence=0.65,
    ),
    IntentRule(
        intent="explain",
        patterns=(
            _rx(r"\b(explain|how does|what is)\b"),
            _rx(r"\b(expliqu(e|ar)|como funciona|o que (é|e))\b"),
        ),
        base_confidence=0.65,
    ),
    IntentRule(
        intent="ask_question",
        patterns=(
            _rx(r"\?$"),
            _rx(r"^\s*(what|how|why|when|where|who)\b"),
            _rx(r"^\s*(o que|como|por que|porque|quando|onde|quem)\b"),
        ),
        base_confidence=0.55,
    ),
    IntentRule(
        intent="execute_tool_like_action",
        patterns=(
            _rx(r"\b(run|execute|cmd|command)\b"),
            _rx(r"\b(rod(e|ar)|execut(e|ar)|comando)\b"),
            _rx(r"^\s*git\s+\w+"),
        ),
        base_confidence=0.6,
    ),
)

