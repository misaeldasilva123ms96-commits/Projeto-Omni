from __future__ import annotations

import os
import socket
import subprocess
import sys
import tempfile
from types import SimpleNamespace
from pathlib import Path

import pytest
import conftest as omni_conftest

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _hook_config() -> SimpleNamespace:
    return SimpleNamespace(
        rootpath=PROJECT_ROOT,
        option=SimpleNamespace(basetemp=None),
    )


def _finish_hook(config: SimpleNamespace, exitstatus: int = 0) -> None:
    omni_conftest.pytest_sessionfinish(
        SimpleNamespace(config=config),
        exitstatus,
    )


@pytest.mark.parametrize(
    "root_name",
    [
        "OMNI_MEMORY_ROOT",
        "OMNI_MEMORY_DIR",
        "OMNI_CACHE_ROOT",
    ],
)
def test_state_writes_remain_inside_isolated_root(root_name) -> None:
    root = Path(os.environ[root_name]).resolve()
    marker = root / "nested" / "isolation-marker.txt"
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text("isolated", encoding="utf-8")

    assert marker.resolve().is_relative_to(root)
    assert root != Path.home().resolve()


@pytest.mark.parametrize(
    "root_name",
    [
        "OMNI_ARTIFACT_ROOT",
        "OMNI_LOG_ROOT",
        "OMNI_DATABASE_ROOT",
        "OMNI_CREDENTIAL_ROOT",
        "OMNI_PROVIDER_STATE_ROOT",
        "OMNI_RUNTIME_SESSION_ROOT",
        "OMNI_UPLOAD_ROOT",
    ],
)
def test_test_storage_roots_are_explicit_and_not_user_home(root_name) -> None:
    root = Path(os.environ[root_name]).resolve()

    assert root.exists()
    assert root != Path.home().resolve()
    assert root != Path(root.anchor)


@pytest.mark.parametrize("host", ["example.com", "8.8.8.8"])
def test_external_network_is_denied_by_default(host) -> None:
    connection = socket.socket()
    try:
        with pytest.raises(OSError, match="External network access is disabled"):
            connection.connect((host, 443))
    finally:
        connection.close()


@pytest.mark.parametrize(
    "name",
    [
        "SUPABASE_URL",
        "SUPABASE_SERVICE_ROLE_KEY",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
    ],
)
def test_real_provider_configuration_is_not_consumed(name) -> None:
    assert name not in os.environ


def test_global_git_configuration_is_not_loaded_from_developer_home() -> None:
    configured = os.environ.get("GIT_CONFIG_GLOBAL")
    if configured is None:
        pytest.skip("Canonical runner supplies the isolated Git contract.")

    assert configured in {"NUL", "/dev/null"}


def test_test_mode_contract_is_explicit() -> None:
    assert os.environ["OMNI_TEST_MODE"] == "true"
    assert os.environ["OMNI_ENABLE_SQLITE_MEMORY"] == "false"
    assert Path(os.environ["OMNI_BASE_DIR"]).resolve() == PROJECT_ROOT
    assert Path(os.environ["OMNI_PYTHON_BASE_DIR"]).resolve() == PROJECT_ROOT / "backend" / "python"
    assert (
        Path(os.environ["OMNI_PYTHON_ENTRY"]).resolve()
        == PROJECT_ROOT / "backend" / "python" / "main.py"
    )
    assert os.environ["OMNI_RUNTIME_MODE"] == "live"
    assert Path(os.environ["OMNI_WORKSPACE_ROOT"]).resolve() == PROJECT_ROOT


@pytest.mark.parametrize(
    "path_name",
    [
        "OMNI_MEMORY_JSON_PATH",
        "OMNI_JSONL_MEMORY_PATH",
        "OMNI_SQLITE_MEMORY_PATH",
    ],
)
def test_memory_file_paths_are_not_created_as_directories(path_name) -> None:
    path = Path(os.environ[path_name]).resolve()

    assert path.parent.is_dir()
    assert not path.is_dir()


def _write_nested_isolation_probe(path: Path, *, fail: bool = False) -> None:
    assertion = "assert False, 'intentional isolation probe failure'" if fail else "assert True"
    path.write_text(
        "\n".join(
            [
                "import os",
                "from pathlib import Path",
                "",
                "def test_probe():",
                "    root = Path(os.environ['OMNI_MEMORY_ROOT'])",
                "    root.mkdir(parents=True, exist_ok=True)",
                "    (root / 'probe.txt').write_text('temporary', encoding='utf-8')",
                "    Path(os.environ['OMNI_ISOLATION_MARKER']).write_text(str(root), encoding='utf-8')",
                f"    {assertion}",
                "",
            ]
        ),
        encoding="utf-8",
    )


