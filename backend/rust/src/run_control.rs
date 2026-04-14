use std::{path::PathBuf, process::Stdio, time::Duration};

use axum::{
    extract::{Path, State},
    http::StatusCode,
    Json,
};
use serde_json::{json, Value};
use tokio::{process::Command, time::timeout};

use crate::{AppState, AppError};

const CONTROL_TIMEOUT_MS: u64 = 5_000;

pub(crate) async fn pause_run(
    State(state): State<AppState>,
    Path(run_id): Path<String>,
) -> Result<(StatusCode, Json<Value>), AppError> {
    let payload = call_control_cli(&state, "pause", &[run_id.clone()], "run").await?;
    Ok((status_for_control(&payload), Json(payload)))
}

pub(crate) async fn resume_run(
    State(state): State<AppState>,
    Path(run_id): Path<String>,
) -> Result<(StatusCode, Json<Value>), AppError> {
    let payload = call_control_cli(&state, "resume", &[run_id.clone()], "run").await?;
    Ok((status_for_control(&payload), Json(payload)))
}

pub(crate) async fn approve_run(
    State(state): State<AppState>,
    Path(run_id): Path<String>,
) -> Result<(StatusCode, Json<Value>), AppError> {
    let payload = call_control_cli(&state, "approve", &[run_id.clone()], "run").await?;
    Ok((status_for_control(&payload), Json(payload)))
}

pub(crate) async fn list_runs(State(state): State<AppState>) -> Result<(StatusCode, Json<Value>), AppError> {
    let payload = call_control_cli(&state, "list", &["--limit".to_string(), "50".to_string()], "runs").await?;
    Ok((status_for_control(&payload), Json(payload)))
}

pub(crate) async fn resolution_summary(State(state): State<AppState>) -> Result<(StatusCode, Json<Value>), AppError> {
    let payload = call_control_cli(&state, "resolution_summary", &[], "summary").await?;
    Ok((status_for_control(&payload), Json(payload)))
}

pub(crate) async fn runs_waiting_operator(State(state): State<AppState>) -> Result<(StatusCode, Json<Value>), AppError> {
    let payload = call_control_cli(
        &state,
        "runs_waiting_operator",
        &["--limit".to_string(), "50".to_string()],
        "runs",
    )
    .await?;
    Ok((status_for_control(&payload), Json(payload)))
}

pub(crate) async fn runs_with_rollback(State(state): State<AppState>) -> Result<(StatusCode, Json<Value>), AppError> {
    let payload = call_control_cli(
        &state,
        "runs_with_rollback",
        &["--limit".to_string(), "50".to_string()],
        "runs",
    )
    .await?;
    Ok((status_for_control(&payload), Json(payload)))
}

pub(crate) async fn get_run(
    State(state): State<AppState>,
    Path(run_id): Path<String>,
) -> Result<(StatusCode, Json<Value>), AppError> {
    let payload = call_control_cli(&state, "show", &[run_id.clone()], "run").await?;
    Ok((status_for_control(&payload), Json(payload)))
}

fn status_for_control(payload: &Value) -> StatusCode {
    if payload.get("status").and_then(Value::as_str) == Some("ok") {
        return StatusCode::OK;
    }
    if payload.get("error").and_then(Value::as_str) == Some("run_not_found") {
        return StatusCode::NOT_FOUND;
    }
    StatusCode::BAD_REQUEST
}

async fn call_control_cli(
    state: &AppState,
    command_name: &str,
    extra_args: &[String],
    payload_key: &str,
) -> Result<Value, AppError> {
    let cli_timeout_ms = state.python_timeout_ms.min(CONTROL_TIMEOUT_MS);
    let mut command = Command::new(&state.python_bin);
    command
        .current_dir(&state.python_root)
        .arg("-m")
        .arg("brain.runtime.control.cli")
        .arg("--root")
        .arg(state.project_root.display().to_string())
        .arg(command_name)
        .args(extra_args)
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .env("PYTHONPATH", merged_pythonpath(&state.python_root))
        .kill_on_drop(true);

    let output = match timeout(Duration::from_millis(cli_timeout_ms), command.output()).await {
        Ok(Ok(output)) => output,
        Ok(Err(error)) => {
            return Err(AppError::python_process(
                "control_cli_spawn_failed",
                format!("failed to spawn control CLI: {error}"),
                None,
            ));
        }
        Err(_) => {
            return Err(AppError::python_process(
                "control_cli_timeout",
                format!("control CLI timed out after {cli_timeout_ms} ms"),
                None,
            ));
        }
    };

    let stderr = String::from_utf8_lossy(&output.stderr).trim().to_string();
    if !output.status.success() {
        return Err(AppError::python_process(
            "control_cli_failed",
            format!(
                "control CLI exited with status {}",
                output.status.code().unwrap_or(-1)
            ),
            if stderr.is_empty() { None } else { Some(stderr) },
        ));
    }

    let stdout = String::from_utf8_lossy(&output.stdout).trim().to_string();
    if stdout.is_empty() {
        return Ok(graceful_error(payload_key, "control CLI returned empty stdout".to_string()));
    }

    serde_json::from_str::<Value>(&stdout)
        .map_err(|error| AppError::python_process("control_cli_invalid_json", format!("invalid control JSON: {error}"), None))
}

