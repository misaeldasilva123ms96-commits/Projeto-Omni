use std::{convert::Infallible, process::Stdio, time::Duration};

use async_stream::stream;
use axum::{
    extract::{Query, State},
    response::sse::{Event, KeepAlive, Sse},
    Json,
};
use serde::Deserialize;
use serde_json::{json, Value};
use tokio::{process::Command, time::{interval, timeout, MissedTickBehavior}};
use tracing::warn;

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

pub(crate) async fn stream(State(state): State<AppState>) -> Sse<impl futures_core::Stream<Item = Result<Event, Infallible>>> {
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

    Sse::new(output).keep_alive(KeepAlive::new().interval(Duration::from_secs(15)).text("heartbeat"))
}

async fn call_observability_cli(
    state: &AppState,
    command_name: &str,
    extra_args: &[String],
    payload_key: &str,
) -> Value {
    let cli_timeout_ms = state.python_timeout_ms.min(OBSERVABILITY_TIMEOUT_MS);
    let mut command = Command::new(&state.python_bin);
    command
        .current_dir(&state.python_root)
        .arg("-m")
        .arg("brain.runtime.observability.cli")
        .arg("--root")
        .arg(state.project_root.display().to_string())
        .arg(command_name)
        .args(extra_args)
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .kill_on_drop(true);

    let output = match timeout(Duration::from_millis(cli_timeout_ms), command.output()).await {
        Ok(Ok(output)) => output,
        Ok(Err(error)) => {
            return graceful_error(payload_key, format!("failed to spawn observability reader: {error}"));
        }
        Err(_) => {
            return graceful_error(payload_key, format!("observability reader timed out after {cli_timeout_ms} ms"));
        }
    };

    let stderr = String::from_utf8_lossy(&output.stderr).trim().to_string();
    if !output.status.success() {
        return graceful_error(
            payload_key,
            if stderr.is_empty() {
                format!("observability reader exited with status {}", output.status.code().unwrap_or(-1))
            } else {
                stderr
            },
        );
    }

    if !stderr.is_empty() {
        warn!(python_stderr = %stderr, "observability reader produced stderr");
    }

    let stdout = String::from_utf8_lossy(&output.stdout).trim().to_string();
    if stdout.is_empty() {
        return graceful_error(payload_key, "observability reader returned empty stdout".to_string());
    }

    match serde_json::from_str::<Value>(&stdout) {
        Ok(value) => value,
        Err(error) => graceful_error(payload_key, format!("invalid observability JSON: {error}")),
    }
}

fn graceful_error(payload_key: &str, message: String) -> Value {
    match payload_key {
        "snapshot" => json!({ "status": "error", "error": message, "snapshot": null }),
        "traces" => json!({ "status": "error", "error": message, "traces": [] }),
        _ => json!({ "status": "error", "error": message }),
    }
}
