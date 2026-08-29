from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.external.adapters.urlhaus import (  # noqa: E402
    URLReputationInput,
    check_url_reputation,
)
from brain.runtime.external.gateway import ExternalAPIGateway  # noqa: E402
from brain.runtime.external.providers import build_external_api_registry  # noqa: E402


@pytest.mark.skipif(
    not (
        os.environ.get("OMNI_EXTERNAL_LIVE_TESTS") == "1"
        and os.environ.get("OMNI_EXTERNAL_URLHAUS_LIVE_TESTS") == "1"
        and os.environ.get("OMNI_EXTERNAL_URLHAUS_AUTH_KEY", "").strip()
    ),
    reason="URLhaus live smoke is explicit opt-in and requires a server credential",
)
def test_live_urlhaus_single_reserved_indicator_lookup():
    result = check_url_reputation(
        URLReputationInput("https://example.com/"),
        gateway=ExternalAPIGateway(registry=build_external_api_registry()),
        global_enabled=True,
        provider_enabled=True,
    )
    assert result.status in {"listed", "not_listed"}
