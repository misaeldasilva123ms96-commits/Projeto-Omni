from __future__ import annotations

import io
import json
import ssl
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.external.gateway import (  # noqa: E402
    ExternalAPIGateway,
    ExternalGatewayError,
    LocalRateLimiter,
    PinnedHTTPSTransport,
    TTLResponseCache,
    TransportResponse,
    _read_limited,
    validate_resolved_addresses,
)
from brain.runtime.external.models import ExternalAPIDefinition, ExternalAPIRequest  # noqa: E402
from brain.runtime.external.registry import ExternalAPIRegistry  # noqa: E402


class FakeClock:
    def __init__(self) -> None:
        self.value = 100.0

    def __call__(self) -> float:
        return self.value


class FakeResolver:
    def __init__(
        self, addresses=("93.184.216.34",), error: ExternalGatewayError | None = None
    ) -> None:
        self.addresses = tuple(addresses)
        self.error = error
        self.calls = 0

    def resolve(self, host: str, port: int) -> tuple[str, ...]:
        self.calls += 1
        if self.error:
            raise self.error
        return self.addresses


class FakeTransport:
    def __init__(self, outcomes: list[object] | None = None) -> None:
        self.outcomes = list(outcomes or [self.success()])
        self.calls: list[dict[str, object]] = []

    @staticmethod
    def success(
        body: object | None = None, *, connected_ip: str = "93.184.216.34"
    ) -> TransportResponse:
        payload = body if body is not None else {"ok": True}
        return TransportResponse(
            200, {"content-type": "application/json"}, json.dumps(payload).encode(), connected_ip
        )

    def request(self, **kwargs: object) -> TransportResponse:
        self.calls.append(dict(kwargs))
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome  # type: ignore[return-value]


def definition(**overrides: object) -> ExternalAPIDefinition:
    values = {
        "api_id": "fixture_api",
        "name": "Fixture",
        "description": "Safe test fixture",
        "base_url": "https://api.example.com",
        "allowed_hosts": frozenset({"api.example.com"}),
        "allowed_methods": frozenset({"GET"}),
        "allowed_paths": frozenset({"/data", "/other", "/third"}),
        "enabled": True,
        "cache_ttl_seconds": None,
        "max_attempts": 2,
    }
    values.update(overrides)
    return ExternalAPIDefinition(**values)


def gateway_for(
    *,
    api: ExternalAPIDefinition | None = None,
    resolver=None,
    transport=None,
    clock=None,
    events=None,
):
    registry = ExternalAPIRegistry()
    registry.register(api or definition())
    clock = clock or FakeClock()
    return ExternalAPIGateway(
        registry=registry,
        resolver=resolver or FakeResolver(),
        transport=transport or FakeTransport(),
        cache=TTLResponseCache(max_entries=2, clock=clock),
        rate_limiter=LocalRateLimiter(clock=clock),
        sleeper=lambda _: None,
        event_sink=(
            (lambda event, payload: events.append((event, payload))) if events is not None else None
        ),
    )


REQUEST = ExternalAPIRequest(
    api_id="fixture_api", method="GET", path="/data", query={"safe": "value"}
)


