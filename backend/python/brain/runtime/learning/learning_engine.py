from __future__ import annotations

from pathlib import Path
from typing import Any

from brain.runtime.learning.runtime_learning_models import (
    ExecutionOutcomeAssessment,
    OutcomeClass,
    RuntimeFeedbackSignal,
    RuntimeLearningRecord,
    RuntimeLearningStage,
    RuntimeLearningSummary,
    RuntimeLearningTrace,
    SignalPolarity,
    new_learning_record_id,
    new_learning_trace_id,
)
from brain.runtime.learning.runtime_learning_store import RuntimeLearningStore


def _trace_id_from_handoff(reasoning_payload: dict[str, Any]) -> str | None:
    tr = reasoning_payload.get("trace")
    if isinstance(tr, dict):
        tid = str(tr.get("trace_id", "")).strip()
        return tid or None
    return None


def _planning_ids(planning_payload: dict[str, Any]) -> tuple[str | None, str | None]:
    if not planning_payload:
        return None, None
    pt = planning_payload.get("planning_trace") or {}
    ep = planning_payload.get("execution_plan") or {}
    if not isinstance(pt, dict):
        pt = {}
    if not isinstance(ep, dict):
        ep = {}
    return (
        str(pt.get("trace_id", "")).strip() or None,
        str(ep.get("plan_id", "")).strip() or None,
    )


