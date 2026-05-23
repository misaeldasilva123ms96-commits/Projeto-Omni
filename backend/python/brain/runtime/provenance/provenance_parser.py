from __future__ import annotations

from typing import Any

from brain.runtime.provenance.provenance_models import ExecutionProvenance


def _legacy_tools(swarm_result: dict[str, Any]) -> list[str]:
    out: list[str] = []
    trace = swarm_result.get("agent_trace")
    if isinstance(trace, list):
        for item in trace:
            if not isinstance(item, dict):
                continue
            t = str(item.get("tool") or item.get("selected_tool") or "").strip()
            if t:
                out.append(t[:128])
    return out[:24]


def _legacy_provider_model(swarm_result: dict[str, Any]) -> tuple[str, str]:
    meta = swarm_result.get("metadata")
    if isinstance(meta, dict):
        p = str(meta.get("provider") or meta.get("llm_provider") or "").strip()
        m = str(meta.get("model") or meta.get("llm_model") or "").strip()
        if p or m:
            return p[:64], m[:128]
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


def _merge_str(primary: str, fallback: str, limit: int) -> str:
    a = str(primary or "").strip()[:limit]
    if a:
        return a
    return str(fallback or "").strip()[:limit]


def parse_execution_provenance(
    swarm_result: dict[str, Any] | None,
    *,
    orchestrator_context: dict[str, Any] | None = None,
    strategy_mode: str = "",
    fallback_used: bool = False,
    latency_total_ms: int = 0,
) -> ExecutionProvenance:
    """
    Merge Node ``metadata.execution_provenance`` (or top-level ``execution_provenance``)
    with Python-side policy context and legacy swarm fields.
    """
    if not isinstance(swarm_result, dict):
        swarm_result = {}
    ctx = orchestrator_context if isinstance(orchestrator_context, dict) else {}

    raw_ep: dict[str, Any] | None = None
    meta = swarm_result.get("metadata")
    if isinstance(meta, dict):
        ep = meta.get("execution_provenance")
        if isinstance(ep, dict):
            raw_ep = ep
    if raw_ep is None:
        top = swarm_result.get("execution_provenance")
        if isinstance(top, dict):
            raw_ep = top

    base = ExecutionProvenance.from_partial_dict(raw_ep) if raw_ep else ExecutionProvenance.empty()

    leg_p, leg_m = _legacy_provider_model(swarm_result)
    leg_tools = _legacy_tools(swarm_result)

    rec = str(ctx.get("policy_recommended") or "").strip().lower()[:64]
    baseline = str(ctx.get("policy_baseline") or "").strip().lower()[:64]
    shadow = bool(ctx.get("policy_shadow_only", True))

    prov_actual = _merge_str(base.provider_actual, leg_p, 64)
    model_actual = _merge_str(base.model_actual, leg_m, 128)

    tool_calls = list(base.tool_calls) if base.tool_calls else leg_tools
    tool_count = base.tool_count if base.tool_count else len(tool_calls)

    strat = _merge_str(base.strategy_actual, strategy_mode, 128)

    policy_applied = bool(base.policy_applied) or (bool(rec) and not shadow)
    policy_match = base.policy_match
    if policy_match is None and rec and prov_actual:
        policy_match = prov_actual.strip().lower() == rec
    elif policy_match is None and rec and not prov_actual:
        policy_match = None

    requested = _merge_str(base.provider_requested, baseline or rec, 64)
    recommended = _merge_str(base.provider_recommended, rec, 64)

    latency_bd = dict(base.latency_breakdown_ms) if base.latency_breakdown_ms else {}
    if latency_total_ms > 0 and "total_turn_ms" not in latency_bd:
        latency_bd["total_turn_ms"] = int(latency_total_ms)

    usage_in = base.usage_tokens_input
    usage_out = base.usage_tokens_output
    cost = base.cost_estimate

    source = _merge_str(base.provenance_source, "python_merged", 64)
    conf = float(base.provenance_confidence or (0.85 if prov_actual else 0.35))

    ch = swarm_result.get("cognitive_runtime_hint")
    lane = str(ch.get("lane") or "") if isinstance(ch, dict) else ""

    return ExecutionProvenance(
        provider_actual=prov_actual,
        model_actual=model_actual,
        provider_requested=requested,
        provider_recommended=recommended,
        strategy_actual=strat,
        tool_calls=tool_calls[:48],
        tool_count=int(tool_count),
        execution_mode=_merge_str(base.execution_mode, lane, 64),
        fallback_path=_merge_str(base.fallback_path, "runtime_fallback" if fallback_used else "", 256),
        node_runtime_path=_merge_str(base.node_runtime_path, "queryEngineAuthority", 128),
        policy_applied=policy_applied,
        policy_match=policy_match,
        latency_breakdown_ms=latency_bd,
        usage_tokens_input=usage_in,
        usage_tokens_output=usage_out,
        cost_estimate=cost,
        provider_failed=bool(base.provider_failed),
        failure_class=_merge_str(base.failure_class, "", 64).lower(),
        failure_reason=_merge_str(base.failure_reason, "", 256),
        provider_diagnostics=list(base.provider_diagnostics),
        provider_fallback_occurred=bool(base.provider_fallback_occurred),
        no_provider_available=bool(base.no_provider_available),
        provenance_source=source,
        provenance_confidence=min(1.0, max(0.0, conf)),
    )
