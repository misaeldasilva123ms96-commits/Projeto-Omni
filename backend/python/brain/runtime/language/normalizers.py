from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


_WS_RE = re.compile(r"\s+")


def normalize_whitespace(text: str) -> str:
    return _WS_RE.sub(" ", str(text or "")).strip()


def infer_language_hint(text: str, user_language: str | None = None) -> str | None:
    hint = str(user_language or "").strip()
    if hint:
        return hint
    lowered = normalize_whitespace(text).lower()
    if not lowered:
        return None
    pt_signals = ("não", "nao", "como", "o que", "qual", "por que", "porque", "resuma", "explique", "plano")
    en_signals = ("what", "how", "why", "summarize", "explain", "plan", "compare")
    if any(sig in lowered for sig in pt_signals):
        return "pt-BR"
    if any(sig in lowered for sig in en_signals):
        return "en"
    return None


def extract_requested_output(text: str, *, intent: str) -> str:
    lowered = normalize_whitespace(text).lower()
    if "json" in lowered:
        return "json"
    if any(term in lowered for term in ("tabela", "table")):
        return "table"
    if any(term in lowered for term in ("bullet", "bullets", "tópicos", "topicos")):
        return "bullets"

    mapping = {
        "summarize": "summary",
        "generate_business_idea": "idea",
        "compare": "comparison",
        "plan": "plan",
        "extract": "extracted_data",
        "classify": "classification",
        "analyze": "analysis",
        "explain": "explanation",
        "execute_tool_like_action": "execution_plan",
        "ask_question": "answer",
        "ambiguous_request": "answer",
    }
    return mapping.get(intent, "answer")


def extract_entities(text: str) -> dict[str, Any]:
    lowered = normalize_whitespace(text).lower()
    entities: dict[str, Any] = {}

    domain_match = re.search(r"\b(domain|dom[ií]nio|nicho|setor)\s*[:=]\s*([a-z0-9_\- ]{2,40})", lowered, re.IGNORECASE)
    if domain_match:
        entities["domain"] = domain_match.group(2).strip()

    about_match = re.search(r"\b(sobre|about)\s+([a-z0-9_\- ]{3,80})", lowered, re.IGNORECASE)
    if about_match and "topic" not in entities:
        entities["topic"] = about_match.group(2).strip()

    target_match = re.search(r"\b(para|for)\s+(iniciante[s]?|beginner[s]?|crian[çc]as|kids|empresas|companies)\b", lowered)
    if target_match:
        entities["audience"] = target_match.group(2).strip()

    if "portugu" in lowered or "pt-br" in lowered:
        entities["language_hint"] = "pt-BR"
    elif "english" in lowered or "en-us" in lowered:
        entities["language_hint"] = "en"

    return entities


def extract_constraints(text: str) -> dict[str, Any]:
    lowered = normalize_whitespace(text).lower()
    constraints: dict[str, Any] = {}

    if any(term in lowered for term in ("baixo orcamento", "baixo orçamento", "low budget", "budget low", "barato")):
        constraints["budget"] = "low"
    elif any(term in lowered for term in ("medio orcamento", "médio orçamento", "medium budget")):
        constraints["budget"] = "medium"
    elif any(term in lowered for term in ("alto orcamento", "alto orçamento", "high budget")):
        constraints["budget"] = "high"

    words_match = re.search(r"\b(at[eé]|max|max\.|no m[aá]ximo)\s*(\d{2,5})\s*(palavras|words)\b", lowered)
    if words_match:
        constraints["max_words"] = int(words_match.group(2))

    format_match = re.search(r"\b(em|as)\s+(json|yaml|markdown|md|lista|t[oó]picos|bullet[s]?)\b", lowered)
    if format_match:
        fmt = format_match.group(2).strip()
        constraints["format"] = "markdown" if fmt in {"md"} else fmt

    tone_match = re.search(r"\b(tom|tone)\s*[:=]\s*(formal|informal|profissional|professional)\b", lowered)
    if tone_match:
        constraints["tone"] = tone_match.group(2).strip()

    urgency_match = re.search(r"\b(urgente|asap|hoje|today)\b", lowered)
    if urgency_match:
        constraints["urgency"] = "high"

    return constraints


@dataclass(frozen=True, slots=True)
class IntentCandidate:
    intent: str
    score: float
    matched_signals: int

