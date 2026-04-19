mod error;
mod observability;
mod observability_auth;
mod run_control;

use std::{
    env,
    fs,
    net::SocketAddr,
    path::{Path, PathBuf},
    process::Stdio,
    sync::Arc,
    time::{Duration, SystemTime, UNIX_EPOCH},
};

use axum::{
    extract::State,
    http::{Request, StatusCode},
    middleware::from_fn_with_state,
    routing::{get, post},
    Json, Router,
};
use error::AppError;
use observability_auth::{require_supabase_auth, sanitize_uri_for_logs, SupabaseAuthConfig};
use runtime::Session;
use serde::{Deserialize, Serialize};
use serde_json::{json, Map, Value};
use tokio::{
    io::AsyncWriteExt,
    net::TcpListener,
    process::Command,
    sync::RwLock,
    time::timeout,
};
use tower_http::{cors::CorsLayer, trace::TraceLayer};
use tracing::{debug, error, info, warn};

#[derive(Clone)]
struct AppState {
    project_root: PathBuf,
    python_root: PathBuf,
    python_bin: String,
    python_entry: PathBuf,
    python_timeout_ms: u64,
    runtime_mode: String,
    runtime_session_version: u32,
    mock_mode: bool,
    node_bin: String,
    python_health: Arc<RwLock<DependencyStatus>>,
    supabase_auth: Arc<SupabaseAuthConfig>,
}

/// `POST /chat` JSON body. `message` is required; `client_session_id` is optional.
/// See `docs/backend/chat-session-contract.md`.
#[derive(Debug, Deserialize)]
struct ChatRequest {
    message: String,
    /// Opaque UI-owned conversation key for logging/correlation; echoed on [`ChatResponse`] when present.
    #[serde(default)]
    client_session_id: Option<String>,
}

/// `POST /api/v1/chat` JSON body — same execution path as [`ChatRequest`] with an optional nested client context.
#[derive(Debug, Deserialize, Serialize)]
struct PublicChatClientContextV1 {
    #[serde(default, skip_serializing_if = "Option::is_none")]
    source: Option<String>,
}

#[derive(Debug, Deserialize)]
struct PublicChatRequestV1 {
    message: String,
    #[serde(default)]
    client_session_id: Option<String>,
    #[serde(default)]
    client_context: Option<PublicChatClientContextV1>,
}

/// Stable v1 envelope: `api_version` plus the same fields as [`ChatResponse`] (flattened for one JSON object).
#[derive(Debug, Serialize)]
struct PublicChatResponseV1 {
    api_version: &'static str,
    #[serde(flatten)]
    chat: ChatResponse,
}

/// `POST /chat` JSON response. `session_id` remains a transport placeholder until Python returns a real orchestrator id.
/// `runtime_session_version` is the Rust runtime epoch, not a user session. See `docs/backend/chat-session-contract.md`.
#[derive(Debug, Serialize, Deserialize)]
struct ChatResponse {
    response: String,
    /// Subprocess / mock path label — **not** the client conversation id today.
    session_id: String,
    source: String,
    /// Rust runtime session epoch; aligns chat envelope with `/health` and `GET /api/v1/status` (additive field).
    #[serde(default)]
    runtime_session_version: u32,
    /// Echo of request `client_session_id` when the client sent one; omitted otherwise.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    client_session_id: Option<String>,
    #[serde(default)]
    matched_commands: Vec<String>,
    #[serde(default)]
    matched_tools: Vec<String>,
    #[serde(default)]
    stop_reason: Option<String>,
    #[serde(default)]
    usage: Option<serde_json::Value>,
    /// Server-issued or orchestrator-backed conversation id when truthfully available on the Python path; omitted otherwise.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    conversation_id: Option<String>,
    /// Conservative per-turn classification of cognitive vs degraded execution (Python `main.py` only).
    #[serde(default, skip_serializing_if = "Option::is_none")]
    cognitive_runtime_inspection: Option<Value>,
    /// Logical LLM provider ids with validated env keys (Python `main.py`); never secret values.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    providers: Option<Vec<String>>,
}

#[derive(Debug, Default, Clone, Serialize)]
struct DependencyStatus {
    observable: bool,
    last_status: String,
    #[serde(default)]
    last_error: Option<String>,
    #[serde(default)]
    last_checked_ms: Option<u64>,
}

#[derive(Debug, Serialize)]
struct DependencyHealth {
    configured_bin: String,
    entry: String,
    entry_exists: bool,
    observable: bool,
    last_status: String,
    #[serde(default)]
    last_error: Option<String>,
    #[serde(default)]
    last_checked_ms: Option<u64>,
}

#[derive(Debug, Serialize)]
struct HealthResponse {
    status: String,
    rust_service: &'static str,
    runtime_mode: String,
    runtime_session_version: u32,
    timestamp_ms: u64,
    python: DependencyHealth,
    node: DependencyHealth,
}

/// Stable public read model for product UIs (`GET /api/v1/status`). Intentionally omits file paths and binary locations.
#[derive(Debug, Serialize)]
struct PublicStatusResponseV1 {
    api_version: &'static str,
    status: String,
    runtime_mode: String,
    rust_service: String,
    python_status: String,
    node_status: String,
    runtime_session_version: u32,
    timestamp_ms: u64,
}

#[derive(Debug, Serialize)]
struct RuntimeSignalsResponse {
    status: &'static str,
    recent_signals: Vec<Value>,
    recent_mode_transitions: Vec<Value>,
    latest_run_summary: Value,
}

#[derive(Debug, Serialize)]
struct SwarmLogResponse {
    status: &'static str,
    events: Vec<Value>,
    total_events: usize,
}

#[derive(Debug, Serialize)]
struct StrategyStateResponse {
    status: &'static str,
    strategy_state: Value,
    recent_changes: Vec<Value>,
}

#[derive(Debug, Serialize)]
struct MilestonesResponse {
    status: &'static str,
    latest_run_id: Option<String>,
    milestone_state: Value,
    patch_sets: Vec<Value>,
    checkpoint_status: Value,
    execution_state: Value,
}

#[derive(Debug, Serialize)]
struct PrSummariesResponse {
    status: &'static str,
    summaries: Vec<Value>,
}

/// Authenticated operator read model — redacted runtime audit + run summary (see `docs/backend/operator-telemetry-api.md`).
#[derive(Debug, Serialize)]
struct OperatorRuntimeSignalsV1 {
    api_version: &'static str,
    status: &'static str,
    timestamp_ms: u64,
    recent_signal_sample_size: usize,
    recent_signals: Vec<Value>,
    recent_mode_transitions: Vec<Value>,
    latest_run_summary: Value,
}

/// Authenticated operator — recent strategy log entries only (no full `strategy_state` blob).
#[derive(Debug, Serialize)]
struct OperatorStrategyChangesV1 {
    api_version: &'static str,
    status: &'static str,
    timestamp_ms: u64,
    strategy_version: u64,
    recent_changes: Vec<Value>,
}

/// Authenticated operator — milestone checkpoint slice with bounded `patch_sets` and redacted nested JSON.
#[derive(Debug, Serialize)]
struct OperatorMilestonesV1 {
    api_version: &'static str,
    status: &'static str,
    timestamp_ms: u64,
    latest_run_id: Option<String>,
    checkpoint_status: Value,
    milestone_state: Value,
    patch_sets: Vec<Value>,
    patch_sets_total: usize,
    patch_sets_returned: usize,
    execution_state: Value,
}

/// Authenticated operator — bounded, redacted tail of `swarm_log.json` events.
#[derive(Debug, Serialize)]
struct OperatorSwarmV1 {
    api_version: &'static str,
    status: &'static str,
    timestamp_ms: u64,
    /// Events in this response after redaction (≤ tail cap).
    events_returned: usize,
    /// Total events in the backing log before tailing.
    total_events: usize,
    events: Vec<Value>,
}

/// Authenticated operator — PR / merge digest rows from `run-summaries.jsonl` (same projection as `/internal/pr-summaries`, redacted).
#[derive(Debug, Serialize)]
struct OperatorPrDigestV1 {
    api_version: &'static str,
    status: &'static str,
    timestamp_ms: u64,
    summaries_returned: usize,
    summaries: Vec<Value>,
}

/// Public summary of runtime signals — counts and latest run labels only (no raw audit lines).
#[derive(Debug, Serialize)]
struct PublicRuntimeSignalsSummaryV1 {
    api_version: &'static str,
    status: &'static str,
    /// Max JSONL lines read from the audit file for this summary (bounded read).
    recent_signal_sample_size: usize,
    recent_signal_count: usize,
    recent_mode_transition_count: usize,
    latest_run_id: String,
    latest_plan_kind: String,
    latest_run_message_preview: String,
    timestamp_ms: u64,
}

