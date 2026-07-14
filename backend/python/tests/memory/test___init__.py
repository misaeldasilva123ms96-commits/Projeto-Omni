from __future__ import annotations

import brain.memory


class TestModule:
    def test_import(self):
        assert brain.memory.__doc__ is not None
        assert "memory" in brain.memory.__doc__.lower()
