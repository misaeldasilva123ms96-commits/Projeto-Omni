#![allow(dead_code)]

use std::{
    collections::{HashMap, HashSet, VecDeque},
    sync::{Arc, Mutex},
    time::{Duration, Instant, SystemTime, UNIX_EPOCH},
};

use axum::{
    extract::{Extension, Path, Query},
    http::StatusCode,
    middleware::from_fn_with_state,
    response::IntoResponse,
    routing::get,
    Json, Router,
};
use serde::Serialize;
use serde_json::{json, Value};

use crate::{observability_auth::require_supabase_auth, AppState};

pub(crate) const HISTORICAL_AUDIT_READONLY_CAPABILITY: &str = "historical_audit:read";
pub(crate) const HISTORICAL_AUDIT_LIST_PATH: &str = "/protected/internal/audit/dry-run";
pub(crate) const HISTORICAL_AUDIT_DETAIL_PATH: &str = "/protected/internal/audit/dry-run/{plan_id}";

const DEFAULT_MAX_QUERY_PARAMS: usize = 24;
const DEFAULT_MAX_PARAM_LENGTH: usize = 160;
const DEFAULT_MAX_PLAN_ID_LENGTH: usize = 128;
const DEFAULT_MAX_FILTERS: usize = 8;
const DEFAULT_MAX_PAGE_SIZE: usize = 100;
const DEFAULT_RATE_LIMIT_MAX_REQUESTS: usize = 30;
const DEFAULT_RATE_LIMIT_WINDOW_SECONDS: u64 = 60;

const ALLOWED_FILTERS: &[&str] = &[
    "plan_type",
    "event_type",
    "source_decision",
    "risk_level",
    "blocked",
    "recorded",
    "degraded",
    "storage_mode",
    "sqlite_enabled",
    "request_id",
    "trace_id",
    "session_id",
    "created_at_from",
    "created_at_to",
    "recorded_at_from",
    "recorded_at_to",
];
const CONTROL_QUERY_PARAMS: &[&str] = &["limit", "offset", "sort_by", "sort_direction"];
const ALLOWED_SORT_FIELDS: &[&str] = &[
    "created_at",
    "recorded_at",
    "risk_level",
    "source_decision",
    "plan_type",
    "event_type",
];
const ALLOWED_SORT_DIRECTIONS: &[&str] = &["asc", "desc"];
const REQUIRED_WARNINGS: &[&str] = &[
    "Query results are readonly audit metadata.",
    "Query results are not approval.",
    "Query results are not execution input.",
    "would_retry/would_replan are not execution.",
    "Eligibility scores are not permission.",
    "Suggested strategies are not instructions.",
    "Copy/export remains disabled.",
    "Omni remains advisory-only.",
];
const FORBIDDEN_OUTPUT_MARKERS: &[&str] = &[
    "authorization",
    "bearer ",
    "cookie",
    "secret",
    "password",
    "token",
    "api_key",
    "apikey",
    "jwt",
    "raw_jsonl",
    "jsonl",
    "raw_sqlite",
    "sqlite",
    "raw_sql",
    "select ",
    "insert ",
    "update ",
    "delete ",
    "raw_prompt",
    "prompt",
    "provider_payload",
    "provider_response",
    "tool_output",
    "stdout",
    "stderr",
    "traceback",
    "stack",
    "command_args",
    "file_contents",
    ".env",
    "raw_exception",
    "raw_repr",
];

#[derive(Debug, Clone)]
pub(crate) struct HistoricalAuditRouteConfig {
    route_enabled: bool,
    authorized_callers: HashSet<String>,
    max_query_params: usize,
    max_param_length: usize,
    max_plan_id_length: usize,
    max_filters: usize,
    max_page_size: usize,
    rate_limit_max_requests: usize,
    rate_limit_window_seconds: u64,
}

