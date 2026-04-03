mod error;

use std::{env, net::SocketAddr, path::PathBuf, process::Stdio};

use axum::{
    extract::State,
    http::StatusCode,
    routing::{get, post},
    Json, Router,
};
use error::AppError;
use runtime::Session;
use serde::{Deserialize, Serialize};
use tokio::{net::TcpListener, process::Command};
use tower_http::{cors::CorsLayer, trace::TraceLayer};
use tracing::{error, info};

#[derive(Clone)]
struct AppState {
    python_bin: String,
    python_entry: PathBuf,
    runtime_session_version: u32,
    mock_mode: bool,
}

#[derive(Debug, Deserialize)]
struct ChatRequest {
    message: String,
}

#[derive(Debug, Serialize, Deserialize)]
struct ChatResponse {
    response: String,
    session_id: String,
    source: String,
    #[serde(default)]
    matched_commands: Vec<String>,
    #[serde(default)]
    matched_tools: Vec<String>,
    #[serde(default)]
    stop_reason: Option<String>,
    #[serde(default)]
    usage: Option<serde_json::Value>,
}

#[derive(Debug, Serialize)]
struct HealthResponse {
    status: &'static str,
}

#[tokio::main]
async fn main() -> Result<(), AppError> {
    init_tracing();

    let host = env::var("APP_HOST").unwrap_or_else(|_| "127.0.0.1".to_string());
    let port = env::var("APP_PORT")
        .ok()
        .and_then(|value| value.parse::<u16>().ok())
        .unwrap_or(3001);

    let state = AppState {
        python_bin: env::var("PYTHON_BIN").unwrap_or_else(|_| "python".to_string()),
        python_entry: resolve_python_entry(),
        runtime_session_version: bootstrap_runtime_session().version,
        mock_mode: env::var("MOCK_CHAT")
            .map(|value| matches!(value.as_str(), "1" | "true" | "TRUE"))
            .unwrap_or(false),
    };

    let app = Router::new()
        .route("/health", get(health))
        .route("/chat", post(chat))
        .layer(CorsLayer::permissive())
        .layer(TraceLayer::new_for_http())
        .with_state(state);

    let address: SocketAddr = format!("{host}:{port}")
        .parse()
        .map_err(|err| AppError::Internal(format!("invalid host/port: {err}")))?;

    let listener = TcpListener::bind(address)
        .await
        .map_err(|err| AppError::Internal(format!("failed to bind listener: {err}")))?;

    info!("API listening on http://{}", listener.local_addr().map_err(|err| {
        AppError::Internal(format!("failed to read listener address: {err}"))
    })?);

    axum::serve(listener, app)
        .await
        .map_err(|err| AppError::Internal(format!("server failed: {err}")))?;

    Ok(())
}

fn init_tracing() {
    tracing_subscriber::fmt()
        .with_env_filter(
            tracing_subscriber::EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| "omini_api=debug,tower_http=debug,info".into()),
        )
        .init();
}

fn resolve_python_entry() -> PathBuf {
    if let Ok(raw_path) = env::var("PYTHON_ENTRY") {
        return PathBuf::from(raw_path);
    }

    PathBuf::from("../python/main.py")
}

async fn health() -> (StatusCode, Json<HealthResponse>) {
    (StatusCode::OK, Json(HealthResponse { status: "ok" }))
}

async fn chat(
    State(state): State<AppState>,
    Json(payload): Json<ChatRequest>,
) -> Result<(StatusCode, Json<ChatResponse>), AppError> {
    let message = payload.message.trim().to_string();
    if message.is_empty() {
        return Err(AppError::InvalidRequest(
            "message must not be empty".to_string(),
        ));
    }

    info!(
        "processing /chat request with runtime session version {} and mock_mode={}",
        state.runtime_session_version,
        state.mock_mode
    );
    let response = call_python(&state, &message).await?;
    Ok((StatusCode::OK, Json(response)))
}

fn bootstrap_runtime_session() -> Session {
    Session::new()
}

async fn call_python(state: &AppState, message: &str) -> Result<ChatResponse, AppError> {
    if state.mock_mode {
        return Ok(build_mock_response(message, "mock-env"));
    }

    let output = Command::new(&state.python_bin)
        .arg(&state.python_entry)
        .arg(message)
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .output()
        .await;

    let output = match output {
        Ok(output) => output,
        Err(err) => {
            error!("python spawn failed, falling back to mock response: {err}");
            return Ok(build_mock_response(message, "mock-spawn-fallback"));
        }
    };

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr).trim().to_string();
        let stdout = String::from_utf8_lossy(&output.stdout).trim().to_string();
        error!(
            "python adapter failed, falling back to mock response: status={:?} stderr={stderr}",
            output.status.code()
        );
        if !stderr.is_empty() || !stdout.is_empty() {
            return Ok(build_mock_response(message, "mock-python-fallback"));
        }
        return Err(AppError::PythonProcess("python adapter failed".to_string()));
    }

    let stdout = String::from_utf8_lossy(&output.stdout).trim().to_string();
    if stdout.is_empty() {
        error!("python adapter returned empty stdout, falling back to mock response");
        return Ok(build_mock_response(message, "mock-empty-fallback"));
    }

    Ok(ChatResponse {
        response: stdout,
        session_id: "python-session".to_string(),
        source: "python-subprocess".to_string(),
        matched_commands: Vec::new(),
        matched_tools: Vec::new(),
        stop_reason: Some("completed".to_string()),
        usage: None,
    })
}

fn build_mock_response(message: &str, source: &str) -> ChatResponse {
    ChatResponse {
        response: format!("Mock response from Rust backend: {message}"),
        session_id: "mock-session".to_string(),
        source: source.to_string(),
        matched_commands: Vec::new(),
        matched_tools: Vec::new(),
        stop_reason: Some("mock_completed".to_string()),
        usage: Some(serde_json::json!({
            "input_tokens": 0,
            "output_tokens": 0
        })),
    }
}
