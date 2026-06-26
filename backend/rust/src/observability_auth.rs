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
use rand::rngs::SysRng;
use rand::Rng;
use serde::{Deserialize, Serialize};

use crate::AppState;

const OBSERVABILITY_STREAM_TICKET_TTL_SECONDS: u64 = 30;
const MAX_ACTIVE_STREAM_TICKETS: usize = 1_024;
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
    SysRng.fill(&mut bytes);
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
}

#[derive(Debug, Serialize, Deserialize, PartialEq, Eq)]
struct UnauthorizedBody {
    error: &'static str,
    message: &'static str,
}

impl SupabaseAuthConfig {
    pub(crate) fn from_env() -> Result<Self, String> {
        let public_demo_mode = env_flag("OMNI_PUBLIC_DEMO_MODE")
            .or_else(|| env_flag("OMINI_PUBLIC_DEMO_MODE"))
            .unwrap_or(false);

        let jwt_secret = match env::var("SUPABASE_JWT_SECRET") {
            Ok(value) => value,
            Err(_) if public_demo_mode => "omni-public-demo-local-auth-key".to_string(),
            Err(_) => return Err("missing SUPABASE_JWT_SECRET environment variable".to_string()),
        };
        if jwt_secret.trim().is_empty() {
            return Err("SUPABASE_JWT_SECRET cannot be empty".to_string());
        }

        let supabase_url = match env::var("SUPABASE_URL").or_else(|_| env::var("VITE_SUPABASE_URL")) {
            Ok(value) => value,
            Err(_) if public_demo_mode => "https://public-demo.local".to_string(),
            Err(_) => return Err(
                "missing SUPABASE_URL (or VITE_SUPABASE_URL) required for Supabase issuer validation"
                    .to_string(),
            ),
        };
        let normalized_url = supabase_url.trim().trim_end_matches('/');
        if normalized_url.is_empty() {
            return Err("SUPABASE_URL cannot be empty".to_string());
        }

        Ok(Self {
            jwt_secret,
            issuer: format!("{normalized_url}/auth/v1"),
        })
    }

    fn validate_token(&self, token: &str) -> Result<SupabaseClaims, jsonwebtoken::errors::Error> {
        let mut validation = Validation::new(Algorithm::HS256);
        validation.validate_exp = true;
        validation.validate_aud = false;
        validation.leeway = 0;
        validation.set_issuer(&[self.issuer.as_str()]);
        validation.algorithms = vec![Algorithm::HS256];

        decode::<SupabaseClaims>(
            token,
            &DecodingKey::from_secret(self.jwt_secret.as_bytes()),
            &validation,
        )
        .map(|data| data.claims)
    }
}

fn env_flag(name: &str) -> Option<bool> {
    env::var(name).ok().map(|value| {
        matches!(
            value.trim().to_ascii_lowercase().as_str(),
            "1" | "true" | "yes" | "on"
        )
    })
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
            if let Some(user_id) = claims.sub {
                req.extensions_mut().insert(user_id);
            }
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
            jwt_secret: "test-secret".to_string(),
            issuer: "https://example.supabase.co/auth/v1".to_string(),
        }
    }

    #[test]
    fn public_demo_mode_uses_local_auth_defaults_without_env_secret() {
        let previous_secret = env::var("SUPABASE_JWT_SECRET").ok();
        let previous_url = env::var("SUPABASE_URL").ok();
        let previous_vite_url = env::var("VITE_SUPABASE_URL").ok();
        let previous_demo = env::var("OMNI_PUBLIC_DEMO_MODE").ok();

        env::remove_var("SUPABASE_JWT_SECRET");
        env::remove_var("SUPABASE_URL");
        env::remove_var("VITE_SUPABASE_URL");
        env::set_var("OMNI_PUBLIC_DEMO_MODE", "true");

        let config = SupabaseAuthConfig::from_env().expect("public demo auth config");
        assert_eq!(config.issuer, "https://public-demo.local/auth/v1");
        assert!(!config.jwt_secret.trim().is_empty());

        if let Some(value) = previous_secret {
            env::set_var("SUPABASE_JWT_SECRET", value);
        } else {
            env::remove_var("SUPABASE_JWT_SECRET");
        }
        if let Some(value) = previous_url {
            env::set_var("SUPABASE_URL", value);
        } else {
            env::remove_var("SUPABASE_URL");
        }
        if let Some(value) = previous_vite_url {
            env::set_var("VITE_SUPABASE_URL", value);
        } else {
            env::remove_var("VITE_SUPABASE_URL");
        }
        if let Some(value) = previous_demo {
            env::set_var("OMNI_PUBLIC_DEMO_MODE", value);
        } else {
            env::remove_var("OMNI_PUBLIC_DEMO_MODE");
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

    fn token_with_offset(exp_offset_seconds: i64) -> String {
        let now = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .expect("unix epoch")
            .as_secs() as i64;
        let claims = json!({
            "iss": "https://example.supabase.co/auth/v1",
            "sub": "operator-123",
            "aud": "authenticated",
            "exp": now + exp_offset_seconds,
        });

        encode(
            &Header::new(Algorithm::HS256),
            &claims,
            &EncodingKey::from_secret("test-secret".as_bytes()),
        )
        .expect("encode test jwt")
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
