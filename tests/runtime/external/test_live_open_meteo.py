from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.external.adapters.open_meteo import (  # noqa: E402
    WeatherForecastInput,
    get_weather_forecast,
)
from brain.runtime.external.gateway import ExternalAPIGateway  # noqa: E402
from brain.runtime.external.providers import build_external_api_registry  # noqa: E402


@unittest.skipUnless(os.getenv("OMNI_EXTERNAL_LIVE_TESTS") == "1", "external live tests are opt-in")
class OpenMeteoLiveSmokeTest(unittest.TestCase):
    def test_public_generic_coordinates(self) -> None:
        result = get_weather_forecast(
            WeatherForecastInput(latitude=-23.55, longitude=-46.63, forecast_days=1),
            gateway=ExternalAPIGateway(registry=build_external_api_registry()),
            global_enabled=True,
            provider_enabled=True,
        )
        self.assertEqual(result.provider, "Open-Meteo")
        self.assertTrue(result.current)


if __name__ == "__main__":
    unittest.main()
