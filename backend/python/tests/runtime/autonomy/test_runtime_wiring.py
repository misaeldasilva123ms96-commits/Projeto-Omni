"""Tests for the runtime wiring of the Autonomy Controller.

Verifies that:
- Autonomy context is built safely from inspection data
- The orchestrator calls the controller in advisory mode
- CONTINUE decision does not change runtime behavior
- ESCALATE_TO_MISAEL is recorded but does not execute
- SELF_REPAIR and SWITCH_PROVIDER are not executed
- Autonomy evaluation failure degrades safely
- Autonomy event emission failure degrades safely
- No raw prompt/response/secrets in autonomy context
- Existing runtime behavior is preserved
"""

from __future__ import annotations

import unittest
from typing import Any

import brain.runtime.autonomy.runtime_wiring as runtime_wiring
from brain.runtime.autonomy.runtime_wiring import (
    _get_controller,
    build_autonomy_context,
    evaluate_autonomy,
    evaluate_and_attach,
    reset_controller_for_testing,
)
from brain.runtime.autonomy import AutonomyContext, DecisionType


SAFE_FALLBACK = "Nao consegui processar isso ainda, mas estou aprendendo."


class _StaticPlan:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def as_dict(self) -> dict[str, Any]:
        return dict(self._payload)


class _SpyDryRunReplanPlanner:
    def __init__(self, payload: dict[str, Any] | None = None) -> None:
        self.calls = 0
        self.payload = payload or {
            "plan_id": "dry-replan-test",
            "plan_type": "dry_run_replan",
            "advisory": True,
            "would_replan": False,
            "replan_reason": "not_replan_decision",
            "blocked": False,
            "block_reasons": [],
            "replan_eligibility_score": 0,
            "risk_level": "low",
            "source_decision": "CONTINUE",
            "fingerprint_id": "",
            "stagnation_score": 0,
            "progress_score": 0,
            "repeated_strategy_count": 0,
            "suggested_strategy": "",
            "evidence_summary": "",
            "created_at": "2026-06-28T00:00:00Z",
        }

    def plan(self, **_: Any) -> _StaticPlan:
        self.calls += 1
        return _StaticPlan(self.payload)


class _FailingDryRunReplanPlanner:
    def plan(self, **_: Any) -> _StaticPlan:
        raise RuntimeError("planner failed")


class _RecordingMemoryFacade:
    backend = "jsonl"
    sqlite_enabled = False

    def __init__(self) -> None:
        self.records: list[Any] = []

    def record_dry_run_replan_plan_evidence(self, record: Any) -> None:
        self.records.append(record)


class _FailingMemoryFacade:
    backend = "sqlite"
    sqlite_enabled = True

    def record_dry_run_replan_plan_evidence(self, record: Any) -> None:
        raise RuntimeError("raw_prompt secret should not leak")


def _make_inspection(
    *,
    runtime_mode: str = "",
    failure_class: str = "",
    failure_reason: str = "",
    fallback_triggered: bool = False,
    provider_failed: bool = False,
    provider_actual: str = "",
) -> dict[str, Any]:
    signals: dict[str, Any] = {}
    if runtime_mode:
        signals["runtime_mode"] = runtime_mode
    if failure_class:
        signals["failure_class"] = failure_class
    if failure_reason:
        signals["failure_reason"] = failure_reason
    if fallback_triggered:
        signals["fallback_triggered"] = True
    if provider_failed:
        signals["provider_failed"] = True
    if provider_actual:
        signals["provider_actual"] = provider_actual
    return {"signals": signals, "runtime_mode": runtime_mode}


