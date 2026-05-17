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
        self.assertTrue(rows["openrouter"]["registered"])
        self.assertTrue(rows["openrouter"]["adapter_implemented"])
        self.assertEqual(rows["openrouter"]["execution_status"], "credential_gated")
        self.assertTrue(rows["openai"]["registered"])
        self.assertTrue(rows["openai"]["adapter_implemented"])
        self.assertEqual(rows["openai"]["execution_status"], "credential_gated")
        self.assertTrue(rows["anthropic"]["registered"])
        self.assertTrue(rows["anthropic"]["adapter_implemented"])
        self.assertEqual(rows["anthropic"]["execution_status"], "credential_gated")
        self.assertTrue(rows["gemini"]["registered"])
        self.assertTrue(rows["gemini"]["adapter_implemented"])
        self.assertEqual(rows["gemini"]["execution_status"], "credential_gated")
        self.assertTrue(rows["deepseek"]["registered"])
        self.assertFalse(rows["deepseek"]["adapter_implemented"])
        self.assertEqual(rows["deepseek"]["execution_status"], "unsupported")
        self.assertTrue(rows["ollama"]["registered"])
        self.assertTrue(rows["ollama"]["adapter_implemented"])
        self.assertEqual(rows["ollama"]["execution_status"], "local_config_gated")
        self.assertTrue(rows["lmstudio"]["registered"])
        self.assertTrue(rows["lmstudio"]["adapter_implemented"])
        self.assertEqual(rows["lmstudio"]["execution_status"], "local_config_gated")

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
            self.assertTrue(openai["adapter_implemented"])
            self.assertTrue(openai["available"])
            self.assertEqual(openai["execution_status"], "active")
            self.assertTrue(openai["selected"])
            self.assertTrue(openai["attempted"])
            self.assertTrue(openai["failed"])
            self.assertEqual(openai["failure_class"], "provider_timeout")
            openrouter = next(item for item in rows if item["provider"] == "openrouter")
            self.assertTrue(openrouter["registered"])
            self.assertFalse(openrouter["configured"])
            self.assertTrue(openrouter["adapter_implemented"])
            self.assertEqual(openrouter["execution_status"], "credential_gated")
            self.assertFalse(openrouter["available"])
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

    def test_openrouter_diagnostics_becomes_available_when_configured(self) -> None:
        saved = {k: os.environ.pop(k, None) for k in PROVIDER_ENV_KEYS}
        try:
            os.environ["OPENROUTER_API_KEY"] = "openrouter-provider-test-key"
            rows = describe_provider_diagnostics(selected_provider="openrouter", include_embedded_local=True)
            openrouter = next(item for item in rows if item["provider"] == "openrouter")
            self.assertTrue(openrouter["registered"])
            self.assertTrue(openrouter["configured"])
            self.assertTrue(openrouter["key_present"])
            self.assertTrue(openrouter["adapter_implemented"])
            self.assertTrue(openrouter["available"])
            self.assertEqual(openrouter["execution_status"], "active")
            self.assertTrue(openrouter["selected"])
            serialized = str(rows).lower()
            self.assertNotIn("openrouter-provider-test-key", serialized)
        finally:
            for k, v in saved.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v

    def test_openai_diagnostics_becomes_available_when_configured(self) -> None:
        saved = {k: os.environ.pop(k, None) for k in PROVIDER_ENV_KEYS}
        try:
            os.environ["OPENAI_API_KEY"] = "openai-provider-test-key"
            rows = describe_provider_diagnostics(selected_provider="openai", include_embedded_local=True)
            openai = next(item for item in rows if item["provider"] == "openai")
            self.assertTrue(openai["registered"])
            self.assertTrue(openai["configured"])
            self.assertTrue(openai["key_present"])
            self.assertTrue(openai["adapter_implemented"])
            self.assertTrue(openai["available"])
            self.assertEqual(openai["execution_status"], "active")
            self.assertTrue(openai["selected"])
            serialized = str(rows).lower()
            self.assertNotIn("openai-provider-test-key", serialized)
        finally:
            for k, v in saved.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v

    def test_anthropic_diagnostics_becomes_available_when_configured(self) -> None:
        saved = {k: os.environ.pop(k, None) for k in PROVIDER_ENV_KEYS}
        try:
            os.environ["ANTHROPIC_API_KEY"] = "anthropic-provider-test-key"
            rows = describe_provider_diagnostics(selected_provider="anthropic", include_embedded_local=True)
            anthropic = next(item for item in rows if item["provider"] == "anthropic")
            self.assertTrue(anthropic["registered"])
            self.assertTrue(anthropic["configured"])
            self.assertTrue(anthropic["key_present"])
            self.assertTrue(anthropic["adapter_implemented"])
            self.assertTrue(anthropic["available"])
            self.assertEqual(anthropic["execution_status"], "active")
            self.assertTrue(anthropic["selected"])
            serialized = str(rows).lower()
            self.assertNotIn("anthropic-provider-test-key", serialized)
        finally:
            for k, v in saved.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v

    def test_gemini_diagnostics_becomes_available_when_configured(self) -> None:
        saved = {k: os.environ.pop(k, None) for k in PROVIDER_ENV_KEYS}
        try:
            os.environ["GEMINI_API_KEY"] = "gemini-provider-test-key"
            rows = describe_provider_diagnostics(selected_provider="gemini", include_embedded_local=True)
            gemini = next(item for item in rows if item["provider"] == "gemini")
            self.assertTrue(gemini["registered"])
            self.assertTrue(gemini["configured"])
            self.assertTrue(gemini["key_present"])
            self.assertTrue(gemini["adapter_implemented"])
            self.assertTrue(gemini["available"])
            self.assertEqual(gemini["execution_status"], "active")
            self.assertTrue(gemini["selected"])
            serialized = str(rows).lower()
            self.assertNotIn("gemini-provider-test-key", serialized)
        finally:
            for k, v in saved.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v

    def test_local_provider_diagnostics_become_available_when_url_configured(self) -> None:
        saved = {k: os.environ.pop(k, None) for k in PROVIDER_ENV_KEYS}
        try:
            os.environ["OLLAMA_URL"] = "http://127.0.0.1:11434"
            os.environ["LMSTUDIO_URL"] = "http://127.0.0.1:1234"
            rows = describe_provider_diagnostics(selected_provider="ollama", include_embedded_local=True)
            ollama = next(item for item in rows if item["provider"] == "ollama")
            self.assertTrue(ollama["registered"])
            self.assertTrue(ollama["configured"])
            self.assertFalse(ollama["key_present"])
            self.assertTrue(ollama["adapter_implemented"])
            self.assertTrue(ollama["available"])
            self.assertEqual(ollama["execution_status"], "active")
            self.assertTrue(ollama["selected"])
            lmstudio = next(item for item in rows if item["provider"] == "lmstudio")
            self.assertTrue(lmstudio["registered"])
            self.assertTrue(lmstudio["configured"])
            self.assertFalse(lmstudio["key_present"])
            self.assertTrue(lmstudio["adapter_implemented"])
            self.assertTrue(lmstudio["available"])
            self.assertEqual(lmstudio["execution_status"], "active")
            serialized = str(rows).lower()
            self.assertNotIn("127.0.0.1", serialized)
        finally:
            for k, v in saved.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v


if __name__ == "__main__":
    unittest.main()