class LearningEngine:
    """Phase 34 — post-execution outcome assessment and bounded learning signals (no strategy mutation)."""

    def __init__(self, root: Path) -> None:
        self._store = RuntimeLearningStore(root)

    def assess_chat_turn(
        self,
        *,
        session_id: str | None,
        run_id: str | None,
        message: str,
        response: str,
        reasoning_payload: dict[str, Any],
        memory_context_payload: dict[str, Any],
        planning_payload: dict[str, Any],
        swarm_result: dict[str, Any],
        evaluation: dict[str, Any],
        duration_ms: int,
        last_runtime_reason: str,
        last_runtime_mode: str,
        safe_fallback_response: str,
        direct_memory_hit: bool,
        feedback_bundle: dict[str, Any] | None = None,
    ) -> tuple[RuntimeLearningRecord, RuntimeLearningTrace]:
        try:
            return self._synthesize(
                record_id=new_learning_record_id(),
                session_id=session_id,
                run_id=run_id,
                message=message,
                response=response,
                reasoning_payload=reasoning_payload,
                memory_context_payload=memory_context_payload,
                planning_payload=planning_payload,
                swarm_result=swarm_result,
                evaluation=evaluation,
                duration_ms=duration_ms,
                last_runtime_reason=last_runtime_reason,
                last_runtime_mode=last_runtime_mode,
                safe_fallback_response=safe_fallback_response,
                direct_memory_hit=direct_memory_hit,
                feedback_bundle=feedback_bundle,
            )
        except Exception as exc:
            return self._minimal_failure_record(
                record_id=new_learning_record_id(),
                session_id=session_id,
                run_id=run_id,
                error=str(exc),
                duration_ms=duration_ms,
            )

    def _minimal_failure_record(
        self,
        *,
        record_id: str,
        session_id: str | None,
        run_id: str | None,
        error: str,
        duration_ms: int,
    ) -> tuple[RuntimeLearningRecord, RuntimeLearningTrace]:
        assessment = ExecutionOutcomeAssessment(
            outcome_class=OutcomeClass.DEGRADED,
            execution_path="unknown",
            response_was_safe_fallback=False,
            runtime_fallback_reason="learning_assessment_error",
            evaluation_overall=None,
            evaluation_flag_count=0,
            duration_ms=max(0, int(duration_ms)),
            notes=[error[:240]],
        )
        sig = RuntimeFeedbackSignal(
            signal_id=f"{record_id}-sig-err",
            signal_type="learning_assessment_failure",
            source_stage=RuntimeLearningStage.RUNTIME,
            polarity=SignalPolarity.NEGATIVE,
            summary="Learning assessment raised an exception; bounded fallback record.",
            weight=0.2,
            evidence={"error": error[:400]},
        )
        summary = RuntimeLearningSummary(
            headline="Learning assessment failed; degraded record only.",
            positive_signals=0,
            negative_signals=1,
            mixed_signals=0,
            neutral_signals=0,
        )
        record = RuntimeLearningRecord(
            record_id=record_id,
            session_id=session_id,
            run_id=run_id,
            reasoning_trace_id=None,
            planning_trace_id=None,
            plan_id=None,
            assessment=assessment,
            signals=[sig],
            summary=summary,
            persisted=False,
            metadata={"phase": "34", "degraded": True},
        )
        trace = RuntimeLearningTrace.from_record(
            record,
            trace_id=new_learning_trace_id(record_id),
            degraded_assessment=True,
            error=error,
        )
        return record, trace

    def _synthesize(
        self,
        *,
        record_id: str,
        session_id: str | None,
        run_id: str | None,
        message: str,
        response: str,
        reasoning_payload: dict[str, Any],
        memory_context_payload: dict[str, Any],
        planning_payload: dict[str, Any],
        swarm_result: dict[str, Any],
        evaluation: dict[str, Any],
        duration_ms: int,
        last_runtime_reason: str,
        last_runtime_mode: str,
        safe_fallback_response: str,
        direct_memory_hit: bool,
        feedback_bundle: dict[str, Any] | None = None,
    ) -> tuple[RuntimeLearningRecord, RuntimeLearningTrace]:
        _ = swarm_result
        signals: list[RuntimeFeedbackSignal] = []
        rid = record_id

        trace_dict = reasoning_payload.get("trace") if isinstance(reasoning_payload.get("trace"), dict) else {}
        validation = str(trace_dict.get("validation_result", "") or "").lower()
        if validation == "valid":
            signals.append(
                RuntimeFeedbackSignal(
                    signal_id=f"{rid}-sr-reason",
                    signal_type="reasoning_validation",
                    source_stage=RuntimeLearningStage.REASONING,
                    polarity=SignalPolarity.POSITIVE,
                    summary="Reasoning validation reported valid handoff.",
                    weight=0.35,
                    evidence={"validation_result": validation},
                )
            )
        elif validation in {"invalid", "fallback"}:
            signals.append(
                RuntimeFeedbackSignal(
                    signal_id=f"{rid}-sr-reason",
                    signal_type="reasoning_validation",
                    source_stage=RuntimeLearningStage.REASONING,
                    polarity=SignalPolarity.NEGATIVE,
                    summary=f"Reasoning validation outcome: {validation or 'unknown'}.",
                    weight=0.35,
                    evidence={"validation_result": validation},
                )
            )
        else:
            signals.append(
                RuntimeFeedbackSignal(
                    signal_id=f"{rid}-sr-reason",
                    signal_type="reasoning_validation",
                    source_stage=RuntimeLearningStage.REASONING,
                    polarity=SignalPolarity.NEUTRAL,
                    summary="Reasoning validation state not classified.",
                    weight=0.15,
                    evidence={"validation_result": validation},
                )
            )

        mem_count = int(memory_context_payload.get("selected_count", 0) or 0)
        if mem_count > 0:
            signals.append(
                RuntimeFeedbackSignal(
                    signal_id=f"{rid}-sr-mem",
                    signal_type="memory_intelligence_presence",
                    source_stage=RuntimeLearningStage.MEMORY_INTELLIGENCE,
                    polarity=SignalPolarity.POSITIVE,
                    summary=f"Memory intelligence selected {mem_count} contextual signals.",
                    weight=0.25,
                    evidence={"selected_count": mem_count, "sources_used": memory_context_payload.get("sources_used", [])},
                )
            )
        else:
            signals.append(
                RuntimeFeedbackSignal(
                    signal_id=f"{rid}-sr-mem",
                    signal_type="memory_intelligence_presence",
                    source_stage=RuntimeLearningStage.MEMORY_INTELLIGENCE,
                    polarity=SignalPolarity.NEUTRAL,
                    summary="No memory intelligence signals selected for this turn.",
                    weight=0.12,
                    evidence={"selected_count": 0},
                )
            )

        planning_trace_id, plan_id = _planning_ids(planning_payload)
        if planning_payload and isinstance(planning_payload.get("planning_trace"), dict):
            pt = planning_payload["planning_trace"]
            ready = bool(pt.get("execution_ready"))
            degraded = bool(pt.get("degraded"))
            if degraded:
                pol = SignalPolarity.MIXED
                txt = "Planning produced a degraded plan path."
            elif ready:
                pol = SignalPolarity.POSITIVE
                txt = "Planning produced an execution-ready structured plan."
            else:
                pol = SignalPolarity.MIXED
                txt = "Planning completed but plan was not execution-ready."
            signals.append(
                RuntimeFeedbackSignal(
                    signal_id=f"{rid}-sr-plan",
                    signal_type="planning_execution_readiness",
                    source_stage=RuntimeLearningStage.PLANNING,
                    polarity=pol,
                    summary=txt,
                    weight=0.3,
                    evidence={"execution_ready": ready, "degraded": degraded, "step_count": pt.get("step_count")},
                )
            )
        else:
            signals.append(
                RuntimeFeedbackSignal(
                    signal_id=f"{rid}-sr-plan",
                    signal_type="planning_execution_readiness",
                    source_stage=RuntimeLearningStage.PLANNING,
                    polarity=SignalPolarity.NEUTRAL,
                    summary="No planning intelligence payload attached to this turn.",
                    weight=0.1,
                    evidence={},
                )
            )

        response_was_fb = response.strip() == safe_fallback_response.strip()
        if response_was_fb:
            signals.append(
                RuntimeFeedbackSignal(
                    signal_id=f"{rid}-sr-exec",
                    signal_type="execution_response_quality",
                    source_stage=RuntimeLearningStage.EXECUTION,
                    polarity=SignalPolarity.NEGATIVE,
                    summary="Assistant response matched safe fallback template.",
                    weight=0.45,
                    evidence={"path": "direct_memory" if direct_memory_hit else "swarm"},
                )
            )
        else:
            overall = evaluation.get("overall")
            overall_f = float(overall) if isinstance(overall, (int, float)) else None
            flags = evaluation.get("flags") if isinstance(evaluation.get("flags"), list) else []
            flag_n = len(flags)
            if overall_f is not None and overall_f < 0.42:
                pol = SignalPolarity.MIXED
                summ = f"Heuristic evaluation overall low ({overall_f:.2f})."
            elif flag_n >= 2:
                pol = SignalPolarity.MIXED
                summ = "Evaluation reported multiple quality flags."
            else:
                pol = SignalPolarity.POSITIVE
                summ = "Execution produced a non-fallback response with acceptable evaluation heuristics."
            signals.append(
                RuntimeFeedbackSignal(
                    signal_id=f"{rid}-sr-exec",
                    signal_type="execution_response_quality",
                    source_stage=RuntimeLearningStage.EXECUTION,
                    polarity=pol,
                    summary=summ,
                    weight=0.4,
                    evidence={"overall": overall_f, "flags": flags[:8], "path": "direct_memory" if direct_memory_hit else "swarm"},
                )
            )

        if duration_ms > 60_000:
            signals.append(
                RuntimeFeedbackSignal(
                    signal_id=f"{rid}-sr-lat",
                    signal_type="latency_budget",
                    source_stage=RuntimeLearningStage.RUNTIME,
                    polarity=SignalPolarity.MIXED,
                    summary="Turn duration exceeded 60s (bounded latency signal).",
                    weight=0.15,
                    evidence={"duration_ms": duration_ms},
                )
            )
        elif duration_ms > 0:
            signals.append(
                RuntimeFeedbackSignal(
                    signal_id=f"{rid}-sr-lat",
                    signal_type="latency_budget",
                    source_stage=RuntimeLearningStage.RUNTIME,
                    polarity=SignalPolarity.NEUTRAL,
                    summary="Turn duration within expected observation window.",
                    weight=0.08,
                    evidence={"duration_ms": duration_ms},
                )
            )

        if last_runtime_reason in {"empty_swarm_response"} or last_runtime_mode == "fallback":
            signals.append(
                RuntimeFeedbackSignal(
                    signal_id=f"{rid}-sr-rt",
                    signal_type="runtime_fallback_indicator",
                    source_stage=RuntimeLearningStage.RUNTIME,
                    polarity=SignalPolarity.NEGATIVE,
                    summary=f"Runtime indicated fallback (mode={last_runtime_mode}, reason={last_runtime_reason}).",
                    weight=0.25,
                    evidence={"last_runtime_mode": last_runtime_mode, "last_runtime_reason": last_runtime_reason},
                )
            )

        if isinstance(feedback_bundle, dict) and feedback_bundle:
            fb_cls = str(feedback_bundle.get("feedback_class", "") or "")
            fb_src = str(feedback_bundle.get("feedback_source", "") or "")
            if fb_cls == "negative":
                signals.append(
                    RuntimeFeedbackSignal(
                        signal_id=f"{rid}-sr-fb41",
                        signal_type="phase41_user_feedback",
                        source_stage=RuntimeLearningStage.RUNTIME,
                        polarity=SignalPolarity.NEGATIVE,
                        summary="User or implicit feedback indicated dissatisfaction.",
                        weight=0.35,
                        evidence={"feedback_class": fb_cls, "feedback_source": fb_src},
                    )
                )
            elif fb_cls == "positive":
                signals.append(
                    RuntimeFeedbackSignal(
                        signal_id=f"{rid}-sr-fb41",
                        signal_type="phase41_user_feedback",
                        source_stage=RuntimeLearningStage.RUNTIME,
                        polarity=SignalPolarity.POSITIVE,
                        summary="User or implicit feedback indicated satisfaction.",
                        weight=0.25,
                        evidence={"feedback_class": fb_cls, "feedback_source": fb_src},
                    )
                )

        neg = sum(1 for s in signals if s.polarity == SignalPolarity.NEGATIVE)
        pos = sum(1 for s in signals if s.polarity == SignalPolarity.POSITIVE)
        mix = sum(1 for s in signals if s.polarity == SignalPolarity.MIXED)

        if response_was_fb or neg >= 2:
            oclass = OutcomeClass.FAILURE
        elif mix >= 2 or neg == 1 or last_runtime_reason == "empty_swarm_response":
            oclass = OutcomeClass.DEGRADED
        else:
            oclass = OutcomeClass.SUCCESS

        assessment = ExecutionOutcomeAssessment(
            outcome_class=oclass,
            execution_path="direct_memory" if direct_memory_hit else "swarm",
            response_was_safe_fallback=response_was_fb,
            runtime_fallback_reason=str(last_runtime_reason or "").strip(),
            evaluation_overall=float(evaluation["overall"]) if isinstance(evaluation.get("overall"), (int, float)) else None,
            evaluation_flag_count=len(evaluation.get("flags", []) or []) if isinstance(evaluation.get("flags"), list) else 0,
            duration_ms=max(0, int(duration_ms)),
            notes=[f"message_len={len(message)}", f"response_len={len(response)}"],
        )

        summary = RuntimeLearningSummary(
            headline=f"Outcome={oclass.value}; signals={len(signals)} (+{pos}/-{neg}/~{mix}).",
            positive_signals=pos,
            negative_signals=neg,
            mixed_signals=mix,
            neutral_signals=sum(1 for s in signals if s.polarity == SignalPolarity.NEUTRAL),
        )

        reasoning_tid = _trace_id_from_handoff(reasoning_payload)
        fb_meta: dict[str, Any] = {}
        if isinstance(feedback_bundle, dict) and feedback_bundle:
            fb_meta["phase41_feedback"] = {
                "feedback_class": str(feedback_bundle.get("feedback_class", "") or "")[:32],
                "feedback_source": str(feedback_bundle.get("feedback_source", "") or "")[:16],
                "implicit_tags": feedback_bundle.get("implicit_tags")
                if isinstance(feedback_bundle.get("implicit_tags"), list)
                else [],
                "explicit": feedback_bundle.get("explicit")
                if isinstance(feedback_bundle.get("explicit"), dict)
                else {},
            }

        record = RuntimeLearningRecord(
            record_id=rid,
            session_id=session_id,
            run_id=run_id or None,
            reasoning_trace_id=reasoning_tid,
            planning_trace_id=planning_trace_id,
            plan_id=plan_id,
            assessment=assessment,
            signals=signals,
            summary=summary,
            persisted=False,
            metadata={"phase": "34", "message_preview": message[:120], **fb_meta},
        )

        persisted = self._store.append_record(record.as_dict())
        record = RuntimeLearningRecord(
            record_id=record.record_id,
            session_id=record.session_id,
            run_id=record.run_id,
            reasoning_trace_id=record.reasoning_trace_id,
            planning_trace_id=record.planning_trace_id,
            plan_id=record.plan_id,
            assessment=record.assessment,
            signals=record.signals,
            summary=record.summary,
            persisted=persisted,
            metadata={**record.metadata, "persistence_path": str(self._store.path)},
        )

        trace = RuntimeLearningTrace.from_record(
            record,
            trace_id=new_learning_trace_id(rid),
            degraded_assessment=False,
            error="",
        )
        return record, trace
