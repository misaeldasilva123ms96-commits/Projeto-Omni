use std::{convert::Infallible, time::Duration};

use async_stream::stream;
use axum::{
    extract::{Query, State},
    response::sse::{Event, KeepAlive, Sse},
    Json,
};
use serde::Deserialize;
use serde_json::{json, Value};
use tokio::time::{interval, MissedTickBehavior};
use tracing::warn;

use crate::python_bridge::{run_python, PythonInvocation, StdinMode};
use crate::AppState;

const OBSERVABILITY_TIMEOUT_MS: u64 = 2_500;
const OBSERVABILITY_STREAM_INTERVAL_MS: u64 = 2_000;
const OBSERVABILITY_HEARTBEAT_INTERVAL_MS: u64 = 10_000;

#[derive(Debug, Deserialize)]
pub(crate) struct LimitQuery {
    limit: Option<usize>,
}

pub(crate) async fn snapshot(State(state): State<AppState>) -> Json<Value> {
    Json(call_observability_cli(&state, "snapshot", &[], "snapshot").await)
}

pub(crate) async fn traces(
    State(state): State<AppState>,
    Query(query): Query<LimitQuery>,
) -> Json<Value> {
    let limit = query.limit.unwrap_or(10).clamp(1, 50);
    Json(
        call_observability_cli(
            &state,
            "traces",
            &["--limit".to_string(), limit.to_string()],
            "traces",
        )
        .await,
    )
}

pub(crate) async fn stream(
    State(state): State<AppState>,
) -> Sse<impl futures_core::Stream<Item = Result<Event, Infallible>>> {
    let output = stream! {
        let mut snapshot_interval = interval(Duration::from_millis(OBSERVABILITY_STREAM_INTERVAL_MS));
        snapshot_interval.set_missed_tick_behavior(MissedTickBehavior::Skip);
        let mut heartbeat_interval = interval(Duration::from_millis(OBSERVABILITY_HEARTBEAT_INTERVAL_MS));
        heartbeat_interval.set_missed_tick_behavior(MissedTickBehavior::Skip);

        loop {
            tokio::select! {
                _ = snapshot_interval.tick() => {
                    let payload = call_observability_cli(&state, "snapshot", &[], "snapshot").await;
                    let serialized = serde_json::to_string(&payload).unwrap_or_else(|_| "{\"status\":\"error\",\"error\":\"serialization_failure\",\"snapshot\":null}".to_string());
                    yield Ok(Event::default().event("snapshot").data(serialized));
                }
                _ = heartbeat_interval.tick() => {
                    yield Ok(Event::default().comment("heartbeat"));
                }
            }
        }
    };

    Sse::new(output).keep_alive(
        KeepAlive::new()
            .interval(Duration::from_secs(15))
            .text("heartbeat"),
    )
}

async fn call_observability_cli(
    state: &AppState,
    command_name: &str,
    extra_args: &[String],
    payload_key: &str,
) -> Value {
    let cli_timeout_ms = state.python_timeout_ms.min(OBSERVABILITY_TIMEOUT_MS);
    let mut args: Vec<std::ffi::OsString> = vec![
        "-m".into(),
        "brain.runtime.observability.cli".into(),
        "--root".into(),
        state.project_root.display().to_string().into(),
        command_name.into(),
    ];
    args.extend(extra_args.iter().map(|arg| arg.as_str().into()));

    let invocation = PythonInvocation::new(&state.python_bin, args)
        .current_dir(&state.python_root)
        .stdin_mode(StdinMode::Inherit)
        .timeout(Some(Duration::from_millis(cli_timeout_ms)));

    let output = match run_python(invocation).await {
        Ok(output) => output,
        Err(error) => {
            return graceful_error(payload_key, spawn_failure_message(&error, cli_timeout_ms));
        }
    };

    let stderr = output.stderr_lossy_trimmed();
    if !output.success {
        return graceful_error(
            payload_key,
            if stderr.is_empty() {
                format!(
                    "observability reader exited with status {}",
                    output.exit_code.unwrap_or(-1)
                )
            } else {
                stderr
            },
        );
    }

    if !stderr.is_empty() {
        warn!(python_stderr = %stderr, "observability reader produced stderr");
    }

    let stdout = output.stdout_lossy_trimmed();
    if stdout.is_empty() {
        return graceful_error(
            payload_key,
            "observability reader returned empty stdout".to_string(),
        );
    }

    match serde_json::from_str::<Value>(&stdout) {
        Ok(value) => value,
        Err(error) => graceful_error(payload_key, format!("invalid observability JSON: {error}")),
    }
}

fn spawn_failure_message(
    error: &crate::python_bridge::BridgeSpawnFailure,
    cli_timeout_ms: u64,
) -> String {
    match error {
        crate::python_bridge::BridgeSpawnFailure::Timeout => {
            format!("observability reader timed out after {cli_timeout_ms} ms")
        }
        crate::python_bridge::BridgeSpawnFailure::Spawn(err)
        | crate::python_bridge::BridgeSpawnFailure::Wait(err)
        | crate::python_bridge::BridgeSpawnFailure::StdinWrite(err) => {
            format!("failed to spawn observability reader: {err}")
        }
    }
}

fn graceful_error(payload_key: &str, message: String) -> Value {
    match payload_key {
        "snapshot" => json!({ "status": "error", "error": message, "snapshot": null }),
        "traces" => json!({ "status": "error", "error": message, "traces": [] }),
        _ => json!({ "status": "error", "error": message }),
    }
}
