use super::*;

const SMOKE_PATH: &str = "/api/v1/runtime/runner-smoke";

fn counted_smoke(name: &str, wait: bool, fail: bool) -> (AppState, PathBuf) {
    let root = env::temp_dir().join(format!(
        "omni-smoke-{}-{name}",
        SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_nanos()
    ));
    fs::create_dir_all(&root).unwrap();
    let script = root.join("smoke.py");
    let counter = root.join("calls.txt");
    let source = format!(
        r#"import json, pathlib, sys, time
root = pathlib.Path(__file__).parent
with (root / 'calls.txt').open('a') as f:
    f.write('call\n')
    f.flush()
if {wait}:
    while not (root / 'release').exists():
        time.sleep(0.01)
if {fail}:
    sys.stderr.write('/opt/private stderr traceback sk-smoke-secret')
    sys.exit(2)
print(json.dumps({{'status': 'ok', 'selected_runtime': 'node', 'public_summary': 'sk-secret-disguised-as-label'}}))
"#,
        wait = if wait { "True" } else { "False" },
        fail = if fail { "True" } else { "False" }
    );
    fs::write(&script, source).unwrap();
    (build_test_state(script, 1000), counter)
}

async fn wait_for_counter(counter: &Path) {
    tokio::time::timeout(Duration::from_secs(5), async {
        while !counter.exists() {
            tokio::time::sleep(Duration::from_millis(10)).await;
        }
    })
    .await
    .expect("fake subprocess started");
}

fn calls(counter: &Path) -> usize {
    fs::read_to_string(counter).unwrap().lines().count()
}

fn smoke_request(ip: [u8; 4]) -> Request<Body> {
    let mut request = get_request(SMOKE_PATH);
    request
        .extensions_mut()
        .insert(ConnectInfo(SocketAddr::from((ip, 41000))));
    request
}

#[tokio::test]
async fn public_health_never_serializes_internal_dependency_details() {
    let mut state = build_test_state(temp_script("print('unused')", "public-health"), 1000);
    let private = "/app/ /home/ /root/ /opt/ C:\\Users\\private stderr traceback stack trace PYTHON_ENTRY PYTHON_BIN sk-test-health-secret";
    update_python_health(&state, "failed", Some(private.to_string())).await;
    state.python_bin = "/opt/private/python".into();
    state.node_bin = "C:\\private\\node.exe".into();
    let response = public_status_router(state)
        .oneshot(get_request("/health"))
        .await
        .unwrap();
    assert_eq!(response.status(), StatusCode::OK);
    let payload = response_json(response).await;
    let serialized = payload.to_string();
    for forbidden in [
        "/app/",
        "/home/",
        "/root/",
        "/opt/",
        "C:\\",
        "stderr",
        "traceback",
        "stack trace",
        "PYTHON_ENTRY",
        "PYTHON_BIN",
        "sk-test-health-secret",
        "configured_bin",
        "\"entry\"",
        "last_error",
    ] {
        assert!(
            !serialized.contains(forbidden),
            "leaked {forbidden}: {serialized}"
        );
    }
    assert_eq!(
        payload["python"]["error_code"],
        "PYTHON_ORCHESTRATOR_FAILED"
    );
}

#[tokio::test]
async fn public_smoke_rate_limit_is_independent_of_chat_toggle() {
    let mut state = build_test_state_with_security(
        temp_script("print('unused')", "smoke-rate"),
        1000,
        test_chat_security_config(),
    );
    state.mock_mode = true;
    let router = chat_router(state);
    for _ in 0..6 {
        assert_eq!(
            router
                .clone()
                .oneshot(smoke_request([198, 51, 100, 1]))
                .await
                .unwrap()
                .status(),
            StatusCode::OK
        );
    }
    let response = router
        .oneshot(smoke_request([198, 51, 100, 1]))
        .await
        .unwrap();
    assert_eq!(response.status(), StatusCode::TOO_MANY_REQUESTS);
}

