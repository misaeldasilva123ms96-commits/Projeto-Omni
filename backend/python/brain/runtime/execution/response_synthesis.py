from __future__ import annotations

import re

from .strategy_models import StrategyExecutionRequest, StrategyExecutionResult


def synthesize_strategy_response(
    request: StrategyExecutionRequest,
    result: StrategyExecutionResult,
) -> tuple[str, str]:
    response = str(result.response_text or "").strip()
    if not response:
        response = str(request.fallback_response or "").strip()
    response = re.sub(r"\n{3,}", "\n\n", response).strip()
    output_mode = str(request.manifest.get("output_mode", "direct") or "direct").strip().lower()
    safety_notes = {str(item).strip().lower() for item in list(request.manifest.get("safety_notes", []) or [])}
    synthesis_mode = output_mode
    if result.fallback_applied or result.blocked:
        synthesis_mode = "fallback"
    elif "high_risk_request" in safety_notes and len(response) > 2200:
        response = response[:2200].rstrip()
        synthesis_mode = "risk_trimmed"
    elif output_mode == "structured" and not response.startswith("{") and not response.startswith("["):
        synthesis_mode = "structured_passthrough"
    elif output_mode == "hybrid":
        synthesis_mode = "hybrid"
    else:
        synthesis_mode = "direct"
    return response, synthesis_mode