/// Public milestone checkpoint summary — counts and status label only.
#[derive(Debug, Serialize)]
struct PublicMilestonesSummaryV1 {
    api_version: &'static str,
    status: &'static str,
    latest_run_id: String,
    completed_milestone_count: u32,
    blocked_milestone_count: u32,
    patch_set_count: usize,
    checkpoint_status: String,
    timestamp_ms: u64,
}

/// Public strategy file summary — version, one safe weight, change log size only.
#[derive(Debug, Serialize)]
struct PublicStrategySummaryV1 {
    api_version: &'static str,
    status: &'static str,
    strategy_version: u64,
    /// Entries in `strategy_log.json` `changes` array (capped for bounded JSON).
    recent_change_log_count: usize,
    create_plan_weight: Option<f64>,
    timestamp_ms: u64,
}

#[tokio::main]
async fn main() -> Result<(), AppError> {
    init_tracing();

    let host = env::var("APP_HOST").unwrap_or_else(|_| "0.0.0.0".to_string());
    let port = env::var("PORT")
        .ok()
        .or_else(|| env::var("APP_PORT").ok())
        .and_then(|value| value.parse::<u16>().ok())
        .unwrap_or(3001);

    let python_bin = env::var("PYTHON_BIN").unwrap_or_else(|_| "python".to_string());
    let mock_mode = env::var("MOCK_CHAT")
        .map(|value| matches!(value.as_str(), "1" | "true" | "TRUE"))
        .unwrap_or(false);
    let python_entry = resolve_python_entry();
    let project_root = resolve_project_root(&python_entry);
    let python_root = resolve_python_root(&project_root, &python_entry);
    let supabase_auth = match SupabaseAuthConfig::from_env() {
        Ok(config) => Arc::new(config),
        Err(error) => {
            error!(%error, "observability auth configuration failed");
            return Err(AppError::Internal(format!(
                "observability auth configuration error: {error}"
            )));
        }
    };
    let state = AppState {
        project_root,
        python_root,
        python_bin: python_bin.clone(),
        python_entry,
        python_timeout_ms: env::var("PYTHON_TIMEOUT_MS")
            .ok()
            .and_then(|value| value.parse::<u64>().ok())
            .filter(|value| *value > 0)
            .unwrap_or(60_000),
        runtime_mode: resolve_runtime_mode(mock_mode),
        runtime_session_version: bootstrap_runtime_session().version,
        mock_mode,
        node_bin: env::var("NODE_BIN").unwrap_or_else(|_| "node".to_string()),
        python_health: Arc::new(RwLock::new(DependencyStatus {
            observable: binary_observable(&python_bin),
            last_status: "not_checked".to_string(),
            last_error: None,
            last_checked_ms: None,
        })),
        supabase_auth,
    };

    let protected_observability = Router::new()
        .route("/api/observability/snapshot", get(observability::snapshot))
        .route("/api/observability/stream", get(observability::stream))
        .route("/api/observability/traces", get(observability::traces))
        .route_layer(from_fn_with_state(
            state.clone(),
            require_supabase_auth,
        ));
    let protected_operator = Router::new()
        .route(
            "/api/v1/operator/runtime/signals",
            get(operator_v1_runtime_signals),
        )
        .route(
            "/api/v1/operator/strategy/changes",
            get(operator_v1_strategy_changes),
        )
        .route("/api/v1/operator/milestones", get(operator_v1_milestones))
        .route("/api/v1/operator/swarm", get(operator_v1_swarm))
        .route("/api/v1/operator/pr-digest", get(operator_v1_pr_digest))
        .route_layer(from_fn_with_state(
            state.clone(),
            require_supabase_auth,
        ));

    let protected_control = Router::new()
        .route("/api/control/runs", get(run_control::list_runs))
        .route("/api/control/runs/:run_id", get(run_control::get_run))
        .route(
            "/api/control/runs/summary/resolution",
            get(run_control::resolution_summary),
        )
        .route(
            "/api/control/runs/waiting-operator",
            get(run_control::runs_waiting_operator),
        )
        .route(
            "/api/control/runs/with-rollback",
            get(run_control::runs_with_rollback),
        )
        .route("/api/control/runs/:run_id/pause", post(run_control::pause_run))
        .route("/api/control/runs/:run_id/resume", post(run_control::resume_run))
        .route("/api/control/runs/:run_id/approve", post(run_control::approve_run))
        .route_layer(from_fn_with_state(
            state.clone(),
            require_supabase_auth,
        ));

    // --- Route map (see `docs/backend/public-api-roadmap.md`) ---
    // Public: /health, /chat, /api/v1/chat, /api/v1/status, /api/v1/*/summary (telemetry wave 1)
    // Internal (no auth middleware): /internal/*
    // Protected (Supabase JWT): /api/observability/*, /api/control/*, /api/v1/operator/*
    let app = Router::new()
        .route("/health", get(health))
        .route("/api/v1/status", get(public_v1_status))
        .route(
            "/api/v1/runtime/signals/summary",
            get(public_v1_runtime_signals_summary),
        )
        .route("/api/v1/milestones/summary", get(public_v1_milestones_summary))
        .route("/api/v1/strategy/summary", get(public_v1_strategy_summary))
        .route("/api/v1/chat", post(public_v1_chat))
        .route("/chat", post(chat))
        .route("/internal/runtime-signals", get(runtime_signals))
        .route("/internal/swarm-log", get(swarm_log))
        .route("/internal/strategy-state", get(strategy_state))
        .route("/internal/milestones", get(milestones))
        .route("/internal/pr-summaries", get(pr_summaries))
        .merge(protected_observability)
        .merge(protected_operator)
        .merge(protected_control)
        .layer(CorsLayer::permissive())
        .layer(
            TraceLayer::new_for_http().make_span_with(|request: &Request<_>| {
                tracing::info_span!(
                    "http-request",
                    method = %request.method(),
                    uri = %sanitize_uri_for_logs(request.uri()),
                    version = ?request.version(),
                )
            }),
        )
        .with_state(state.clone());

    let address: SocketAddr = format!("{host}:{port}")
        .parse()
        .map_err(|err| AppError::Internal(format!("invalid host/port: {err}")))?;

    let listener = TcpListener::bind(address)
        .await
        .map_err(|err| AppError::Internal(format!("failed to bind listener: {err}")))?;

    let bound_address = listener.local_addr().map_err(|err| {
        AppError::Internal(format!("failed to read listener address: {err}"))
    })?;

    info!(
        "API listening on http://{} (host={}, port={}, render_port_env={}, observability_auth=enabled)",
        bound_address,
        host,
        port,
        env::var("PORT").unwrap_or_else(|_| "unset".to_string())
    );

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

    let candidates = [
        PathBuf::from("../python/main.py"),
        PathBuf::from("backend/python/main.py"),
    ];
    for candidate in candidates {
        if candidate.exists() {
            return candidate;
        }
    }
    PathBuf::from("backend/python/main.py")
}

fn resolve_project_root(python_entry: &Path) -> PathBuf {
    if let Ok(base_dir) = env::var("BASE_DIR") {
        let candidate = PathBuf::from(base_dir);
        if candidate.exists() {
            return candidate;
        }
    }

    let current = env::current_dir().unwrap_or_else(|_| PathBuf::from("."));
    let mut candidates = vec![current];
    if let Some(parent) = python_entry.parent() {
        candidates.push(parent.to_path_buf());
        candidates.extend(parent.ancestors().map(Path::to_path_buf));
    }

    for candidate in candidates {
        if candidate.join("backend").join("python").exists()
            && candidate.join("backend").join("rust").exists()
        {
            return candidate;
        }
    }

    env::current_dir().unwrap_or_else(|_| PathBuf::from("."))
}

fn resolve_python_root(project_root: &Path, python_entry: &Path) -> PathBuf {
    if let Ok(base_dir) = env::var("PYTHON_BASE_DIR") {
        let candidate = PathBuf::from(base_dir);
        if candidate.exists() {
            return candidate;
        }
    }

    if python_entry.parent().is_some_and(|parent| parent.ends_with("python")) {
        return python_entry
            .parent()
            .map(Path::to_path_buf)
            .unwrap_or_else(|| project_root.join("backend").join("python"));
    }

    project_root.join("backend").join("python")
}

