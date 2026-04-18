from __future__ import annotations

import os
import unittest

from config.secrets_manager import (
    SecretError,
    build_controlled_os_environ_base,
    describe_configuration,
    merge_provider_credentials,
    get_secret,
)


class SecretsManagerTest(unittest.TestCase):
    def test_unknown_secret_raises(self) -> None:
        with self.assertRaises(SecretError) as ctx:
            get_secret("not_a_provider")
        self.assertIn("Unknown", str(ctx.exception))

    def test_placeholder_rejected(self) -> None:
        prev = os.environ.get("OPENAI_API_KEY")
        try:
            os.environ["OPENAI_API_KEY"] = "YOUR_OPENAI_API_KEY_HERE"
            with self.assertRaises(SecretError):
                get_secret("openai")
        finally:
            if prev is None:
                os.environ.pop("OPENAI_API_KEY", None)
            else:
                os.environ["OPENAI_API_KEY"] = prev

    def test_merge_skips_missing_openai(self) -> None:
        prev = os.environ.pop("OPENAI_API_KEY", None)
        try:
            env = merge_provider_credentials(build_controlled_os_environ_base())
            self.assertNotIn("OPENAI_API_KEY", env)
        finally:
            if prev is not None:
                os.environ["OPENAI_API_KEY"] = prev

    def test_merge_sets_valid_openai(self) -> None:
        prev = os.environ.pop("OPENAI_API_KEY", None)
        try:
            os.environ["OPENAI_API_KEY"] = "openai-test-placeholder"
            env = merge_provider_credentials(build_controlled_os_environ_base())
            self.assertEqual(env.get("OPENAI_API_KEY"), "openai-test-placeholder")
        finally:
            if prev is None:
                os.environ.pop("OPENAI_API_KEY", None)
            else:
                os.environ["OPENAI_API_KEY"] = prev

    def test_describe_never_contains_values(self) -> None:
        prev = os.environ.get("OPENAI_API_KEY")
        try:
            os.environ["OPENAI_API_KEY"] = "secret-value-never-returned"
            d = describe_configuration()
            self.assertEqual(d.get("openai"), "configured")
            self.assertNotIn("secret-value", str(d))
        finally:
            if prev is None:
                os.environ.pop("OPENAI_API_KEY", None)
            else:
                os.environ["OPENAI_API_KEY"] = prev


if __name__ == "__main__":
    unittest.main()
