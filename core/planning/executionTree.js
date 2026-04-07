function buildTreeNode({
  nodeId,
  parentId = null,
  branchId = null,
  ownerAgent = 'master_orchestrator',
  goalId = null,
  stepId = null,
  label = '',
  nodeType = 'step',
}) {
  return {
    node_id: nodeId,
    parent_id: parentId,
    branch_id: branchId,
    owner_agent: ownerAgent,
    goal_id: goalId,
    step_id: stepId,
    label,
    node_type: nodeType,
    state: 'pending',
    retries: 0,
    children: [],
    merge_target: null,
  };
}

function buildExecutionTree({ steps = [], planHierarchy = null, branchPlan = null, milestonePlan = null }) {
  const rootGoalId = planHierarchy?.root_goal_id || 'goal:root';
  const nodes = [];
  const rootNode = buildTreeNode({
    nodeId: 'tree:root',
    parentId: null,
    goalId: rootGoalId,
    label: 'Runtime root goal',
    nodeType: 'goal',
  });
  nodes.push(rootNode);

  const goalNodes = new Map();
  if (planHierarchy && Array.isArray(planHierarchy.subgoals)) {
    for (const subgoal of planHierarchy.subgoals) {
      const node = buildTreeNode({
        nodeId: `tree:${subgoal.goal_id}`,
        parentId: 'tree:root',
        goalId: subgoal.goal_id,
        label: subgoal.label || subgoal.goal_id,
        nodeType: 'subgoal',
      });
      nodes.push(node);
      rootNode.children.push(node.node_id);
      goalNodes.set(subgoal.goal_id, node.node_id);
    }
  }

  const branchNodes = new Map();
  const milestoneNodes = new Map();
  if (branchPlan && Array.isArray(branchPlan.branches)) {
    for (const branch of branchPlan.branches) {
      const node = buildTreeNode({
        nodeId: `tree:${branch.branch_id}`,
        parentId: 'tree:root',
        branchId: branch.branch_id,
        label: branch.label || branch.branch_id,
        nodeType: 'branch',
      });
      nodes.push(node);
      rootNode.children.push(node.node_id);
      branchNodes.set(branch.branch_id, node.node_id);
    }
  }

  if (milestonePlan && Array.isArray(milestonePlan.milestone_tree?.milestones)) {
    for (const milestone of milestonePlan.milestone_tree.milestones) {
      const node = buildTreeNode({
        nodeId: `tree:${milestone.milestone_id}`,
        parentId: 'tree:root',
        ownerAgent: 'task_planner',
        goalId: milestone.goal_id || null,
        label: milestone.title || milestone.milestone_id,
        nodeType: 'milestone',
      });
      nodes.push(node);
      rootNode.children.push(node.node_id);
      milestoneNodes.set(milestone.milestone_id, node.node_id);
    }
  }

  for (const step of steps) {
    const parentId = step.branch_id
      ? branchNodes.get(step.branch_id) || 'tree:root'
      : step.milestone_id
        ? milestoneNodes.get(step.milestone_id) || 'tree:root'
      : step.goal_id
        ? goalNodes.get(step.goal_id) || 'tree:root'
        : 'tree:root';
    const node = buildTreeNode({
      nodeId: `tree:${step.step_id}`,
      parentId,
      branchId: step.branch_id || null,
      ownerAgent: step.selected_agent || 'master_orchestrator',
      goalId: step.goal_id || null,
      stepId: step.step_id,
      label: step.goal || step.step_id,
    });
    nodes.push(node);
    const parent = nodes.find(item => item.node_id === parentId);
    if (parent) {
      parent.children.push(node.node_id);
    }
  }

  return {
    version: 1,
    root_node_id: rootNode.node_id,
    nodes,
    bounded: true,
    merge_policy: branchPlan?.merge_mode || 'linear-completion',
  };
}

module.exports = {
  buildExecutionTree,
  buildTreeNode,
};
