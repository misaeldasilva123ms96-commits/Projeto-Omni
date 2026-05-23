from __future__ import annotations

from typing import Any

from brain.runtime.language.oil_schema import OILError, OILResult
from brain.runtime.language.renderers import (
    RESULT_RENDERERS,
    normalize_language,
    render_error_message,
    render_generic_success,
)


DEFAULT_FALLBACK_PT = "Nao consegui processar isso ainda, mas estou aprendendo."
DEFAULT_FALLBACK_EN = "I could not process that yet, but I am learning."


class OutputComposer:
    """Deterministic structured result → user-facing natural language (Phase 30.4)."""

    def compose(
        self,
        result: OILResult | OILError | dict[str, Any] | str,
        *,
        user_language: str | None = None,
        tone: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        _ = metadata
        lang = normalize_language(user_language)

        if isinstance(result, str):
            return result.strip() or (DEFAULT_FALLBACK_EN if lang == "en" else DEFAULT_FALLBACK_PT)

        if isinstance(result, OILError):
            return render_error_message(
                code=result.error.code,
                message=result.error.message,
                recoverable=result.error.recoverable,
                lang=lang,
            )

        if isinstance(result, OILResult):
            return self._compose_oil_result(result, lang=lang, tone=tone)

        if isinstance(result, dict):
            return self._compose_dict(result, lang=lang, tone=tone)

        return DEFAULT_FALLBACK_EN if lang == "en" else DEFAULT_FALLBACK_PT

    def _compose_oil_result(self, result: OILResult, *, lang: str, tone: str | None) -> str:
        status = str(result.status or "").strip().lower()
        if status and status not in {"success", "ok", "completed"}:
            msg = str(result.data.get("message") or result.data.get("error") or "").strip()
            if msg:
                return msg
            return DEFAULT_FALLBACK_EN if lang == "en" else DEFAULT_FALLBACK_PT
        rtype = str(result.result_type or "").strip().lower()
        renderer = RESULT_RENDERERS.get(rtype, render_generic_success)
        return renderer(dict(result.data), lang=lang, tone=tone)

    def _compose_dict(self, payload: dict[str, Any], *, lang: str, tone: str | None) -> str:
        if "error" in payload and isinstance(payload.get("error"), dict):
            err = payload["error"]
            code = str(err.get("code") or "")
            message = str(err.get("message") or "")
            recoverable = bool(err.get("recoverable", False))
            return render_error_message(code=code, message=message, recoverable=recoverable, lang=lang)
        if "result_type" in payload and "status" in payload:
            try:
                oil = OILResult.deserialize(payload)
            except ValueError:
                return self._compose_loose_dict(payload, lang=lang, tone=tone)
            return self._compose_oil_result(oil, lang=lang, tone=tone)
        return self._compose_loose_dict(payload, lang=lang, tone=tone)

    def _compose_loose_dict(self, payload: dict[str, Any], *, lang: str, tone: str | None) -> str:
        if "response" in payload and isinstance(payload.get("response"), str):
            text = str(payload["response"]).strip()
            if text:
                return text
        if "message" in payload and isinstance(payload.get("message"), str):
            text = str(payload["message"]).strip()
            if text:
                return text
        return render_generic_success(dict(payload), lang=lang, tone=tone)


def compose_output(
    result: OILResult | OILError | dict[str, Any] | str,
    *,
    user_language: str | None = None,
    tone: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> str:
    return OutputComposer().compose(result, user_language=user_language, tone=tone, metadata=metadata)
