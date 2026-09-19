use super::*;
use axum::response::IntoResponse;

struct SettingsTempDir(PathBuf);

impl SettingsTempDir {
    fn new() -> Self {
        let path = env::temp_dir().join(format!(
            "omni-settings-cli-{}-{}",
            std::process::id(),
            SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .unwrap()
                .as_nanos()
        ));
        fs::create_dir(&path).unwrap();
        Self(path)
    }
}

impl Drop for SettingsTempDir {
    fn drop(&mut self) {
        assert_eq!(self.0.parent(), Some(env::temp_dir().as_path()));
        assert!(self
            .0
            .file_name()
            .unwrap()
            .to_string_lossy()
            .starts_with("omni-settings-cli-"));
        fs::remove_dir_all(&self.0).expect("remove isolated settings test directory");
    }
}

fn repo_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .unwrap()
        .parent()
        .unwrap()
        .to_path_buf()
}

#[test]
fn settings_cli_path_uses_python_root_for_all_layouts() {
    let mut state = build_test_state(repo_root().join("backend/python/main.py"), 1000);
    let windows_root = if cfg!(windows) {
        PathBuf::from(r"D:\Dev\Projetos\Projeto-Omni")
    } else {
        PathBuf::from("D:")
            .join("Dev")
            .join("Projetos")
            .join("Projeto-Omni")
    };
    for project in [PathBuf::from("/repo"), PathBuf::from("/app"), windows_root] {
        state.project_root = project.clone();
        state.python_root = project.join("backend").join("python");
        assert_eq!(
            python_settings_cli_path(&state),
            state
                .python_root
                .join("config")
                .join("provider_settings_cli.py")
        );
        assert!(!python_settings_cli_path(&state)
            .components()
            .any(|part| part == std::path::Component::ParentDir));
    }
    state.python_root = PathBuf::from("custom python root");
    assert_eq!(
        python_settings_cli_path(&state),
        state
            .python_root
            .join("config")
            .join("provider_settings_cli.py")
    );
}

#[test]
fn settings_cli_docker_contract_matches_python_runtime_root() {
    let docker = include_str!("../../../Dockerfile.demo");
    assert!(docker.contains("BASE_DIR=/app"));
    assert!(docker.contains("PYTHON_BASE_DIR=/app/backend/python"));
    assert!(docker.contains("PYTHON_ENTRY=/app/backend/python/main.py"));
    assert!(docker.contains("COPY --chown=omni:omni backend/python ./backend/python"));
    let mut state = build_test_state(repo_root().join("backend/python/main.py"), 1000);
    state.project_root = PathBuf::from("/app");
    state.python_root = PathBuf::from("/app").join("backend").join("python");
    assert_eq!(
        python_settings_cli_path(&state),
        PathBuf::from("/app")
            .join("backend")
            .join("python")
            .join("config")
            .join("provider_settings_cli.py")
    );
}

