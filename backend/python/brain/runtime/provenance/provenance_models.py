from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


def _s(v: Any, limit: int) -> str:
    if v is None:
        return ""
    return str(v).strip()[:limit]


@dataclass(slots=True)
class ExecutionProvenance:
    """Canonical cross-runtime execution truth (Phase 42). All fields degrade gracefully."""

    provider_actual: str = ""
    model_actual: str = ""
    provider_requested: str = ""
    provider_recommended: str = ""
    strategy_actual: str = ""
    tool_calls: list[str] = field(default_factory=list)
    tool_count: int = 0
    execution_mode: str = ""
    fallback_path: str = ""
    node_runtime_path: str = ""
    policy_applied: bool = False
    policy_match: bool | None = None
    latency_breakdown_ms: dict[str, Any] = field(default_factory=dict)
    usage_tokens_input: int | None = None
    usage_tokens_output: int | None = None
    cost_estimate: float | None = None
    provider_failed: bool = False
    failure_class: str = ""
    failure_reason: str = ""
    provider_diagnostics: list[dict[str, Any]] = field(default_factory=list)
    provider_fallback_occurred: bool = False
    no_provider_available: bool = False
    provenance_source: str = ""
    provenance_confidence: float = 0.0

    def as_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["tool_calls"] = list(self.tool_calls)
        d["latency_breakdown_ms"] = dict(self.latency_breakdown_ms)
        d["provider_diagnostics"] = [dict(item) for item in self.provider_diagnostics]
        return d

    @classmethod
    def empty(cls) -> ExecutionProvenance:
        return cls()

    @classmethod
    def from_partial_dict(cls, raw: dict[str, Any] | None) -> ExecutionProvenance:
        if not isinstance(raw, dict):
            return cls.empty()
        lat = raw.get("latency_breakdown_ms")
        if not isinstance(lat, dict):
            lat = {}
        tools = raw.get("tool_calls")
        if isinstance(tools, list):
            tc = [str(t).strip()[:128] for t in tools if str(t).strip()][:48]
        else:
            tc = []
        ui = raw.get("usage_tokens_input")
        uo = raw.get("usage_tokens_output")
        ce = raw.get("cost_estimate")
        pm = raw.get("policy_match")
        diagnostics_raw = raw.get("provider_diagnostics")
        diagnostics: list[dict[str, Any]] = []
        if isinstance(diagnostics_raw, list):
            for item in diagnostics_raw[:16]:
                if not isinstance(item, dict):
                    continue
                diagnostics.append(
                    {
                        "provider": _s(item.get("provider"), 64).lower(),
                        "configured": bool(item.get("configured")),
                        "available": bool(item.get("available")),
                        "selected": bool(item.get("selected")),
                        "attempted": bool(item.get("attempted")),
                        "succeeded": bool(item.get("succeeded")),
                        "failed": bool(item.get("failed")),
                        "failure_class": _s(item.get("failure_class"), 64).lower() or None,
                        "failure_reason": _s(item.get("failure_reason"), 256) or None,
                        "latency_ms": int(item.get("latency_ms")) if isinstance(item.get("latency_ms"), (int, float)) else None,
                    }
                )
        return cls(
            provider_actual=_s(raw.get("provider_actual"), 64),
            model_actual=_s(raw.get("model_actual"), 128),
            provider_requested=_s(raw.get("provider_requested"), 64),
            provider_recommended=_s(raw.get("provider_recommended"), 64),
            strategy_actual=_s(raw.get("strategy_actual"), 128),
            tool_calls=tc,
            tool_count=int(raw.get("tool_count") or len(tc)),
            execution_mode=_s(raw.get("execution_mode"), 64),
            fallback_path=_s(raw.get("fallback_path"), 256),
            node_runtime_path=_s(raw.get("node_runtime_path"), 128),
            policy_applied=bool(raw.get("policy_applied")),
            policy_match=pm if isinstance(pm, bool) else None,
            latency_breakdown_ms={str(k)[:64]: int(v) for k, v in lat.items() if isinstance(v, (int, float))},
            usage_tokens_input=int(ui) if isinstance(ui, (int, float)) else None,
            usage_tokens_output=int(uo) if isinstance(uo, (int, float)) else None,
            cost_estimate=float(ce) if isinstance(ce, (int, float)) else None,
            provider_failed=bool(raw.get("provider_failed")),
            failure_class=_s(raw.get("failure_class"), 64).lower(),
            failure_reason=_s(raw.get("failure_reason"), 256),
            provider_diagnostics=diagnostics,
            provider_fallback_occurred=bool(raw.get("provider_fallback_occurred")),
            no_provider_available=bool(raw.get("no_provider_available")),
            provenance_source=_s(raw.get("provenance_source"), 64),
            provenance_confidence=float(raw.get("provenance_confidence") or 0.0),
        )


def provenance_to_flat_dict(p: ExecutionProvenance | None) -> dict[str, Any]:
    if p is None:
        return {}
    return p.as_dict()
