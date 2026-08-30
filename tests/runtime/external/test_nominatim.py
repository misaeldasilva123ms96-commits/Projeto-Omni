from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.external.adapters.nominatim import (  # noqa: E402
    OSM_GEOCODER_USER_AGENT,
    GeocodePlaceInput,
    build_nominatim_request,
    get_geocode_place,
    normalize_nominatim_response,
)
from brain.runtime.external.gateway import (  # noqa: E402
    ExternalAPIGateway,
    ExternalGatewayError,
    LocalRateLimiter,
    TTLResponseCache,
    TransportResponse,
)
from brain.runtime.external.models import ExternalAPIRequest, RedirectPolicy  # noqa: E402
from brain.runtime.external.providers import (  # noqa: E402
    build_external_api_registry,
    nominatim_definition,
)
from brain.runtime.external.tools import execute_external_action  # noqa: E402
from brain.runtime.execution.models import ExecutionIntent, RiskLevel  # noqa: E402
from brain.runtime.execution.risk_classifier import DeterministicRiskClassifier  # noqa: E402
from brain.runtime.orchestrator import BrainOrchestrator, BrainPaths  # noqa: E402

from test_gateway import FakeClock, FakeResolver, FakeTransport  # noqa: E402

NOMINATIM_READY_ENV = {
    "OMNI_EXTERNAL_NOMINATIM_PUBLIC_API_COMPLIANCE_ACK": "true",
    "OMNI_EXTERNAL_NOMINATIM_SINGLE_INSTANCE_ACK": "true",
    "OMNI_PYTHON_MODE": "service",
    "OMNI_PYTHON_SERVICE_FALLBACK_TO_SUBPROCESS": "false",
}


def candidate(**overrides: object) -> dict[str, object]:
    value: dict[str, object] = {
        "display_name": "Goiânia, Região Geográfica Imediata de Goiânia, Goiás, Brasil",
        "lat": "-16.6808820",
        "lon": "-49.2532691",
        "class": "place",
        "type": "city",
        "importance": 0.71,
        "address": {"state": "Goiás", "country_code": "br"},
        "licence": "Data © OpenStreetMap contributors, ODbL 1.0",
    }
    value.update(overrides)
    return value


def gateway(
    payload: object,
    *,
    clock: FakeClock | None = None,
    outcomes: int = 1,
) -> tuple[ExternalAPIGateway, FakeTransport]:
    test_clock = clock or FakeClock()
    response = TransportResponse(
        200,
        {},
        json.dumps(payload).encode(),
        "93.184.216.34",
    )
    transport = FakeTransport([response] * outcomes)
    return (
        ExternalAPIGateway(
            registry=build_external_api_registry(),
            resolver=FakeResolver(),
            transport=transport,
            cache=TTLResponseCache(clock=test_clock),
            rate_limiter=LocalRateLimiter(clock=test_clock),
            sleeper=lambda _: None,
        ),
        transport,
    )


