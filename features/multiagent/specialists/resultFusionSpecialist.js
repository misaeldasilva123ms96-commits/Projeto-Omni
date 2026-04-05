function normalizeContribution(result = {}) {
  const action = result.action || {};
  const evaluation = result.evaluation || {};
  const confidence = Number(
    result.confidence
      ?? (result.ok ? 0.8 : 0.35)
      + (evaluation.critic?.decision === 'approve' ? 0.05 : 0)
      - (evaluation.critic?.decision === 'stop' ? 0.15 : 0),
  );
  return {
    step_id: action.step_id || result.step_id || null,
    branch_id: action.execution_context?.branch_id || result.branch_id || null,
    specialist_id: action.selected_agent || result.selected_agent || 'unknown',
    tool: action.selected_tool || result.selected_tool || 'none',
    ok: Boolean(result.ok),
    confidence: Math.max(0, Math.min(1, confidence)),
    summary: String(result.summary || '').trim(),
    conflict_key: `${action.execution_context?.shared_goal_id || 'root'}:${action.selected_tool || result.selected_tool || 'none'}`,
  };
}

function fuseResults(stepResults = [], cooperativePlan = null, branchState = null) {
  const contributions = stepResults.map(normalizeContribution);
  const grouped = new Map();
  for (const item of contributions) {
    const current = grouped.get(item.conflict_key) || [];
    current.push(item);
    grouped.set(item.conflict_key, current);
  }

  const conflicts = [];
  const merged = [];
  for (const items of grouped.values()) {
    if (items.length > 1) {
      const summaries = new Set(items.map(item => item.summary).filter(Boolean));
      if (summaries.size > 1) {
        conflicts.push({
          conflict_key: items[0].conflict_key,
          branch_ids: items.map(item => item.branch_id).filter(Boolean),
          specialist_ids: items.map(item => item.specialist_id),
        });
      }
    }
    const winner = [...items].sort((a, b) => b.confidence - a.confidence)[0];
    merged.push(winner);
  }

  return {
    cooperative_mode: cooperativePlan?.mode || 'single-specialist',
    contribution_count: contributions.length,
    merged_count: merged.length,
    contributions,
    conflicts,
    merged,
    branch_resolution: branchState
      ? {
          winner_branch_id: branchState.winner_branch_id || null,
          merge_mode: branchState.merge_mode || 'winner-selection',
          pruned_branch_ids: branchState.pruned_branch_ids || [],
        }
      : null,
  };
}

module.exports = {
  fuseResults,
  normalizeContribution,
};