class BuildAutonomyContextTest(unittest.TestCase):
    def test_empty_inspection(self) -> None:
        ctx = build_autonomy_context(None, "s1", "ok")
        self.assertEqual(ctx.session_id, "s1")
        self.assertEqual(ctx.error_type, "")
        self.assertEqual(ctx.error_count, 0)
        self.assertFalse(ctx.no_safe_next_action)

    def test_empty_dict_inspection(self) -> None:
        ctx = build_autonomy_context({}, "s1", "ok")
        self.assertEqual(ctx.session_id, "s1")

    def test_no_signals(self) -> None:
        inspection: dict[str, Any] = {"other": "data"}
        ctx = build_autonomy_context(inspection, "s1", "ok")
        self.assertEqual(ctx.error_type, "")

    def test_failure_class_sets_error_type(self) -> None:
        inspection = _make_inspection(failure_class="provider_timeout")
        ctx = build_autonomy_context(inspection, "s1", "ok")
        self.assertEqual(ctx.error_type, "provider_timeout")
        self.assertEqual(ctx.error_count, 1)

    def test_failure_reason_fallback(self) -> None:
        inspection = _make_inspection(failure_reason="node_crash")
        ctx = build_autonomy_context(inspection, "s1", "ok")
        self.assertEqual(ctx.error_type, "node_crash")
        self.assertEqual(ctx.error_count, 1)

    def test_failure_class_takes_priority(self) -> None:
        inspection = _make_inspection(
            failure_class="provider_timeout",
            failure_reason="node_crash",
        )
        ctx = build_autonomy_context(inspection, "s1", "ok")
        self.assertEqual(ctx.error_type, "provider_timeout")

    def test_runtime_mode_fallback_sets_error(self) -> None:
        inspection = _make_inspection(runtime_mode="safe_fallback")
        ctx = build_autonomy_context(inspection, "s1", "ok")
        self.assertEqual(ctx.error_type, "safe_fallback")
        self.assertEqual(ctx.error_count, 1)

    def test_runtime_mode_provider_failure_sets_error(self) -> None:
        inspection = _make_inspection(runtime_mode="provider_failure")
        ctx = build_autonomy_context(inspection, "s1", "ok")
        self.assertEqual(ctx.error_type, "provider_failure")

    def test_runtime_mode_node_fallback_sets_error(self) -> None:
        inspection = _make_inspection(runtime_mode="node_fallback")
        ctx = build_autonomy_context(inspection, "s1", "ok")
        self.assertEqual(ctx.error_type, "node_fallback")

    def test_safe_fallback_response_sets_no_safe_next_action(self) -> None:
        ctx = build_autonomy_context({"signals": {}}, "s1", SAFE_FALLBACK)
        self.assertTrue(ctx.no_safe_next_action)

    def test_provider_failed_metadata(self) -> None:
        inspection = _make_inspection(
            provider_failed=True,
            provider_actual="openai",
        )
        ctx = build_autonomy_context(inspection, "s1", "ok")
        self.assertEqual(ctx.metadata.get("provider_failure_type"), "openai")

    def test_runtime_mode_in_metadata(self) -> None:
        inspection = _make_inspection(runtime_mode="standard")
        ctx = build_autonomy_context(inspection, "s1", "ok")
        self.assertEqual(ctx.metadata.get("runtime_mode"), "standard")

    def test_no_raw_prompt_or_response_in_context(self) -> None:
        inspection = _make_inspection(runtime_mode="standard")
        ctx = build_autonomy_context(inspection, "s1", "user message here")
        ctx_dict = ctx.as_dict()
        as_text = str(ctx_dict)
        self.assertNotIn("raw_prompt", as_text)
        self.assertNotIn("raw_response", as_text)
        self.assertNotIn("api_key", as_text)

    def test_no_secrets_in_context(self) -> None:
        inspection = _make_inspection(runtime_mode="standard")
        ctx = build_autonomy_context(inspection, "s1", "ok")
        ctx_dict = ctx.as_dict()
        values_text = str(list(ctx_dict.values()))
        for secret_key in ("api_key", "token", "password"):
            self.assertNotIn(secret_key, values_text)