fn resolve_runtime_mode(mock_mode: bool) -> String {
    if mock_mode {
        return "mock".to_string();
    }
    match env::var("OMINI_RUNTIME_MODE")
        .unwrap_or_else(|_| "live".to_string())
        .trim()
        .to_lowercase()
        .as_str()
    {
        "fallback" | "mock" => env::var("OMINI_RUNTIME_MODE")
            .unwrap_or_else(|_| "live".to_string())
            .trim()
            .to_lowercase(),
        _ => "live".to_string(),
    }
}

fn binary_observable(bin: &str) -> bool {
    let candidate = Path::new(bin);
    if candidate.components().count() > 1 {
        return candidate.exists();
    }

    env::var_os("PATH")
        .map(|paths| {
            env::split_paths(&paths).any(|dir| {
                let direct = dir.join(bin);
                if direct.exists() {
                    return true;
                }
                if cfg!(windows) {
                    ["exe", "cmd", "bat"]
                        .iter()
                        .any(|ext| dir.join(format!("{bin}.{ext}")).exists())
                } else {
                    false
                }
            })
        })
        .unwrap_or(false)
}

fn unix_timestamp_ms() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|value| value.as_millis() as u64)
        .unwrap_or(0)
}

/// Shared liveness snapshot used by `/health` and derived public contracts.
async fn build_health_snapshot(state: &AppState) -> HealthResponse {
    let python_status = state.python_health.read().await.clone();
    let node_observable = binary_observable(&state.node_bin);
    let python_ready = matches!(
        python_status.last_status.as_str(),
        "not_checked" | "ready" | "mock"
    );
    let status = if state.python_entry.exists() && python_ready {
        "ok"
    } else {
        "degraded"
    };

    HealthResponse {
        status: status.to_string(),
        rust_service: "ok",
        runtime_mode: state.runtime_mode.clone(),
        runtime_session_version: state.runtime_session_version,
        timestamp_ms: unix_timestamp_ms(),
        python: DependencyHealth {
            configured_bin: state.python_bin.clone(),
            entry: state.python_entry.display().to_string(),
            entry_exists: state.python_entry.exists(),
            observable: python_status.observable,
            last_status: python_status.last_status,
            last_error: python_status.last_error,
            last_checked_ms: python_status.last_checked_ms,
        },
        node: DependencyHealth {
            configured_bin: state.node_bin.clone(),
            entry: String::new(),
            entry_exists: false,
            observable: node_observable,
            last_status: if node_observable {
                "observable".to_string()
            } else {
                "unavailable".to_string()
            },
            last_error: None,
            last_checked_ms: Some(unix_timestamp_ms()),
        },
    }
}

async fn health(State(state): State<AppState>) -> (StatusCode, Json<HealthResponse>) {
    let snapshot = build_health_snapshot(&state).await;
    (StatusCode::OK, Json(snapshot))
}

/// Versioned public status — subset of `/health` without paths or internal-only diagnostics.
async fn public_v1_status(State(state): State<AppState>) -> (StatusCode, Json<PublicStatusResponseV1>) {
    let h = build_health_snapshot(&state).await;
    (
        StatusCode::OK,
        Json(PublicStatusResponseV1 {
            api_version: "1",
            status: h.status.clone(),
            runtime_mode: h.runtime_mode.clone(),
            rust_service: h.rust_service.to_string(),
            python_status: h.python.last_status.clone(),
            node_status: h.node.last_status.clone(),
            runtime_session_version: h.runtime_session_version,
            timestamp_ms: h.timestamp_ms,
        }),
    )
}

fn truncate_preview(s: &str, max_chars: usize) -> String {
    let count = s.chars().count();
    if count <= max_chars {
        s.to_string()
    } else {
        format!("{}…", s.chars().take(max_chars).collect::<String>())
    }
}

/// Product-safe subset of `/internal/runtime-signals` — no raw audit JSONL rows.
async fn public_v1_runtime_signals_summary(
    State(state): State<AppState>,
) -> (StatusCode, Json<PublicRuntimeSignalsSummaryV1>) {
    const SAMPLE: usize = 20;
    let audit_path = state
        .project_root
        .join(".logs")
        .join("fusion-runtime")
        .join("execution-audit.jsonl");
    let run_summary_path = state
        .project_root
        .join(".logs")
        .join("fusion-runtime")
        .join("run-summaries.jsonl");
    let recent_signals = read_recent_jsonl(&audit_path, SAMPLE);
    let recent_mode_transition_count = recent_signals
        .iter()
        .filter(|item| item.get("event_type").and_then(Value::as_str) == Some("runtime.mode.transition"))
        .count();
    let latest_run_summary = read_latest_jsonl(&run_summary_path).unwrap_or_else(|| json!({}));
    let latest_run_id = latest_run_summary
        .get("run_id")
        .and_then(Value::as_str)
        .unwrap_or("")
        .to_string();
    let latest_plan_kind = latest_run_summary
        .get("plan_kind")
        .and_then(Value::as_str)
        .unwrap_or("")
        .to_string();
    let latest_run_message_preview = latest_run_summary
        .get("message")
        .and_then(Value::as_str)
        .map(|s| truncate_preview(s, 200))
        .unwrap_or_default();

    (
        StatusCode::OK,
        Json(PublicRuntimeSignalsSummaryV1 {
            api_version: "1",
            status: "ok",
            recent_signal_sample_size: SAMPLE,
            recent_signal_count: recent_signals.len(),
            recent_mode_transition_count,
            latest_run_id,
            latest_plan_kind,
            latest_run_message_preview,
            timestamp_ms: unix_timestamp_ms(),
        }),
    )
}

/// Product-safe subset of `/internal/milestones` — counts and checkpoint status string only.
async fn public_v1_milestones_summary(
    State(state): State<AppState>,
) -> (StatusCode, Json<PublicMilestonesSummaryV1>) {
    let latest_run_summary = read_latest_jsonl(
        &state
            .project_root
            .join(".logs")
            .join("fusion-runtime")
            .join("run-summaries.jsonl"),
    );
    let latest_run_id = latest_run_summary
        .as_ref()
        .and_then(|value| value.get("run_id"))
        .and_then(Value::as_str)
        .unwrap_or("")
        .to_string();

    let checkpoint = if latest_run_id.is_empty() {
        json!({})
    } else {
        read_json_value(
            &state
                .project_root
                .join(".logs")
                .join("fusion-runtime")
                .join("checkpoints")
                .join(format!("{latest_run_id}.json")),
        )
        .unwrap_or_else(|| json!({}))
    };
    let engineering = checkpoint
        .get("engineering_data")
        .cloned()
        .unwrap_or_else(|| json!({}));
    let milestone_state = engineering
        .get("milestone_state")
        .cloned()
        .unwrap_or_else(|| json!({}));
    let completed_milestone_count = milestone_state
        .get("completed_milestones")
        .and_then(Value::as_u64)
        .unwrap_or(0) as u32;
    let blocked_milestone_count = milestone_state
        .get("blocked_milestones")
        .and_then(Value::as_u64)
        .unwrap_or(0) as u32;
    let patch_set_count = engineering
        .get("patch_sets")
        .and_then(Value::as_array)
        .map(Vec::len)
        .unwrap_or(0);
    let checkpoint_status = checkpoint
        .get("status")
        .and_then(Value::as_str)
        .unwrap_or("unknown")
        .to_string();

    (
        StatusCode::OK,
        Json(PublicMilestonesSummaryV1 {
            api_version: "1",
            status: "ok",
            latest_run_id,
            completed_milestone_count,
            blocked_milestone_count,
            patch_set_count,
            checkpoint_status,
            timestamp_ms: unix_timestamp_ms(),
        }),
    )
}

/// Product-safe subset of `/internal/strategy-state` — no full rules blob or change payloads.
async fn public_v1_strategy_summary(
    State(state): State<AppState>,
) -> (StatusCode, Json<PublicStrategySummaryV1>) {
    const MAX_CHANGE_LOG_COUNT: usize = 10_000;
    let strategy_state_path = state
        .python_root
        .join("brain")
        .join("evolution")
        .join("strategy_state.json");
    let strategy_log_path = state
        .python_root
        .join("brain")
        .join("evolution")
        .join("strategy_log.json");
    let strategy_state = read_json_value(&strategy_state_path).unwrap_or_else(|| json!({}));
    let strategy_version = strategy_state.get("version").and_then(Value::as_u64).unwrap_or(0);
    let create_plan_weight = strategy_state
        .get("capability_weights")
        .and_then(|cw| cw.get("create_plan"))
        .and_then(Value::as_f64);
    let recent_change_log_count = read_json_value(&strategy_log_path)
        .and_then(|value| {
            value
                .get("changes")
                .and_then(Value::as_array)
                .map(Vec::len)
        })
        .unwrap_or(0)
        .min(MAX_CHANGE_LOG_COUNT);

    (
        StatusCode::OK,
        Json(PublicStrategySummaryV1 {
            api_version: "1",
            status: "ok",
            strategy_version,
            recent_change_log_count,
            create_plan_weight,
            timestamp_ms: unix_timestamp_ms(),
        }),
    )
}

