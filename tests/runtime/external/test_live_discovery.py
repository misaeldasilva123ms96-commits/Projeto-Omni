from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.external.discovery import (  # noqa: E402
    DiscoveryClient,
    build_discovery_source_registry,
)
from brain.runtime.external.gateway import ExternalAPIGateway  # noqa: E402


def enabled(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


@unittest.skipUnless(
    enabled("OMNI_EXTERNAL_LIVE_TESTS")
    and enabled("OMNI_EXTERNAL_DISCOVERY_LIVE_TESTS")
    and enabled("OMNI_EXTERNAL_APIS_GURU_DISCOVERY_LIVE_TESTS"),
    "APIs.guru discovery live smoke is opt-in",
)
class APIsGuruLiveTest(unittest.TestCase):
    def test_single_catalog_request(self) -> None:
        client = DiscoveryClient(ExternalAPIGateway(registry=build_discovery_source_registry()))
        gates = {
            "OMNI_EXTERNAL_API_ENABLED": "1",
            "OMNI_EXTERNAL_DISCOVERY_ENABLED": "1",
            "OMNI_EXTERNAL_APIS_GURU_DISCOVERY_ENABLED": "1",
        }
        with patch.dict(os.environ, gates):
            self.assertGreater(len(client.load("apis-guru")), 0)


@unittest.skipUnless(
    enabled("OMNI_EXTERNAL_LIVE_TESTS")
    and enabled("OMNI_EXTERNAL_DISCOVERY_LIVE_TESTS")
    and enabled("OMNI_EXTERNAL_PUBLIC_APIS_DISCOVERY_LIVE_TESTS"),
    "public-apis discovery live smoke is opt-in",
)
class PublicAPIsLiveTest(unittest.TestCase):
    def test_single_catalog_request(self) -> None:
        client = DiscoveryClient(ExternalAPIGateway(registry=build_discovery_source_registry()))
        gates = {
            "OMNI_EXTERNAL_API_ENABLED": "1",
            "OMNI_EXTERNAL_DISCOVERY_ENABLED": "1",
            "OMNI_EXTERNAL_PUBLIC_APIS_DISCOVERY_ENABLED": "1",
        }
        with patch.dict(os.environ, gates):
            self.assertGreater(len(client.load("public-apis")), 0)


if __name__ == "__main__":
    unittest.main()
