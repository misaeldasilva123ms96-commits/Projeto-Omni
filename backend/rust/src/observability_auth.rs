//! Supabase JWT validation for operator routes.
//!
//! **Secrets:** `SUPABASE_JWT_SECRET` is sensitive and must never appear in HTTP responses.
//! Public issuer URL may come from `SUPABASE_URL` or `VITE_SUPABASE_URL` (same value as the browser anon project URL).
//! Python-side provider keys are centralized under `backend/python/config/`; this Rust module only reads what the Axum process needs.

use std::{
    collections::HashMap,
    env,
    sync::{Arc, Mutex},
    time::{Duration, Instant},
};

use axum::{
    extract::{Request, State},
    http::{
        header::{AUTHORIZATION, CACHE_CONTROL},
        HeaderMap, StatusCode,
    },
    middleware::Next,
    response::{IntoResponse, Response},
    Json,
};
use jsonwebtoken::{decode, Algorithm, DecodingKey, Validation};
use rand::Rng;
use serde::{Deserialize, Serialize};
use serde_json::Value;

use crate::AppState;

const OBSERVABILITY_STREAM_TICKET_TTL_SECONDS: u64 = 30;
const MAX_ACTIVE_STREAM_TICKETS: usize = 1_024;
const SUPABASE_AUTHENTICATED_AUDIENCE: &str = "authenticated";
const MINIMUM_HS256_SECRET_BYTES: usize = 32;
pub(crate) const OBSERVABILITY_STREAM_TICKET_STORE_MODE_ENV: &str =
    "OMNI_OBSERVABILITY_STREAM_TICKET_STORE_MODE";

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum ObservabilityStreamTicketStoreMode {
    ProcessLocal,
}

impl ObservabilityStreamTicketStoreMode {
    pub(crate) fn as_str(self) -> &'static str {
        match self {
            Self::ProcessLocal => "process_local",
        }
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum ObservabilityStreamTicketScope {
    Stream,
    #[cfg(test)]
    Other,
}

pub(crate) trait ObservabilityStreamTicketStore: Send + Sync {
    fn issue(&self, scope: ObservabilityStreamTicketScope) -> IssuedObservabilityStreamTicket;
    fn consume(&self, ticket: &str, scope: ObservabilityStreamTicketScope) -> bool;
    fn mode(&self) -> ObservabilityStreamTicketStoreMode;
}

#[derive(Clone, Copy, Debug)]
struct ProcessLocalTicketRecord {
    expires_at: Instant,
    scope: ObservabilityStreamTicketScope,
}

/// Process-local storage is the safe default for the current single-instance deployment.
/// Multi-instance deployments require sticky routing, or a future shared implementation of
/// [`ObservabilityStreamTicketStore`], so issue and consume reach the same ticket state.
#[derive(Clone, Debug)]
pub(crate) struct ProcessLocalObservabilityStreamTicketStore {
    tickets: Arc<Mutex<HashMap<String, ProcessLocalTicketRecord>>>,
    ttl: Duration,
}

#[derive(Debug, Serialize, Deserialize, PartialEq, Eq)]
pub(crate) struct IssuedObservabilityStreamTicket {
    pub(crate) ticket: String,
    pub(crate) expires_in_seconds: u64,
}

impl Default for ProcessLocalObservabilityStreamTicketStore {
    fn default() -> Self {
        Self::with_ttl(Duration::from_secs(OBSERVABILITY_STREAM_TICKET_TTL_SECONDS))
    }
}

impl ProcessLocalObservabilityStreamTicketStore {
    fn with_ttl(ttl: Duration) -> Self {
        Self {
            tickets: Arc::new(Mutex::new(HashMap::new())),
            ttl,
        }
    }

    fn issue_at(
        &self,
        scope: ObservabilityStreamTicketScope,
        now: Instant,
    ) -> IssuedObservabilityStreamTicket {
        let ticket = generate_stream_ticket();
        let expires_at = now + self.ttl;
        let mut tickets = self
            .tickets
            .lock()
            .unwrap_or_else(|poisoned| poisoned.into_inner());
        tickets.retain(|_, record| record.expires_at > now);
        if tickets.len() >= MAX_ACTIVE_STREAM_TICKETS {
            if let Some(oldest) = tickets
                .iter()
                .min_by_key(|(_, record)| record.expires_at)
                .map(|(ticket, _)| ticket.clone())
            {
                tickets.remove(&oldest);
            }
        }
        tickets.insert(
            ticket.clone(),
            ProcessLocalTicketRecord { expires_at, scope },
        );

        IssuedObservabilityStreamTicket {
            ticket,
            expires_in_seconds: self.ttl.as_secs(),
        }
    }