fn graceful_error(payload_key: &str, message: String) -> Value {
    match payload_key {
        "run" => json!({ "status": "error", "error": message, "run": null }),
        "runs" => json!({ "status": "error", "error": message, "runs": [] }),
        "summary" => json!({ "status": "error", "error": message, "summary": {} }),
        _ => json!({ "status": "error", "error": message }),
    }
}

fn merged_pythonpath(python_root: &PathBuf) -> String {
    let current = std::env::var("PYTHONPATH").ok().filter(|value| !value.trim().is_empty());
    match current {
        Some(existing) => format!("{};{}", python_root.display(), existing),
        None => python_root.display().to_string(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use axum::{
        body::Body,
        http::{header::AUTHORIZATION, Method, Request},
        middleware::from_fn_with_state,
        routing::{get, post},
        Router,
    };
    use jsonwebtoken::{encode, Algorithm, EncodingKey, Header};
    use serde_json::json;
    use std::{fs, sync::Arc};
    use tower::ServiceExt;

    use crate::{
        observability_auth::{require_supabase_auth, SupabaseAuthConfig},
        DependencyStatus,
    };

    fn project_python_root() -> PathBuf {
        PathBuf::from(env!("CARGO_MANIFEST_DIR"))
            .parent()
            .expect("backend dir")
            .join("python")
    }

    fn temp_workspace(name: &str) -> PathBuf {
        let root = std::env::temp_dir().join(format!("omini-run-control-{name}-{}", std::process::id()));
        let _ = fs::remove_dir_all(&root);
        fs::create_dir_all(root.join(".logs").join("fusion-runtime").join("control")).expect("workspace");
        root
    }

    fn build_state(project_root: PathBuf) -> AppState {
        AppState {
            project_root,
            python_root: project_python_root(),
            python_bin: std::env::var("PYTHON_BIN").unwrap_or_else(|_| "python".to_string()),
            python_entry: std::env::temp_dir().join("unused.py"),
            python_timeout_ms: 10_000,
            runtime_mode: "live".to_string(),
            runtime_session_version: 1,
            mock_mode: false,
            node_bin: "node".to_string(),
            python_health: Arc::new(tokio::sync::RwLock::new(DependencyStatus::default())),
            supabase_auth: Arc::new(SupabaseAuthConfig {
                jwt_secret: "test-secret".to_string(),
                issuer: "https://example.supabase.co/auth/v1".to_string(),
            }),
        }
    }

    fn token() -> String {
        let now = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .expect("unix epoch")
            .as_secs() as i64;
        let claims = json!({
            "iss": "https://example.supabase.co/auth/v1",
            "sub": "operator-123",
            "aud": "authenticated",
            "exp": now + 3600,
        });
        encode(
            &Header::new(Algorithm::HS256),
            &claims,
            &EncodingKey::from_secret("test-secret".as_bytes()),
        )
        .expect("encode token")
    }

    fn control_router(state: AppState) -> Router {
        Router::new()
            .route("/api/control/runs", get(list_runs))
            .route("/api/control/runs/:run_id", get(get_run))
            .route("/api/control/runs/summary/resolution", get(resolution_summary))
            .route("/api/control/runs/waiting-operator", get(runs_waiting_operator))
            .route("/api/control/runs/with-rollback", get(runs_with_rollback))
            .route("/api/control/runs/:run_id/pause", post(pause_run))
            .route("/api/control/runs/:run_id/resume", post(resume_run))
            .route("/api/control/runs/:run_id/approve", post(approve_run))
            .route_layer(from_fn_with_state(state.clone(), require_supabase_auth))
            .with_state(state)
    }

    fn seed_run(project_root: &PathBuf, status: &str) {
        let path = project_root
            .join(".logs")
            .join("fusion-runtime")
            .join("control")
            .join("run_registry.json");
        fs::write(
            path,
            serde_json::to_string_pretty(&json!({
                "runs": {
                    "run-1": {
                        "run_id": "run-1",
                        "goal_id": "goal-1",
                        "session_id": "sess-1",
                        "status": status,
                        "started_at": "2026-04-12T00:00:00+00:00",
                        "updated_at": "2026-04-12T00:00:00+00:00",
                        "last_action": "seeded",
                        "progress_score": 0.4,
                        "metadata": {}
                    }
                }
            }))
            .expect("seed registry"),
        )
        .expect("write registry");
    }

    async fn read_json(response: axum::response::Response) -> Value {
        let body = axum::body::to_bytes(response.into_body(), usize::MAX)
            .await
            .expect("read body");
        serde_json::from_slice(&body).expect("json body")
    }

    #[tokio::test]
    async fn control_endpoints_require_auth() {
        let workspace = temp_workspace("auth");
        seed_run(&workspace, "paused");
        let response = control_router(build_state(workspace))
            .oneshot(
                Request::builder()
                    .method(Method::GET)
                    .uri("/api/control/runs")
                    .body(Body::empty())
                    .expect("request"),
            )
            .await
            .expect("response");
        assert_eq!(response.status(), StatusCode::UNAUTHORIZED);
    }

    #[tokio::test]
    async fn pause_resume_approve_endpoints_return_ok() {
        let workspace = temp_workspace("actions");
        seed_run(&workspace, "awaiting_approval");
        let auth = format!("Bearer {}", token());
        let router = control_router(build_state(workspace.clone()));

        let pause = router
            .clone()
            .oneshot(
                Request::builder()
                    .method(Method::POST)
                    .uri("/api/control/runs/run-1/pause")
                    .header(AUTHORIZATION, &auth)
                    .body(Body::empty())
                    .expect("pause request"),
            )
            .await
            .expect("pause response");
        assert_eq!(pause.status(), StatusCode::OK);

        let resume = router
            .clone()
            .oneshot(
                Request::builder()
                    .method(Method::POST)
                    .uri("/api/control/runs/run-1/resume")
                    .header(AUTHORIZATION, &auth)
                    .body(Body::empty())
                    .expect("resume request"),
            )
            .await
            .expect("resume response");
        assert_eq!(resume.status(), StatusCode::OK);

        let approve = router
            .oneshot(
                Request::builder()
                    .method(Method::POST)
                    .uri("/api/control/runs/run-1/approve")
                    .header(AUTHORIZATION, &auth)
                    .body(Body::empty())
                    .expect("approve request"),
            )
            .await
            .expect("approve response");
        assert_eq!(approve.status(), StatusCode::OK);

        let payload = read_json(approve).await;
        assert_eq!(payload["status"], "ok");
        assert_eq!(payload["run"]["status"], "running");
    }

    #[tokio::test]
    async fn list_and_get_endpoints_return_structured_json() {
        let workspace = temp_workspace("inspect");
        seed_run(&workspace, "paused");
        let auth = format!("Bearer {}", token());
        let router = control_router(build_state(workspace));

        let list = router
            .clone()
            .oneshot(
                Request::builder()
                    .method(Method::GET)
                    .uri("/api/control/runs")
                    .header(AUTHORIZATION, &auth)
                    .body(Body::empty())
                    .expect("list request"),
            )
            .await
            .expect("list response");
        assert_eq!(list.status(), StatusCode::OK);
        let list_payload = read_json(list).await;
        assert_eq!(list_payload["status"], "ok");
        assert_eq!(list_payload["runs"][0]["run_id"], "run-1");

        let show = router
            .clone()
            .oneshot(
                Request::builder()
                    .method(Method::GET)
                    .uri("/api/control/runs/run-1")
                    .header(AUTHORIZATION, &auth)
                    .body(Body::empty())
                    .expect("show request"),
            )
            .await
            .expect("show response");
        assert_eq!(show.status(), StatusCode::OK);
        let show_payload = read_json(show).await;
        assert_eq!(show_payload["run"]["status"], "paused");

        let summary = router
            .clone()
            .oneshot(
                Request::builder()
                    .method(Method::GET)
                    .uri("/api/control/runs/summary/resolution")
                    .header(AUTHORIZATION, &auth)
                    .body(Body::empty())
                    .expect("summary request"),
            )
            .await
            .expect("summary response");
        assert_eq!(summary.status(), StatusCode::OK);
        let summary_payload = read_json(summary).await;
        assert_eq!(summary_payload["status"], "ok");
        assert!(summary_payload["summary"]["resolution_counts"].is_object());

        let waiting = router
            .clone()
            .oneshot(
                Request::builder()
                    .method(Method::GET)
                    .uri("/api/control/runs/waiting-operator")
                    .header(AUTHORIZATION, &auth)
                    .body(Body::empty())
                    .expect("waiting request"),
            )
            .await
            .expect("waiting response");
        assert_eq!(waiting.status(), StatusCode::OK);
        let waiting_payload = read_json(waiting).await;
        assert_eq!(waiting_payload["status"], "ok");

        let rollback = router
            .oneshot(
                Request::builder()
                    .method(Method::GET)
                    .uri("/api/control/runs/with-rollback")
                    .header(AUTHORIZATION, &auth)
                    .body(Body::empty())
                    .expect("rollback request"),
            )
            .await
            .expect("rollback response");
        assert_eq!(rollback.status(), StatusCode::OK);
        let rollback_payload = read_json(rollback).await;
        assert_eq!(rollback_payload["status"], "ok");
    }
}