class DNSValidationTest(unittest.TestCase):
    def test_request_model_rejects_absolute_urls_and_sensitive_headers(self) -> None:
        with self.assertRaises(ValueError):
            ExternalAPIRequest("fixture_api", "GET", "https://attacker.example/path")
        with self.assertRaises(ValueError):
            ExternalAPIRequest(
                "fixture_api",
                "GET",
                "/data",
                headers={"Authorization": "not-allowed"},
            )
        with self.assertRaises(ValueError):
            ExternalAPIRequest(
                "fixture_api",
                "GET",
                "/data",
                headers={"User-Agent": "safe\r\nInjected: value"},
            )

    def test_non_allowlisted_path_is_denied_before_dns_or_transport(self) -> None:
        resolver = FakeResolver()
        transport = FakeTransport()
        with self.assertRaises(ExternalGatewayError) as caught:
            gateway_for(resolver=resolver, transport=transport).execute(
                ExternalAPIRequest("fixture_api", "GET", "/admin"),
                global_enabled=True,
                provider_enabled=True,
            )
        self.assertEqual(caught.exception.code, "path_not_allowed")
        self.assertEqual(resolver.calls, 0)
        self.assertEqual(transport.calls, [])

    def test_public_ipv4_and_ipv6_are_allowed(self) -> None:
        self.assertEqual(validate_resolved_addresses(("93.184.216.34",)), ("93.184.216.34",))
        self.assertEqual(
            validate_resolved_addresses(("2606:4700:4700::1111",)), ("2606:4700:4700::1111",)
        )

    def test_non_public_and_mixed_answers_are_denied(self) -> None:
        for addresses in (
            ("10.0.0.1",),
            ("127.0.0.1",),
            ("169.254.1.1",),
            ("192.0.2.1",),
            ("::1",),
            ("fe80::1",),
            ("93.184.216.34", "10.0.0.1"),
        ):
            with (
                self.subTest(addresses=addresses),
                self.assertRaises(ExternalGatewayError) as caught,
            ):
                validate_resolved_addresses(addresses)
            self.assertEqual(caught.exception.code, "dns_non_public_address")

    def test_dns_failure_and_empty_answer_deny(self) -> None:
        for resolver in (
            FakeResolver(error=ExternalGatewayError("dns_resolution_failed")),
            FakeResolver(addresses=()),
        ):
            with self.subTest(resolver=resolver), self.assertRaises(ExternalGatewayError):
                gateway_for(resolver=resolver).execute(
                    REQUEST, global_enabled=True, provider_enabled=True
                )

    def test_transport_connects_to_the_exact_validated_ip(self) -> None:
        resolver = FakeResolver(("93.184.216.35",))
        transport = FakeTransport([FakeTransport.success(connected_ip="93.184.216.35")])
        gateway_for(resolver=resolver, transport=transport).execute(
            REQUEST, global_enabled=True, provider_enabled=True
        )
        self.assertEqual(transport.calls[0]["pinned_ip"], "93.184.216.35")
        self.assertEqual(transport.calls[0]["logical_host"], "api.example.com")

    def test_transport_cannot_report_a_different_connected_ip(self) -> None:
        transport = FakeTransport([FakeTransport.success(connected_ip="93.184.216.99")])
        with self.assertRaises(ExternalGatewayError) as caught:
            gateway_for(transport=transport).execute(
                REQUEST, global_enabled=True, provider_enabled=True
            )
        self.assertEqual(caught.exception.code, "pinned_ip_mismatch")


class TLSRedirectAndLimitTest(unittest.TestCase):
    def test_transport_refuses_context_without_tls_verification(self) -> None:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        transport = PinnedHTTPSTransport(context_factory=lambda: context)
        with self.assertRaises(ExternalGatewayError) as caught:
            transport.request(
                logical_host="api.example.com",
                pinned_ip="93.184.216.34",
                port=443,
                method="GET",
                target="/",
                headers={},
                timeout_seconds=1,
                max_response_bytes=10,
            )
        self.assertEqual(caught.exception.code, "tls_verification_required")

    def test_all_redirects_are_denied_without_following_location(self) -> None:
        for location in ("https://other.example/path", "http://api.example.com/path", "/same-host"):
            response = TransportResponse(302, {"location": location}, b"", "93.184.216.34")
            transport = FakeTransport([response])
            with self.subTest(location=location), self.assertRaises(ExternalGatewayError) as caught:
                gateway_for(transport=transport).execute(
                    REQUEST, global_enabled=True, provider_enabled=True
                )
            self.assertEqual(caught.exception.code, "redirect_denied")
            self.assertEqual(len(transport.calls), 1)

    def test_streaming_limit_accepts_exact_and_rejects_above(self) -> None:
        class Response:
            def __init__(self, body: bytes) -> None:
                self.body = io.BytesIO(body)

            def read(self, size: int) -> bytes:
                return self.body.read(size)

        self.assertEqual(_read_limited(Response(b"12345"), 5), b"12345")  # type: ignore[arg-type]
        with self.assertRaises(ExternalGatewayError) as caught:
            _read_limited(Response(b"123456"), 5)  # type: ignore[arg-type]
        self.assertEqual(caught.exception.code, "response_too_large")

    def test_timeout_and_malformed_json_are_typed(self) -> None:
        cases = (
            (ExternalGatewayError("request_timeout", retryable=True), "request_timeout", 2),
            (TransportResponse(200, {}, b"not-json", "93.184.216.34"), "malformed_json", 1),
        )
        for outcome, code, calls in cases:
            transport = FakeTransport([outcome] * calls)
            with self.subTest(code=code), self.assertRaises(ExternalGatewayError) as caught:
                gateway_for(transport=transport).execute(
                    REQUEST, global_enabled=True, provider_enabled=True
                )
            self.assertEqual(caught.exception.code, code)
            self.assertEqual(len(transport.calls), calls)