const OPERATOR_JSON_MAX_DEPTH: usize = 14;
const OPERATOR_JSON_MAX_ARRAY_LEN: usize = 48;
const OPERATOR_JSON_MAX_STRING_CHARS: usize = 1200;

fn string_looks_like_filesystem_path(s: &str) -> bool {
    let t = s.trim();
    if t.len() < 2 {
        return false;
    }
    if t.starts_with('/') && !t.starts_with("//") {
        return true;
    }
    let b = t.as_bytes();
    b.len() >= 3 && b[1] == b':' && (b[2] == b'\\' || b[2] == b'/')
}

fn operator_redact_sensitive_key(key: &str) -> bool {
    let k = key.to_lowercase();
    matches!(
        k.as_str(),
        "authorization" | "password" | "api_key" | "apikey" | "access_token" | "refresh_token"
    ) || k.ends_with("_secret")
        || k == "jwt"
}

/// Bounded-depth JSON redaction for operator telemetry (paths, secrets, oversized strings/arrays).
fn operator_redact_json(value: &Value, depth: usize) -> Value {
    if depth == 0 {
        return json!("[DEPTH_LIMIT]");
    }
    match value {
        Value::Null | Value::Bool(_) | Value::Number(_) => value.clone(),
        Value::String(s) => {
            if string_looks_like_filesystem_path(s) {
                json!("[PATH_REDACTED]")
            } else {
                Value::String(truncate_preview(s, OPERATOR_JSON_MAX_STRING_CHARS))
            }
        }
        Value::Array(arr) => Value::Array(
            arr.iter()
                .take(OPERATOR_JSON_MAX_ARRAY_LEN)
                .map(|item| operator_redact_json(item, depth - 1))
                .collect(),
        ),
        Value::Object(map) => {
            let mut out = Map::new();
            for (k, v) in map.iter() {
                if operator_redact_sensitive_key(k) {
                    continue;
                }
                let kl = k.to_lowercase();
                if kl == "cwd" || kl == "executable" {
                    out.insert(k.clone(), json!("[REDACTED]"));
                    continue;
                }
                if kl.contains("path")
                    && v.as_str().is_some_and(string_looks_like_filesystem_path)
                {
                    out.insert(k.clone(), json!("[PATH_REDACTED]"));
                    continue;
                }
                if (kl == "env" || kl == "environment") && v.is_object() {
                    out.insert(k.clone(), json!({}));
                    continue;
                }
                out.insert(k.clone(), operator_redact_json(v, depth - 1));
            }
            Value::Object(out)
        }
    }
}

fn fusion_latest_checkpoint(state: &AppState) -> (Option<String>, Value) {
    let latest_run_summary = read_latest_jsonl(
        &state
            .project_root
            .join(".logs")
            .join("fusion-runtime")
            .join("run-summaries.jsonl"),
    );
    let latest_run_id = latest_run_summary
        .as_ref()
        .and_then(|value| value.get("run_id"))
        .and_then(Value::as_str)
        .map(str::to_string);
    let checkpoint = latest_run_id
        .as_ref()
        .and_then(|run_id| {
            read_json_value(
                &state
                    .project_root
                    .join(".logs")
                    .join("fusion-runtime")
                    .join("checkpoints")
                    .join(format!("{run_id}.json")),
            )
        })
        .unwrap_or_else(|| json!({}));
    (latest_run_id, checkpoint)
}

/// Latest `tail` swarm events (chronological order preserved), plus total count in file.
fn fusion_swarm_events_tail(state: &AppState, tail: usize) -> (Vec<Value>, usize) {
    let swarm_path = state
        .python_root
        .join("brain")
        .join("runtime")
        .join("swarm_log.json");
    let payload = read_json_value(&swarm_path).unwrap_or_else(|| json!({ "events": [] }));
    let events = payload
        .get("events")
        .and_then(Value::as_array)
        .cloned()
        .unwrap_or_default();
    let total_events = events.len();
    let events = events
        .into_iter()
        .rev()
        .take(tail)
        .collect::<Vec<_>>()
        .into_iter()
        .rev()
        .collect();
    (events, total_events)
}

/// Recent run-summary rows projected like `/internal/pr-summaries` (bounded `limit`).
fn fusion_pr_digest_rows(state: &AppState, limit: usize) -> Vec<Value> {
    read_recent_jsonl(
        &state
            .project_root
            .join(".logs")
            .join("fusion-runtime")
            .join("run-summaries.jsonl"),
        limit,
    )
    .into_iter()
    .map(|entry| {
        json!({
            "run_id": entry.get("run_id").cloned().unwrap_or_else(|| json!("")),
            "timestamp": entry.get("timestamp").cloned().unwrap_or_else(|| json!("")),
            "message": entry.get("message").cloned().unwrap_or_else(|| json!("")),
            "pr_summary": entry
                .get("execution_state")
                .and_then(|value| value.get("pr_summary"))
                .cloned()
                .or_else(|| entry.get("engineering_data").and_then(|value| value.get("pr_summary")).cloned())
                .unwrap_or_else(|| json!({})),
            "merge_readiness": entry
                .get("execution_state")
                .and_then(|value| value.get("merge_readiness"))
                .cloned()
                .unwrap_or_else(|| json!({})),
        })
    })
    .collect()
}

async fn runtime_signals(State(state): State<AppState>) -> (StatusCode, Json<RuntimeSignalsResponse>) {
    let audit_path = state.project_root.join(".logs").join("fusion-runtime").join("execution-audit.jsonl");
    let run_summary_path = state.project_root.join(".logs").join("fusion-runtime").join("run-summaries.jsonl");
    let recent_signals = read_recent_jsonl(&audit_path, 20);
    let recent_mode_transitions = recent_signals
        .iter()
        .filter(|item| item.get("event_type").and_then(Value::as_str) == Some("runtime.mode.transition"))
        .cloned()
        .collect::<Vec<_>>();
    let latest_run_summary = read_latest_jsonl(&run_summary_path).unwrap_or_else(|| json!({}));

    (
        StatusCode::OK,
        Json(RuntimeSignalsResponse {
            status: "ok",
            recent_signals,
            recent_mode_transitions,
            latest_run_summary,
        }),
    )
}

async fn swarm_log(State(state): State<AppState>) -> (StatusCode, Json<SwarmLogResponse>) {
    const TAIL: usize = 12;
    let (events, total_events) = fusion_swarm_events_tail(&state, TAIL);

    (
        StatusCode::OK,
        Json(SwarmLogResponse {
            status: "ok",
            events,
            total_events,
        }),
    )
}

async fn strategy_state(State(state): State<AppState>) -> (StatusCode, Json<StrategyStateResponse>) {
    let strategy_state_path = state.python_root.join("brain").join("evolution").join("strategy_state.json");
    let strategy_log_path = state.python_root.join("brain").join("evolution").join("strategy_log.json");
    let strategy_state = read_json_value(&strategy_state_path).unwrap_or_else(|| json!({}));
    let recent_changes = read_json_value(&strategy_log_path)
        .and_then(|value| value.get("changes").and_then(Value::as_array).cloned())
        .unwrap_or_default()
        .into_iter()
        .rev()
        .take(8)
        .collect::<Vec<_>>()
        .into_iter()
        .rev()
        .collect();

    (
        StatusCode::OK,
        Json(StrategyStateResponse {
            status: "ok",
            strategy_state,
            recent_changes,
        }),
    )
}

async fn milestones(State(state): State<AppState>) -> (StatusCode, Json<MilestonesResponse>) {
    let (latest_run_id, checkpoint) = fusion_latest_checkpoint(&state);
    let engineering = checkpoint.get("engineering_data").cloned().unwrap_or_else(|| json!({}));

    (
        StatusCode::OK,
        Json(MilestonesResponse {
            status: "ok",
            latest_run_id,
            milestone_state: engineering.get("milestone_state").cloned().unwrap_or_else(|| json!({})),
            patch_sets: engineering
                .get("patch_sets")
                .and_then(Value::as_array)
                .cloned()
                .unwrap_or_default(),
            checkpoint_status: json!({
                "status": checkpoint.get("status").cloned().unwrap_or_else(|| json!("unknown")),
                "next_step_index": checkpoint.get("next_step_index").cloned().unwrap_or_else(|| json!(0)),
                "total_actions": checkpoint.get("total_actions").cloned().unwrap_or_else(|| json!(0)),
            }),
            execution_state: checkpoint.get("execution_state").cloned().unwrap_or_else(|| json!({})),
        }),
    )
}

