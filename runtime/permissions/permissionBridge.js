const PermissionMode = Object.freeze({
  ALLOW: 'allow',
  DENY: 'deny',
  PROMPT: 'prompt',
});

function createPermissionPolicy({ defaultMode = PermissionMode.PROMPT, toolModes = {} } = {}) {
  return {
    defaultMode,
    toolModes: { ...toolModes },
  };
}

function modeFor(policy, toolName) {
  return policy.toolModes[toolName] || policy.defaultMode;
}

function authorizeExecution({ policy, toolName, input, promptDecider }) {
  const mode = modeFor(policy, toolName);
  if (mode === PermissionMode.ALLOW) {
    return { allowed: true, mode };
  }

  if (mode === PermissionMode.DENY) {
    return {
      allowed: false,
      mode,
      reason: `tool '${toolName}' denied by permission policy`,
    };
  }

  if (typeof promptDecider === 'function') {
    const decision = promptDecider({ toolName, input });
    if (decision?.allowed) {
      return { allowed: true, mode };
    }
    return {
      allowed: false,
      mode,
      reason: decision?.reason || `tool '${toolName}' requires approval`,
    };
  }

  return {
    allowed: false,
    mode,
    reason: `tool '${toolName}' requires interactive approval`,
  };
}

module.exports = {
  PermissionMode,
  authorizeExecution,
  createPermissionPolicy,
};
