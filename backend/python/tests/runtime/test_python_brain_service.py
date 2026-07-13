from __future__ import annotations

from brain.runtime.config import python_service_mode


def test_service_mode_default_is_subprocess(monkeypatch) -> None:
    monkeypatch.delenv("OMINI_PYTHON_MODE", raising=False)
    monkeypatch.delenv("OMNI_PYTHON_MODE", raising=False)
    assert python_service_mode() is False


def test_service_mode_enabled(monkeypatch) -> None:
    monkeypatch.setenv("OMNI_PYTHON_MODE", "service")
    assert python_service_mode() is True


def test_service_mode_disabled_explicit(monkeypatch) -> None:
    monkeypatch.setenv("OMNI_PYTHON_MODE", "subprocess")
    assert python_service_mode() is False


def test_service_mode_case_insensitive(monkeypatch) -> None:
    monkeypatch.setenv("OMNI_PYTHON_MODE", "SERVICE")
    assert python_service_mode() is True


def test_service_mode_legacy_env(monkeypatch) -> None:
    monkeypatch.delenv("OMNI_PYTHON_MODE", raising=False)
    monkeypatch.setenv("OMINI_PYTHON_MODE", "service")
    assert python_service_mode() is True


def test_service_mode_prefers_canonical_env(monkeypatch) -> None:
    monkeypatch.setenv("OMNI_PYTHON_MODE", "service")
    monkeypatch.setenv("OMINI_PYTHON_MODE", "subprocess")
    assert python_service_mode() is True