class EvaluateAutonomyTest(unittest.TestCase):
    def setUp(self) -> None:
        reset_controller_for_testing()

    def test_continue_decision_on_success(self) -> None:
        inspection = _make_inspection(runtime_mode="standard")
        result = evaluate_autonomy(inspection, "s1", "good response")
        self.assertEqual(result["decision"], DecisionType.CONTINUE.value)
        self.assertTrue(result["advisory"])
        self.assertEqual(result["session_id"], "s1")

    def test_escalate_on_fallback_response(self) -> None:
        inspection = _make_inspection(runtime_mode="standard")
        result = evaluate_autonomy(inspection, "s1", SAFE_FALLBACK)
        self.assertEqual(result["decision"], DecisionType.ABORT_SAFE.value)

    def test_retry_on_failure_class(self) -> None:
        inspection = _make_inspection(failure_class="timeout")
        result = evaluate_autonomy(inspection, "s1", "ok")
        self.assertEqual(result["decision"], DecisionType.RETRY.value)

    def test_provider_failure_retry_in_advisory_mode(self) -> None:
        inspection = _make_inspection(
            failure_class="provider_timeout",
            runtime_mode="provider_failure",
        )
        result = evaluate_autonomy(inspection, "s1", "ok")
        self.assertEqual(result["decision"], DecisionType.RETRY.value)
        self.assertTrue(result["advisory"])

    def test_advisory_flag_always_true(self) -> None:
        for runtime_mode in ("standard", "safe_fallback", "provider_failure"):
            inspection = _make_inspection(runtime_mode=runtime_mode)
            result = evaluate_autonomy(inspection, "s1", "test")
            self.assertTrue(result["advisory"], f"Failed for {runtime_mode}")

    def test_evaluate_none_inspection(self) -> None:
        result = evaluate_autonomy(None, "s1", "test")
        self.assertEqual(result["decision"], DecisionType.CONTINUE.value)

    def test_result_has_required_keys(self) -> None:
        result = evaluate_autonomy({}, "s1", "test")
        for key in ("decision", "advisory", "reason", "risk_level", "session_id"):
            self.assertIn(key, result)

    def test_result_includes_read_only_dry_run_retry_plan(self) -> None:
        inspection = _make_inspection(failure_class="timeout")
        result = evaluate_autonomy(inspection, "s1", "ok")

        plan = result.get("dry_run_retry_plan")
        self.assertIsInstance(plan, dict)
        self.assertEqual(plan.get("plan_type"), "dry_run_retry")
        self.assertTrue(plan.get("advisory"))
        self.assertEqual(plan.get("source_decision"), DecisionType.RETRY.value)

    def test_dry_run_retry_plan_does_not_change_response_or_provider(self) -> None:
        inspection = _make_inspection(failure_class="timeout", provider_actual="openai")
        response = "stable runtime response"
        result = evaluate_autonomy(inspection, "s1", response)

        self.assertEqual(response, "stable runtime response")
        plan_text = str(result.get("dry_run_retry_plan", {})).lower()
        self.assertNotIn("provider_call", plan_text)
        self.assertNotIn("model_call", plan_text)
        self.assertNotIn("execute_retry", plan_text)
        self.assertNotIn("raw_response", plan_text)

    def test_result_includes_read_only_dry_run_replan_plan(self) -> None:
        inspection = _make_inspection(failure_class="timeout")
        result = evaluate_autonomy(inspection, "s1", "ok")

        plan = result.get("dry_run_replan_plan")
        self.assertIsInstance(plan, dict)
        self.assertEqual(plan.get("plan_type"), "dry_run_replan")
        self.assertTrue(plan.get("advisory"))
        self.assertIn("would_replan", plan)
        self.assertIn("suggested_strategy", plan)

    def test_dry_run_replan_plan_does_not_change_response_prompt_or_provider(self) -> None:
        inspection = _make_inspection(failure_class="timeout", provider_actual="openai")
        response = "stable runtime response"
        inspection_before = dict(inspection)
        planner = _SpyDryRunReplanPlanner()

        result = evaluate_autonomy(
            inspection,
            "s1",
            response,
            dry_run_replan_planner=planner,  # type: ignore[arg-type]
        )

        self.assertEqual(response, "stable runtime response")
        self.assertEqual(inspection, inspection_before)
        self.assertEqual(planner.calls, 1)
        plan_text = str(result.get("dry_run_replan_plan", {})).lower()
        self.assertNotIn("prompt_rewrite", plan_text)
        self.assertNotIn("rewritten_prompt", plan_text)
        self.assertNotIn("provider_call", plan_text)
        self.assertNotIn("model_call", plan_text)
        self.assertNotIn("raw_response", plan_text)

    def test_dry_run_replan_evidence_is_recorded_when_plan_exists(self) -> None:
        facade = _RecordingMemoryFacade()
        original_get_memory_facade = runtime_wiring._get_memory_facade
        runtime_wiring._get_memory_facade = lambda: facade  # type: ignore[assignment]
        try:
            result = evaluate_autonomy(
                _make_inspection(failure_class="timeout"),
                "session-1",
                "stable response",
            )
        finally:
            runtime_wiring._get_memory_facade = original_get_memory_facade  # type: ignore[assignment]

        self.assertEqual(len(facade.records), 1)
        record_payload = facade.records[0].as_dict()
        self.assertEqual(record_payload["event_type"], "dry_run_replan_plan_evidence")
        self.assertEqual(record_payload["session_id"], "session-1")
        self.assertNotIn("raw_prompt", str(record_payload))
        diagnostic = result["dry_run_replan_plan_persistence"]
        self.assertTrue(diagnostic["attempted"])
        self.assertTrue(diagnostic["recorded"])
        self.assertFalse(diagnostic["degraded"])
        self.assertEqual(diagnostic["event_type"], "dry_run_replan_plan_evidence")

    def test_no_replan_evidence_record_attempted_when_plan_missing(self) -> None:
        facade = _RecordingMemoryFacade()
        original_get_memory_facade = runtime_wiring._get_memory_facade
        runtime_wiring._get_memory_facade = lambda: facade  # type: ignore[assignment]
        try:
            result = evaluate_autonomy(
                _make_inspection(failure_class="timeout"),
                "session-1",
                "stable response",
                dry_run_replan_planner=_FailingDryRunReplanPlanner(),  # type: ignore[arg-type]
            )
        finally:
            runtime_wiring._get_memory_facade = original_get_memory_facade  # type: ignore[assignment]

        self.assertEqual(facade.records, [])
        diagnostic = result["dry_run_replan_plan_persistence"]
        self.assertFalse(diagnostic["attempted"])
        self.assertFalse(diagnostic["recorded"])
        self.assertFalse(diagnostic["degraded"])

    def test_replan_evidence_persistence_failure_degrades_safely(self) -> None:
        original_get_memory_facade = runtime_wiring._get_memory_facade
        runtime_wiring._get_memory_facade = lambda: _FailingMemoryFacade()  # type: ignore[assignment]
        response = "stable runtime response"
        try:
            result = evaluate_autonomy(
                _make_inspection(failure_class="timeout", provider_actual="openai"),
                "session-1",
                response,
            )
        finally:
            runtime_wiring._get_memory_facade = original_get_memory_facade  # type: ignore[assignment]

        self.assertEqual(response, "stable runtime response")
        diagnostic = result["dry_run_replan_plan_persistence"]
        self.assertTrue(diagnostic["attempted"])
        self.assertFalse(diagnostic["recorded"])
        self.assertTrue(diagnostic["degraded"])
        self.assertEqual(diagnostic["error_category"], "record_failed")
        diagnostic_text = str(diagnostic).lower()
        self.assertNotIn("raw_prompt", diagnostic_text)
        self.assertNotIn("secret", diagnostic_text)
        self.assertNotIn("traceback", diagnostic_text)

    def test_replan_persistence_diagnostics_are_safe_metadata_only(self) -> None:
        facade = _RecordingMemoryFacade()
        original_get_memory_facade = runtime_wiring._get_memory_facade
        runtime_wiring._get_memory_facade = lambda: facade  # type: ignore[assignment]
        try:
            result = evaluate_autonomy(
                _make_inspection(failure_class="timeout"),
                "session-1",
                "stable response",
            )
        finally:
            runtime_wiring._get_memory_facade = original_get_memory_facade  # type: ignore[assignment]

        diagnostic = result["dry_run_replan_plan_persistence"]
        self.assertEqual(
            set(diagnostic.keys()),
            {
                "attempted",
                "recorded",
                "degraded",
                "error_category",
                "event_type",
                "storage_mode",
                "sqlite_enabled",
                "recorded_at",
            },
        )
        diagnostic_text = str(diagnostic).lower()
        for forbidden in (
            "prompt",
            "rewritten",
            "response",
            "provider_payload",
            "tool_output",
            "api_key",
            "token",
            "secret",
        ):
            self.assertNotIn(forbidden, diagnostic_text)


