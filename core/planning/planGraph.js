function buildPlanNode(step, extra = {}) {
  return {
    node_id: step.step_id,
    step_id: step.step_id,
    selected_tool: step.selected_tool,
    selected_agent: step.selected_agent,
    tool_arguments: step.tool_arguments,
    goal: step.goal,
    depends_on: Array.isArray(step.depends_on) ? step.depends_on : [],
    parallel_safe: Boolean(extra.parallel_safe),
    retryable: extra.retryable !== false,
    state: extra.state || 'pending',
  };
}

function buildPlanGraph({ steps = [], mode = 'linear' }) {
  const nodes = steps.map((step, index) => buildPlanNode(step, {
    parallel_safe: Boolean(step.parallel_safe),
    retryable: true,
    state: 'pending',
    order: index,
  }));
  return {
    version: 1,
    mode,
    nodes,
  };
}

module.exports = {
  buildPlanGraph,
  buildPlanNode,
};
