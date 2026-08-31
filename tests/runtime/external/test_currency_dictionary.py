from __future__ import annotations

import json
import os
import sys
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.external.adapters.frankfurter import (  # noqa: E402
    CurrencyConvertInput,
    convert_currency,
)
from brain.runtime.external.adapters.free_dictionary import (  # noqa: E402
    DictionaryLookupInput,
    lookup_dictionary,
)
from brain.runtime.external.config import (  # noqa: E402
    EXTERNAL_API_ENABLED_ENV,
    FRANKFURTER_ENABLED_ENV,
)
from brain.runtime.external.gateway import (  # noqa: E402
    ExternalAPIGateway,
    ExternalGatewayError,
    LocalRateLimiter,
    TTLResponseCache,
    TransportResponse,
)
from brain.runtime.external.models import SafePathTemplate  # noqa: E402
from brain.runtime.external.policy import ExternalAPIPolicy  # noqa: E402
from brain.runtime.external.providers import build_external_api_registry  # noqa: E402
from brain.runtime.external.tools import execute_external_action  # noqa: E402
from brain.runtime.orchestrator import BrainOrchestrator  # noqa: E402
from test_gateway import FakeClock, FakeResolver, FakeTransport  # noqa: E402


def gateway(payload: object, *, status: int = 200):
    clock = FakeClock()
    transport = FakeTransport(
        [TransportResponse(status, {}, json.dumps(payload).encode(), "93.184.216.34")]
    )
    return (
        ExternalAPIGateway(
            registry=build_external_api_registry(),
            resolver=FakeResolver(),
            transport=transport,
            cache=TTLResponseCache(clock=clock),
            rate_limiter=LocalRateLimiter(clock=clock),
            sleeper=lambda _: None,
        ),
        transport,
    )


def test_currency_decimal_fixed_request_cache_and_identity():
    gw, transport = gateway([{"date": "2026-08-29", "base": "USD", "quote": "BRL", "rate": 3}])
    result = convert_currency(
        CurrencyConvertInput("0.1", "usd", "brl"),
        gateway=gw,
        global_enabled=True,
        provider_enabled=True,
    )
    assert result.converted_amount == "0.30"
    assert result.rate == "3"
    assert (
        "base=USD" in transport.calls[0]["target"] and "quotes=BRL" in transport.calls[0]["target"]
    )


@pytest.mark.parametrize(
    ("global_enabled", "provider_enabled", "error"),
    [(False, True, "external_api_disabled"), (True, False, "provider_disabled")],
)
def test_same_currency_explicit_gates_deny_without_transport(
    global_enabled, provider_enabled, error
):
    gw, transport = gateway([])
    with pytest.raises(ExternalGatewayError, match=error):
        convert_currency(
            CurrencyConvertInput("2.50", "EUR", "EUR"),
            gateway=gw,
            global_enabled=global_enabled,
            provider_enabled=provider_enabled,
        )
    assert transport.calls == []
    assert gw.resolver.calls == 0


def test_same_currency_default_gates_deny_without_transport():
    gw, transport = gateway([])
    with patch.dict(
        os.environ,
        {
            "OMNI_EXTERNAL_API_ENABLED": "false",
            "OMNI_EXTERNAL_FRANKFURTER_ENABLED": "false",
        },
    ):
        with pytest.raises(ExternalGatewayError, match="external_api_disabled"):
            convert_currency(CurrencyConvertInput("2.50", "EUR", "EUR"), gateway=gw)
    assert transport.calls == []
    assert gw.resolver.calls == 0


def test_same_currency_enabled_is_local_and_runtime_truthful():
    gw, transport = gateway([])
    with patch.dict(
        os.environ,
        {
            "OMNI_EXTERNAL_API_ENABLED": "true",
            "OMNI_EXTERNAL_FRANKFURTER_ENABLED": "true",
        },
    ):
        outcome = execute_external_action(
            action={
                "selected_tool": "currency_convert",
                "tool_arguments": {
                    "amount": Decimal("2.50"),
                    "from_currency": "EUR",
                    "to_currency": "EUR",
                },
            },
            gateway=gw,
        )
    assert outcome["ok"] is True
    assert outcome["result_payload"]["rate"] == "1"
    assert outcome["result_payload"]["converted_amount"] == "2.50"
    assert outcome["result_payload"]["provider"] != "Frankfurter"
    assert outcome["result_payload"]["provenance"] == {
        "source_type": "local_compute",
        "provider": "local",
        "cached": False,
        "freshness": "local_identity",
    }
    assert outcome["runtime_truth"] == {
        "source": "local_computation",
        "provider": "local",
        "tool": "currency_convert",
        "cached": False,
    }
    assert transport.calls == []
    assert gw.resolver.calls == 0


