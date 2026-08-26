//! Public request/response DTOs for the omni-api HTTP boundary.

use std::collections::BTreeMap;
use std::fmt;

use serde::{Deserialize, Serialize};
use serde_json::Value;

/// `POST /chat` JSON body. `message` is required; `client_session_id` is optional.
/// See `docs/backend/chat-session-contract.md`.
#[derive(Debug, Deserialize)]
pub(crate) struct ChatRequest {
    pub(crate) message: String,
    /// Opaque UI-owned conversation key for logging/correlation; echoed on [`ChatResponse`] when present.
    #[serde(default)]
    pub(crate) client_session_id: Option<String>,
    #[serde(default)]
    pub(crate) request_id: Option<String>,
    #[serde(default)]
    pub(crate) provider_preference: Option<String>,
    #[serde(default)]
    pub(crate) session_provider_credentials: Option<BTreeMap<String, SessionProviderCredential>>,
}

/// `POST /api/v1/chat` JSON body — same execution path as [`ChatRequest`] with an optional nested client context.
#[derive(Debug, Deserialize, Serialize)]
pub(crate) struct PublicChatClientContextV1 {
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub(crate) source: Option<String>,
}

#[derive(Debug, Deserialize)]
pub(crate) struct PublicChatRequestV1 {
    pub(crate) message: String,
    #[serde(default)]
    pub(crate) client_session_id: Option<String>,
    #[serde(default)]
    pub(crate) request_id: Option<String>,
    #[serde(default)]
    pub(crate) client_context: Option<PublicChatClientContextV1>,
    #[serde(default)]
    pub(crate) provider_preference: Option<String>,
    #[serde(default)]
    pub(crate) session_provider_credentials: Option<BTreeMap<String, SessionProviderCredential>>,
}

#[derive(Clone, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct SessionProviderCredential {
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub(crate) api_key: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub(crate) model: Option<String>,
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
pub(crate) struct PublicChatResponseV1 {
    pub(crate) api_version: &'static str,
    #[serde(flatten)]
    pub(crate) chat: ChatResponse,
}

/// `POST /chat` JSON response. `session_id` is the orchestrator runtime session id when Python emits one.
/// `runtime_session_version` is the Rust runtime epoch, not a user session. See `docs/backend/chat-session-contract.md`.
#[derive(Debug, Serialize, Deserialize)]
pub(crate) struct ChatResponse {
    pub(crate) response: String,
    /// Runtime session key from Python, or a compatibility placeholder when unavailable.
    pub(crate) session_id: String,
    pub(crate) source: String,
    /// Rust runtime session epoch; aligns chat envelope with `/health` and `GET /api/v1/status` (additive field).
    #[serde(default)]
    pub(crate) runtime_session_version: u32,
    /// Echo of request `client_session_id` when the client sent one; omitted otherwise.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub(crate) client_session_id: Option<String>,
    #[serde(default)]
    pub(crate) matched_commands: Vec<String>,
    #[serde(default)]
    pub(crate) matched_tools: Vec<String>,
    #[serde(default)]
    pub(crate) stop_reason: Option<String>,
    #[serde(default)]
    pub(crate) usage: Option<serde_json::Value>,
    /// Server-issued or orchestrator-backed conversation id when truthfully available on the Python path; omitted otherwise.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub(crate) conversation_id: Option<String>,
    /// Conservative per-turn classification of cognitive vs degraded execution (Python `main.py` only).
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub(crate) cognitive_runtime_inspection: Option<Value>,
    /// Logical LLM provider ids with validated env keys (Python `main.py`); never secret values.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub(crate) providers: Option<Vec<String>>,
    /// Structured bridge/runtime failure when available. Additive and backward-compatible.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub(crate) error: Option<Value>,
}

#[derive(Debug, Default, Clone, Serialize)]
pub(crate) struct DependencyStatus {
    pub(crate) observable: bool,
    pub(crate) last_status: String,
    #[serde(default)]
    pub(crate) last_error: Option<String>,
    #[serde(default)]
    pub(crate) last_checked_ms: Option<u64>,
}

#[derive(Debug, Serialize)]
pub(crate) struct DependencyHealth {
    pub(crate) configured_bin: String,
    pub(crate) entry: String,
    pub(crate) entry_exists: bool,
    pub(crate) observable: bool,
    pub(crate) last_status: String,
    #[serde(default)]
    pub(crate) last_error: Option<String>,
    #[serde(default)]
    pub(crate) last_checked_ms: Option<u64>,
}

#[derive(Debug, Serialize)]
pub(crate) struct HealthResponse {
    pub(crate) status: String,
    pub(crate) rust_service: &'static str,
    pub(crate) runtime_mode: String,
    pub(crate) observability_stream_ticket_store_mode: &'static str,
    pub(crate) runtime_session_version: u32,
    pub(crate) timestamp_ms: u64,
    pub(crate) python: DependencyHealth,
    pub(crate) node: DependencyHealth,
}

