from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.providers.models import ProviderHealth, ProviderRequest, ProviderResponse, ProviderType
from config.provider_registry import (
    PROVIDERS,
    describe_provider_diagnostics,
    get_available_providers,
    provider_metadata,
    providers_capability,
)


PROVIDER_ENV_KEYS = (
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "GROQ_API_KEY",
    "GEMINI_API_KEY",
    "DEEPSEEK_API_KEY",
    "OPENROUTER_API_KEY",
    "OLLAMA_URL",
    "LMSTUDIO_URL",
)


class ProviderRegistryTest(unittest.TestCase):
    def test_providers_list_is_stable(self) -> None:
        self.assertEqual(
            PROVIDERS,
            ("groq", "openrouter", "openai", "anthropic", "gemini", "deepseek", "ollama", "lmstudio"),
        )

    def test_provider_metadata_marks_unsupported_and_local_parity(self) -> None:
        rows = {row["provider"]: row for row in provider_metadata()}
        self.assertEqual(set(rows), set(PROVIDERS))
        self.assertTrue(rows["groq"]["registered"])
        self.assertTrue(rows["groq"]["adapter_implemented"])
        self.assertEqual(rows["groq"]["execution_status"], "credential_gated")
        for provider in ("openrouter", "openai", "anthropic", "gemini", "deepseek"):
            self.assertTrue(rows[provider]["registered"])
            self.assertFalse(rows[provider]["adapter_implemented"])
            self.assertEqual(rows[provider]["execution_status"], "unsupported")
        for provider in ("ollama", "lmstudio"):
            self.assertTrue(rows[provider]["registered"])
            self.assertFalse(rows[provider]["adapter_implemented"])
            self.assertEqual(rows[provider]["execution_status"], "local_config_gated")

    def test_get_available_providers_skips_missing_and_placeholders(self) -> None:
        saved = {k: os.environ.pop(k, None) for k in PROVIDER_ENV_KEYS}
        try:
            os.environ["GROQ_API_KEY"] = "groq-registry-test-key"
            os.environ["GEMINI_API_KEY"] = "gemini-registry-test-key"
            os.environ["OPENAI_API_KEY"] = "YOUR_OPENAI_API_KEY_HERE"
            avail = get_available_providers()
            self.assertIn("groq", avail)
            self.assertIn("gemini", avail)
            self.assertNotIn("openai", avail)
            self.assertEqual(providers_capability(), {"providers": avail})
        finally:
            for k, v in saved.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v

    def test_provider_contract_models_are_serializable(self) -> None:
        request = ProviderRequest(prompt="hello", temperature=0.1)
        response = ProviderResponse(provider_name="demo", provider_type=ProviderType.GENERIC.value, content="ok")
        health = ProviderHealth(provider_name="demo", healthy=True, detail="fine")
        self.assertEqual(request.as_dict()["prompt"], "hello")
        self.assertEqual(response.as_dict()["content"], "ok")
        self.assertTrue(health.as_dict()["healthy"])

    def test_describe_provider_diagnostics_marks_attempt_failure(self) -> None:
        saved = {k: os.environ.pop(k, None) for k in PROVIDER_ENV_KEYS}
        try:
            os.environ["OPENAI_API_KEY"] = "openai-provider-test-key"
            rows = describe_provider_diagnostics(
                selected_provider="openai",
                actual_provider="openai",
                attempted_provider="openai",
                failure_class="provider_timeout",
                failure_reason="request timed out",
                include_embedded_local=True,
            )
            openai = next(item for item in rows if item["provider"] == "openai")
            self.assertTrue(openai["configured"])
            self.assertTrue(openai["key_present"])
            self.assertTrue(openai["model_configured"])
            self.assertFalse(openai["adapter_implemented"])
            self.assertFalse(openai["available"])
            self.assertEqual(openai["execution_status"], "unsupported")
            self.assertTrue(openai["selected"])
            self.assertTrue(openai["attempted"])
            self.assertTrue(openai["failed"])
            self.assertEqual(openai["failure_class"], "provider_timeout")
            openrouter = next(item for item in rows if item["provider"] == "openrouter")
            self.assertTrue(openrouter["registered"])
            self.assertFalse(openrouter["adapter_implemented"])
            self.assertEqual(openrouter["execution_status"], "unsupported")
            heuristic = next(item for item in rows if item["provider"] == "local-heuristic")
            self.assertTrue(heuristic["configured"])
            self.assertFalse(heuristic["key_present"])
            self.assertTrue(heuristic["model_configured"])
            self.assertTrue(heuristic["adapter_implemented"])
            self.assertTrue(heuristic["available"])
            self.assertFalse(heuristic["selected"])
            serialized = str(rows).lower()
            self.assertNotIn("openai-provider-test-key", serialized)
            self.assertNotIn("key_prefix", serialized)
            self.assertNotIn("key_length", serialized)
            self.assertNotIn("key_hash", serialized)
        finally:
            for k, v in saved.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v


if __name__ == "__main__":
    unittest.main()
