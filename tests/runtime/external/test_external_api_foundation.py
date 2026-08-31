from __future__ import annotations

import json
import os
import sys
import unittest
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.external.config import (
    EXTERNAL_API_ENABLED_ENV,
    external_api_enabled,
)  # noqa: E402
from brain.runtime.external.models import AuthenticationType, ExternalAPIDefinition  # noqa: E402
from brain.runtime.external.policy import ExternalAPIPolicy, ExternalAPIPolicyError  # noqa: E402
from brain.runtime.external.provenance import ExternalResponseProvenance  # noqa: E402
from brain.runtime.external.registry import ExternalAPIRegistry  # noqa: E402


def safe_definition(
    *, api_id: str = "fixture_api", enabled: bool = True, **overrides: object
) -> ExternalAPIDefinition:
    values = {
        "api_id": api_id,
        "name": "Fixture API",
        "description": "Test-only external API fixture",
        "base_url": "https://api.example.com/v1",
        "allowed_hosts": frozenset({"api.example.com"}),
        "allowed_methods": frozenset({"GET"}),
        "allowed_paths": frozenset({"/", "/v1", "/v1/items"}),
        "enabled": enabled,
        "provenance": "test_fixture",
    }
    values.update(overrides)
    return ExternalAPIDefinition(**values)


class ExternalAPIRegistryTest(unittest.TestCase):
    def test_register_and_lookup(self) -> None:
        registry = ExternalAPIRegistry()
        definition = safe_definition()
        registry.register(definition)
        self.assertIs(registry.get("fixture_api"), definition)
        self.assertTrue(registry.is_registered("fixture_api"))
        self.assertEqual(registry.list(), (definition,))

    def test_duplicate_id_is_rejected(self) -> None:
        registry = ExternalAPIRegistry()
        registry.register(safe_definition())
        with self.assertRaises(ValueError):
            registry.register(safe_definition())

    def test_missing_lookup_fails_safely(self) -> None:
        self.assertIsNone(ExternalAPIRegistry().get("missing"))

    def test_invalid_configuration_is_rejected(self) -> None:
        registry = ExternalAPIRegistry()
        with self.assertRaises(ExternalAPIPolicyError):
            registry.register(safe_definition(base_url="http://api.example.com"))

    def test_unknown_authentication_never_registers(self) -> None:
        registry = ExternalAPIRegistry()
        with self.assertRaises(ExternalAPIPolicyError):
            registry.register(safe_definition(auth_type=AuthenticationType.UNKNOWN))


class ExternalAPIPolicyTest(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = ExternalAPIRegistry()
        self.registry.register(safe_definition())
        self.policy = ExternalAPIPolicy(self.registry)

    def test_only_registered_safe_fixture_is_accepted(self) -> None:
        decision = self.policy.evaluate(
            api_id="fixture_api",
            endpoint="https://api.example.com/v1/items",
            method="GET",
            feature_enabled=True,
        )
        self.assertTrue(decision.allowed)

    def test_unsafe_urls_are_rejected(self) -> None:
        cases = {
            "http://api.example.com": "https_required",
            "https://localhost/test": "localhost_denied",
            "https://127.0.0.1/test": "non_public_ip_denied",
            "https://10.0.0.1/test": "non_public_ip_denied",
            "https://192.168.1.1/test": "non_public_ip_denied",
            "https://169.254.1.1/test": "non_public_ip_denied",
            "https://user:password@api.example.com/test": "embedded_credentials_denied",
            "https://other.example.com/test": "host_not_allowlisted",
        }
        for endpoint, reason in cases.items():
            with self.subTest(endpoint=endpoint):
                decision = self.policy.evaluate(
                    api_id="fixture_api", endpoint=endpoint, method="GET", feature_enabled=True
                )
                self.assertFalse(decision.allowed)
                self.assertEqual(decision.reason, reason)

    def test_method_disabled_and_unknown_api_are_rejected(self) -> None:
        self.assertEqual(
            self.policy.evaluate(
                api_id="fixture_api",
                endpoint="https://api.example.com",
                method="POST",
                feature_enabled=True,
            ).reason,
            "method_not_allowed",
        )
        self.assertEqual(
            self.policy.evaluate(
                api_id="missing",
                endpoint="https://api.example.com",
                method="GET",
                feature_enabled=True,
            ).reason,
            "unknown_api",
        )

    def test_disabled_api_is_rejected(self) -> None:
        registry = ExternalAPIRegistry()
        registry.register(safe_definition(enabled=False))
        decision = ExternalAPIPolicy(registry).evaluate(
            api_id="fixture_api",
            endpoint="https://api.example.com",
            method="GET",
            feature_enabled=True,
        )
        self.assertEqual(decision.reason, "api_disabled")


class ExternalAPIFeatureGateTest(unittest.TestCase):
    def test_gate_defaults_off_and_only_explicit_truthy_values_enable(self) -> None:
        for value, expected in (
            (None, False),
            ("false", False),
            ("invalid", False),
            ("true", True),
        ):
            with self.subTest(value=value), patch.dict(os.environ, {}, clear=False):
                os.environ.pop(EXTERNAL_API_ENABLED_ENV, None)
                if value is not None:
                    os.environ[EXTERNAL_API_ENABLED_ENV] = value
                self.assertIs(external_api_enabled(), expected)


class ExternalAPIProvenanceTest(unittest.TestCase):
    def test_serialized_provenance_has_no_secret_fields(self) -> None:
        payload = ExternalResponseProvenance(
            source_type="external_api",
            provider="fixture",
            api_id="fixture_api",
            retrieved_at=datetime(2026, 1, 1, tzinfo=UTC),
            endpoint="https://api.example.com/items?api_key=must-not-be-serialized",
            cached=False,
            freshness="fresh",
            request_id="request-1",
        ).as_dict()
        serialized = json.dumps(payload).lower()
        for forbidden in ("api_key", "authorization", "cookie", "token", "password"):
            self.assertNotIn(forbidden, serialized)
        self.assertEqual(payload["endpoint"], "https://api.example.com/items")


if __name__ == "__main__":
    unittest.main()
