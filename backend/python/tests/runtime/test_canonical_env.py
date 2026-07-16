from __future__ import annotations

import pytest

from brain.env import read_env, read_env_bool, read_env_float, read_env_int


def test_canonical_value_is_read(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OMNI_RUNTIME_MODE", "canonical")
    assert read_env("OMNI_RUNTIME_MODE") == "canonical"


def test_obsolete_prefix_is_not_read_or_logged(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    obsolete_name = "OMINI_RUNTIME_MODE"
    secret_value = "obsolete-secret-sentinel"
    monkeypatch.delenv("OMNI_RUNTIME_MODE", raising=False)
    monkeypatch.setenv(obsolete_name, secret_value)

    assert read_env("OMNI_RUNTIME_MODE", "default") == "default"
    assert secret_value not in caplog.text


def test_unprefixed_name_is_not_an_omni_configuration_alias(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OMNI_BASE_DIR", raising=False)
    monkeypatch.setenv("BASE_DIR", "obsolete-base")
    assert read_env("OMNI_BASE_DIR", "default-base") == "default-base"


def test_typed_readers_use_canonical_names(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OMNI_FLAG", "true")
    monkeypatch.setenv("OMNI_COUNT", "7")
    monkeypatch.setenv("OMNI_RATIO", "1.5")

    assert read_env_bool("OMNI_FLAG") is True
    assert read_env_int("OMNI_COUNT", 0) == 7
    assert read_env_float("OMNI_RATIO", 0.0) == 1.5