async fn pr_summaries(State(state): State<AppState>) -> (StatusCode, Json<PrSummariesResponse>) {
    const LIMIT: usize = 6;
    let summaries = fusion_pr_digest_rows(&state, LIMIT);

    (
        StatusCode::OK,
        Json(PrSummariesResponse {
            status: "ok",
            summaries,
        }),
    )
}

/// `GET /api/v1/operator/runtime/signals` — Supabase JWT; same sources as `/internal/runtime-signals` with redaction.
async fn operator_v1_runtime_signals(
    State(state): State<AppState>,
) -> (StatusCode, Json<OperatorRuntimeSignalsV1>) {
    const SAMPLE: usize = 20;
    let audit_path = state
        .project_root
        .join(".logs")
        .join("fusion-runtime")
        .join("execution-audit.jsonl");
    let run_summary_path = state
        .project_root
        .join(".logs")
        .join("fusion-runtime")
        .join("run-summaries.jsonl");
    let raw_signals = read_recent_jsonl(&audit_path, SAMPLE);
    let recent_signals: Vec<Value> = raw_signals
        .iter()
        .map(|v| operator_redact_json(v, OPERATOR_JSON_MAX_DEPTH))
        .collect();
    let recent_mode_transitions: Vec<Value> = raw_signals
        .iter()
        .filter(|item| {
            item.get("event_type").and_then(Value::as_str) == Some("runtime.mode.transition")
        })
        .map(|v| operator_redact_json(v, OPERATOR_JSON_MAX_DEPTH))
        .collect();
    let latest_run_summary = operator_redact_json(
        &read_latest_jsonl(&run_summary_path).unwrap_or_else(|| json!({})),
        OPERATOR_JSON_MAX_DEPTH,
    );

    (
        StatusCode::OK,
        Json(OperatorRuntimeSignalsV1 {
            api_version: "1",
            status: "ok",
            timestamp_ms: unix_timestamp_ms(),
            recent_signal_sample_size: SAMPLE,
            recent_signals,
            recent_mode_transitions,
            latest_run_summary,
        }),
    )
}

/// `GET /api/v1/operator/strategy/changes` — recent `strategy_log.json` entries only (no full rules blob).
async fn operator_v1_strategy_changes(
    State(state): State<AppState>,
) -> (StatusCode, Json<OperatorStrategyChangesV1>) {
    const MAX_CHANGES: usize = 12;
    let strategy_state_path = state
        .python_root
        .join("brain")
        .join("evolution")
        .join("strategy_state.json");
    let strategy_log_path = state
        .python_root
        .join("brain")
        .join("evolution")
        .join("strategy_log.json");
    let strategy_state = read_json_value(&strategy_state_path).unwrap_or_else(|| json!({}));
    let strategy_version = strategy_state.get("version").and_then(Value::as_u64).unwrap_or(0);
    let recent_changes: Vec<Value> = read_json_value(&strategy_log_path)
        .and_then(|value| value.get("changes").and_then(Value::as_array).cloned())
        .unwrap_or_default()
        .into_iter()
        .rev()
        .take(MAX_CHANGES)
        .map(|v| operator_redact_json(&v, OPERATOR_JSON_MAX_DEPTH))
        .rev()
        .collect();

    (
        StatusCode::OK,
        Json(OperatorStrategyChangesV1 {
            api_version: "1",
            status: "ok",
            timestamp_ms: unix_timestamp_ms(),
            strategy_version,
            recent_changes,
        }),
    )
}

/// `GET /api/v1/operator/milestones` — latest checkpoint slice; `patch_sets` capped; nested JSON redacted.
async fn operator_v1_milestones(
    State(state): State<AppState>,
) -> (StatusCode, Json<OperatorMilestonesV1>) {
    const MAX_PATCH: usize = 5;
    let (latest_run_id, checkpoint) = fusion_latest_checkpoint(&state);
    let engineering = checkpoint.get("engineering_data").cloned().unwrap_or_else(|| json!({}));
    let milestone_state = operator_redact_json(
        &engineering
            .get("milestone_state")
            .cloned()
            .unwrap_or_else(|| json!({})),
        OPERATOR_JSON_MAX_DEPTH,
    );
    let patch_sets_full = engineering
        .get("patch_sets")
        .and_then(Value::as_array)
        .cloned()
        .unwrap_or_default();
    let patch_sets_total = patch_sets_full.len();
    let patch_sets: Vec<Value> = patch_sets_full
        .iter()
        .take(MAX_PATCH)
        .map(|v| operator_redact_json(v, OPERATOR_JSON_MAX_DEPTH))
        .collect();
    let patch_sets_returned = patch_sets.len();
    let checkpoint_status = json!({
        "status": checkpoint.get("status").cloned().unwrap_or_else(|| json!("unknown")),
        "next_step_index": checkpoint.get("next_step_index").cloned().unwrap_or_else(|| json!(0)),
        "total_actions": checkpoint.get("total_actions").cloned().unwrap_or_else(|| json!(0)),
    });
    let execution_state = operator_redact_json(
        &checkpoint
            .get("execution_state")
            .cloned()
            .unwrap_or_else(|| json!({})),
        OPERATOR_JSON_MAX_DEPTH,
    );

    (
        StatusCode::OK,
        Json(OperatorMilestonesV1 {
            api_version: "1",
            status: "ok",
            timestamp_ms: unix_timestamp_ms(),
            latest_run_id,
            checkpoint_status,
            milestone_state,
            patch_sets,
            patch_sets_total,
            patch_sets_returned,
            execution_state,
        }),
    )
}

/// `GET /api/v1/operator/swarm` — redacted tail of `swarm_log.json` (same source as `/internal/swarm-log`).
async fn operator_v1_swarm(State(state): State<AppState>) -> (StatusCode, Json<OperatorSwarmV1>) {
    const TAIL: usize = 10;
    let (raw_events, total_events) = fusion_swarm_events_tail(&state, TAIL);
    let events: Vec<Value> = raw_events
        .iter()
        .map(|e| operator_redact_json(e, OPERATOR_JSON_MAX_DEPTH))
        .collect();
    let events_returned = events.len();

    (
        StatusCode::OK,
        Json(OperatorSwarmV1 {
            api_version: "1",
            status: "ok",
            timestamp_ms: unix_timestamp_ms(),
            events_returned,
            total_events,
            events,
        }),
    )
}

/// `GET /api/v1/operator/pr-digest` — redacted PR-style rows from `run-summaries.jsonl` (same projection as `/internal/pr-summaries`).
async fn operator_v1_pr_digest(State(state): State<AppState>) -> (StatusCode, Json<OperatorPrDigestV1>) {
    const LIMIT: usize = 6;
    let summaries: Vec<Value> = fusion_pr_digest_rows(&state, LIMIT)
        .iter()
        .map(|v| operator_redact_json(v, OPERATOR_JSON_MAX_DEPTH))
        .collect();
    let summaries_returned = summaries.len();

    (
        StatusCode::OK,
        Json(OperatorPrDigestV1 {
            api_version: "1",
            status: "ok",
            timestamp_ms: unix_timestamp_ms(),
            summaries_returned,
            summaries,
        }),
    )
}

/// Normalizes optional client session id: trim, drop empty, cap length for safe logging/JSON size.
fn normalize_client_session_id(raw: Option<String>) -> Option<String> {
    const MAX_CHARS: usize = 256;
    let inner = raw?;
    let s = inner.trim().to_string();
    if s.is_empty() {
        return None;
    }
    if s.chars().count() > MAX_CHARS {
        warn!(
            len = s.chars().count(),
            "client_session_id exceeded {MAX_CHARS} characters; truncating"
        );
        Some(s.chars().take(MAX_CHARS).collect())
    } else {
        Some(s)
    }
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

    let client_session_id = normalize_client_session_id(payload.client_session_id);

    info!(
        client_session_id = ?client_session_id,
        "processing /chat request with runtime session version {} and runtime_mode={}",
        state.runtime_session_version,
        state.runtime_mode
    );
    let response = call_python(&state, &message, client_session_id, None).await?;
    Ok((StatusCode::OK, Json(response)))
}