class EvaluateAndAttachTest(unittest.TestCase):
    def setUp(self) -> None:
        reset_controller_for_testing()

    def test_attaches_to_inspection_dict(self) -> None:
        inspection: dict[str, Any] = {"signals": {}}
        evaluate_and_attach(inspection, "s1", "good response")
        self.assertIn("autonomy_evaluation", inspection)
        self.assertEqual(
            inspection["autonomy_evaluation"]["decision"],
            DecisionType.CONTINUE.value,
        )
        self.assertTrue(inspection["autonomy_evaluation"]["advisory"])

    def test_attaches_controller_stats_to_inspection(self) -> None:
        inspection: dict[str, Any] = {"signals": {}}
        evaluate_and_attach(inspection, "s1", "good response")
        self.assertIn("autonomy_controller_stats", inspection)
        stats = inspection["autonomy_controller_stats"]
        self.assertEqual(stats["total_evaluations"], 1)
        self.assertIn("decisions_by_type", stats)
        self.assertIn("last_decision", stats)
        self.assertTrue(stats["advisory_mode_enabled"])
        self.assertIn("active_session_count", stats)

    def test_attaches_read_only_autonomy_evidence_payload(self) -> None:
        inspection: dict[str, Any] = {"signals": {}}
        evaluate_and_attach(inspection, "s1", "good response")
        self.assertIn("autonomy_evidence", inspection)
        evidence = inspection["autonomy_evidence"]
        self.assertTrue(evidence["read_only"])
        self.assertEqual(evidence["mode"], "advisory-only")
        self.assertIn("summary", evidence)

    def test_controller_stats_escalation(self) -> None:
        inspection: dict[str, Any] = {"signals": {}}
        safe_fallback = "Nao consegui processar isso ainda, mas estou aprendendo."
        evaluate_and_attach(inspection, "s1", safe_fallback)
        self.assertIn("autonomy_controller_stats", inspection)
        stats = inspection["autonomy_controller_stats"]
        self.assertEqual(stats["total_evaluations"], 1)
        self.assertEqual(stats["abort_safe_count"], 1)

    def test_does_not_modify_when_no_inspection(self) -> None:
        evaluate_and_attach(None, "s1", "good response")

    def test_does_not_raise_on_failure(self) -> None:
        evaluate_and_attach(42, "s1", "good response")

    def test_does_not_change_runtime_behavior(self) -> None:
        inspection: dict[str, Any] = {"signals": {}}
        before = dict(inspection)
        evaluate_and_attach(inspection, "s1", "good response")
        for key, value in before.items():
            self.assertEqual(inspection[key], value)

    def test_escalate_recorded_but_not_executed(self) -> None:
        inspection: dict[str, Any] = {"signals": {}}
        evaluate_and_attach(inspection, "s1", SAFE_FALLBACK)
        self.assertIn("autonomy_evaluation", inspection)
        eval_result = inspection["autonomy_evaluation"]
        self.assertEqual(eval_result["decision"], DecisionType.ABORT_SAFE.value)
        self.assertTrue(eval_result["advisory"])

    def test_attaches_dry_run_retry_plan_to_inspection(self) -> None:
        inspection = _make_inspection(failure_class="timeout")
        evaluate_and_attach(inspection, "s1", "ok")

        plan = inspection["autonomy_evaluation"]["dry_run_retry_plan"]
        self.assertEqual(plan["plan_type"], "dry_run_retry")
        self.assertTrue(plan["advisory"])
        self.assertEqual(plan["source_decision"], DecisionType.RETRY.value)
        self.assertNotIn("raw_prompt", str(plan))

    def test_attaches_dry_run_replan_plan_to_inspection(self) -> None:
        inspection = _make_inspection(failure_class="timeout")
        evaluate_and_attach(inspection, "s1", "ok")

        plan = inspection["autonomy_evaluation"]["dry_run_replan_plan"]
        self.assertEqual(plan["plan_type"], "dry_run_replan")
        self.assertTrue(plan["advisory"])
        self.assertNotIn("raw_prompt", str(plan))
        self.assertNotIn("rewritten_prompt", str(plan))


