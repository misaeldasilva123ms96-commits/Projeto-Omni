from __future__ import annotations

import json
import os
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from urllib.error import HTTPError
from unittest.mock import patch

from backend.python.config.provider_health import (
    provider_health_probe_allowed,
    read_provider_health,
    record_provider_health,
)
from backend.python.config.provider_settings_controller import (
    ProviderSettingsController,
    _test_anthropic,
    _test_openai_compatible,
)


class _MetadataStore:
    def list_credential_metadata(self, user_id: str):
        return [SimpleNamespace(provider_id="openai", updated_at=1234)]


class ProviderHealthCacheTest(unittest.TestCase):
    def setUp(self) -> None:
        self._temporary = tempfile.TemporaryDirectory()
        self._environment = patch.dict(
            os.environ,
            {
                "OMNI_PROVIDER_HEALTH_CACHE_DIR": self._temporary.name,
                "OMNI_PROVIDER_HEALTH_TTL_MS": "1000",
                "OMNI_PROVIDER_HEALTH_FAILURE_THRESHOLD": "3",
                "OMNI_PROVIDER_HEALTH_CIRCUIT_OPEN_MS": "2000",
            },
            clear=False,
        )
        self._environment.start()

    def tearDown(self) -> None:
        self._environment.stop()
        self._temporary.cleanup()

    def test_missing_snapshot_is_unknown_and_does_not_probe(self) -> None:
        snapshot = read_provider_health("user-1", "openai", now_ms=1000)
        self.assertIsNone(snapshot["reachable"])
        self.assertIsNone(snapshot["healthy"])
        self.assertFalse(snapshot["health_valid"])
        self.assertEqual(snapshot["cache_status"], "missing")
        self.assertEqual(list(Path(self._temporary.name).iterdir()), [])

    def test_success_snapshot_records_latency_and_validity_without_identity(self) -> None:
        snapshot = record_provider_health(
            "private-user-id",
            "openai",
            reachable=True,
            healthy=True,
            latency_ms=42,
            now_ms=10_000,
        )
        self.assertTrue(snapshot["reachable"])
        self.assertTrue(snapshot["healthy"])
        self.assertTrue(snapshot["health_valid"])
        self.assertEqual(snapshot["latency_ms"], 42)
        self.assertEqual(snapshot["valid_until"], 11_000)
        self.assertEqual(snapshot["circuit_state"], "closed")

        cache_files = list(Path(self._temporary.name).glob("*.json"))
        self.assertEqual(len(cache_files), 1)
        serialized = cache_files[0].read_text(encoding="utf-8")
        self.assertNotIn("private-user-id", serialized)
        self.assertNotIn("api_key", serialized.lower())

    def test_expired_snapshot_is_explicitly_stale(self) -> None:
        record_provider_health(
            "user-1",
            "openai",
            reachable=True,
            healthy=True,
            latency_ms=10,
            now_ms=1_000,
        )
        snapshot = read_provider_health("user-1", "openai", now_ms=2_001)
        self.assertFalse(snapshot["health_valid"])
        self.assertEqual(snapshot["cache_status"], "stale")
        self.assertTrue(snapshot["healthy"])

    def test_failure_threshold_opens_then_half_opens_circuit(self) -> None:
        for now_ms in (1_000, 1_100, 1_200):
            snapshot = record_provider_health(
                "user-1",
                "openai",
                reachable=False,
                healthy=False,
                latency_ms=5,
                now_ms=now_ms,
            )
        self.assertEqual(snapshot["consecutive_failures"], 3)
        self.assertEqual(snapshot["circuit_state"], "open")
        allowed, blocked = provider_health_probe_allowed("user-1", "openai", now_ms=2_000)
        self.assertFalse(allowed)
        self.assertEqual(blocked["circuit_state"], "open")
        allowed, half_open = provider_health_probe_allowed("user-1", "openai", now_ms=3_200)
        self.assertTrue(allowed)
        self.assertEqual(half_open["circuit_state"], "half_open")

    def test_corrupt_cache_fails_to_unknown(self) -> None:
        record_provider_health(
            "user-1",
            "openai",
            reachable=True,
            healthy=True,
            latency_ms=1,
            now_ms=1_000,
        )
        cache_file = next(Path(self._temporary.name).glob("*.json"))
        cache_file.write_text("not-json", encoding="utf-8")
        snapshot = read_provider_health("user-1", "openai", now_ms=1_001)
        self.assertEqual(snapshot["cache_status"], "missing")
        self.assertIsNone(snapshot["healthy"])