impl Default for HistoricalAuditRouteConfig {
    fn default() -> Self {
        Self {
            route_enabled: false,
            authorized_callers: HashSet::new(),
            max_query_params: DEFAULT_MAX_QUERY_PARAMS,
            max_param_length: DEFAULT_MAX_PARAM_LENGTH,
            max_plan_id_length: DEFAULT_MAX_PLAN_ID_LENGTH,
            max_filters: DEFAULT_MAX_FILTERS,
            max_page_size: DEFAULT_MAX_PAGE_SIZE,
            rate_limit_max_requests: DEFAULT_RATE_LIMIT_MAX_REQUESTS,
            rate_limit_window_seconds: DEFAULT_RATE_LIMIT_WINDOW_SECONDS,
        }
    }
}

#[cfg(test)]
impl HistoricalAuditRouteConfig {
    fn enabled_for_test_callers(callers: &[&str]) -> Self {
        Self {
            route_enabled: true,
            authorized_callers: callers.iter().map(|caller| (*caller).to_string()).collect(),
            ..Self::default()
        }
    }

    fn with_max_page_size(mut self, max_page_size: usize) -> Self {
        self.max_page_size = max_page_size;
        self
    }

    fn with_rate_limit(mut self, max_requests: usize, window_seconds: u64) -> Self {
        self.rate_limit_max_requests = max_requests;
        self.rate_limit_window_seconds = window_seconds;
        self
    }
}

#[derive(Debug)]
struct HistoricalAuditRouteState {
    config: HistoricalAuditRouteConfig,
    rate_limiter: Mutex<HashMap<String, VecDeque<Instant>>>,
}

impl HistoricalAuditRouteState {
    fn new(config: HistoricalAuditRouteConfig) -> Self {
        Self {
            config,
            rate_limiter: Mutex::new(HashMap::new()),
        }
    }

    fn authorize(&self, caller_id: &str) -> GuardDecision {
        if !self.config.route_enabled {
            return GuardDecision::deny(StatusCode::NOT_FOUND, "route_disabled");
        }
        if !is_safe_id(caller_id, 128) {
            return GuardDecision::deny(StatusCode::UNAUTHORIZED, "missing_caller_identity");
        }
        if !self.config.authorized_callers.contains(caller_id) {
            return GuardDecision::deny(
                StatusCode::FORBIDDEN,
                "missing_historical_audit_readonly_capability",
            );
        }
        GuardDecision::allow("historical_audit_readonly_authorized")
    }

    fn check_rate_limit(&self, caller_id: &str, now: Instant) -> GuardDecision {
        let limit = self.config.rate_limit_max_requests.max(1);
        let window = Duration::from_secs(self.config.rate_limit_window_seconds.max(1));
        let mut limiter = self
            .rate_limiter
            .lock()
            .unwrap_or_else(|poisoned| poisoned.into_inner());
        let hits = limiter.entry(caller_id.to_string()).or_default();
        while hits
            .front()
            .map(|hit| now.duration_since(*hit) >= window)
            .unwrap_or(false)
        {
            hits.pop_front();
        }
        if hits.len() >= limit {
            return GuardDecision::deny(StatusCode::TOO_MANY_REQUESTS, "rate_limited");
        }
        hits.push_back(now);
        GuardDecision::allow("rate_limit_accepted")
    }
}

#[derive(Debug, Clone)]
struct GuardDecision {
    allowed: bool,
    status: StatusCode,
    reason: &'static str,
}

impl GuardDecision {
    fn allow(reason: &'static str) -> Self {
        Self {
            allowed: true,
            status: StatusCode::OK,
            reason,
        }
    }

    fn deny(status: StatusCode, reason: &'static str) -> Self {
        Self {
            allowed: false,
            status,
            reason,
        }
    }
}

struct EnvelopeContext {
    operation_name: &'static str,
    caller_id: String,
    decision: GuardDecision,
    degraded: bool,
    query_keys: Vec<String>,
    page_size: Option<usize>,
    data: Value,
}

#[derive(Debug, Serialize)]
struct SafeRouteEnvelope {
    status: &'static str,
    degraded: bool,
    error_category: &'static str,
    warnings: Vec<&'static str>,
    route: SafeRouteMetadata,
    audit: SafeAuditMetadata,
    observability: SafeObservabilityMetadata,
    data: Value,
    generated_at_ms: u64,
}

#[derive(Debug, Serialize)]
struct SafeRouteMetadata {
    route_id: &'static str,
    operation_name: &'static str,
    capability_required: &'static str,
    production_wired: bool,
    service_delegation: &'static str,
}

