from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.external.adapters.open_meteo import (  # noqa: E402
    CURRENT_FIELDS,
    DAILY_FIELDS,
    WeatherForecastInput,
    build_open_meteo_request,
    get_weather_forecast,
    normalize_open_meteo_response,
)
from brain.runtime.external.gateway import (  # noqa: E402
    ExternalAPIGateway,
    ExternalGatewayError,
    TransportResponse,
)
from brain.runtime.external.providers import build_external_api_registry  # noqa: E402
from brain.runtime.external.tools import execute_external_action  # noqa: E402
from brain.runtime.execution.models import ExecutionIntent, RiskLevel  # noqa: E402
from brain.runtime.execution.risk_classifier import DeterministicRiskClassifier  # noqa: E402
from brain.runtime.orchestrator import BrainOrchestrator, BrainPaths  # noqa: E402

from test_gateway import FakeResolver, FakeTransport  # noqa: E402


def provider_payload() -> dict[str, object]:
    return {
        "latitude": -23.55,
        "longitude": -46.63,
        "timezone": "America/Sao_Paulo",
        "current": {
            "time": "2026-08-28T12:00",
            "temperature_2m": 20.0,
            "apparent_temperature": 19.0,
            "precipitation": 0.0,
            "weather_code": 1,
            "wind_speed_10m": 8.0,
        },
        "daily": {
            "time": ["2026-08-28"],
            "weather_code": [1],
            "temperature_2m_max": [24.0],
            "temperature_2m_min": [14.0],
            "precipitation_sum": [0.0],
        },
    }


def gateway(payload: object | None = None) -> tuple[ExternalAPIGateway, FakeTransport]:
    body = provider_payload() if payload is None else payload
    transport = FakeTransport(
        [TransportResponse(200, {}, __import__("json").dumps(body).encode(), "93.184.216.34")]
    )
    return (
        ExternalAPIGateway(
            registry=build_external_api_registry(),
            resolver=FakeResolver(),
            transport=transport,
            sleeper=lambda _: None,
        ),
        transport,
    )


class OpenMeteoAdapterTest(unittest.TestCase):
    def test_registered_weather_read_has_explicit_low_risk_classification(self) -> None:
        classification = DeterministicRiskClassifier().classify(
            ExecutionIntent(
                action_id="weather-1",
                action_type="execute",
                capability="weather_forecast",
                description="Read governed weather data",
                input_payload_summary={"tool_arguments": {}},
                expected_outcome="weather result",
                reversible=True,
                target_subsystem="external_api",
            )
        )
        self.assertEqual(classification.level, RiskLevel.LOW)
        self.assertEqual(classification.reason_code, "governed_external_read")

    def test_input_ranges_are_enforced(self) -> None:
        for values, reason in (
            ((-91, 0, 1), "invalid_latitude"),
            ((0, 181, 1), "invalid_longitude"),
            ((0, 0, 0), "invalid_forecast_days"),
            ((0, 0, 8), "invalid_forecast_days"),
        ):
            with self.subTest(values=values), self.assertRaises(ValueError) as caught:
                WeatherForecastInput(*values)
            self.assertEqual(str(caught.exception), reason)

    def test_request_parameters_are_fixed_and_governed(self) -> None:
        request = build_open_meteo_request(WeatherForecastInput(-23.55, -46.63, 3))
        self.assertEqual(request.api_id, "open_meteo")
        self.assertEqual(request.path, "/v1/forecast")
        self.assertEqual(request.query["current"], CURRENT_FIELDS)
        self.assertEqual(request.query["daily"], DAILY_FIELDS)
        self.assertEqual(request.query["timezone"], "auto")

    def test_normal_response_is_minimized_and_attributed(self) -> None:
        api_gateway, _ = gateway()
        result = get_weather_forecast(
            WeatherForecastInput(-23.55, -46.63, 1),
            gateway=api_gateway,
            global_enabled=True,
            provider_enabled=True,
        )
        self.assertEqual(result.provider, "Open-Meteo")
        self.assertEqual(result.timezone, "America/Sao_Paulo")
        self.assertIn("Open-Meteo", result.provenance["attribution"])
        self.assertNotIn("current_units", result.as_dict())

    def test_incomplete_or_inconsistent_response_is_rejected(self) -> None:
        wrong_type = provider_payload()
        wrong_type["current"] = {**wrong_type["current"], "temperature_2m": "warm"}
        for payload in ({"latitude": 1}, {**provider_payload(), "current": {}}, wrong_type):
            with self.subTest(payload=payload), self.assertRaises(ExternalGatewayError) as caught:
                normalize_open_meteo_response(payload, {})
            self.assertEqual(caught.exception.code, "provider_schema_error")

    def test_both_feature_gates_are_required_for_tool_execution(self) -> None:
        for global_value, provider_value, expected in (
            ("false", "true", "external_api_disabled"),
            ("true", "false", "provider_disabled"),
            ("true", "true", None),
        ):
            api_gateway, transport = gateway()
            with patch.dict(
                os.environ,
                {
                    "OMNI_EXTERNAL_API_ENABLED": global_value,
                    "OMNI_EXTERNAL_OPEN_METEO_ENABLED": provider_value,
                },
            ):
                result = execute_external_action(
                    action={
                        "selected_tool": "weather_forecast",
                        "tool_arguments": {
                            "latitude": -23.55,
                            "longitude": -46.63,
                            "forecast_days": 1,
                        },
                    },
                    gateway=api_gateway,
                )
            if expected:
                self.assertFalse(result["ok"])
                self.assertEqual(result["error_payload"]["kind"], expected)
                self.assertEqual(transport.calls, [])
            else:
                self.assertTrue(result["ok"])
                self.assertEqual(result["runtime_truth"]["source"], "external_api")

    def test_orchestrator_uses_governed_external_gateway_path(self) -> None:
        orchestrator = BrainOrchestrator(
            BrainPaths.from_entrypoint(PROJECT_ROOT / "backend" / "python" / "main.py")
        )
        api_gateway, transport = gateway()
        orchestrator.external_api_gateway = api_gateway
        action = {
            "step_id": "weather-1",
            "selected_tool": "weather_forecast",
            "tool_arguments": {"latitude": -23.55, "longitude": -46.63, "forecast_days": 1},
            "policy_decision": {},
            "retry_policy": {"max_attempts": 1},
        }
        with patch.dict(
            os.environ,
            {"OMNI_EXTERNAL_API_ENABLED": "true", "OMNI_EXTERNAL_OPEN_METEO_ENABLED": "true"},
        ):
            result = orchestrator._execute_single_action_core(
                action=action,
                step_results=[],
                semantic_retrieval=None,
                session_id="external-test",
                task_id="weather-test",
                run_id="weather-run",
            )
        self.assertTrue(result["ok"])
        self.assertEqual(result["runtime_truth"]["tool"], "weather_forecast")
        self.assertEqual(len(transport.calls), 1)
        intent = orchestrator._build_execution_intent(
            action=action,
            session_id="external-test",
            task_id="weather-test",
            run_id="weather-run",
        )
        self.assertEqual(intent.input_payload_summary["tool_arguments"]["coordinates"], "redacted")


if __name__ == "__main__":
    unittest.main()
