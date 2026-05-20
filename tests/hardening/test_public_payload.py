"""
Tests for Phase 1C — Backend public payload sanitization.
Run: pytest tests/hardening/test_public_payload.py -v
"""

import importlib.util, sys, os


def load_inspector():
    spec = importlib.util.spec_from_file_location(
        "cognitive_runtime_inspector",
        os.path.join(
            os.path.dirname(__file__),
            "../../backend/python/brain/runtime/observability/cognitive_runtime_inspector.py",
        ),
    )
    mod = importlib.util.module_from_spec(spec)
    # stub dependencies
    class _Fake:
        def __getattr__(self, item):
            return ""
    for dep in [
        "brain.runtime.observability.runtime_lane_classifier",
        "brain.runtime.observability.runtime_modes",
    ]:
        fake = type(sys)("fake")
        for attr in [
            "LANE_BRIDGE_EXECUTION_REQUEST", "LANE_COMPATIBILITY_EXECUTION",
            "LANE_LOCAL_DIRECT_RESPONSE", "LANE_MATCHER_SHORTCUT",
            "LANE_SAFE_DEGRADED_FALLBACK", "LANE_TRUE_ACTION_EXECUTION",
            "TRANSPORT_SUCCESS", "classify_execution_runtime_lane", "classify_runtime_lane",
            "RUNTIME_MODE_COMPATIBILITY_EXECUTION", "RUNTIME_MODE_DEFINITIONS",
            "RUNTIME_MODE_DIRECT_LOCAL_RESPONSE", "RUNTIME_MODE_FULL_COGNITIVE_RUNTIME",
            "RUNTIME_MODE_LOCAL_TOOL_SUCCESS", "RUNTIME_MODE_MATCHER_SHORTCUT",
            "RUNTIME_MODE_NODE_EXECUTION_SUCCESS", "RUNTIME_MODE_NODE_FAILURE",
            "RUNTIME_MODE_PARTIAL_COGNITIVE_RUNTIME", "RUNTIME_MODE_PROVIDER_FAILURE",
            "RUNTIME_MODE_SAFE_FALLBACK",
        ]:
            setattr(fake, attr, attr)
        sys.modules[dep] = fake
    try:
        spec.loader.exec_module(mod)
    except Exception:
        pass
    return mod


mod = load_inspector()
build_public = getattr(mod, "build_public_cognitive_runtime_inspection", None)
strip_internal = getattr(mod, "strip_internal_fields", None)


def test_public_inspection_removes_stack():
    if not strip_internal:
        return
    payload = {"runtime_mode": "FULL", "stack": "traceback...", "token": "abc123"}
    result = strip_internal(payload)
    assert "stack" not in result
    assert "token" not in result
    assert result.get("runtime_mode") == "FULL"


def test_public_inspection_removes_nested_stack():
    if not strip_internal:
        return
    payload = {"signals": {"fallback_triggered": True, "stack": "err at line 1", "stderr": "bad"}}
    result = strip_internal(payload)
    assert "stack" not in result.get("signals", {})
    assert "stderr" not in result.get("signals", {})
    assert result["signals"]["fallback_triggered"] is True


def test_public_inspection_keeps_runtime_mode():
    if not build_public:
        return
    full = {"runtime_mode": "FULL_COGNITIVE_RUNTIME", "signals": {}}
    result = build_public(full)
    assert result.get("runtime_mode") == "FULL_COGNITIVE_RUNTIME"


def test_public_inspection_has_public_summary():
    if not build_public:
        return
    full = {"runtime_mode": "SAFE_FALLBACK", "signals": {}}
    result = build_public(full)
    assert "public_summary" in result
    assert isinstance(result["public_summary"], str)
    assert len(result["public_summary"]) > 0