#[derive(Debug, Serialize)]
struct SafeAuditMetadata {
    event_type: &'static str,
    caller_id: String,
    caller_source: &'static str,
    decision_allowed: bool,
    decision_reason: &'static str,
    query_keys: Vec<String>,
    page_size: Option<usize>,
}

#[derive(Debug, Serialize)]
struct SafeObservabilityMetadata {
    route_id: &'static str,
    operation_name: &'static str,
    decision_allowed: bool,
    decision_reason: &'static str,
    status_code: u16,
    route_enabled: bool,
    rate_limit_max_requests: usize,
    rate_limit_window_seconds: u64,
}

pub(crate) fn protected_historical_audit_router(
    state: AppState,
    config: HistoricalAuditRouteConfig,
) -> Router<AppState> {
    let route_state = Arc::new(HistoricalAuditRouteState::new(config));
    Router::new()
        .route(HISTORICAL_AUDIT_LIST_PATH, get(list_dry_run_audit))
        .route(HISTORICAL_AUDIT_DETAIL_PATH, get(get_dry_run_audit_detail))
        .layer(Extension(route_state))
        .route_layer(from_fn_with_state(state, require_supabase_auth))
}

async fn list_dry_run_audit(
    Extension(route_state): Extension<Arc<HistoricalAuditRouteState>>,
    caller: Option<Extension<String>>,
    Query(query): Query<HashMap<String, String>>,
) -> impl IntoResponse {
    let caller_id = caller.map(|Extension(value)| value).unwrap_or_default();
    if caller_id.is_empty() {
        return denied_envelope(
            &route_state,
            "list_historical_dry_run_audit",
            "",
            GuardDecision::deny(StatusCode::UNAUTHORIZED, "missing_caller_identity"),
            query_keys(&query),
            page_size(&query),
        );
    }

    let authz = route_state.authorize(&caller_id);
    if !authz.allowed {
        return denied_envelope(
            &route_state,
            "list_historical_dry_run_audit",
            &caller_id,
            authz,
            query_keys(&query),
            page_size(&query),
        );
    }

    let rate = route_state.check_rate_limit(&caller_id, Instant::now());
    if !rate.allowed {
        return denied_envelope(
            &route_state,
            "list_historical_dry_run_audit",
            &caller_id,
            rate,
            query_keys(&query),
            page_size(&query),
        );
    }

    let complexity = validate_list_query(&route_state.config, &query);
    if !complexity.allowed {
        return denied_envelope(
            &route_state,
            "list_historical_dry_run_audit",
            &caller_id,
            complexity,
            query_keys(&query),
            page_size(&query),
        );
    }

    placeholder_envelope(
        &route_state,
        "list_historical_dry_run_audit",
        &caller_id,
        query_keys(&query),
        page_size(&query),
    )
}

async fn get_dry_run_audit_detail(
    Extension(route_state): Extension<Arc<HistoricalAuditRouteState>>,
    caller: Option<Extension<String>>,
    Path(plan_id): Path<String>,
) -> impl IntoResponse {
    let caller_id = caller.map(|Extension(value)| value).unwrap_or_default();
    if caller_id.is_empty() {
        return denied_envelope(
            &route_state,
            "get_historical_dry_run_audit_detail",
            "",
            GuardDecision::deny(StatusCode::UNAUTHORIZED, "missing_caller_identity"),
            vec!["plan_id".to_string()],
            None,
        );
    }

    let authz = route_state.authorize(&caller_id);
    if !authz.allowed {
        return denied_envelope(
            &route_state,
            "get_historical_dry_run_audit_detail",
            &caller_id,
            authz,
            vec!["plan_id".to_string()],
            None,
        );
    }

    let rate = route_state.check_rate_limit(&caller_id, Instant::now());
    if !rate.allowed {
        return denied_envelope(
            &route_state,
            "get_historical_dry_run_audit_detail",
            &caller_id,
            rate,
            vec!["plan_id".to_string()],
            None,
        );
    }

    let complexity = validate_plan_id(&route_state.config, &plan_id);
    if !complexity.allowed {
        return denied_envelope(
            &route_state,
            "get_historical_dry_run_audit_detail",
            &caller_id,
            complexity,
            vec!["plan_id".to_string()],
            None,
        );
    }

    placeholder_envelope(
        &route_state,
        "get_historical_dry_run_audit_detail",
        &caller_id,
        vec!["plan_id".to_string()],
        None,
    )
}

