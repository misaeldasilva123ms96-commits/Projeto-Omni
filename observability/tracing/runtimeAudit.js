function buildRuntimeTrace({
  thought,
  plan,
  action,
  provider,
  sessionSnapshot,
}) {
  return {
    timestamp: new Date().toISOString(),
    intent: thought.intent,
    complexity: thought.complexity,
    strategy: plan.strategy,
    selected_tool: action.selected_tool,
    permission_requirement: action.permission_requirement,
    provider: provider.name,
    delegates: plan.delegates,
    session_id: sessionSnapshot.session_id,
  };
}

module.exports = {
  buildRuntimeTrace,
};
