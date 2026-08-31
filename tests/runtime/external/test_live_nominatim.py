from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.external.adapters.nominatim import (  # noqa: E402
    GeocodePlaceInput,
    get_geocode_place,
)
from brain.runtime.external.config import nominatim_operational_guard_satisfied  # noqa: E402
from brain.runtime.external.gateway import ExternalAPIGateway  # noqa: E402
from brain.runtime.external.providers import build_external_api_registry  # noqa: E402


@unittest.skipUnless(
    os.getenv("OMNI_EXTERNAL_LIVE_TESTS") == "1"
    and os.getenv("OMNI_EXTERNAL_NOMINATIM_LIVE_TESTS") == "1"
    and nominatim_operational_guard_satisfied(),
    "Nominatim live test requires live opt-in gates and the operational guard",
)
class NominatimLiveSmokeTest(unittest.TestCase):
    def test_one_generic_settlement_query(self) -> None:
        result = get_geocode_place(
            GeocodePlaceInput("Goiânia", "Goiás", "br"),
            gateway=ExternalAPIGateway(registry=build_external_api_registry()),
            global_enabled=True,
            provider_enabled=True,
        )
        self.assertTrue(result.candidates)
        self.assertEqual(result.provider, "Nominatim / OpenStreetMap")


if __name__ == "__main__":
    unittest.main()