fn validate_list_query(
    config: &HistoricalAuditRouteConfig,
    query: &HashMap<String, String>,
) -> GuardDecision {
    if query.len() > config.max_query_params {
        return GuardDecision::deny(StatusCode::BAD_REQUEST, "too_many_query_params");
    }

    let mut filter_count = 0;
    for (key, value) in query {
        let key_allowed = CONTROL_QUERY_PARAMS.contains(&key.as_str());
        let filter_allowed = ALLOWED_FILTERS.contains(&key.as_str());
        if !key_allowed && !filter_allowed {
            return GuardDecision::deny(StatusCode::BAD_REQUEST, "unsupported_query_param");
        }
        if value.len() > config.max_param_length {
            return GuardDecision::deny(StatusCode::BAD_REQUEST, "query_param_too_large");
        }
        if filter_allowed {
            filter_count += 1;
        }
    }

    if filter_count > config.max_filters {
        return GuardDecision::deny(StatusCode::BAD_REQUEST, "too_many_filters");
    }
    if let Some(sort_by) = query.get("sort_by") {
        if !ALLOWED_SORT_FIELDS.contains(&sort_by.as_str()) {
            return GuardDecision::deny(StatusCode::BAD_REQUEST, "unsupported_sort_field");
        }
    }
    if let Some(sort_direction) = query.get("sort_direction") {
        if !ALLOWED_SORT_DIRECTIONS.contains(&sort_direction.as_str()) {
            return GuardDecision::deny(StatusCode::BAD_REQUEST, "unsupported_sort_direction");
        }
    }
    if let Some(limit) = query.get("limit") {
        if parse_bounded_usize(limit, 1, config.max_page_size).is_none() {
            return GuardDecision::deny(StatusCode::BAD_REQUEST, "limit_out_of_bounds");
        }
    }
    if let Some(offset) = query.get("offset") {
        if parse_bounded_usize(offset, 0, 10_000).is_none() {
            return GuardDecision::deny(StatusCode::BAD_REQUEST, "offset_out_of_bounds");
        }
    }

    GuardDecision::allow("query_complexity_accepted")
}

fn validate_plan_id(config: &HistoricalAuditRouteConfig, plan_id: &str) -> GuardDecision {
    if !is_safe_id(plan_id, config.max_plan_id_length) {
        return GuardDecision::deny(StatusCode::BAD_REQUEST, "invalid_plan_id");
    }
    GuardDecision::allow("detail_query_complexity_accepted")
}

fn denied_envelope(
    state: &HistoricalAuditRouteState,
    operation_name: &'static str,
    caller_id: &str,
    decision: GuardDecision,
    query_keys: Vec<String>,
    page_size: Option<usize>,
) -> (StatusCode, Json<SafeRouteEnvelope>) {
    let status = decision.status;
    (
        status,
        Json(build_envelope(
            state,
            EnvelopeContext {
                operation_name,
                caller_id: caller_id.to_string(),
                decision,
                degraded: true,
                query_keys,
                page_size,
                data: json!({}),
            },
        )),
    )
}

fn placeholder_envelope(
    state: &HistoricalAuditRouteState,
    operation_name: &'static str,
    caller_id: &str,
    query_keys: Vec<String>,
    page_size: Option<usize>,
) -> (StatusCode, Json<SafeRouteEnvelope>) {
    let decision = GuardDecision::deny(
        StatusCode::NOT_IMPLEMENTED,
        "service_delegation_unavailable",
    );
    (
        StatusCode::NOT_IMPLEMENTED,
        Json(build_envelope(
            state,
            EnvelopeContext {
                operation_name,
                caller_id: caller_id.to_string(),
                decision,
                degraded: true,
                query_keys,
                page_size,
                data: json!({
                    "items": [],
                    "detail": null,
                    "delegation_boundary": "HistoricalDryRunAuditQueryService",
                    "storage_accessed": false,
                    "runtime_invoked": false,
                    "copy_export_enabled": false
                }),
            },
        )),
    )
}