def test_cross_currency_runtime_truth_remains_external():
    gw, transport = gateway([{"date": "2026-08-29", "base": "USD", "quote": "BRL", "rate": "5.1"}])
    with patch.dict(
        os.environ,
        {
            "OMNI_EXTERNAL_API_ENABLED": "true",
            "OMNI_EXTERNAL_FRANKFURTER_ENABLED": "true",
        },
    ):
        outcome = execute_external_action(
            action={
                "selected_tool": "currency_convert",
                "tool_arguments": {
                    "amount": "10",
                    "from_currency": "USD",
                    "to_currency": "BRL",
                },
            },
            gateway=gw,
        )
    assert outcome["ok"] is True
    assert outcome["runtime_truth"]["source"] == "external_api"
    assert outcome["runtime_truth"]["provider"] == "frankfurter"
    assert len(transport.calls) == 1


@pytest.mark.parametrize("amount", [0, -1, float("nan"), float("inf"), "NaN", "1000000000001"])
def test_currency_rejects_unsafe_amounts(amount):
    with pytest.raises(ValueError):
        CurrencyConvertInput(amount, "USD", "BRL").normalized()


@pytest.mark.parametrize(
    "word", ["a/b", "a%2Fb", "%", ".", "..", "a?b", "a#b", "a\r\n", "\0", "https://x", "a\\b"]
)
def test_dictionary_rejects_unsafe_segments(word):
    with pytest.raises(ValueError):
        DictionaryLookupInput(word).normalized()


def test_dictionary_bounds_and_ignores_audio():
    payload = [
        {
            "word": "hello",
            "phonetics": [{"text": "/həˈləʊ/", "audio": "https://evil.test/a"}],
            "meanings": [
                {
                    "partOfSpeech": "noun",
                    "synonyms": [str(x) for x in range(20)],
                    "antonyms": [str(x) for x in range(20)],
                    "definitions": [
                        {"definition": "x" * 2000, "example": "y" * 2000} for _ in range(10)
                    ],
                }
            ],
        }
    ]
    gw, _ = gateway(payload)
    result = lookup_dictionary(
        DictionaryLookupInput("Hello"), gateway=gw, global_enabled=True, provider_enabled=True
    ).as_dict()
    assert len(result["meanings"][0]["definitions"]) == 3
    assert len(result["meanings"][0]["synonyms"]) == 10
    assert len(result["meanings"][0]["definitions"][0]["definition"]) == 1000
    assert "audio" not in str(result).lower()


@pytest.mark.parametrize(
    "path",
    [
        "/api/v2/entries/fr/hello",
        "/api/v1/entries/en/hello",
        "/api/v2/entries/en/a/b",
        "/api/v2/entries/en/../admin",
        "/admin",
        "//api/v2/entries/en/hello",
    ],
)
def test_safe_template_denies_wrong_authority(path):
    assert not SafePathTemplate.FREE_DICTIONARY_ENGLISH_WORD.matches(path)


def test_policy_accepts_only_typed_dictionary_path():
    policy = ExternalAPIPolicy(build_external_api_registry())
    assert policy.evaluate(
        api_id="free_dictionary",
        endpoint="https://api.dictionaryapi.dev/api/v2/entries/en/don't",
        method="GET",
        feature_enabled=True,
    ).allowed
    assert not policy.evaluate(
        api_id="free_dictionary",
        endpoint="https://api.dictionaryapi.dev/api/v2/entries/en/a/b",
        method="GET",
        feature_enabled=True,
    ).allowed


def test_runtime_truth_and_privacy_redaction():
    gw, _ = gateway([{"date": "2026-08-29", "base": "USD", "quote": "BRL", "rate": "5.1"}])
    with patch.dict(
        os.environ,
        {EXTERNAL_API_ENABLED_ENV: "false", FRANKFURTER_ENABLED_ENV: "false"},
    ):
        outcome = execute_external_action(
            action={
                "selected_tool": "currency_convert",
                "tool_arguments": {
                    "amount": "100",
                    "from_currency": "USD",
                    "to_currency": "BRL",
                },
            },
            gateway=gw,
        )
    # Explicit gates deny execution, while redaction never retains the amount.
    assert not outcome["ok"]
    redacted = BrainOrchestrator._redact_external_action(
        {
            "selected_tool": "currency_convert",
            "tool_arguments": {"amount": "100", "from_currency": "USD", "to_currency": "BRL"},
        }
    )
    assert (
        "amount" not in redacted["tool_arguments"] and redacted["tool_arguments"]["amount_supplied"]
    )
    dictionary = BrainOrchestrator._redact_external_action(
        {"selected_tool": "dictionary_lookup", "tool_arguments": {"word": "secret"}}
    )
    assert dictionary["tool_arguments"] == {"dictionary_word": "redacted", "word_length": 6}
