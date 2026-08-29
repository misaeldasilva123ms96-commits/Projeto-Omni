from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.external.discovery import (  # noqa: E402
    DiscoveryClient,
    build_discovery_source_registry,
)
from brain.runtime.external.gateway import ExternalAPIGateway  # noqa: E402
from brain.runtime.external.schema_intake import SchemaIntakeClient  # noqa: E402

LIVE_GATES = (
    "OMNI_EXTERNAL_LIVE_TESTS",
    "OMNI_EXTERNAL_DISCOVERY_LIVE_TESTS",
    "OMNI_EXTERNAL_APIS_GURU_DISCOVERY_LIVE_TESTS",
    "OMNI_EXTERNAL_SCHEMA_INTAKE_LIVE_TESTS",
    "OMNI_EXTERNAL_APIS_GURU_SCHEMA_INTAKE_LIVE_TESTS",
)


@pytest.mark.skipif(
    not all(os.environ.get(name) == "1" for name in LIVE_GATES),
    reason="APIs.guru schema intake live smoke is explicit opt-in",
)
def test_live_apis_guru_catalog_and_one_exact_schema_intake() -> None:
    gates = {
        "OMNI_EXTERNAL_API_ENABLED": "1",
        "OMNI_EXTERNAL_DISCOVERY_ENABLED": "1",
        "OMNI_EXTERNAL_APIS_GURU_DISCOVERY_ENABLED": "1",
        "OMNI_EXTERNAL_SCHEMA_INTAKE_ENABLED": "1",
        "OMNI_EXTERNAL_APIS_GURU_SCHEMA_INTAKE_ENABLED": "1",
    }
    with patch.dict(os.environ, gates):
        candidates = DiscoveryClient(
            ExternalAPIGateway(registry=build_discovery_source_registry())
        ).load("apis-guru")
        selected = next(
            item
            for item in candidates
            if item.source_record_id == "swagger.io:generator" and item.schema_available
        )
        proposal = SchemaIntakeClient().intake(selected)
    assert proposal.detected_openapi_version.startswith(("2.0", "3."))
    assert proposal.operation_count >= 0
    assert len(proposal.canonical_schema_sha256) == 64
    assert proposal.execution_authorized is False
    assert proposal.registration_authorized is False
