from __future__ import annotations

import os

from brain.runtime.config import python_service_mode


def test_service_mode_default_is_subprocess() -> None:
    os.environ.pop("OMINI_PYTHON_MODE", None)
    os.environ.pop("OMNI_PYTHON_MODE", None)
    assert python_service_mode() is False


def test_service_mode_enabled() -> None:
    os.environ["OMINI_PYTHON_MODE"] = "service"
    assert python_service_mode() is True


def test_service_mode_disabled_explicit() -> None:
    os.environ["OMINI_PYTHON_MODE"] = "subprocess"
    assert python_service_mode() is False


def test_service_mode_case_insensitive() -> None:
    os.environ["OMINI_PYTHON_MODE"] = "SERVICE"
    assert python_service_mode() is True


def test_service_mode_legacy_env() -> None:
    os.environ.pop("OMINI_PYTHON_MODE", None)
    os.environ["OMNI_PYTHON_MODE"] = "service"
    assert python_service_mode() is True
