const SAFE_AGENT_CAPABILITIES = Object.freeze([
  'read_safe',
  'summarize',
  'inspect_runtime',
  'inspect_docs',
  'propose_patch',
  'create_report',
]);

const SENSITIVE_AGENT_CAPABILITIES = Object.freeze([
  'write',
  'destructive',
  'shell',
  'network',
  'git_sensitive',
  'credential_access',
  'provider_control',
]);

const SECRET_PATTERNS = [
  /\bBearer\s+[A-Za-z0-9._=-]{8,}/i,
  /\b(?:sk|ghp|xoxb)-[A-Za-z0-9._=-]{8,}/i,
  /\b(?:OPENAI|ANTHROPIC|GROQ|GEMINI|DEEPSEEK|OPENROUTER|SUPABASE)_[A-Z0-9_]*KEY\s*=/i,
  /\b(?:api[_-]?key|apikey|x-api-key|authorization|cookie|set-cookie|token)\b\s*[:=]/i,
  /-----BEGIN [A-Z ]*PRIVATE KEY-----/i,
  /\b(?:stack trace|traceback)\b/i,
];

function normalizeCapability(value) {
  return String(value || '')
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9_:-]+/g, '_')
    .replace(/^_+|_+$/g, '')
    .slice(0, 64);
}

function normalizePolicyResult(value) {
  return String(value || '').trim().toLowerCase() === 'allow' ? 'allow' : 'block';
}

function normalizeIdentifier(value, fallback = '') {
  const normalized = String(value || '')
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9_.:-]+/g, '_')
    .replace(/^_+|_+$/g, '')
    .slice(0, 96);
  return normalized || fallback;
}

function sanitizeLabel(value, fallback = '') {
  const raw = String(value || '').trim();
  if (!raw) return fallback;
  const redacted = redactSensitiveText(raw);
  return redacted
    .replace(/[^\w .:/@+-]/g, '')
    .trim()
    .slice(0, 96) || fallback;
}

function sanitizeReason(value) {
  return String(value || '')
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9_.:-]+/g, '_')
    .replace(/^_+|_+$/g, '')
    .slice(0, 96);
}

function redactSensitiveText(value) {
  let text = String(value || '');
  for (const pattern of SECRET_PATTERNS) {
    text = text.replace(pattern, '[redacted]');
  }
  return text;
}

function hasSecretIndicator(value) {
  const text = typeof value === 'string' ? value : JSON.stringify(value || {});
  return SECRET_PATTERNS.some(pattern => pattern.test(text));
}

function safeCapabilityList(values, allowedSet) {
  const list = Array.isArray(values) ? values : [];
  return [...new Set(list.map(normalizeCapability).filter(item => allowedSet.includes(item)))];
}

function buildToolScope(capability) {
  if (capability === 'propose_patch') {
    return 'proposal_only';
  }
  if (capability === 'inspect_runtime') {
    return 'runtime_truth_read_only';
  }
  if (capability === 'inspect_docs') {
    return 'docs_read_only';
  }
  if (capability === 'create_report') {
    return 'report_metadata_only';
  }
  return 'metadata_read_only';
}

function buildGatewayTruth(decision) {
  return {
    agent_id: decision.agent_id,
    agent_type: decision.agent_type,
    requested_capability: decision.requested_capability,
    decision: decision.decision,
    decision_reason: decision.decision_reason,
    denied_capabilities: decision.denied_capabilities,
    risk_level: decision.risk_level,
    policy_result: decision.policy_result,
    created_at: decision.created_at,
  };
}

function evaluateGovernedAgentRequest({
  agent = {},
  requestedCapability,
  context = {},
  policyResult = 'allow',
  now = new Date(),
} = {}) {
  const capability = normalizeCapability(requestedCapability || agent.requested_capability);
  const normalizedPolicy = normalizePolicyResult(policyResult || context.policy_result);
  const agentId = normalizeIdentifier(agent.agent_id || agent.id, 'agent_unknown');
  const agentType = normalizeIdentifier(agent.agent_type || agent.type, 'unknown');
  const agentName = sanitizeLabel(agent.agent_name || agent.name, 'unknown');
  const createdAt = Number.isFinite(now?.getTime?.()) ? now.toISOString() : new Date().toISOString();
  const allowedCapabilities = safeCapabilityList(
    agent.allowed_capabilities?.length ? agent.allowed_capabilities : SAFE_AGENT_CAPABILITIES,
    SAFE_AGENT_CAPABILITIES,
  );
  const deniedCapabilities = [
    ...new Set([
      ...SENSITIVE_AGENT_CAPABILITIES,
      ...safeCapabilityList(agent.denied_capabilities, SENSITIVE_AGENT_CAPABILITIES),
    ]),
  ];

  let decision = 'deny';
  let decisionReason = 'unknown_capability';
  let riskLevel = 'medium';
  let toolScope = 'none';

  if (hasSecretIndicator(agent) || hasSecretIndicator(context)) {
    decisionReason = 'secret_indicator_detected';
    riskLevel = 'high';
  } else if (normalizedPolicy !== 'allow') {
    decisionReason = 'policy_blocked';
    riskLevel = 'high';
  } else if (SENSITIVE_AGENT_CAPABILITIES.includes(capability)) {
    decisionReason = 'sensitive_capability_blocked';
    riskLevel = 'high';
  } else if (allowedCapabilities.includes(capability)) {
    decision = 'allow';
    decisionReason = capability === 'propose_patch'
      ? 'proposal_only_capability_allowed'
      : 'safe_capability_allowed';
    riskLevel = capability === 'propose_patch' ? 'medium' : 'low';
    toolScope = buildToolScope(capability);
  }

  const result = {
    ok: decision === 'allow',
    agent_id: agentId,
    agent_name: agentName,
    agent_type: agentType,
    requested_capability: capability,
    allowed_capabilities: allowedCapabilities,
    denied_capabilities: deniedCapabilities,
    tool_scope: toolScope,
    policy_result: normalizedPolicy,
    decision,
    decision_reason: sanitizeReason(decisionReason),
    risk_level: riskLevel,
    created_at: createdAt,
  };

  return {
    ...result,
    runtimeTruth: buildGatewayTruth(result),
  };
}

module.exports = {
  SAFE_AGENT_CAPABILITIES,
  SENSITIVE_AGENT_CAPABILITIES,
  evaluateGovernedAgentRequest,
  hasSecretIndicator,
  normalizeCapability,
};