def test_parallel_pytest_processes_receive_separate_roots(tmp_path) -> None:
    probe_parent = PROJECT_ROOT / ".tmp"
    probe_parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="parallel-isolation-", dir=probe_parent) as temp_dir:
        probe = Path(temp_dir) / "test_parallel_probe.py"
        _write_nested_isolation_probe(probe)
        processes = []
        markers = [tmp_path / f"parallel-{index}.txt" for index in range(2)]

        for marker in markers:
            env = os.environ.copy()
            env["OMNI_ISOLATION_MARKER"] = str(marker)
            processes.append(
                subprocess.Popen(
                    [sys.executable, "-m", "pytest", "-q", str(probe)],
                    cwd=PROJECT_ROOT,
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                )
            )

        results = [process.communicate(timeout=120) for process in processes]

        assert [process.returncode for process in processes] == [0, 0], results
        roots = [Path(marker.read_text(encoding="utf-8")).resolve() for marker in markers]
        assert roots[0] != roots[1]
        assert all(not root.exists() for root in roots)


def test_failed_pytest_process_removes_temporary_state(tmp_path) -> None:
    probe_parent = PROJECT_ROOT / ".tmp"
    probe_parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="failed-isolation-", dir=probe_parent) as temp_dir:
        probe = Path(temp_dir) / "test_failed_probe.py"
        marker = tmp_path / "failed.txt"
        _write_nested_isolation_probe(probe, fail=True)
        env = os.environ.copy()
        env["OMNI_ISOLATION_MARKER"] = str(marker)

        completed = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", str(probe)],
            cwd=PROJECT_ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )

        root = Path(marker.read_text(encoding="utf-8")).resolve()
        assert completed.returncode == 1
        assert not root.exists()


@pytest.mark.parametrize(
    "name",
    [
        "OMNI_TEST_MODE",
        "HOME",
        "USERPROFILE",
        "XDG_CONFIG_HOME",
        "XDG_CACHE_HOME",
        "XDG_DATA_HOME",
        "XDG_STATE_HOME",
    ],
)
def test_pytest_hooks_restore_existing_environment_values(monkeypatch, name) -> None:
    original = f"original-{name.lower()}"
    monkeypatch.setenv(name, original)
    config = _hook_config()

    omni_conftest.pytest_configure(config)
    assert os.environ.get(name) != original
    _finish_hook(config)

    assert os.environ[name] == original


def test_pytest_hooks_remove_variables_that_were_originally_absent(monkeypatch) -> None:
    monkeypatch.delenv("OMNI_UPLOAD_ROOT", raising=False)
    config = _hook_config()

    omni_conftest.pytest_configure(config)
    assert "OMNI_UPLOAD_ROOT" in os.environ
    _finish_hook(config)

    assert "OMNI_UPLOAD_ROOT" not in os.environ


@pytest.mark.parametrize("name", ["OPENAI_API_KEY", "SUPABASE_URL", "SSH_AUTH_SOCK", "GIT_ASKPASS"])
def test_sensitive_environment_is_hidden_then_restored(monkeypatch, name) -> None:
    monkeypatch.setenv(name, "sensitive-test-marker")
    config = _hook_config()

    omni_conftest.pytest_configure(config)
    assert name not in os.environ
    _finish_hook(config)

    assert os.environ[name] == "sensitive-test-marker"


def test_cleanup_failure_still_restores_environment(monkeypatch) -> None:
    monkeypatch.setenv("HOME", "original-home")
    config = _hook_config()
    omni_conftest.pytest_configure(config)
    monkeypatch.setattr(
        omni_conftest.shutil,
        "rmtree",
        lambda path: (_ for _ in ()).throw(OSError("cleanup probe")),
    )

    with pytest.warns(RuntimeWarning, match="cleanup failed"):
        _finish_hook(config, exitstatus=1)

    assert os.environ["HOME"] == "original-home"


def test_multiple_sequential_hook_sessions_remain_isolated(monkeypatch) -> None:
    monkeypatch.setenv("HOME", "caller-home")
    roots = []

    for exitstatus in [0, 1]:
        config = _hook_config()
        omni_conftest.pytest_configure(config)
        roots.append(config._omni_isolation_root)
        assert os.environ["HOME"] != "caller-home"
        _finish_hook(config, exitstatus=exitstatus)
        assert os.environ["HOME"] == "caller-home"

    assert roots[0] != roots[1]
    assert all(not root.exists() for root in roots)


@pytest.mark.parametrize("probe_fails", [False, True])
def test_pytest_main_does_not_contaminate_caller_environment(
    monkeypatch,
    tmp_path,
    probe_fails,
) -> None:
    monkeypatch.setenv("HOME", "pytest-main-caller-home")
    monkeypatch.setenv("OPENAI_API_KEY", "pytest-main-sensitive-marker")
    probe = tmp_path / f"test_nested_{probe_fails}.py"
    assertion = "assert False" if probe_fails else "assert True"
    probe.write_text(f"def test_nested():\n    {assertion}\n", encoding="utf-8")

    result = pytest.main(["-q", str(probe), "-p", "no:cacheprovider"])

    assert result == (pytest.ExitCode.TESTS_FAILED if probe_fails else pytest.ExitCode.OK)
    assert os.environ["HOME"] == "pytest-main-caller-home"
    assert os.environ["OPENAI_API_KEY"] == "pytest-main-sensitive-marker"