class RetryCacheRateAndGateTest(unittest.TestCase):
    def test_cache_identity_is_opaque_canonical_and_wire_aligned(self) -> None:
        scalar = ExternalAPIRequest(
            "fixture_api", "GET", "/data", query={"value": "('a', 'b')", "z": "last"}
        )
        repeated = ExternalAPIRequest(
            "fixture_api", "GET", "/data", query={"z": "last", "value": ("a", "b")}
        )
        reordered = ExternalAPIRequest(
            "fixture_api", "GET", "/data", query={"z": "last", "value": "('a', 'b')"}
        )
        scalar_key = ExternalAPIGateway._cache_key(scalar)
        self.assertEqual(scalar_key, ExternalAPIGateway._cache_key(reordered))
        self.assertNotEqual(scalar_key, ExternalAPIGateway._cache_key(repeated))
        self.assertRegex(scalar_key, r"^external-api-cache:v2:[0-9a-f]{64}$")
        self.assertNotIn("('a', 'b')", scalar_key)
        self.assertNotIn("last", scalar_key)
        for changed in (
            ExternalAPIRequest("fixture_api", "GET", "/other", query=scalar.query),
            ExternalAPIRequest("fixture_api", "POST", "/data", query=scalar.query),
            ExternalAPIRequest("other_api", "GET", "/data", query=scalar.query),
        ):
            self.assertNotEqual(scalar_key, ExternalAPIGateway._cache_key(changed))

    def test_cache_identity_binds_form_semantics_without_raw_or_credentials(self) -> None:
        first = ExternalAPIRequest(
            "fixture_api", "POST", "/data", form_fields={"url": "https://bad.example/a"}
        )
        reordered = ExternalAPIRequest(
            "fixture_api", "POST", "/data", form_fields={"url": "https://bad.example/a"}
        )
        changed = ExternalAPIRequest(
            "fixture_api", "POST", "/data", form_fields={"url": "https://bad.example/b"}
        )
        first_key = ExternalAPIGateway._cache_key(first)
        self.assertEqual(first_key, ExternalAPIGateway._cache_key(reordered))
        self.assertNotEqual(first_key, ExternalAPIGateway._cache_key(changed))
        self.assertNotIn("bad.example", first_key)
        self.assertNotIn("Auth-Key", first_key)

    def test_wire_equivalent_mapping_order_hits_same_opaque_cache_entry(self) -> None:
        transport = FakeTransport([FakeTransport.success()])
        gateway = gateway_for(api=definition(cache_ttl_seconds=10), transport=transport)
        first = ExternalAPIRequest(
            "fixture_api",
            "GET",
            "/data",
            query={"longitude": -49.2532691, "latitude": -16.680882},
        )
        second = ExternalAPIRequest(
            "fixture_api",
            "GET",
            "/data",
            query={"latitude": -16.680882, "longitude": -49.2532691},
        )
        gateway.execute(first, global_enabled=True, provider_enabled=True)
        cached = gateway.execute(second, global_enabled=True, provider_enabled=True)
        self.assertTrue(cached.provenance["cached"])
        self.assertEqual(len(transport.calls), 1)
        self.assertEqual(
            transport.calls[0]["target"],
            "/data?latitude=-16.680882&longitude=-49.2532691",
        )
        stored_keys = tuple(gateway.cache._entries)  # noqa: SLF001 - security boundary assertion
        self.assertEqual(len(stored_keys), 1)
        self.assertRegex(stored_keys[0], r"^external-api-cache:v2:[0-9a-f]{64}$")
        self.assertNotIn("latitude", stored_keys[0])
        self.assertNotIn("-49.2532691", stored_keys[0])

    def test_transient_retries_are_bounded_and_400_is_not_retried(self) -> None:
        transient = FakeTransport(
            [ExternalGatewayError("connection_failed", retryable=True), FakeTransport.success()]
        )
        gateway_for(transport=transient).execute(
            REQUEST, global_enabled=True, provider_enabled=True
        )
        self.assertEqual(len(transient.calls), 2)
        bad_request = FakeTransport([TransportResponse(400, {}, b"{}", "93.184.216.34")])
        with self.assertRaises(ExternalGatewayError) as caught:
            gateway_for(transport=bad_request).execute(
                REQUEST, global_enabled=True, provider_enabled=True
            )
        self.assertEqual(caught.exception.code, "provider_http_error")
        self.assertEqual(len(bad_request.calls), 1)

    def test_policy_denial_and_provider_gate_do_not_call_transport(self) -> None:
        cases = (
            ({"global_enabled": False}, "external_api_disabled"),
            ({"global_enabled": True}, "provider_disabled"),
            ({"provider_enabled": False, "global_enabled": True}, "provider_disabled"),
        )
        for options, code in cases:
            transport = FakeTransport()
            with self.subTest(code=code), self.assertRaises(ExternalGatewayError) as caught:
                gateway_for(transport=transport).execute(REQUEST, **options)
            self.assertEqual(caught.exception.code, code)
            self.assertEqual(transport.calls, [])

    def test_cache_miss_hit_expiry_and_capacity(self) -> None:
        clock = FakeClock()
        transport = FakeTransport(
            [
                FakeTransport.success(),
                FakeTransport.success(),
                FakeTransport.success(),
                FakeTransport.success(),
            ]
        )
        gateway = gateway_for(
            api=definition(cache_ttl_seconds=10), transport=transport, clock=clock
        )
        first = gateway.execute(REQUEST, global_enabled=True, provider_enabled=True)
        second = gateway.execute(REQUEST, global_enabled=True, provider_enabled=True)
        self.assertFalse(first.provenance["cached"])
        self.assertTrue(second.provenance["cached"])
        self.assertEqual(len(transport.calls), 1)
        clock.value += 11
        gateway.execute(REQUEST, global_enabled=True, provider_enabled=True)
        self.assertEqual(len(transport.calls), 2)
        gateway.execute(
            ExternalAPIRequest("fixture_api", "GET", "/other"),
            global_enabled=True,
            provider_enabled=True,
        )
        gateway.execute(
            ExternalAPIRequest("fixture_api", "GET", "/third"),
            global_enabled=True,
            provider_enabled=True,
        )
        self.assertEqual(len(gateway.cache), 2)

    def test_rate_limit_blocks_before_transport(self) -> None:
        transport = FakeTransport([FakeTransport.success(), FakeTransport.success()])
        gateway = gateway_for(api=definition(rate_limit_requests=1), transport=transport)
        gateway.execute(REQUEST, global_enabled=True, provider_enabled=True)
        with self.assertRaises(ExternalGatewayError) as caught:
            gateway.execute(
                ExternalAPIRequest("fixture_api", "GET", "/other"),
                global_enabled=True,
                provider_enabled=True,
            )
        self.assertEqual(caught.exception.code, "rate_limit_exceeded")
        self.assertEqual(len(transport.calls), 1)

    def test_each_retry_consumes_rate_limit_quota(self) -> None:
        transport = FakeTransport(
            [ExternalGatewayError("connection_failed", retryable=True), FakeTransport.success()]
        )
        with self.assertRaises(ExternalGatewayError) as caught:
            gateway_for(
                api=definition(rate_limit_requests=1, max_attempts=2), transport=transport
            ).execute(REQUEST, global_enabled=True, provider_enabled=True)
        self.assertEqual(caught.exception.code, "rate_limit_exceeded")
        self.assertEqual(len(transport.calls), 1)

    def test_retry_succeeds_when_transport_attempt_quota_is_sufficient(self) -> None:
        transport = FakeTransport(
            [ExternalGatewayError("connection_failed", retryable=True), FakeTransport.success()]
        )
        gateway_for(
            api=definition(rate_limit_requests=2, max_attempts=2), transport=transport
        ).execute(REQUEST, global_enabled=True, provider_enabled=True)
        self.assertEqual(len(transport.calls), 2)

    def test_cache_hit_does_not_consume_transport_attempt_quota(self) -> None:
        transport = FakeTransport([FakeTransport.success(), FakeTransport.success()])
        gateway = gateway_for(
            api=definition(cache_ttl_seconds=10, rate_limit_requests=2), transport=transport
        )
        gateway.execute(REQUEST, global_enabled=True, provider_enabled=True)
        cached = gateway.execute(REQUEST, global_enabled=True, provider_enabled=True)
        gateway.execute(
            ExternalAPIRequest("fixture_api", "GET", "/other"),
            global_enabled=True,
            provider_enabled=True,
        )
        self.assertTrue(cached.provenance["cached"])
        self.assertEqual(len(transport.calls), 2)

    def test_observability_never_emits_query_or_coordinates(self) -> None:
        events: list[tuple[str, dict[str, object]]] = []
        gateway_for(events=events).execute(REQUEST, global_enabled=True, provider_enabled=True)
        serialized = json.dumps(events)
        self.assertIn("external_api.request_started", serialized)
        self.assertIn("external_api.request_succeeded", serialized)
        self.assertNotIn("safe=value", serialized)


if __name__ == "__main__":
    unittest.main()