#[tokio::test]
async fn public_health_classifies_actual_python_errors_and_untrusted_states() {
    let state = build_test_state(temp_script("import sys\nsys.stderr.write('/app/ /home/ /root/ /opt/ C:\\\\private stderr traceback stack trace PYTHON_ENTRY PYTHON_BIN sk-test-env-secret')\nsys.exit(1)", "health-python-error"), 1000);
    call_python_subprocess(&state, "test", None, None, None)
        .await
        .unwrap();
    let response = public_status_router(state.clone())
        .oneshot(get_request("/health"))
        .await
        .unwrap();
    let payload = response_json(response).await;
    assert_eq!(payload["python"]["last_status"], "unavailable");
    assert_eq!(
        payload["python"]["error_code"],
        "PYTHON_ORCHESTRATOR_FAILED"
    );
    for forbidden in [
        "/app/",
        "/home/",
        "/root/",
        "/opt/",
        "C:\\",
        "stderr",
        "traceback",
        "stack trace",
        "PYTHON_ENTRY",
        "PYTHON_BIN",
        "sk-test-env-secret",
    ] {
        assert!(!payload.to_string().contains(forbidden));
    }
    for (internal, public, code) in [
        ("timeout", "timeout", Some("TIMEOUT")),
        ("ready", "ready", None),
        ("not_checked", "not_checked", None),
        ("mock", "mock", None),
        (
            "/opt/arbitrary-state",
            "degraded",
            Some("PYTHON_ORCHESTRATOR_FAILED"),
        ),
    ] {
        update_python_health(&state, internal, None).await;
        let snapshot = build_health_snapshot(&state).await;
        assert_eq!(snapshot.python.last_status, public);
        assert_eq!(snapshot.python.error_code, code);
    }
}

#[tokio::test]
async fn public_smoke_cache_reuses_results_and_refreshes_after_expiry() {
    for fail in [false, true] {
        let (state, counter) = counted_smoke("cache", false, fail);
        let router = chat_router(state.clone());
        for client in 1..=20 {
            let response = router
                .clone()
                .oneshot(smoke_request([198, 51, 100, client]))
                .await
                .unwrap();
            assert_eq!(response.status(), StatusCode::OK);
            let payload = response_json(response).await;
            assert_eq!(payload["status"], if fail { "error" } else { "ok" });
            assert!(!payload.to_string().contains("sk-"));
            assert!(!payload.to_string().contains("/opt/"));
        }
        assert_eq!(calls(&counter), 1);
        // Age the completion timestamp deterministically instead of sleeping.
        state
            .chat_security
            .smoke_cache
            .lock()
            .await
            .as_mut()
            .unwrap()
            .0 = Instant::now() - SMOKE_CACHE_TTL;
        assert_eq!(
            router
                .oneshot(smoke_request([198, 51, 100, 21]))
                .await
                .unwrap()
                .status(),
            StatusCode::OK
        );
        assert_eq!(calls(&counter), 2);
    }
}

#[tokio::test]
async fn public_smoke_single_flight_survives_client_cancellation() {
    let (state, counter) = counted_smoke("concurrent", true, false);
    let router = chat_router(state.clone());
    let first = tokio::spawn(router.clone().oneshot(smoke_request([198, 51, 100, 1])));
    wait_for_counter(&counter).await;
    first.abort();
    let mut requests = Vec::new();
    for client in 2..=30 {
        requests.push(tokio::spawn(
            router
                .clone()
                .oneshot(smoke_request([198, 51, 100, client])),
        ));
    }
    for request in requests {
        let response = request.await.unwrap().unwrap();
        assert_eq!(response.status(), StatusCode::SERVICE_UNAVAILABLE);
        assert_eq!(
            response_json(response).await["public_failure_class"],
            "busy"
        );
    }
    assert_eq!(calls(&counter), 1);
    fs::write(counter.parent().unwrap().join("release"), "go").unwrap();
    let cache = tokio::time::timeout(
        Duration::from_secs(5),
        state.chat_security.smoke_cache.lock(),
    )
    .await
    .unwrap();
    assert!(cache.is_some());
    drop(cache);
    assert_eq!(
        router
            .oneshot(smoke_request([198, 51, 100, 31]))
            .await
            .unwrap()
            .status(),
        StatusCode::OK
    );
    assert_eq!(calls(&counter), 1);
}

#[tokio::test]
async fn public_smoke_timeout_is_bounded_and_cached() {
    let (state, counter) = counted_smoke("timeout", true, false);
    let router = chat_router(state.clone());
    let started = Instant::now();
    let response = router
        .clone()
        .oneshot(smoke_request([198, 51, 100, 1]))
        .await
        .unwrap();
    assert_eq!(
        response_json(response).await["public_failure_class"],
        "timeout"
    );
    assert!(started.elapsed() < SMOKE_TIMEOUT + Duration::from_secs(3));
    let response = router
        .oneshot(smoke_request([198, 51, 100, 2]))
        .await
        .unwrap();
    assert_eq!(
        response_json(response).await["public_failure_class"],
        "timeout"
    );
    assert_eq!(calls(&counter), 1);
}

