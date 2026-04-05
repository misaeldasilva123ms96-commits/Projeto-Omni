function buildBrainExecutorAction({
  actionId,
  stepId,
  strategy,
  stepGoal,
  dependencyStepIds,
  selectedTool,
  selectedAgent,
  permissionRequirement,
  approvalState,
  executionContext,
  toolArguments,
  timeoutMs,
  retryPolicy,
  transcriptLink,
  memoryUpdateHints,
  audit,
}) {
  return {
    version: '1.0.0',
    action_id: actionId,
    step_id: stepId,
    strategy,
    step_goal: stepGoal || '',
    dependency_step_ids: Array.isArray(dependencyStepIds) ? dependencyStepIds : [],
    selected_tool: selectedTool,
    selected_agent: selectedAgent || 'master_orchestrator',
    permission_requirement: permissionRequirement || 'prompt_if_destructive',
    approval_state: approvalState || 'pending',
    execution_context: executionContext || {},
    tool_arguments: toolArguments || {},
    timeout_ms: timeoutMs || 30000,
    retry_policy: retryPolicy || {
      max_attempts: 1,
      backoff_ms: 0,
    },
    transcript_link: transcriptLink || {},
    memory_update_hints: memoryUpdateHints || {},
    result_payload: null,
    error_payload: null,
    usage_accounting: null,
    audit: audit || {},
  };
}

module.exports = {
  buildBrainExecutorAction,
};
