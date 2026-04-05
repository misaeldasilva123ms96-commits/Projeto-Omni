const TOOL_TAXONOMY = {
  none: { category: 'direct_response', policy_level: 'low', mutating: false, privileged: false },
  read_file: { category: 'code_file_read', policy_level: 'low', mutating: false, privileged: false },
  glob_search: { category: 'information_gathering', policy_level: 'low', mutating: false, privileged: false },
  grep_search: { category: 'information_gathering', policy_level: 'low', mutating: false, privileged: false },
  write_file: { category: 'file_mutation', policy_level: 'medium', mutating: true, privileged: true },
  filesystem_read: { category: 'code_file_read', policy_level: 'low', mutating: false, privileged: false },
  filesystem_write: { category: 'file_mutation', policy_level: 'medium', mutating: true, privileged: true },
  directory_tree: { category: 'information_gathering', policy_level: 'low', mutating: false, privileged: false },
  git_status: { category: 'information_gathering', policy_level: 'low', mutating: false, privileged: false },
  git_diff: { category: 'information_gathering', policy_level: 'low', mutating: false, privileged: false },
  git_commit: { category: 'execution_shell', policy_level: 'high', mutating: true, privileged: true },
  test_runner: { category: 'execution_shell', policy_level: 'medium', mutating: false, privileged: true },
  package_manager: { category: 'execution_shell', policy_level: 'high', mutating: true, privileged: true },
  dependency_inspection: { category: 'information_gathering', policy_level: 'low', mutating: false, privileged: false },
  code_search: { category: 'information_gathering', policy_level: 'low', mutating: false, privileged: false },
  autonomous_debug_loop: { category: 'execution_shell', policy_level: 'high', mutating: true, privileged: true },
  shell_command: { category: 'execution_shell', policy_level: 'high', mutating: true, privileged: true },
  web_request: { category: 'external_network', policy_level: 'high', mutating: false, privileged: true },
  human_approval: { category: 'human_approval', policy_level: 'high', mutating: false, privileged: true },
};

function describeTool(toolName) {
  return TOOL_TAXONOMY[String(toolName || 'none')] || {
    category: 'unknown',
    policy_level: 'medium',
    mutating: false,
    privileged: false,
  };
}

function specialistAllowsTool(specialist, toolName) {
  const category = describeTool(toolName).category;
  const specialistScopes = {
    master_orchestrator: ['direct_response', 'information_gathering', 'code_file_read', 'file_mutation', 'execution_shell'],
    researcher_agent: ['information_gathering', 'code_file_read'],
    coder_agent: ['code_file_read', 'file_mutation', 'execution_shell'],
    reviewer_agent: ['information_gathering', 'code_file_read', 'direct_response'],
    memory_agent: ['information_gathering', 'code_file_read', 'direct_response'],
    critic_agent: ['direct_response', 'information_gathering', 'code_file_read'],
  };
  return (specialistScopes[String(specialist || 'master_orchestrator')] || ['direct_response']).includes(category);
}

function buildPolicyDecision({ toolName, approvalState = 'approved', parallelSafe = false, specialist = 'master_orchestrator' }) {
  const tool = describeTool(toolName);
  if (!specialistAllowsTool(specialist, toolName)) {
    return {
      decision: 'stop',
      reason_code: 'specialist_scope_violation',
      operator_message: 'A ferramenta solicitada nao pertence ao escopo do especialista atual.',
      tool,
    };
  }
  if (tool.mutating && parallelSafe) {
    return {
      decision: 'stop',
      reason_code: 'unsafe_parallel_mutation',
      operator_message: 'Mutacoes paralelas nao sao permitidas por politica.',
      tool,
    };
  }
  if (tool.privileged && approvalState !== 'approved' && toolName !== 'none') {
    return {
      decision: 'stop',
      reason_code: 'missing_approval',
      operator_message: 'A acao exige aprovacao explicita antes da execucao.',
      tool,
    };
  }
  return {
    decision: 'allow',
    reason_code: 'policy_allows_execution',
    operator_message: 'Execucao permitida dentro dos limites atuais.',
    tool,
  };
}

module.exports = {
  TOOL_TAXONOMY,
  buildPolicyDecision,
  describeTool,
  specialistAllowsTool,
};