    fn consume_at(
        &self,
        ticket: &str,
        scope: ObservabilityStreamTicketScope,
        now: Instant,
    ) -> bool {
        if ticket.is_empty() {
            return false;
        }
        let mut tickets = self
            .tickets
            .lock()
            .unwrap_or_else(|poisoned| poisoned.into_inner());
        let Some(record) = tickets.get(ticket).copied() else {
            return false;
        };
        if record.expires_at <= now {
            tickets.remove(ticket);
            return false;
        }
        if record.scope != scope {
            return false;
        }
        tickets.remove(ticket);
        true
    }
}

impl ObservabilityStreamTicketStore for ProcessLocalObservabilityStreamTicketStore {
    fn issue(&self, scope: ObservabilityStreamTicketScope) -> IssuedObservabilityStreamTicket {
        self.issue_at(scope, Instant::now())
    }

    fn consume(&self, ticket: &str, scope: ObservabilityStreamTicketScope) -> bool {
        self.consume_at(ticket, scope, Instant::now())
    }

    fn mode(&self) -> ObservabilityStreamTicketStoreMode {
        ObservabilityStreamTicketStoreMode::ProcessLocal
    }
}

pub(crate) fn build_observability_stream_ticket_store(
    configured_mode: &str,
) -> Result<Arc<dyn ObservabilityStreamTicketStore>, String> {
    match configured_mode.trim().to_ascii_lowercase().as_str() {
        "" | "process_local" => Ok(Arc::new(
            ProcessLocalObservabilityStreamTicketStore::default(),
        )),
        "shared_external" => Err(
            "observability stream ticket store mode shared_external is not supported".to_string(),
        ),
        _ => Err("unsupported observability stream ticket store mode".to_string()),
    }
}

pub(crate) fn observability_stream_ticket_store_from_env(
) -> Result<Arc<dyn ObservabilityStreamTicketStore>, String> {
    let mode = env::var(OBSERVABILITY_STREAM_TICKET_STORE_MODE_ENV)
        .unwrap_or_else(|_| "process_local".to_string());
    build_observability_stream_ticket_store(&mode)
}

fn generate_stream_ticket() -> String {
    let mut bytes = [0_u8; 32];
    rand::rng().fill_bytes(&mut bytes);
    let mut ticket = String::with_capacity(4 + bytes.len() * 2);
    ticket.push_str("ost_");
    for byte in bytes {
        use std::fmt::Write;
        let _ = write!(ticket, "{byte:02x}");
    }
    ticket
}

#[derive(Clone, Debug)]
pub(crate) struct SupabaseAuthConfig {
    pub(crate) jwt_secret: String,
    pub(crate) issuer: String,
}

#[derive(Debug, Deserialize, Clone)]
#[allow(dead_code)]
struct SupabaseClaims {
    exp: usize,
    iss: String,
    sub: Option<String>,
    #[serde(default)]
    role: Option<String>,
    #[serde(default)]
    app_metadata: Value,
}

#[derive(Clone, Debug)]
pub(crate) struct AuthenticatedSubject {
    pub(crate) user_id: String,
    capabilities: Vec<String>,
    roles: Vec<String>,
}

impl AuthenticatedSubject {
    pub(crate) fn can_read_control(&self) -> bool {
        self.is_control_admin()
            || self
                .capabilities
                .iter()
                .any(|v| matches!(v.as_str(), "run_control:read" | "run_control:write"))
    }

    pub(crate) fn can_write_control(&self) -> bool {
        self.is_control_admin() || self.capabilities.iter().any(|v| v == "run_control:write")
    }