fn build_envelope(
    state: &HistoricalAuditRouteState,
    context: EnvelopeContext,
) -> SafeRouteEnvelope {
    let safe_caller_id = safe_string(&context.caller_id, 128);
    let safe_query_keys = context
        .query_keys
        .into_iter()
        .filter_map(|key| {
            let safe = safe_string(&key, 64);
            if safe.is_empty() {
                None
            } else {
                Some(safe)
            }
        })
        .collect::<Vec<_>>();
    SafeRouteEnvelope {
        status: if context.decision.allowed {
            "ok"
        } else {
            "blocked"
        },
        degraded: context.degraded,
        error_category: context.decision.reason,
        warnings: REQUIRED_WARNINGS.to_vec(),
        route: SafeRouteMetadata {
            route_id: "historical_dry_run_audit",
            operation_name: context.operation_name,
            capability_required: HISTORICAL_AUDIT_READONLY_CAPABILITY,
            production_wired: false,
            service_delegation: "HistoricalDryRunAuditQueryService",
        },
        audit: SafeAuditMetadata {
            event_type: "historical_dry_run_audit_route_access",
            caller_id: safe_caller_id,
            caller_source: "supabase_sub",
            decision_allowed: context.decision.allowed,
            decision_reason: context.decision.reason,
            query_keys: safe_query_keys,
            page_size: context.page_size,
        },
        observability: SafeObservabilityMetadata {
            route_id: "historical_dry_run_audit",
            operation_name: context.operation_name,
            decision_allowed: context.decision.allowed,
            decision_reason: context.decision.reason,
            status_code: context.decision.status.as_u16(),
            route_enabled: state.config.route_enabled,
            rate_limit_max_requests: state.config.rate_limit_max_requests,
            rate_limit_window_seconds: state.config.rate_limit_window_seconds,
        },
        data: context.data,
        generated_at_ms: now_ms(),
    }
}

fn query_keys(query: &HashMap<String, String>) -> Vec<String> {
    let mut keys = query.keys().cloned().collect::<Vec<_>>();
    keys.sort();
    keys
}

fn page_size(query: &HashMap<String, String>) -> Option<usize> {
    query
        .get("limit")
        .and_then(|value| parse_bounded_usize(value, 1, DEFAULT_MAX_PAGE_SIZE))
}

fn parse_bounded_usize(value: &str, min: usize, max: usize) -> Option<usize> {
    let parsed = value.parse::<usize>().ok()?;
    if (min..=max).contains(&parsed) {
        Some(parsed)
    } else {
        None
    }
}

fn is_safe_id(value: &str, max_length: usize) -> bool {
    if value.is_empty() || value.len() > max_length {
        return false;
    }
    let lowered = value.to_ascii_lowercase();
    if FORBIDDEN_OUTPUT_MARKERS
        .iter()
        .any(|marker| lowered.contains(marker))
    {
        return false;
    }
    value
        .chars()
        .all(|ch| ch.is_ascii_alphanumeric() || matches!(ch, '_' | '-' | '.' | ':' | '+'))
}

fn safe_string(value: &str, max_length: usize) -> String {
    let normalized = value.replace(['\0', '\r', '\n'], " ").trim().to_string();
    let lowered = normalized.to_ascii_lowercase();
    if FORBIDDEN_OUTPUT_MARKERS
        .iter()
        .any(|marker| lowered.contains(marker))
    {
        return String::new();
    }
    normalized
        .chars()
        .filter(|ch| ch.is_ascii_alphanumeric() || matches!(ch, '_' | '-' | '.' | ':' | '/' | '+'))
        .take(max_length)
        .collect()
}

fn now_ms() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|duration| duration.as_millis() as u64)
        .unwrap_or(0)
}

#[cfg(test)]
mod tests {
    use super::*;
    use axum::{
        body::{to_bytes, Body},
        http::{header::AUTHORIZATION, Method, Request},
    };
    use jsonwebtoken::{encode, Algorithm, EncodingKey, Header};
    use serde_json::Value;
    use tower::ServiceExt;

