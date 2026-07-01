from __future__ import annotations

import json
import unittest
from pathlib import Path

from brain.memory.historical_audit_route_controls import (
    HISTORICAL_AUDIT_READONLY_CAPABILITY,
    HistoricalAuditCallerIdentity,
    HistoricalAuditControlDecision,
    HistoricalAuditRouteControlConfig,
    authorize_historical_audit_readonly,
    build_historical_audit_route_audit_event,
    build_historical_audit_route_observability_fields,
    check_historical_audit_route_enabled,
    extract_historical_audit_caller_from_supabase_sub,
    validate_historical_audit_detail_query_complexity,
    validate_historical_audit_list_query_complexity,
)


class HistoricalDryRunAuditRouteControlsTests(unittest.TestCase):
    def test_auth_missing_fails_closed(self) -> None:
        caller, decision = extract_historical_audit_caller_from_supabase_sub("")

        self.assertIsNone(caller)
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.status_code, 401)

    def test_invalid_auth_caller_fails_closed(self) -> None:
        caller, decision = extract_historical_audit_caller_from_supabase_sub(
            "Bearer sk-secret-token"
        )

        self.assertIsNone(caller)
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "invalid_caller_identity")

    def test_unauthorized_caller_fails_closed(self) -> None:
        decision = authorize_historical_audit_readonly(
            HistoricalAuditCallerIdentity("user-123"),
            [],
            HistoricalAuditRouteControlConfig(route_enabled=True),
        )

        self.assertFalse(decision.allowed)
        self.assertEqual(decision.status_code, 403)

    def test_missing_historical_audit_readonly_capability_fails_closed(self) -> None:
        decision = authorize_historical_audit_readonly(
            HistoricalAuditCallerIdentity("user-123"),
            ["runtime:read"],
            HistoricalAuditRouteControlConfig(route_enabled=True),
        )

        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "missing_historical_audit_readonly_capability")

    def test_authorized_caller_passes_control_helper_only(self) -> None:
        decision = authorize_historical_audit_readonly(
            HistoricalAuditCallerIdentity("user-123"),
            [HISTORICAL_AUDIT_READONLY_CAPABILITY],
            HistoricalAuditRouteControlConfig(route_enabled=True),
        )

        self.assertTrue(decision.allowed)
        self.assertEqual(decision.reason, "historical_audit_readonly_authorized")

    def test_route_enabled_switch_defaults_disabled(self) -> None:
        config = HistoricalAuditRouteControlConfig.default()

        self.assertFalse(config.route_enabled)
        self.assertFalse(check_historical_audit_route_enabled(config).allowed)

    def test_disabled_switch_fails_closed(self) -> None:
        decision = authorize_historical_audit_readonly(
            HistoricalAuditCallerIdentity("user-123"),
            [HISTORICAL_AUDIT_READONLY_CAPABILITY],
        )

        self.assertFalse(decision.allowed)
        self.assertEqual(decision.status_code, 404)
        self.assertEqual(decision.reason, "route_disabled")

    def test_rate_limit_config_is_bounded_deterministic(self) -> None:
        config = HistoricalAuditRouteControlConfig(
            rate_limit_max_requests=10_000,
            rate_limit_window_seconds=100_000,
        )

        self.assertEqual(config.rate_limit_max_requests, 300)
        self.assertEqual(config.rate_limit_window_seconds, 3_600)
        self.assertEqual(config.as_dict()["rate_limit_max_requests"], 300)

    def test_size_limit_config_is_bounded_deterministic(self) -> None:
        config = HistoricalAuditRouteControlConfig(
            max_query_params=999,
            max_param_length=999,
            max_plan_id_length=999,
            max_page_size=999,
            max_offset=99_999,
        )

        self.assertLessEqual(config.max_query_params, 24)
        self.assertLessEqual(config.max_param_length, 160)
        self.assertLessEqual(config.max_plan_id_length, 128)
        self.assertLessEqual(config.max_page_size, 100)
        self.assertLessEqual(config.max_offset, 10_000)

    def test_query_complexity_guard_rejects_excessive_filters_pagination_and_sort(self) -> None:
        filter_heavy = {
            "plan_type": "dry_run_retry",
            "event_type": "event",
            "source_decision": "CONTINUE",
        }
        config = HistoricalAuditRouteControlConfig(route_enabled=True, max_filters=2)

        self.assertFalse(
            validate_historical_audit_list_query_complexity(filter_heavy, config).allowed
        )
        self.assertFalse(
            validate_historical_audit_list_query_complexity(
                {"limit": "101"}, HistoricalAuditRouteControlConfig(route_enabled=True)
            ).allowed
        )
        self.assertFalse(
            validate_historical_audit_list_query_complexity(
                {"sort_by": "raw_sql"}, HistoricalAuditRouteControlConfig(route_enabled=True)
            ).allowed
        )

    def test_detail_complexity_rejects_invalid_plan_id(self) -> None:
        result = validate_historical_audit_detail_query_complexity("../secret.env")

        self.assertFalse(result.allowed)
        self.assertEqual(result.reason, "invalid_plan_id")

    def test_safe_audit_event_schema_excludes_forbidden_fields(self) -> None:
        event = build_historical_audit_route_audit_event(
            HistoricalAuditCallerIdentity("user-123"),
            HistoricalAuditControlDecision(True, "allowed", 200),
            operation_name="list",
            query_summary={
                "limit": 25,
                "raw_sql": "select * from audit",
                "authorization": "Bearer sk-secret-token",
                "prompt": "raw prompt",
                "provider_payload": {"token": "secret"},
            },
            config=HistoricalAuditRouteControlConfig(route_enabled=True),
        )

        serialized = json.dumps(event, sort_keys=True).lower()
        self.assertEqual(set(event), {
            "event_type",
            "route_id",
            "operation_name",
            "caller_id",
            "caller_source",
            "decision_allowed",
            "decision_reason",
            "status_code",
            "query_keys",
            "page_size",
            "safe_audit_logging_enabled",
            "warnings",
            "generated_at",
        })
        self.assert_forbidden_markers_absent(serialized)

    def test_safe_observability_schema_excludes_forbidden_fields(self) -> None:
        fields = build_historical_audit_route_observability_fields(
            HistoricalAuditControlDecision(False, "route_disabled", 404),
            operation_name="detail provider_payload stdout raw_jsonl",
            latency_ms=90_000,
        )

        serialized = json.dumps(fields, sort_keys=True).lower()
        self.assertEqual(set(fields), {
            "route_id",
            "operation_name",
            "decision_allowed",
            "decision_reason",
            "status_code",
            "route_enabled",
            "rate_limit_max_requests",
            "rate_limit_window_seconds",
            "safe_observability_enabled",
            "latency_ms",
        })
        self.assertEqual(fields["latency_ms"], 60_000)
        self.assert_forbidden_markers_absent(serialized)

    def test_no_raw_jsonl_sqlite_sql_prompt_provider_or_tool_output_exposure(self) -> None:
        event = build_historical_audit_route_audit_event(
            HistoricalAuditCallerIdentity("user-123"),
            HistoricalAuditControlDecision(False, "missing_historical_audit_readonly_capability", 403),
            operation_name="list",
            query_summary={
                "request_id": "raw_jsonl sqlite select * from audit provider_payload tool_output"
            },
        )

        self.assert_forbidden_markers_absent(json.dumps(event).lower())

    def test_no_direct_api_to_memory_facade_access_or_runtime_execution_trigger(self) -> None:
        event = build_historical_audit_route_audit_event(
            HistoricalAuditCallerIdentity("user-123"),
            HistoricalAuditControlDecision(True, "allowed", 200),
            operation_name="list",
            query_summary={"session_id": "MemoryFacade retry_execution provider_call"},
        )

        serialized = json.dumps(event).lower()
        self.assert_forbidden_markers_absent(serialized)

    def test_no_route_registration_exists(self) -> None:
        repo_root = Path(__file__).resolve().parents[3]
        main_rs = (repo_root / "rust" / "src" / "main.rs").read_text(encoding="utf-8")

        self.assertNotIn('/internal/audit/dry-run', main_rs)
        self.assertNotIn("historical_audit_route_controls", main_rs)

    def test_existing_runtime_provider_execution_behavior_is_not_triggered(self) -> None:
        decision = authorize_historical_audit_readonly(
            HistoricalAuditCallerIdentity("user-123"),
            [HISTORICAL_AUDIT_READONLY_CAPABILITY],
            HistoricalAuditRouteControlConfig(route_enabled=True),
        )

        serialized = json.dumps(decision.as_dict()).lower()
        self.assertNotIn("provider_call", serialized)
        self.assertNotIn("retry_execution", serialized)
        self.assertNotIn("replan_execution", serialized)

    def assert_forbidden_markers_absent(self, serialized: str) -> None:
        for marker in (
            "authorization",
            "bearer ",
            "cookie",
            "secret",
            "token",
            "raw_jsonl",
            "jsonl",
            "raw_sqlite",
            "sqlite",
            "raw_sql",
            "select ",
            "memoryfacade",
            "prompt",
            "provider_payload",
            "provider_response",
            "tool_output",
            "stdout",
            "stderr",
            "traceback",
            "stack",
            "command_args",
            "file_contents",
            ".env",
            "raw_exception",
            "raw_repr",
            "provider_call",
            "retry_execution",
            "replan_execution",
        ):
            self.assertNotIn(marker, serialized)


if __name__ == "__main__":
    unittest.main()
