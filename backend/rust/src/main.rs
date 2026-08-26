mod client_identity;
mod error;
mod historical_audit_capability;
mod observability;
mod observability_auth;
mod protected_historical_audit;
mod python_bridge;
mod run_control;
#[cfg(test)]
mod test_support;

use std::{
    collections::{BTreeMap, HashMap, VecDeque},
    env, fmt, fs,
    io::Seek,
    net::{IpAddr, SocketAddr},
    path::{Path, PathBuf},
    sync::{Arc, Mutex},
    time::{Duration, Instant, SystemTime, UNIX_EPOCH},
};

use axum::{
    body::Bytes,
    extract::{ConnectInfo, Path as AxumPath, State},
    http::{
        header::{AUTHORIZATION, CONTENT_TYPE},
        HeaderMap, HeaderValue, Method, Request, StatusCode,
    },
    middleware::from_fn_with_state,
    response::{IntoResponse, Response},
    routing::{delete, get, post, put},
    Extension, Json, Router,
};
use client_identity::{
    ClientIdentitySource, TrustedProxyConfig, DEFAULT_TRUST_PROXY_MAX_HOPS, MAX_TRUST_PROXY_HOPS,
};
use error::AppError;
#[cfg(test)]
use observability_auth::ProcessLocalObservabilityStreamTicketStore;
use observability_auth::{
    issue_observability_stream_ticket, observability_stream_ticket_store_from_env,
    require_observability_stream_ticket, require_supabase_auth, sanitize_uri_for_logs,
    ObservabilityStreamTicketStore, SupabaseAuthConfig,
};
use python_bridge::{run_python, BridgeSpawnFailure, PythonInvocation, StderrMode, StdinMode};
use runtime::Session;
use serde::{Deserialize, Serialize};
use serde_json::{json, Map, Value};
use tokio::{
    io::{AsyncReadExt, AsyncWriteExt},
    net::{TcpListener, TcpStream},
    sync::RwLock,
    time::timeout,
};
use tower_http::{
    cors::{AllowOrigin, CorsLayer},
    trace::TraceLayer,
};
use tracing::{debug, error, info, warn};

#[derive(Clone)]
struct AppState {
    project_root: PathBuf,
    python_root: PathBuf,
    python_bin: String,
    python_entry: PathBuf,
    python_timeout_ms: u64,
    python_runtime: PythonRuntimeConfig,
    python_circuit: Arc<Mutex<PythonCircuitBreaker>>,
    runtime_mode: String,
    runtime_session_version: u32,
    mock_mode: bool,
    node_bin: String,
    python_health: Arc<RwLock<DependencyStatus>>,
    supabase_auth: Arc<SupabaseAuthConfig>,
    observability_stream_tickets: Arc<dyn ObservabilityStreamTicketStore>,
    chat_security: Arc<ChatSecurityState>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
enum PythonRuntimeMode {
    Subprocess,
    Service,
}

#[derive(Debug, Clone)]
struct PythonRuntimeConfig {
    mode: PythonRuntimeMode,
    service_host: String,
    service_port: u16,
    service_timeout_ms: u64,
    fallback_to_subprocess: bool,
    retry_attempts: usize,
    circuit_breaker_enabled: bool,
    circuit_failure_threshold: usize,
    circuit_reset_ms: u64,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum CircuitBreakerState {
    Closed,
    Open,
    HalfOpen,
}

#[derive(Debug)]
struct PythonCircuitBreaker {
    state: CircuitBreakerState,
    failure_count: usize,
    opened_at: Option<Instant>,
    half_open_in_flight: bool,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum PythonServiceFailureKind {
    Timeout,
    ServiceFailure,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
struct PythonServiceFailure {
    kind: PythonServiceFailureKind,
    circuit_state: CircuitBreakerState,
}

pub(crate) struct ChatSecurityState {
    config: ChatSecurityConfig,
    rate_limiter: Mutex<HashMap<IpAddr, VecDeque<Instant>>>,
    rate_limit_max_clients: usize,
    trusted_proxy: TrustedProxyConfig,
}

#[derive(Debug, Clone)]
pub(crate) struct ChatSecurityConfig {
    max_message_chars: usize,
    max_body_bytes: usize,
    rate_limit_enabled: bool,
    rate_limit_per_minute: usize,
}

/// `POST /chat` JSON body. `message` is required; `client_session_id` is optional.
/// See `docs/backend/chat-session-contract.md`.
#[derive(Debug, Deserialize)]
struct ChatRequest {
    message: String,
    /// Opaque UI-owned conversation key for logging/correlation; echoed on [`ChatResponse`] when present.
    #[serde(default)]
    client_session_id: Option<String>,
    #[serde(default)]
    request_id: Option<String>,
    #[serde(default)]
    provider_preference: Option<String>,
    #[serde(default)]
    session_provider_credentials: Option<BTreeMap<String, SessionProviderCredential>>,
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
    request_id: Option<String>,
    #[serde(default)]
    client_context: Option<PublicChatClientContextV1>,
    #[serde(default)]
    provider_preference: Option<String>,
    #[serde(default)]
    session_provider_credentials: Option<BTreeMap<String, SessionProviderCredential>>,
}

#[derive(Clone, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct SessionProviderCredential {
    #[serde(default, skip_serializing_if = "Option::is_none")]
    api_key: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    model: Option<String>,
}

impl fmt::Debug for SessionProviderCredential {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("SessionProviderCredential")
            .field("api_key", &self.api_key.as_ref().map(|_| "[REDACTED]"))
            .field("model", &self.model)
            .finish()
    }
}

/// Stable v1 envelope: `api_version` plus the same fields as [`ChatResponse`] (flattened for one JSON object).
#[derive(Debug, Serialize)]
struct PublicChatResponseV1 {
    api_version: &'static str,
    #[serde(flatten)]
    chat: ChatResponse,
}

/// `POST /chat` JSON response. `session_id` is the orchestrator runtime session id when Python emits one.
/// `runtime_session_version` is the Rust runtime epoch, not a user session. See `docs/backend/chat-session-contract.md`.
#[derive(Debug, Serialize, Deserialize)]
struct ChatResponse {
    response: String,
    /// Runtime session key from Python, or a compatibility placeholder when unavailable.
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
    /// Structured bridge/runtime failure when available. Additive and backward-compatible.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    error: Option<Value>,
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
    observability_stream_ticket_store_mode: &'static str,
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
struct PublicRunnerSmokeResponseV1 {
    api_version: &'static str,
    status: String,
    selected_runtime: String,
    cwd_label: String,
    runner_exists: bool,
    adapter_exists: bool,
    fusion_brain_exists: bool,
    contract_exists: bool,
    runner_exit_code: Option<i64>,
    stdout_json_valid: bool,
    result_degraded: bool,
    public_failure_class: Option<String>,
    public_summary: Option<String>,
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

/// ----- Settings API (BYOK) -----
#[derive(Debug, Default, Serialize, Deserialize)]
struct ProviderHealthSignals {
    #[serde(default)]
    executable: bool,
    #[serde(default)]
    available: bool,
    #[serde(default)]
    reachable: Option<bool>,
    #[serde(default)]
    healthy: Option<bool>,
    #[serde(default)]
    health_valid: bool,
    #[serde(default)]
    last_checked_at: Option<u64>,
    #[serde(default)]
    valid_until: Option<u64>,
    #[serde(default)]
    latency_ms: Option<u64>,
    #[serde(default)]
    cache_status: String,
    #[serde(default)]
    circuit_state: String,
    #[serde(default)]
    consecutive_failures: u32,
    #[serde(default)]
    next_probe_at: Option<u64>,
}

/// Provider metadata — never contains secrets.
#[derive(Debug, Serialize, Deserialize)]
struct ProviderMetadata {
    provider: String,
    configured: bool,
    updated_at: Option<f64>,
    #[serde(flatten)]
    health: ProviderHealthSignals,
}

/// GET /api/v1/settings/providers
#[derive(Debug, Serialize, Deserialize)]
struct ListProvidersResponse {
    status: String,
    providers: Vec<ProviderMetadata>,
}

/// POST /api/v1/settings/providers
#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct SaveProviderRequest {
    provider: String,
    api_key: String,
}

#[derive(Debug, Serialize, Deserialize)]
struct SaveProviderResponse {
    status: String,
    provider: String,
    configured: bool,
    #[serde(default)]
    updated_at: Option<f64>,
    #[serde(flatten)]
    health: ProviderHealthSignals,
}

/// PUT /api/v1/settings/providers/{provider}
#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct UpdateProviderRequest {
    api_key: String,
}

#[derive(Debug, Serialize, Deserialize)]
struct UpdateProviderResponse {
    status: String,
    provider: String,
    configured: bool,
    #[serde(default)]
    updated_at: Option<f64>,
    #[serde(flatten)]
    health: ProviderHealthSignals,
}

/// DELETE /api/v1/settings/providers/{provider}
#[derive(Debug, Serialize, Deserialize)]
struct DeleteProviderResponse {
    status: String,
    provider: String,
    configured: bool,
    updated_at: Option<f64>,
    #[serde(flatten)]
    health: ProviderHealthSignals,
}

/// POST /api/v1/settings/providers/{provider}/test
#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct TestProviderRequest {
    api_key: String,
}

#[derive(Debug, Serialize, Deserialize)]
struct TestProviderResponse {
    provider: String,
    success: bool,
    #[serde(skip_serializing_if = "Option::is_none")]
    error: Option<String>,
    #[serde(default)]
    cached: bool,
    #[serde(flatten)]
    health: ProviderHealthSignals,
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

const DEFAULT_LOCAL_CORS_ORIGINS: [&str; 3] = [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
];

#[derive(Debug, Clone, PartialEq, Eq)]
struct CorsOriginConfig {
    origins: Vec<HeaderValue>,
    wildcard: bool,
    local_defaults_applied: bool,
}

fn env_truthy(name: &str) -> bool {
    env::var(name)
        .ok()
        .map(|value| {
            matches!(
                value.trim().to_ascii_lowercase().as_str(),
                "1" | "true" | "yes" | "on"
            )
        })
        .unwrap_or(false)
}

fn is_local_or_demo_cors_mode() -> bool {
    if env_truthy("OMNI_PUBLIC_DEMO_MODE") {
        return true;
    }

    env::var("OMNI_ENV")
        .ok()
        .into_iter()
        .map(|value| value.trim().to_ascii_lowercase())
        .any(|value| {
            matches!(
                value.as_str(),
                "local" | "dev" | "development" | "test" | "demo"
            )
        })
}

fn is_local_or_demo_runtime_mode() -> bool {
    if env_truthy("OMNI_PUBLIC_DEMO_MODE") {
        return true;
    }

    env::var("OMNI_ENV")
        .ok()
        .into_iter()
        .map(|value| value.trim().to_ascii_lowercase())
        .any(|value| {
            matches!(
                value.as_str(),
                "local" | "dev" | "development" | "test" | "demo"
            )
        })
}

fn validate_mock_mode_for_environment(mock_mode: bool) -> Result<(), AppError> {
    if !mock_mode || is_local_or_demo_runtime_mode() || env_truthy("OMNI_ALLOW_MOCK_CHAT") {
        return Ok(());
    }

    Err(AppError::Internal(
        "MOCK_CHAT is blocked outside local/demo environments; set OMNI_ALLOW_MOCK_CHAT=true only for an explicitly approved non-live deployment"
            .to_string(),
    ))
}

fn configured_cors_origins() -> Option<String> {
    env::var("OMNI_ALLOWED_ORIGINS")
        .ok()
        .map(|value| value.trim().to_string())
        .filter(|value| !value.is_empty())
}

fn parse_cors_origin_list(raw: &str, allow_wildcard: bool) -> (Vec<HeaderValue>, bool) {
    let mut origins = Vec::new();
    let mut wildcard = false;

    for item in raw.split(',') {
        let origin = item.trim();
        if origin.is_empty() {
            continue;
        }
        if origin == "*" {
            if allow_wildcard {
                wildcard = true;
            }
            continue;
        }
        if let Ok(header_value) = HeaderValue::from_str(origin) {
            origins.push(header_value);
        }
    }

    (origins, wildcard)
}

fn resolve_cors_origin_config() -> CorsOriginConfig {
    let local_or_demo = is_local_or_demo_cors_mode();
    if let Some(raw) = configured_cors_origins() {
        let (origins, wildcard) = parse_cors_origin_list(&raw, local_or_demo);
        return CorsOriginConfig {
            origins,
            wildcard,
            local_defaults_applied: false,
        };
    }

    if local_or_demo {
        let origins = DEFAULT_LOCAL_CORS_ORIGINS
            .iter()
            .filter_map(|origin| HeaderValue::from_str(origin).ok())
            .collect();
        return CorsOriginConfig {
            origins,
            wildcard: false,
            local_defaults_applied: true,
        };
    }

    CorsOriginConfig {
        origins: Vec::new(),
        wildcard: false,
        local_defaults_applied: false,
    }
}

fn build_cors_layer() -> CorsLayer {
    let config = resolve_cors_origin_config();
    let layer = CorsLayer::new()
        .allow_methods([
            Method::GET,
            Method::POST,
            Method::PUT,
            Method::DELETE,
            Method::OPTIONS,
        ])
        .allow_headers([AUTHORIZATION, CONTENT_TYPE]);

    if config.wildcard {
        layer.allow_origin(AllowOrigin::any())
    } else if !config.origins.is_empty() {
        layer.allow_origin(AllowOrigin::list(config.origins))
    } else {
        layer
    }
}

fn protected_internal_router(state: AppState) -> Router<AppState> {
    Router::new()
        .route("/internal/runtime-signals", get(runtime_signals))
        .route("/internal/swarm-log", get(swarm_log))
        .route("/internal/strategy-state", get(strategy_state))
        .route("/internal/milestones", get(milestones))
        .route("/internal/pr-summaries", get(pr_summaries))
        .route_layer(from_fn_with_state(state, require_supabase_auth))
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
    validate_mock_mode_for_environment(mock_mode)?;
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
    let observability_stream_tickets = match observability_stream_ticket_store_from_env() {
        Ok(store) => store,
        Err(error) => {
            error!(%error, "observability stream ticket store configuration failed");
            return Err(AppError::Internal(
                "observability stream ticket store configuration error".to_string(),
            ));
        }
    };
    info!(
        mode = observability_stream_tickets.mode().as_str(),
        "observability stream ticket store configured"
    );
    let chat_security = ChatSecurityState::from_env().map_err(|configuration_error| {
        error!(%configuration_error, "chat security configuration failed");
        AppError::Internal("chat security configuration error".to_string())
    })?;
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
        python_runtime: PythonRuntimeConfig::from_env(),
        python_circuit: Arc::new(Mutex::new(PythonCircuitBreaker::new())),
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
        observability_stream_tickets,
        chat_security: Arc::new(chat_security),
    };