    use crate::{
        default_chat_security_state,
        observability_auth::{ProcessLocalObservabilityStreamTicketStore, SupabaseAuthConfig},
        ChatSecurityConfig, ChatSecurityState, DependencyStatus, PythonCircuitBreaker,
        PythonRuntimeConfig, PythonRuntimeMode,
    };
    use std::{path::PathBuf, sync::Arc};
    use tokio::sync::RwLock;

    fn build_test_state() -> AppState {
        AppState {
            project_root: PathBuf::from("."),
            python_root: PathBuf::from("backend/python"),
            python_bin: "python".to_string(),
            python_entry: PathBuf::from("backend/python/main.py"),
            python_timeout_ms: 1_000,
            python_runtime: PythonRuntimeConfig {
                mode: PythonRuntimeMode::Subprocess,
                service_host: "127.0.0.1".to_string(),
                service_port: 7010,
                service_timeout_ms: 30_000,
                fallback_to_subprocess: false,
                retry_attempts: 0,
                circuit_breaker_enabled: true,
                circuit_failure_threshold: 3,
                circuit_reset_ms: 30_000,
            },
            python_circuit: Arc::new(Mutex::new(PythonCircuitBreaker::new())),
            runtime_mode: "live".to_string(),
            runtime_session_version: 1,
            mock_mode: false,
            node_bin: "node".to_string(),
            python_health: Arc::new(RwLock::new(DependencyStatus::default())),
            supabase_auth: Arc::new(SupabaseAuthConfig {
                jwt_secret: "test-secret".to_string(),
                issuer: "https://example.supabase.co/auth/v1".to_string(),
            }),
            observability_stream_tickets: Arc::new(
                ProcessLocalObservabilityStreamTicketStore::default(),
            ),
            chat_security: default_chat_security_state(),
        }
    }

    fn test_router(config: HistoricalAuditRouteConfig) -> Router {
        let state = build_test_state();
        protected_historical_audit_router(state.clone(), config).with_state(state)
    }

    fn token(sub: Option<&str>, exp_offset_seconds: i64) -> String {
        let now = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .expect("unix")
            .as_secs() as i64;
        let mut claims = json!({
            "iss": "https://example.supabase.co/auth/v1",
            "aud": "authenticated",
            "exp": now + exp_offset_seconds,
        });
        if let Some(sub) = sub {
            claims["sub"] = json!(sub);
        }
        encode(
            &Header::new(Algorithm::HS256),
            &claims,
            &EncodingKey::from_secret("test-secret".as_bytes()),
        )
        .expect("jwt")
    }

    fn get(path: &str) -> Request<Body> {
        Request::builder()
            .method(Method::GET)
            .uri(path)
            .body(Body::empty())
            .expect("request")
    }

    fn get_with_token(path: &str, token: &str) -> Request<Body> {
        Request::builder()
            .method(Method::GET)
            .uri(path)
            .header(AUTHORIZATION, format!("Bearer {token}"))
            .body(Body::empty())
            .expect("request")
    }

    async fn response_json(response: axum::response::Response) -> Value {
        let body = to_bytes(response.into_body(), usize::MAX)
            .await
            .expect("body");
        serde_json::from_slice(&body).expect("json")
    }

    #[tokio::test]
    async fn route_builder_exists_but_candidate_route_is_disabled_by_default() {
        let response = test_router(HistoricalAuditRouteConfig::default())
            .oneshot(get_with_token(
                HISTORICAL_AUDIT_LIST_PATH,
                &token(Some("operator-123"), 300),
            ))
            .await
            .expect("response");
        assert_eq!(response.status(), StatusCode::NOT_FOUND);
        let body = response_json(response).await;
        assert_eq!(body["error_category"], "route_disabled");
        assert_eq!(body["route"]["production_wired"], false);
    }

    #[tokio::test]
    async fn no_auth_internal_historical_audit_route_is_not_added() {
        let response = test_router(HistoricalAuditRouteConfig::enabled_for_test_callers(&[
            "operator-123",
        ]))
        .oneshot(get_with_token(
            "/internal/audit/dry-run",
            &token(Some("operator-123"), 300),
        ))
        .await
        .expect("response");
        assert_eq!(response.status(), StatusCode::NOT_FOUND);
    }

