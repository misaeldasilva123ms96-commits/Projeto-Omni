from __future__ import annotations

import os
import unittest

from config.secrets_manager import apply_runtime_provider_secrets, describe_configuration_safe, get_secret


class SecretsManagerTest(unittest.TestCase):
    def test_unknown_provider(self) -> None:
        r = get_secret("not_a_provider")
        self.assertFalse(r.present)
        self.assertEqual(r.error, "unknown_logical_provider")

    def test_apply_normalizes_supabase_and_openai(self) -> None:
        prev = {k: os.environ.pop(k, None) for k in ("OPENAI_API_KEY", "SUPABASE_URL", "SUPABASE_ANON_KEY", "VITE_SUPABASE_URL", "VITE_SUPABASE_ANON_KEY")}
        try:
            os.environ["VITE_SUPABASE_URL"] = "https://example.supabase.co"
            os.environ["VITE_SUPABASE_ANON_KEY"] = "anon-test"
            os.environ["OPENAI_API_KEY"] = "openai-test-placeholder"
            base = {"PATH": os.environ.get("PATH", "")}
            merged = apply_runtime_provider_secrets(base)
            self.assertEqual(merged["SUPABASE_URL"], "https://example.supabase.co")
            self.assertEqual(merged["SUPABASE_ANON_KEY"], "anon-test")
            self.assertEqual(merged["OPENAI_API_KEY"], "openai-test-placeholder")
        finally:
            for k, v in prev.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v

    def test_describe_safe_has_no_values(self) -> None:
        d = describe_configuration_safe()
        self.assertIn("providers", d)
        for _k, v in d["providers"].items():
            self.assertIsInstance(v, bool)


if __name__ == "__main__":
    unittest.main()