    let protected_observability = Router::new()
        .route("/api/observability/snapshot", get(observability::snapshot))
        .route("/api/observability/traces", get(observability::traces))
        .route(
            "/api/observability/stream-ticket",
            post(issue_observability_stream_ticket),
        )
        .route_layer(from_fn_with_state(state.clone(), require_supabase_auth));
    let protected_observability_stream = Router::new()
        .route("/api/observability/stream", get(observability::stream))
        .route_layer(from_fn_with_state(
            state.clone(),
            require_observability_stream_ticket,
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
        .route_layer(from_fn_with_state(state.clone(), require_supabase_auth));

    let protected_control = Router::new()
        .route("/api/control/runs", get(run_control::list_runs))
        .route("/api/control/runs/{run_id}", get(run_control::get_run))
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
        .route(
            "/api/control/runs/{run_id}/pause",
            post(run_control::pause_run),
        )
        .route(
            "/api/control/runs/{run_id}/resume",
            post(run_control::resume_run),
        )
        .route(
            "/api/control/runs/{run_id}/approve",
            post(run_control::approve_run),
        )
        .route_layer(from_fn_with_state(state.clone(), require_supabase_auth));

    let protected_settings = Router::new()
        .route("/api/v1/settings/providers", get(settings_list_providers))
        .route("/api/v1/settings/providers", post(settings_save_provider))
        .route(
            "/api/v1/settings/providers/{provider}",
            put(settings_update_provider),
        )
        .route(
            "/api/v1/settings/providers/{provider}",
            delete(settings_delete_provider),
        )
        .route(
            "/api/v1/settings/providers/{provider}/test",
            post(settings_test_provider),
        )
        .route_layer(from_fn_with_state(state.clone(), require_supabase_auth));
    let protected_internal = protected_internal_router(state.clone());

    // --- Route map (see `docs/backend/public-api-roadmap.md`) ---
    // Public: /health, /chat, /api/v1/chat, /api/v1/status, /api/v1/*/summary
    // Protected: /api/observability/, /api/control/, /api/v1/operator/, /api/v1/settings/, /internal/
    let app = Router::new()
        .route("/health", get(health))
        .route("/api/v1/status", get(public_v1_status))
        .route(
            "/api/v1/runtime/runner-smoke",
            get(public_v1_runtime_runner_smoke),
        )
        .route(
            "/api/v1/runtime/signals/summary",
            get(public_v1_runtime_signals_summary),
        )
        .route(
            "/api/v1/milestones/summary",
            get(public_v1_milestones_summary),
        )
        .route("/api/v1/strategy/summary", get(public_v1_strategy_summary))
        .route("/api/v1/chat", post(public_v1_chat))
        .route("/chat", post(chat))
        .merge(protected_observability)
        .merge(protected_observability_stream)
        .merge(protected_operator)
        .merge(protected_control)
        .merge(protected_settings)
        .merge(protected_internal)
        .layer(build_cors_layer())
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

    let bound_address = listener
        .local_addr()
        .map_err(|err| AppError::Internal(format!("failed to read listener address: {err}")))?;

    info!(
        "API listening on http://{} (host={}, port={}, render_port_env={}, observability_auth=enabled)",
        bound_address,
        host,
        port,
        env::var("PORT").unwrap_or_else(|_| "unset".to_string())
    );

    axum::serve(
        listener,
        app.into_make_service_with_connect_info::<SocketAddr>(),
    )
    .with_graceful_shutdown(shutdown_signal())
    .await
    .map_err(|err| AppError::Internal(format!("server failed: {err}")))?;

    Ok(())
}

async fn shutdown_signal() {
    #[cfg(unix)]
    {
        let mut terminate =
            tokio::signal::unix::signal(tokio::signal::unix::SignalKind::terminate())
                .expect("failed to install SIGTERM handler");
        tokio::select! {
            result = tokio::signal::ctrl_c() => {
                if let Err(error) = result {
                    warn!(%error, "failed to listen for Ctrl+C");
                }
            }
            _ = terminate.recv() => {}
        }
    }

    #[cfg(not(unix))]
    if let Err(error) = tokio::signal::ctrl_c().await {
        warn!(%error, "failed to listen for Ctrl+C");
    }

    info!("shutdown signal received; draining HTTP connections");
}

fn init_tracing() {
    tracing_subscriber::fmt()
        .with_env_filter(
            tracing_subscriber::EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| "omni_api=debug,tower_http=debug,info".into()),
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

    if python_entry
        .parent()
        .is_some_and(|parent| parent.ends_with("python"))
    {
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
    let mode = read_env_string("OMNI_RUNTIME_MODE", "live")
        .trim()
        .to_lowercase();
    match mode.as_str() {
        "fallback" | "mock" => mode,
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

fn read_env_value(canonical: &str) -> Option<String> {
    env::var(canonical)
        .ok()
        .map(|value| value.trim().to_string())
        .filter(|value| !value.is_empty())
}

fn read_env_usize(canonical: &str, default: usize) -> usize {
    read_env_value(canonical)
        .and_then(|value| value.trim().parse::<usize>().ok())
        .filter(|value| *value > 0)
        .unwrap_or(default)
}

fn read_env_usize_clamped(canonical: &str, default: usize, max: usize) -> usize {
    read_env_usize(canonical, default).min(max)
}

fn read_bounded_env_usize(
    canonical: &str,
    default: usize,
    max: usize,
) -> Result<usize, &'static str> {
    let Some(raw) = env::var(canonical).ok() else {
        return Ok(default);
    };
    let value = raw
        .trim()
        .parse::<usize>()
        .map_err(|_| "numeric chat security configuration is invalid")?;
    if value == 0 || value > max {
        return Err("numeric chat security configuration is outside the accepted range");
    }
    Ok(value)
}

fn read_env_bool(canonical: &str, default: bool) -> bool {
    read_env_value(canonical)
        .map(|value| {
            matches!(
                value.trim().to_lowercase().as_str(),
                "1" | "true" | "yes" | "on"
            )
        })
        .unwrap_or(default)
}

fn read_env_string(canonical: &str, default: &str) -> String {
    read_env_value(canonical).unwrap_or_else(|| default.to_string())
}

fn read_env_u16(canonical: &str, default: u16) -> u16 {
    read_env_value(canonical)
        .and_then(|value| value.trim().parse::<u16>().ok())
        .filter(|value| *value > 0)
        .unwrap_or(default)
}

fn read_env_u64(canonical: &str, default: u64) -> u64 {
    read_env_value(canonical)
        .and_then(|value| value.trim().parse::<u64>().ok())
        .filter(|value| *value > 0)
        .unwrap_or(default)
}

impl PythonRuntimeConfig {
    fn from_env() -> Self {
        Self {
            mode: PythonRuntimeMode::from_env(),
            service_host: read_env_string("OMNI_PYTHON_SERVICE_HOST", "127.0.0.1"),
            service_port: read_env_u16("OMNI_PYTHON_SERVICE_PORT", 7010),
            service_timeout_ms: read_env_u64("OMNI_PYTHON_SERVICE_TIMEOUT_MS", 30_000),
            fallback_to_subprocess: read_env_bool(
                "OMNI_PYTHON_SERVICE_FALLBACK_TO_SUBPROCESS",
                false,
            ),
            retry_attempts: read_env_usize_clamped("OMNI_PYTHON_SERVICE_RETRY_ATTEMPTS", 0, 3),
            circuit_breaker_enabled: read_env_bool(
                "OMNI_PYTHON_SERVICE_CIRCUIT_BREAKER_ENABLED",
                true,
            ),
            circuit_failure_threshold: read_env_usize(
                "OMNI_PYTHON_SERVICE_CIRCUIT_FAILURE_THRESHOLD",
                3,
            ),
            circuit_reset_ms: read_env_u64("OMNI_PYTHON_SERVICE_CIRCUIT_RESET_MS", 30_000),
        }
    }
}

impl PythonCircuitBreaker {
    fn new() -> Self {
        Self {
            state: CircuitBreakerState::Closed,
            failure_count: 0,
            opened_at: None,
            half_open_in_flight: false,
        }
    }

    fn state_label(state: CircuitBreakerState) -> &'static str {
        match state {
            CircuitBreakerState::Closed => "CLOSED",
            CircuitBreakerState::Open => "OPEN",
            CircuitBreakerState::HalfOpen => "HALF_OPEN",
        }
    }

    fn before_call(&mut self, config: &PythonRuntimeConfig, now: Instant) -> CircuitBreakerState {
        if !config.circuit_breaker_enabled {
            return CircuitBreakerState::Closed;
        }

        match self.state {
            CircuitBreakerState::Closed => CircuitBreakerState::Closed,
            CircuitBreakerState::Open => {
                let reset_elapsed = self
                    .opened_at
                    .map(|opened| {
                        now.duration_since(opened).as_millis() as u64 >= config.circuit_reset_ms
                    })
                    .unwrap_or(true);
                if reset_elapsed {
                    self.state = CircuitBreakerState::HalfOpen;
                    self.half_open_in_flight = true;
                    CircuitBreakerState::HalfOpen
                } else {
                    CircuitBreakerState::Open
                }
            }
            CircuitBreakerState::HalfOpen => {
                if self.half_open_in_flight {
                    CircuitBreakerState::Open
                } else {
                    self.half_open_in_flight = true;
                    CircuitBreakerState::HalfOpen
                }
            }
        }
    }

    fn record_success(&mut self) {
        self.state = CircuitBreakerState::Closed;
        self.failure_count = 0;
        self.opened_at = None;
        self.half_open_in_flight = false;
    }

    fn record_failure(&mut self, config: &PythonRuntimeConfig, now: Instant) {
        if !config.circuit_breaker_enabled {
            return;
        }

        match self.state {
            CircuitBreakerState::HalfOpen => {
                self.state = CircuitBreakerState::Open;
                self.failure_count = config.circuit_failure_threshold.max(1);
                self.opened_at = Some(now);
                self.half_open_in_flight = false;
            }
            _ => {
                self.failure_count = self.failure_count.saturating_add(1);
                self.half_open_in_flight = false;
                if self.failure_count >= config.circuit_failure_threshold.max(1) {
                    self.state = CircuitBreakerState::Open;
                    self.opened_at = Some(now);
                }
            }
        }
    }
}

impl PythonRuntimeMode {
    fn from_env() -> Self {
        let raw = read_env_string("OMNI_PYTHON_MODE", "subprocess");
        match raw.trim().to_lowercase().as_str() {
            "service" => Self::Service,
            _ => Self::Subprocess,
        }
    }
}

impl ChatSecurityState {
    const DEFAULT_MAX_CLIENTS: usize = 10_000;
    const MAX_CLIENTS: usize = 1_000_000;

    fn from_env() -> Result<Self, &'static str> {
        let max_hops = read_bounded_env_usize(
            "OMNI_TRUST_PROXY_MAX_HOPS",
            DEFAULT_TRUST_PROXY_MAX_HOPS,
            MAX_TRUST_PROXY_HOPS,
        )?;
        let max_clients = read_bounded_env_usize(
            "OMNI_RATE_LIMIT_MAX_CLIENTS",
            Self::DEFAULT_MAX_CLIENTS,
            Self::MAX_CLIENTS,
        )?;
        let trusted_proxy = TrustedProxyConfig::parse(
            read_env_bool("OMNI_TRUST_PROXY_HEADERS", false),
            &env::var("OMNI_TRUSTED_PROXY_CIDRS").unwrap_or_default(),
            max_hops,
        )?;

        Ok(Self {
            config: ChatSecurityConfig {
                max_message_chars: read_env_usize("OMNI_MAX_MESSAGE_CHARS", 8_000),
                max_body_bytes: read_env_usize("OMNI_MAX_BODY_BYTES", 65_536),
                rate_limit_enabled: read_env_bool("OMNI_RATE_LIMIT_ENABLED", true),
                rate_limit_per_minute: read_env_usize("OMNI_RATE_LIMIT_PER_MINUTE", 30),
            },
            rate_limiter: Mutex::new(HashMap::new()),
            rate_limit_max_clients: max_clients,
            trusted_proxy,
        })
    }

    #[cfg(test)]
    fn with_config(config: ChatSecurityConfig) -> Self {
        Self {
            config,
            rate_limiter: Mutex::new(HashMap::new()),
            rate_limit_max_clients: Self::DEFAULT_MAX_CLIENTS,
            trusted_proxy: TrustedProxyConfig::direct_only(),
        }
    }

    fn check_rate_limit(&self, client_key: IpAddr, now: Instant) -> bool {
        if !self.config.rate_limit_enabled {
            return true;
        }
        let limit = self.config.rate_limit_per_minute.max(1);
        let window = Duration::from_secs(60);
        let mut guard = self
            .rate_limiter
            .lock()
            .unwrap_or_else(|poisoned| poisoned.into_inner());
        guard.retain(|_, hits| {
            while hits
                .front()
                .is_some_and(|instant| now.duration_since(*instant) >= window)
            {
                hits.pop_front();
            }
            !hits.is_empty()
        });
        if !guard.contains_key(&client_key) && guard.len() >= self.rate_limit_max_clients {
            return false;
        }
        let hits = guard.entry(client_key).or_default();
        while hits
            .front()
            .is_some_and(|instant| now.duration_since(*instant) >= window)
        {
            hits.pop_front();
        }
        if hits.len() >= limit {
            return false;
        }
        hits.push_back(now);
        true
    }
}

#[cfg(test)]
pub(crate) fn default_chat_security_state() -> Arc<ChatSecurityState> {
    Arc::new(ChatSecurityState::from_env().expect("valid chat security test configuration"))
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
        observability_stream_ticket_store_mode: state.observability_stream_tickets.mode().as_str(),
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
async fn public_v1_status(
    State(state): State<AppState>,
) -> (StatusCode, Json<PublicStatusResponseV1>) {
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

fn safe_runner_smoke_string(value: &Value, key: &str, allowed: &[&str], fallback: &str) -> String {
    let candidate = value
        .get(key)
        .and_then(Value::as_str)
        .unwrap_or(fallback)
        .trim()
        .to_ascii_lowercase();
    if allowed
        .iter()
        .any(|allowed_value| *allowed_value == candidate)
    {
        candidate
    } else {
        fallback.to_string()
    }
}

fn safe_runner_smoke_optional_string(value: &Value, key: &str) -> Option<String> {
    let candidate = value.get(key)?.as_str()?.trim();
    if candidate.is_empty() || candidate.len() > 120 {
        return None;
    }
    if !candidate
        .chars()
        .all(|ch| ch.is_ascii_alphanumeric() || matches!(ch, '_' | '-' | '.'))
    {
        return None;
    }
    Some(candidate.to_string())
}

fn bool_from_json(value: &Value, key: &str) -> bool {
    value.get(key).and_then(Value::as_bool).unwrap_or(false)
}

fn build_runner_smoke_fallback(status: &str, failure_class: &str) -> PublicRunnerSmokeResponseV1 {
    PublicRunnerSmokeResponseV1 {
        api_version: "1",
        status: status.to_string(),
        selected_runtime: "unknown".to_string(),
        cwd_label: "unknown".to_string(),
        runner_exists: false,
        adapter_exists: false,
        fusion_brain_exists: false,
        contract_exists: false,
        runner_exit_code: None,
        stdout_json_valid: false,
        result_degraded: true,
        public_failure_class: Some(failure_class.to_string()),
        public_summary: Some(format!("runner_smoke_{failure_class}")),
    }
}

fn parse_runner_smoke_response(value: &Value) -> PublicRunnerSmokeResponseV1 {
    PublicRunnerSmokeResponseV1 {
        api_version: "1",
        status: safe_runner_smoke_string(value, "status", &["ok", "degraded", "error"], "error"),
        selected_runtime: safe_runner_smoke_string(
            value,
            "selected_runtime",
            &["node", "bun", "unknown"],
            "unknown",
        ),
        cwd_label: safe_runner_smoke_string(
            value,
            "cwd_label",
            &["app", "repo", "unknown"],
            "unknown",
        ),
        runner_exists: bool_from_json(value, "runner_exists"),
        adapter_exists: bool_from_json(value, "adapter_exists"),
        fusion_brain_exists: bool_from_json(value, "fusion_brain_exists"),
        contract_exists: bool_from_json(value, "contract_exists"),
        runner_exit_code: value.get("runner_exit_code").and_then(Value::as_i64),
        stdout_json_valid: bool_from_json(value, "stdout_json_valid"),
        result_degraded: bool_from_json(value, "result_degraded"),
        public_failure_class: safe_runner_smoke_optional_string(value, "public_failure_class"),
        public_summary: safe_runner_smoke_optional_string(value, "public_summary"),
    }
}

async fn public_v1_runtime_runner_smoke(
    State(state): State<AppState>,
) -> (StatusCode, Json<PublicRunnerSmokeResponseV1>) {
    if state.mock_mode {
        return (
            StatusCode::OK,
            Json(build_runner_smoke_fallback("degraded", "mock_mode")),
        );
    }

    let body = serde_json::to_vec(&json!({
        "diagnostic": "runner_smoke",
        "message": "responda apenas OK",
        "client_session_id": "runner-smoke-public-safe",
        "request_source": "rust_runner_smoke",
        "runtime_session_version": state.runtime_session_version,
    }))
    .unwrap_or_else(|_| br#"{"diagnostic":"runner_smoke"}"#.to_vec());

    let invocation = PythonInvocation::new(
        &state.python_bin,
        vec![state.python_entry.as_os_str().to_os_string()],
    )
    .stderr_mode(StderrMode::Null)
    .stdin_payload(Some(body))
    .timeout(Some(Duration::from_secs(8)));

    let output = match run_python(invocation).await {
        Ok(output) => output,
        Err(error) => {
            let failure_class = match error {
                BridgeSpawnFailure::Spawn(_) => "python_spawn_failed",
                BridgeSpawnFailure::StdinWrite(_) => "python_stdin_failed",
                BridgeSpawnFailure::Wait(_) => "python_wait_failed",
                BridgeSpawnFailure::Timeout => "timeout",
            };
            return (
                StatusCode::OK,
                Json(build_runner_smoke_fallback("error", failure_class)),
            );
        }
    };

    if !output.success {
        return (
            StatusCode::OK,
            Json(build_runner_smoke_fallback(
                "error",
                "python_subprocess_failed",
            )),
        );
    }

    let parsed = serde_json::from_slice::<Value>(&output.stdout);
    match parsed {
        Ok(value) => (StatusCode::OK, Json(parse_runner_smoke_response(&value))),
        Err(_) => (
            StatusCode::OK,
            Json(build_runner_smoke_fallback("error", "invalid_json")),
        ),
    }
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
        .filter(|item| {
            item.get("event_type").and_then(Value::as_str) == Some("runtime.mode.transition")
        })
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
    let strategy_version = strategy_state
        .get("version")
        .and_then(Value::as_u64)
        .unwrap_or(0);
    let create_plan_weight = strategy_state
        .get("capability_weights")
        .and_then(|cw| cw.get("create_plan"))
        .and_then(Value::as_f64);
    let recent_change_log_count = read_json_value(&strategy_log_path)
        .and_then(|value| value.get("changes").and_then(Value::as_array).map(Vec::len))
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
                if kl.contains("path") && v.as_str().is_some_and(string_looks_like_filesystem_path)
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

async fn runtime_signals(
    State(state): State<AppState>,
) -> (StatusCode, Json<RuntimeSignalsResponse>) {
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
    let recent_signals = read_recent_jsonl(&audit_path, 20);
    let recent_mode_transitions = recent_signals
        .iter()
        .filter(|item| {
            item.get("event_type").and_then(Value::as_str) == Some("runtime.mode.transition")
        })
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

async fn strategy_state(
    State(state): State<AppState>,
) -> (StatusCode, Json<StrategyStateResponse>) {
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
    let engineering = checkpoint
        .get("engineering_data")
        .cloned()
        .unwrap_or_else(|| json!({}));

    (
        StatusCode::OK,
        Json(MilestonesResponse {
            status: "ok",
            latest_run_id,
            milestone_state: engineering
                .get("milestone_state")
                .cloned()
                .unwrap_or_else(|| json!({})),
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
            execution_state: checkpoint
                .get("execution_state")
                .cloned()
                .unwrap_or_else(|| json!({})),
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
    let strategy_version = strategy_state
        .get("version")
        .and_then(Value::as_u64)
        .unwrap_or(0);
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
    let engineering = checkpoint
        .get("engineering_data")
        .cloned()
        .unwrap_or_else(|| json!({}));
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
async fn operator_v1_pr_digest(
    State(state): State<AppState>,
) -> (StatusCode, Json<OperatorPrDigestV1>) {
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
#[cfg(test)]
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

fn build_public_error_payload(code: &str) -> Value {
    let (message, severity, retryable) = match code {
        "INPUT_VALIDATION_FAILED" => ("Request input failed validation.", "blocked", false),
        "PAYLOAD_TOO_LARGE" => (
            "Request payload exceeds the configured size limit.",
            "blocked",
            false,
        ),
        "RATE_LIMITED" => ("Too many requests. Please retry later.", "blocked", true),
        "INVALID_CONTENT_TYPE" => (
            "Request content type must be application/json.",
            "blocked",
            false,
        ),
        "INVALID_JSON" => ("Request body must be valid JSON.", "blocked", false),
        "PYTHON_ORCHESTRATOR_FAILED" => (
            "Python orchestrator could not complete the request.",
            "error",
            true,
        ),
        "TIMEOUT" => ("The operation timed out.", "error", true),
        "INTERNAL_ERROR_REDACTED" => (
            "An internal runtime error occurred and details were redacted.",
            "critical",
            false,
        ),
        _ => ("Request could not be processed.", "error", false),
    };
    json!({
        "error_public_code": code,
        "error_public_message": message,
        "severity": severity,
        "retryable": retryable,
        "internal_error_redacted": true,
    })
}

fn public_error_response(status: StatusCode, code: &str) -> Response {
    (status, Json(build_public_error_payload(code))).into_response()
}

type BoxedResponseResult<T> = Result<T, Box<Response>>;

fn boxed_public_error_response(status: StatusCode, code: &str) -> Box<Response> {
    Box::new(public_error_response(status, code))
}

fn validate_content_type(headers: &HeaderMap) -> BoxedResponseResult<()> {
    let Some(value) = headers.get(CONTENT_TYPE) else {
        return Err(boxed_public_error_response(
            StatusCode::UNSUPPORTED_MEDIA_TYPE,
            "INVALID_CONTENT_TYPE",
        ));
    };
    let Ok(raw) = value.to_str() else {
        return Err(boxed_public_error_response(
            StatusCode::UNSUPPORTED_MEDIA_TYPE,
            "INVALID_CONTENT_TYPE",
        ));
    };
    let mime = raw.split(';').next().unwrap_or("").trim();
    if mime.eq_ignore_ascii_case("application/json") {
        Ok(())
    } else {
        Err(boxed_public_error_response(
            StatusCode::UNSUPPORTED_MEDIA_TYPE,
            "INVALID_CONTENT_TYPE",
        ))
    }
}

fn contains_unsafe_control_chars(value: &str) -> bool {
    value
        .chars()
        .any(|ch| ch.is_control() && ch != '\t' && ch != '\n' && ch != '\r')
}

fn validate_message(message: &str, max_chars: usize) -> BoxedResponseResult<String> {
    let trimmed = message.trim().to_string();
    if trimmed.is_empty() {
        return Err(boxed_public_error_response(
            StatusCode::BAD_REQUEST,
            "INPUT_VALIDATION_FAILED",
        ));
    }
    if trimmed.chars().count() > max_chars {
        return Err(boxed_public_error_response(
            StatusCode::PAYLOAD_TOO_LARGE,
            "PAYLOAD_TOO_LARGE",
        ));
    }
    if contains_unsafe_control_chars(&trimmed) {
        return Err(boxed_public_error_response(
            StatusCode::BAD_REQUEST,
            "INPUT_VALIDATION_FAILED",
        ));
    }
    Ok(trimmed)
}

fn validate_optional_id(raw: Option<String>) -> BoxedResponseResult<Option<String>> {
    let Some(value) = raw else {
        return Ok(None);
    };
    let trimmed = value.trim().to_string();
    if trimmed.is_empty() {
        return Ok(None);
    }
    if trimmed.chars().count() > 128 || contains_unsafe_control_chars(&trimmed) {
        return Err(boxed_public_error_response(
            StatusCode::BAD_REQUEST,
            "INPUT_VALIDATION_FAILED",
        ));
    }
    if !trimmed
        .chars()
        .all(|ch| ch.is_ascii_alphanumeric() || matches!(ch, '_' | '-' | '.' | ':'))
    {
        return Err(boxed_public_error_response(
            StatusCode::BAD_REQUEST,
            "INPUT_VALIDATION_FAILED",
        ));
    }
    Ok(Some(trimmed))
}

const BYOK_ALLOWED_PROVIDERS: &[&str] = &[
    "groq",
    "openrouter",
    "openai",
    "anthropic",
    "gemini",
    "ollama",
    "lmstudio",
];
const BYOK_MAX_PROVIDER_COUNT: usize = 4;
const BYOK_MAX_API_KEY_CHARS: usize = 4096;
const BYOK_MAX_MODEL_CHARS: usize = 128;

fn normalize_provider_id(value: &str) -> Option<String> {
    let normalized = value.trim().to_ascii_lowercase();
    if normalized.is_empty() || contains_unsafe_control_chars(&normalized) {
        return None;
    }
    if BYOK_ALLOWED_PROVIDERS.contains(&normalized.as_str()) {
        Some(normalized)
    } else {
        None
    }
}

fn validate_provider_preference(raw: Option<String>) -> BoxedResponseResult<Option<String>> {
    let Some(value) = raw else {
        return Ok(None);
    };
    let trimmed = value.trim();
    if trimmed.is_empty() {
        return Ok(None);
    }
    normalize_provider_id(trimmed).map(Some).ok_or_else(|| {
        boxed_public_error_response(StatusCode::BAD_REQUEST, "INPUT_VALIDATION_FAILED")
    })
}

fn validate_optional_secret_string(
    raw: Option<String>,
    max_chars: usize,
) -> BoxedResponseResult<Option<String>> {
    let Some(value) = raw else {
        return Ok(None);
    };
    let trimmed = value.trim().to_string();
    if trimmed.is_empty() {
        return Ok(None);
    }
    if trimmed.chars().count() > max_chars || contains_unsafe_control_chars(&trimmed) {
        return Err(boxed_public_error_response(
            StatusCode::BAD_REQUEST,
            "INPUT_VALIDATION_FAILED",
        ));
    }
    Ok(Some(trimmed))
}

fn validate_session_provider_credentials(
    raw: Option<BTreeMap<String, SessionProviderCredential>>,
) -> BoxedResponseResult<Option<BTreeMap<String, SessionProviderCredential>>> {
    let Some(raw_credentials) = raw else {
        return Ok(None);
    };
    if raw_credentials.is_empty() {
        return Ok(None);
    }
    if raw_credentials.len() > BYOK_MAX_PROVIDER_COUNT {
        return Err(boxed_public_error_response(
            StatusCode::BAD_REQUEST,
            "PAYLOAD_TOO_LARGE",
        ));
    }

    let mut validated = BTreeMap::new();
    for (provider, credential) in raw_credentials {
        let Some(provider_id) = normalize_provider_id(&provider) else {
            return Err(boxed_public_error_response(
                StatusCode::BAD_REQUEST,
                "INPUT_VALIDATION_FAILED",
            ));
        };
        let api_key = validate_optional_secret_string(credential.api_key, BYOK_MAX_API_KEY_CHARS)?;
        let model = validate_optional_secret_string(credential.model, BYOK_MAX_MODEL_CHARS)?;
        if api_key.is_none() && model.is_none() {
            continue;
        }
        validated.insert(provider_id, SessionProviderCredential { api_key, model });
    }

    if validated.is_empty() {
        Ok(None)
    } else {
        Ok(Some(validated))
    }
}

/// ----- Settings API (BYOK) Handlers -----
fn python_settings_cli_path(state: &AppState) -> PathBuf {
    state
        .project_root
        .join("..")
        .join("python")
        .join("config")
        .join("provider_settings_cli.py")
}

async fn run_settings_cli(
    state: &AppState,
    args: &[&str],
    stdin_secret: Option<&str>,
) -> Result<Value, AppError> {
    let cli_path = python_settings_cli_path(state);

    let mut cli_args: Vec<std::ffi::OsString> = Vec::with_capacity(args.len() + 1);
    cli_args.push(cli_path.into_os_string());
    cli_args.extend(args.iter().map(|arg| (*arg).into()));

    let invocation = PythonInvocation::new(&state.python_bin, cli_args)
        .env(
            "OMNI_CREDENTIAL_STORE_KEY",
            env::var("OMNI_CREDENTIAL_STORE_KEY").unwrap_or_default(),
        )
        .env(
            "OMNI_PUBLIC_DEMO_MODE",
            env::var("OMNI_PUBLIC_DEMO_MODE").unwrap_or_default(),
        )
        .env("PYTHONPATH", &state.python_root)
        .stdin_mode(if stdin_secret.is_some() {
            StdinMode::Piped
        } else {
            StdinMode::Null
        })
        .stdin_payload(stdin_secret.map(|secret| secret.as_bytes().to_vec()));

    let output = run_python(invocation).await.map_err(|error| match error {
        BridgeSpawnFailure::Spawn(e) => {
            AppError::Internal(format!("failed to spawn settings CLI: {e}"))
        }
        BridgeSpawnFailure::StdinWrite(e) => {
            AppError::Internal(format!("failed to write to settings CLI stdin: {e}"))
        }
        BridgeSpawnFailure::Wait(e) => {
            AppError::Internal(format!("failed to read settings CLI output: {e}"))
        }
        // The settings CLI intentionally runs without a wait timeout; this arm
        // exists for exhaustiveness only.
        BridgeSpawnFailure::Timeout => AppError::Internal("settings CLI timed out".into()),
    })?;

    if !output.success {
        let stderr = String::from_utf8_lossy(&output.stderr);
        return Err(AppError::Internal(format!("settings CLI failed: {stderr}")));
    }

    let stdout = String::from_utf8_lossy(&output.stdout);
    serde_json::from_str(&stdout)
        .map_err(|e| AppError::Internal(format!("invalid JSON from settings CLI: {e}")))
}

fn extract_user_id(extensions: &axum::http::Extensions) -> Option<String> {
    extensions.get::<String>().cloned()
}

/// GET /api/v1/settings/providers
async fn settings_list_providers(
    State(state): State<AppState>,
    extensions: axum::http::Extensions,
) -> Result<Json<ListProvidersResponse>, AppError> {
    let user_id =
        extract_user_id(&extensions).ok_or_else(|| AppError::Internal("unauthenticated".into()))?;
    let result = run_settings_cli(&state, &["list", &user_id], None).await?;

    let providers: Vec<ProviderMetadata> = serde_json::from_value(result)
        .map_err(|e| AppError::Internal(format!("parse list providers: {e}")))?;

    Ok(Json(ListProvidersResponse {
        status: "ok".to_string(),
        providers,
    }))
}

/// POST /api/v1/settings/providers
async fn settings_save_provider(
    State(state): State<AppState>,
    extensions: axum::http::Extensions,
    Json(payload): Json<SaveProviderRequest>,
) -> Result<Json<SaveProviderResponse>, AppError> {
    let user_id =
        extract_user_id(&extensions).ok_or_else(|| AppError::Internal("unauthenticated".into()))?;

    let provider = payload.provider.trim().to_ascii_lowercase();
    if provider.is_empty() {
        return Err(AppError::Internal("provider is required".into()));
    }
    if payload.api_key.trim().is_empty() {
        return Err(AppError::Internal("api_key is required".into()));
    }

    let result = run_settings_cli(
        &state,
        &["save", &user_id, &provider],
        Some(&payload.api_key),
    )
    .await?;

    let response: SaveProviderResponse = serde_json::from_value(result)
        .map_err(|e| AppError::Internal(format!("parse save provider: {e}")))?;

    Ok(Json(response))
}

/// PUT /api/v1/settings/providers/{provider}
async fn settings_update_provider(
    State(state): State<AppState>,
    extensions: axum::http::Extensions,
    AxumPath(provider): AxumPath<String>,
    Json(payload): Json<UpdateProviderRequest>,
) -> Result<Json<UpdateProviderResponse>, AppError> {
    let user_id =
        extract_user_id(&extensions).ok_or_else(|| AppError::Internal("unauthenticated".into()))?;

    let provider = provider.trim().to_ascii_lowercase();
    if provider.is_empty() {
        return Err(AppError::Internal("provider is required".into()));
    }
    if payload.api_key.trim().is_empty() {
        return Err(AppError::Internal("api_key is required".into()));
    }

    let result = run_settings_cli(
        &state,
        &["update", &user_id, &provider],
        Some(&payload.api_key),
    )
    .await?;

    let response: UpdateProviderResponse = serde_json::from_value(result)
        .map_err(|e| AppError::Internal(format!("parse update provider: {e}")))?;

    Ok(Json(response))
}

/// DELETE /api/v1/settings/providers/{provider}
async fn settings_delete_provider(
    State(state): State<AppState>,
    extensions: axum::http::Extensions,
    AxumPath(provider): AxumPath<String>,
) -> Result<Json<DeleteProviderResponse>, AppError> {
    let user_id =
        extract_user_id(&extensions).ok_or_else(|| AppError::Internal("unauthenticated".into()))?;

    let provider = provider.trim().to_ascii_lowercase();
    if provider.is_empty() {
        return Err(AppError::Internal("provider is required".into()));
    }

    let result = run_settings_cli(&state, &["delete", &user_id, &provider], None).await?;

    let response: DeleteProviderResponse = serde_json::from_value(result)
        .map_err(|e| AppError::Internal(format!("parse delete provider: {e}")))?;

    Ok(Json(response))
}

/// POST /api/v1/settings/providers/{provider}/test
async fn settings_test_provider(
    State(state): State<AppState>,
    extensions: axum::http::Extensions,
    AxumPath(provider): AxumPath<String>,
    Json(payload): Json<TestProviderRequest>,
) -> Result<Json<TestProviderResponse>, AppError> {
    let user_id =
        extract_user_id(&extensions).ok_or_else(|| AppError::Internal("unauthenticated".into()))?;

    let provider = provider.trim().to_ascii_lowercase();
    if provider.is_empty() {
        return Err(AppError::Internal("provider is required".into()));
    }
    if payload.api_key.trim().is_empty() {
        return Err(AppError::Internal("api_key is required".into()));
    }

    let result = run_settings_cli(
        &state,
        &["test", &user_id, &provider],
        Some(&payload.api_key),
    )
    .await?;

    let response: TestProviderResponse = serde_json::from_value(result)
        .map_err(|e| AppError::Internal(format!("parse test provider: {e}")))?;

    Ok(Json(response))
}

fn build_private_bridge_context(
    client_context: Option<Value>,
    provider_preference: &Option<String>,
    credentials: &Option<BTreeMap<String, SessionProviderCredential>>,
) -> Option<Value> {
    let mut out = Map::new();
    if let Some(Value::Object(obj)) = client_context {
        out.extend(obj);
    }
    if let Some(provider) = provider_preference {
        out.insert(
            "provider_preference".to_string(),
            Value::String(provider.clone()),
        );
    }
    if let Some(credentials) = credentials {
        if let Ok(value) = serde_json::to_value(credentials) {
            out.insert("session_provider_credentials".to_string(), value);
        }
    }
    if out.is_empty() {
        None
    } else {
        Some(Value::Object(out))
    }
}

fn validate_body_size(bytes: &Bytes, max_body_bytes: usize) -> BoxedResponseResult<()> {
    if bytes.len() > max_body_bytes {
        Err(boxed_public_error_response(
            StatusCode::PAYLOAD_TOO_LARGE,
            "PAYLOAD_TOO_LARGE",
        ))
    } else {
        Ok(())
    }
}

fn validate_chat_rate_limit(
    state: &AppState,
    headers: &HeaderMap,
    peer: Option<SocketAddr>,
) -> BoxedResponseResult<()> {
    let Some(peer) = peer else {
        warn!("chat request rejected because TCP peer identity was unavailable");
        return Err(boxed_public_error_response(
            StatusCode::INTERNAL_SERVER_ERROR,
            "INTERNAL_ERROR_REDACTED",
        ));
    };
    let identity = state
        .chat_security
        .trusted_proxy
        .resolve(peer.ip(), headers);
    if identity.source == ClientIdentitySource::ForwardedHeaderRejected {
        warn!("trusted forwarding metadata was rejected; using the TCP peer identity");
    }
    if state
        .chat_security
        .check_rate_limit(identity.effective_ip, Instant::now())
    {
        Ok(())
    } else {
        Err(boxed_public_error_response(
            StatusCode::TOO_MANY_REQUESTS,
            "RATE_LIMITED",
        ))
    }
}

fn parse_chat_request(bytes: &Bytes) -> BoxedResponseResult<ChatRequest> {
    serde_json::from_slice::<ChatRequest>(bytes)
        .map_err(|_| boxed_public_error_response(StatusCode::BAD_REQUEST, "INVALID_JSON"))
}

fn parse_public_chat_request(bytes: &Bytes) -> BoxedResponseResult<PublicChatRequestV1> {
    serde_json::from_slice::<PublicChatRequestV1>(bytes)
        .map_err(|_| boxed_public_error_response(StatusCode::BAD_REQUEST, "INVALID_JSON"))
}

async fn chat(
    State(state): State<AppState>,
    peer: Option<Extension<ConnectInfo<SocketAddr>>>,
    headers: HeaderMap,
    body: Bytes,
) -> Result<Response, AppError> {
    if let Err(response) = validate_content_type(&headers) {
        return Ok(*response);
    }
    if let Err(response) = validate_body_size(&body, state.chat_security.config.max_body_bytes) {
        return Ok(*response);
    }
    if let Err(response) = validate_chat_rate_limit(
        &state,
        &headers,
        peer.map(|Extension(ConnectInfo(peer))| peer),
    ) {
        return Ok(*response);
    }
    let payload = match parse_chat_request(&body) {
        Ok(payload) => payload,
        Err(response) => return Ok(*response),
    };
    let message = match validate_message(
        &payload.message,
        state.chat_security.config.max_message_chars,
    ) {
        Ok(message) => message,
        Err(response) => return Ok(*response),
    };

    let client_session_id = match validate_optional_id(payload.client_session_id) {
        Ok(value) => value,
        Err(response) => return Ok(*response),
    };
    let request_id = match validate_optional_id(payload.request_id) {
        Ok(value) => value,
        Err(response) => return Ok(*response),
    };
    let provider_preference = match validate_provider_preference(payload.provider_preference) {
        Ok(value) => value,
        Err(response) => return Ok(*response),
    };
    let session_provider_credentials =
        match validate_session_provider_credentials(payload.session_provider_credentials) {
            Ok(value) => value,
            Err(response) => return Ok(*response),
        };
    let private_context =
        build_private_bridge_context(None, &provider_preference, &session_provider_credentials);

    info!(
        client_session_id = ?client_session_id,
        "processing /chat request with runtime session version {} and runtime_mode={}",
        state.runtime_session_version,
        state.runtime_mode
    );
    let response = call_python(
        &state,
        &message,
        client_session_id,
        request_id,
        private_context.as_ref(),
    )
    .await?;
    Ok((StatusCode::OK, Json(response)).into_response())
}

async fn public_v1_chat(
    State(state): State<AppState>,
    peer: Option<Extension<ConnectInfo<SocketAddr>>>,
    headers: HeaderMap,
    body: Bytes,
) -> Result<Response, AppError> {
    if let Err(response) = validate_content_type(&headers) {
        return Ok(*response);
    }
    if let Err(response) = validate_body_size(&body, state.chat_security.config.max_body_bytes) {
        return Ok(*response);
    }
    if let Err(response) = validate_chat_rate_limit(
        &state,
        &headers,
        peer.map(|Extension(ConnectInfo(peer))| peer),
    ) {
        return Ok(*response);
    }
    let payload = match parse_public_chat_request(&body) {
        Ok(payload) => payload,
        Err(response) => return Ok(*response),
    };
    let message = match validate_message(
        &payload.message,
        state.chat_security.config.max_message_chars,
    ) {
        Ok(message) => message,
        Err(response) => return Ok(*response),
    };

    let client_session_id = match validate_optional_id(payload.client_session_id) {
        Ok(value) => value,
        Err(response) => return Ok(*response),
    };
    let request_id = match validate_optional_id(payload.request_id) {
        Ok(value) => value,
        Err(response) => return Ok(*response),
    };
    let provider_preference = match validate_provider_preference(payload.provider_preference) {
        Ok(value) => value,
        Err(response) => return Ok(*response),
    };
    let session_provider_credentials =
        match validate_session_provider_credentials(payload.session_provider_credentials) {
            Ok(value) => value,
            Err(response) => return Ok(*response),
        };
    let client_context_json = payload
        .client_context
        .as_ref()
        .and_then(|ctx| serde_json::to_value(ctx).ok());
    let private_context = build_private_bridge_context(
        client_context_json,
        &provider_preference,
        &session_provider_credentials,
    );

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
        request_id,
        private_context.as_ref(),
    )
    .await?;

    Ok((
        StatusCode::OK,
        Json(PublicChatResponseV1 {
            api_version: "1",
            chat,
        }),
    )
        .into_response())
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

fn public_demo_mode_enabled() -> bool {
    env::var("OMNI_PUBLIC_DEMO_MODE")
        .ok()
        .map(|value| {
            matches!(
                value.trim().to_ascii_lowercase().as_str(),
                "1" | "true" | "yes" | "on"
            )
        })
        .unwrap_or(false)
}

fn python_debug_logging_enabled() -> bool {
    if public_demo_mode_enabled() {
        return false;
    }
    env::var("OMNI_LOG_LEVEL")
        .ok()
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
    if trimmed
        .chars()
        .any(|c| c == '\n' || c == '\r' || c.is_control())
    {
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
    String::new()
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
    runtime_session_id: Option<String>,
    conversation_id: Option<String>,
    cognitive_runtime_inspection: Option<Value>,
    providers: Option<Vec<String>>,
    stop_reason: Option<String>,
    error: Option<Value>,
}

fn build_bridge_error(failure_class: &str, message: &str, detail: Option<&str>) -> Value {
    let mut out = Map::new();
    out.insert(
        "failure_class".into(),
        Value::String(failure_class.trim().to_string()),
    );
    out.insert("message".into(), Value::String(message.trim().to_string()));
    if let Some(d) = detail {
        let t = d.trim();
        if !t.is_empty() {
            out.insert("detail".into(), Value::String(t.to_string()));
        }
    }
    Value::Object(out)
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
            runtime_session_id: None,
            conversation_id: None,
            cognitive_runtime_inspection: Some(json!({
                "runtime_mode": "SAFE_FALLBACK",
                "runtime_reason": "PYTHON_BRIDGE_EMPTY_STDOUT",
                "execution_tier": "technical_fallback",
                "rust_boundary": true,
                "reason": "python_stdout_empty_trimmed",
                "signals": {
                    "failure_class": "PYTHON_BRIDGE_EMPTY_STDOUT",
                    "fallback_triggered": true,
                    "execution_path_used": "rust_python_bridge",
                    "compatibility_execution_active": false,
                    "provider_actual": "",
                    "provider_failed": false,
                    "execution_provenance": serde_json::Value::Null,
                }
            })),
            providers: None,
            stop_reason: Some("python_empty_stdout".to_string()),
            error: Some(build_bridge_error(
                "PYTHON_BRIDGE_EMPTY_STDOUT",
                "Python bridge returned empty stdout.",
                None,
            )),
        };
    }

    if python_debug_logging_enabled() {
        debug!(python_stdout = %trimmed, "python subprocess stdout");
    }

    match serde_json::from_str::<Value>(trimmed) {
        Ok(json) => {
            let runtime_session_id = json
                .get("runtime_session_id")
                .and_then(Value::as_str)
                .and_then(normalize_conversation_id_from_str);
            let conversation_id = extract_conversation_id_from_python_json(&json);
            let mut response = extract_response_text_from_python_json(&json);
            let inspection = json.get("cognitive_runtime_inspection").cloned();
            let providers = extract_providers_from_python_json(&json);
            let stop_reason = extract_stop_reason_from_python_json(&json);
            let mut error = json.get("error").cloned();
            if error.is_none() {
                if let Some(code) = json.get("error_public_code").and_then(Value::as_str) {
                    let mut public_error = Map::new();
                    public_error
                        .insert("error_public_code".into(), Value::String(code.to_string()));
                    for key in [
                        "error_public_message",
                        "severity",
                        "retryable",
                        "internal_error_redacted",
                    ] {
                        if let Some(value) = json.get(key) {
                            public_error.insert(key.to_string(), value.clone());
                        }
                    }
                    error = Some(Value::Object(public_error));
                }
            }
            if response.trim().is_empty() {
                response = PYTHON_FALLBACK_RESPONSE.to_string();
                if error.is_none() {
                    error = Some(build_bridge_error(
                        "PYTHON_BRIDGE_INVALID_JSON",
                        "Python bridge returned JSON without a usable response field.",
                        Some("missing_or_empty_response"),
                    ));
                }
            }
            ParsedPythonChat {
                response,
                runtime_session_id,
                conversation_id,
                cognitive_runtime_inspection: inspection,
                providers,
                stop_reason,
                error,
            }
        }
        Err(err) => {
            warn!(error = %err, "failed to parse python output");
            let parse_detail = err.to_string();
            ParsedPythonChat {
                response: PYTHON_PARSE_FAILURE_RESPONSE.to_string(),
                runtime_session_id: None,
                conversation_id: None,
                cognitive_runtime_inspection: Some(json!({
                    "runtime_mode": "SAFE_FALLBACK",
                    "runtime_reason": "PYTHON_BRIDGE_INVALID_JSON",
                    "execution_tier": "technical_fallback",
                    "rust_boundary": true,
                    "reason": "python_stdout_json_parse_failed",
                    "parse_error": err.to_string(),
                    "signals": {
                        "failure_class": "PYTHON_BRIDGE_INVALID_JSON",
                        "fallback_triggered": true,
                        "execution_path_used": "rust_python_bridge",
                        "compatibility_execution_active": false,
                        "provider_actual": "",
                        "provider_failed": false,
                        "execution_provenance": serde_json::Value::Null,
                    }
                })),
                providers: None,
                stop_reason: Some("python_stdout_invalid_json".to_string()),
                error: Some(build_bridge_error(
                    "PYTHON_BRIDGE_INVALID_JSON",
                    "Rust could not parse Python stdout as JSON.",
                    Some(parse_detail.as_str()),
                )),
            }
        }
    }
}

/// JSON body written to Python stdin (see `docs/backend/python-bridge-contract.md`).
fn build_python_stdin_json(
    message: &str,
    client_session_id: &Option<String>,
    request_id: &Option<String>,
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
    if let Some(id) = request_id {
        m.insert("request_id".into(), Value::String(id.clone()));
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

fn build_python_service_json(
    message: &str,
    client_session_id: &Option<String>,
    request_id: &Option<String>,
    client_context: Option<&Value>,
) -> Vec<u8> {
    let mut m = serde_json::Map::new();
    m.insert("message".into(), Value::String(message.to_string()));
    if let Some(id) = client_session_id {
        m.insert("session_id".into(), Value::String(id.clone()));
    }
    if let Some(id) = request_id {
        m.insert("request_id".into(), Value::String(id.clone()));
    }
    if let Some(ctx) = client_context {
        if let Some(obj) = ctx.as_object() {
            if !obj.is_empty() {
                m.insert("metadata".into(), ctx.clone());
            }
        }
    }
    serde_json::to_vec(&Value::Object(m)).unwrap_or_else(|_| br#"{"message":""}"#.to_vec())
}

fn parse_http_response(raw: &[u8]) -> Option<(u16, String)> {
    let text = String::from_utf8_lossy(raw);
    let (head, body) = text.split_once("\r\n\r\n")?;
    let status = head
        .lines()
        .next()?
        .split_whitespace()
        .nth(1)?
        .parse::<u16>()
        .ok()?;
    Some((status, body.trim().to_string()))
}

async fn post_python_service(
    state: &AppState,
    body: Vec<u8>,
) -> Result<(u16, String), &'static str> {
    let host = state.python_runtime.service_host.as_str();
    let port = state.python_runtime.service_port;
    let service_token = read_env_string("OMNI_PYTHON_SERVICE_TOKEN", "");
    let request = format!(
        "POST /internal/brain/run HTTP/1.1\r\nHost: {host}:{port}\r\nContent-Type: application/json\r\nAuthorization: Bearer {}\r\nContent-Length: {}\r\nConnection: close\r\n\r\n",
        service_token,
        body.len(),
    );

    let mut stream = timeout(
        Duration::from_millis(state.python_runtime.service_timeout_ms),
        TcpStream::connect((host, port)),
    )
    .await
    .map_err(|_| "timeout")?
    .map_err(|_| "connect_failed")?;

    timeout(
        Duration::from_millis(state.python_runtime.service_timeout_ms),
        async {
            stream
                .write_all(request.as_bytes())
                .await
                .map_err(|_| "write_failed")?;
            stream.write_all(&body).await.map_err(|_| "write_failed")?;
            stream.flush().await.map_err(|_| "write_failed")?;
            let mut out = Vec::new();
            stream
                .read_to_end(&mut out)
                .await
                .map_err(|_| "read_failed")?;
            parse_http_response(&out).ok_or("invalid_http_response")
        },
    )
    .await
    .map_err(|_| "timeout")?
}

fn build_python_fallback_response(
    state: &AppState,
    source: &str,
    client_session_id: Option<String>,
    stop_reason: &str,
    detail: Option<&str>,
) -> ChatResponse {
    let public_detail = (!public_demo_mode_enabled()).then_some(detail).flatten();
    let mut inspection = json!({
        "runtime_mode": "SAFE_FALLBACK",
        "runtime_reason": stop_reason,
        "execution_tier": "technical_fallback",
        "rust_boundary": true,
        "source": source,
        "stop_reason": stop_reason,
        "signals": {
            "failure_class": match stop_reason {
                "python_empty_stdout" => "PYTHON_BRIDGE_EMPTY_STDOUT",
                "python_stdout_invalid_json" => "PYTHON_BRIDGE_INVALID_JSON",
                "python_subprocess_nonzero_exit" => "PYTHON_BRIDGE_NONZERO_EXIT",
                "python_subprocess_timeout" => "PYTHON_BRIDGE_NONZERO_EXIT",
                "python_service_timeout" => "TIMEOUT",
                "python_service_unavailable" | "python_service_error" => {
                    "PYTHON_ORCHESTRATOR_FAILED"
                }
                _ => "PYTHON_BRIDGE_NONZERO_EXIT",
            },
            "fallback_triggered": true,
            "execution_path_used": "rust_python_bridge",
            "compatibility_execution_active": false,
            "provider_actual": "",
            "provider_failed": false,
            "execution_provenance": serde_json::Value::Null,
        }
    });
    if let Some(d) = public_detail {
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
        error: Some(build_bridge_error(
            match stop_reason {
                "python_empty_stdout" => "PYTHON_BRIDGE_EMPTY_STDOUT",
                "python_stdout_invalid_json" => "PYTHON_BRIDGE_INVALID_JSON",
                "python_subprocess_nonzero_exit" => "PYTHON_BRIDGE_NONZERO_EXIT",
                "python_subprocess_timeout" => "PYTHON_BRIDGE_NONZERO_EXIT",
                "python_service_timeout" => "TIMEOUT",
                "python_service_unavailable" | "python_service_error" => {
                    "PYTHON_ORCHESTRATOR_FAILED"
                }
                _ => "PYTHON_BRIDGE_NONZERO_EXIT",
            },
            PYTHON_FALLBACK_RESPONSE,
            public_detail,
        )),
    }
}

fn annotate_service_metadata(
    response: &mut ChatResponse,
    fallback_triggered: bool,
    service_fallback_used: bool,
    circuit_state: CircuitBreakerState,
    error_public_code: &str,
) {
    let mut inspection = response
        .cognitive_runtime_inspection
        .take()
        .unwrap_or_else(|| json!({}));

    if let Some(obj) = inspection.as_object_mut() {
        obj.insert(
            "runtime_mode".into(),
            Value::String("SAFE_FALLBACK".to_string()),
        );
        obj.insert(
            "runtime_reason".into(),
            Value::String(error_public_code.to_string()),
        );
        obj.insert("fallback_triggered".into(), Value::Bool(fallback_triggered));
        obj.insert("service_mode_attempted".into(), Value::Bool(true));
        obj.insert(
            "service_fallback_used".into(),
            Value::Bool(service_fallback_used),
        );
        obj.insert(
            "circuit_breaker_state".into(),
            Value::String(PythonCircuitBreaker::state_label(circuit_state).to_string()),
        );
        obj.insert(
            "error_public_code".into(),
            Value::String(error_public_code.to_string()),
        );
        obj.insert("internal_error_redacted".into(), Value::Bool(true));
        let signals = obj
            .entry("signals")
            .or_insert_with(|| Value::Object(Map::new()));
        if let Some(signals_obj) = signals.as_object_mut() {
            signals_obj.insert("fallback_triggered".into(), Value::Bool(fallback_triggered));
            signals_obj.insert("service_mode_attempted".into(), Value::Bool(true));
            signals_obj.insert(
                "service_fallback_used".into(),
                Value::Bool(service_fallback_used),
            );
            signals_obj.insert(
                "circuit_breaker_state".into(),
                Value::String(PythonCircuitBreaker::state_label(circuit_state).to_string()),
            );
            signals_obj.insert(
                "failure_class".into(),
                Value::String(error_public_code.to_string()),
            );
        }
    }

    response.cognitive_runtime_inspection = Some(inspection);
}

fn service_failure_code(kind: PythonServiceFailureKind) -> &'static str {
    match kind {
        PythonServiceFailureKind::Timeout => "TIMEOUT",
        PythonServiceFailureKind::ServiceFailure => "PYTHON_ORCHESTRATOR_FAILED",
    }
}

fn service_failure_stop_reason(kind: PythonServiceFailureKind) -> &'static str {
    match kind {
        PythonServiceFailureKind::Timeout => "python_service_timeout",
        PythonServiceFailureKind::ServiceFailure => "python_service_unavailable",
    }
}

fn current_python_circuit_state(state: &AppState) -> CircuitBreakerState {
    state
        .python_circuit
        .lock()
        .map(|guard| guard.state)
        .unwrap_or(CircuitBreakerState::Closed)
}

fn record_python_service_failure(
    state: &AppState,
    _kind: PythonServiceFailureKind,
    observed_state: CircuitBreakerState,
) {
    if !state.python_runtime.circuit_breaker_enabled {
        return;
    }
    if let Ok(mut guard) = state.python_circuit.lock() {
        if guard.state == observed_state || observed_state == CircuitBreakerState::HalfOpen {
            guard.record_failure(&state.python_runtime, Instant::now());
        }
    }
}

async fn execute_python_service_with_policy(
    state: &AppState,
    body: Vec<u8>,
) -> Result<(String, CircuitBreakerState), PythonServiceFailure> {
    let attempts = state.python_runtime.retry_attempts.saturating_add(1);
    let mut last_failure = PythonServiceFailureKind::ServiceFailure;
    let mut last_state = CircuitBreakerState::Closed;

    for _ in 0..attempts {
        let circuit_state = {
            let mut guard = state
                .python_circuit
                .lock()
                .map_err(|_| PythonServiceFailure {
                    kind: PythonServiceFailureKind::ServiceFailure,
                    circuit_state: CircuitBreakerState::Open,
                })?;
            guard.before_call(&state.python_runtime, Instant::now())
        };
        last_state = circuit_state;

        if circuit_state == CircuitBreakerState::Open {
            return Err(PythonServiceFailure {
                kind: PythonServiceFailureKind::ServiceFailure,
                circuit_state,
            });
        }

        match post_python_service(state, body.clone()).await {
            Ok((status, response_body)) if (200..300).contains(&status) => {
                if serde_json::from_str::<Value>(&response_body).is_err() {
                    last_failure = PythonServiceFailureKind::ServiceFailure;
                    record_python_service_failure(state, last_failure, circuit_state);
                    continue;
                }
                if let Ok(mut guard) = state.python_circuit.lock() {
                    guard.record_success();
                }
                return Ok((response_body, circuit_state));
            }
            Ok(_) => {
                last_failure = PythonServiceFailureKind::ServiceFailure;
                record_python_service_failure(state, last_failure, circuit_state);
            }
            Err("timeout") => {
                last_failure = PythonServiceFailureKind::Timeout;
                record_python_service_failure(state, last_failure, circuit_state);
            }
            Err(_) => {
                last_failure = PythonServiceFailureKind::ServiceFailure;
                record_python_service_failure(state, last_failure, circuit_state);
            }
        }
    }

    Err(PythonServiceFailure {
        kind: last_failure,
        circuit_state: current_python_circuit_state(state).max_state(last_state),
    })
}

trait CircuitStateOrder {
    fn max_state(self, other: Self) -> Self;
}

impl CircuitStateOrder for CircuitBreakerState {
    fn max_state(self, other: Self) -> Self {
        if self == CircuitBreakerState::Open || other == CircuitBreakerState::Open {
            CircuitBreakerState::Open
        } else if self == CircuitBreakerState::HalfOpen || other == CircuitBreakerState::HalfOpen {
            CircuitBreakerState::HalfOpen
        } else {
            CircuitBreakerState::Closed
        }
    }
}

async fn call_python_service(
    state: &AppState,
    message: &str,
    client_session_id: Option<String>,
    request_id: Option<String>,
    client_context: Option<&Value>,
) -> Result<ChatResponse, AppError> {
    let body = build_python_service_json(message, &client_session_id, &request_id, client_context);
    let result = execute_python_service_with_policy(state, body).await;
    let (response_body, circuit_state) = match result {
        Ok(value) => value,
        Err(failure) => {
            let code = service_failure_code(failure.kind);
            let stop_reason = service_failure_stop_reason(failure.kind);
            update_python_health(
                state,
                if failure.kind == PythonServiceFailureKind::Timeout {
                    "timeout"
                } else {
                    "failed"
                },
                Some(code.to_string()),
            )
            .await;

            if state.python_runtime.fallback_to_subprocess {
                let mut fallback = call_python_subprocess(
                    state,
                    message,
                    client_session_id,
                    request_id,
                    client_context,
                )
                .await?;
                fallback.source = "python-service-subprocess-fallback".to_string();
                fallback.stop_reason = Some(format!("{stop_reason}_subprocess_fallback"));
                annotate_service_metadata(&mut fallback, true, true, failure.circuit_state, code);
                return Ok(fallback);
            }

            let mut fallback = build_python_fallback_response(
                state,
                "python-service",
                client_session_id,
                stop_reason,
                Some(code),
            );
            annotate_service_metadata(&mut fallback, true, false, failure.circuit_state, code);
            return Ok(fallback);
        }
    };

    let parsed = extract_chat_from_python_output(&response_body);
    if parsed.response == PYTHON_FALLBACK_RESPONSE
        || parsed.response == PYTHON_PARSE_FAILURE_RESPONSE
    {
        let kind = PythonServiceFailureKind::ServiceFailure;
        let code = service_failure_code(kind);
        let stop_reason = "python_service_error";
        update_python_health(state, "failed", Some(code.to_string())).await;
        record_python_service_failure(state, kind, circuit_state);
        let current_state = current_python_circuit_state(state);
        if state.python_runtime.fallback_to_subprocess {
            let mut fallback = call_python_subprocess(
                state,
                message,
                client_session_id,
                request_id,
                client_context,
            )
            .await?;
            fallback.source = "python-service-subprocess-fallback".to_string();
            fallback.stop_reason = Some(format!("{stop_reason}_subprocess_fallback"));
            annotate_service_metadata(&mut fallback, true, true, current_state, code);
            return Ok(fallback);
        }
        let mut fallback = build_python_fallback_response(
            state,
            "python-service",
            client_session_id,
            stop_reason,
            Some(code),
        );
        annotate_service_metadata(&mut fallback, true, false, current_state, code);
        return Ok(fallback);
    }

    let stop_reason = parsed
        .stop_reason
        .clone()
        .unwrap_or_else(|| "python_service_completed".to_string());
    update_python_health(state, "ready", None).await;

    Ok(ChatResponse {
        response: parsed.response,
        session_id: parsed
            .runtime_session_id
            .unwrap_or_else(|| "python-session".to_string()),
        source: "python-service".to_string(),
        runtime_session_version: state.runtime_session_version,
        client_session_id,
        matched_commands: Vec::new(),
        matched_tools: Vec::new(),
        stop_reason: Some(stop_reason),
        usage: None,
        conversation_id: parsed.conversation_id,
        cognitive_runtime_inspection: parsed.cognitive_runtime_inspection,
        providers: parsed.providers,
        error: parsed.error,
    })
}

async fn call_python(
    state: &AppState,
    message: &str,
    client_session_id: Option<String>,
    request_id: Option<String>,
    client_context: Option<&Value>,
) -> Result<ChatResponse, AppError> {
    if state.mock_mode {
        update_python_health(state, "mock", None).await;
        return Ok(build_mock_response(
            state,
            message,
            "mock-env",
            client_session_id,
        ));
    }

    if state.python_runtime.mode == PythonRuntimeMode::Service {
        return call_python_service(
            state,
            message,
            client_session_id,
            request_id,
            client_context,
        )
        .await;
    }

    call_python_subprocess(
        state,
        message,
        client_session_id,
        request_id,
        client_context,
    )
    .await
}

async fn call_python_subprocess(
    state: &AppState,
    message: &str,
    client_session_id: Option<String>,
    request_id: Option<String>,
    client_context: Option<&Value>,
) -> Result<ChatResponse, AppError> {
    if state.mock_mode {
        update_python_health(state, "mock", None).await;
        return Ok(build_mock_response(
            state,
            message,
            "mock-env",
            client_session_id,
        ));
    }

    let stdin_body = build_python_stdin_json(
        message,
        &client_session_id,
        &request_id,
        state.runtime_session_version,
        client_context,
    );

    let invocation = PythonInvocation::new(
        &state.python_bin,
        vec![state.python_entry.as_os_str().to_os_string()],
    )
    .stdin_payload(Some(stdin_body))
    .timeout(Some(Duration::from_millis(state.python_timeout_ms)));

    let output = match run_python(invocation).await {
        Ok(output) => output,
        Err(error) => {
            let (failure_class, message, health_state) = match &error {
                BridgeSpawnFailure::Spawn(err) => (
                    "python_subprocess_spawn_failed",
                    format!("failed to spawn python subprocess: {err}"),
                    "failed",
                ),
                BridgeSpawnFailure::StdinWrite(err) => (
                    "python_subprocess_stdin_failed",
                    format!("failed to write python stdin: {err}"),
                    "failed",
                ),
                BridgeSpawnFailure::Wait(err) => (
                    "python_subprocess_wait_failed",
                    format!("failed to await python subprocess: {err}"),
                    "failed",
                ),
                BridgeSpawnFailure::Timeout => (
                    "python_subprocess_timeout",
                    format!(
                        "python subprocess timed out after {} ms",
                        state.python_timeout_ms
                    ),
                    "timeout",
                ),
            };
            error!("{message}");
            update_python_health(state, health_state, Some(message.clone())).await;
            return Ok(build_python_fallback_response(
                state,
                "python-subprocess",
                client_session_id.clone(),
                failure_class,
                Some(message.as_str()),
            ));
        }
    };

    if !output.success {
        let code = output.exit_code.unwrap_or(-1);
        let stderr = output.stderr_lossy_trimmed();
        let message = format!("python adapter exited with status {}", code);
        warn!("{message}");
        if !stderr.is_empty() && python_debug_logging_enabled() {
            warn!("python stderr: {stderr}");
        } else if !stderr.is_empty() {
            warn!("python stderr was redacted in public demo mode");
        }
        let health_detail = if public_demo_mode_enabled() || stderr.is_empty() {
            message.clone()
        } else {
            stderr.clone()
        };
        update_python_health(state, "failed", Some(health_detail)).await;
        return Ok(build_python_fallback_response(
            state,
            "python-subprocess",
            client_session_id.clone(),
            "python_subprocess_nonzero_exit",
            Some(if stderr.is_empty() {
                message.as_str()
            } else {
                stderr.as_str()
            }),
        ));
    }

    let stderr = String::from_utf8_lossy(&output.stderr).trim().to_string();
    if !stderr.is_empty() {
        if python_debug_logging_enabled() {
            warn!("python adapter produced stderr on successful exit: {stderr}");
        } else {
            warn!("python adapter produced stderr; detail redacted in public demo mode");
        }
        let health_detail = if public_demo_mode_enabled() {
            "python adapter produced stderr".to_string()
        } else {
            stderr
        };
        update_python_health(state, "stderr_warning", Some(health_detail)).await;
    }

    let stdout = String::from_utf8_lossy(&output.stdout).trim().to_string();
    if stdout.is_empty() {
        let message = "python adapter returned empty stdout".to_string();
        warn!("{message}");
        update_python_health(state, "empty_stdout", Some(message.clone())).await;
        return Ok(build_python_fallback_response(
            state,
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
        session_id: parsed
            .runtime_session_id
            .unwrap_or_else(|| "python-session".to_string()),
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
        error: parsed.error,
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
        error: None,
    }
}

fn read_json_value(path: &Path) -> Option<Value> {
    fs::read_to_string(path)
        .ok()
        .and_then(|raw| serde_json::from_str::<Value>(&raw).ok())
}

const JSONL_TAIL_MAX_BYTES: u64 = 2 * 1024 * 1024;

fn read_recent_jsonl(path: &Path, limit: usize) -> Vec<Value> {
    if limit == 0 {
        return Vec::new();
    }

    let mut file = match fs::File::open(path) {
        Ok(file) => file,
        Err(_) => return Vec::new(),
    };
    let file_len = match file.metadata() {
        Ok(metadata) => metadata.len(),
        Err(_) => return Vec::new(),
    };
    if file_len == 0 {
        return Vec::new();
    }

    let read_len = file_len.min(JSONL_TAIL_MAX_BYTES);
    let start = file_len.saturating_sub(read_len);
    if file.seek(std::io::SeekFrom::Start(start)).is_err() {
        return Vec::new();
    }

    let mut bytes = Vec::with_capacity(read_len as usize);
    if std::io::Read::read_to_end(&mut file, &mut bytes).is_err() {
        return Vec::new();
    }

    let raw = String::from_utf8_lossy(&bytes);
    let mut lines = raw.lines();
    if start > 0 {
        let _ = lines.next();
    }

    let mut parsed: Vec<Value> = lines
        .filter_map(|line| {
            let trimmed = line.trim();
            if trimmed.is_empty() {
                None
            } else {
                serde_json::from_str::<Value>(trimmed).ok()
            }
        })
        .collect();
    if parsed.len() > limit {
        parsed.drain(0..parsed.len() - limit);
    }
    parsed
}

fn read_latest_jsonl(path: &Path) -> Option<Value> {
    read_recent_jsonl(path, 1).into_iter().next()
}

#[cfg(test)]
mod main_tests;