    #[tokio::test]
    async fn missing_jwt_denies_access_when_route_enabled() {
        let response = test_router(HistoricalAuditRouteConfig::enabled_for_test_callers(&[
            "operator-123",
        ]))
        .oneshot(get(HISTORICAL_AUDIT_LIST_PATH))
        .await
        .expect("response");
        assert_eq!(response.status(), StatusCode::UNAUTHORIZED);
    }

    #[tokio::test]
    async fn invalid_jwt_denies_access_when_route_enabled() {
        let response = test_router(HistoricalAuditRouteConfig::enabled_for_test_callers(&[
            "operator-123",
        ]))
        .oneshot(get_with_token(HISTORICAL_AUDIT_LIST_PATH, "not-a-jwt"))
        .await
        .expect("response");
        assert_eq!(response.status(), StatusCode::UNAUTHORIZED);
    }

    #[tokio::test]
    async fn missing_caller_identity_denies_access() {
        let response = test_router(HistoricalAuditRouteConfig::enabled_for_test_callers(&[
            "operator-123",
        ]))
        .oneshot(get_with_token(
            HISTORICAL_AUDIT_LIST_PATH,
            &token(None, 300),
        ))
        .await
        .expect("response");
        assert_eq!(response.status(), StatusCode::UNAUTHORIZED);
        let body = response_json(response).await;
        assert_eq!(body["error_category"], "missing_caller_identity");
    }

    #[tokio::test]
    async fn missing_readonly_capability_denies_access() {
        let response = test_router(HistoricalAuditRouteConfig::enabled_for_test_callers(&[
            "operator-123",
        ]))
        .oneshot(get_with_token(
            HISTORICAL_AUDIT_LIST_PATH,
            &token(Some("operator-456"), 300),
        ))
        .await
        .expect("response");
        assert_eq!(response.status(), StatusCode::FORBIDDEN);
        let body = response_json(response).await;
        assert_eq!(
            body["error_category"],
            "missing_historical_audit_readonly_capability"
        );
    }

    #[tokio::test]
    async fn valid_auth_but_disabled_switch_still_denies_access() {
        let mut config = HistoricalAuditRouteConfig::default();
        config.authorized_callers.insert("operator-123".to_string());
        let response = test_router(config)
            .oneshot(get_with_token(
                HISTORICAL_AUDIT_LIST_PATH,
                &token(Some("operator-123"), 300),
            ))
            .await
            .expect("response");
        assert_eq!(response.status(), StatusCode::NOT_FOUND);
        let body = response_json(response).await;
        assert_eq!(body["error_category"], "route_disabled");
    }

    #[tokio::test]
    async fn excessive_query_complexity_denies_access() {
        let response = test_router(HistoricalAuditRouteConfig::enabled_for_test_callers(&[
            "operator-123",
        ]))
        .oneshot(get_with_token(
            "/protected/internal/audit/dry-run?unknown=value",
            &token(Some("operator-123"), 300),
        ))
        .await
        .expect("response");
        assert_eq!(response.status(), StatusCode::BAD_REQUEST);
        let body = response_json(response).await;
        assert_eq!(body["error_category"], "unsupported_query_param");
    }

    #[tokio::test]
    async fn excessive_page_size_denies_access() {
        let config = HistoricalAuditRouteConfig::enabled_for_test_callers(&["operator-123"])
            .with_max_page_size(5);
        let response = test_router(config)
            .oneshot(get_with_token(
                "/protected/internal/audit/dry-run?limit=6",
                &token(Some("operator-123"), 300),
            ))
            .await
            .expect("response");
        assert_eq!(response.status(), StatusCode::BAD_REQUEST);
        let body = response_json(response).await;
        assert_eq!(body["error_category"], "limit_out_of_bounds");
    }

    #[tokio::test]
    async fn invalid_sort_and_detail_filter_deny_access() {
        let router = test_router(HistoricalAuditRouteConfig::enabled_for_test_callers(&[
            "operator-123",
        ]));
        let invalid_sort = router
            .clone()
            .oneshot(get_with_token(
                "/protected/internal/audit/dry-run?sort_by=raw_sql",
                &token(Some("operator-123"), 300),
            ))
            .await
            .expect("response");
        assert_eq!(invalid_sort.status(), StatusCode::BAD_REQUEST);

        let invalid_plan = router
            .oneshot(get_with_token(
                "/protected/internal/audit/dry-run/../secret",
                &token(Some("operator-123"), 300),
            ))
            .await
            .expect("response");
        assert_ne!(invalid_plan.status(), StatusCode::OK);
    }