#[tokio::test]
async fn public_smoke_uses_trusted_identity_and_fails_closed_without_peer() {
    let mut state = build_test_state(temp_script("print('unused')", "smoke-proxy"), 1000);
    state.mock_mode = true;
    Arc::get_mut(&mut state.chat_security)
        .unwrap()
        .trusted_proxy = TrustedProxyConfig::parse(true, "10.0.0.0/8", 8).unwrap();
    let router = chat_router(state);
    assert_eq!(
        router
            .clone()
            .oneshot(get_request(SMOKE_PATH))
            .await
            .unwrap()
            .status(),
        StatusCode::SERVICE_UNAVAILABLE
    );
    for i in 0..6 {
        let mut request = smoke_request([10, 0, 0, 1]);
        request
            .headers_mut()
            .insert("x-forwarded-for", "198.51.100.1".parse().unwrap());
        assert_eq!(
            router.clone().oneshot(request).await.unwrap().status(),
            StatusCode::OK,
            "request {i}"
        );
    }
    let mut request = smoke_request([10, 0, 0, 2]);
    request
        .headers_mut()
        .insert("x-forwarded-for", "198.51.100.1".parse().unwrap());
    assert_eq!(
        router.clone().oneshot(request).await.unwrap().status(),
        StatusCode::TOO_MANY_REQUESTS
    );
    for i in 0..7 {
        let mut request = smoke_request([203, 0, 113, 1]);
        request.headers_mut().insert(
            "x-forwarded-for",
            format!("198.51.100.{}", i + 10).parse().unwrap(),
        );
        assert_eq!(
            router.clone().oneshot(request).await.unwrap().status(),
            if i < 6 {
                StatusCode::OK
            } else {
                StatusCode::TOO_MANY_REQUESTS
            }
        );
    }
}

#[test]
fn public_smoke_rate_table_is_bounded_and_window_expires() {
    let mut security = ChatSecurityState::with_config(test_chat_security_config());
    security.rate_limit_max_clients = 1;
    let a = IpAddr::from([198, 51, 100, 1]);
    let b = IpAddr::from([198, 51, 100, 2]);
    let now = Instant::now();
    for _ in 0..6 {
        assert!(security.check_smoke_rate_limit(a, now));
    }
    assert!(!security.check_smoke_rate_limit(a, now));
    assert!(!security.check_smoke_rate_limit(b, now));
    assert!(security.check_smoke_rate_limit(b, now + Duration::from_secs(60)));
    assert_eq!(security.smoke_rate_limiter.lock().unwrap().len(), 1);
    assert!(security.rate_limiter.lock().unwrap().is_empty());
}

#[tokio::test]
async fn public_smoke_does_not_inherit_credentials_or_forward_requests() {
    let guard = EnvTestGuard::new(&[
        "OPENAI_API_KEY",
        "GEMINI_API_KEY",
        "SUPABASE_SERVICE_ROLE_KEY",
        "OMNI_BYOK_PROVIDER",
        "OMNI_NODE_SERVICE_TOKEN",
        "CUSTOM_SECRET",
        "NODE_OPTIONS",
        "PYTHONPATH",
    ]);
    for key in [
        "OPENAI_API_KEY",
        "GEMINI_API_KEY",
        "SUPABASE_SERVICE_ROLE_KEY",
        "OMNI_BYOK_PROVIDER",
        "OMNI_NODE_SERVICE_TOKEN",
        "CUSTOM_SECRET",
        "NODE_OPTIONS",
        "PYTHONPATH",
    ] {
        guard.set(
            key,
            if key == "NODE_OPTIONS" {
                "--no-warnings"
            } else {
                "diagnostic-secret-sentinel"
            },
        );
    }
    let script = r#"import json, os, sys
body = json.load(sys.stdin)
assert body['message'] == 'responda apenas OK'
assert body['diagnostic'] == 'runner_smoke'
assert 'session_provider_credentials' not in body
assert not any(value == 'diagnostic-secret-sentinel' for value in os.environ.values())
assert 'NODE_OPTIONS' not in os.environ
assert 'PYTHONPATH' not in os.environ
print(json.dumps({'status': 'ok', 'public_summary': 'diagnostic-secret-sentinel', 'public_failure_class': 'sk-secret-label'}))
"#;
    let state = build_test_state(temp_script(script, "smoke-env"), 1000);
    let mut request = smoke_request([198, 51, 100, 1]);
    request.headers_mut().insert(
        AUTHORIZATION,
        "Bearer diagnostic-secret-sentinel".parse().unwrap(),
    );
    let payload = response_json(chat_router(state).oneshot(request).await.unwrap()).await;
    assert_eq!(payload["status"], "ok");
    assert_eq!(payload["public_failure_class"], "diagnostic_failed");
    assert!(!payload.to_string().contains("sentinel"));
    assert!(!payload.to_string().contains("sk-secret"));
}
