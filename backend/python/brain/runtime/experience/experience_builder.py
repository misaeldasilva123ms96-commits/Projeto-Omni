from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from brain.runtime.experience.experience_models import ExperienceRecord, new_experience_id, new_turn_id
from brain.runtime.feedback.feedback_models import FeedbackBundle


def _tools_from_swarm(swarm_result: dict[str, Any]) -> list[str]:
    out: list[str] = []
    if not isinstance(swarm_result, dict):
        return out
    trace = swarm_result.get("agent_trace")
    if isinstance(trace, list):
        for item in trace:
            if not isinstance(item, dict):
                continue
            t = str(item.get("tool") or item.get("selected_tool") or "").strip()
            if t:
                out.append(t[:128])
    return out[:24]


def _provider_model_from_swarm(swarm_result: dict[str, Any]) -> tuple[str, str]:
    if not isinstance(swarm_result, dict):
        return "", ""
    meta = swarm_result.get("metadata")
    if isinstance(meta, dict):
        p = str(meta.get("provider") or meta.get("llm_provider") or "").strip()
        m = str(meta.get("model") or meta.get("llm_model") or "").strip()
        if p or m:
            return p[:64], m[:128]
    # execution_request path sometimes embeds provider on first action
    er = swarm_result.get("execution_request")
    if isinstance(er, dict):
        acts = er.get("actions")
        if isinstance(acts, list) and acts:
            a0 = acts[0] if isinstance(acts[0], dict) else {}
            if isinstance(a0, dict):
                args = a0.get("tool_arguments")
                if isinstance(args, dict):
                    p = str(args.get("provider") or "").strip()
                    m = str(args.get("model") or "").strip()
                    return p[:64], m[:128]
    return "", ""


def build_experience_record(
    *,
    session_id: str,
    user_input: str,
    normalized_intent: str,
    swarm_result: dict[str, Any],
    strategy_payload: dict[str, Any],
    latency_ms: int,
    fallback_used: bool,
    error_class: str,
    response_quality_score: float | None,
    feedback: FeedbackBundle,
    success_outcome: bool,
    learning_summary: str,
    agent_trace_summary: str,
    cost_estimate: float | None = None,
    execution_provenance: dict[str, Any] | None = None,
) -> ExperienceRecord:
    turn_id = new_turn_id()
    eid = new_experience_id(session_id, turn_id)
    ts = datetime.now(timezone.utc).isoformat()
    sel = strategy_payload.get("selected_strategy") if isinstance(strategy_payload, dict) else {}
    strategy_mode = ""
    if isinstance(sel, dict):
        strategy_mode = str(sel.get("mode", "") or "").strip()
    prov, model = _provider_model_from_swarm(swarm_result)
    tools = _tools_from_swarm(swarm_result)
    ep = dict(execution_provenance) if isinstance(execution_provenance, dict) else None
    meta: dict[str, Any] = {"feedback": feedback.as_dict()}
    if ep:
        meta["execution_provenance"] = ep
        pa = str(ep.get("provider_actual") or "").strip()
        ma = str(ep.get("model_actual") or "").strip()
        if pa:
            prov = pa[:64]
        if ma:
            model = ma[:128]
        tc = ep.get("tool_calls")
        if isinstance(tc, list) and tc:
            tools = [str(t).strip()[:128] for t in tc if str(t).strip()][:24]
        ce_ep = ep.get("cost_estimate")
        if isinstance(ce_ep, (int, float)) and cost_estimate is None:
            cost_estimate = float(ce_ep)
    return ExperienceRecord(
        experience_id=eid,
        session_id=str(session_id or "")[:512],
        turn_id=turn_id,
        timestamp=ts,
        user_input=str(user_input or "")[:4000],
        normalized_intent=str(normalized_intent or "unknown")[:256],
        provider_selected=prov,
        model_selected=model,
        tools_selected=tools,
        strategy_selected=strategy_mode[:128] or "unknown",
        latency_ms=max(0, int(latency_ms)),
        cost_estimate=cost_estimate,
        fallback_used=bool(fallback_used),
        error_class=str(error_class or "")[:128],
        response_quality_score=response_quality_score,
        feedback_class=str(feedback.feedback_class)[:32],
        feedback_source=str(feedback.feedback_source)[:16],
        success_outcome=bool(success_outcome),
        agent_trace_summary=str(agent_trace_summary or "")[:2000],
        learning_signals_summary=str(learning_summary or "")[:2000],
        metadata=meta,
    )
