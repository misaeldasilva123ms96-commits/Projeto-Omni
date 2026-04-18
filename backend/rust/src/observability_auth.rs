//! Supabase JWT validation for operator routes.
//!
//! **Secrets:** `SUPABASE_JWT_SECRET` is sensitive and must never appear in HTTP responses.
//! Public issuer URL may come from `SUPABASE_URL` or `VITE_SUPABASE_URL` (same value as the browser anon project URL).
//! Python-side provider keys are centralized under `backend/python/config/`; this Rust module only reads what the Axum process needs.

use std::env;

use axum::{
    extract::{Request, State},
    http::{header::AUTHORIZATION, HeaderMap, StatusCode},
    middleware::Next,
    response::{IntoResponse, Response},
    Json,
};
use jsonwebtoken::{decode, Algorithm, DecodingKey, Validation};
use serde::{Deserialize, Serialize};

use crate::AppState;

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
    aud: Option<serde_json::Value>,
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

        let supabase_url = env::var("SUPABASE_URL")
            .or_else(|_| env::var("VITE_SUPABASE_URL"))
            .map_err(|_| {
                "missing SUPABASE_URL (or VITE_SUPABASE_URL) required for Supabase issuer validation"
                    .to_string()
            })?;
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

pub(crate) async fn require_supabase_auth(
    State(state): State<AppState>,
    req: Request,
    next: Next,
) -> Response {
    let token = extract_auth_token(req.headers(), req.uri().path(), req.uri().query());
    let Some(token) = token else {
        return unauthorized_response();
    };

    match state.supabase_auth.validate_token(token) {
        Ok(_) => next.run(req).await,
        Err(_) => unauthorized_response(),
    }
}

pub(crate) fn sanitize_uri_for_logs(uri: &axum::http::Uri) -> String {
    let Some(query) = uri.query() else {
        return uri.to_string();
    };

    let sanitized_query = query
        .split('&')
        .filter(|segment| !segment.is_empty())
        .map(|segment| sanitize_query_segment(segment))
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
    if key == "token" {
        if value.is_empty() {
            "token=[REDACTED]".to_string()
        } else {
            "token=[REDACTED]".to_string()
        }
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

fn extract_auth_token<'a>(
    headers: &'a HeaderMap,
    path: &str,
    query: Option<&'a str>,
) -> Option<&'a str> {
    extract_bearer_token(headers).or_else(|| {
        if path == "/api/observability/stream" {
            extract_query_token(query)
        } else {
            None
        }
    })
}

fn extract_bearer_token(headers: &HeaderMap) -> Option<&str> {
    let header = headers.get(AUTHORIZATION)?.to_str().ok()?.trim();
    header
        .strip_prefix("Bearer ")
        .or_else(|| header.strip_prefix("bearer "))
        .map(str::trim)
        .filter(|token| !token.is_empty())
}

fn extract_query_token(query: Option<&str>) -> Option<&str> {
    let query = query?;
    query.split('&').find_map(|segment| {
        let (key, value) = segment.split_once('=').unwrap_or((segment, ""));
        if key == "token" && !value.is_empty() {
            Some(value)
        } else {
            None
        }
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use axum::{body::Body, http::{Method, Request}, routing::get, Router};
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

    fn build_state() -> AppState {
        AppState {
            project_root: std::env::temp_dir(),
            python_root: std::env::temp_dir(),
            python_bin: "python".to_string(),
            python_entry: std::env::temp_dir().join("main.py"),
            python_timeout_ms: 1_000,
            runtime_mode: "live".to_string(),
            runtime_session_version: 1,
            mock_mode: false,
            node_bin: "node".to_string(),
            python_health: Arc::new(tokio::sync::RwLock::new(Default::default())),
            supabase_auth: Arc::new(build_config()),
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
        Router::new()
            .route("/api/observability/snapshot", get(ok_handler))
            .route("/api/observability/stream", get(ok_handler))
            .route_layer(axum::middleware::from_fn_with_state(
                state.clone(),
                require_supabase_auth,
            ))
            .with_state(state)
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
    async fn sse_query_token_with_valid_jwt_proceeds() {
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

        assert_eq!(response.status(), StatusCode::OK);
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
}
