from __future__ import annotations

import json
import math
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))
sys.path.insert(0, str(PROJECT_ROOT / "tests" / "runtime" / "external"))

from brain.runtime.execution.bindings import resolve_tool_output_binding  # noqa: E402
from brain.runtime.execution.manifest import build_execution_manifest  # noqa: E402
from brain.runtime.external.config import (  # noqa: E402
    EXTERNAL_API_ENABLED_ENV,
    OPEN_METEO_ENABLED_ENV,
    OSM_GEOCODER_ENABLED_ENV,
    OSM_GEOCODER_PUBLIC_API_COMPLIANCE_ACK_ENV,
    OSM_GEOCODER_SINGLE_INSTANCE_ACK_ENV,
    PYTHON_MODE_ENV,
    PYTHON_SERVICE_FALLBACK_ENV,
)
from brain.runtime.external.gateway import ExternalAPIGateway  # noqa: E402
from brain.runtime.external.providers import build_external_api_registry  # noqa: E402
from brain.runtime.orchestrator import BrainOrchestrator, BrainPaths  # noqa: E402

from test_gateway import FakeResolver, FakeTransport  # noqa: E402

BINDING = {
    "type": "geocode_unique_candidate_to_weather",
    "source_step_id": "geocode-1",
}


def governed_nominatim_test_env(**overrides: str) -> dict[str, str]:
    """Build the complete test-only environment for governed Nominatim execution."""
    environment = {
        EXTERNAL_API_ENABLED_ENV: "true",
        OSM_GEOCODER_ENABLED_ENV: "true",
        OPEN_METEO_ENABLED_ENV: "true",
        OSM_GEOCODER_PUBLIC_API_COMPLIANCE_ACK_ENV: "true",
        OSM_GEOCODER_SINGLE_INSTANCE_ACK_ENV: "true",
        PYTHON_MODE_ENV: "service",
        PYTHON_SERVICE_FALLBACK_ENV: "false",
    }
    environment.update(overrides)
    return environment


def source_result(*, latitude: object = -16.68, longitude: object = -49.25) -> dict:
    return {
        "ok": True,
        "selected_tool": "geocode_place",
        "action": {"step_id": "geocode-1"},
        "result_payload": {
            "resolution": "unique",
            "candidates": [{"latitude": latitude, "longitude": longitude}],
        },
        "runtime_truth": {
            "source": "external_api",
            "provider": "nominatim",
            "tool": "geocode_place",
        },
    }


def target_action(**overrides: object) -> dict:
    value = {
        "step_id": "weather-2",
        "selected_tool": "weather_forecast",
        "tool_arguments": {"forecast_days": 2},
        "argument_binding": dict(BINDING),
    }
    value.update(overrides)
    return value


class TypedBindingResolverTest(unittest.TestCase):
    def test_unique_candidate_builds_a_new_action(self) -> None:
        original = target_action()
        resolved = resolve_tool_output_binding(original, [source_result()])
        self.assertIsNone(resolved.error)
        self.assertIsNot(resolved.action, original)
        self.assertNotIn("latitude", original["tool_arguments"])
        self.assertEqual(resolved.action["tool_arguments"]["latitude"], -16.68)
        self.assertEqual(resolved.action["tool_arguments"]["longitude"], -49.25)
        self.assertEqual(resolved.provenance["bound_fields"], ["latitude", "longitude"])
        self.assertNotIn("-16.68", json.dumps(resolved.provenance))

    def test_unknown_wrong_target_missing_duplicate_conflict_and_cycle_deny(self) -> None:
        cases = (
            (
                target_action(argument_binding={"type": "jsonpath", "source_step_id": "geocode-1"}),
                [source_result()],
                "unknown_binding_type",
            ),
            (
                target_action(argument_binding={**BINDING, "source_path": "$.anything"}),
                [source_result()],
                "binding_declaration_invalid",
            ),
            (target_action(selected_tool="read_file"), [source_result()], "binding_target_invalid"),
            (target_action(), [], "binding_source_not_found"),
            (
                target_action(),
                [source_result(), source_result()],
                "binding_source_ambiguous_identity",
            ),
            (
                target_action(tool_arguments={"latitude": 1, "forecast_days": 2}),
                [source_result()],
                "binding_argument_conflict",
            ),
            (target_action(step_id="geocode-1"), [source_result()], "binding_cycle_denied"),
        )
        for action, results, expected in cases:
            with self.subTest(expected=expected):
                self.assertEqual(resolve_tool_output_binding(action, results).error, expected)

    def test_forged_sources_and_invalid_coordinates_fail_closed(self) -> None:
        forged = source_result()
        forged["selected_tool"] = "fake_tool"
        bad_truth = source_result()
        bad_truth["runtime_truth"]["provider"] = "attacker"
        cases = [forged, bad_truth]
        for value in ("javascript:alert(1)", math.nan, math.inf, 91, -181, True):
            cases.append(
                source_result(
                    latitude=value if value != -181 else 0,
                    longitude=value if value == -181 else 0,
                )
            )
        for source in cases:
            with self.subTest(source=source):
                self.assertEqual(
                    resolve_tool_output_binding(target_action(), [source]).error,
                    "binding_source_invalid",
                )

    def test_ambiguity_and_dependency_failure_are_distinct(self) -> None:
        ambiguous = source_result()
        ambiguous["result_payload"] = {
            "resolution": "ambiguous",
            "candidates": [
                {"latitude": 1.0, "longitude": 2.0},
                {"latitude": 3.0, "longitude": 4.0},
            ],
        }
        failed = source_result()
        failed["ok"] = False
        self.assertEqual(
            resolve_tool_output_binding(target_action(), [ambiguous]).error,
            "binding_source_ambiguous",
        )
        self.assertEqual(
            resolve_tool_output_binding(target_action(), [failed]).error,
            "dependency_failed",
        )

    def test_manifest_exposes_dependency_without_values(self) -> None:
        class Request:
            intent = "weather"
            requested_output = "answer"

        class Routing:
            requires_tools = True
            requires_node_runtime = False
            strategy = "tool"
            fallback_allowed = True
            intent = "weather"
            risk_level = "low"

        manifest = build_execution_manifest(
            oil_request=Request(),
            routing_decision=Routing(),
            selected_tools=["geocode_place", "weather_forecast"],
        ).manifest
        weather_step = manifest.step_plan[-1]
        self.assertEqual(weather_step.depends_on, ["s2"])
        self.assertEqual(weather_step.binding, "geocode_unique_candidate_to_weather")