class ProviderSettingsHealthTest(unittest.TestCase):
    def setUp(self) -> None:
        self._temporary = tempfile.TemporaryDirectory()
        self._environment = patch.dict(
            os.environ,
            {
                "OMNI_PROVIDER_HEALTH_CACHE_DIR": self._temporary.name,
                "OMNI_PROVIDER_HEALTH_FAILURE_THRESHOLD": "3",
                "OMNI_PROVIDER_HEALTH_CIRCUIT_OPEN_MS": "60000",
            },
            clear=False,
        )
        self._environment.start()

    def tearDown(self) -> None:
        self._environment.stop()
        self._temporary.cleanup()

    def test_list_separates_configuration_execution_and_unknown_health(self) -> None:
        controller = ProviderSettingsController(store=_MetadataStore())
        rows = {row["provider"]: row for row in controller.list_providers("user-1")}
        self.assertTrue(rows["openai"]["configured"])
        self.assertTrue(rows["openai"]["executable"])
        self.assertTrue(rows["openai"]["available"])
        self.assertIsNone(rows["openai"]["reachable"])
        self.assertIsNone(rows["openai"]["healthy"])
        self.assertFalse(rows["openai"]["health_valid"])
        self.assertFalse(rows["groq"]["configured"])
        self.assertTrue(rows["groq"]["executable"])
        self.assertFalse(rows["groq"]["available"])
        self.assertFalse(rows["deepseek"]["executable"])

    @patch(
        "backend.python.config.provider_settings_controller._run_provider_test",
        return_value={"success": True, "reachable": True},
    )
    def test_manual_test_records_fresh_health(self, provider_test) -> None:
        controller = ProviderSettingsController(store=object())
        result = controller.test_provider("user-1", "openai", "test-secret")
        self.assertTrue(result["success"])
        self.assertTrue(result["reachable"])
        self.assertTrue(result["healthy"])
        self.assertTrue(result["health_valid"])
        self.assertFalse(result["cached"])
        self.assertIsInstance(result["last_checked_at"], int)
        self.assertIsInstance(result["latency_ms"], int)
        provider_test.assert_called_once_with(
            provider_id="openai",
            secret="test-secret",
        )

    @patch(
        "backend.python.config.provider_settings_controller._run_provider_test",
        return_value={
            "success": False,
            "reachable": False,
            "error": "Unable to reach provider",
        },
    )
    def test_open_circuit_reuses_safe_cached_failure(self, provider_test) -> None:
        controller = ProviderSettingsController(store=object())
        for _ in range(3):
            result = controller.test_provider("user-1", "openai", "test-secret")
        self.assertEqual(result["circuit_state"], "open")

        blocked = controller.test_provider("user-1", "openai", "test-secret")
        self.assertFalse(blocked["success"])
        self.assertTrue(blocked["cached"])
        self.assertEqual(blocked["error"], "Provider health circuit is open")
        self.assertEqual(provider_test.call_count, 3)

    @patch("backend.python.config.provider_settings_controller._run_provider_test")
    def test_unsupported_adapter_never_contacts_provider(self, provider_test) -> None:
        controller = ProviderSettingsController(store=object())
        result = controller.test_provider("user-1", "deepseek", "test-secret")
        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "Provider adapter is not executable")
        provider_test.assert_not_called()

    @patch("backend.python.config.provider_settings_controller._run_provider_test")
    def test_local_provider_without_safe_probe_stays_unknown(self, provider_test) -> None:
        controller = ProviderSettingsController(store=object())
        result = controller.test_provider("user-1", "ollama", "test-secret")
        self.assertFalse(result["success"])
        self.assertIsNone(result["reachable"])
        self.assertIsNone(result["healthy"])
        self.assertEqual(
            result["error"],
            "Active health test is not supported for this provider",
        )
        provider_test.assert_not_called()

    def test_cache_payload_contains_only_health_metadata(self) -> None:
        record_provider_health(
            "user-1",
            "openai",
            reachable=True,
            healthy=True,
            latency_ms=1,
            now_ms=1_000,
        )
        payload = json.loads(next(Path(self._temporary.name).glob("*.json")).read_text())
        self.assertNotIn("provider", payload)
        self.assertNotIn("user", payload)
        self.assertNotIn("secret", payload)

    @patch(
        "backend.python.config.provider_settings_controller._http_get",
        return_value=SimpleNamespace(status_code=401),
    )
    def test_auth_failure_is_reachable_but_not_healthy(self, _http_get) -> None:
        result = _test_openai_compatible("openai", "test-secret")
        self.assertFalse(result["success"])
        self.assertTrue(result["reachable"])
        self.assertEqual(result["error"], "Invalid API key")

    @patch(
        "backend.python.config.provider_settings_controller._http_get",
        side_effect=OSError("connection refused"),
    )
    def test_transport_failure_is_not_reachable(self, _http_get) -> None:
        result = _test_openai_compatible("openai", "test-secret")
        self.assertFalse(result["success"])
        self.assertFalse(result["reachable"])
        self.assertEqual(result["error"], "Unable to reach provider")

    @patch("backend.python.config.provider_settings_controller._http_post")
    def test_anthropic_http_error_body_classifies_invalid_key(self, http_post) -> None:
        body = json.dumps({"error": {"type": "authentication_error"}}).encode()
        http_post.side_effect = HTTPError(
            url="https://api.anthropic.com/v1/messages",
            code=400,
            msg="Bad Request",
            hdrs=None,
            fp=BytesIO(body),
        )
        result = _test_anthropic("test-secret")
        self.assertFalse(result["success"])
        self.assertTrue(result["reachable"])
        self.assertEqual(result["error"], "Invalid API key")


if __name__ == "__main__":
    unittest.main()
