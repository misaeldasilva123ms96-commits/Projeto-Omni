from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.external.adapters.urlhaus import (  # noqa: E402
    URLReputationInput,
    check_url_reputation,
)
from brain.runtime.external.credentials import (  # noqa: E402
    EnvironmentCredentialResolver,
    ResolvedCredential,
)
from brain.runtime.external.gateway import (  # noqa: E402
    ExternalAPIGateway,
    ExternalGatewayError,
    LocalRateLimiter,
    TTLResponseCache,
    TransportResponse,
)
from brain.runtime.external.models import ExternalAPIRequest  # noqa: E402
from brain.runtime.external.providers import build_external_api_registry  # noqa: E402
from brain.runtime.external.tools import execute_external_action  # noqa: E402
from brain.runtime.execution.models import ExecutionIntent, RiskLevel  # noqa: E402
from brain.runtime.execution.risk_classifier import DeterministicRiskClassifier  # noqa: E402
from brain.runtime.orchestrator import BrainOrchestrator  # noqa: E402
from test_gateway import FakeClock, FakeResolver, FakeTransport  # noqa: E402

SECRET = "SUPER_SECRET_URLHAUS_TEST_KEY_SENTINEL"


class FakeCredentialResolver:
    def __init__(self, outcome=ResolvedCredential("Auth-Key", SECRET)):
        self.outcome = outcome
        self.calls = 0

    def resolve(self, credential_id):
        self.calls += 1
        if isinstance(self.outcome, Exception):
            raise self.outcome
        assert credential_id == "urlhaus_auth_key"
        return self.outcome


class TrackingResolver(FakeResolver):
    def __init__(self):
        super().__init__()
        self.hosts = []

    def resolve(self, host, port):
        self.hosts.append(host)
        return super().resolve(host, port)


def gateway(payload, *, credential=None, status=200):
    clock = FakeClock()
    transport = FakeTransport(
        [TransportResponse(status, {}, json.dumps(payload).encode(), "93.184.216.34")]
    )
    resolver = TrackingResolver()
    credentials = credential or FakeCredentialResolver()
    return (
        ExternalAPIGateway(
            registry=build_external_api_registry(),
            resolver=resolver,
            transport=transport,
            cache=TTLResponseCache(clock=clock),
            rate_limiter=LocalRateLimiter(clock=clock),
            sleeper=lambda _: None,
            credential_resolver=credentials,
        ),
        transport,
        resolver,
        credentials,
    )


@pytest.mark.parametrize(
    "value",
    [
        "file:///x",
        "ftp://example.com/x",
        "javascript:alert(1)",
        "https://user:pass@example.com/",
        "http://localhost/x",
        "http://a.local/x",
        "http://internal/x",
        "http://127.0.0.1/x",
        "http://10.0.0.1/x",
        "http://[::1]/x",
        " https://example.com/",
        "https://example.com/\r\n",
    ],
)
def test_url_validation_denies_unsafe_indicators(value):
    with pytest.raises(ValueError):
        URLReputationInput(value).normalized()


def test_fragment_is_stripped_but_query_preserved():
    assert URLReputationInput("HTTPS://Example.COM:443/a?token=x#private").normalized() == (
        "https://example.com/a?token=x"
    )


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (
            "https://[2606:4700:4700::1111]/path",
            "https://[2606:4700:4700::1111]/path",
        ),
        (
            "https://[2606:4700:4700:0:0:0:0:1111]/path",
            "https://[2606:4700:4700::1111]/path",
        ),
        (
            "https://[2606:4700:4700::1111]:443/path",
            "https://[2606:4700:4700::1111]/path",
        ),
        (
            "http://[2606:4700:4700::1111]:80/path",
            "http://[2606:4700:4700::1111]/path",
        ),
        (
            "https://[2606:4700:4700::1111]:8443/path",
            "https://[2606:4700:4700::1111]:8443/path",
        ),
        (
            "https://[2606:4700:4700::1111]/x?a=1#secret",
            "https://[2606:4700:4700::1111]/x?a=1",
        ),
        ("https://8.8.8.8/path", "https://8.8.8.8/path"),
        ("HTTPS://Example.COM:443/a", "https://example.com/a"),
    ],
)
def test_host_type_normalization(value, expected):
    assert URLReputationInput(value).normalized() == expected