/// Stable public read model for product UIs (`GET /api/v1/status`). Intentionally omits file paths and binary locations.
#[derive(Debug, Serialize)]
pub(crate) struct PublicStatusResponseV1 {
    pub(crate) api_version: &'static str,
    pub(crate) status: String,
    pub(crate) runtime_mode: String,
    pub(crate) rust_service: String,
    pub(crate) python_status: String,
    pub(crate) node_status: String,
    pub(crate) runtime_session_version: u32,
    pub(crate) timestamp_ms: u64,
}

#[derive(Debug, Serialize)]
pub(crate) struct PublicRunnerSmokeResponseV1 {
    pub(crate) api_version: &'static str,
    pub(crate) status: String,
    pub(crate) selected_runtime: String,
    pub(crate) cwd_label: String,
    pub(crate) runner_exists: bool,
    pub(crate) adapter_exists: bool,
    pub(crate) fusion_brain_exists: bool,
    pub(crate) contract_exists: bool,
    pub(crate) runner_exit_code: Option<i64>,
    pub(crate) stdout_json_valid: bool,
    pub(crate) result_degraded: bool,
    pub(crate) public_failure_class: Option<String>,
    pub(crate) public_summary: Option<String>,
}

#[derive(Debug, Serialize)]
pub(crate) struct RuntimeSignalsResponse {
    pub(crate) status: &'static str,
    pub(crate) recent_signals: Vec<Value>,
    pub(crate) recent_mode_transitions: Vec<Value>,
    pub(crate) latest_run_summary: Value,
}

#[derive(Debug, Serialize)]
pub(crate) struct SwarmLogResponse {
    pub(crate) status: &'static str,
    pub(crate) events: Vec<Value>,
    pub(crate) total_events: usize,
}

#[derive(Debug, Serialize)]
pub(crate) struct StrategyStateResponse {
    pub(crate) status: &'static str,
    pub(crate) strategy_state: Value,
    pub(crate) recent_changes: Vec<Value>,
}

#[derive(Debug, Serialize)]
pub(crate) struct MilestonesResponse {
    pub(crate) status: &'static str,
    pub(crate) latest_run_id: Option<String>,
    pub(crate) milestone_state: Value,
    pub(crate) patch_sets: Vec<Value>,
    pub(crate) checkpoint_status: Value,
    pub(crate) execution_state: Value,
}

#[derive(Debug, Serialize)]
pub(crate) struct PrSummariesResponse {
    pub(crate) status: &'static str,
    pub(crate) summaries: Vec<Value>,
}

/// ----- Settings API (BYOK) -----
#[derive(Debug, Default, Serialize, Deserialize)]
pub(crate) struct ProviderHealthSignals {
    #[serde(default)]
    pub(crate) executable: bool,
    #[serde(default)]
    pub(crate) available: bool,
    #[serde(default)]
    pub(crate) reachable: Option<bool>,
    #[serde(default)]
    pub(crate) healthy: Option<bool>,
    #[serde(default)]
    pub(crate) health_valid: bool,
    #[serde(default)]
    pub(crate) last_checked_at: Option<u64>,
    #[serde(default)]
    pub(crate) valid_until: Option<u64>,
    #[serde(default)]
    pub(crate) latency_ms: Option<u64>,
    #[serde(default)]
    pub(crate) cache_status: String,
    #[serde(default)]
    pub(crate) circuit_state: String,
    #[serde(default)]
    pub(crate) consecutive_failures: u32,
    #[serde(default)]
    pub(crate) next_probe_at: Option<u64>,
}

/// Provider metadata — never contains secrets.
#[derive(Debug, Serialize, Deserialize)]
pub(crate) struct ProviderMetadata {
    pub(crate) provider: String,
    pub(crate) configured: bool,
    pub(crate) updated_at: Option<f64>,
    #[serde(flatten)]
    pub(crate) health: ProviderHealthSignals,
}

/// GET /api/v1/settings/providers
#[derive(Debug, Serialize, Deserialize)]
pub(crate) struct ListProvidersResponse {
    pub(crate) status: String,
    pub(crate) providers: Vec<ProviderMetadata>,
}

/// POST /api/v1/settings/providers
#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct SaveProviderRequest {
    pub(crate) provider: String,
    pub(crate) api_key: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub(crate) struct SaveProviderResponse {
    pub(crate) status: String,
    pub(crate) provider: String,
    pub(crate) configured: bool,
    #[serde(default)]
    pub(crate) updated_at: Option<f64>,
    #[serde(flatten)]
    pub(crate) health: ProviderHealthSignals,
}

/// PUT /api/v1/settings/providers/{provider}
#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct UpdateProviderRequest {
    pub(crate) api_key: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub(crate) struct UpdateProviderResponse {
    pub(crate) status: String,
    pub(crate) provider: String,
    pub(crate) configured: bool,
    #[serde(default)]
    pub(crate) updated_at: Option<f64>,
    #[serde(flatten)]
    pub(crate) health: ProviderHealthSignals,
}

