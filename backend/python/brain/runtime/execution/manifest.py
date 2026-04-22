from __future__ import annotations

import hashlib
from typing import Any

from brain.runtime.execution.manifest_models import ExecutionManifest, ManifestBuildResult, ManifestStep
from brain.runtime.tooling.tool_registry_extensions import get_tool_metadata


def _normalize_output_mode(requested_output: str | None) -> str:
    value = str(requested_output or "").strip().lower()
    if value in {"json", "table"}:
        return "structured"
    if value in {"bullets", "comparison", "plan", "analysis", "explanation", "answer", "summary"}:
        return "hybrid"
    return "direct"


def build_execution_manifest(
    *,
    oil_request: Any,
    routing_decision: Any,
    strategy_payload: dict[str, Any] | None = None,
    selected_tools: list[str] | None = None,
    provider_path: str | None = None,
) -> ManifestBuildResult:
    try:
        selected_tools = [str(item).strip() for item in (selected_tools or []) if str(item).strip()]
        strategy_payload = dict(strategy_payload or {})
        normalized_strategy = str(
            getattr(routing_decision, "strategy", "")
            or strategy_payload.get("selected_strategy", {}).get("path")
            or getattr(routing_decision, "execution_strategy", "")
            or "SAFE_FALLBACK"
        ).strip()
        fallback_strategy = "SAFE_FALLBACK" if getattr(routing_decision, "fallback_allowed", True) else "STRICT_ABORT"
        steps: list[ManifestStep] = [
            ManifestStep(
                step_id="s1",
                kind="reason",
                description=f"classify intent={getattr(routing_decision, 'intent', getattr(oil_request, 'intent', 'unknown'))}",
            )
        ]
        if getattr(routing_decision, "requires_tools", False) and selected_tools:
            for index, tool in enumerate(selected_tools, start=2):
                tool_meta = get_tool_metadata(tool)
                steps.append(
                    ManifestStep(
                        step_id=f"s{index}",
                        kind="tool",
                        description=f"use tool {tool_meta.name} ({tool_meta.category})",
                    )
                )
        elif getattr(routing_decision, "requires_node_runtime", False):
            steps.append(
                ManifestStep(
                    step_id="s2",
                    kind="delegate",
                    description="delegate execution to node runtime bridge",
                )
            )
        else:
            steps.append(
                ManifestStep(
                    step_id="s2",
                    kind="synthesize",
                    description="synthesize direct runtime response",
                )
            )
        observability_tags = [
            f"intent:{getattr(oil_request, 'intent', 'unknown')}",
            f"strategy:{normalized_strategy}",
            f"task_type:{getattr(routing_decision, 'task_type', 'unknown')}",
        ]
        if selected_tools:
            observability_tags.extend([f"tool:{tool}" for tool in selected_tools])
        safety_notes = []
        if str(getattr(routing_decision, "risk_level", "")).strip() in {"high", "critical"}:
            safety_notes.append("high_risk_request")
        if getattr(routing_decision, "requires_node_runtime", False):
            safety_notes.append("node_runtime_delegation")
        manifest_id = "manifest-" + hashlib.sha1(
            "|".join(
                [
                    str(getattr(oil_request, "intent", "unknown")),
                    normalized_strategy,
                    ",".join(selected_tools),
                    str(provider_path or ""),
                ]
            ).encode("utf-8")
        ).hexdigest()[:12]
        manifest = ExecutionManifest(
            manifest_id=manifest_id,
            intent=str(getattr(oil_request, "intent", "unknown")),
            chosen_strategy=normalized_strategy,
            selected_tools=selected_tools,
            step_plan=steps,
            fallback_strategy=fallback_strategy,
            observability_tags=observability_tags,
            safety_notes=safety_notes,
            output_mode=_normalize_output_mode(getattr(oil_request, "requested_output", None)),
            summary_rationale=str(
                getattr(routing_decision, "internal_reasoning_hint", "")
                or getattr(routing_decision, "reasoning", "")
                or "runtime routing manifest built from deterministic hints"
            ).strip(),
            provider_path=str(provider_path or "").strip(),
            metadata={
                "confidence": float(getattr(routing_decision, "confidence", 0.0) or 0.0),
                "preferred_capability_path": getattr(routing_decision, "preferred_capability_path", ""),
                "manifest_driven_execution": True,
            },
        )
        return ManifestBuildResult(
            manifest=manifest,
            degraded=False,
            fallback_triggered=False,
            reason="manifest_built",
        )
    except Exception as exc:
        return ManifestBuildResult(
            manifest=None,
            degraded=True,
            fallback_triggered=True,
            reason="manifest_build_failed",
            metadata={"error": str(exc)},
        )
