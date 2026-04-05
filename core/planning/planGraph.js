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
    goal_id: extra.goal_id || step.goal_id || null,
    parent_goal_id: extra.parent_goal_id || step.parent_goal_id || null,
    branch_id: extra.branch_id || step.branch_id || null,
    shared_goal_id: extra.shared_goal_id || step.shared_goal_id || null,
  };
}

function buildPlanGraph({ steps = [], mode = 'linear' }) {
  const nodes = steps.map((step, index) => buildPlanNode(step, {
    parallel_safe: Boolean(step.parallel_safe),
    retryable: true,
    state: 'pending',
    order: index,
    goal_id: step.goal_id,
    parent_goal_id: step.parent_goal_id,
    branch_id: step.branch_id,
    shared_goal_id: step.shared_goal_id,
  }));
  return {
    version: 1,
    mode,
    nodes,
  };
}

function buildHierarchicalPlan({ rootGoal, subgoals = [] }) {
  return {
    version: 1,
    mode: 'hierarchical',
    root_goal_id: rootGoal.goal_id,
    root_goal: rootGoal,
    subgoals,
  };
}

module.exports = {
  buildPlanGraph,
  buildHierarchicalPlan,
  buildPlanNode,
};