/// DELETE /api/v1/settings/providers/{provider}
#[derive(Debug, Serialize, Deserialize)]
pub(crate) struct DeleteProviderResponse {
    pub(crate) status: String,
    pub(crate) provider: String,
    pub(crate) configured: bool,
    pub(crate) updated_at: Option<f64>,
    #[serde(flatten)]
    pub(crate) health: ProviderHealthSignals,
}

/// POST /api/v1/settings/providers/{provider}/test
#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct TestProviderRequest {
    pub(crate) api_key: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub(crate) struct TestProviderResponse {
    pub(crate) provider: String,
    pub(crate) success: bool,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub(crate) error: Option<String>,
    #[serde(default)]
    pub(crate) cached: bool,
    #[serde(flatten)]
    pub(crate) health: ProviderHealthSignals,
}

/// Authenticated operator read model — redacted runtime audit + run summary (see `docs/backend/operator-telemetry-api.md`).
#[derive(Debug, Serialize)]
pub(crate) struct OperatorRuntimeSignalsV1 {
    pub(crate) api_version: &'static str,
    pub(crate) status: &'static str,
    pub(crate) timestamp_ms: u64,
    pub(crate) recent_signal_sample_size: usize,
    pub(crate) recent_signals: Vec<Value>,
    pub(crate) recent_mode_transitions: Vec<Value>,
    pub(crate) latest_run_summary: Value,
}

/// Authenticated operator — recent strategy log entries only (no full `strategy_state` blob).
#[derive(Debug, Serialize)]
pub(crate) struct OperatorStrategyChangesV1 {
    pub(crate) api_version: &'static str,
    pub(crate) status: &'static str,
    pub(crate) timestamp_ms: u64,
    pub(crate) strategy_version: u64,
    pub(crate) recent_changes: Vec<Value>,
}

/// Authenticated operator — milestone checkpoint slice with bounded `patch_sets` and redacted nested JSON.
#[derive(Debug, Serialize)]
pub(crate) struct OperatorMilestonesV1 {
    pub(crate) api_version: &'static str,
    pub(crate) status: &'static str,
    pub(crate) timestamp_ms: u64,
    pub(crate) latest_run_id: Option<String>,
    pub(crate) checkpoint_status: Value,
    pub(crate) milestone_state: Value,
    pub(crate) patch_sets: Vec<Value>,
    pub(crate) patch_sets_total: usize,
    pub(crate) patch_sets_returned: usize,
    pub(crate) execution_state: Value,
}

/// Authenticated operator — bounded, redacted tail of `swarm_log.json` events.
#[derive(Debug, Serialize)]
pub(crate) struct OperatorSwarmV1 {
    pub(crate) api_version: &'static str,
    pub(crate) status: &'static str,
    pub(crate) timestamp_ms: u64,
    /// Events in this response after redaction (≤ tail cap).
    pub(crate) events_returned: usize,
    /// Total events in the backing log before tailing.
    pub(crate) total_events: usize,
    pub(crate) events: Vec<Value>,
}

/// Authenticated operator — PR / merge digest rows from `run-summaries.jsonl` (same projection as `/internal/pr-summaries`, redacted).
#[derive(Debug, Serialize)]
pub(crate) struct OperatorPrDigestV1 {
    pub(crate) api_version: &'static str,
    pub(crate) status: &'static str,
    pub(crate) timestamp_ms: u64,
    pub(crate) summaries_returned: usize,
    pub(crate) summaries: Vec<Value>,
}

/// Public summary of runtime signals — counts and latest run labels only (no raw audit lines).
#[derive(Debug, Serialize)]
pub(crate) struct PublicRuntimeSignalsSummaryV1 {
    pub(crate) api_version: &'static str,
    pub(crate) status: &'static str,
    /// Max JSONL lines read from the audit file for this summary (bounded read).
    pub(crate) recent_signal_sample_size: usize,
    pub(crate) recent_signal_count: usize,
    pub(crate) recent_mode_transition_count: usize,
    pub(crate) latest_run_id: String,
    pub(crate) latest_plan_kind: String,
    pub(crate) latest_run_message_preview: String,
    pub(crate) timestamp_ms: u64,
}

/// Public milestone checkpoint summary — counts and status label only.
#[derive(Debug, Serialize)]
pub(crate) struct PublicMilestonesSummaryV1 {
    pub(crate) api_version: &'static str,
    pub(crate) status: &'static str,
    pub(crate) latest_run_id: String,
    pub(crate) completed_milestone_count: u32,
    pub(crate) blocked_milestone_count: u32,
    pub(crate) patch_set_count: usize,
    pub(crate) checkpoint_status: String,
    pub(crate) timestamp_ms: u64,
}

/// Public strategy file summary — version, one safe weight, change log size only.
#[derive(Debug, Serialize)]
pub(crate) struct PublicStrategySummaryV1 {
    pub(crate) api_version: &'static str,
    pub(crate) status: &'static str,
    pub(crate) strategy_version: u64,
    /// Entries in `strategy_log.json` `changes` array (capped for bounded JSON).
    pub(crate) recent_change_log_count: usize,
    pub(crate) create_plan_weight: Option<f64>,
    pub(crate) timestamp_ms: u64,
}