    pub(crate) fn is_control_admin(&self) -> bool {
        self.roles.iter().any(|v| {
            matches!(
                v.as_str(),
                "admin" | "operator" | "service_role" | "omni_operator"
            )
        }) || self.capabilities.iter().any(|v| v == "run_control:admin")
    }
}

fn string_values(value: Option<&Value>) -> Vec<String> {
    match value {
        Some(Value::String(value)) => vec![value.trim().to_ascii_lowercase()],
        Some(Value::Array(values)) => values
            .iter()
            .filter_map(Value::as_str)
            .map(|v| v.trim().to_ascii_lowercase())
            .filter(|v| !v.is_empty())
            .collect(),
        _ => Vec::new(),
    }
}

fn authenticated_subject(claims: &SupabaseClaims) -> Option<AuthenticatedSubject> {
    let user_id = claims.sub.as_deref()?.trim();
    if user_id.is_empty() {
        return None;
    }
    let metadata = claims.app_metadata.as_object();
    let mut roles = claims
        .role
        .as_deref()
        .map(|v| vec![v.trim().to_ascii_lowercase()])
        .unwrap_or_default();
    roles.extend(string_values(metadata.and_then(|v| v.get("role"))));
    roles.extend(string_values(metadata.and_then(|v| v.get("roles"))));
    let mut capabilities = string_values(metadata.and_then(|v| v.get("capabilities")));
    capabilities.extend(string_values(metadata.and_then(|v| v.get("permissions"))));
    Some(AuthenticatedSubject {
        user_id: user_id.to_string(),
        capabilities,
        roles,
    })
}

#[derive(Debug, Serialize, Deserialize, PartialEq, Eq)]
struct UnauthorizedBody {
    error: &'static str,
    message: &'static str,
}

impl SupabaseAuthConfig {
    pub(crate) fn from_env() -> Result<Self, String> {
        let jwt_secret = env::var("SUPABASE_JWT_SECRET")
            .map_err(|_| "missing SUPABASE_JWT_SECRET environment variable".to_string())?;
        if jwt_secret.trim().is_empty() {
            return Err("SUPABASE_JWT_SECRET cannot be empty".to_string());
        }
        if jwt_secret.len() < MINIMUM_HS256_SECRET_BYTES {
            return Err(format!(
                "SUPABASE_JWT_SECRET must contain at least {MINIMUM_HS256_SECRET_BYTES} bytes"
            ));
        }

        let supabase_url =
            env::var("SUPABASE_URL")
                .or_else(|_| env::var("VITE_SUPABASE_URL"))
                .map_err(|_| {
                "missing SUPABASE_URL (or VITE_SUPABASE_URL) required for Supabase issuer validation"
                    .to_string()
            })?;
        let configured_url = supabase_url.trim();
        if configured_url.is_empty() {
            return Err("SUPABASE_URL cannot be empty".to_string());
        }
        if configured_url != supabase_url {
            return Err("SUPABASE_URL must be a clean absolute HTTPS project URL".to_string());
        }

        let mut parsed_url = reqwest::Url::parse(configured_url)
            .map_err(|_| "SUPABASE_URL must be a valid absolute HTTPS URL".to_string())?;
        let has_https_authority = configured_url
            .get(..8)
            .is_some_and(|prefix| prefix.eq_ignore_ascii_case("https://"))
            && configured_url
                .get(8..)
                .is_some_and(|authority| !authority.starts_with(['/', '\\']));
        if parsed_url.scheme() != "https" || !has_https_authority {
            return Err("SUPABASE_URL must use HTTPS with an explicit host".to_string());
        }
        if parsed_url.host_str().is_none_or(str::is_empty) {
            return Err("SUPABASE_URL must include a host".to_string());
        }
        if !parsed_url.username().is_empty() || parsed_url.password().is_some() {
            return Err("SUPABASE_URL must not include user information".to_string());
        }
        if parsed_url.fragment().is_some() {
            return Err("SUPABASE_URL must not include a fragment".to_string());
        }
        if parsed_url.query().is_some() {
            return Err("SUPABASE_URL must not include a query string".to_string());
        }
        if parsed_url.path() != "/" {
            return Err("SUPABASE_URL must be a project base URL without a path".to_string());
        }

        parsed_url.set_path("/auth/v1");

        Ok(Self {
            jwt_secret,
            issuer: parsed_url.to_string(),
        })
    }

