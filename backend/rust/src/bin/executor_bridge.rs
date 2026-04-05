use runtime::{
    glob_search, grep_search, read_file, write_file, GrepSearchInput, PermissionMode,
    PermissionPolicy, PermissionPromptDecision, PermissionPrompter, PermissionRequest,
    Session,
};
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::{env, fs, process, time::Instant};

#[derive(Debug, Deserialize)]
struct BridgeRequest {
    action_id: String,
    step_id: String,
    strategy: String,
    selected_tool: String,
    selected_agent: String,
    permission_requirement: String,
    approval_state: String,
    execution_context: Value,
    tool_arguments: Value,
    transcript_link: Value,
    memory_update_hints: Value,
}

#[derive(Debug, Serialize)]
struct BridgeResponse {
    ok: bool,
    action_id: String,
    step_id: String,
    selected_tool: String,
    selected_agent: String,
    transcript_link: Value,
    result_payload: Option<Value>,
    error_payload: Option<Value>,
    usage_accounting: Value,
    audit: Value,
}

struct ApprovalPrompter {
    approval_state: String,
}

impl PermissionPrompter for ApprovalPrompter {
    fn decide(&mut self, _request: &PermissionRequest) -> PermissionPromptDecision {
        if self.approval_state == "approved" {
            PermissionPromptDecision::Allow
        } else {
            PermissionPromptDecision::Deny {
                reason: "approval required by permission policy".to_string(),
            }
        }
    }
}

fn main() {
    if let Err(error) = run() {
        eprintln!("{error}");
        process::exit(1);
    }
}

fn run() -> Result<(), String> {
    let input_path = env::args()
        .nth(1)
        .ok_or_else(|| "missing payload path".to_string())?;
    let payload = fs::read_to_string(&input_path)
        .map_err(|error| format!("failed to read payload: {error}"))?;
    let request: BridgeRequest =
        serde_json::from_str(&payload).map_err(|error| format!("invalid payload: {error}"))?;
    if let Some(project_root) = request
        .execution_context
        .get("project_root")
        .and_then(Value::as_str)
    {
        std::env::set_current_dir(project_root)
            .map_err(|error| format!("failed to switch project root: {error}"))?;
    }

    let started = Instant::now();
    let policy = PermissionPolicy::new(PermissionMode::Prompt)
        .with_tool_mode("read_file", PermissionMode::Allow)
        .with_tool_mode("glob_search", PermissionMode::Allow)
        .with_tool_mode("grep_search", PermissionMode::Allow)
        .with_tool_mode("write_file", PermissionMode::Prompt)
        .with_tool_mode("bash", PermissionMode::Deny);

    let input_repr = request.tool_arguments.to_string();
    let permission = policy.authorize(
        &request.selected_tool,
        &input_repr,
        Some(&mut ApprovalPrompter {
            approval_state: request.approval_state.clone(),
        }),
    );

    let session = Session::new();
    let transcript_link = request.transcript_link.clone();

    let response = match permission {
        runtime::PermissionOutcome::Allow => {
            let result_payload = execute_tool(&request)?;
            BridgeResponse {
                ok: true,
                action_id: request.action_id,
                step_id: request.step_id,
                selected_tool: request.selected_tool,
                selected_agent: request.selected_agent,
                transcript_link,
                result_payload: Some(result_payload),
                error_payload: None,
                usage_accounting: json!({
                    "duration_ms": started.elapsed().as_millis(),
                    "session_messages": session.messages.len(),
                    "kind": "tool-execution"
                }),
                audit: json!({
                    "strategy": request.strategy,
                    "permission_requirement": request.permission_requirement,
                    "execution_context": request.execution_context,
                    "memory_update_hints": request.memory_update_hints
                }),
            }
        }
        runtime::PermissionOutcome::Deny { reason } => BridgeResponse {
            ok: false,
            action_id: request.action_id,
            step_id: request.step_id,
            selected_tool: request.selected_tool,
            selected_agent: request.selected_agent,
            transcript_link,
            result_payload: None,
            error_payload: Some(json!({
                "kind": "permission_denied",
                "message": reason
            })),
            usage_accounting: json!({
                "duration_ms": started.elapsed().as_millis(),
                "session_messages": session.messages.len(),
                "kind": "permission-check"
            }),
            audit: json!({
                "strategy": request.strategy,
                "permission_requirement": request.permission_requirement,
                "execution_context": request.execution_context,
                "memory_update_hints": request.memory_update_hints
            }),
        },
    };

    println!(
        "{}",
        serde_json::to_string(&response)
            .map_err(|error| format!("failed to serialize response: {error}"))?
    );
    Ok(())
}

fn execute_tool(request: &BridgeRequest) -> Result<Value, String> {
    match request.selected_tool.as_str() {
        "read_file" => {
            let path = request
                .tool_arguments
                .get("path")
                .and_then(Value::as_str)
                .ok_or_else(|| "read_file requires tool_arguments.path".to_string())?;
            let offset = request
                .tool_arguments
                .get("offset")
                .and_then(Value::as_u64)
                .map(|value| value as usize);
            let limit = request
                .tool_arguments
                .get("limit")
                .and_then(Value::as_u64)
                .map(|value| value as usize);
            let output = read_file(path, offset, limit)
                .map_err(|error| format!("read_file failed: {error}"))?;
            serde_json::to_value(output).map_err(|error| error.to_string())
        }
        "glob_search" => {
            let pattern = request
                .tool_arguments
                .get("pattern")
                .and_then(Value::as_str)
                .ok_or_else(|| "glob_search requires tool_arguments.pattern".to_string())?;
            let base_path = request
                .tool_arguments
                .get("path")
                .and_then(Value::as_str);
            let output = glob_search(pattern, base_path)
                .map_err(|error| format!("glob_search failed: {error}"))?;
            serde_json::to_value(output).map_err(|error| error.to_string())
        }
        "grep_search" => {
            let input: GrepSearchInput = serde_json::from_value(request.tool_arguments.clone())
                .map_err(|error| format!("invalid grep_search input: {error}"))?;
            let output = grep_search(&input)
                .map_err(|error| format!("grep_search failed: {error}"))?;
            serde_json::to_value(output).map_err(|error| error.to_string())
        }
        "write_file" => {
            let path = request
                .tool_arguments
                .get("path")
                .and_then(Value::as_str)
                .ok_or_else(|| "write_file requires tool_arguments.path".to_string())?;
            let content = request
                .tool_arguments
                .get("content")
                .and_then(Value::as_str)
                .ok_or_else(|| "write_file requires tool_arguments.content".to_string())?;
            let output = write_file(path, content)
                .map_err(|error| format!("write_file failed: {error}"))?;
            serde_json::to_value(output).map_err(|error| error.to_string())
        }
        other => Err(format!("unsupported tool: {other}")),
    }
}
