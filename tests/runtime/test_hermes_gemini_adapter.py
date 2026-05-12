from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND_PYTHON = ROOT / "backend" / "python"
sys.path.insert(0, str(BACKEND_PYTHON))

from brain.runtime.hermes_gemini_adapter import analyze_with_hermes_gemini
from brain.runtime.hermes_gemini_adapter import extract_json_object


def test_extract_json_object_from_fenced_markdown():
    raw = """```json
{
  "role": "hermes_brain_preview",
  "decision": "analyze_only",
  "summary": "ok",
  "recommended_next_steps": ["step"],
  "risks": ["risk"],
  "should_omni_execute": false
}
```"""

    parsed = extract_json_object(raw)

    assert parsed is not None
    assert parsed["role"] == "hermes_brain_preview"
    assert parsed["decision"] == "analyze_only"
    assert parsed["should_omni_execute"] is False


def test_extract_json_object_from_surrounding_text():
    raw = 'Before {"role":"hermes_brain_preview","should_omni_execute":false} after'

    parsed = extract_json_object(raw)

    assert parsed is not None
    assert parsed["role"] == "hermes_brain_preview"


def test_extract_json_object_rejects_invalid_output():
    assert extract_json_object("not json") is None


def test_adapter_disabled_by_default(monkeypatch):
    monkeypatch.delenv("OMNI_HERMES_GEMINI_ENABLED", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    result = analyze_with_hermes_gemini("test")

    assert result["enabled"] is False
    assert result["attempted"] is False
    assert result["succeeded"] is False
    assert result["error_public_code"] == "HERMES_DISABLED"


def test_adapter_enabled_without_key_is_public_safe(monkeypatch):
    monkeypatch.setenv("OMNI_HERMES_GEMINI_ENABLED", "true")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    result = analyze_with_hermes_gemini("test")

    assert result["enabled"] is True
    assert result["attempted"] is False
    assert result["succeeded"] is False
    assert result["error_public_code"] == "HERMES_MISSING_API_KEY"
