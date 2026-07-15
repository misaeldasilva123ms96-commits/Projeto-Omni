from __future__ import annotations

import pytest

from brain.env import (
    env_alias_usage_snapshot,
    legacy_env_names,
    read_env,
    read_env_bool,
    read_env_float,
    read_env_int,
    reset_env_alias_usage,
)


def test_canonical_value_wins_over_legacy_alias(monkeypatch: pytest.MonkeyPatch) -> None:
    reset_env_alias_usage()
    monkeypatch.setenv("OMNI_RUNTIME_MODE", "canonical")
    monkeypatch.setenv("OMINI_RUNTIME_MODE", "legacy")

    assert read_env("OMNI_RUNTIME_MODE") == "canonical"
    snapshot = env_alias_usage_snapshot()
    assert snapshot["legacy_reads"] == 0
    assert snapshot["canonical_overrides"] == 1
    assert snapshot["aliases"][0]["canonical"] == "OMNI_RUNTIME_MODE"
    assert snapshot["aliases"][0]["legacy"] == "OMINI_RUNTIME_MODE"


def test_misspelled_legacy_alias_remains_supported(monkeypatch: pytest.MonkeyPatch) -> None:
    reset_env_alias_usage()
    monkeypatch.delenv("OMNI_RUNTIME_MODE", raising=False)
    monkeypatch.setenv("OMINI_RUNTIME_MODE", "legacy-secret-value")

    with pytest.warns(DeprecationWarning, match="use OMNI_RUNTIME_MODE instead"):
        assert read_env("OMNI_RUNTIME_MODE") == "legacy-secret-value"
    snapshot = env_alias_usage_snapshot()
    assert snapshot["legacy_reads"] == 1
    assert snapshot["canonical_overrides"] == 0
    assert "legacy-secret-value" not in str(snapshot)


def test_explicit_unprefixed_alias_remains_supported(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OMNI_BASE_DIR", raising=False)
    monkeypatch.delenv("OMINI_BASE_DIR", raising=False)
    monkeypatch.setenv("BASE_DIR", "legacy-base")

    with pytest.warns(DeprecationWarning, match="use OMNI_BASE_DIR instead"):
        assert read_env("OMNI_BASE_DIR") == "legacy-base"

    assert legacy_env_names("OMNI_BASE_DIR") == ("BASE_DIR", "OMINI_BASE_DIR")


def test_typed_readers_use_canonical_alias_policy(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OMNI_FLAG", "true")
    monkeypatch.setenv("OMNI_COUNT", "7")
    monkeypatch.setenv("OMNI_RATIO", "1.5")

    assert read_env_bool("OMNI_FLAG") is True
    assert read_env_int("OMNI_COUNT") == 7
    assert read_env_float("OMNI_RATIO") == 1.5


def test_canonical_false_overrides_truthy_legacy_alias(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reset_env_alias_usage()
    monkeypatch.setenv("OMNI_PUBLIC_DEMO_MODE", "false")
    monkeypatch.setenv("OMINI_PUBLIC_DEMO_MODE", "true")

    assert read_env_bool("OMNI_PUBLIC_DEMO_MODE") is False
    snapshot = env_alias_usage_snapshot()
    assert snapshot["legacy_reads"] == 0
    assert snapshot["canonical_overrides"] == 1
