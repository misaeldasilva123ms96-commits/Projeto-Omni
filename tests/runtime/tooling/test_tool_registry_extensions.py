from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.orchestration.capability_registry import CapabilityRegistry  # noqa: E402
from brain.runtime.tooling.tool_registry_extensions import get_tool_metadata  # noqa: E402


class ToolRegistryExtensionsTest(unittest.TestCase):
    def test_known_tool_metadata_is_exposed(self) -> None:
        metadata = get_tool_metadata("read_file")
        self.assertEqual(metadata.name, "read_file")
        self.assertEqual(metadata.risk_level, "low")
        self.assertTrue(metadata.safe_fallback_available)

    def test_unknown_tool_uses_conservative_defaults(self) -> None:
        metadata = get_tool_metadata("unknown_tool_xyz")
        self.assertEqual(metadata.name, "unknown_tool_xyz")
        self.assertEqual(metadata.risk_level, "medium")
        self.assertTrue(metadata.safe_fallback_available)

    def test_capability_registry_is_enriched_additively(self) -> None:
        registry = CapabilityRegistry()
        capability = registry.get("engineering_tool_execution")
        self.assertIsNotNone(capability)
        self.assertIn("name", capability.metadata)
        self.assertEqual(capability.metadata["name"], "engineering_tool_execution")


if __name__ == "__main__":
    unittest.main()