@patch.dict(os.environ, NOMINATIM_READY_ENV)
class NominatimComplianceTest(unittest.TestCase):
    def test_provider_invariants_are_fail_safe(self) -> None:
        definition = nominatim_definition()
        self.assertEqual(definition.base_url, "https://nominatim.openstreetmap.org")
        self.assertEqual(definition.allowed_hosts, {"nominatim.openstreetmap.org"})
        self.assertEqual(definition.allowed_paths, {"/search"})
        self.assertEqual(definition.allowed_methods, {"GET"})
        self.assertIs(definition.redirect_policy, RedirectPolicy.DENY)
        self.assertLessEqual(definition.rate_limit_requests, 1)
        self.assertGreaterEqual(definition.rate_limit_window_seconds, 1.1)
        self.assertGreater(definition.cache_ttl_seconds or 0, 0)
        self.assertEqual(definition.max_attempts, 1)

    def test_request_has_fixed_query_and_identifiable_user_agent(self) -> None:
        request = build_nominatim_request(GeocodePlaceInput("Goiânia", "Goiás", "BR"))
        self.assertEqual(request.path, "/search")
        self.assertEqual(
            request.query,
            {
                "q": "Goiânia, Goiás",
                "format": "jsonv2",
                "addressdetails": 1,
                "limit": 3,
                "featureType": "settlement",
                "accept-language": "pt-BR,pt,en",
                "countrycodes": "br",
            },
        )
        self.assertEqual(request.headers["User-Agent"], OSM_GEOCODER_USER_AGENT)
        self.assertNotEqual(request.headers["User-Agent"], "Omni-External-API/1")

    def test_gateway_uses_custom_user_agent(self) -> None:
        api_gateway, transport = gateway([candidate()])
        get_geocode_place(
            GeocodePlaceInput("Goiânia", "Goiás", "br"),
            gateway=api_gateway,
            global_enabled=True,
            provider_enabled=True,
        )
        headers = transport.calls[0]["headers"]
        self.assertEqual(headers["User-Agent"], OSM_GEOCODER_USER_AGENT)

    def test_wrong_path_and_method_are_denied_before_transport(self) -> None:
        for request in (
            ExternalAPIRequest("nominatim", "GET", "/reverse"),
            ExternalAPIRequest("nominatim", "POST", "/search"),
        ):
            api_gateway, transport = gateway([candidate()])
            with self.subTest(request=request), self.assertRaises(ExternalGatewayError):
                api_gateway.execute(request, global_enabled=True, provider_enabled=True)
            self.assertEqual(transport.calls, [])

        api_gateway, _ = gateway([candidate()])
        wrong_host = api_gateway.policy.evaluate(
            api_id="nominatim",
            endpoint="https://attacker.example/search",
            method="GET",
            feature_enabled=True,
        )
        self.assertFalse(wrong_host.allowed)

    def test_operational_compliance_guard_denies_before_dns_and_transport(self) -> None:
        cases = (
            {"OMNI_PYTHON_MODE": "subprocess"},
            {"OMNI_PYTHON_SERVICE_FALLBACK_TO_SUBPROCESS": "true"},
            {"OMNI_EXTERNAL_NOMINATIM_PUBLIC_API_COMPLIANCE_ACK": "false"},
            {"OMNI_EXTERNAL_NOMINATIM_SINGLE_INSTANCE_ACK": "false"},
            {"OMNI_PYTHON_MODE": "invalid"},
        )
        for environment in cases:
            resolver = FakeResolver()
            transport = FakeTransport()
            api_gateway = ExternalAPIGateway(
                registry=build_external_api_registry(),
                resolver=resolver,
                transport=transport,
            )
            with (
                self.subTest(environment=environment),
                patch.dict(os.environ, environment),
                self.assertRaises(ExternalGatewayError) as caught,
            ):
                get_geocode_place(
                    GeocodePlaceInput("Goiânia"),
                    gateway=api_gateway,
                    global_enabled=True,
                    provider_enabled=True,
                )
            self.assertEqual(caught.exception.code, "provider_compliance_guard_failed")
            self.assertEqual(str(caught.exception), "provider_compliance_guard_failed")
            self.assertEqual(resolver.calls, 0)
            self.assertEqual(transport.calls, [])

    def test_operational_compliance_guard_allows_fake_transport(self) -> None:
        resolver = FakeResolver()
        transport = FakeTransport([FakeTransport.success([candidate()])])
        api_gateway = ExternalAPIGateway(
            registry=build_external_api_registry(), resolver=resolver, transport=transport
        )
        result = get_geocode_place(
            GeocodePlaceInput("Goiânia"),
            gateway=api_gateway,
            global_enabled=True,
            provider_enabled=True,
        )
        self.assertEqual(result.provider, "Nominatim / OpenStreetMap")
        self.assertEqual(resolver.calls, 1)
        self.assertEqual(len(transport.calls), 1)

    def test_missing_or_invalid_operational_values_deny_before_network(self) -> None:
        environments = (
            {},
            {
                "OMNI_EXTERNAL_NOMINATIM_PUBLIC_API_COMPLIANCE_ACK": "invalid",
                "OMNI_EXTERNAL_NOMINATIM_SINGLE_INSTANCE_ACK": "true",
                "OMNI_PYTHON_MODE": "service",
                "OMNI_PYTHON_SERVICE_FALLBACK_TO_SUBPROCESS": "false",
            },
            {
                "OMNI_EXTERNAL_NOMINATIM_PUBLIC_API_COMPLIANCE_ACK": "true",
                "OMNI_EXTERNAL_NOMINATIM_SINGLE_INSTANCE_ACK": "true",
                "OMNI_PYTHON_MODE": "service",
                "OMNI_PYTHON_SERVICE_FALLBACK_TO_SUBPROCESS": "invalid",
            },
        )
        for environment in environments:
            resolver = FakeResolver()
            transport = FakeTransport()
            api_gateway = ExternalAPIGateway(
                registry=build_external_api_registry(),
                resolver=resolver,
                transport=transport,
            )
            with (
                self.subTest(environment=environment),
                patch.dict(os.environ, environment, clear=True),
                self.assertRaises(ExternalGatewayError) as caught,
            ):
                get_geocode_place(
                    GeocodePlaceInput("Goiânia"),
                    gateway=api_gateway,
                    global_enabled=True,
                    provider_enabled=True,
                )
            self.assertEqual(caught.exception.code, "provider_compliance_guard_failed")
            self.assertEqual(resolver.calls, 0)
            self.assertEqual(transport.calls, [])