def nominatim_payload(*, ambiguous: bool = False) -> list[dict[str, object]]:
    first = {
        "display_name": "Goiânia, Goiás, Brasil",
        "lat": "-16.68",
        "lon": "-49.25",
        "class": "place",
        "type": "city",
        "importance": 0.7,
        "address": {"state": "Goiás", "country_code": "br"},
    }
    return [first, {**first, "display_name": "Outra Goiânia"}] if ambiguous else [first]


def weather_payload() -> dict[str, object]:
    return {
        "latitude": -16.68,
        "longitude": -49.25,
        "timezone": "America/Sao_Paulo",
        "current": {
            "time": "2026-08-29T12:00",
            "temperature_2m": 25.0,
            "apparent_temperature": 25.5,
            "precipitation": 0.0,
            "weather_code": 1,
            "wind_speed_10m": 8.0,
        },
        "daily": {
            "time": ["2026-08-29"],
            "weather_code": [1],
            "temperature_2m_max": [29.0],
            "temperature_2m_min": [18.0],
            "precipitation_sum": [0.0],
        },
    }


class ComposedRuntimeTest(unittest.TestCase):
    def orchestrator(self, geocode_payload: object) -> tuple[BrainOrchestrator, FakeTransport]:
        transport = FakeTransport(
            [
                FakeTransport.success(geocode_payload),
                FakeTransport.success(weather_payload()),
            ]
        )
        orchestrator = BrainOrchestrator(
            BrainPaths.from_entrypoint(PROJECT_ROOT / "backend" / "python" / "main.py")
        )
        orchestrator.external_api_gateway = ExternalAPIGateway(
            registry=build_external_api_registry(),
            resolver=FakeResolver(),
            transport=transport,
            sleeper=lambda _: None,
        )
        return orchestrator, transport

    @staticmethod
    def geocode_action(step_id: str = "geocode-1") -> dict:
        return {
            "step_id": step_id,
            "selected_tool": "geocode_place",
            "tool_arguments": {
                "place_name": "Goiânia",
                "state_or_region": "Goiás",
                "country_code": "br",
            },
            "policy_decision": {},
            "retry_policy": {"max_attempts": 1},
        }

    @staticmethod
    def weather_action(source_step_id: str = "geocode-1") -> dict:
        action = target_action()
        action["argument_binding"] = {
            "type": "geocode_unique_candidate_to_weather",
            "source_step_id": source_step_id,
        }
        action["policy_decision"] = {}
        action["retry_policy"] = {"max_attempts": 1}
        return action

    def execute(self, orchestrator: BrainOrchestrator, action: dict, prior: list[dict]) -> dict:
        return orchestrator._execute_single_action_core(
            action=action,
            step_results=prior,
            semantic_retrieval=None,
            session_id="binding-test",
            task_id="binding-task",
            run_id="binding-run",
        )

    def test_unique_geocode_calls_weather_once_with_private_bound_coordinates(self) -> None:
        orchestrator, transport = self.orchestrator(nominatim_payload())
        events: list[dict[str, object]] = []
        original_append = orchestrator._append_runtime_event

        def capture(**kwargs: object) -> object:
            if str(kwargs.get("event_type", "")).startswith("runtime.tool_binding"):
                events.append(dict(kwargs))
            return original_append(**kwargs)

        orchestrator._append_runtime_event = capture  # type: ignore[method-assign]
        with patch.dict(
            os.environ,
            governed_nominatim_test_env(),
        ):
            geocode = self.execute(orchestrator, self.geocode_action(), [])
            weather = self.execute(orchestrator, self.weather_action(), [geocode])
        self.assertTrue(geocode["ok"])
        self.assertTrue(weather["ok"])
        self.assertEqual(weather["runtime_truth"]["provider"], "open_meteo")
        self.assertTrue(weather["binding"]["resolved"])
        self.assertEqual(
            [call["logical_host"] for call in transport.calls],
            ["nominatim.openstreetmap.org", "api.open-meteo.com"],
        )
        serialized = json.dumps(events)
        self.assertNotIn("-16.68", serialized)
        self.assertNotIn("-49.25", serialized)
        self.assertNotIn("Goiânia", serialized)
        self.assertEqual(weather["action"]["tool_arguments"]["coordinates"], "redacted")

    def test_ambiguous_geocode_never_calls_weather(self) -> None:
        orchestrator, transport = self.orchestrator(nominatim_payload(ambiguous=True))
        with patch.dict(
            os.environ,
            governed_nominatim_test_env(),
        ):
            geocode = self.execute(orchestrator, self.geocode_action(), [])
            weather = self.execute(orchestrator, self.weather_action(), [geocode])
        self.assertEqual(weather["error_payload"]["kind"], "binding_source_ambiguous")
        self.assertEqual(len(transport.calls), 1)

    def test_failed_dependency_and_provider_gates_never_bypass_target(self) -> None:
        orchestrator, transport = self.orchestrator([])
        with patch.dict(
            os.environ,
            governed_nominatim_test_env(),
        ):
            geocode = self.execute(orchestrator, self.geocode_action(), [])
            weather = self.execute(orchestrator, self.weather_action(), [geocode])
        self.assertFalse(geocode["ok"])
        self.assertEqual(weather["error_payload"]["kind"], "dependency_failed")
        self.assertEqual(len(transport.calls), 1)

        for global_gate, nominatim_gate, expected in (
            ("false", "true", "external_api_disabled"),
            ("true", "false", "provider_disabled"),
        ):
            orchestrator, transport = self.orchestrator(nominatim_payload())
            with patch.dict(
                os.environ,
                governed_nominatim_test_env(
                    **{
                        EXTERNAL_API_ENABLED_ENV: global_gate,
                        OSM_GEOCODER_ENABLED_ENV: nominatim_gate,
                    }
                ),
            ):
                geocode = self.execute(orchestrator, self.geocode_action(), [])
                weather = self.execute(orchestrator, self.weather_action(), [geocode])
            self.assertEqual(geocode["error_payload"]["kind"], expected)
            self.assertEqual(weather["error_payload"]["kind"], "dependency_failed")
            self.assertEqual(transport.calls, [])

        orchestrator, transport = self.orchestrator(nominatim_payload())
        with patch.dict(
            os.environ,
            governed_nominatim_test_env(**{OPEN_METEO_ENABLED_ENV: "false"}),
        ):
            geocode = self.execute(orchestrator, self.geocode_action(), [])
            weather = self.execute(orchestrator, self.weather_action(), [geocode])
        self.assertEqual(weather["error_payload"]["kind"], "provider_disabled")
        self.assertEqual(len(transport.calls), 1)

    def test_cached_geocode_still_binds_without_extra_transport(self) -> None:
        orchestrator, transport = self.orchestrator(nominatim_payload())
        environment = governed_nominatim_test_env()
        with patch.dict(os.environ, environment):
            first_geocode = self.execute(orchestrator, self.geocode_action(), [])
            first_weather = self.execute(orchestrator, self.weather_action(), [first_geocode])
            second_geocode = self.execute(orchestrator, self.geocode_action("geocode-2"), [])
            second_weather = self.execute(
                orchestrator, self.weather_action("geocode-2"), [second_geocode]
            )
        self.assertTrue(second_geocode["runtime_truth"]["cached"])
        self.assertTrue(first_weather["ok"])
        self.assertTrue(second_weather["runtime_truth"]["cached"])
        self.assertEqual(len(transport.calls), 2)


if __name__ == "__main__":
    unittest.main()
