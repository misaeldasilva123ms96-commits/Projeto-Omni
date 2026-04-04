mod error;

use std::{
    env,
    fs,
    net::SocketAddr,
    path::{Path, PathBuf},
    process::Stdio,
    time::{SystemTime, UNIX_EPOCH},
};

use axum::{
    extract::{Path as AxumPath, Query, State},
    http::StatusCode,
    routing::{get, post},
    Json, Router,
};
use error::AppError;
use runtime::Session;
use serde::{Deserialize, Serialize};
use serde_json::Value;
use tokio::{net::TcpListener, process::Command};
use tower_http::{cors::CorsLayer, trace::TraceLayer};
use tracing::{error, info};

#[derive(Clone)]
struct AppState {
    python_bin: String,
    python_entry: PathBuf,
    python_root: PathBuf,
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

#[derive(Debug, Deserialize)]
struct SessionListQuery {
    #[serde(default)]
    user_id: Option<String>,
}

#[derive(Debug, Deserialize)]
struct SessionPath {
    session_id: String,
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
    usage: Option<Value>,
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

#[derive(Debug, Serialize)]
struct ConversationMessage {
    id: String,
    role: String,
    content: String,
    turn_id: Option<String>,
    session_id: Option<String>,
    feedback: Option<String>,
}

#[derive(Debug, Serialize)]
struct SessionListItem {
    session_id: String,
    user_id: Option<String>,
    title: String,
    preview: String,
    created_at: Option<String>,
    updated_at: Option<String>,
    turn_count: usize,
}

#[derive(Debug, Serialize)]
struct SessionDetailResponse {
    session_id: String,
    user_id: Option<String>,
    title: String,
    summary: Option<String>,
    messages: Vec<ConversationMessage>,
    created_at: Option<String>,
    updated_at: Option<String>,
}

#[tokio::main]
async fn main() -> Result<(), AppError> {
    init_tracing();

    let host = env::var("APP_HOST").unwrap_or_else(|_| "127.0.0.1".to_string());
    let port = env::var("APP_PORT")
        .ok()
        .and_then(|value| value.parse::<u16>().ok())
        .unwrap_or(3001);

    let python_entry = resolve_python_entry();
    let python_root = python_entry
        .parent()
        .map(Path::to_path_buf)
        .ok_or_else(|| AppError::Internal("failed to resolve python root".to_string()))?;

    let state = AppState {
        python_bin: env::var("PYTHON_BIN").unwrap_or_else(|_| "python".to_string()),
        python_entry,
        python_root,
        runtime_session_version: bootstrap_runtime_session().version,
        mock_mode: env::var("MOCK_CHAT")
            .map(|value| matches!(value.as_str(), "1" | "true" | "TRUE"))
            .unwrap_or(false),
    };

    let app = Router::new()
        .route("/health", get(health))
        .route("/chat", post(chat))
        .route("/feedback", post(feedback))
        .route("/sessions", get(list_sessions))
        .route("/sessions/:session_id", get(get_session))
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

async fn list_sessions(
    State(state): State<AppState>,
    Query(query): Query<SessionListQuery>,
) -> Result<(StatusCode, Json<Vec<SessionListItem>>), AppError> {
    let user_id = query.user_id.unwrap_or_default();
    let sessions_dir = sessions_dir_for(&state.python_root, &user_id);
    let mut items: Vec<SessionListItem> = Vec::new();

    if sessions_dir.exists() {
        let entries = fs::read_dir(&sessions_dir)
            .map_err(|err| AppError::Internal(format!("failed to read sessions dir: {err}")))?;

        for entry in entries.flatten() {
            let path = entry.path();
            if path.extension().and_then(|ext| ext.to_str()) != Some("json") {
                continue;
            }
            if let Some(item) = build_session_list_item(&path)? {
                items.push(item);
            }
        }
    }

    items.sort_by(|a, b| b.updated_at.cmp(&a.updated_at));
    Ok((StatusCode::OK, Json(items)))
}

async fn get_session(
    State(state): State<AppState>,
    Query(query): Query<SessionListQuery>,
    AxumPath(path): AxumPath<SessionPath>,
) -> Result<(StatusCode, Json<SessionDetailResponse>), AppError> {
    let user_id = query.user_id.unwrap_or_default();
    let session_path = sessions_dir_for(&state.python_root, &user_id).join(format!("{}.json", path.session_id));
    if !session_path.exists() {
        return Err(AppError::InvalidRequest("session not found".to_string()));
    }

    let mut payload = read_json_file(&session_path)?;
    persist_session_metadata_if_missing(&session_path, &mut payload)?;
    let title = session_title(&payload);
    let summary = payload
        .get("summary")
        .and_then(Value::as_str)
        .map(repair_text);
    let created_at = session_created_at(&payload);
    let updated_at = session_updated_at(&payload);
    let messages = session_messages(&payload);
    let response = SessionDetailResponse {
        session_id: payload
            .get("session_id")
            .and_then(Value::as_str)
            .unwrap_or(&path.session_id)
            .to_string(),
        user_id: payload.get("user_id").and_then(Value::as_str).map(str::to_string),
        title,
        summary,
        messages,
        created_at,
        updated_at,
    };

    Ok((StatusCode::OK, Json(response)))
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

    let response = call_python(&state, &message, &user_id, &session_id, &turn_id).await?;
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
    format!(
        "user-{}",
        trimmed.replace(|c: char| !c.is_ascii_alphanumeric() && c != '-' && c != '_', "-")
    )
}

fn build_turn_id() -> String {
    let millis = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|value| value.as_millis())
        .unwrap_or(0);
    format!("turn-{millis}")
}

fn sessions_dir_for(python_root: &Path, user_id: &str) -> PathBuf {
    if user_id.trim().is_empty() {
        return python_root.join("brain").join("runtime").join("sessions");
    }

    python_root
        .join("users")
        .join(safe_identifier(user_id))
        .join("sessions")
}

fn safe_identifier(value: &str) -> String {
    value
        .chars()
        .map(|ch| {
            if ch.is_ascii_alphanumeric() || ch == '-' || ch == '_' || ch == '.' {
                ch
            } else {
                '-'
            }
        })
        .collect::<String>()
        .trim_matches(&['-', '_', '.'][..])
        .to_string()
}

fn read_json_file(path: &Path) -> Result<Value, AppError> {
    let raw = fs::read_to_string(path)
        .map_err(|err| AppError::Internal(format!("failed to read session file: {err}")))?;
    serde_json::from_str(&raw)
        .map_err(|err| AppError::Internal(format!("failed to parse session file: {err}")))
}

fn build_session_list_item(path: &Path) -> Result<Option<SessionListItem>, AppError> {
    let mut payload = read_json_file(path)?;
    persist_session_metadata_if_missing(path, &mut payload)?;
    let session_id = payload
        .get("session_id")
        .and_then(Value::as_str)
        .or_else(|| path.file_stem().and_then(|stem| stem.to_str()))
        .unwrap_or_default()
        .to_string();
    if session_id.is_empty() {
        return Ok(None);
    }

    let user_id = payload.get("user_id").and_then(Value::as_str).map(str::to_string);
    let title = session_title(&payload);
    let preview = session_preview(&payload);
    let created_at = session_created_at(&payload);
    let updated_at = session_updated_at(&payload);
    let turn_count = payload
        .get("turns")
        .and_then(Value::as_array)
        .map(|turns| turns.len())
        .unwrap_or(0);

    Ok(Some(SessionListItem {
        session_id,
        user_id,
        title,
        preview,
        created_at,
        updated_at,
        turn_count,
    }))
}

fn session_title(payload: &Value) -> String {
    if let Some(title) = payload.get("title").and_then(Value::as_str) {
        let repaired = repair_text(title);
        let trimmed = repaired.trim();
        if !trimmed.is_empty() {
            return shorten(trimmed, 60);
        }
    }

    payload
        .get("turns")
        .and_then(Value::as_array)
        .and_then(|turns| {
            turns.iter().find_map(|turn| {
                turn.get("message")
                    .and_then(Value::as_str)
                    .map(repair_text)
                    .map(|text| shorten(&text, 60))
            })
        })
        .filter(|title| !title.is_empty())
        .unwrap_or_else(|| "Nova conversa".to_string())
}

fn session_preview(payload: &Value) -> String {
    payload
        .get("turns")
        .and_then(Value::as_array)
        .and_then(|turns| turns.last())
        .and_then(|turn| turn.get("response").and_then(Value::as_str).or_else(|| turn.get("message").and_then(Value::as_str)))
        .map(repair_text)
        .map(|text| shorten(&text, 72))
        .unwrap_or_default()
}

fn session_updated_at(payload: &Value) -> Option<String> {
    if let Some(updated_at) = payload.get("updated_at").and_then(Value::as_str) {
        if !updated_at.trim().is_empty() {
            return Some(updated_at.to_string());
        }
    }

    payload
        .get("turns")
        .and_then(Value::as_array)
        .and_then(|turns| turns.last())
        .and_then(|turn| turn.get("created_at").and_then(Value::as_str))
        .map(str::to_string)
}

fn session_created_at(payload: &Value) -> Option<String> {
    if let Some(created_at) = payload.get("created_at").and_then(Value::as_str) {
        if !created_at.trim().is_empty() {
            return Some(created_at.to_string());
        }
    }

    payload
        .get("turns")
        .and_then(Value::as_array)
        .and_then(|turns| turns.first())
        .and_then(|turn| turn.get("created_at").and_then(Value::as_str))
        .map(str::to_string)
}

fn session_messages(payload: &Value) -> Vec<ConversationMessage> {
    if let Some(turns) = payload.get("turns").and_then(Value::as_array) {
        let mut messages = Vec::new();
        for turn in turns {
            let turn_id = turn.get("turn_id").and_then(Value::as_str).map(str::to_string);
            let session_id = payload.get("session_id").and_then(Value::as_str).map(str::to_string);
            if let Some(user_message) = turn.get("message").and_then(Value::as_str) {
                messages.push(ConversationMessage {
                    id: format!("{}-user", turn_id.clone().unwrap_or_else(|| format!("msg-{}", messages.len()))),
                    role: "user".to_string(),
                    content: repair_text(user_message),
                    turn_id: turn_id.clone(),
                    session_id: session_id.clone(),
                    feedback: None,
                });
            }
            if let Some(assistant_message) = turn.get("response").and_then(Value::as_str) {
                let feedback = turn
                    .get("feedback")
                    .and_then(Value::as_object)
                    .and_then(|feedback| feedback.get("value"))
                    .and_then(Value::as_str)
                    .map(str::to_string);
                messages.push(ConversationMessage {
                    id: format!("{}-assistant", turn_id.clone().unwrap_or_else(|| format!("msg-{}", messages.len()))),
                    role: "assistant".to_string(),
                    content: repair_text(assistant_message),
                    turn_id: turn_id.clone(),
                    session_id: session_id.clone(),
                    feedback,
                });
            }
        }
        return messages;
    }

    payload
        .get("history")
        .and_then(Value::as_array)
        .map(|history| {
            history
                .iter()
                .enumerate()
                .filter_map(|(index, item)| {
                    Some(ConversationMessage {
                        id: format!("history-{index}"),
                        role: item.get("role")?.as_str()?.to_string(),
                        content: repair_text(item.get("content")?.as_str()?),
                        turn_id: None,
                        session_id: payload.get("session_id").and_then(Value::as_str).map(str::to_string),
                        feedback: None,
                    })
                })
                .collect::<Vec<_>>()
        })
        .unwrap_or_default()
}

fn repair_text(value: &str) -> String {
    if value.contains('Ã') || value.contains('ï') {
        let repaired = value
            .as_bytes()
            .iter()
            .copied()
            .collect::<Vec<u8>>();
        if let Ok(latin1) = String::from_utf8(repaired) {
            return latin1;
        }
    }
    value.to_string()
}

fn persist_session_metadata_if_missing(path: &Path, payload: &mut Value) -> Result<(), AppError> {
    let computed_title = session_title(payload);
    let computed_created_at = session_created_at(payload);
    let computed_updated_at = session_updated_at(payload);

    let Some(object) = payload.as_object_mut() else {
        return Ok(());
    };

    let mut changed = false;

    let title_missing = object
        .get("title")
        .and_then(Value::as_str)
        .map(|value| value.trim().is_empty())
        .unwrap_or(true);
    if title_missing {
        object.insert("title".to_string(), Value::String(computed_title));
        changed = true;
    }

    let created_missing = object
        .get("created_at")
        .and_then(Value::as_str)
        .map(|value| value.trim().is_empty())
        .unwrap_or(true);
    if created_missing {
        if let Some(created_at) = computed_created_at {
            object.insert("created_at".to_string(), Value::String(created_at));
            changed = true;
        }
    }

    let updated_missing = object
        .get("updated_at")
        .and_then(Value::as_str)
        .map(|value| value.trim().is_empty())
        .unwrap_or(true);
    if updated_missing {
        if let Some(updated_at) = computed_updated_at {
            object.insert("updated_at".to_string(), Value::String(updated_at));
            changed = true;
        }
    }

    if changed {
        let raw = serde_json::to_string_pretty(payload)
            .map_err(|err| AppError::Internal(format!("failed to serialize upgraded session: {err}")))?;
        fs::write(path, raw)
            .map_err(|err| AppError::Internal(format!("failed to persist upgraded session: {err}")))?;
    }

    Ok(())
}

fn shorten(value: &str, limit: usize) -> String {
    let trimmed = value.trim();
    if trimmed.chars().count() <= limit {
        return trimmed.to_string();
    }
    let shortened = trimmed.chars().take(limit.saturating_sub(1)).collect::<String>();
    format!("{shortened}…")
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
