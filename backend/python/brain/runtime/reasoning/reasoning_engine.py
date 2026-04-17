from __future__ import annotations

import hashlib
from typing import Any

from brain.runtime.language import (
    ReasoningHandoffContract,
    build_reasoning_oil_result,
    normalize_input_to_oil_request,
)
from brain.runtime.language.oil_schema import OILRequest
from brain.runtime.reasoning.models import ReasoningOutcome, ReasoningTrace

_TASK_TYPE_BY_INTENT = {
    "ask_question": "simple_query",
    "summarize": "simple_query",
    "compare": "repository_analysis",
    "analyze": "repository_analysis",
    "plan": "code_mutation",
    "execute_tool_like_action": "code_mutation",
}

_CAPABILITY_HINTS_BY_INTENT = {
    "ask_question": ["read_file", "glob_search"],
    "summarize": ["read_file"],
    "compare": ["read_file", "grep_search"],
    "analyze": ["code_search", "grep_search"],
    "plan": ["git_status", "test_runner"],
    "execute_tool_like_action": ["shell_command", "test_runner"],
}


class ReasoningEngine:
    """Phase 31 deterministic reasoning layer with OIL-dominant boundaries."""

    def reason(
        self,
        *,
        raw_input: str,
        session_id: str | None,
        run_id: str | None,
        source_component: str,
        preferred_mode: str | None = None,
        oil_request: OILRequest | None = None,
        memory_context: dict[str, Any] | None = None,
    ) -> ReasoningOutcome:
        normalized_input = str(raw_input or "").strip()
        mode = self._select_mode(normalized_input, preferred_mode=preferred_mode)
        active_oil_request = oil_request or normalize_input_to_oil_request(
            normalized_input,
            session_id=session_id,
            run_id=run_id,
            metadata={
                "source_component": source_component,
                "reasoning_mode": mode,
                "reasoning_phase": "interpret",
            },
        )
        active_memory_context = dict(memory_context or {})
        interpretation = self._interpret(
            oil_request=active_oil_request,
            mode=mode,
            normalized_input=normalized_input,
            memory_context=active_memory_context,
        )
        plan = self._plan(
            oil_request=active_oil_request,
            interpretation=interpretation,
            mode=mode,
            memory_context=active_memory_context,
        )
        reasoning = self._reason(
            oil_request=active_oil_request,
            interpretation=interpretation,
            plan=plan,
            mode=mode,
            memory_context=active_memory_context,
        )
        validation = self._validate(oil_request=active_oil_request, plan=plan, reasoning=reasoning, mode=mode)
        handoff = self._handoff(
            oil_request=active_oil_request,
            interpretation=interpretation,
            plan=plan,
            reasoning=reasoning,
            validation=validation,
            mode=mode,
            memory_context=active_memory_context,
        )
        oil_result = build_reasoning_oil_result(
            handoff=handoff,
            confidence=float(interpretation.get("confidence", 0.0)),
            mode=mode,
        )
        trace = self._trace(
            session_id=session_id,
            run_id=run_id,
            mode=mode,
            interpretation=interpretation,
            plan=plan,
            validation=validation,
            handoff=handoff,
            normalized_input=normalized_input,
        )
        return ReasoningOutcome(
            mode=mode,
            normalized_input=normalized_input,
            oil_request=active_oil_request,
            oil_result=oil_result,
            execution_handoff=handoff.as_dict(),
            trace=trace,
            confidence=max(0.0, min(1.0, float(interpretation.get("confidence", 0.0)))),
            memory_context=active_memory_context,
        )

    @staticmethod
    def _select_mode(text: str, *, preferred_mode: str | None = None) -> str:
        preferred = str(preferred_mode or "").strip().lower()
        if preferred in {"fast", "deep", "critical"}:
            return preferred
        lowered = text.lower()
        critical_signals = ("production", "credential", "secret", "drop ", "delete ", "rm -rf", "security")
        if any(token in lowered for token in critical_signals):
            return "critical"
        deep_signals = ("architecture", "refactor", "analysis", "planejamento", "strategy", "trade-off")
        if len(text) > 160 or any(token in lowered for token in deep_signals):
            return "deep"
        return "fast"

    @staticmethod
    def _interpret(
        *,
        oil_request: Any,
        mode: str,
        normalized_input: str,
        memory_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        confidence = float(oil_request.extensions.get("confidence", 0.0) or 0.0)
        memory_selected_count = int((memory_context or {}).get("selected_count", 0) or 0)
        memory_bonus = min(0.2, memory_selected_count * 0.02)
        confidence = max(0.0, min(1.0, confidence + memory_bonus))
        summary = (
            f"intent={oil_request.intent} mode={mode} confidence={confidence:.2f} "
            f"memory_selected={memory_selected_count}"
        )
        return {
            "intent": oil_request.intent,
            "confidence": confidence,
            "summary": summary,
            "normalized_input": normalized_input,
            "requested_output": str(oil_request.requested_output or "answer"),
            "memory_selected_count": memory_selected_count,
        }

    @staticmethod
    def _plan(
        *,
        oil_request: Any,
        interpretation: dict[str, Any],
        mode: str,
        memory_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        steps = ["interpret", "plan", "reason", "validate", "handoff_to_execution"]
        if int((memory_context or {}).get("selected_count", 0) or 0) > 0:
            steps.insert(1, "memory_contextualization")
        if mode == "deep":
            steps.insert(3, "review_assumptions")
        if mode == "critical":
            steps.insert(3, "risk_gate")
            steps.append("governance_confirmation")
        task_type = _TASK_TYPE_BY_INTENT.get(interpretation["intent"], "simple_query")
        execution_strategy = "direct" if mode == "fast" else "phased" if mode == "deep" else "guarded"
        return {
            "steps": steps,
            "task_type": task_type,
            "execution_strategy": execution_strategy,
            "summary": f"{task_type}:{execution_strategy} ({len(steps)} stages)",
            "requested_output": interpretation.get("requested_output", "answer"),
            "intent": oil_request.intent,
            "memory_context_id": str((memory_context or {}).get("context_id", "")).strip(),
        }

    @staticmethod
    def _reason(
        *,
        oil_request: Any,
        interpretation: dict[str, Any],
        plan: dict[str, Any],
        mode: str,
        memory_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        confidence = float(interpretation.get("confidence", 0.0))
        suggested_capabilities = list(_CAPABILITY_HINTS_BY_INTENT.get(oil_request.intent, ["read_file"]))
        if mode in {"deep", "critical"} and "code_search" not in suggested_capabilities:
            suggested_capabilities.append("code_search")
        sources = list((memory_context or {}).get("sources_used", []))
        if "semantic_memory" in sources and "code_search" not in suggested_capabilities:
            suggested_capabilities.append("code_search")
        if "transcript" in sources and "read_file" not in suggested_capabilities:
            suggested_capabilities.append("read_file")
        return {
            "should_execute": True,
            "task_type": str(plan["task_type"]),
            "execution_strategy": str(plan["execution_strategy"]),
            "suggested_capabilities": suggested_capabilities,
            "reasoning_summary": (
                f"Intent {oil_request.intent} routed as {plan['task_type']} with "
                f"{plan['execution_strategy']} strategy under {mode} mode "
                f"(memory_sources={len(sources)})."
            ),
            "confidence": confidence,
            "memory_sources": sources,
        }

    @staticmethod
    def _validate(*, oil_request: Any, plan: dict[str, Any], reasoning: dict[str, Any], mode: str) -> dict[str, Any]:
        issues: list[str] = []
        if not oil_request.intent:
            issues.append("missing_intent")
        if not plan.get("steps"):
            issues.append("missing_plan_steps")
        if not reasoning.get("task_type"):
            issues.append("missing_task_type")
        valid = not issues
        outcome = "valid" if valid else "invalid"
        governance = {
            "reason": "reasoning_validation_passed" if valid else "reasoning_validation_failed",
            "source": "system_reasoning",
            "severity": "normal" if valid else "critical",
        }
        return {
            "valid": valid,
            "outcome": outcome,
            "issues": issues,
            "governance": governance,
            "mode": mode,
        }

    @staticmethod
    def _handoff(
        *,
        oil_request: Any,
        interpretation: dict[str, Any],
        plan: dict[str, Any],
        reasoning: dict[str, Any],
        validation: dict[str, Any],
        mode: str,
        memory_context: dict[str, Any] | None = None,
    ) -> ReasoningHandoffContract:
        proceed = bool(validation.get("valid", False) and reasoning.get("should_execute", False))
        governance = dict(validation.get("governance", {}))
        memory_payload = dict(memory_context or {})
        observability = {
            "reasoning_mode": mode,
            "intent": oil_request.intent,
            "validation_outcome": validation.get("outcome", "invalid"),
            "plan_stage_count": len(plan.get("steps", [])),
            "memory_consulted": bool(memory_payload),
            "memory_selected_count": int(memory_payload.get("selected_count", 0) or 0),
        }
        return ReasoningHandoffContract(
            proceed=proceed,
            mode=mode,
            intent=oil_request.intent,
            task_type=str(reasoning.get("task_type", "")),
            execution_strategy=str(reasoning.get("execution_strategy", "")),
            suggested_capabilities=list(reasoning.get("suggested_capabilities", [])),
            reasoning_summary=str(reasoning.get("reasoning_summary", "")),
            governance=governance,
            observability=observability,
            plan_steps=list(plan.get("steps", [])),
            validation={
                "outcome": validation.get("outcome", "invalid"),
                "issues": list(validation.get("issues", [])),
            },
            metadata={
                "requested_output": interpretation.get("requested_output", "answer"),
                "confidence": interpretation.get("confidence", 0.0),
                "input_entities": len(getattr(oil_request, "entities", {}) or {}),
                "memory_context_id": str(memory_payload.get("context_id", "")).strip() or None,
                "memory_summary": str(memory_payload.get("context_summary", "")).strip(),
            },
        )

    @staticmethod
    def _trace(
        *,
        session_id: str | None,
        run_id: str | None,
        mode: str,
        interpretation: dict[str, Any],
        plan: dict[str, Any],
        validation: dict[str, Any],
        handoff: ReasoningHandoffContract,
        normalized_input: str,
    ) -> ReasoningTrace:
        trace_id = hashlib.sha1(f"{session_id}:{run_id}:{mode}:{normalized_input}".encode("utf-8")).hexdigest()[:16]
        return ReasoningTrace(
            trace_id=f"reason-{trace_id}",
            session_id=session_id,
            run_id=run_id,
            mode=mode,
            interpreted_intent=str(interpretation.get("intent", "")),
            interpretation_summary=str(interpretation.get("summary", "")),
            plan_summary=str(plan.get("summary", "")),
            validation_result=str(validation.get("outcome", "invalid")),
            handoff_decision="proceed" if handoff.proceed else "blocked",
            governance=dict(handoff.governance),
            observability=dict(handoff.observability),
        )