@pytest.mark.parametrize(
    "value",
    [
        "http://[::1]/",
        "http://[fd00::1]/",
        "http://[fe80::1]/",
        "http://127.0.0.1/",
        "http://10.0.0.1/",
        "http://172.16.0.1/",
        "http://192.168.0.1/",
        "http://169.254.0.1/",
    ],
)
def test_non_global_ip_literals_remain_denied(value):
    with pytest.raises(ValueError, match="internal_url_not_allowed"):
        URLReputationInput(value).normalized()


def test_public_ipv6_form_round_trip_never_resolves_target():
    gw, transport, resolver, _ = gateway({"query_status": "no_results"})
    result = check_url_reputation(
        URLReputationInput("https://[2606:4700:4700::1111]/x?a=1#secret"),
        gateway=gw,
        global_enabled=True,
        provider_enabled=True,
    )
    decoded = parse_qs(transport.calls[0]["body"].decode("ascii"))
    assert decoded == {"url": ["https://[2606:4700:4700::1111]/x?a=1"]}
    assert result.status == "not_listed"
    assert resolver.hosts == ["urlhaus-api.abuse.ch"]
    assert len(transport.calls) == 1


@pytest.mark.parametrize(
    ("global_on", "provider_on", "error"),
    [(False, True, "external_api_disabled"), (True, False, "provider_disabled")],
)
def test_gates_precede_credentials_and_transport(global_on, provider_on, error):
    gw, transport, resolver, credentials = gateway({"query_status": "no_results"})
    with pytest.raises(ExternalGatewayError, match=error):
        check_url_reputation(
            URLReputationInput("https://example.com/x"),
            gateway=gw,
            global_enabled=global_on,
            provider_enabled=provider_on,
        )
    assert credentials.calls == resolver.calls == 0 and transport.calls == []


def test_missing_credential_fails_before_network():
    credentials = FakeCredentialResolver(ValueError("credential_unavailable"))
    gw, transport, resolver, _ = gateway({}, credential=credentials)
    with pytest.raises(ExternalGatewayError, match="credential_unavailable"):
        check_url_reputation(
            URLReputationInput("https://example.com/x"),
            gateway=gw,
            global_enabled=True,
            provider_enabled=True,
        )
    assert resolver.calls == 0 and transport.calls == []


def test_provider_auth_failure_is_secret_free_and_not_retried():
    gw, transport, _, _ = gateway({}, status=401)
    with pytest.raises(ExternalGatewayError, match="provider_auth_failed") as caught:
        check_url_reputation(
            URLReputationInput("https://example.com/x"),
            gateway=gw,
            global_enabled=True,
            provider_enabled=True,
        )
    assert len(transport.calls) == 1 and SECRET not in str(caught.value)


def test_trusted_header_form_and_no_target_fetch():
    gw, transport, resolver, _ = gateway({"query_status": "no_results"})
    events = []
    result = check_url_reputation(
        URLReputationInput("https://example.com/a?q=secret#fragment"),
        gateway=gw,
        global_enabled=True,
        provider_enabled=True,
        event_sink=lambda name, payload: events.append((name, payload)),
    )
    call = transport.calls[0]
    assert result.status == "not_listed"
    assert call["logical_host"] == "urlhaus-api.abuse.ch" and call["method"] == "POST"
    assert call["target"] == "/v1/url/" and call["headers"]["Auth-Key"] == SECRET
    assert call["headers"]["Content-Type"] == "application/x-www-form-urlencoded"
    assert call["body"] == b"url=https%3A%2F%2Fexample.com%2Fa%3Fq%3Dsecret"
    assert resolver.calls == 1
    serialized = json.dumps(result.as_dict(), default=str)
    assert SECRET not in serialized and "fragment" not in call["body"].decode()
    assert SECRET not in json.dumps(events) and "example.com" not in json.dumps(events)
    assert not any(
        word in serialized.lower() for word in ('"safe": true', '"benign": true', '"trusted": true')
    )


def test_positive_match_is_bounded_and_discards_payloads():
    payload = {
        "query_status": "ok",
        "url_status": "online",
        "threat": "malware_download",
        "date_added": "2026-08-29",
        "tags": ["x" * 200] * 30,
        "payloads": [{"download_url": "https://malware.invalid/file"}],
    }
    gw, _, _, _ = gateway(payload)
    result = check_url_reputation(
        URLReputationInput("https://example.com/x"),
        gateway=gw,
        global_enabled=True,
        provider_enabled=True,
    ).as_dict()
    assert result["status"] == "listed" and len(result["tags"]) == 20
    assert result["classification"] == "known_malware_url"
    assert len(result["tags"][0]) == 100 and "payload" not in json.dumps(result).lower()


