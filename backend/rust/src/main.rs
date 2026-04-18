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
use serde_json::{json, Value};
use tokio::{net::TcpListener, process::Command, sync::RwLock, time::timeout};
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

/// `POST /chat` JSON body. `message` is required; `client_session_id` is optional and not forwarded to Python yet
/// (argv-only bridge). See `docs/backend/chat-session-contract.md`.
#[derive(Debug, Deserialize)]
struct ChatRequest {
    message: String,
    /// Opaque UI-owned conversation key for logging/correlation; echoed on [`ChatResponse`] when present.
    #[serde(default)]
    client_session_id: Option<String>,
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
    // Public: /health, /chat, /api/v1/status, /api/v1/*/summary (telemetry wave 1)
    // Internal (no auth middleware): /internal/*
    // Protected (Supabase JWT): merged /api/observability/*, /api/control/*
    let app = Router::new()
        .route("/health", get(health))
        .route("/api/v1/status", get(public_v1_status))
        .route(
            "/api/v1/runtime/signals/summary",
            get(public_v1_runtime_signals_summary),
        )
        .route("/api/v1/milestones/summary", get(public_v1_milestones_summary))
        .route("/api/v1/strategy/summary", get(public_v1_strategy_summary))
        .route("/chat", post(chat))
        .route("/internal/runtime-signals", get(runtime_signals))
        .route("/internal/swarm-log", get(swarm_log))
        .route("/internal/strategy-state", get(strategy_state))
        .route("/internal/milestones", get(milestones))
        .route("/internal/pr-summaries", get(pr_summaries))
        .merge(protected_observability)
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
    let swarm_path = state.python_root.join("brain").join("runtime").join("swarm_log.json");
    let payload = read_json_value(&swarm_path).unwrap_or_else(|| json!({ "events": [] }));
    let events = payload
        .get("events")
        .and_then(Value::as_array)
        .cloned()
        .unwrap_or_default();
    let total_events = events.len();
    let events = events.into_iter().rev().take(12).collect::<Vec<_>>().into_iter().rev().collect();

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
    let latest_run_summary = read_latest_jsonl(
        &state.project_root.join(".logs").join("fusion-runtime").join("run-summaries.jsonl"),
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
    let summaries = read_recent_jsonl(
        &state.project_root.join(".logs").join("fusion-runtime").join("run-summaries.jsonl"),
        6,
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
    .collect();

    (
        StatusCode::OK,
        Json(PrSummariesResponse {
            status: "ok",
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
    let response = call_python(&state, &message, client_session_id).await?;
    Ok((StatusCode::OK, Json(response)))
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

const PYTHON_FALLBACK_RESPONSE: &str = "Entendido. Como posso ajuda-lo?";
const PYTHON_RESPONSE_CANDIDATE_KEYS: &[&str] = &["response", "message", "text", "answer"];

fn python_debug_logging_enabled() -> bool {
    env::var("OMINI_LOG_LEVEL")
        .ok()
        .or_else(|| env::var("LOG_LEVEL").ok())
        .map(|value| value.trim().eq_ignore_ascii_case("debug"))
        .unwrap_or(false)
}

fn extract_response_from_python_output(stdout: &str) -> String {
    let trimmed = stdout.trim();
    if trimmed.is_empty() {
        return PYTHON_FALLBACK_RESPONSE.to_string();
    }

    if python_debug_logging_enabled() {
        debug!(python_stdout = %trimmed, "python subprocess stdout");
    }

    match serde_json::from_str::<Value>(trimmed) {
        Ok(json) => {
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
        Err(err) => {
            warn!(error = %err, "failed to parse python output");
            PYTHON_FALLBACK_RESPONSE.to_string()
        }
    }
}

fn build_python_fallback_response(
    state: &AppState,
    source: &str,
    client_session_id: Option<String>,
) -> ChatResponse {
    ChatResponse {
        response: PYTHON_FALLBACK_RESPONSE.to_string(),
        session_id: "python-session".to_string(),
        source: source.to_string(),
        runtime_session_version: state.runtime_session_version,
        client_session_id,
        matched_commands: Vec::new(),
        matched_tools: Vec::new(),
        stop_reason: Some("completed".to_string()),
        usage: None,
    }
}

async fn call_python(
    state: &AppState,
    message: &str,
    client_session_id: Option<String>,
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

    let mut command = Command::new(&state.python_bin);
    command
        .arg(&state.python_entry)
        .arg(message)
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .kill_on_drop(true);

    let output = match timeout(Duration::from_millis(state.python_timeout_ms), command.output()).await {
        Ok(Ok(output)) => output,
        Ok(Err(err)) => {
            let message = format!("failed to spawn or await python subprocess: {err}");
            error!("{message}");
            update_python_health(state, "failed", Some(message.clone())).await;
            return Ok(build_python_fallback_response(
                &state,
                "python-subprocess",
                client_session_id.clone(),
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
        ));
    }

    update_python_health(state, "ready", None).await;

    Ok(ChatResponse {
        response: extract_response_from_python_output(&stdout),
        session_id: "python-session".to_string(),
        source: "python-subprocess".to_string(),
        runtime_session_version: state.runtime_session_version,
        client_session_id,
        matched_commands: Vec::new(),
        matched_tools: Vec::new(),
        stop_reason: Some("completed".to_string()),
        usage: None,
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
        let response = call_python(&state, "hello", None)
            .await
            .expect("python success");
        assert_eq!(response.response, "ok from python");
        assert_eq!(response.source, "python-subprocess");
    }

    #[tokio::test]
    async fn call_python_returns_timeout_fallback() {
        let state = build_test_state(temp_script("import time\ntime.sleep(2)\nprint('late')\n", "timeout"), 200);
        let response = call_python(&state, "hello", None)
            .await
            .expect("timeout fallback expected");
        assert_eq!(response.response, PYTHON_FALLBACK_RESPONSE);
        assert_eq!(response.source, "python-subprocess");
    }

    #[tokio::test]
    async fn call_python_returns_stderr_fallback() {
        let state = build_test_state(temp_script("import sys\nsys.stderr.write('boom')\nprint('ignored')\n", "stderr"), 2_000);
        let response = call_python(&state, "hello", None)
            .await
            .expect("stderr fallback expected");
        assert_eq!(response.response, PYTHON_FALLBACK_RESPONSE);
        assert_eq!(response.source, "python-subprocess");
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
}


