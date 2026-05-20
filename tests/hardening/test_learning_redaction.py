"""
Tests for Phase 1E — Learning/Log Redaction.
Run: pytest tests/hardening/test_learning_redaction.py -v
"""
import re
import importlib.util
import sys
import types
import os


def load_sanitize():
    path = os.path.join(
        os.path.dirname(__file__),
        "../../backend/python/brain/runtime/learning/learning_logger.py",
    )
    spec = importlib.util.spec_from_file_location("brain.runtime.learning.learning_logger", path)
    mod = importlib.util.module_from_spec(spec)

    # Register the module itself before exec so relative imports resolve correctly
    sys.modules["brain.runtime.learning.learning_logger"] = mod

    # Stub all relative-import dependencies as proper module objects
    for dep_name, attrs in {
        "brain.runtime.learning.learning_improvement_engine": ["LearningImprovementEngine"],
        "brain.runtime.learning.learning_models": [
            "DecisionEvaluation", "ExecutionOutcome", "LearningRecord",
            "new_controlled_learning_record_id",
        ],
        "brain.runtime.learning.learning_store": ["ControlledLearningStore"],
        "brain.runtime.learning.models": ["utc_now_iso"],
    }.items():
        if dep_name not in sys.modules:
            stub = types.ModuleType(dep_name)
            for attr in attrs:
                setattr(stub, attr, attr)
            sys.modules[dep_name] = stub

    spec.loader.exec_module(mod)
    return mod


mod = load_sanitize()
_patterns = getattr(mod, "_SECRET_PATTERNS", [])


def apply_patterns(text):
    result = text
    for pat, repl in _patterns:
        result = pat.sub(repl, result)
    return result


def test_email_redacted():
    out = apply_patterns("contact user@example.com now")
    assert "user@example.com" not in out, f"Email not redacted: {out}"
    assert "[REDACTED_EMAIL]" in out


def test_sk_proj_key_redacted():
    out = apply_patterns("key=sk-proj-ABCDEFGHIJKLMNOPQRSTU")
    assert "sk-proj-" not in out, f"sk-proj key not redacted: {out}"
    assert "[REDACTED_API_KEY]" in out


def test_sk_key_redacted():
    out = apply_patterns("key=sk-ABCDEFGHIJKLMNOP")
    assert "sk-ABCDEF" not in out, f"sk- key not redacted: {out}"
    assert "[REDACTED_API_KEY]" in out


def test_bearer_token_redacted():
    out = apply_patterns("Authorization: Bearer eyABCDEFGHIJKLMNOP")
    assert "eyABCDEFGHIJKLMNOP" not in out, f"Bearer token not redacted: {out}"


def test_jwt_redacted():
    fake_jwt = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ1c2VyIn0.SflKxwRJSMeKKF2QT4"
    out = apply_patterns(fake_jwt)
    assert "eyJhbGci" not in out, f"JWT not redacted: {out}"
    assert "[REDACTED_JWT]" in out


def test_unix_path_redacted():
    out = apply_patterns("file at /home/user/project/secret.py")
    assert "/home/user" not in out, f"Unix path not redacted: {out}"
    assert "[REDACTED_PATH]" in out


def test_windows_path_redacted():
    out = apply_patterns(r"path: C:\Users\admin\Documents\key.txt")
    assert r"C:\Users\admin" not in out, f"Windows path not redacted: {out}"


def test_cpf_redacted():
    out = apply_patterns("cpf: 123.456.789-09")
    assert "123.456.789-09" not in out, f"CPF not redacted: {out}"
    assert "[REDACTED_CPF]" in out


def test_phone_br_redacted():
    out = apply_patterns("tel: +55 (11) 99999-9999")
    assert "+55 (11) 99999-9999" not in out, f"Phone not redacted: {out}"


def test_password_redacted():
    out = apply_patterns("password=MySuperSecret")
    assert "MySuperSecret" not in out, f"Password not redacted: {out}"
