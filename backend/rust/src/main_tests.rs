// Unit tests for the omni-api binary boundary.
#![cfg(test)]

    use super::*;
    use crate::test_support::EnvTestGuard;
    use axum::{
        body::{to_bytes, Body},
        http::{Method, Request},
    };
    use jsonwebtoken::{encode, Algorithm, EncodingKey, Header};
    use std::fs;
    use tower::ServiceExt;

    #[test]
    fn provider_settings_health_signals_round_trip_without_secret_fields() {
        let raw = json!({
            "provider": "openai",
            "configured": true,
            "updated_at": 1234,
            "executable": true,
            "available": true,
            "reachable": true,
            "healthy": true,
            "health_valid": true,
            "last_checked_at": 2000,
            "valid_until": 3000,
            "latency_ms": 42,
            "cache_status": "fresh",
            "circuit_state": "closed",
            "consecutive_failures": 0,
            "next_probe_at": null
        });
        let metadata: ProviderMetadata = serde_json::from_value(raw).expect("provider metadata");
        assert!(metadata.configured);
        assert!(metadata.health.executable);
        assert_eq!(metadata.health.reachable, Some(true));
        assert_eq!(metadata.health.latency_ms, Some(42));

        let serialized = serde_json::to_value(metadata).expect("serialize provider metadata");
        assert_eq!(serialized["cache_status"], "fresh");
        assert!(serialized.get("api_key").is_none());
        assert!(serialized.get("secret").is_none());
    }

    #[test]
    fn provider_test_response_preserves_open_circuit_metadata() {
        let raw = json!({
            "provider": "openai",
            "success": false,
            "error": "Provider health circuit is open",
            "cached": true,
            "circuit_state": "open",
            "consecutive_failures": 3,
            "next_probe_at": 4000
        });
        let response: TestProviderResponse = serde_json::from_value(raw).expect("test response");
        assert!(!response.success);
        assert!(response.cached);
        assert_eq!(response.health.circuit_state, "open");
        assert_eq!(response.health.consecutive_failures, 3);
        assert_eq!(response.health.next_probe_at, Some(4000));
    }

    fn temp_script(content: &str, name: &str) -> PathBuf {
        let root = env::temp_dir().join(format!("omni-rust-tests-{name}"));
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
                jwt_secret: "test-only-high-entropy-secret-material".to_string(),
                issuer: "https://example.supabase.co/auth/v1".to_string(),
            }),
            observability_stream_tickets: Arc::new(
                ProcessLocalObservabilityStreamTicketStore::default(),
            ),
            chat_security: Arc::new(ChatSecurityState::with_config(ChatSecurityConfig {
                max_message_chars: 8_000,
                max_body_bytes: 65_536,
                rate_limit_enabled: true,
                rate_limit_per_minute: 30,
            })),
        }
    }

    fn build_test_state_with_security(
        script_path: PathBuf,
        python_timeout_ms: u64,
        config: ChatSecurityConfig,
    ) -> AppState {
        let mut state = build_test_state(script_path, python_timeout_ms);
        state.chat_security = Arc::new(ChatSecurityState::with_config(config));
        state
    }

    fn build_service_state(port: u16, timeout_ms: u64) -> AppState {
        let mut state = build_test_state(temp_script("print('unused')\n", "service-mode"), 15_000);
        state.python_runtime = PythonRuntimeConfig {
            mode: PythonRuntimeMode::Service,
            service_host: "127.0.0.1".to_string(),
            service_port: port,
            service_timeout_ms: timeout_ms,
            fallback_to_subprocess: false,
            retry_attempts: 0,
            circuit_breaker_enabled: true,
            circuit_failure_threshold: 3,
            circuit_reset_ms: 30_000,
        };
        state
    }

    async fn mock_python_service_many(
        responses: Vec<(u16, Value)>,
    ) -> (u16, tokio::task::JoinHandle<Vec<String>>) {
        let listener = TcpListener::bind("127.0.0.1:0").await.expect("bind");
        let port = listener.local_addr().expect("addr").port();
        let handle = tokio::spawn(async move {
            let mut requests = Vec::new();
            for (status, body) in responses {
                let (mut stream, _) = listener.accept().await.expect("accept");
                let mut buf = vec![0_u8; 16_384];
                let n = stream.read(&mut buf).await.expect("read");
                requests.push(String::from_utf8_lossy(&buf[..n]).to_string());
                let response_body = serde_json::to_vec(&body).expect("body json");
                let response = format!(
                    "HTTP/1.1 {status} OK\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n",
                    response_body.len()
                );
                stream
                    .write_all(response.as_bytes())
                    .await
                    .expect("write head");
                stream.write_all(&response_body).await.expect("write body");
            }
            requests
        });
        (port, handle)
    }

    async fn mock_python_service_once(
        status: u16,
        body: Value,
    ) -> (u16, tokio::task::JoinHandle<String>) {
        let (port, handle) = mock_python_service_many(vec![(status, body)]).await;
        let single = tokio::spawn(async move {
            handle
                .await
                .expect("requests")
                .into_iter()
                .next()
                .unwrap_or_default()
        });
        (port, single)
    }

    fn test_chat_security_config() -> ChatSecurityConfig {
        ChatSecurityConfig {
            max_message_chars: 20,
            max_body_bytes: 512,
            rate_limit_enabled: false,
            rate_limit_per_minute: 30,
        }
    }

    fn chat_router(state: AppState) -> Router {
        Router::new()
            .route("/chat", post(chat))
            .route("/api/v1/chat", post(public_v1_chat))
            .route(
                "/api/v1/runtime/runner-smoke",
                get(public_v1_runtime_runner_smoke),
            )
            .with_state(state)
    }

    async fn response_json(response: Response) -> Value {
        let body = to_bytes(response.into_body(), usize::MAX)
            .await
            .expect("read body");
        serde_json::from_slice(&body).expect("json body")
    }

    fn json_post(path: &str, body: impl Into<Body>) -> Request<Body> {
        json_post_from(path, body, SocketAddr::from(([198, 51, 100, 10], 42_000)))
    }

    fn json_post_from(path: &str, body: impl Into<Body>, peer: SocketAddr) -> Request<Body> {
        let mut request = Request::builder()
            .method(Method::POST)
            .uri(path)
            .header(CONTENT_TYPE, "application/json")
            .body(body.into())
            .expect("request");
        request.extensions_mut().insert(ConnectInfo(peer));
        request
    }

    fn with_forwarded_for(mut request: Request<Body>, value: &str) -> Request<Body> {
        request.headers_mut().insert(
            "x-forwarded-for",
            HeaderValue::from_str(value).expect("forwarded header"),
        );
        request
    }

    fn get_request(path: &str) -> Request<Body> {
        Request::builder()
            .method(Method::GET)
            .uri(path)
            .body(Body::empty())
            .expect("request")
    }

    fn get_request_with_bearer(path: &str, token: &str) -> Request<Body> {
        Request::builder()
            .method(Method::GET)
            .uri(path)
            .header(AUTHORIZATION, format!("Bearer {token}"))
            .body(Body::empty())
            .expect("request")
    }

    fn public_status_router(state: AppState) -> Router {
        Router::new()
            .route("/health", get(health))
            .route("/api/v1/status", get(public_v1_status))
            .with_state(state)
    }

    fn with_clean_cors_env(vars: &[(&str, &str)], test: impl FnOnce()) {
        let keys = [
            "OMNI_ALLOWED_ORIGINS",
            "OMNI_PUBLIC_DEMO_MODE",
            "OMNI_ENV",
            "APP_ENV",
            "RUST_ENV",
        ];
        let env = EnvTestGuard::new(&keys);
        for key in keys {
            env.remove(key);
        }
        for (key, value) in vars {
            env.set(key, value);
        }

        test();
    }

    fn with_clean_mock_env(vars: &[(&str, &str)], test: impl FnOnce()) {
        let keys = [
            "MOCK_CHAT",
            "OMNI_ALLOW_MOCK_CHAT",
            "OMNI_PUBLIC_DEMO_MODE",
            "OMNI_ENV",
            "APP_ENV",
            "RUST_ENV",
        ];
        let env = EnvTestGuard::new(&keys);
        for key in keys {
            env.remove(key);
        }
        for (key, value) in vars {
            env.set(key, value);
        }

        test();
    }

    fn header_values_as_strings(values: &[HeaderValue]) -> Vec<String> {
        values
            .iter()
            .map(|value| value.to_str().expect("origin header").to_string())
            .collect()
    }

    #[test]
    fn mock_chat_is_rejected_without_explicit_non_live_authorization() {
        with_clean_mock_env(&[], || {
            let error =
                validate_mock_mode_for_environment(true).expect_err("mock must fail closed");
            assert!(error.to_string().contains("MOCK_CHAT is blocked"));
        });
    }

    #[test]
    fn mock_chat_is_allowed_in_local_demo_or_explicit_override() {
        with_clean_mock_env(&[("OMNI_ENV", "development")], || {
            validate_mock_mode_for_environment(true).expect("development mock");
        });
        with_clean_mock_env(&[("OMNI_PUBLIC_DEMO_MODE", "true")], || {
            validate_mock_mode_for_environment(true).expect("public demo mock");
        });
        with_clean_mock_env(&[("OMNI_ALLOW_MOCK_CHAT", "true")], || {
            validate_mock_mode_for_environment(true).expect("explicit mock override");
        });
    }

    #[tokio::test]
    async fn security_audit_internal_routes_require_supabase_auth() {
        let state = build_test_state(
            temp_script("print('{\"response\":\"unused\"}')\n", "internal-auth"),
            15_000,
        );
        let app = protected_internal_router(state.clone()).with_state(state);

        for path in [
            "/internal/runtime-signals",
            "/internal/swarm-log",
            "/internal/strategy-state",
            "/internal/milestones",
            "/internal/pr-summaries",
        ] {
            let response = app
                .clone()
                .oneshot(get_request(path))
                .await
                .expect("response");
            assert_eq!(response.status(), StatusCode::UNAUTHORIZED, "{path}");
        }
    }

    #[tokio::test]
    async fn security_audit_internal_routes_reject_invalid_bearer_token() {
        let state = build_test_state(
            temp_script(
                "print('{\"response\":\"unused\"}')\n",
                "internal-invalid-token",
            ),
            15_000,
        );
        let app = protected_internal_router(state.clone()).with_state(state);

        let response = app
            .oneshot(get_request_with_bearer(
                "/internal/runtime-signals",
                "not-a-valid-jwt",
            ))
            .await
            .expect("response");

        assert_eq!(response.status(), StatusCode::UNAUTHORIZED);
    }

    #[tokio::test]
    async fn historical_demo_key_is_rejected_by_protected_internal_route() {
        let historical_key = ["omni", "public", "demo", "local", "auth", "key"].join("-");
        let now = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .expect("unix epoch")
            .as_secs();
        let claims = json!({
            "iss": "https://example.supabase.co/auth/v1",
            "sub": "audit-reproducer",
            "aud": "authenticated",
            "exp": now + 300,
        });
        let token = encode(
            &Header::new(Algorithm::HS256),
            &claims,
            &EncodingKey::from_secret(historical_key.as_bytes()),
        )
        .expect("encode audit token");
        let state = build_test_state(
            temp_script(
                "print('{\"response\":\"unused\"}')\n",
                "historical-demo-key",
            ),
            15_000,
        );
        let app = protected_internal_router(state.clone()).with_state(state);

        let response = app
            .oneshot(get_request_with_bearer("/internal/runtime-signals", &token))
            .await
            .expect("protected route response");

        assert_eq!(response.status(), StatusCode::UNAUTHORIZED);
    }

    #[tokio::test]
    async fn security_audit_public_routes_remain_public_without_bearer_token() {
        let state = build_test_state(
            temp_script("print('{\"response\":\"unused\"}')\n", "public-routes"),
            15_000,
        );
        let app = public_status_router(state);

        for path in ["/health", "/api/v1/status"] {
            let response = app
                .clone()
                .oneshot(get_request(path))
                .await
                .expect("response");
            assert_ne!(response.status(), StatusCode::UNAUTHORIZED, "{path}");
        }
    }

    #[test]
    fn security_audit_cors_uses_canonical_allowed_origins() {
        with_clean_cors_env(
            &[(
                "OMNI_ALLOWED_ORIGINS",
                "https://app.example.com, http://localhost:5173",
            )],
            || {
                let config = resolve_cors_origin_config();
                assert_eq!(
                    header_values_as_strings(&config.origins),
                    vec![
                        "https://app.example.com".to_string(),
                        "http://localhost:5173".to_string()
                    ]
                );
                assert!(!config.wildcard);
                assert!(!config.local_defaults_applied);
            },
        );
    }

    #[test]
    fn security_audit_cors_ignores_obsolete_prefix() {
        let obsolete_name = ["OMIN", "I_ALLOWED_ORIGINS"].concat();
        let env = EnvTestGuard::new(&["OMNI_ALLOWED_ORIGINS", &obsolete_name]);
        env.remove("OMNI_ALLOWED_ORIGINS");
        env.set(&obsolete_name, "https://obsolete.example.com");

        let config = resolve_cors_origin_config();
        assert!(config.origins.is_empty());
        assert!(!config.wildcard);
    }

    #[test]
    fn security_audit_cors_is_fail_closed_without_production_origins() {
        with_clean_cors_env(&[], || {
            let config = resolve_cors_origin_config();
            assert!(config.origins.is_empty());
            assert!(!config.wildcard);
            assert!(!config.local_defaults_applied);
        });
    }

    #[test]
    fn security_audit_cors_applies_local_defaults_only_in_local_or_demo_mode() {
        with_clean_cors_env(&[("OMNI_ENV", "development")], || {
            let config = resolve_cors_origin_config();
            assert_eq!(
                header_values_as_strings(&config.origins),
                DEFAULT_LOCAL_CORS_ORIGINS
                    .iter()
                    .map(|value| value.to_string())
                    .collect::<Vec<_>>()
            );
            assert!(config.local_defaults_applied);
            assert!(!config.wildcard);
        });
    }

    #[test]
    fn security_audit_cors_blocks_wildcard_outside_demo_mode() {
        with_clean_cors_env(&[("OMNI_ALLOWED_ORIGINS", "*")], || {
            let config = resolve_cors_origin_config();
            assert!(config.origins.is_empty());
            assert!(!config.wildcard);
        });
    }

    #[test]
    fn security_audit_cors_allows_wildcard_only_in_public_demo_mode() {
        with_clean_cors_env(
            &[
                ("OMNI_ALLOWED_ORIGINS", "*"),
                ("OMNI_PUBLIC_DEMO_MODE", "true"),
            ],
            || {
                let config = resolve_cors_origin_config();
                assert!(config.origins.is_empty());
                assert!(config.wildcard);
            },
        );
    }

    async fn assert_python_not_invoked(state: &AppState) {
        let guard = state.python_health.read().await;
        assert!(!matches!(
            guard.last_status.as_str(),
            "ready" | "failed" | "timeout" | "stderr_warning" | "empty_stdout" | "mock"
        ));
    }

    #[tokio::test]
    async fn health_snapshot_reports_process_local_ticket_store_mode() {
        let state = build_test_state(
            temp_script("print('{\"response\":\"ok\"}')\n", "health-ticket-store"),
            15_000,
        );

        let snapshot = build_health_snapshot(&state).await;

        assert_eq!(
            snapshot.observability_stream_ticket_store_mode,
            "process_local"
        );
    }

    #[tokio::test]
    async fn call_python_returns_successful_response() {
        let state = build_test_state(
            temp_script("print('{\"response\":\"ok from python\"}')\n", "success"),
            15_000,
        );
        let response = call_python(&state, "hello", None, None, None)
            .await
            .expect("python success");
        assert_eq!(response.response, "ok from python");
        assert_eq!(response.source, "python-subprocess");
        assert_eq!(response.stop_reason.as_deref(), Some("python_completed"));
    }

    #[tokio::test]
    async fn chat_route_valid_request_invokes_runtime() {
        let state = build_test_state_with_security(
            temp_script("print('{\"response\":\"ok\"}')\n", "chat-valid"),
            15_000,
            test_chat_security_config(),
        );
        let response = chat_router(state)
            .oneshot(json_post(
                "/chat",
                r#"{"message":"hello","client_session_id":"sess-1","request_id":"req:1"}"#,
            ))
            .await
            .expect("response");
        assert_eq!(response.status(), StatusCode::OK);
        let body = response_json(response).await;
        assert_eq!(body["response"].as_str(), Some("ok"));
        assert_eq!(body["client_session_id"].as_str(), Some("sess-1"));
    }

    #[tokio::test]
    async fn runner_smoke_route_returns_safe_fields_only() {
        let script = r#"import json
import sys

_ = sys.stdin.read()
print(json.dumps({
    "status": "ok",
    "selected_runtime": "node",
    "cwd_label": "app",
    "runner_exists": True,
    "adapter_exists": True,
    "fusion_brain_exists": True,
    "contract_exists": True,
    "runner_exit_code": 0,
    "stdout_json_valid": True,
    "result_degraded": False,
    "public_failure_class": None,
    "public_summary": "runner_smoke_ok",
    "stdout": "sk-test-secret Authorization raw response stack trace",
    "env": {"OPENAI_API_KEY": "sk-test-secret"}
}))
"#;
        let state = build_test_state(temp_script(script, "runner-smoke-safe"), 15_000);
        let response = chat_router(state)
            .oneshot(get_request("/api/v1/runtime/runner-smoke"))
            .await
            .expect("runner smoke route");
        assert_eq!(response.status(), StatusCode::OK);
        let payload = response_json(response).await;

        assert_eq!(payload["api_version"].as_str(), Some("1"));
        assert_eq!(payload["status"].as_str(), Some("ok"));
        assert_eq!(payload["selected_runtime"].as_str(), Some("node"));
        assert_eq!(payload["cwd_label"].as_str(), Some("app"));
        assert_eq!(payload["runner_exists"].as_bool(), Some(true));
        assert_eq!(payload["adapter_exists"].as_bool(), Some(true));
        assert_eq!(payload["fusion_brain_exists"].as_bool(), Some(true));
        assert_eq!(payload["contract_exists"].as_bool(), Some(true));
        assert_eq!(payload["runner_exit_code"].as_i64(), Some(0));
        assert_eq!(payload["stdout_json_valid"].as_bool(), Some(true));
        assert_eq!(payload["result_degraded"].as_bool(), Some(false));
        assert_eq!(payload["public_summary"].as_str(), Some("runner_smoke_ok"));

        let serialized = serde_json::to_string(&payload).expect("json");
        assert!(!serialized.contains("stderr"));
        assert!(!serialized.contains("env"));
        assert!(!serialized.contains("sk-test-secret"));
        assert!(!serialized.contains("Authorization"));
        assert!(!serialized.contains("raw response"));
        assert!(!serialized.contains("stack trace"));
    }

    #[tokio::test]
    async fn chat_route_rejects_empty_message_before_runtime() {
        let state = build_test_state_with_security(
            temp_script("print('{\"response\":\"should-not-run\"}')\n", "chat-empty"),
            15_000,
            test_chat_security_config(),
        );
        let response = chat_router(state.clone())
            .oneshot(json_post("/chat", r#"{"message":"   "}"#))
            .await
            .expect("response");
        assert_eq!(response.status(), StatusCode::BAD_REQUEST);
        let body = response_json(response).await;
        assert_eq!(
            body["error_public_code"].as_str(),
            Some("INPUT_VALIDATION_FAILED")
        );
        assert_python_not_invoked(&state).await;
    }

    #[tokio::test]
    async fn chat_route_rejects_oversized_message_and_body_before_runtime() {
        let state = build_test_state_with_security(
            temp_script(
                "print('{\"response\":\"should-not-run\"}')\n",
                "chat-oversized",
            ),
            15_000,
            ChatSecurityConfig {
                max_message_chars: 5,
                max_body_bytes: 32,
                rate_limit_enabled: false,
                rate_limit_per_minute: 30,
            },
        );
        let response = chat_router(state.clone())
            .oneshot(json_post("/chat", r#"{"message":"too long"}"#))
            .await
            .expect("response");
        assert_eq!(response.status(), StatusCode::PAYLOAD_TOO_LARGE);
        let body = response_json(response).await;
        assert_eq!(
            body["error_public_code"].as_str(),
            Some("PAYLOAD_TOO_LARGE")
        );

        let response = chat_router(state.clone())
            .oneshot(json_post(
                "/chat",
                format!(r#"{{"message":"{}"}}"#, "x".repeat(64)),
            ))
            .await
            .expect("response");
        assert_eq!(response.status(), StatusCode::PAYLOAD_TOO_LARGE);
        assert_python_not_invoked(&state).await;
    }

    #[tokio::test]
    async fn chat_route_rejects_invalid_json_and_content_type_before_runtime() {
        let state = build_test_state_with_security(
            temp_script(
                "print('{\"response\":\"should-not-run\"}')\n",
                "chat-invalid-json",
            ),
            15_000,
            test_chat_security_config(),
        );
        let response = chat_router(state.clone())
            .oneshot(json_post("/chat", "not-json"))
            .await
            .expect("response");
        assert_eq!(response.status(), StatusCode::BAD_REQUEST);
        let body = response_json(response).await;
        assert_eq!(body["error_public_code"].as_str(), Some("INVALID_JSON"));

        let response = chat_router(state.clone())
            .oneshot(
                Request::builder()
                    .method(Method::POST)
                    .uri("/chat")
                    .header(CONTENT_TYPE, "text/plain")
                    .body(Body::from(r#"{"message":"hello"}"#))
                    .expect("request"),
            )
            .await
            .expect("response");
        assert_eq!(response.status(), StatusCode::UNSUPPORTED_MEDIA_TYPE);
        let body = response_json(response).await;
        assert_eq!(
            body["error_public_code"].as_str(),
            Some("INVALID_CONTENT_TYPE")
        );
        assert_python_not_invoked(&state).await;
    }

    #[tokio::test]
    async fn chat_route_rejects_unsafe_control_chars_and_ids() {
        let state = build_test_state_with_security(
            temp_script(
                "print('{\"response\":\"should-not-run\"}')\n",
                "chat-control",
            ),
            15_000,
            test_chat_security_config(),
        );
        let response = chat_router(state.clone())
            .oneshot(json_post("/chat", "{\"message\":\"bad\\u0000value\"}"))
            .await
            .expect("response");
        assert_eq!(response.status(), StatusCode::BAD_REQUEST);

        let response = chat_router(state.clone())
            .oneshot(json_post(
                "/chat",
                r#"{"message":"ok","client_session_id":"bad/id"}"#,
            ))
            .await
            .expect("response");
        assert_eq!(response.status(), StatusCode::BAD_REQUEST);

        let response = chat_router(state.clone())
            .oneshot(json_post(
                "/chat",
                r#"{"message":"ok","request_id":"bad id"}"#,
            ))
            .await
            .expect("response");
        assert_eq!(response.status(), StatusCode::BAD_REQUEST);
        assert_python_not_invoked(&state).await;
    }

    #[tokio::test]
    async fn chat_route_allows_tab_and_newline_in_message() {
        let state = build_test_state_with_security(
            temp_script("print('{\"response\":\"ok\"}')\n", "chat-control-safe"),
            15_000,
            test_chat_security_config(),
        );
        let response = chat_router(state)
            .oneshot(json_post("/chat", "{\"message\":\"hello\\n\\tworld\"}"))
            .await
            .expect("response");
        assert_eq!(response.status(), StatusCode::OK);
    }

    fn rate_limit_state(enabled: bool, per_minute: usize, max_clients: usize) -> ChatSecurityState {
        let mut state = ChatSecurityState::with_config(ChatSecurityConfig {
            max_message_chars: 20,
            max_body_bytes: 512,
            rate_limit_enabled: enabled,
            rate_limit_per_minute: per_minute,
        });
        state.rate_limit_max_clients = max_clients;
        state
    }

    #[test]
    fn rate_limiter_prunes_expired_buckets_before_capacity_check() {
        let state = rate_limit_state(true, 1, 1);
        let now = Instant::now();
        let expired = now - Duration::from_secs(60);
        assert!(state.check_rate_limit("198.51.100.1".parse().unwrap(), expired));
        assert!(state.check_rate_limit("198.51.100.2".parse().unwrap(), now));
        let guard = state.rate_limiter.lock().unwrap();
        assert_eq!(guard.len(), 1);
        assert!(guard.contains_key(&"198.51.100.2".parse().unwrap()));
    }

    #[test]
    fn rate_limiter_rejects_new_client_at_capacity_without_eviction() {
        let state = rate_limit_state(true, 2, 1);
        let now = Instant::now();
        let existing: IpAddr = "198.51.100.1".parse().unwrap();
        let newcomer: IpAddr = "198.51.100.2".parse().unwrap();
        assert!(state.check_rate_limit(existing, now));
        assert!(!state.check_rate_limit(newcomer, now));
        assert!(state.check_rate_limit(existing, now));
        let guard = state.rate_limiter.lock().unwrap();
        assert_eq!(guard.len(), 1);
        assert!(guard.contains_key(&existing));
        assert!(!guard.contains_key(&newcomer));
    }

    #[test]
    fn disabled_rate_limiter_does_not_create_buckets() {
        let state = rate_limit_state(false, 1, 1);
        assert!(state.check_rate_limit("198.51.100.1".parse().unwrap(), Instant::now()));
        assert!(state.rate_limiter.lock().unwrap().is_empty());
    }

    #[test]
    fn concurrent_requests_for_one_client_cannot_exceed_limit() {
        use std::sync::{
            atomic::{AtomicUsize, Ordering},
            Barrier,
        };

        let state = Arc::new(rate_limit_state(true, 7, 100));
        let barrier = Arc::new(Barrier::new(32));
        let admitted = Arc::new(AtomicUsize::new(0));
        let now = Instant::now();
        let mut handles = Vec::new();
        for _ in 0..32 {
            let state = Arc::clone(&state);
            let barrier = Arc::clone(&barrier);
            let admitted = Arc::clone(&admitted);
            handles.push(std::thread::spawn(move || {
                barrier.wait();
                if state.check_rate_limit("198.51.100.1".parse().unwrap(), now) {
                    admitted.fetch_add(1, Ordering::SeqCst);
                }
            }));
        }
        for handle in handles {
            handle.join().expect("rate limit worker");
        }
        assert_eq!(admitted.load(Ordering::SeqCst), 7);
        assert_eq!(state.rate_limiter.lock().unwrap().len(), 1);
    }

    #[test]
    fn concurrent_distinct_clients_remain_isolated() {
        let state = Arc::new(rate_limit_state(true, 1, 32));
        let now = Instant::now();
        let handles: Vec<_> = (1..=16)
            .map(|last_octet| {
                let state = Arc::clone(&state);
                std::thread::spawn(move || {
                    state.check_rate_limit(
                        IpAddr::V4(std::net::Ipv4Addr::new(198, 51, 100, last_octet)),
                        now,
                    )
                })
            })
            .collect();
        assert!(handles
            .into_iter()
            .all(|handle| handle.join().expect("isolated client worker")));
        assert_eq!(state.rate_limiter.lock().unwrap().len(), 16);
    }

    #[tokio::test]
    async fn chat_routes_use_peer_buckets_and_ignore_spoofed_headers_by_default() {
        let state = build_test_state_with_security(
            temp_script("print('{\"response\":\"ok\"}')\n", "chat-peer-buckets"),
            15_000,
            ChatSecurityConfig {
                max_message_chars: 20,
                max_body_bytes: 512,
                rate_limit_enabled: true,
                rate_limit_per_minute: 1,
            },
        );
        let peer_a = SocketAddr::from(([198, 51, 100, 10], 42_000));
        let peer_b = SocketAddr::from(([198, 51, 100, 11], 42_001));
        let first = chat_router(state.clone())
            .oneshot(with_forwarded_for(
                json_post_from("/chat", r#"{"message":"one"}"#, peer_a),
                "203.0.113.1",
            ))
            .await
            .expect("first peer response");
        let spoof_changed = chat_router(state.clone())
            .oneshot(with_forwarded_for(
                json_post_from("/chat", r#"{"message":"two"}"#, peer_a),
                "203.0.113.2",
            ))
            .await
            .expect("same peer response");
        let independent = chat_router(state.clone())
            .oneshot(with_forwarded_for(
                json_post_from("/chat", r#"{"message":"three"}"#, peer_b),
                "203.0.113.1",
            ))
            .await
            .expect("second peer response");
        assert_eq!(first.status(), StatusCode::OK);
        assert_eq!(spoof_changed.status(), StatusCode::TOO_MANY_REQUESTS);
        assert_eq!(independent.status(), StatusCode::OK);
        assert_eq!(state.chat_security.rate_limiter.lock().unwrap().len(), 2);
    }

    #[tokio::test]
    async fn missing_peer_identity_fails_closed_without_runtime_invocation() {
        let state = build_test_state_with_security(
            temp_script(
                "print('{\"response\":\"should-not-run\"}')\n",
                "chat-missing-peer",
            ),
            15_000,
            test_chat_security_config(),
        );
        let request = Request::builder()
            .method(Method::POST)
            .uri("/chat")
            .header(CONTENT_TYPE, "application/json")
            .header("x-forwarded-for", "203.0.113.7")
            .body(Body::from(r#"{"message":"hello"}"#))
            .expect("request without peer");
        let response = chat_router(state.clone())
            .oneshot(request)
            .await
            .expect("missing peer response");
        assert_eq!(response.status(), StatusCode::INTERNAL_SERVER_ERROR);
        let body = response_json(response).await;
        assert_eq!(
            body["error_public_code"].as_str(),
            Some("INTERNAL_ERROR_REDACTED")
        );
        assert_python_not_invoked(&state).await;
    }

    #[tokio::test]
    async fn both_chat_routes_share_trusted_chain_resolution() {
        let mut security = rate_limit_state(true, 1, 10);
        security.trusted_proxy =
            TrustedProxyConfig::parse(true, "10.0.0.0/8", 8).expect("trusted proxy config");
        let mut state = build_test_state(
            temp_script("print('{\"response\":\"ok\"}')\n", "chat-trusted-chain"),
            15_000,
        );
        state.chat_security = Arc::new(security);
        let peer = SocketAddr::from(([10, 0, 0, 2], 42_000));
        let first = chat_router(state.clone())
            .oneshot(with_forwarded_for(
                json_post_from("/chat", r#"{"message":"one"}"#, peer),
                "198.51.100.99, 203.0.113.8, 10.0.0.3",
            ))
            .await
            .expect("legacy chat response");
        let second = chat_router(state.clone())
            .oneshot(with_forwarded_for(
                json_post_from("/api/v1/chat", r#"{"message":"two"}"#, peer),
                "192.0.2.99, 203.0.113.8, 10.0.0.3",
            ))
            .await
            .expect("v1 chat response");
        assert_eq!(first.status(), StatusCode::OK);
        assert_eq!(second.status(), StatusCode::TOO_MANY_REQUESTS);
        let guard = state.chat_security.rate_limiter.lock().unwrap();
        assert_eq!(guard.len(), 1);
        assert!(guard.contains_key(&"203.0.113.8".parse().unwrap()));
    }

    #[tokio::test]
    async fn malformed_trusted_headers_share_fail_closed_peer_bucket() {
        let mut security = rate_limit_state(true, 1, 10);
        security.trusted_proxy =
            TrustedProxyConfig::parse(true, "10.0.0.0/8", 8).expect("trusted proxy config");
        let mut state = build_test_state(
            temp_script("print('{\"response\":\"ok\"}')\n", "chat-malformed-chain"),
            15_000,
        );
        state.chat_security = Arc::new(security);
        let peer = SocketAddr::from(([10, 0, 0, 2], 42_000));
        let first = chat_router(state.clone())
            .oneshot(with_forwarded_for(
                json_post_from("/chat", r#"{"message":"one"}"#, peer),
                "203.0.113.1,,10.0.0.3",
            ))
            .await
            .expect("first malformed response");
        let second = chat_router(state.clone())
            .oneshot(with_forwarded_for(
                json_post_from("/chat", r#"{"message":"two"}"#, peer),
                "attacker-selected-value",
            ))
            .await
            .expect("second malformed response");
        assert_eq!(first.status(), StatusCode::OK);
        assert_eq!(second.status(), StatusCode::TOO_MANY_REQUESTS);
        let guard = state.chat_security.rate_limiter.lock().unwrap();
        assert_eq!(guard.len(), 1);
        assert!(guard.contains_key(&"10.0.0.2".parse().unwrap()));
    }

    #[tokio::test]
    async fn capacity_rejection_does_not_invoke_runtime() {
        let mut security = rate_limit_state(true, 30, 1);
        assert!(security.check_rate_limit("198.51.100.1".parse().unwrap(), Instant::now()));
        let mut state = build_test_state(
            temp_script(
                "print('{\"response\":\"should-not-run\"}')\n",
                "chat-capacity-block",
            ),
            15_000,
        );
        security.trusted_proxy = TrustedProxyConfig::direct_only();
        state.chat_security = Arc::new(security);
        let response = chat_router(state.clone())
            .oneshot(json_post_from(
                "/api/v1/chat",
                r#"{"message":"blocked"}"#,
                SocketAddr::from(([198, 51, 100, 2], 42_000)),
            ))
            .await
            .expect("capacity response");
        assert_eq!(response.status(), StatusCode::TOO_MANY_REQUESTS);
        assert_eq!(state.chat_security.rate_limiter.lock().unwrap().len(), 1);
        assert_python_not_invoked(&state).await;
    }

    #[tokio::test]
    async fn chat_route_rate_limits_and_can_disable_rate_limit() {
        let enabled_state = build_test_state_with_security(
            temp_script("print('{\"response\":\"ok\"}')\n", "chat-rate-enabled"),
            15_000,
            ChatSecurityConfig {
                max_message_chars: 20,
                max_body_bytes: 512,
                rate_limit_enabled: true,
                rate_limit_per_minute: 1,
            },
        );
        let response = chat_router(enabled_state.clone())
            .oneshot(json_post("/chat", r#"{"message":"one"}"#))
            .await
            .expect("response");
        assert_eq!(response.status(), StatusCode::OK);
        let response = chat_router(enabled_state)
            .oneshot(json_post("/chat", r#"{"message":"two"}"#))
            .await
            .expect("response");
        assert_eq!(response.status(), StatusCode::TOO_MANY_REQUESTS);
        let body = response_json(response).await;
        assert_eq!(body["error_public_code"].as_str(), Some("RATE_LIMITED"));
        assert_eq!(body["retryable"].as_bool(), Some(true));

        let disabled_state = build_test_state_with_security(
            temp_script("print('{\"response\":\"ok\"}')\n", "chat-rate-disabled"),
            15_000,
            ChatSecurityConfig {
                max_message_chars: 20,
                max_body_bytes: 512,
                rate_limit_enabled: false,
                rate_limit_per_minute: 1,
            },
        );
        let response = chat_router(disabled_state.clone())
            .oneshot(json_post("/chat", r#"{"message":"one"}"#))
            .await
            .expect("response");
        assert_eq!(response.status(), StatusCode::OK);
        let response = chat_router(disabled_state)
            .oneshot(json_post("/chat", r#"{"message":"two"}"#))
            .await
            .expect("response");
        assert_eq!(response.status(), StatusCode::OK);
    }

    #[test]
    fn chat_security_canonical_env_works() {
        let keys = [
            "OMNI_MAX_MESSAGE_CHARS",
            "OMNI_MAX_BODY_BYTES",
            "OMNI_RATE_LIMIT_ENABLED",
            "OMNI_RATE_LIMIT_PER_MINUTE",
            "OMNI_RATE_LIMIT_MAX_CLIENTS",
            "OMNI_TRUST_PROXY_HEADERS",
            "OMNI_TRUSTED_PROXY_CIDRS",
            "OMNI_TRUST_PROXY_MAX_HOPS",
        ];
        let env = EnvTestGuard::new(&keys);
        for key in keys {
            env.remove(key);
        }
        env.set("OMNI_MAX_MESSAGE_CHARS", "123");
        env.set("OMNI_MAX_BODY_BYTES", "456");
        env.set("OMNI_RATE_LIMIT_ENABLED", "false");
        env.set("OMNI_RATE_LIMIT_PER_MINUTE", "7");
        let canonical = ChatSecurityState::from_env().expect("canonical chat security config");
        assert_eq!(canonical.config.max_message_chars, 123);
        assert_eq!(canonical.config.max_body_bytes, 456);
        assert!(!canonical.config.rate_limit_enabled);
        assert_eq!(canonical.config.rate_limit_per_minute, 7);
        assert_eq!(canonical.rate_limit_max_clients, 10_000);
        let default_identity = canonical.trusted_proxy.resolve(
            "10.0.0.1".parse().unwrap(),
            &HeaderMap::from_iter([(
                "x-forwarded-for".parse().unwrap(),
                HeaderValue::from_static("203.0.113.9"),
            )]),
        );
        assert_eq!(default_identity.source, ClientIdentitySource::DirectPeer);
        assert_eq!(
            default_identity.effective_ip,
            "10.0.0.1".parse::<IpAddr>().unwrap()
        );

        env.set("OMNI_MAX_MESSAGE_CHARS", "321");
        env.set("OMNI_MAX_BODY_BYTES", "654");
        env.set("OMNI_RATE_LIMIT_ENABLED", "true");
        env.set("OMNI_RATE_LIMIT_PER_MINUTE", "9");
        env.set("OMNI_RATE_LIMIT_MAX_CLIENTS", "55");
        env.set("OMNI_TRUST_PROXY_HEADERS", "true");
        env.set("OMNI_TRUSTED_PROXY_CIDRS", "10.0.0.1,2001:db8::/32");
        env.set("OMNI_TRUST_PROXY_MAX_HOPS", "4");
        let updated = ChatSecurityState::from_env().expect("updated chat security config");
        assert_eq!(updated.config.max_message_chars, 321);
        assert_eq!(updated.config.max_body_bytes, 654);
        assert!(updated.config.rate_limit_enabled);
        assert_eq!(updated.config.rate_limit_per_minute, 9);
        assert_eq!(updated.rate_limit_max_clients, 55);
        let forwarded = updated.trusted_proxy.resolve(
            "10.0.0.1".parse().unwrap(),
            &HeaderMap::from_iter([(
                "x-forwarded-for".parse().unwrap(),
                HeaderValue::from_static("203.0.113.9"),
            )]),
        );
        assert_eq!(
            forwarded.source,
            ClientIdentitySource::TrustedForwardedChain
        );
        assert_eq!(
            forwarded.effective_ip,
            "203.0.113.9".parse::<IpAddr>().unwrap()
        );
    }

    #[test]
    fn chat_security_rejects_invalid_proxy_and_capacity_environment() {
        let keys = [
            "OMNI_RATE_LIMIT_MAX_CLIENTS",
            "OMNI_TRUST_PROXY_HEADERS",
            "OMNI_TRUSTED_PROXY_CIDRS",
            "OMNI_TRUST_PROXY_MAX_HOPS",
        ];
        let env = EnvTestGuard::new(&keys);
        for key in keys {
            env.remove(key);
        }

        for value in ["0", "1000001", "not-a-number"] {
            env.set("OMNI_RATE_LIMIT_MAX_CLIENTS", value);
            assert!(ChatSecurityState::from_env().is_err());
        }
        env.remove("OMNI_RATE_LIMIT_MAX_CLIENTS");

        env.set("OMNI_TRUST_PROXY_HEADERS", "true");
        for cidrs in ["", "invalid", "0.0.0.0/0", "::/0"] {
            env.set("OMNI_TRUSTED_PROXY_CIDRS", cidrs);
            assert!(ChatSecurityState::from_env().is_err());
        }
        env.set("OMNI_TRUSTED_PROXY_CIDRS", "127.0.0.1");
        for value in ["0", "65", "not-a-number"] {
            env.set("OMNI_TRUST_PROXY_MAX_HOPS", value);
            assert!(ChatSecurityState::from_env().is_err());
        }
    }

    #[test]
    fn python_debug_logging_is_disabled_in_public_demo() {
        let keys = ["LOG_LEVEL", "OMNI_PUBLIC_DEMO_MODE", "OMNI_LOG_LEVEL"];
        let env = EnvTestGuard::new(&keys);
        for key in keys {
            env.remove(key);
        }

        env.set("OMNI_LOG_LEVEL", "debug");
        assert!(python_debug_logging_enabled());
        env.set("OMNI_PUBLIC_DEMO_MODE", "true");
        assert!(!python_debug_logging_enabled());
    }

    #[test]
    fn python_runtime_mode_canonical_env_works() {
        let keys = [
            "OMNI_PYTHON_MODE",
            "OMNI_PYTHON_SERVICE_HOST",
            "OMNI_PYTHON_SERVICE_PORT",
            "OMNI_PYTHON_SERVICE_TIMEOUT_MS",
            "OMNI_PYTHON_SERVICE_FALLBACK_TO_SUBPROCESS",
            "OMNI_PYTHON_SERVICE_RETRY_ATTEMPTS",
            "OMNI_PYTHON_SERVICE_CIRCUIT_BREAKER_ENABLED",
            "OMNI_PYTHON_SERVICE_CIRCUIT_FAILURE_THRESHOLD",
            "OMNI_PYTHON_SERVICE_CIRCUIT_RESET_MS",
        ];
        let env = EnvTestGuard::new(&keys);
        for key in keys {
            env.remove(key);
        }

        let default = PythonRuntimeConfig::from_env();
        assert_eq!(default.mode, PythonRuntimeMode::Subprocess);
        assert_eq!(default.service_host, "127.0.0.1");
        assert_eq!(default.service_port, 7010);
        assert_eq!(default.service_timeout_ms, 30_000);
        assert!(!default.fallback_to_subprocess);
        assert_eq!(default.retry_attempts, 0);
        assert!(default.circuit_breaker_enabled);
        assert_eq!(default.circuit_failure_threshold, 3);
        assert_eq!(default.circuit_reset_ms, 30_000);

        env.set("OMNI_PYTHON_MODE", "service");
        env.set("OMNI_PYTHON_SERVICE_HOST", "127.0.0.2");
        env.set("OMNI_PYTHON_SERVICE_PORT", "7011");
        env.set("OMNI_PYTHON_SERVICE_TIMEOUT_MS", "1234");
        env.set("OMNI_PYTHON_SERVICE_FALLBACK_TO_SUBPROCESS", "true");
        env.set("OMNI_PYTHON_SERVICE_RETRY_ATTEMPTS", "9");
        env.set("OMNI_PYTHON_SERVICE_CIRCUIT_BREAKER_ENABLED", "false");
        env.set("OMNI_PYTHON_SERVICE_CIRCUIT_FAILURE_THRESHOLD", "2");
        env.set("OMNI_PYTHON_SERVICE_CIRCUIT_RESET_MS", "4567");
        let configured = PythonRuntimeConfig::from_env();
        assert_eq!(configured.mode, PythonRuntimeMode::Service);
        assert_eq!(configured.service_host, "127.0.0.2");
        assert_eq!(configured.service_port, 7011);
        assert_eq!(configured.service_timeout_ms, 1234);
        assert!(configured.fallback_to_subprocess);
        assert_eq!(configured.retry_attempts, 3);
        assert!(!configured.circuit_breaker_enabled);
        assert_eq!(configured.circuit_failure_threshold, 2);
        assert_eq!(configured.circuit_reset_ms, 4567);

        env.set("OMNI_PYTHON_MODE", "subprocess");
        env.set("OMNI_PYTHON_SERVICE_HOST", "127.0.0.3");
        env.set("OMNI_PYTHON_SERVICE_PORT", "7012");
        env.set("OMNI_PYTHON_SERVICE_TIMEOUT_MS", "4321");
        env.set("OMNI_PYTHON_SERVICE_FALLBACK_TO_SUBPROCESS", "false");
        env.set("OMNI_PYTHON_SERVICE_RETRY_ATTEMPTS", "1");
        env.set("OMNI_PYTHON_SERVICE_CIRCUIT_BREAKER_ENABLED", "true");
        env.set("OMNI_PYTHON_SERVICE_CIRCUIT_FAILURE_THRESHOLD", "5");
        env.set("OMNI_PYTHON_SERVICE_CIRCUIT_RESET_MS", "9876");
        let canonical = PythonRuntimeConfig::from_env();
        assert_eq!(canonical.mode, PythonRuntimeMode::Subprocess);
        assert_eq!(canonical.service_host, "127.0.0.3");
        assert_eq!(canonical.service_port, 7012);
        assert_eq!(canonical.service_timeout_ms, 4321);
        assert!(!canonical.fallback_to_subprocess);
        assert_eq!(canonical.retry_attempts, 1);
        assert!(canonical.circuit_breaker_enabled);
        assert_eq!(canonical.circuit_failure_threshold, 5);
        assert_eq!(canonical.circuit_reset_ms, 9876);

        env.set("OMNI_PYTHON_MODE", "invalid");
        assert_eq!(
            PythonRuntimeConfig::from_env().mode,
            PythonRuntimeMode::Subprocess
        );

        env.set("OMNI_PYTHON_MODE", "   ");
        assert_eq!(
            PythonRuntimeConfig::from_env().mode,
            PythonRuntimeMode::Subprocess
        );
    }

    #[tokio::test]
    async fn service_mode_sends_expected_json_and_preserves_public_envelope() {
        let (port, handle) = mock_python_service_once(
            200,
            json!({
                "response": "ok from service",
                "conversation_id": "conv-service",
                "cognitive_runtime_inspection": {
                    "runtime_mode": "FULL_COGNITIVE_RUNTIME",
                    "runtime_truth": {
                        "runtime_mode": "FULL_COGNITIVE_RUNTIME",
                        "fallback_triggered": false
                    }
                },
                "error_public_code": "RULE_BASED_INTENT_USED",
                "error_public_message": "Intent was classified by deterministic rules.",
                "severity": "info",
                "retryable": false,
                "internal_error_redacted": true,
                "providers": ["openai"]
            }),
        )
        .await;
        let state = build_service_state(port, 5_000);
        let response = call_python(
            &state,
            "hello",
            Some("sess-1".to_string()),
            Some("req-1".to_string()),
            Some(&json!({"source": "frontend"})),
        )
        .await
        .expect("service response");
        let request = handle.await.expect("service request");

        assert!(request.starts_with("POST /internal/brain/run HTTP/1.1"));
        assert!(request.contains("\"message\":\"hello\""));
        assert!(request.contains("\"session_id\":\"sess-1\""));
        assert!(request.contains("\"request_id\":\"req-1\""));
        assert!(request.contains("\"metadata\":{\"source\":\"frontend\"}"));
        assert_eq!(response.response, "ok from service");
        assert_eq!(response.source, "python-service");
        assert_eq!(response.conversation_id.as_deref(), Some("conv-service"));
        assert_eq!(
            response
                .cognitive_runtime_inspection
                .as_ref()
                .and_then(|v| v.get("runtime_mode"))
                .and_then(Value::as_str),
            Some("FULL_COGNITIVE_RUNTIME")
        );
        assert_eq!(response.providers, Some(vec!["openai".to_string()]));
        assert_eq!(
            response
                .error
                .as_ref()
                .and_then(|v| v.get("error_public_code"))
                .and_then(Value::as_str),
            Some("RULE_BASED_INTENT_USED")
        );
    }

    #[tokio::test]
    async fn service_mode_unavailable_and_timeout_are_public_safe() {
        let unavailable_listener = TcpListener::bind("127.0.0.1:0").await.expect("bind");
        let unavailable_port = unavailable_listener.local_addr().expect("addr").port();
        let _unavailable_handle = tokio::spawn(async move {
            let (_stream, _) = unavailable_listener.accept().await.expect("accept");
        });
        let state = build_service_state(unavailable_port, 1_000);
        let response = call_python(&state, "hello", None, None, None)
            .await
            .expect("fallback");
        assert_eq!(response.source, "python-service");
        assert_eq!(
            response.stop_reason.as_deref(),
            Some("python_service_unavailable")
        );
        assert_eq!(
            response
                .error
                .as_ref()
                .and_then(|v| v.get("failure_class"))
                .and_then(Value::as_str),
            Some("PYTHON_ORCHESTRATOR_FAILED")
        );
        let serialized = serde_json::to_string(&response).expect("serialize");
        assert!(!serialized.contains("stack"));
        assert!(!serialized.contains("token"));
        assert!(!serialized.contains("/home/"));

        let listener = TcpListener::bind("127.0.0.1:0").await.expect("bind");
        let port = listener.local_addr().expect("addr").port();
        let _handle = tokio::spawn(async move {
            let (_stream, _) = listener.accept().await.expect("accept");
            tokio::time::sleep(Duration::from_millis(250)).await;
        });
        let timeout_state = build_service_state(port, 25);
        let timeout_response = call_python(&timeout_state, "hello", None, None, None)
            .await
            .expect("timeout fallback");
        assert_eq!(
            timeout_response.stop_reason.as_deref(),
            Some("python_service_timeout")
        );
        assert_eq!(
            timeout_response
                .error
                .as_ref()
                .and_then(|v| v.get("failure_class"))
                .and_then(Value::as_str),
            Some("TIMEOUT")
        );
    }

    #[tokio::test]
    async fn service_retry_is_bounded_and_can_recover() {
        let (port, handle) = mock_python_service_many(vec![
            (500, json!({"response": "fail"})),
            (200, json!({"response": "ok after retry"})),
        ])
        .await;
        let mut state = build_service_state(port, 5_000);
        state.python_runtime.retry_attempts = 1;
        state.python_runtime.circuit_failure_threshold = 10;

        let response = call_python(&state, "hello", None, None, None)
            .await
            .expect("retry response");
        let requests = handle.await.expect("requests");
        assert_eq!(requests.len(), 2);
        assert_eq!(response.response, "ok after retry");
        assert_eq!(
            state.python_circuit.lock().expect("circuit").state,
            CircuitBreakerState::Closed
        );
    }

    #[tokio::test]
    async fn service_failure_optionally_falls_back_to_subprocess() {
        let (port, _handle) =
            mock_python_service_once(500, json!({"response": "service failed"})).await;
        let script = r#"print('{"response":"ok from subprocess","cognitive_runtime_inspection":{"runtime_mode":"FULL_COGNITIVE_RUNTIME"}}')"#;
        let mut state = build_test_state(temp_script(script, "service-fallback"), 15_000);
        state.python_runtime = PythonRuntimeConfig {
            mode: PythonRuntimeMode::Service,
            service_host: "127.0.0.1".to_string(),
            service_port: port,
            service_timeout_ms: 5_000,
            fallback_to_subprocess: true,
            retry_attempts: 0,
            circuit_breaker_enabled: true,
            circuit_failure_threshold: 3,
            circuit_reset_ms: 30_000,
        };

        let response = call_python(&state, "hello", None, None, None)
            .await
            .expect("fallback response");
        assert_eq!(response.response, "ok from subprocess");
        assert_eq!(response.source, "python-service-subprocess-fallback");
        let inspection = response.cognitive_runtime_inspection.expect("inspection");
        assert_eq!(inspection["runtime_mode"].as_str(), Some("SAFE_FALLBACK"));
        assert_eq!(inspection["fallback_triggered"].as_bool(), Some(true));
        assert_eq!(inspection["service_mode_attempted"].as_bool(), Some(true));
        assert_eq!(inspection["service_fallback_used"].as_bool(), Some(true));
        assert_ne!(
            inspection["runtime_mode"].as_str(),
            Some("FULL_COGNITIVE_RUNTIME")
        );
    }

    #[tokio::test]
    async fn service_failure_without_fallback_does_not_invoke_subprocess() {
        let (port, _handle) =
            mock_python_service_once(500, json!({"response": "service failed"})).await;
        let mut state = build_service_state(port, 5_000);
        state.python_entry = temp_script(
            "print('{\"response\":\"should-not-run\"}')\n",
            "no-fallback",
        );
        state.python_runtime.fallback_to_subprocess = false;

        let response = call_python(&state, "hello", None, None, None)
            .await
            .expect("service failure response");
        assert_eq!(response.response, PYTHON_FALLBACK_RESPONSE);
        assert_eq!(response.source, "python-service");
        assert_eq!(
            response.stop_reason.as_deref(),
            Some("python_service_unavailable")
        );
    }

    #[tokio::test]
    async fn circuit_opens_skips_service_and_half_open_transitions() {
        let (port, handle) = mock_python_service_many(vec![
            (500, json!({"response": "fail-1"})),
            (500, json!({"response": "fail-2"})),
            (200, json!({"response": "probe ok"})),
        ])
        .await;
        let mut state = build_service_state(port, 5_000);
        state.python_runtime.circuit_failure_threshold = 2;
        state.python_runtime.circuit_reset_ms = 1_000;

        let first = call_python(&state, "hello", None, None, None)
            .await
            .expect("first failure");
        assert_eq!(
            first
                .error
                .as_ref()
                .and_then(|v| v.get("failure_class"))
                .and_then(Value::as_str),
            Some("PYTHON_ORCHESTRATOR_FAILED")
        );

        let second = call_python(&state, "hello", None, None, None)
            .await
            .expect("second failure");
        assert_eq!(
            second
                .cognitive_runtime_inspection
                .as_ref()
                .and_then(|v| v.get("circuit_breaker_state"))
                .and_then(Value::as_str),
            Some("OPEN")
        );

        let skipped = call_python(&state, "hello", None, None, None)
            .await
            .expect("open circuit skip");
        assert_eq!(
            skipped
                .cognitive_runtime_inspection
                .as_ref()
                .and_then(|v| v.get("circuit_breaker_state"))
                .and_then(Value::as_str),
            Some("OPEN")
        );

        {
            let mut circuit = state.python_circuit.lock().expect("circuit");
            circuit.opened_at = Some(Instant::now() - Duration::from_millis(2_000));
        }
        let probe = call_python(&state, "hello", None, None, None)
            .await
            .expect("half-open probe");
        assert_eq!(probe.response, "probe ok");
        assert_eq!(
            state.python_circuit.lock().expect("circuit").state,
            CircuitBreakerState::Closed
        );
        let requests = handle.await.expect("requests");
        assert_eq!(requests.len(), 3);
    }

    #[tokio::test]
    async fn half_open_failure_reopens_circuit() {
        let (port, _handle) =
            mock_python_service_once(500, json!({"response": "probe failed"})).await;
        let mut state = build_service_state(port, 5_000);
        state.python_runtime.circuit_failure_threshold = 1;
        state.python_runtime.circuit_reset_ms = 1;
        {
            let mut circuit = state.python_circuit.lock().expect("circuit");
            circuit.state = CircuitBreakerState::Open;
            circuit.opened_at = Some(Instant::now() - Duration::from_millis(50));
        }

        let response = call_python(&state, "hello", None, None, None)
            .await
            .expect("half-open failure");
        assert_eq!(
            response
                .cognitive_runtime_inspection
                .as_ref()
                .and_then(|v| v.get("circuit_breaker_state"))
                .and_then(Value::as_str),
            Some("OPEN")
        );
        assert_eq!(
            state.python_circuit.lock().expect("circuit").state,
            CircuitBreakerState::Open
        );
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
        let response = call_python(&state, "hello", Some("sess-9".to_string()), None, None)
            .await
            .expect("python stdin bridge");
        assert_eq!(response.response, "msg=hello;cid=sess-9;rsv=1");
        assert_eq!(response.client_session_id.as_deref(), Some("sess-9"));
    }

    #[tokio::test]
    async fn chat_route_does_not_echo_session_byok_key() {
        let script = r#"import json,sys
d=json.loads(sys.stdin.read())
ctx=d.get("client_context") or {}
creds=ctx.get("session_provider_credentials") or {}
seen=bool((creds.get("openai") or {}).get("api_key"))
print(json.dumps({"response": "byok_seen=" + str(seen).lower()}))
"#;
        let state = build_test_state(temp_script(script, "byok-private"), 15_000);
        let response = chat_router(state)
            .oneshot(json_post(
                "/chat",
                r#"{"message":"hello","provider_preference":"openai","session_provider_credentials":{"openai":{"api_key":"test-byok-key","model":"gpt-4o-mini"}}}"#,
            ))
            .await
            .expect("response");
        assert_eq!(response.status(), StatusCode::OK);
        let body = response_json(response).await;
        let body_text = serde_json::to_string(&body).unwrap();
        assert_eq!(body["response"].as_str(), Some("byok_seen=true"));
        assert!(!body_text.contains("test-byok-key"));
        assert!(!body_text.contains("gpt-4o-mini"));
        assert!(body.get("session_provider_credentials").is_none());
    }

    #[tokio::test]
    async fn chat_route_rejects_invalid_session_byok_without_echoing_secret_material() {
        let state = build_test_state(temp_script("print('{}')", "byok-invalid"), 15_000);
        let response = chat_router(state)
            .oneshot(json_post(
                "/chat",
                r#"{"message":"hello","provider_preference":"openai","session_provider_credentials":{"deepseek":{"api_key":"sk-test-byok-session-openai","model":"byok-test-model"}}}"#,
            ))
            .await
            .expect("response");
        assert_eq!(response.status(), StatusCode::BAD_REQUEST);
        let body = response_json(response).await;
        let body_text = serde_json::to_string(&body).unwrap();
        assert!(!body_text.contains("sk-test-byok-session-openai"));
        assert!(!body_text.contains("byok-test-model"));
        assert!(body.is_object());
        assert!(body.get("session_provider_credentials").is_none());
    }

    #[test]
    fn build_python_stdin_json_includes_optional_client_session() {
        let v = build_python_stdin_json("hi", &Some("c1".into()), &Some("r1".into()), 42, None);
        let parsed: Value = serde_json::from_slice(&v).expect("json");
        assert_eq!(parsed["message"].as_str(), Some("hi"));
        assert_eq!(parsed["client_session_id"].as_str(), Some("c1"));
        assert_eq!(parsed["request_id"].as_str(), Some("r1"));
        assert_eq!(parsed["runtime_session_version"].as_u64(), Some(42));
        assert_eq!(parsed["request_source"].as_str(), Some("rust_boundary"));
        let v2 = build_python_stdin_json("x", &None, &None, 0, None);
        let p2: Value = serde_json::from_slice(&v2).unwrap();
        assert!(p2.get("client_session_id").is_none());
    }

    #[test]
    fn build_python_stdin_json_includes_optional_client_context() {
        let ctx = json!({"source": "frontend"});
        let v = build_python_stdin_json("m", &None, &None, 3, Some(&ctx));
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
    fn extract_chat_from_python_output_uses_truthful_runtime_session_id() {
        let raw = r#"{"response":"hi","runtime_session_id":"runtime-session-1"}"#;
        let parsed = extract_chat_from_python_output(raw);
        assert_eq!(
            parsed.runtime_session_id.as_deref(),
            Some("runtime-session-1")
        );

        let invalid = extract_chat_from_python_output(
            r#"{"response":"hi","runtime_session_id":"bad\nsession"}"#,
        );
        assert!(invalid.runtime_session_id.is_none());
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
        let raw =
            r#"{"message":"hi","client_session_id":"s1","client_context":{"source":"frontend"}}"#;
        let p: PublicChatRequestV1 = serde_json::from_str(raw).expect("deserialize");
        assert_eq!(p.message, "hi");
        assert_eq!(p.client_session_id.as_deref(), Some("s1"));
        let ctx = p.client_context.expect("context");
        assert_eq!(ctx.source.as_deref(), Some("frontend"));
    }

    #[test]
    fn chat_request_deserializes_typed_session_provider_credentials() {
        let raw = r#"{"message":"hi","provider_preference":"openai","session_provider_credentials":{"openai":{"api_key":"test-byok-key","model":"gpt-4o-mini"}}}"#;
        let p: ChatRequest = serde_json::from_str(raw).expect("deserialize");
        assert_eq!(p.provider_preference.as_deref(), Some("openai"));
        let credentials = p.session_provider_credentials.expect("credentials");
        assert_eq!(
            credentials
                .get("openai")
                .and_then(|item| item.model.as_deref()),
            Some("gpt-4o-mini")
        );
    }

    #[test]
    fn session_provider_credentials_reject_unknown_fields() {
        let raw = r#"{"message":"hi","session_provider_credentials":{"openai":{"api_key":"test-byok-key","extra":"nope"}}}"#;
        assert!(serde_json::from_str::<ChatRequest>(raw).is_err());
    }

    #[test]
    fn session_byok_validation_rejects_unknown_provider_and_deepseek() {
        let mut unknown = BTreeMap::new();
        unknown.insert(
            "notreal".to_string(),
            SessionProviderCredential {
                api_key: Some("test-byok-key".to_string()),
                model: None,
            },
        );
        assert!(validate_session_provider_credentials(Some(unknown)).is_err());

        let mut deepseek = BTreeMap::new();
        deepseek.insert(
            "deepseek".to_string(),
            SessionProviderCredential {
                api_key: Some("test-byok-key".to_string()),
                model: None,
            },
        );
        assert!(validate_session_provider_credentials(Some(deepseek)).is_err());
    }

    #[test]
    fn session_byok_validation_rejects_oversized_and_control_chars() {
        let mut too_long = BTreeMap::new();
        too_long.insert(
            "openai".to_string(),
            SessionProviderCredential {
                api_key: Some("x".repeat(BYOK_MAX_API_KEY_CHARS + 1)),
                model: None,
            },
        );
        assert!(validate_session_provider_credentials(Some(too_long)).is_err());

        let mut control = BTreeMap::new();
        control.insert(
            "openai".to_string(),
            SessionProviderCredential {
                api_key: Some("bad\u{0000}key".to_string()),
                model: None,
            },
        );
        assert!(validate_session_provider_credentials(Some(control)).is_err());
    }

    #[test]
    fn build_python_stdin_json_forwards_private_byok_bridge_fields() {
        let mut credentials = BTreeMap::new();
        credentials.insert(
            "openai".to_string(),
            SessionProviderCredential {
                api_key: Some("test-byok-key".to_string()),
                model: Some("gpt-4o-mini".to_string()),
            },
        );
        let context = build_private_bridge_context(
            Some(json!({"source": "frontend"})),
            &Some("openai".to_string()),
            &Some(credentials),
        )
        .expect("context");
        let v = build_python_stdin_json("m", &None, &None, 3, Some(&context));
        let parsed: Value = serde_json::from_slice(&v).unwrap();
        assert_eq!(
            parsed["client_context"]["provider_preference"].as_str(),
            Some("openai")
        );
        assert_eq!(
            parsed["client_context"]["session_provider_credentials"]["openai"]["api_key"].as_str(),
            Some("test-byok-key")
        );
    }

    #[test]
    fn build_python_stdin_json_forwards_byok_model_without_public_response_echo() {
        let mut credentials = BTreeMap::new();
        credentials.insert(
            "openai".to_string(),
            SessionProviderCredential {
                api_key: Some("sk-test-byok-session-openai".to_string()),
                model: Some("byok-test-model".to_string()),
            },
        );
        let context =
            build_private_bridge_context(None, &Some("openai".to_string()), &Some(credentials))
                .expect("context");
        let v = build_python_stdin_json("m", &None, &None, 3, Some(&context));
        let parsed: Value = serde_json::from_slice(&v).unwrap();

        assert_eq!(
            parsed["client_context"]["provider_preference"].as_str(),
            Some("openai")
        );
        assert_eq!(
            parsed["client_context"]["session_provider_credentials"]["openai"]["model"].as_str(),
            Some("byok-test-model")
        );

        let public = ChatResponse {
            response: "ok".to_string(),
            session_id: "python-session".to_string(),
            source: "python-subprocess".to_string(),
            runtime_session_version: 1,
            client_session_id: None,
            matched_commands: vec![],
            matched_tools: vec![],
            stop_reason: Some("completed".to_string()),
            usage: None,
            conversation_id: None,
            cognitive_runtime_inspection: None,
            providers: None,
            error: None,
        };
        let public_text = serde_json::to_string(&public).unwrap();
        assert!(!public_text.contains("sk-test-byok-session-openai"));
        assert!(!public_text.contains("byok-test-model"));
        assert!(!public_text.contains("session_provider_credentials"));
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
                error: None,
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
                error: None,
            },
        };
        let v = serde_json::to_value(&body).expect("serialize");
        assert_eq!(v["providers"], json!(["openai", "groq"]));
    }

    #[tokio::test]
    async fn call_python_returns_timeout_fallback() {
        let state = build_test_state(
            temp_script("import time\ntime.sleep(2)\nprint('late')\n", "timeout"),
            200,
        );
        let response = call_python(&state, "hello", None, None, None)
            .await
            .expect("timeout fallback expected");
        assert_eq!(response.response, PYTHON_FALLBACK_RESPONSE);
        assert_eq!(response.source, "python-subprocess");
        assert_eq!(
            response.stop_reason.as_deref(),
            Some("python_subprocess_timeout")
        );
        assert!(response.cognitive_runtime_inspection.is_some());
        assert_eq!(
            response
                .error
                .as_ref()
                .and_then(|e| e.get("failure_class"))
                .and_then(Value::as_str),
            Some("PYTHON_BRIDGE_NONZERO_EXIT")
        );
    }

    #[tokio::test]
    async fn call_python_returns_stderr_fallback() {
        let state = build_test_state(
            temp_script(
                "import sys\nsys.stderr.write('boom')\nsys.exit(1)\n",
                "stderr",
            ),
            15_000,
        );
        let response = call_python(&state, "hello", None, None, None)
            .await
            .expect("stderr fallback expected");
        assert_eq!(response.response, PYTHON_FALLBACK_RESPONSE);
        assert_eq!(response.source, "python-subprocess");
        assert_eq!(
            response.stop_reason.as_deref(),
            Some("python_subprocess_nonzero_exit")
        );
        assert!(response.cognitive_runtime_inspection.is_some());
        assert_eq!(
            response
                .error
                .as_ref()
                .and_then(|e| e.get("failure_class"))
                .and_then(Value::as_str),
            Some("PYTHON_BRIDGE_NONZERO_EXIT")
        );
    }

    #[test]
    fn public_demo_fallback_redacts_internal_detail() {
        let keys = ["OMNI_PUBLIC_DEMO_MODE"];
        let env = EnvTestGuard::new(&keys);
        env.set("OMNI_PUBLIC_DEMO_MODE", "true");
        let state = build_test_state(temp_script("print('ok')\n", "public-redaction"), 15_000);

        let response = build_python_fallback_response(
            &state,
            "python-subprocess",
            None,
            "python_subprocess_nonzero_exit",
            Some("Traceback: /home/runner/work/private.py Authorization: Bearer secret"),
        );
        let serialized = serde_json::to_string(&response).expect("serialize");

        assert!(!serialized.contains("Traceback"));
        assert!(!serialized.contains("/home/runner/work"));
        assert!(!serialized.contains("Authorization"));
        assert!(!serialized.contains("secret"));
        assert!(response
            .cognitive_runtime_inspection
            .as_ref()
            .and_then(|value| value.get("detail"))
            .is_none());
        assert!(response
            .error
            .as_ref()
            .and_then(|value| value.get("detail"))
            .is_none());
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
        let response = call_python(&state, "hello", None, None, None)
            .await
            .expect("python success");
        assert_eq!(response.response, "ok");
        assert_eq!(response.conversation_id.as_deref(), Some("real-1"));
    }

    #[tokio::test]
    async fn call_python_maps_runtime_session_id_from_stdout_json() {
        let script = r#"print('{"response":"ok","runtime_session_id":"runtime-real-1"}')"#;
        let state = build_test_state(temp_script(script, "runtime-session-id"), 15_000);
        let response = call_python(&state, "hello", Some("client-1".into()), None, None)
            .await
            .expect("python success");
        assert_eq!(response.session_id, "runtime-real-1");
        assert_eq!(response.client_session_id.as_deref(), Some("client-1"));
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
