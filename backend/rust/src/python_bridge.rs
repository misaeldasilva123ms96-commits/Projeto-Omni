//! Shared mechanics for spawning the Python side of the bridge.
//!
//! Every Python invocation from the Rust layer funnels through [`run_python`]
//! so process policy stays uniform: piped stdout, explicit stdin/stderr
//! policies, `kill_on_drop(true)`, optional bounded wait timeout, and no
//! shell interpretation. Callers keep ownership of error mapping, health
//! updates, fallback envelopes, and payload parsing.

use std::{
    ffi::OsString,
    io::Error,
    path::Path,
    process::Stdio,
    time::Duration,
};

use tokio::{
    io::AsyncWriteExt,
    process::Command,
    time,
};
use tracing::warn;

/// stdin wiring for the child process.
///
/// `Inherit` preserves the historical default (no `.stdin(...)` call), used by
/// CLI helpers that never feed the child process.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub(crate) enum StdinMode {
    Inherit,
    Piped,
    Null,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub(crate) enum StderrMode {
    Piped,
    Null,
}

#[derive(Debug)]
pub(crate) enum BridgeSpawnFailure {
    Spawn(Error),
    StdinWrite(Error),
    Wait(Error),
    Timeout,
}

#[derive(Debug)]
pub(crate) struct BridgeOutput {
    pub success: bool,
    pub exit_code: Option<i32>,
    pub stdout: Vec<u8>,
    pub stderr: Vec<u8>,
}

impl BridgeOutput {
    pub fn stderr_lossy_trimmed(&self) -> String {
        String::from_utf8_lossy(&self.stderr).trim().to_string()
    }

    pub fn stdout_lossy_trimmed(&self) -> String {
        String::from_utf8_lossy(&self.stdout).trim().to_string()
    }
}

pub(crate) struct PythonInvocation<'a> {
    pub python_bin: &'a Path,
    pub args: Vec<OsString>,
    pub current_dir: Option<&'a Path>,
    pub env_overrides: Vec<(String, OsString)>,
    pub stdin_mode: StdinMode,
    pub stderr_mode: StderrMode,
    /// Payload written to the piped stdin before waiting. Requires
    /// [`StdinMode::Piped`] to take effect.
    pub stdin_payload: Option<Vec<u8>>,
    pub timeout: Option<Duration>,
}

impl<'a> PythonInvocation<'a> {
    pub fn new<P: AsRef<Path> + ?Sized>(python_bin: &'a P, args: Vec<OsString>) -> Self {
        Self {
            python_bin: python_bin.as_ref(),
            args,
            current_dir: None,
            env_overrides: Vec::new(),
            stdin_mode: StdinMode::Piped,
            stderr_mode: StderrMode::Piped,
            stdin_payload: None,
            timeout: None,
        }
    }

    pub fn current_dir(mut self, dir: &'a Path) -> Self {
        self.current_dir = Some(dir);
        self
    }

    pub fn env(mut self, key: &str, value: impl Into<OsString>) -> Self {
        self.env_overrides.push((key.to_string(), value.into()));
        self
    }

    pub fn stdin_mode(mut self, mode: StdinMode) -> Self {
        self.stdin_mode = mode;
        self
    }

    pub fn stderr_mode(mut self, mode: StderrMode) -> Self {
        self.stderr_mode = mode;
        self
    }

    pub fn stdin_payload(mut self, payload: Option<Vec<u8>>) -> Self {
        self.stdin_payload = payload;
        self
    }

    pub fn timeout(mut self, timeout: Option<Duration>) -> Self {
        self.timeout = timeout;
        self
    }
}

fn stdio_for(mode: StdinMode) -> Stdio {
    match mode {
        StdinMode::Inherit => Stdio::inherit(),
        StdinMode::Piped => Stdio::piped(),
        StdinMode::Null => Stdio::null(),
    }
}

fn stderr_stdio_for(mode: StderrMode) -> Stdio {
    match mode {
        StderrMode::Piped => Stdio::piped(),
        StderrMode::Null => Stdio::null(),
    }
}

pub(crate) async fn run_python(
    invocation: PythonInvocation<'_>,
) -> Result<BridgeOutput, BridgeSpawnFailure> {
    let mut command = Command::new(invocation.python_bin);
    command
        .args(&invocation.args)
        .stdin(stdio_for(invocation.stdin_mode))
        .stdout(Stdio::piped())
        .stderr(stderr_stdio_for(invocation.stderr_mode))
        // Never leave an orphaned Python child behind if the caller future is
        // dropped between spawn and wait.
        .kill_on_drop(true);

    if let Some(dir) = invocation.current_dir {
        command.current_dir(dir);
    }
    for (key, value) in &invocation.env_overrides {
        command.env(key, value);
    }

    let mut child = command.spawn().map_err(BridgeSpawnFailure::Spawn)?;

    if let Some(payload) = invocation.stdin_payload {
        if let Some(mut stdin) = child.stdin.take() {
            if let Err(err) = stdin.write_all(&payload).await {
                let _ = child.kill().await;
                return Err(BridgeSpawnFailure::StdinWrite(err));
            }
            if let Err(err) = stdin.flush().await {
                warn!("python stdin flush: {err}");
            }
        }
    }

    let wait = child.wait_with_output();
    let output = match invocation.timeout {
        Some(limit) => match time::timeout(limit, wait).await {
            Ok(Ok(output)) => output,
            Ok(Err(err)) => return Err(BridgeSpawnFailure::Wait(err)),
            Err(_) => return Err(BridgeSpawnFailure::Timeout),
        },
        None => match wait.await {
            Ok(output) => output,
            Err(err) => return Err(BridgeSpawnFailure::Wait(err)),
        },
    };

    Ok(BridgeOutput {
        success: output.status.success(),
        exit_code: output.status.code(),
        stdout: output.stdout,
        stderr: output.stderr,
    })
}