    #[tokio::test]
    async fn rate_limit_denies_excessive_requests() {
        let config = HistoricalAuditRouteConfig::enabled_for_test_callers(&["operator-123"])
            .with_rate_limit(1, 60);
        let router = test_router(config);
        let first = router
            .clone()
            .oneshot(get_with_token(
                HISTORICAL_AUDIT_LIST_PATH,
                &token(Some("operator-123"), 300),
            ))
            .await
            .expect("response");
        assert_eq!(first.status(), StatusCode::NOT_IMPLEMENTED);

        let second = router
            .oneshot(get_with_token(
                HISTORICAL_AUDIT_LIST_PATH,
                &token(Some("operator-123"), 300),
            ))
            .await
            .expect("response");
        assert_eq!(second.status(), StatusCode::TOO_MANY_REQUESTS);
        let body = response_json(second).await;
        assert_eq!(body["error_category"], "rate_limited");
    }

    #[tokio::test]
    async fn safe_audit_and_observability_fields_exclude_forbidden_fields() {
        let response = test_router(HistoricalAuditRouteConfig::enabled_for_test_callers(&[
            "operator-123",
        ]))
        .oneshot(get_with_token(
            HISTORICAL_AUDIT_LIST_PATH,
            &token(Some("operator-123"), 300),
        ))
        .await
        .expect("response");
        assert_eq!(response.status(), StatusCode::NOT_IMPLEMENTED);
        let body = response_json(response).await;
        let serialized = serde_json::to_string(&body).expect("json");
        for forbidden in [
            "Authorization",
            "Bearer",
            "api_key",
            "raw_jsonl",
            "raw_sqlite",
            "raw_sql",
            "raw_prompt",
            "provider_payload",
            "tool_output",
            "stdout",
            "stderr",
            "stack trace",
            ".env",
        ] {
            assert!(!serialized.contains(forbidden), "{forbidden}");
        }
        assert_eq!(
            body["data"]["delegation_boundary"],
            "HistoricalDryRunAuditQueryService"
        );
        assert_eq!(body["data"]["storage_accessed"], false);
        assert_eq!(body["data"]["runtime_invoked"], false);
        assert_eq!(body["data"]["copy_export_enabled"], false);
    }

    #[test]
    fn route_skeleton_does_not_reference_direct_storage_or_execution_paths() {
        let source = include_str!("protected_historical_audit.rs");
        let forbidden = [
            ["Memory", "Facade"].concat(),
            ["read_recent", "_jsonl"].concat(),
            ["rus", "qlite"].concat(),
            ["SELECT", " "].concat(),
            ["call", "_python"].concat(),
            ["call", "_provider"].concat(),
            ["provider", "_router"].concat(),
            ["retry", "_execution"].concat(),
            ["replan", "_execution"].concat(),
            ["Cock", "pit"].concat(),
            ["copy", "_to"].concat(),
            ["download", "_"].concat(),
        ];
        for marker in forbidden {
            assert!(!source.contains(&marker), "{marker}");
        }
    }

    #[test]
    fn production_router_does_not_wire_candidate_routes() {
        let main_source = include_str!("main.rs");
        assert!(!main_source.contains("/protected/internal/audit/dry-run"));
        assert!(!main_source.contains("/internal/audit/dry-run"));
        assert!(!main_source.contains("protected_historical_audit_router(state"));
    }

    #[test]
    fn test_state_keeps_runtime_and_provider_execution_unmodified() {
        let state = build_test_state();
        assert_eq!(state.runtime_mode, "live");
        assert!(!state.mock_mode);
        let _chat_security: Arc<ChatSecurityState> =
            Arc::new(ChatSecurityState::with_config(ChatSecurityConfig {
                max_message_chars: 10,
                max_body_bytes: 128,
                rate_limit_enabled: false,
                rate_limit_per_minute: 1,
            }));
    }
}
