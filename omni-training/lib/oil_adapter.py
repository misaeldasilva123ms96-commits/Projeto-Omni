from __future__ import annotations

import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_PYTHON = PROJECT_ROOT / "backend" / "python"
if BACKEND_PYTHON.exists() and str(BACKEND_PYTHON) not in sys.path:
    sys.path.insert(0, str(BACKEND_PYTHON))

try:
    from brain.runtime.language import translate_to_oil_projection  # type: ignore
except Exception:  # pragma: no cover - fallback path is what matters
    translate_to_oil_projection = None


def _fallback_projection(text: str) -> dict[str, Any]:
    lowered = str(text or "").lower()
    user_intent = "ambiguous_request"
    if any(term in lowered for term in ("debug", "erro", "falha", "corrija", "bug")):
        user_intent = "analyze"
    elif any(term in lowered for term in ("plano", "roadmap", "etapas", "plan")):
        user_intent = "plan"
    elif any(term in lowered for term in ("explique", "explain", "resuma", "summarize")):
        user_intent = "explain"
    desired_output = "json" if "json" in lowered else "answer"
    urgency = "high" if any(term in lowered for term in ("urgent", "urgente", "hoje", "today")) else "medium"
    execution_bias = "deep" if user_intent in {"analyze", "plan"} else "balanced"
    memory_relevance = "high" if any(term in lowered for term in ("context", "contexto", "memory", "lembra")) else "low"
    return {
        "user_intent": user_intent,
        "entities": {},
        "constraints": {},
        "desired_output": desired_output,
        "urgency": urgency,
        "execution_bias": execution_bias,
        "memory_relevance": memory_relevance,
        "metadata": {"source": "omni_training_fallback"},
    }


def convert_text_to_oil(text: str, *, session_id: str = "omni-training") -> dict[str, Any]:
    if translate_to_oil_projection is None:
        return _fallback_projection(text)
    _, projection = translate_to_oil_projection(
        text,
        session_id=session_id,
        run_id="omni-training",
        metadata={"source_component": "omni-training"},
    )
    return projection.as_dict()