#[test]
fn settings_cli_real_list_from_unrelated_cwd() {
    const CHILD: &str = "OMNI_SETTINGS_CLI_TEST_CHILD";
    let mut state = build_test_state(repo_root().join("backend/python/main.py"), 1000);
    state.project_root = repo_root();
    state.python_root = repo_root().join("backend").join("python");
    if env::var_os(CHILD).is_some() {
        assert_ne!(env::current_dir().unwrap(), state.project_root);
        assert!(python_settings_cli_path(&state).is_file());
        let runtime = tokio::runtime::Builder::new_current_thread()
            .enable_all()
            .build()
            .unwrap();
        let value = runtime.block_on(async {
            timeout(
                Duration::from_secs(20),
                run_settings_cli(&state, &["list", "settings-cli-test-user"], None),
            )
            .await
            .expect("bounded integration test")
            .expect("real settings CLI list")
        });
        let providers: Vec<ProviderMetadata> =
            serde_json::from_value(value).expect("CLI JSON provider list");
        for expected in ["openai", "openrouter", "groq", "gemini", "anthropic"] {
            assert!(providers.iter().any(|item| item.provider == expected));
        }
        assert!(providers.iter().all(|item| !item.configured));
        assert!(!Path::new(&env::var_os("OMNI_CREDENTIAL_STORE_PATH").unwrap()).exists());
        assert_eq!(
            fs::read_dir(env::current_dir().unwrap()).unwrap().count(),
            0
        );
        return;
    }
    // Change CWD and environment only in a child test process; parallel tests are unaffected.
    let directory = SettingsTempDir::new();
    // Preserve an explicitly configured relative interpreter across the CWD change.
    let python_bin = if Path::new(&state.python_bin).components().count() > 1 {
        fs::canonicalize(&state.python_bin).expect("configured Python executable")
    } else {
        PathBuf::from(&state.python_bin)
    };
    let mut command = std::process::Command::new(env::current_exe().unwrap());
    command.env_clear();
    for key in [
        "PATH",
        "SystemRoot",
        "WINDIR",
        "TEMP",
        "TMP",
        "TMPDIR",
        "LD_LIBRARY_PATH",
    ] {
        if let Some(value) = env::var_os(key) {
            command.env(key, value);
        }
    }
    let output = command
        .arg("--exact")
        .arg("main_tests::settings_cli_tests::settings_cli_real_list_from_unrelated_cwd")
        .arg("--nocapture")
        .current_dir(&directory.0)
        .env(CHILD, "1")
        .env("PYTHON_BIN", python_bin)
        .env("PYTHONDONTWRITEBYTECODE", "1")
        .env(
            "OMNI_CREDENTIAL_STORE_PATH",
            directory.0.join("credentials.enc"),
        )
        .env("OMNI_CREDENTIAL_STORE_KEY", "00".repeat(32))
        .env("OMNI_PROVIDER_HEALTH_CACHE_DIR", directory.0.join("health"))
        .output()
        .expect("isolated Rust test subprocess");
    assert!(
        output.status.success(),
        "child test failed: {} {}",
        String::from_utf8_lossy(&output.stdout),
        String::from_utf8_lossy(&output.stderr)
    );
    assert!(
        String::from_utf8_lossy(&output.stdout).contains("1 passed; 0 failed"),
        "exact child test must actually execute"
    );
    assert_eq!(fs::read_dir(&directory.0).unwrap().count(), 0);
}

#[tokio::test]
async fn settings_cli_missing_file_fails_closed_without_path_leakage() {
    let directory = SettingsTempDir::new();
    let mut state = build_test_state(directory.0.join("unused.py"), 1000);
    state.project_root = directory.0.join("repo");
    state.python_root = state.project_root.join("backend").join("python");
    fs::create_dir_all(&state.python_root).unwrap();
    // A decoy at the old location must never be executed as a fallback.
    let decoy = directory.0.join("python").join("config");
    fs::create_dir_all(&decoy).unwrap();
    fs::write(
        decoy.join("provider_settings_cli.py"),
        "from pathlib import Path\nPath(__file__).with_name('executed').touch()\nprint('[]')\n",
    )
    .unwrap();
    for is_directory in [false, true] {
        if is_directory {
            fs::create_dir_all(
                state
                    .python_root
                    .join("config")
                    .join("provider_settings_cli.py"),
            )
            .unwrap();
        }
        let error = run_settings_cli(&state, &["list", "test-user"], None)
            .await
            .unwrap_err();
        let response = error.into_response();
        assert_eq!(response.status(), StatusCode::INTERNAL_SERVER_ERROR);
        let payload = response_json(response).await;
        assert_eq!(
            payload,
            json!({"error": "internal error: settings CLI unavailable", "code": "internal_error"})
        );
        assert!(!decoy.join("executed").exists());
    }
}

#[tokio::test]
async fn settings_cli_secrets_remain_in_stdin_for_save_update_test() {
    let directory = SettingsTempDir::new();
    let mut state = build_test_state(directory.0.join("unused.py"), 1000);
    state.project_root = directory.0.join("repo");
    state.python_root = directory.0.join("configured-python");
    let config = state.python_root.join("config");
    fs::create_dir_all(&config).unwrap();
    fs::write(config.join("provider_settings_cli.py"), r#"import json, os, sys
secret = sys.stdin.read()
assert secret == 'settings-fake-stdin-sentinel'
assert secret not in ' '.join(sys.argv)
assert secret not in os.environ.values()
assert sys.argv[1:] in [[operation, 'test-user', 'openai'] for operation in ['save', 'update', 'test']]
print(json.dumps({'stdin_ok': True}))
"#).unwrap();
    for operation in ["save", "update", "test"] {
        let result = run_settings_cli(
            &state,
            &[operation, "test-user", "openai"],
            Some("settings-fake-stdin-sentinel"),
        )
        .await
        .unwrap();
        assert_eq!(result, json!({"stdin_ok": true}));
    }
}
