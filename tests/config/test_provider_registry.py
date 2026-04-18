from __future__ import annotations

import os
import unittest

from config.provider_registry import PROVIDERS, get_available_providers, providers_capability


class ProviderRegistryTest(unittest.TestCase):
    def test_providers_list_is_stable(self) -> None:
        self.assertEqual(
            PROVIDERS,
            ("openai", "anthropic", "groq", "gemini", "deepseek"),
        )

    def test_get_available_providers_skips_missing_and_placeholders(self) -> None:
        keys = (
            "OPENAI_API_KEY",
            "ANTHROPIC_API_KEY",
            "GROQ_API_KEY",
            "GEMINI_API_KEY",
            "DEEPSEEK_API_KEY",
        )
        saved = {k: os.environ.pop(k, None) for k in keys}
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


if __name__ == "__main__":
    unittest.main()