async fn public_v1_chat(
    State(state): State<AppState>,
    Json(payload): Json<PublicChatRequestV1>,
) -> Result<(StatusCode, Json<PublicChatResponseV1>), AppError> {
    let message = payload.message.trim().to_string();
    if message.is_empty() {
        return Err(AppError::InvalidRequest(
            "message must not be empty".to_string(),
        ));
    }

    let client_session_id = normalize_client_session_id(payload.client_session_id);
    let client_context_json = payload
        .client_context
        .as_ref()
        .and_then(|ctx| serde_json::to_value(ctx).ok());

    info!(
        client_session_id = ?client_session_id,
        "processing /api/v1/chat request with runtime session version {} and runtime_mode={}",
        state.runtime_session_version,
        state.runtime_mode
    );

    let chat = call_python(
        &state,
        &message,
        client_session_id,
        client_context_json.as_ref(),
    )
    .await?;

    Ok((
        StatusCode::OK,
        Json(PublicChatResponseV1 {
            api_version: "1",
            chat,
        }),
    ))
}

fn bootstrap_runtime_session() -> Session {
    Session::new()
}

async fn update_python_health(state: &AppState, status: &str, error_message: Option<String>) {
    let mut guard = state.python_health.write().await;
    guard.observable = binary_observable(&state.python_bin);
    guard.last_status = status.to_string();
    guard.last_error = error_message;
    guard.last_checked_ms = Some(unix_timestamp_ms());
}

const PYTHON_FALLBACK_RESPONSE: &str =
    "[degraded:rust_python_boundary] O motor cognitivo Python não respondeu de forma válida. Verifique /health, logs do processo e variáveis PYTHON_BIN / entrada backend/python/main.py.";
const PYTHON_PARSE_FAILURE_RESPONSE: &str =
    "[degraded:python_stdout] A saída do adaptador Python não é JSON válido; a resposta do cérebro pode estar incompleta.";
const PYTHON_RESPONSE_CANDIDATE_KEYS: &[&str] = &["response", "message", "text", "answer"];

fn python_debug_logging_enabled() -> bool {
    env::var("OMINI_LOG_LEVEL")
        .ok()
        .or_else(|| env::var("LOG_LEVEL").ok())
        .map(|value| value.trim().eq_ignore_ascii_case("debug"))
        .unwrap_or(false)
}

const PYTHON_CONVERSATION_ID_KEYS: &[&str] = &["server_conversation_id", "conversation_id"];

fn normalize_conversation_id_from_str(raw: &str) -> Option<String> {
    const MAX_CHARS: usize = 256;
    let trimmed = raw.trim();
    if trimmed.is_empty() {
        return None;
    }
    if trimmed.chars().any(|c| c == '\n' || c == '\r' || c.is_control()) {
        return None;
    }
    if trimmed.chars().count() > MAX_CHARS {
        return None;
    }
    Some(trimmed.to_string())
}

fn extract_conversation_id_from_python_json(json: &Value) -> Option<String> {
    for key in PYTHON_CONVERSATION_ID_KEYS {
        if let Some(s) = json.get(*key).and_then(Value::as_str) {
            if let Some(id) = normalize_conversation_id_from_str(s) {
                return Some(id);
            }
        }
    }
    None
}

fn extract_response_text_from_python_json(json: &Value) -> String {
    for key in PYTHON_RESPONSE_CANDIDATE_KEYS {
        if let Some(value) = json.get(*key).and_then(Value::as_str) {
            let candidate = value.trim();
            if !candidate.is_empty() {
                return candidate.to_string();
            }
        }
    }
    PYTHON_FALLBACK_RESPONSE.to_string()
}

fn extract_stop_reason_from_python_json(json: &Value) -> Option<String> {
    json.get("stop_reason")
        .and_then(Value::as_str)
        .map(|s| s.trim().to_string())
        .filter(|s| !s.is_empty())
}

#[derive(Debug, Clone)]
struct ParsedPythonChat {
    response: String,
    conversation_id: Option<String>,
    cognitive_runtime_inspection: Option<Value>,
    providers: Option<Vec<String>>,
    stop_reason: Option<String>,
}

fn extract_providers_from_python_json(json: &Value) -> Option<Vec<String>> {
    let arr = json.get("providers")?.as_array()?;
    let out: Vec<String> = arr
        .iter()
        .filter_map(|v| v.as_str().map(|s| s.trim().to_string()))
        .filter(|s| !s.is_empty())
        .collect();
    if out.is_empty() {
        None
    } else {
        Some(out)
    }
}

fn extract_chat_from_python_output(stdout: &str) -> ParsedPythonChat {
    let trimmed = stdout.trim();
    if trimmed.is_empty() {
        return ParsedPythonChat {
            response: PYTHON_FALLBACK_RESPONSE.to_string(),
            conversation_id: None,
            cognitive_runtime_inspection: Some(json!({
                "execution_tier": "technical_fallback",
                "rust_boundary": true,
                "reason": "python_stdout_empty_trimmed",
            })),
            providers: None,
            stop_reason: Some("python_empty_stdout".to_string()),
        };
    }

    if python_debug_logging_enabled() {
        debug!(python_stdout = %trimmed, "python subprocess stdout");
    }

    match serde_json::from_str::<Value>(trimmed) {
        Ok(json) => {
            let conversation_id = extract_conversation_id_from_python_json(&json);
            let response = extract_response_text_from_python_json(&json);
            let inspection = json.get("cognitive_runtime_inspection").cloned();
            let providers = extract_providers_from_python_json(&json);
            let stop_reason = extract_stop_reason_from_python_json(&json);
            ParsedPythonChat {
                response,
                conversation_id,
                cognitive_runtime_inspection: inspection,
                providers,
                stop_reason,
            }
        }
        Err(err) => {
            warn!(error = %err, "failed to parse python output");
            ParsedPythonChat {
                response: PYTHON_PARSE_FAILURE_RESPONSE.to_string(),
                conversation_id: None,
                cognitive_runtime_inspection: Some(json!({
                    "execution_tier": "technical_fallback",
                    "rust_boundary": true,
                    "reason": "python_stdout_json_parse_failed",
                    "parse_error": err.to_string(),
                })),
                providers: None,
                stop_reason: Some("python_stdout_invalid_json".to_string()),
            }
        }
    }
}

