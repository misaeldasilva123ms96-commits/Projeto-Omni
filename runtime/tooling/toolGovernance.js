const { OMNI_ERROR_CODE, buildPublicError } = require('./errorTaxonomy');

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
  verification_runner: { category: 'execution_shell', policy_level: 'medium', mutating: false, privileged: true },
  filesystem_patch_set: { category: 'file_mutation', policy_level: 'high', mutating: true, privileged: true },
  shell_command: { category: 'execution_shell', policy_level: 'high', mutating: true, privileged: true },
  web_request: { category: 'external_network', policy_level: 'high', mutating: false, privileged: true },
  human_approval: { category: 'human_approval', policy_level: 'high', mutating: false, privileged: true },
};

const POLICY_VERSION = 'tool_governance_v1';
const READ_SAFE_TOOLS = new Set(['status', 'health', 'list', 'directory_tree', 'git_status', 'git_diff', 'dependency_inspection', 'glob_search', 'grep_search', 'code_search']);
const READ_SENSITIVE_TOOLS = new Set(['read_file', 'filesystem_read', 'memory_read', 'debug_inspection']);
const WRITE_TOOLS = new Set(['write_file', 'edit_file', 'filesystem_write', 'filesystem_patch_set', 'generated_file_write']);
const DESTRUCTIVE_TOOLS = new Set(['delete', 'overwrite', 'git_reset', 'git_clean', 'rm', 'remove_file']);
const SHELL_TOOLS = new Set(['shell_command', 'run_command', 'test_runner', 'verification_runner', 'package_manager', 'autonomous_debug_loop']);
const NETWORK_TOOLS = new Set(['curl', 'fetch', 'web_request', 'network_request']);
const GIT_SENSITIVE_TOOLS = new Set(['git_commit', 'git_push', 'git_branch_mutation']);

function envTruthy(...names) {
  return names.some(name => ['1', 'true', 'yes', 'on'].includes(String(process.env[name] || '').trim().toLowerCase()));
}

function isPublicDemoMode() {
  return envTruthy('OMNI_PUBLIC_DEMO_MODE', 'OMINI_PUBLIC_DEMO_MODE');
}

function classifyToolCategory(toolName) {
  const tool = String(toolName || '').trim();
  if (READ_SAFE_TOOLS.has(tool)) return 'read_safe';
  if (READ_SENSITIVE_TOOLS.has(tool)) return 'read_sensitive';
  if (WRITE_TOOLS.has(tool)) return 'write';
  if (DESTRUCTIVE_TOOLS.has(tool)) return 'destructive';
  if (SHELL_TOOLS.has(tool)) return 'shell';
  if (NETWORK_TOOLS.has(tool)) return 'network';
  if (GIT_SENSITIVE_TOOLS.has(tool) || (tool.startsWith('git_') && !['git_status', 'git_diff'].includes(tool))) {
    return 'git_sensitive';
  }
  return 'unknown';
}

function buildPublicGovernanceAudit({ allowed, category, reasonCode, approvalRequired = false, publicDemoBlocked = false }) {
  return {
    allowed: Boolean(allowed),
    category: String(category || 'unknown'),
    reason_code: String(reasonCode || 'unknown'),
    approval_required: Boolean(approvalRequired),
    public_demo_blocked: Boolean(publicDemoBlocked),
    policy_version: POLICY_VERSION,
  };
}

