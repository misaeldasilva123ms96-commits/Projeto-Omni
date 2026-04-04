mod error;

use std::{
    env,
    net::SocketAddr,
    path::PathBuf,
    process::Stdio,
    time::{SystemTime, UNIX_EPOCH},
};

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
    #[serde(default)]
    user_id: Option<String>,
    #[serde(default)]
    session_id: Option<String>,
}

#[derive(Debug, Deserialize)]
struct FeedbackRequest {
    turn_id: String,
    value: String,
    #[serde(default)]
    text: Option<String>,
    #[serde(default)]
    user_id: Option<String>,
    #[serde(default)]
    session_id: Option<String>,
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
    #[serde(default)]
    turn_id: Option<String>,
    #[serde(default)]
    user_id: Option<String>,
    #[serde(default)]
    evolution_version: Option<u32>,
}

#[derive(Debug, Serialize)]
struct FeedbackResponse {
    status: &'static str,
    turn_id: String,
    session_id: String,
    user_id: Option<String>,
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
        .route("/feedback", post(feedback))
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

    let user_id = payload.user_id.unwrap_or_default();
    let session_id = payload
        .session_id
        .filter(|value| !value.trim().is_empty())
        .unwrap_or_else(|| default_session_id(&user_id));
    let turn_id = build_turn_id();

    info!(
        "processing /chat request with runtime session version {} and mock_mode={} user_id={} session_id={}",
        state.runtime_session_version,
        state.mock_mode,
        user_id,
        session_id
    );

    let response = call_python(
        &state,
        &message,
        &user_id,
        &session_id,
        &turn_id,
    )
    .await?;
    Ok((StatusCode::OK, Json(response)))
}

async fn feedback(
    State(state): State<AppState>,
    Json(payload): Json<FeedbackRequest>,
) -> Result<(StatusCode, Json<FeedbackResponse>), AppError> {
    let turn_id = payload.turn_id.trim().to_string();
    let value = payload.value.trim().to_ascii_lowercase();
    if turn_id.is_empty() {
        return Err(AppError::InvalidRequest("turn_id must not be empty".to_string()));
    }
    if value != "up" && value != "down" {
        return Err(AppError::InvalidRequest("value must be 'up' or 'down'".to_string()));
    }

    let user_id = payload.user_id.unwrap_or_default();
    let session_id = payload
        .session_id
        .filter(|value| !value.trim().is_empty())
        .unwrap_or_else(|| default_session_id(&user_id));

    call_python_feedback(
        &state,
        &turn_id,
        &value,
        payload.text.as_deref().unwrap_or_default(),
        &user_id,
        &session_id,
    )
    .await?;

    Ok((
        StatusCode::OK,
        Json(FeedbackResponse {
            status: "recorded",
            turn_id,
            session_id,
            user_id: if user_id.is_empty() { None } else { Some(user_id) },
        }),
    ))
}

fn bootstrap_runtime_session() -> Session {
    Session::new()
}

fn default_session_id(user_id: &str) -> String {
    let trimmed = user_id.trim();
    if trimmed.is_empty() {
        return "python-session".to_string();
    }
    format!("user-{}", trimmed.replace(|c: char| !c.is_ascii_alphanumeric() && c != '-' && c != '_', "-"))
}

fn build_turn_id() -> String {
    let millis = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|value| value.as_millis())
        .unwrap_or(0);
    format!("turn-{millis}")
}

async fn call_python(
    state: &AppState,
    message: &str,
    user_id: &str,
    session_id: &str,
    turn_id: &str,
) -> Result<ChatResponse, AppError> {
    if state.mock_mode {
        return Ok(build_mock_response(message, "mock-env", session_id, turn_id, user_id));
    }

    let output = Command::new(&state.python_bin)
        .arg(&state.python_entry)
        .arg(message)
        .env("AI_USER_ID", user_id)
        .env("AI_SESSION_ID", session_id)
        .env("OMINI_TURN_ID", turn_id)
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .output()
        .await;

    let output = match output {
        Ok(output) => output,
        Err(err) => {
            error!("python spawn failed, falling back to mock response: {err}");
            return Ok(build_mock_response(message, "mock-spawn-fallback", session_id, turn_id, user_id));
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
            return Ok(build_mock_response(message, "mock-python-fallback", session_id, turn_id, user_id));
        }
        return Err(AppError::PythonProcess("python adapter failed".to_string()));
    }

    let stdout = String::from_utf8_lossy(&output.stdout).trim().to_string();
    if stdout.is_empty() {
        error!("python adapter returned empty stdout, falling back to mock response");
        return Ok(build_mock_response(message, "mock-empty-fallback", session_id, turn_id, user_id));
    }

    Ok(ChatResponse {
        response: stdout,
        session_id: session_id.to_string(),
        source: "python-subprocess".to_string(),
        matched_commands: Vec::new(),
        matched_tools: Vec::new(),
        stop_reason: Some("completed".to_string()),
        usage: None,
        turn_id: Some(turn_id.to_string()),
        user_id: if user_id.is_empty() { None } else { Some(user_id.to_string()) },
        evolution_version: None,
    })
}

async fn call_python_feedback(
    state: &AppState,
    turn_id: &str,
    value: &str,
    text: &str,
    user_id: &str,
    session_id: &str,
) -> Result<(), AppError> {
    let output = Command::new(&state.python_bin)
        .arg(&state.python_entry)
        .arg("--feedback")
        .env("AI_USER_ID", user_id)
        .env("AI_SESSION_ID", session_id)
        .env("OMINI_TURN_ID", turn_id)
        .env("OMINI_FEEDBACK_VALUE", value)
        .env("OMINI_FEEDBACK_TEXT", text)
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .output()
        .await
        .map_err(|err| AppError::PythonProcess(format!("failed to submit feedback: {err}")))?;

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr).trim().to_string();
        return Err(AppError::PythonProcess(format!("feedback adapter failed: {stderr}")));
    }

    Ok(())
}

fn build_mock_response(message: &str, source: &str, session_id: &str, turn_id: &str, user_id: &str) -> ChatResponse {
    ChatResponse {
        response: format!("Mock response from Rust backend: {message}"),
        session_id: session_id.to_string(),
        source: source.to_string(),
        matched_commands: Vec::new(),
        matched_tools: Vec::new(),
        stop_reason: Some("mock_completed".to_string()),
        usage: Some(serde_json::json!({
            "input_tokens": 0,
            "output_tokens": 0
        })),
        turn_id: Some(turn_id.to_string()),
        user_id: if user_id.is_empty() { None } else { Some(user_id.to_string()) },
        evolution_version: None,
    }
}