def test_cache_identity_is_digest_only_and_credential_required_on_hit():
    request = ExternalAPIRequest(
        api_id="urlhaus",
        method="POST",
        path="/v1/url/",
        form_fields={"url": "https://example.com/private?q=secret"},
    )
    key = ExternalAPIGateway._cache_key(request)
    assert "example.com" not in key and "secret" not in key and SECRET not in key


def test_cached_response_still_requires_credential():
    credentials = FakeCredentialResolver()
    gw, transport, _, _ = gateway({"query_status": "no_results"}, credential=credentials)
    value = URLReputationInput("https://example.com/x")
    check_url_reputation(value, gateway=gw, global_enabled=True, provider_enabled=True)
    credentials.outcome = ValueError("credential_unavailable")
    with pytest.raises(ExternalGatewayError, match="credential_unavailable"):
        check_url_reputation(value, gateway=gw, global_enabled=True, provider_enabled=True)
    assert len(transport.calls) == 1 and credentials.calls == 2


def test_no_auth_provider_never_resolves_credentials():
    credentials = FakeCredentialResolver(AssertionError("must not resolve"))
    gw, transport, _, _ = gateway(
        [{"date": "2026-08-29", "base": "USD", "quote": "BRL", "rate": "5"}],
        credential=credentials,
    )
    response = gw.execute(
        ExternalAPIRequest(
            api_id="frankfurter",
            method="GET",
            path="/v2/rates",
            query={"base": "USD", "quotes": "BRL"},
        ),
        global_enabled=True,
        provider_enabled=True,
    )
    assert response.status_code == 200 and credentials.calls == 0 and len(transport.calls) == 1


@pytest.mark.parametrize(
    "value", [None, "", "   ", "value\r\nInjected: yes", "x\0y", "x" * 513, "placeholder"]
)
def test_environment_credential_validation(monkeypatch, value):
    environment = {} if value is None else {"OMNI_EXTERNAL_URLHAUS_AUTH_KEY": value}
    with patch("brain.runtime.external.credentials.os.environ", environment):
        with pytest.raises(ValueError, match="credential_(unavailable|invalid)"):
            EnvironmentCredentialResolver().resolve("urlhaus_auth_key")


@pytest.mark.parametrize("header", ["Auth-Key", "Authorization", "X-API-Key", "api-key"])
def test_caller_sensitive_headers_are_denied(header):
    with pytest.raises(ValueError):
        ExternalAPIRequest(
            api_id="urlhaus",
            method="POST",
            path="/v1/url/",
            headers={header: "caller-secret"},
            form_fields={"url": "https://example.com/"},
        )


def test_tool_runtime_truth_and_orchestrator_redaction(monkeypatch):
    monkeypatch.setenv("OMNI_EXTERNAL_API_ENABLED", "true")
    monkeypatch.setenv("OMNI_EXTERNAL_URLHAUS_ENABLED", "true")
    gw, _, _, _ = gateway({"query_status": "no_results"})
    outcome = execute_external_action(
        action={
            "selected_tool": "url_reputation_check",
            "tool_arguments": {"url": "https://example.com/private?q=secret"},
        },
        gateway=gw,
    )
    assert outcome["runtime_truth"] == {
        "source": "external_api",
        "provider": "urlhaus",
        "tool": "url_reputation_check",
        "cached": False,
    }
    redacted = BrainOrchestrator._redact_external_action(
        {
            "selected_tool": "url_reputation_check",
            "tool_arguments": {"url": "https://example.com/private?q=secret"},
        }
    )
    assert "example.com" not in json.dumps(redacted)


def test_tool_is_medium_risk_due_to_privacy_and_security_decision_boundary():
    classification = DeterministicRiskClassifier().classify(
        ExecutionIntent(
            action_id="urlhaus-test",
            capability="url_reputation_check",
            action_type="read",
            description="advisory URL lookup",
            target_subsystem="external_api",
            input_payload_summary={},
            expected_outcome="bounded reputation metadata",
            reversible=True,
        )
    )
    assert classification.level is RiskLevel.MEDIUM