class SafetyDegradationTest(unittest.TestCase):
    def test_evaluation_failure_does_not_raise(self) -> None:
        try:
            evaluate_and_attach(None, "s1", "test")
        except Exception:
            self.fail("evaluate_and_attach raised unexpectedly")

    def test_controller_internal_failure_safe(self) -> None:
        try:
            _ = evaluate_autonomy(None, "s1", "test")
        except Exception:
            self.fail("evaluate_autonomy raised unexpectedly")

    def test_reset_controller_does_not_break(self) -> None:
        reset_controller_for_testing()
        result = evaluate_autonomy({}, "s1", "test")
        self.assertIsNotNone(result)


class OrchestratorIntegrationGuardTest(unittest.TestCase):
    def test_import_guard_present(self) -> None:
        from brain.runtime import orchestrator

        self.assertTrue(hasattr(orchestrator, "_AUTONOMY_AVAILABLE"))
        self.assertTrue(orchestrator._AUTONOMY_AVAILABLE)

    def test_evaluate_and_attach_available(self) -> None:
        from brain.runtime import orchestrator

        self.assertTrue(hasattr(orchestrator, "evaluate_and_attach"))
        self.assertTrue(callable(orchestrator.evaluate_and_attach))

    def test_orchestrator_run_accesses_autonomy(self) -> None:
        import inspect

        from brain.runtime import orchestrator

        source = inspect.getsource(orchestrator.BrainOrchestrator.run)
        self.assertIn("_AUTONOMY_AVAILABLE", source)
        self.assertIn("evaluate_and_attach", source)
        self.assertIn("last_cognitive_runtime_inspection", source)


