from __future__ import annotations

import concurrent.futures
import json
import os
import re
import time
from typing import Any


DEFAULT_MODEL = "gemini-2.5-flash"
DEFAULT_TIMEOUT_MS = 30000
DEFAULT_MAX_OUTPUT_CHARS = 12000


def _truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _safe_int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def _redact_sensitive_text(text: str) -> str:
    if not text:
        return text

    redacted = text

    for env_name in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
        value = os.getenv(env_name)
        if value:
            redacted = redacted.replace(value, "[REDACTED]")

    redacted = re.sub(
        r"(AIza[0-9A-Za-z_\-]{20,})",
        "[REDACTED_GOOGLE_API_KEY]",
        redacted,
    )

    return redacted


def extract_json_object(raw_text: str) -> dict[str, Any] | None:
    """
    Extracts the first JSON object from model output.

    Handles:
    - raw JSON
    - ```json fenced JSON
    - explanatory text surrounding JSON

    Returns None when no valid JSON object is found.
    """
    if not raw_text or not raw_text.strip():
        return None

    text = raw_text.strip()

    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
    if fenced:
        text = fenced.group(1).strip()

    if not text.startswith("{"):
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None
        text = text[start : end + 1]

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return None

    if not isinstance(parsed, dict):
        return None

    return parsed


def _build_prompt(task: str) -> str:
    return f"""
You are Hermes, the experimental cognitive brain for Projeto Omni.

Mode: analysis_only.

Rules:
- Do not execute commands.
- Do not request secrets.
- Do not modify files.
- Do not claim actions were performed.
- Do not bypass Omni governance.
- Return JSON only.

Task:
{task}

Return schema:
{{
  "role": "hermes_brain_preview",
  "decision": "analyze_only",
  "summary": "...",
  "recommended_next_steps": ["..."],
  "risks": ["..."],
  "should_omni_execute": false
}}
""".strip()


def analyze_with_hermes_gemini(task: str) -> dict[str, Any]:
    """
    Experimental analysis-only Hermes adapter backed by Gemini.

    This adapter is intentionally non-executing:
    - no shell
    - no file writes
    - no secret requests
    - no direct autonomous action
    """
    started = time.perf_counter()
    timeout_ms = _safe_int_env("OMNI_HERMES_TIMEOUT_MS", DEFAULT_TIMEOUT_MS)
    max_output_chars = _safe_int_env("OMNI_HERMES_MAX_OUTPUT_CHARS", DEFAULT_MAX_OUTPUT_CHARS)
    model = os.getenv("OMNI_HERMES_GEMINI_MODEL", DEFAULT_MODEL)

    base: dict[str, Any] = {
        "provider": "gemini",
        "runtime": "hermes_gemini_adapter",
        "mode": "analysis_only",
        "model": model,
        "enabled": _truthy(os.getenv("OMNI_HERMES_GEMINI_ENABLED")),
        "attempted": False,
        "succeeded": False,
        "latency_ms": 0,
        "output_truncated": False,
        "analysis": None,
        "error_public_code": None,
        "error_public_message": None,
    }

    if not base["enabled"]:
        base.update(
            {
                "error_public_code": "HERMES_DISABLED",
                "error_public_message": "Hermes Gemini adapter is disabled.",
                "latency_ms": int((time.perf_counter() - started) * 1000),
            }
        )
        return base

    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        base.update(
            {
                "error_public_code": "HERMES_MISSING_API_KEY",
                "error_public_message": "Gemini API key is not configured.",
                "latency_ms": int((time.perf_counter() - started) * 1000),
            }
        )
        return base

    def _call_gemini() -> str:
        from google import genai  # lazy import: keeps test/runtime safe when package is absent

        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=model,
            contents=_build_prompt(task),
        )
        return getattr(response, "text", "") or ""

    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    future = executor.submit(_call_gemini)

    try:
        base["attempted"] = True
        raw_text = future.result(timeout=timeout_ms / 1000)
        raw_text = _redact_sensitive_text(raw_text)

        output_truncated = len(raw_text) > max_output_chars
        public_raw = raw_text[:max_output_chars]

        parsed = extract_json_object(raw_text)
        if parsed is None:
            base.update(
                {
                    "error_public_code": "HERMES_INVALID_JSON",
                    "error_public_message": "Hermes returned non-JSON output.",
                    "raw_response_public": public_raw,
                    "output_truncated": output_truncated,
                }
            )
            return base

        base.update(
            {
                "succeeded": True,
                "analysis": parsed,
                "raw_response_public": public_raw,
                "output_truncated": output_truncated,
            }
        )
        return base

    except concurrent.futures.TimeoutError:
        future.cancel()
        base.update(
            {
                "error_public_code": "HERMES_TIMEOUT",
                "error_public_message": "Hermes Gemini adapter timed out.",
            }
        )
        return base

    except Exception as exc:
        base.update(
            {
                "error_public_code": "HERMES_PROVIDER_ERROR",
                "error_public_message": _redact_sensitive_text(str(exc))[:500],
            }
        )
        return base

    finally:
        executor.shutdown(wait=False, cancel_futures=True)
        base["latency_ms"] = int((time.perf_counter() - started) * 1000)