/// JSON body written to Python stdin (see `docs/backend/python-bridge-contract.md`).
fn build_python_stdin_json(
    message: &str,
    client_session_id: &Option<String>,
    runtime_session_version: u32,
    client_context: Option<&Value>,
) -> Vec<u8> {
    let mut m = serde_json::Map::new();
    m.insert("message".into(), Value::String(message.to_string()));
    m.insert(
        "runtime_session_version".into(),
        Value::Number(runtime_session_version.into()),
    );
    m.insert(
        "request_source".into(),
        Value::String("rust_boundary".to_string()),
    );
    if let Some(id) = client_session_id {
        m.insert("client_session_id".into(), Value::String(id.clone()));
    }
    if let Some(ctx) = client_context {
        if let Some(obj) = ctx.as_object() {
            if !obj.is_empty() {
                m.insert("client_context".into(), ctx.clone());
            }
        }
    }
    serde_json::to_vec(&Value::Object(m)).unwrap_or_else(|_| br#"{"message":""}"#.to_vec())
}

fn build_python_fallback_response(
    state: &AppState,
    source: &str,
    client_session_id: Option<String>,
    stop_reason: &str,
    detail: Option<&str>,
) -> ChatResponse {
    let mut inspection = json!({
        "execution_tier": "technical_fallback",
        "rust_boundary": true,
        "source": source,
        "stop_reason": stop_reason,
    });
    if let Some(d) = detail {
        if let Some(obj) = inspection.as_object_mut() {
            obj.insert("detail".into(), Value::String(d.to_string()));
        }
    }
    ChatResponse {
        response: PYTHON_FALLBACK_RESPONSE.to_string(),
        session_id: "python-session".to_string(),
        source: source.to_string(),
        runtime_session_version: state.runtime_session_version,
        client_session_id,
        matched_commands: Vec::new(),
        matched_tools: Vec::new(),
        stop_reason: Some(stop_reason.to_string()),
        usage: None,
        conversation_id: None,
        cognitive_runtime_inspection: Some(inspection),
        providers: None,
    }
}

async fn call_python(
    state: &AppState,
    message: &str,
    client_session_id: Option<String>,
    client_context: Option<&Value>,
) -> Result<ChatResponse, AppError> {
    if state.mock_mode {
        update_python_health(state, "mock", None).await;
        return Ok(build_mock_response(
            &state,
            message,
            "mock-env",
            client_session_id,
        ));
    }

    let stdin_body = build_python_stdin_json(
        message,
        &client_session_id,
        state.runtime_session_version,
        client_context,
    );

    let mut command = Command::new(&state.python_bin);
    command
        .arg(&state.python_entry)
        .arg(message)
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .kill_on_drop(true);

    let mut child = match command.spawn() {
        Ok(child) => child,
        Err(err) => {
            let message = format!("failed to spawn python subprocess: {err}");
            error!("{message}");
            update_python_health(state, "failed", Some(message.clone())).await;
            return Ok(build_python_fallback_response(
                &state,
                "python-subprocess",
                client_session_id.clone(),
                "python_subprocess_spawn_failed",
                Some(message.as_str()),
            ));
        }
    };

    if let Some(mut stdin) = child.stdin.take() {
        if let Err(err) = stdin.write_all(&stdin_body).await {
            let message = format!("failed to write python stdin: {err}");
            error!("{message}");
            let _ = child.kill().await;
            update_python_health(state, "failed", Some(message.clone())).await;
            return Ok(build_python_fallback_response(
                &state,
                "python-subprocess",
                client_session_id.clone(),
                "python_subprocess_stdin_failed",
                Some(message.as_str()),
            ));
        }
        if let Err(err) = stdin.flush().await {
            warn!("python stdin flush: {err}");
        }
    }

    let output = match timeout(
        Duration::from_millis(state.python_timeout_ms),
        child.wait_with_output(),
    )
    .await
    {
        Ok(Ok(output)) => output,
        Ok(Err(err)) => {
            let message = format!("failed to await python subprocess: {err}");
            error!("{message}");
            update_python_health(state, "failed", Some(message.clone())).await;
            return Ok(build_python_fallback_response(
                &state,
                "python-subprocess",
                client_session_id.clone(),
                "python_subprocess_wait_failed",
                Some(message.as_str()),
            ));
        }
        Err(_) => {
            let message = format!(
                "python subprocess timed out after {} ms",
                state.python_timeout_ms
            );
            error!("{message}");
            update_python_health(state, "timeout", Some(message.clone())).await;
            return Ok(build_python_fallback_response(
                &state,
                "python-subprocess",
                client_session_id.clone(),
                "python_subprocess_timeout",
                Some(message.as_str()),
            ));
        }
    };

    if !output.status.success() {
        let code = output.status.code().unwrap_or(-1);
        let stderr = String::from_utf8_lossy(&output.stderr).trim().to_string();
        let message = format!(
            "python adapter exited with status {}",
            code
        );
        warn!("{message}");
        if !stderr.is_empty() {
            warn!("python stderr: {stderr}");
        }
        update_python_health(
            state,
            "failed",
            Some(if stderr.is_empty() { message.clone() } else { stderr.clone() }),
        )
        .await;
        return Ok(build_python_fallback_response(
            &state,
            "python-subprocess",
            client_session_id.clone(),
            "python_subprocess_nonzero_exit",
            Some(
                if stderr.is_empty() {
                    message.as_str()
                } else {
                    stderr.as_str()
                },
            ),
        ));
    }

    let stderr = String::from_utf8_lossy(&output.stderr).trim().to_string();
    if !stderr.is_empty() {
        warn!("python adapter produced stderr on successful exit: {stderr}");
        update_python_health(state, "stderr_warning", Some(stderr)).await;
    }

    let stdout = String::from_utf8_lossy(&output.stdout).trim().to_string();
    if stdout.is_empty() {
        let message = "python adapter returned empty stdout".to_string();
        warn!("{message}");
        update_python_health(state, "empty_stdout", Some(message.clone())).await;
        return Ok(build_python_fallback_response(
            &state,
            "python-subprocess",
            client_session_id.clone(),
            "python_empty_stdout",
            Some(message.as_str()),
        ));
    }

    update_python_health(state, "ready", None).await;

    let parsed = extract_chat_from_python_output(&stdout);
    let stop_reason = parsed
        .stop_reason
        .clone()
        .unwrap_or_else(|| "python_completed".to_string());

    Ok(ChatResponse {
        response: parsed.response,
        session_id: "python-session".to_string(),
        source: "python-subprocess".to_string(),
        runtime_session_version: state.runtime_session_version,
        client_session_id,
        matched_commands: Vec::new(),
        matched_tools: Vec::new(),
        stop_reason: Some(stop_reason),
        usage: None,
        conversation_id: parsed.conversation_id,
        cognitive_runtime_inspection: parsed.cognitive_runtime_inspection,
        providers: parsed.providers,
    })
}

fn build_mock_response(
    state: &AppState,
    message: &str,
    source: &str,
    client_session_id: Option<String>,
) -> ChatResponse {
    ChatResponse {
        response: format!("Mock response from Rust backend: {message}"),
        session_id: "mock-session".to_string(),
        source: source.to_string(),
        runtime_session_version: state.runtime_session_version,
        client_session_id,
        matched_commands: Vec::new(),
        matched_tools: Vec::new(),
        stop_reason: Some("mock_completed".to_string()),
        usage: Some(serde_json::json!({
            "input_tokens": 0,
            "output_tokens": 0
        })),
        conversation_id: None,
        cognitive_runtime_inspection: None,
        providers: None,
    }
}

fn read_json_value(path: &Path) -> Option<Value> {
    fs::read_to_string(path)
        .ok()
        .and_then(|raw| serde_json::from_str::<Value>(&raw).ok())
}

fn read_recent_jsonl(path: &Path, limit: usize) -> Vec<Value> {
    fs::read_to_string(path)
        .ok()
        .map(|raw| {
            raw.lines()
                .filter_map(|line| {
                    let trimmed = line.trim();
                    if trimmed.is_empty() {
                        None
                    } else {
                        serde_json::from_str::<Value>(trimmed).ok()
                    }
                })
                .rev()
                .take(limit)
                .collect::<Vec<_>>()
                .into_iter()
                .rev()
                .collect::<Vec<_>>()
        })
        .unwrap_or_default()
}

fn read_latest_jsonl(path: &Path) -> Option<Value> {
    read_recent_jsonl(path, 1).into_iter().next()
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;

    fn temp_script(content: &str, name: &str) -> PathBuf {
        let root = env::temp_dir().join(format!("omini-rust-tests-{name}"));
        let _ = fs::create_dir_all(&root);
        let path = root.join("script.py");
        fs::write(&path, content).expect("write temp python script");
        path
    }

    fn build_test_state(script_path: PathBuf, python_timeout_ms: u64) -> AppState {
        let project_root = resolve_project_root(&script_path);
        let python_root = resolve_python_root(&project_root, &script_path);
        AppState {
            project_root,
            python_root,
            python_bin: env::var("PYTHON_BIN").unwrap_or_else(|_| "python".to_string()),
            python_entry: script_path,
            python_timeout_ms,
            runtime_mode: "live".to_string(),
            runtime_session_version: 1,
            mock_mode: false,
            node_bin: "node".to_string(),
            python_health: Arc::new(RwLock::new(DependencyStatus::default())),
            supabase_auth: Arc::new(SupabaseAuthConfig {
                jwt_secret: "test-secret".to_string(),
                issuer: "https://example.supabase.co/auth/v1".to_string(),
            }),
        }
    }

    #[tokio::test]
    async fn call_python_returns_successful_response() {
        let state = build_test_state(
            temp_script("print('{\"response\":\"ok from python\"}')\n", "success"),
            15_000,
        );
        let response = call_python(&state, "hello", None, None)
            .await
            .expect("python success");
        assert_eq!(response.response, "ok from python");
        assert_eq!(response.source, "python-subprocess");
        assert_eq!(response.stop_reason.as_deref(), Some("python_completed"));
    }

    #[tokio::test]
    async fn call_python_stdin_bridge_echoes_message_and_client_session() {
        let script = r#"import json,sys
raw=sys.stdin.read()
d=json.loads(raw)
cid=d.get("client_session_id") or ""
print(json.dumps({"response": f"msg={d['message']};cid={cid};rsv={d.get('runtime_session_version')}"}))
"#;
        let state = build_test_state(temp_script(script, "stdin-bridge"), 15_000);
        let response = call_python(&state, "hello", Some("sess-9".to_string()), None)
            .await
            .expect("python stdin bridge");
        assert_eq!(response.response, "msg=hello;cid=sess-9;rsv=1");
        assert_eq!(response.client_session_id.as_deref(), Some("sess-9"));
    }

    #[test]
    fn build_python_stdin_json_includes_optional_client_session() {
        let v = build_python_stdin_json("hi", &Some("c1".into()), 42, None);
        let parsed: Value = serde_json::from_slice(&v).expect("json");
        assert_eq!(parsed["message"].as_str(), Some("hi"));
        assert_eq!(parsed["client_session_id"].as_str(), Some("c1"));
        assert_eq!(parsed["runtime_session_version"].as_u64(), Some(42));
        assert_eq!(parsed["request_source"].as_str(), Some("rust_boundary"));
        let v2 = build_python_stdin_json("x", &None, 0, None);
        let p2: Value = serde_json::from_slice(&v2).unwrap();
        assert!(p2.get("client_session_id").is_none());
    }

    #[test]
    fn build_python_stdin_json_includes_optional_client_context() {
        let ctx = json!({"source": "frontend"});
        let v = build_python_stdin_json("m", &None, 3, Some(&ctx));
        let parsed: Value = serde_json::from_slice(&v).unwrap();
        assert_eq!(parsed["client_context"], ctx);
    }

    #[test]
    fn extract_chat_from_python_output_merges_optional_conversation_id() {
        let raw = r#"{"response":"hi","server_conversation_id":"srv-1","noise":true}"#;
        let parsed = extract_chat_from_python_output(raw);
        assert_eq!(parsed.response, "hi");
        assert_eq!(parsed.conversation_id.as_deref(), Some("srv-1"));
    }

    #[test]
    fn extract_chat_from_python_output_ignores_invalid_conversation_id() {
        let raw = format!(
            r#"{{"response":"x","conversation_id":"{}"}}"#,
            "y".repeat(300)
        );
        let parsed = extract_chat_from_python_output(&raw);
        assert!(parsed.conversation_id.is_none());
    }

    #[test]
    fn extract_chat_from_python_output_parses_providers_array() {
        let raw = r#"{"response":"hi","providers":["openai","groq","gemini"]}"#;
        let parsed = extract_chat_from_python_output(raw);
        assert_eq!(parsed.response, "hi");
        assert_eq!(
            parsed.providers,
            Some(vec![
                "openai".to_string(),
                "groq".to_string(),
                "gemini".to_string(),
            ])
        );
    }

    #[test]
    fn extract_chat_from_python_output_omits_empty_providers() {
        let raw = r#"{"response":"x","providers":[]}"#;
        let parsed = extract_chat_from_python_output(raw);
        assert!(parsed.providers.is_none());
    }

    #[test]
    fn extract_chat_from_python_output_invalid_json_sets_degraded_stop_reason() {
        let parsed = extract_chat_from_python_output("not-json {{{");
        assert_eq!(
            parsed.stop_reason.as_deref(),
            Some("python_stdout_invalid_json")
        );
        assert!(parsed.response.contains("degraded:python_stdout"));
    }

    #[test]
    fn public_chat_request_v1_deserializes_optional_client_context() {
        let raw = r#"{"message":"hi","client_session_id":"s1","client_context":{"source":"frontend"}}"#;
        let p: PublicChatRequestV1 = serde_json::from_str(raw).expect("deserialize");
        assert_eq!(p.message, "hi");
        assert_eq!(p.client_session_id.as_deref(), Some("s1"));
        let ctx = p.client_context.expect("context");
        assert_eq!(ctx.source.as_deref(), Some("frontend"));
    }

    #[test]
    fn public_chat_response_v1_serializes_api_version_and_flattened_chat() {
        let body = PublicChatResponseV1 {
            api_version: "1",
            chat: ChatResponse {
                response: "hello".into(),
                session_id: "python-session".into(),
                source: "python-subprocess".into(),
                runtime_session_version: 2,
                client_session_id: Some("c".into()),
                matched_commands: vec![],
                matched_tools: vec![],
                stop_reason: Some("completed".into()),
                usage: None,
                conversation_id: Some("conv-9".into()),
                cognitive_runtime_inspection: None,
                providers: None,
            },
        };
        let v = serde_json::to_value(&body).expect("serialize");
        assert_eq!(v["api_version"], "1");
        assert_eq!(v["response"], "hello");
        assert_eq!(v["conversation_id"], "conv-9");
    }

    #[test]
    fn public_chat_response_v1_serializes_providers_when_present() {
        let body = PublicChatResponseV1 {
            api_version: "1",
            chat: ChatResponse {
                response: "hello".into(),
                session_id: "python-session".into(),
                source: "python-subprocess".into(),
                runtime_session_version: 2,
                client_session_id: None,
                matched_commands: vec![],
                matched_tools: vec![],
                stop_reason: Some("completed".into()),
                usage: None,
                conversation_id: None,
                cognitive_runtime_inspection: None,
                providers: Some(vec!["openai".into(), "groq".into()]),
            },
        };
        let v = serde_json::to_value(&body).expect("serialize");
        assert_eq!(v["providers"], json!(["openai", "groq"]));
    }

    #[tokio::test]
    async fn call_python_returns_timeout_fallback() {
        let state = build_test_state(temp_script("import time\ntime.sleep(2)\nprint('late')\n", "timeout"), 200);
        let response = call_python(&state, "hello", None, None)
            .await
            .expect("timeout fallback expected");
        assert_eq!(response.response, PYTHON_FALLBACK_RESPONSE);
        assert_eq!(response.source, "python-subprocess");
        assert_eq!(
            response.stop_reason.as_deref(),
            Some("python_subprocess_timeout")
        );
        assert!(response.cognitive_runtime_inspection.is_some());
    }

    #[tokio::test]
    async fn call_python_returns_stderr_fallback() {
        let state = build_test_state(
            temp_script("import sys\nsys.stderr.write('boom')\nsys.exit(1)\n", "stderr"),
            15_000,
        );
        let response = call_python(&state, "hello", None, None)
            .await
            .expect("stderr fallback expected");
        assert_eq!(response.response, PYTHON_FALLBACK_RESPONSE);
        assert_eq!(response.source, "python-subprocess");
        assert_eq!(
            response.stop_reason.as_deref(),
            Some("python_subprocess_nonzero_exit")
        );
        assert!(response.cognitive_runtime_inspection.is_some());
    }

    #[test]
    fn normalize_client_session_id_trims_and_drops_empty() {
        assert_eq!(normalize_client_session_id(None), None);
        assert_eq!(normalize_client_session_id(Some("   ".to_string())), None);
        assert_eq!(
            normalize_client_session_id(Some("  abc  ".to_string())),
            Some("abc".to_string())
        );
    }

    #[test]
    fn normalize_client_session_id_truncates_long_strings() {
        let long = "x".repeat(300);
        let out = normalize_client_session_id(Some(long)).expect("truncated");
        assert_eq!(out.chars().count(), 256);
    }

    #[tokio::test]
    async fn call_python_merges_conversation_id_from_stdout_json() {
        let script = r#"print('{"response":"ok","conversation_id":"real-1"}')"#;
        let state = build_test_state(temp_script(script, "convo-id"), 15_000);
        let response = call_python(&state, "hello", None, None)
            .await
            .expect("python success");
        assert_eq!(response.response, "ok");
        assert_eq!(response.conversation_id.as_deref(), Some("real-1"));
    }

    #[test]
    fn operator_redact_masks_paths_and_cwd() {
        let v = json!({"cwd": "/tmp/x", "msg": "ok", "nested": {"repo_path": "/usr/bin"}});
        let out = operator_redact_json(&v, OPERATOR_JSON_MAX_DEPTH);
        assert_eq!(out["cwd"], "[REDACTED]");
        assert_eq!(out["msg"], "ok");
        assert_eq!(out["nested"]["repo_path"], "[PATH_REDACTED]");
    }

    #[test]
    fn operator_redact_drops_sensitive_keys() {
        let v = json!({"password": "x", "access_token": "y", "keep": 1});
        let out = operator_redact_json(&v, 10);
        assert!(out.get("password").is_none());
        assert!(out.get("access_token").is_none());
        assert_eq!(out["keep"], 1);
    }

    #[test]
    fn operator_redact_pr_digest_like_row_masks_path_in_message() {
        let row = json!({
            "run_id": "run-1",
            "message": "/home/user/secret.txt",
            "pr_summary": {"title": "ok"},
            "merge_readiness": {}
        });
        let out = operator_redact_json(&row, OPERATOR_JSON_MAX_DEPTH);
        assert_eq!(out["run_id"], "run-1");
        assert_eq!(out["message"], "[PATH_REDACTED]");
        assert_eq!(out["pr_summary"]["title"], "ok");
    }
}


