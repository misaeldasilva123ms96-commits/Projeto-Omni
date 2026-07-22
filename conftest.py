from __future__ import annotations

import ipaddress
import os
import shutil
import socket
import tempfile
import warnings
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
_REMOVED_ENV_KEYS = (
    "GIT_ASKPASS",
    "GIT_SSH_COMMAND",
    "SSH_AUTH_SOCK",
)


def _is_sensitive_environment_key(key: str) -> bool:
    upper = key.upper()
    return upper.startswith(_SENSITIVE_ENV_PREFIXES) or upper.endswith(_SENSITIVE_ENV_SUFFIXES)


def _restore_environment(snapshot: dict[str, tuple[bool, str | None]]) -> None:
    for key, (existed, value) in snapshot.items():
        if existed and value is not None:
            os.environ[key] = value
        else:
            os.environ.pop(key, None)


def pytest_configure(config: pytest.Config) -> None:
    isolation_parent = Path(config.rootpath) / ".tmp" / "pytest-direct"
    isolation_parent.mkdir(parents=True, exist_ok=True)
    root = Path(tempfile.mkdtemp(prefix=f"{os.getpid()}-", dir=isolation_parent))
    if not config.option.basetemp:
        config.option.basetemp = str(root / "pytest")
    isolated_home = root / "home"
    isolated_temp = root / "temp"
    isolated = {
        "OMNI_TEST_MODE": "true",
        "OMNI_BASE_DIR": Path(config.rootpath),
        "OMNI_PYTHON_BASE_DIR": Path(config.rootpath) / "backend" / "python",
        "OMNI_PYTHON_ENTRY": Path(config.rootpath) / "backend" / "python" / "main.py",
        "OMNI_RUNTIME_MODE": "live",
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
        "HOME": isolated_home,
        "USERPROFILE": isolated_home,
        "TMP": isolated_temp,
        "TEMP": isolated_temp,
        "TMPDIR": isolated_temp,
        "XDG_CONFIG_HOME": isolated_home / ".config",
        "XDG_CACHE_HOME": isolated_home / ".cache",
        "XDG_DATA_HOME": isolated_home / ".local" / "share",
        "XDG_STATE_HOME": isolated_home / ".local" / "state",
        "GIT_CONFIG_GLOBAL": "NUL" if os.name == "nt" else "/dev/null",
    }
    file_path_keys = {
        "OMNI_PYTHON_ENTRY",
        "OMNI_MEMORY_JSON_PATH",
        "OMNI_JSONL_MEMORY_PATH",
        "OMNI_SQLITE_MEMORY_PATH",
    }
    removed_keys = {key for key in os.environ if _is_sensitive_environment_key(key)} | set(
        _REMOVED_ENV_KEYS
    )
    affected_keys = set(isolated) | removed_keys
    snapshot = {key: (key in os.environ, os.environ.get(key)) for key in affected_keys}
    config._omni_environment_snapshot = snapshot  # type: ignore[attr-defined]
    config._omni_isolation_root = root  # type: ignore[attr-defined]

    try:
        for key, value in isolated.items():
            if isinstance(value, Path):
                target = value.parent if key in file_path_keys else value
                target.mkdir(parents=True, exist_ok=True)
                os.environ[key] = str(value)
            else:
                os.environ[key] = value
        config._omni_isolated_env = {  # type: ignore[attr-defined]
            key: str(value) for key, value in isolated.items()
        }
        for key in removed_keys:
            os.environ.pop(key, None)
    except BaseException:
        _restore_environment(snapshot)
        shutil.rmtree(root, ignore_errors=True)
        raise


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    root = getattr(session.config, "_omni_isolation_root", None)
    snapshot = getattr(session.config, "_omni_environment_snapshot", {})
    cleanup_error: BaseException | None = None
    try:
        if root is not None:
            shutil.rmtree(root)
    except BaseException as error:
        cleanup_error = error
    finally:
        _restore_environment(snapshot)
        session.config._omni_environment_snapshot = {}  # type: ignore[attr-defined]
    if cleanup_error is not None:
        warnings.warn(
            f"Omni test isolation cleanup failed ({type(cleanup_error).__name__}); "
            "the original pytest exit status is unchanged.",
            RuntimeWarning,
            stacklevel=1,
        )


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
    # This guard applies only to sockets opened in the current pytest process.
    # Child-process egress requires an external container/namespace/firewall boundary.
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