class NoAutonomousActionTest(unittest.TestCase):
    def test_self_repair_not_executed(self) -> None:
        from brain.runtime.autonomy import DISABLED_DECISIONS, DecisionType

        self.assertIn(DecisionType.SELF_REPAIR, DISABLED_DECISIONS)

    def test_switch_provider_not_executed(self) -> None:
        from brain.runtime.autonomy import DISABLED_DECISIONS, DecisionType

        self.assertIn(DecisionType.SWITCH_PROVIDER, DISABLED_DECISIONS)

    def test_no_execution_path_in_autonomy_result(self) -> None:
        result = evaluate_autonomy(None, "s1", "test")
        for exec_key in ("execute", "action", "patch", "commit", "push", "merge"):
            self.assertNotIn(exec_key, result.get("decision", "").lower())


class ContextSanitizationTest(unittest.TestCase):
    def test_context_excludes_raw_prompt(self) -> None:
        ctx = AutonomyContext(
            session_id="s1",
            metadata={"safe": "data"},
        )
        as_text = str(ctx.as_dict())
        self.assertNotIn("raw_prompt", as_text)

    def test_context_excludes_auth_tokens(self) -> None:
        ctx = AutonomyContext(session_id="s1")
        as_text = str(ctx.as_dict())
        for secret in ("api_key", "auth_token", "authorization"):
            self.assertNotIn(secret, as_text)

    def test_context_excludes_provider_credentials(self) -> None:
        ctx = AutonomyContext(session_id="s1")
        values_text = str(list(ctx.as_dict().values()))
        for cred in ("credential", "password"):
            self.assertNotIn(cred, values_text)

    def test_context_excludes_stack_traces(self) -> None:
        ctx = AutonomyContext(session_id="s1")
        as_text = str(ctx.as_dict())
        self.assertNotIn("traceback", as_text)
        self.assertNotIn("stack", as_text)

    def test_metadata_only_safe_fields(self) -> None:
        ctx = AutonomyContext(
            session_id="s1",
            metadata={"runtime_mode": "standard", "fallback_triggered": "False"},
        )
        meta = ctx.metadata
        self.assertIn("runtime_mode", meta)
        self.assertNotIn("raw_prompt", meta)
        self.assertNotIn("api_key", meta)


if __name__ == "__main__":
    unittest.main()