class NominatimInputAndNormalizationTest(unittest.TestCase):
    def test_input_validation_and_normalization(self) -> None:
        valid = GeocodePlaceInput("  Goiânia  ", " Goiás ", "BR")
        self.assertEqual(
            (valid.place_name, valid.state_or_region, valid.country_code),
            ("Goiânia", "Goiás", "br"),
        )
        for values, code in (
            (("x", None, None), "invalid_place_name"),
            (("x" * 101, None, None), "invalid_place_name"),
            (("Goiânia\nRua", None, None), "invalid_place_name"),
            (("Goiânia", 7, None), "invalid_state_or_region"),
            (("Goiânia", None, "bra"), "invalid_country_code"),
            (("Goiânia", None, "b1"), "invalid_country_code"),
        ):
            with self.subTest(code=code), self.assertRaises(ValueError) as caught:
                GeocodePlaceInput(*values)
            self.assertEqual(str(caught.exception), code)

    def test_one_candidate_is_unique_and_minimized(self) -> None:
        result = normalize_nominatim_response(
            [candidate(extra="not propagated")],
            value=GeocodePlaceInput("Goiânia", "Goiás", "br"),
            provenance={"attribution": "© OpenStreetMap contributors; ODbL 1.0"},
        )
        self.assertEqual(result.resolution, "unique")
        self.assertEqual(len(result.candidates), 1)
        self.assertEqual(result.candidates[0].country_code, "br")
        self.assertNotIn("extra", result.as_dict()["candidates"][0])
        self.assertIn("OpenStreetMap", result.provenance["attribution"])

    def test_multiple_candidates_remain_ambiguous_and_bounded(self) -> None:
        results = [candidate(display_name=f"Springfield {index}") for index in range(5)]
        normalized = normalize_nominatim_response(
            results,
            value=GeocodePlaceInput("Springfield"),
            provenance={},
        )
        self.assertEqual(normalized.resolution, "ambiguous")
        self.assertEqual(len(normalized.candidates), 3)

    def test_empty_or_invalid_provider_data_fails_without_invention(self) -> None:
        invalid_payloads = (
            [],
            {"lat": "1"},
            [candidate(lat="91")],
            [candidate(lon="-181")],
            [candidate(lat="NaN")],
            [candidate(address={})],
            [candidate(address={"country_code": "brazil"})],
        )
        for payload in invalid_payloads:
            with self.subTest(payload=payload), self.assertRaises(ExternalGatewayError) as caught:
                normalize_nominatim_response(
                    payload,
                    value=GeocodePlaceInput("Goiânia"),
                    provenance={},
                )
            expected = "location_not_found" if payload == [] else "provider_schema_error"
            self.assertEqual(caught.exception.code, expected)


