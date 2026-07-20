from __future__ import annotations

import ipaddress
import os
import shutil
import socket
from pathlib import Path

import pytest

_SENSITIVE_ENV_SUFFIXES = (
    "_API_KEY",
    "_TOKEN",
    "_SECRET",
    "_PASSWORD",
    "_CREDENTIAL",
    "_CREDENTIALS",
)
_SENSITIVE_ENV_PREFIXES = (
    "OPENAI_",
    "ANTHROPIC_",
    "DEEPSEEK_",
    "GEMINI_",
    "GROQ_",
    "MISTRAL_",
    "SUPABASE_",
    "AZURE_",
    "AWS_",
    "GITHUB_",
)


def pytest_configure(config: pytest.Config) -> None:
    root = Path(config.rootpath) / ".tmp" / "pytest-direct" / str(os.getpid())
    root.mkdir(parents=True, exist_ok=True)
    if not config.option.basetemp:
        config.option.basetemp = str(root / "pytest")
    isolated = {
        "OMNI_TEST_MODE": "true",
        "OMNI_MEMORY_ROOT": root / "memory",
        "OMNI_MEMORY_DIR": root / "memory",
        "OMNI_MEMORY_JSON_PATH": root / "memory" / "memory.json",
        "OMNI_JSONL_MEMORY_PATH": root / "memory" / "audit.jsonl",
        "OMNI_SQLITE_MEMORY_PATH": root / "memory" / "memory.sqlite",
        "OMNI_ENABLE_SQLITE_MEMORY": "false",
        "OMNI_CACHE_ROOT": root / "cache",
        "OMNI_ARTIFACT_ROOT": root / "artifacts",
        "OMNI_LOG_ROOT": root / "logs",
        "OMNI_DATABASE_ROOT": root / "databases",
        "OMNI_CREDENTIAL_ROOT": root / "credentials",
        "OMNI_PROVIDER_STATE_ROOT": root / "providers",
        "OMNI_RUNTIME_SESSION_ROOT": root / "sessions",
        "OMNI_UPLOAD_ROOT": root / "uploads",
        "OMNI_WORKSPACE_ROOT": Path(config.rootpath),
    }
    for key, value in isolated.items():
        if isinstance(value, Path):
            value.mkdir(parents=True, exist_ok=True)
            os.environ[key] = str(value)
        else:
            os.environ[key] = value
    config._omni_isolated_env = {  # type: ignore[attr-defined]
        key: str(value) for key, value in isolated.items()
    }
    config._omni_isolation_root = root  # type: ignore[attr-defined]

    for key in tuple(os.environ):
        upper = key.upper()
        if upper.startswith(_SENSITIVE_ENV_PREFIXES) or upper.endswith(_SENSITIVE_ENV_SUFFIXES):
            os.environ.pop(key, None)


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    root = getattr(session.config, "_omni_isolation_root", None)
    if root is not None:
        shutil.rmtree(root, ignore_errors=True)


def _is_loopback_host(host: object) -> bool:
    text = str(host).strip("[]").lower()
    if text == "localhost":
        return True
    try:
        return ipaddress.ip_address(text).is_loopback
    except ValueError:
        return False


@pytest.fixture(autouse=True)
def _enforce_test_isolation(
    monkeypatch: pytest.MonkeyPatch,
    pytestconfig: pytest.Config,
):
    isolated = getattr(pytestconfig, "_omni_isolated_env", {})
    for key, value in isolated.items():
        monkeypatch.setenv(key, value)

    original_connect = socket.socket.connect
    original_connect_ex = socket.socket.connect_ex

    def guarded_connect(sock: socket.socket, address):
        host = address[0] if isinstance(address, tuple) and address else address
        if not _is_loopback_host(host):
            raise OSError("External network access is disabled in Omni tests.")
        return original_connect(sock, address)

    def guarded_connect_ex(sock: socket.socket, address):
        host = address[0] if isinstance(address, tuple) and address else address
        if not _is_loopback_host(host):
            return 13
        return original_connect_ex(sock, address)

    monkeypatch.setattr(socket.socket, "connect", guarded_connect)
    monkeypatch.setattr(socket.socket, "connect_ex", guarded_connect_ex)