    fn validate_token(&self, token: &str) -> Result<SupabaseClaims, jsonwebtoken::errors::Error> {
        let mut validation = Validation::new(Algorithm::HS256);
        validation.validate_exp = true;
        validation.validate_aud = true;
        validation.leeway = 0;
        validation.set_required_spec_claims(&["exp", "iss", "aud"]);
        validation.set_issuer(&[self.issuer.as_str()]);
        validation.set_audience(&[SUPABASE_AUTHENTICATED_AUDIENCE]);
        validation.algorithms = vec![Algorithm::HS256];

        decode::<SupabaseClaims>(
            token,
            &DecodingKey::from_secret(self.jwt_secret.as_bytes()),
            &validation,
        )
        .map(|data| data.claims)
    }
}

pub(crate) async fn require_supabase_auth(
    State(state): State<AppState>,
    mut req: Request,
    next: Next,
) -> Response {
    let token = extract_bearer_token(req.headers());
    let Some(token) = token else {
        return unauthorized_response();
    };

    match state.supabase_auth.validate_token(token) {
        Ok(claims) => {
            let Some(subject) = authenticated_subject(&claims) else {
                return unauthorized_response();
            };
            req.extensions_mut().insert(subject.user_id.clone());
            req.extensions_mut().insert(subject);
            next.run(req).await
        }
        Err(_) => unauthorized_response(),
    }
}

pub(crate) async fn issue_observability_stream_ticket(
    State(state): State<AppState>,
) -> impl IntoResponse {
    (
        [(CACHE_CONTROL, "no-store")],
        Json(
            state
                .observability_stream_tickets
                .issue(ObservabilityStreamTicketScope::Stream),
        ),
    )
}

pub(crate) async fn require_observability_stream_ticket(
    State(state): State<AppState>,
    req: Request,
    next: Next,
) -> Response {
    let Some(ticket) = extract_stream_ticket(req.uri().query()) else {
        return unauthorized_stream_ticket_response();
    };
    if !state
        .observability_stream_tickets
        .consume(ticket, ObservabilityStreamTicketScope::Stream)
    {
        return unauthorized_stream_ticket_response();
    }
    next.run(req).await
}

pub(crate) fn sanitize_uri_for_logs(uri: &axum::http::Uri) -> String {
    let Some(query) = uri.query() else {
        return uri.to_string();
    };

    let sanitized_query = query
        .split('&')
        .filter(|segment| !segment.is_empty())
        .map(sanitize_query_segment)
        .collect::<Vec<_>>()
        .join("&");

    if sanitized_query.is_empty() {
        uri.path().to_string()
    } else {
        format!("{}?{}", uri.path(), sanitized_query)
    }
}

fn sanitize_query_segment(segment: &str) -> String {
    let mut parts = segment.splitn(2, '=');
    let key = parts.next().unwrap_or_default();
    let value = parts.next().unwrap_or_default();
    if matches!(key, "token" | "ticket") {
        format!("{key}=[REDACTED]")
    } else if value.is_empty() {
        key.to_string()
    } else {
        format!("{key}={value}")
    }
}

fn unauthorized_response() -> Response {
    (
        StatusCode::UNAUTHORIZED,
        Json(UnauthorizedBody {
            error: "unauthorized",
            message: "Valid Supabase session required",
        }),
    )
        .into_response()
}

fn unauthorized_stream_ticket_response() -> Response {
    (
        StatusCode::UNAUTHORIZED,
        Json(UnauthorizedBody {
            error: "unauthorized",
            message: "Valid observability stream ticket required",
        }),
    )
        .into_response()
}

fn extract_bearer_token(headers: &HeaderMap) -> Option<&str> {
    let header = headers.get(AUTHORIZATION)?.to_str().ok()?.trim();
    header
        .strip_prefix("Bearer ")
        .or_else(|| header.strip_prefix("bearer "))
        .map(str::trim)
        .filter(|token| !token.is_empty())
}

fn extract_stream_ticket(query: Option<&str>) -> Option<&str> {
    let mut matches = query?.split('&').filter_map(|segment| {
        let (key, value) = segment.split_once('=').unwrap_or((segment, ""));
        (key == "ticket" && !value.is_empty()).then_some(value)
    });
    let ticket = matches.next()?;
    if matches.next().is_some() {
        return None;
    }
    Some(ticket)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::test_support::EnvTestGuard;
    use axum::{
        body::Body,
        http::{Method, Request},
        routing::{get, post},
        Router,
    };
    use jsonwebtoken::{encode, EncodingKey, Header};
    use serde_json::{json, Value};
    use std::sync::Arc;
    use tower::ServiceExt;

    fn build_config() -> SupabaseAuthConfig {
        SupabaseAuthConfig {
            jwt_secret: "test-only-high-entropy-secret-material".to_string(),
            issuer: "https://example.supabase.co/auth/v1".to_string(),
        }
    }

    #[test]
    fn public_demo_mode_without_explicit_auth_config_fails_closed() {
        let env = EnvTestGuard::new(&[
            "SUPABASE_JWT_SECRET",
            "SUPABASE_URL",
            "VITE_SUPABASE_URL",
            "OMNI_PUBLIC_DEMO_MODE",
        ]);
        env.remove("SUPABASE_JWT_SECRET");
        env.remove("SUPABASE_URL");
        env.remove("VITE_SUPABASE_URL");
        env.set("OMNI_PUBLIC_DEMO_MODE", "true");

        let error = SupabaseAuthConfig::from_env()
            .expect_err("public demo must not synthesize authentication configuration");
        assert!(error.contains("SUPABASE_JWT_SECRET"));
    }

    fn auth_config_from_url(url: Option<&str>) -> Result<SupabaseAuthConfig, String> {
        let env = EnvTestGuard::new(&["SUPABASE_JWT_SECRET", "SUPABASE_URL", "VITE_SUPABASE_URL"]);
        env.set(
            "SUPABASE_JWT_SECRET",
            "test-only-high-entropy-secret-material",
        );
        env.remove("SUPABASE_URL");
        env.remove("VITE_SUPABASE_URL");
        if let Some(url) = url {
            env.set("SUPABASE_URL", url);
        }
        SupabaseAuthConfig::from_env()
    }

    #[test]
    fn explicit_https_project_urls_construct_the_historical_issuer() {
        for url in [
            "https://example.supabase.co",
            "https://example.supabase.co/",
        ] {
            let config = auth_config_from_url(Some(url)).expect("explicit secure auth config");
            assert_eq!(config.issuer, "https://example.supabase.co/auth/v1");
        }
    }

    #[test]
    fn missing_and_empty_supabase_urls_fail_closed() {
        let missing = auth_config_from_url(None).expect_err("missing URL must fail");
        assert!(missing.contains("missing SUPABASE_URL"));

        for url in ["", "   "] {
            let empty = auth_config_from_url(Some(url)).expect_err("empty URL must fail");
            assert!(empty.contains("cannot be empty"));
        }
    }

    #[test]
    fn malformed_or_unsafe_supabase_urls_fail_closed() {
        let rejected = [
            "not-a-url",
            "localhost",
            "example.com",
            "/relative",
            "http://example.supabase.co",
            "ftp://example.supabase.co",
            "https:///missing-host",
            "https://user@example.supabase.co",
            "https://user:password@example.supabase.co",
            "https://[invalid",
            "https://example.supabase.co#fragment",
            "https://example.supabase.co?query=value",
            "https://example.supabase.co/rest/v1",
            " https://example.supabase.co",
            "https://example.supabase.co ",
        ];

        for url in rejected {
            let error = auth_config_from_url(Some(url)).expect_err("unsafe URL must fail");
            assert!(error.starts_with("SUPABASE_URL"));
            assert!(!error.contains(url));
        }
    }

    fn build_state() -> AppState {
        AppState {
            project_root: std::env::temp_dir(),
            python_root: std::env::temp_dir(),
            python_bin: "python".to_string(),
            python_entry: std::env::temp_dir().join("main.py"),
            python_timeout_ms: 1_000,
            python_runtime: crate::PythonRuntimeConfig {
                mode: crate::PythonRuntimeMode::Subprocess,
                service_host: "127.0.0.1".to_string(),
                service_port: 7010,
                service_timeout_ms: 30_000,
                fallback_to_subprocess: false,
                retry_attempts: 0,
                circuit_breaker_enabled: true,
                circuit_failure_threshold: 3,
                circuit_reset_ms: 30_000,
            },
            python_circuit: Arc::new(std::sync::Mutex::new(crate::PythonCircuitBreaker::new())),
            runtime_mode: "live".to_string(),
            runtime_session_version: 1,
            mock_mode: false,
            node_bin: "node".to_string(),
            python_health: Arc::new(tokio::sync::RwLock::new(Default::default())),
            supabase_auth: Arc::new(build_config()),
            observability_stream_tickets: Arc::new(
                ProcessLocalObservabilityStreamTicketStore::default(),
            ),
            chat_security: crate::default_chat_security_state(),
        }
    }

    fn token_with_issuer_secret_and_audience(
        exp_offset_seconds: i64,
        issuer: &str,
        secret: &str,
        audience: Option<Value>,
    ) -> String {
        let now = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .expect("unix epoch")
            .as_secs() as i64;
        let mut claims = json!({
            "iss": issuer,
            "sub": "operator-123",
            "exp": now + exp_offset_seconds,
        });
        if let Some(audience) = audience {
            claims["aud"] = audience;
        }

        encode(
            &Header::new(Algorithm::HS256),
            &claims,
            &EncodingKey::from_secret(secret.as_bytes()),
        )
        .expect("encode test jwt")
    }

    fn token_with_audience(exp_offset_seconds: i64, audience: Option<Value>) -> String {
        token_with_issuer_secret_and_audience(
            exp_offset_seconds,
            "https://example.supabase.co/auth/v1",
            "test-only-high-entropy-secret-material",
            audience,
        )
    }

    fn token_with_offset(exp_offset_seconds: i64) -> String {
        token_with_audience(exp_offset_seconds, Some(json!("authenticated")))
    }

    fn test_router() -> Router {
        async fn ok_handler() -> Json<Value> {
            Json(json!({ "ok": true }))
        }

        let state = build_state();
        let protected = Router::new()
            .route("/api/observability/snapshot", get(ok_handler))
            .route(
                "/api/observability/stream-ticket",
                post(issue_observability_stream_ticket),
            )
            .route_layer(axum::middleware::from_fn_with_state(
                state.clone(),
                require_supabase_auth,
            ));
        let stream = Router::new()
            .route("/api/observability/stream", get(ok_handler))
            .route_layer(axum::middleware::from_fn_with_state(
                state.clone(),
                require_observability_stream_ticket,
            ));
        protected.merge(stream).with_state(state)
    }

    async fn read_json(response: Response) -> Value {
        let body = axum::body::to_bytes(response.into_body(), usize::MAX)
            .await
            .expect("read body");
        serde_json::from_slice(&body).expect("json body")
    }

    #[tokio::test]
    async fn request_without_authorization_header_returns_401() {
        let response = test_router()
            .oneshot(
                Request::builder()
                    .method(Method::GET)
                    .uri("/api/observability/snapshot")
                    .body(Body::empty())
                    .expect("request"),
            )
            .await
            .expect("response");

        assert_eq!(response.status(), StatusCode::UNAUTHORIZED);
        let body = read_json(response).await;
        assert_eq!(
            body,
            json!({
                "error": "unauthorized",
                "message": "Valid Supabase session required"
            })
        );
    }

    #[tokio::test]
    async fn malformed_token_returns_401() {
        let response = test_router()
            .oneshot(
                Request::builder()
                    .method(Method::GET)
                    .uri("/api/observability/snapshot")
                    .header(AUTHORIZATION, "Bearer not-a-jwt")
                    .body(Body::empty())
                    .expect("request"),
            )
            .await
            .expect("response");

        assert_eq!(response.status(), StatusCode::UNAUTHORIZED);
    }

    #[tokio::test]
    async fn expired_token_returns_401() {
        let response = test_router()
            .oneshot(
                Request::builder()
                    .method(Method::GET)
                    .uri("/api/observability/snapshot")
                    .header(AUTHORIZATION, format!("Bearer {}", token_with_offset(-60)))
                    .body(Body::empty())
                    .expect("request"),
            )
            .await
            .expect("response");

        assert_eq!(response.status(), StatusCode::UNAUTHORIZED);
    }

    #[tokio::test]
    async fn token_without_audience_returns_401() {
        let response = test_router()
            .oneshot(
                Request::builder()
                    .method(Method::GET)
                    .uri("/api/observability/snapshot")
                    .header(
                        AUTHORIZATION,
                        format!("Bearer {}", token_with_audience(300, None)),
                    )
                    .body(Body::empty())
                    .expect("request"),
            )
            .await
            .expect("response");

        assert_eq!(response.status(), StatusCode::UNAUTHORIZED);
    }

    #[tokio::test]
    async fn token_with_wrong_audience_returns_401() {
        for audience in [
            json!("another-service"),
            json!(["another-service", "third-service"]),
        ] {
            let response = test_router()
                .oneshot(
                    Request::builder()
                        .method(Method::GET)
                        .uri("/api/observability/snapshot")
                        .header(
                            AUTHORIZATION,
                            format!("Bearer {}", token_with_audience(300, Some(audience))),
                        )
                        .body(Body::empty())
                        .expect("request"),
                )
                .await
                .expect("response");

            assert_eq!(response.status(), StatusCode::UNAUTHORIZED);
        }
    }

    #[tokio::test]
    async fn token_with_wrong_issuer_returns_401() {
        let token = token_with_issuer_secret_and_audience(
            300,
            "https://attacker.invalid/auth/v1",
            "test-only-high-entropy-secret-material",
            Some(json!("authenticated")),
        );
        let response = test_router()
            .oneshot(
                Request::builder()
                    .method(Method::GET)
                    .uri("/api/observability/snapshot")
                    .header(AUTHORIZATION, format!("Bearer {token}"))
                    .body(Body::empty())
                    .expect("request"),
            )
            .await
            .expect("response");

        assert_eq!(response.status(), StatusCode::UNAUTHORIZED);
    }

    #[tokio::test]
    async fn token_with_wrong_signature_returns_401() {
        let token = token_with_issuer_secret_and_audience(
            300,
            "https://example.supabase.co/auth/v1",
            "different-test-only-high-entropy-secret",
            Some(json!("authenticated")),
        );
        let response = test_router()
            .oneshot(
                Request::builder()
                    .method(Method::GET)
                    .uri("/api/observability/snapshot")
                    .header(AUTHORIZATION, format!("Bearer {token}"))
                    .body(Body::empty())
                    .expect("request"),
            )
            .await
            .expect("response");

        assert_eq!(response.status(), StatusCode::UNAUTHORIZED);
    }

    #[tokio::test]
    async fn valid_header_token_proceeds_to_handler() {
        let response = test_router()
            .oneshot(
                Request::builder()
                    .method(Method::GET)
                    .uri("/api/observability/snapshot")
                    .header(AUTHORIZATION, format!("Bearer {}", token_with_offset(300)))
                    .body(Body::empty())
                    .expect("request"),
            )
            .await
            .expect("response");

        assert_eq!(response.status(), StatusCode::OK);
    }

    #[tokio::test]
    async fn token_with_expected_audience_in_array_proceeds_to_handler() {
        let response = test_router()
            .oneshot(
                Request::builder()
                    .method(Method::GET)
                    .uri("/api/observability/snapshot")
                    .header(
                        AUTHORIZATION,
                        format!(
                            "Bearer {}",
                            token_with_audience(
                                300,
                                Some(json!(["authenticated", "another-service"]))
                            )
                        ),
                    )
                    .body(Body::empty())
                    .expect("request"),
            )
            .await
            .expect("response");

        assert_eq!(response.status(), StatusCode::OK);
    }

    #[tokio::test]
    async fn sse_query_token_with_valid_jwt_is_rejected() {
        let response = test_router()
            .oneshot(
                Request::builder()
                    .method(Method::GET)
                    .uri(format!(
                        "/api/observability/stream?token={}",
                        token_with_offset(300)
                    ))
                    .body(Body::empty())
                    .expect("request"),
            )
            .await
            .expect("response");

        assert_eq!(response.status(), StatusCode::UNAUTHORIZED);
    }

    #[tokio::test]
    async fn sse_query_token_with_invalid_jwt_returns_401() {
        let response = test_router()
            .oneshot(
                Request::builder()
                    .method(Method::GET)
                    .uri("/api/observability/stream?token=invalid-token")
                    .body(Body::empty())
                    .expect("request"),
            )
            .await
            .expect("response");

        assert_eq!(response.status(), StatusCode::UNAUTHORIZED);
    }

    #[tokio::test]
    async fn valid_stream_ticket_is_accepted_once() {
        let router = test_router();
        let issue_response = router
            .clone()
            .oneshot(
                Request::builder()
                    .method(Method::POST)
                    .uri("/api/observability/stream-ticket")
                    .header(AUTHORIZATION, format!("Bearer {}", token_with_offset(300)))
                    .body(Body::empty())
                    .expect("request"),
            )
            .await
            .expect("response");
        assert_eq!(issue_response.status(), StatusCode::OK);
        assert_eq!(
            issue_response
                .headers()
                .get("cache-control")
                .and_then(|value| value.to_str().ok()),
            Some("no-store")
        );
        let body = read_json(issue_response).await;
        let ticket = body.get("ticket").and_then(Value::as_str).expect("ticket");
        assert_eq!(body.get("expires_in_seconds"), Some(&json!(30)));

        let first = router
            .clone()
            .oneshot(
                Request::builder()
                    .method(Method::GET)
                    .uri(format!("/api/observability/stream?ticket={ticket}"))
                    .body(Body::empty())
                    .expect("request"),
            )
            .await
            .expect("response");
        assert_eq!(first.status(), StatusCode::OK);

        let reused = router
            .oneshot(
                Request::builder()
                    .method(Method::GET)
                    .uri(format!("/api/observability/stream?ticket={ticket}"))
                    .body(Body::empty())
                    .expect("request"),
            )
            .await
            .expect("response");
        assert_eq!(reused.status(), StatusCode::UNAUTHORIZED);
    }

    #[tokio::test]
    async fn stream_rejects_missing_or_unknown_ticket() {
        for uri in [
            "/api/observability/stream",
            "/api/observability/stream?ticket=unknown-reference",
        ] {
            let response = test_router()
                .oneshot(
                    Request::builder()
                        .method(Method::GET)
                        .uri(uri)
                        .body(Body::empty())
                        .expect("request"),
                )
                .await
                .expect("response");
            assert_eq!(response.status(), StatusCode::UNAUTHORIZED);
            let body = read_json(response).await;
            assert_eq!(
                body,
                json!({
                    "error": "unauthorized",
                    "message": "Valid observability stream ticket required"
                })
            );
        }
    }

    #[test]
    fn sanitize_uri_redacts_token_query_parameter() {
        let uri: axum::http::Uri = "/api/observability/stream?token=secret-token&interval=2"
            .parse()
            .expect("uri");
        assert_eq!(
            sanitize_uri_for_logs(&uri),
            "/api/observability/stream?token=[REDACTED]&interval=2"
        );
    }

    #[test]
    fn stream_ticket_is_opaque_scoped_and_single_use() {
        let store = ProcessLocalObservabilityStreamTicketStore::with_ttl(
            std::time::Duration::from_secs(30),
        );
        let now = std::time::Instant::now();
        let issued = store.issue_at(ObservabilityStreamTicketScope::Stream, now);

        assert_eq!(issued.expires_in_seconds, 30);
        assert!(issued.ticket.starts_with("ost_"));
        assert_ne!(issued.ticket, token_with_offset(300));
        assert!(store.consume_at(
            &issued.ticket,
            ObservabilityStreamTicketScope::Stream,
            now + std::time::Duration::from_secs(1)
        ));
        assert!(!store.consume_at(
            &issued.ticket,
            ObservabilityStreamTicketScope::Stream,
            now + std::time::Duration::from_secs(2)
        ));
    }

    #[test]
    fn expired_or_unknown_stream_ticket_is_rejected() {
        let store =
            ProcessLocalObservabilityStreamTicketStore::with_ttl(std::time::Duration::from_secs(5));
        let now = std::time::Instant::now();
        let issued = store.issue_at(ObservabilityStreamTicketScope::Stream, now);

        assert!(!store.consume_at(
            &issued.ticket,
            ObservabilityStreamTicketScope::Stream,
            now + std::time::Duration::from_secs(6)
        ));
        assert!(!store.consume_at(
            "unknown-reference",
            ObservabilityStreamTicketScope::Stream,
            now
        ));
    }

    #[test]
    fn process_local_ticket_store_mode_is_explicit() {
        let store = ProcessLocalObservabilityStreamTicketStore::default();

        assert_eq!(
            store.mode(),
            ObservabilityStreamTicketStoreMode::ProcessLocal
        );
        assert_eq!(store.mode().as_str(), "process_local");
    }

    #[test]
    fn unsupported_shared_ticket_store_mode_fails_closed() {
        assert!(build_observability_stream_ticket_store("shared_external").is_err());
        assert!(build_observability_stream_ticket_store("unknown").is_err());
    }

    #[test]
    fn stream_ticket_rejects_wrong_scope_without_consuming_valid_scope() {
        let store = ProcessLocalObservabilityStreamTicketStore::with_ttl(
            std::time::Duration::from_secs(30),
        );
        let now = std::time::Instant::now();
        let issued = store.issue_at(ObservabilityStreamTicketScope::Stream, now);

        assert!(!store.consume_at(
            &issued.ticket,
            ObservabilityStreamTicketScope::Other,
            now + std::time::Duration::from_secs(1),
        ));
        assert!(store.consume_at(
            &issued.ticket,
            ObservabilityStreamTicketScope::Stream,
            now + std::time::Duration::from_secs(2),
        ));
    }

    #[test]
    fn sanitize_uri_redacts_stream_ticket_query_parameter() {
        let uri: axum::http::Uri = "/api/observability/stream?ticket=opaque-reference&interval=2"
            .parse()
            .expect("uri");
        assert_eq!(
            sanitize_uri_for_logs(&uri),
            "/api/observability/stream?ticket=[REDACTED]&interval=2"
        );
    }
}