@patch.dict(os.environ, NOMINATIM_READY_ENV)
class NominatimGatewayIntegrationTest(unittest.TestCase):
    def test_malformed_json_is_rejected_without_retry(self) -> None:
        transport = FakeTransport([TransportResponse(200, {}, b"not-json", "93.184.216.34")])
        api_gateway = ExternalAPIGateway(
            registry=build_external_api_registry(),
            resolver=FakeResolver(),
            transport=transport,
            sleeper=lambda _: None,
        )
        with self.assertRaises(ExternalGatewayError) as caught:
            get_geocode_place(
                GeocodePlaceInput("Goiânia"),
                gateway=api_gateway,
                global_enabled=True,
                provider_enabled=True,
            )
        self.assertEqual(caught.exception.code, "malformed_json")
        self.assertEqual(len(transport.calls), 1)

    def test_repeated_normalized_query_uses_one_transport_call(self) -> None:
        api_gateway, transport = gateway([candidate()])
        first = get_geocode_place(
            GeocodePlaceInput("  Goiânia ", " Goiás ", "BR"),
            gateway=api_gateway,
            global_enabled=True,
            provider_enabled=True,
        )
        second = get_geocode_place(
            GeocodePlaceInput("Goiânia", "Goiás", "br"),
            gateway=api_gateway,
            global_enabled=True,
            provider_enabled=True,
        )
        self.assertFalse(first.provenance["cached"])
        self.assertTrue(second.provenance["cached"])
        self.assertEqual(len(transport.calls), 1)

    def test_cache_expiry_and_rate_window_are_testable(self) -> None:
        clock = FakeClock()
        api_gateway, transport = gateway([candidate()], clock=clock, outcomes=2)
        value = GeocodePlaceInput("Goiânia", "Goiás", "br")
        get_geocode_place(value, gateway=api_gateway, global_enabled=True, provider_enabled=True)
        clock.value += 86_401
        get_geocode_place(value, gateway=api_gateway, global_enabled=True, provider_enabled=True)
        self.assertEqual(len(transport.calls), 2)

    def test_rate_limit_blocks_distinct_second_query_without_transport(self) -> None:
        api_gateway, transport = gateway([candidate()], outcomes=2)
        get_geocode_place(
            GeocodePlaceInput("Goiânia"),
            gateway=api_gateway,
            global_enabled=True,
            provider_enabled=True,
        )
        with self.assertRaises(ExternalGatewayError) as caught:
            get_geocode_place(
                GeocodePlaceInput("Anápolis"),
                gateway=api_gateway,
                global_enabled=True,
                provider_enabled=True,
            )
        self.assertEqual(caught.exception.code, "rate_limit_exceeded")
        self.assertEqual(len(transport.calls), 1)

    def test_global_and_provider_gates_fail_closed(self) -> None:
        for environment, code in (
            (
                {"OMNI_EXTERNAL_API_ENABLED": "false", "OMNI_EXTERNAL_NOMINATIM_ENABLED": "true"},
                "external_api_disabled",
            ),
            (
                {"OMNI_EXTERNAL_API_ENABLED": "true", "OMNI_EXTERNAL_NOMINATIM_ENABLED": "false"},
                "provider_disabled",
            ),
        ):
            api_gateway, transport = gateway([candidate()])
            with patch.dict(os.environ, environment):
                result = execute_external_action(
                    action={
                        "selected_tool": "geocode_place",
                        "tool_arguments": {"place_name": "Goiânia"},
                    },
                    gateway=api_gateway,
                )
            self.assertFalse(result["ok"])
            self.assertEqual(result["error_payload"]["kind"], code)
            self.assertEqual(transport.calls, [])

    def test_observability_and_provenance_do_not_expose_raw_query(self) -> None:
        events: list[tuple[str, dict[str, object]]] = []
        api_gateway, _ = gateway([candidate()])
        result = get_geocode_place(
            GeocodePlaceInput("Goiânia", "Goiás", "br"),
            gateway=api_gateway,
            global_enabled=True,
            provider_enabled=True,
            event_sink=lambda event, payload: events.append((event, payload)),
        )
        self.assertNotIn("?", result.provenance["endpoint"])
        self.assertNotIn("Goiânia", json.dumps(events, ensure_ascii=False))
        normalized_event = events[-1][1]
        self.assertEqual(normalized_event["candidate_count"], 1)
        self.assertEqual(normalized_event["resolution"], "unique")

    def test_tool_is_low_risk_and_uses_orchestrator_gateway_path(self) -> None:
        classification = DeterministicRiskClassifier().classify(
            ExecutionIntent(
                action_id="geocode-1",
                action_type="execute",
                capability="geocode_place",
                description="Resolve a settlement",
                input_payload_summary={"tool_arguments": {}},
                expected_outcome="candidate list",
                reversible=True,
                target_subsystem="external_api",
            )
        )
        self.assertEqual(classification.level, RiskLevel.LOW)
        orchestrator = BrainOrchestrator(
            BrainPaths.from_entrypoint(PROJECT_ROOT / "backend" / "python" / "main.py")
        )
        api_gateway, transport = gateway([candidate()])
        orchestrator.external_api_gateway = api_gateway
        action = {
            "step_id": "geocode-1",
            "selected_tool": "geocode_place",
            "tool_arguments": {
                "place_name": "Goiânia",
                "state_or_region": "Goiás",
                "country_code": "br",
            },
            "policy_decision": {},
            "retry_policy": {"max_attempts": 1},
        }
        with patch.dict(
            os.environ,
            {"OMNI_EXTERNAL_API_ENABLED": "true", "OMNI_EXTERNAL_NOMINATIM_ENABLED": "true"},
        ):
            result = orchestrator._execute_single_action_core(
                action=action,
                step_results=[],
                semantic_retrieval=None,
                session_id="external-test",
                task_id="geocode-test",
                run_id="geocode-run",
            )
        self.assertTrue(result["ok"])
        self.assertEqual(result["runtime_truth"]["provider"], "nominatim")
        self.assertEqual(len(transport.calls), 1)
        intent = orchestrator._build_execution_intent(
            action=action,
            session_id="external-test",
            task_id="geocode-test",
            run_id="geocode-run",
        )
        self.assertEqual(intent.input_payload_summary["tool_arguments"]["place_query"], "redacted")


if __name__ == "__main__":
    unittest.main()
