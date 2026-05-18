from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.providers.models import ProviderHealth, ProviderRequest, ProviderResponse, ProviderType
from config.provider_registry import (
    DEFAULT_FALLBACK_CHAIN,
    PROVIDERS,
    describe_provider_diagnostics,
    describe_provider_diagnostics_snapshot,
    get_available_providers,
    provider_metadata,
    providers_capability,
)


PROVIDER_ENV_KEYS = (
    "OPENAI_API_KEY",
    "OPENAI_MODEL",
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_MODEL",
    "GROQ_API_KEY",
    "GROQ_MODEL",
    "GEMINI_API_KEY",
    "GEMINI_MODEL",
    "DEEPSEEK_API_KEY",
    "DEEPSEEK_MODEL",
    "OPENROUTER_API_KEY",
    "OPENROUTER_MODEL",
    "OLLAMA_URL",
    "OLLAMA_MODEL",
    "OLLAMA_API_KEY",
    "LMSTUDIO_URL",
    "LMSTUDIO_MODEL",
    "LMSTUDIO_API_KEY",
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
        self.assertEqual(rows["groq"]["key_env"], "GROQ_API_KEY")
        self.assertEqual(rows["groq"]["model_env"], "GROQ_MODEL")
        self.assertTrue(rows["openrouter"]["registered"])
        self.assertTrue(rows["openrouter"]["adapter_implemented"])
        self.assertEqual(rows["openrouter"]["execution_status"], "credential_gated")
        self.assertEqual(rows["openrouter"]["key_env"], "OPENROUTER_API_KEY")
        self.assertEqual(rows["openrouter"]["model_env"], "OPENROUTER_MODEL")
        self.assertTrue(rows["openai"]["registered"])
        self.assertTrue(rows["openai"]["adapter_implemented"])
        self.assertEqual(rows["openai"]["execution_status"], "credential_gated")
        self.assertEqual(rows["openai"]["key_env"], "OPENAI_API_KEY")
        self.assertEqual(rows["openai"]["model_env"], "OPENAI_MODEL")
        self.assertTrue(rows["anthropic"]["registered"])
        self.assertTrue(rows["anthropic"]["adapter_implemented"])
        self.assertEqual(rows["anthropic"]["execution_status"], "credential_gated")
        self.assertEqual(rows["anthropic"]["key_env"], "ANTHROPIC_API_KEY")
        self.assertEqual(rows["anthropic"]["model_env"], "ANTHROPIC_MODEL")
        self.assertTrue(rows["gemini"]["registered"])
        self.assertTrue(rows["gemini"]["adapter_implemented"])
        self.assertEqual(rows["gemini"]["execution_status"], "credential_gated")
        self.assertEqual(rows["gemini"]["key_env"], "GEMINI_API_KEY")
        self.assertEqual(rows["gemini"]["model_env"], "GEMINI_MODEL")
        self.assertTrue(rows["deepseek"]["registered"])
        self.assertFalse(rows["deepseek"]["adapter_implemented"])
        self.assertEqual(rows["deepseek"]["execution_status"], "unsupported")
        self.assertEqual(rows["deepseek"]["key_env"], "DEEPSEEK_API_KEY")
        self.assertEqual(rows["deepseek"]["model_env"], "DEEPSEEK_MODEL")
        self.assertTrue(rows["ollama"]["registered"])
        self.assertTrue(rows["ollama"]["adapter_implemented"])
        self.assertEqual(rows["ollama"]["execution_status"], "local_config_gated")
        self.assertEqual(rows["ollama"]["url_env"], "OLLAMA_URL")
        self.assertEqual(rows["ollama"]["model_env"], "OLLAMA_MODEL")
        self.assertEqual(rows["ollama"]["optional_key_env"], "OLLAMA_API_KEY")
        self.assertTrue(rows["lmstudio"]["registered"])
        self.assertTrue(rows["lmstudio"]["adapter_implemented"])
        self.assertEqual(rows["lmstudio"]["execution_status"], "local_config_gated")
        self.assertEqual(rows["lmstudio"]["url_env"], "LMSTUDIO_URL")
        self.assertEqual(rows["lmstudio"]["model_env"], "LMSTUDIO_MODEL")
        self.assertEqual(rows["lmstudio"]["optional_key_env"], "LMSTUDIO_API_KEY")

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
            self.assertEqual(openrouter["key_env"], "OPENROUTER_API_KEY")
            self.assertEqual(openrouter["model_env"], "OPENROUTER_MODEL")
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

    def test_provider_diagnostics_snapshot_is_complete_and_public_safe(self) -> None:
        saved = {k: os.environ.pop(k, None) for k in PROVIDER_ENV_KEYS}
        try:
            os.environ["GROQ_API_KEY"] = "groq-provider-test-key"
            os.environ["GROQ_MODEL"] = "groq-model-secret-shape"
            os.environ["OLLAMA_URL"] = "http://127.0.0.1:11434"
            os.environ["OLLAMA_MODEL"] = "ollama-model-secret-shape"
            os.environ["OLLAMA_API_KEY"] = "ollama-provider-test-key"

            snapshot = describe_provider_diagnostics_snapshot(
                selected_provider="groq",
                actual_provider="groq",
                attempted_provider="groq",
                fallback_triggered=False,
                fallback_reason="",
            )

            self.assertEqual(snapshot["fallback_chain"], list(DEFAULT_FALLBACK_CHAIN))
            self.assertEqual(snapshot["active_provider"], "groq")
            self.assertFalse(snapshot["fallback_triggered"])
            self.assertIsNone(snapshot["fallback_reason"])
            rows = {row["id"]: row for row in snapshot["providers"]}
            self.assertEqual(set(rows), set(PROVIDERS))
            for provider in PROVIDERS:
                row = rows[provider]
                self.assertIn("registered", row)
                self.assertIn("configured", row)
                self.assertIn("adapter_implemented", row)
                self.assertIn("executable", row)
                self.assertIn("execution_status", row)
            self.assertTrue(rows["groq"]["configured"])
            self.assertTrue(rows["groq"]["executable"])
            self.assertEqual(rows["groq"]["key_env"], "GROQ_API_KEY")
            self.assertEqual(rows["groq"]["model_env"], "GROQ_MODEL")
            self.assertTrue(rows["ollama"]["configured"])
            self.assertTrue(rows["ollama"]["executable"])
            self.assertEqual(rows["ollama"]["url_env"], "OLLAMA_URL")
            self.assertEqual(rows["ollama"]["optional_key_env"], "OLLAMA_API_KEY")
            self.assertFalse(rows["deepseek"]["adapter_implemented"])
            self.assertFalse(rows["deepseek"]["executable"])
            self.assertEqual(rows["deepseek"]["execution_status"], "unsupported")
            serialized = str(snapshot).lower()
            self.assertNotIn("groq-provider-test-key", serialized)
            self.assertNotIn("groq-model-secret-shape", serialized)
            self.assertNotIn("127.0.0.1", serialized)
            self.assertNotIn("ollama-model-secret-shape", serialized)
            self.assertNotIn("ollama-provider-test-key", serialized)
        finally:
            for k, v in saved.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v

    def test_provider_diagnostics_snapshot_redacts_env_values_for_all_providers(self) -> None:
        saved = {k: os.environ.pop(k, None) for k in PROVIDER_ENV_KEYS}
        fake_env = {
            "GROQ_API_KEY": "matrix-groq-key-sentinel",
            "GROQ_MODEL": "matrix-groq-model-sentinel",
            "OPENROUTER_API_KEY": "matrix-openrouter-key-sentinel",
            "OPENROUTER_MODEL": "matrix-openrouter-model-sentinel",
            "OPENAI_API_KEY": "matrix-openai-key-sentinel",
            "OPENAI_MODEL": "matrix-openai-model-sentinel",
            "ANTHROPIC_API_KEY": "matrix-anthropic-key-sentinel",
            "ANTHROPIC_MODEL": "matrix-anthropic-model-sentinel",
            "GEMINI_API_KEY": "matrix-gemini-key-sentinel",
            "GEMINI_MODEL": "matrix-gemini-model-sentinel",
            "DEEPSEEK_API_KEY": "matrix-deepseek-key-sentinel",
            "DEEPSEEK_MODEL": "matrix-deepseek-model-sentinel",
            "OLLAMA_URL": "http://matrix-ollama.local.invalid",
            "OLLAMA_MODEL": "matrix-ollama-model-sentinel",
            "OLLAMA_API_KEY": "matrix-ollama-key-sentinel",
            "LMSTUDIO_URL": "http://matrix-lmstudio.local.invalid",
            "LMSTUDIO_MODEL": "matrix-lmstudio-model-sentinel",
            "LMSTUDIO_API_KEY": "matrix-lmstudio-key-sentinel",
        }
        try:
            os.environ.update(fake_env)
            snapshot = describe_provider_diagnostics_snapshot(
                selected_provider="gemini",
                actual_provider="gemini",
                attempted_provider="gemini",
                fallback_triggered=False,
                fallback_reason=None,
            )

            serialized = json.dumps(snapshot, sort_keys=True)
            rows = {row["id"]: row for row in snapshot["providers"]}
            self.assertEqual(set(rows), set(PROVIDERS))
            self.assertEqual(snapshot["fallback_chain"], list(DEFAULT_FALLBACK_CHAIN))
            for provider in PROVIDERS:
                row = rows[provider]
                self.assertIn("registered", row)
                self.assertIn("configured", row)
                self.assertIn("adapter_implemented", row)
                self.assertIn("executable", row)
                self.assertIn("execution_status", row)
            self.assertFalse(rows["deepseek"]["adapter_implemented"])
            self.assertFalse(rows["deepseek"]["executable"])
            self.assertEqual(rows["deepseek"]["execution_status"], "unsupported")
            self.assertEqual(rows["groq"]["key_env"], "GROQ_API_KEY")
            self.assertEqual(rows["openrouter"]["key_env"], "OPENROUTER_API_KEY")
            self.assertEqual(rows["openai"]["key_env"], "OPENAI_API_KEY")
            self.assertEqual(rows["anthropic"]["key_env"], "ANTHROPIC_API_KEY")
            self.assertEqual(rows["gemini"]["key_env"], "GEMINI_API_KEY")
            self.assertEqual(rows["ollama"]["url_env"], "OLLAMA_URL")
            self.assertEqual(rows["ollama"]["optional_key_env"], "OLLAMA_API_KEY")
            self.assertEqual(rows["lmstudio"]["url_env"], "LMSTUDIO_URL")
            self.assertEqual(rows["lmstudio"]["optional_key_env"], "LMSTUDIO_API_KEY")
            for value in fake_env.values():
                self.assertNotIn(value, serialized)
            self.assertNotIn("matrix-ollama.local.invalid", serialized)
            self.assertNotIn("matrix-lmstudio.local.invalid", serialized)
            self.assertNotIn("Authorization", serialized)
            self.assertNotIn("x-api-key", serialized)
            self.assertNotIn("raw request", serialized)
            self.assertNotIn("raw response", serialized)
            self.assertNotIn("stack trace", serialized)
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
            os.environ["OLLAMA_API_KEY"] = "ollama-provider-test-key"
            os.environ["LMSTUDIO_API_KEY"] = "lmstudio-provider-test-key"
            rows = describe_provider_diagnostics(selected_provider="ollama", include_embedded_local=True)
            ollama = next(item for item in rows if item["provider"] == "ollama")
            self.assertTrue(ollama["registered"])
            self.assertTrue(ollama["configured"])
            self.assertFalse(ollama["key_present"])
            self.assertTrue(ollama["adapter_implemented"])
            self.assertTrue(ollama["available"])
            self.assertEqual(ollama["execution_status"], "active")
            self.assertEqual(ollama["url_env"], "OLLAMA_URL")
            self.assertEqual(ollama["model_env"], "OLLAMA_MODEL")
            self.assertEqual(ollama["optional_key_env"], "OLLAMA_API_KEY")
            self.assertTrue(ollama["selected"])
            lmstudio = next(item for item in rows if item["provider"] == "lmstudio")
            self.assertTrue(lmstudio["registered"])
            self.assertTrue(lmstudio["configured"])
            self.assertFalse(lmstudio["key_present"])
            self.assertTrue(lmstudio["adapter_implemented"])
            self.assertTrue(lmstudio["available"])
            self.assertEqual(lmstudio["execution_status"], "active")
            self.assertEqual(lmstudio["url_env"], "LMSTUDIO_URL")
            self.assertEqual(lmstudio["model_env"], "LMSTUDIO_MODEL")
            self.assertEqual(lmstudio["optional_key_env"], "LMSTUDIO_API_KEY")
            serialized = str(rows).lower()
            self.assertNotIn("127.0.0.1", serialized)
            self.assertNotIn("ollama-provider-test-key", serialized)
            self.assertNotIn("lmstudio-provider-test-key", serialized)
        finally:
            for k, v in saved.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v


if __name__ == "__main__":
    unittest.main()
