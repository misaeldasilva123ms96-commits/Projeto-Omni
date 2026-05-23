from __future__ import annotations

from typing import Any, Callable


def normalize_language(user_language: str | None) -> str:
    if not user_language or not str(user_language).strip():
        return "pt-BR"
    u = str(user_language).strip().lower()
    if u.startswith("pt"):
        return "pt-BR"
    if u.startswith("en"):
        return "en"
    return "pt-BR"


def _tone(tone: str | None) -> str:
    t = (tone or "default").strip().lower()
    if t in {"default", "concise", "explanatory", "structured"}:
        return t
    return "default"


def _pick(lang: str, pt: str, en: str) -> str:
    return en if lang == "en" else pt


def _format_data_lines(data: dict[str, Any], *, lang: str) -> list[str]:
    lines: list[str] = []
    for key, value in sorted(data.items()):
        if value is None or value == "":
            continue
        label = key.replace("_", " ")
        lines.append(f"{label}: {value}")
    if not lines:
        lines.append(_pick(lang, "(sem detalhes estruturados.)", "(no structured details.)"))
    return lines


def _apply_tone(text: str, *, tone: str, lang: str) -> str:
    t = _tone(tone)
    if t == "concise":
        parts = [p.strip() for p in text.replace("\n", " ").split(".") if p.strip()]
        return (parts[0] + ".").strip() if parts else text.strip()
    if t == "explanatory":
        intro = _pick(lang, "Aqui está o resultado.", "Here is the result.")
        return f"{intro}\n\n{text.strip()}"
    if t == "structured":
        if "\n" in text.strip():
            return text.strip()
        return "- " + text.strip().replace(". ", ".\n- ")
    return text.strip()


def render_business_idea(data: dict[str, Any], *, lang: str, tone: str | None) -> str:
    idea = str(data.get("idea") or data.get("title") or "").strip()
    market = str(data.get("target_market") or data.get("market") or "").strip()
    if lang == "en":
        if idea and market:
            base = f"A promising direction is to build {idea} focused on {market}."
        elif idea:
            base = f"A promising direction is to build {idea}."
        else:
            base = "Here is a concise business direction based on the available signals."
    else:
        if idea and market:
            base = f"Uma ideia promissora é criar um {idea} voltado para {market}."
        elif idea:
            base = f"Uma ideia promissora é criar um {idea}."
        else:
            base = "Uma ideia promissora pode ser explorada a partir dos sinais disponíveis."
    return _apply_tone(base, tone=tone, lang=lang)


def render_summary(data: dict[str, Any], *, lang: str, tone: str | None) -> str:
    summary = str(data.get("summary") or data.get("text") or data.get("body") or "").strip()
    if summary:
        base = summary
    else:
        base = _pick(lang, "Resumo indisponível.", "Summary unavailable.")
    return _apply_tone(base, tone=tone, lang=lang)


def render_plan(data: dict[str, Any], *, lang: str, tone: str | None) -> str:
    steps = data.get("steps")
    if isinstance(steps, list) and steps:
        lines = [f"{i + 1}. {s}" for i, s in enumerate(str(s).strip() for s in steps if str(s).strip())]
        header = _pick(lang, "Plano sugerido:", "Suggested plan:")
        base = header + "\n" + "\n".join(lines)
    else:
        plan_text = str(data.get("plan") or data.get("outline") or "").strip()
        base = plan_text or _pick(lang, "Plano indisponível.", "Plan unavailable.")
    return _apply_tone(base, tone=tone, lang=lang)


def render_comparison(data: dict[str, Any], *, lang: str, tone: str | None) -> str:
    a = str(data.get("a") or data.get("left") or "").strip()
    b = str(data.get("b") or data.get("right") or "").strip()
    if a and b:
        base = _pick(lang, f"Comparação entre “{a}” e “{b}”.", f"Comparison between “{a}” and “{b}”.")
    else:
        base = _pick(lang, "Comparação resumida com base nos dados disponíveis.", "Comparison based on available data.")
    return _apply_tone(base, tone=tone, lang=lang)


def render_extracted_data(data: dict[str, Any], *, lang: str, tone: str | None) -> str:
    lines = _format_data_lines(data, lang=lang)
    header = _pick(lang, "Dados extraídos:", "Extracted data:")
    base = header + "\n" + "\n".join(lines)
    return _apply_tone(base, tone=tone, lang=lang)


def render_answer(data: dict[str, Any], *, lang: str, tone: str | None) -> str:
    answer = str(data.get("answer") or data.get("response") or data.get("text") or "").strip()
    base = answer or _pick(lang, "Resposta indisponível.", "Answer unavailable.")
    return _apply_tone(base, tone=tone, lang=lang)


def render_generic_success(data: dict[str, Any], *, lang: str, tone: str | None) -> str:
    msg = str(data.get("message") or data.get("detail") or "").strip()
    if msg:
        base = msg
    else:
        base = _pick(lang, "Operação concluída com sucesso.", "Operation completed successfully.")
    return _apply_tone(base, tone=tone, lang=lang)


def render_error_message(*, code: str, message: str, recoverable: bool, lang: str) -> str:
    code_u = str(code or "").strip().upper()
    msg = str(message or "").strip()
    if code_u == "AMBIGUOUS_INTENT":
        if lang == "en":
            return (
                "I could not confidently determine what you want to do yet. "
                "Please rephrase your request with a bit more detail."
            )
        return (
            "Não consegui identificar com segurança o que você quer fazer ainda. "
            "Reformule seu pedido com um pouco mais de detalhe."
        )
    if recoverable:
        if lang == "en":
            return msg or "Something went wrong, but you can try again with a clearer request."
        return msg or "Algo deu errado, mas você pode tentar de novo com um pedido mais claro."
    if lang == "en":
        return msg or "An error occurred while processing your request."
    return msg or "Ocorreu um erro ao processar seu pedido."


Renderer = Callable[[dict[str, Any], str, str | None], str]

RESULT_RENDERERS: dict[str, Renderer] = {
    "business_idea": render_business_idea,
    "idea": render_business_idea,
    "summary": render_summary,
    "plan": render_plan,
    "comparison": render_comparison,
    "extracted_data": render_extracted_data,
    "answer": render_answer,
    "generic_success": render_generic_success,
}