function evaluateToolGovernance(action = {}) {
  const tool = String(action.selected_tool || action.tool || '').trim();
  const args = action.tool_arguments && typeof action.tool_arguments === 'object' ? action.tool_arguments : {};
  const category = classifyToolCategory(tool);
  const approvalState = String(action.approval_state || action.approvalState || '').trim().toLowerCase();
  const explicitScope = Boolean(action.explicit_scope || action.scope || args.path || args.workspace_root);

  if (isPublicDemoMode() && ['shell', 'write', 'destructive', 'network', 'git_sensitive'].includes(category)) {
    return decision(false, category, 'public_demo_mode', { publicDemoBlocked: true });
  }
  if (category === 'read_safe') return decision(true, category, 'read_safe_allowed');
  if (category === 'read_sensitive') {
    return explicitScope
      ? decision(true, category, 'read_sensitive_scope_allowed')
      : decision(false, category, 'missing_explicit_scope', { approvalRequired: true });
  }
  if (category === 'write') {
    return approvalState === 'approved'
      ? decision(true, category, 'write_approved')
      : decision(false, category, 'missing_approval', { approvalRequired: true });
  }
  if (category === 'destructive') return decision(false, category, 'destructive_tool_blocked', { approvalRequired: true });
  if (category === 'shell') return decision(true, category, 'shell_delegated_to_shell_policy');
  if (category === 'network') return decision(false, category, 'network_tool_requires_governance', { approvalRequired: true });
  if (category === 'git_sensitive') {
    return approvalState === 'approved'
      ? decision(true, category, 'git_sensitive_approved')
      : decision(false, category, 'git_sensitive_requires_approval', { approvalRequired: true });
  }
  return decision(false, category, 'unknown_tool_requires_governance', { approvalRequired: true });
}

function decision(allowed, category, reason, { approvalRequired = false, publicDemoBlocked = false } = {}) {
  const errorPublicCode = publicDemoBlocked
    ? OMNI_ERROR_CODE.TOOL_BLOCKED_PUBLIC_DEMO
    : approvalRequired
      ? OMNI_ERROR_CODE.TOOL_APPROVAL_REQUIRED
      : allowed
        ? ''
        : OMNI_ERROR_CODE.TOOL_BLOCKED_BY_GOVERNANCE;
  const error = errorPublicCode
    ? buildPublicError(errorPublicCode)
    : {
        error_public_code: '',
        error_public_message: '',
        severity: 'info',
        retryable: false,
        internal_error_redacted: true,
      };
  return {
    allowed: Boolean(allowed),
    category,
    reason,
    ...error,
    approval_required: Boolean(approvalRequired),
    public_demo_blocked: Boolean(publicDemoBlocked),
    governance_audit: buildPublicGovernanceAudit({
      allowed,
      category,
      reasonCode: reason,
      approvalRequired,
      publicDemoBlocked,
    }),
  };
}

function buildGovernanceBlockedResult(action = {}, decisionPayload = {}) {
  const tool = String(action.selected_tool || action.tool || '');
  return {
    ok: false,
    selected_tool: tool,
    tool_status: 'blocked',
    error_public_code: String(decisionPayload.error_public_code || 'TOOL_BLOCKED_BY_GOVERNANCE'),
    error_public_message: String(decisionPayload.error_public_message || 'Tool execution was blocked by governance policy.'),
    severity: String(decisionPayload.severity || 'blocked'),
    retryable: Boolean(decisionPayload.retryable),
    internal_error_redacted: true,
    governance_audit: { ...(decisionPayload.governance_audit || {}) },
    tool_execution: {
      tool_requested: true,
      tool_selected: tool,
      tool_available: true,
      tool_attempted: false,
      tool_succeeded: false,
      tool_failed: false,
      tool_denied: true,
      tool_failure_class: String(decisionPayload.error_public_code || 'TOOL_BLOCKED_BY_GOVERNANCE'),
      tool_failure_reason: String(decisionPayload.error_public_message || 'Tool execution was blocked by governance policy.'),
    },
    error_payload: {
      kind: 'tool_blocked',
      message: 'Tool execution was blocked by governance policy.',
      public_code: String(decisionPayload.error_public_code || 'TOOL_BLOCKED_BY_GOVERNANCE'),
    },
  };
}

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
    dependency_impact_specialist: ['information_gathering', 'code_file_read'],
    test_selection_specialist: ['information_gathering', 'execution_shell', 'code_file_read'],
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
  buildGovernanceBlockedResult,
  buildPublicGovernanceAudit,
  classifyToolCategory,
  describeTool,
  evaluateToolGovernance,
  specialistAllowsTool,
};
