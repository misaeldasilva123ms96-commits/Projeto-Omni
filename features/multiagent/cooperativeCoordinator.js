function buildContribution({
  specialistId,
  role,
  sharedGoalId,
  summary,
  dependsOn = [],
  confidence = 0.7,
  branchId = null,
  status = 'planned',
  metadata = {},
}) {
  return {
    contribution_id: `${sharedGoalId}:${specialistId}:${branchId || 'main'}`,
    specialist_id: specialistId,
    role,
    shared_goal_id: sharedGoalId,
    depends_on: Array.isArray(dependsOn) ? dependsOn : [],
    summary: String(summary || '').trim(),
    confidence: Math.max(0, Math.min(1, Number(confidence || 0))),
    branch_id: branchId,
    status,
    metadata,
  };
}

function buildCooperativePlan({ message = '', plannerResult, delegation, strategySuggestions = [] }) {
  const sharedGoalId = 'shared-goal:root';
  const steps = Array.isArray(plannerResult?.steps) ? plannerResult.steps : [];
  const delegates = delegation?.delegates || [];
  const wantsAnalysis = String(message || '').toLowerCase().includes('analise');
  const contributions = [];

  if (delegates.includes('task_planner')) {
    contributions.push(buildContribution({
      specialistId: 'task_planner',
      role: 'planner',
      sharedGoalId,
      summary: 'Decompor a meta compartilhada em etapas executáveis e seguras.',
      confidence: 0.86,
      metadata: { step_count: steps.length, plan_kind: plannerResult?.plan_kind || 'linear' },
    }));
  }

  if (steps.some(step => ['glob_search', 'grep_search', 'read_file'].includes(step.selected_tool))) {
    contributions.push(buildContribution({
      specialistId: 'researcher_agent',
      role: 'researcher',
      sharedGoalId,
      summary: 'Coletar evidências do workspace para a meta compartilhada.',
      dependsOn: ['task_planner'],
      confidence: 0.82,
      metadata: { read_steps: steps.filter(step => step.selected_agent === 'researcher_agent').length },
    }));
  }

  if (wantsAnalysis || delegates.includes('reviewer_agent')) {
    contributions.push(buildContribution({
      specialistId: 'reviewer_agent',
      role: 'reviewer',
      sharedGoalId,
      summary: 'Revisar lacunas, conflitos e qualidade das evidências antes da síntese.',
      dependsOn: ['researcher_agent'],
      confidence: 0.74,
      metadata: { review_scope: wantsAnalysis ? 'analysis' : 'execution' },
    }));
  }

  if (delegates.includes('critic_agent')) {
    contributions.push(buildContribution({
      specialistId: 'critic_agent',
      role: 'critic',
      sharedGoalId,
      summary: 'Checar risco, branches fracos e necessidade de revisão antes de agir.',
      dependsOn: ['task_planner'],
      confidence: 0.71,
      metadata: { strategy_candidates: strategySuggestions.length },
    }));
  }

  if (delegates.includes('dependency_impact_specialist')) {
    contributions.push(buildContribution({
      specialistId: 'dependency_impact_specialist',
      role: 'impact-analyst',
      sharedGoalId,
      summary: 'Mapear impacto entre modulos, arquivos afetados e hotspots de integracao.',
      dependsOn: ['task_planner', 'researcher_agent'].filter(id => contributions.some(item => item.specialist_id === id)),
      confidence: 0.77,
      metadata: {
        candidate_count: Array.isArray(plannerResult?.repo_impact_analysis?.module_change_candidates)
          ? plannerResult.repo_impact_analysis.module_change_candidates.length
          : 0,
      },
    }));
  }

  if (delegates.includes('test_selection_specialist')) {
    contributions.push(buildContribution({
      specialistId: 'test_selection_specialist',
      role: 'verification-planner',
      sharedGoalId,
      summary: 'Selecionar verificacoes direcionadas e regressao minima antes do merge readiness.',
      dependsOn: ['dependency_impact_specialist', 'researcher_agent'].filter(id => contributions.some(item => item.specialist_id === id)),
      confidence: 0.76,
      metadata: {
        verification_modes: plannerResult?.verification_plan?.verification_modes || [],
      },
    }));
  }

  if (delegates.includes('synthesizer_agent')) {
    contributions.push(buildContribution({
      specialistId: 'synthesizer_agent',
      role: 'synthesizer',
      sharedGoalId,
      summary: 'Fundir as contribuições em uma resposta final rastreável.',
      dependsOn: ['reviewer_agent', 'critic_agent'].filter(id => contributions.some(item => item.specialist_id === id)),
      confidence: 0.79,
      metadata: {},
    }));
  }

  return {
    shared_goal_id: sharedGoalId,
    mode: contributions.length >= 2 ? 'cooperative-shared-goal' : 'single-specialist',
    contributions,
    merge_contract: {
      owner: 'master_orchestrator',
      fusion_policy: 'confidence-grounded-merge',
      unresolved_conflict_policy: 'surface-to-operator',
    },
  };
}

module.exports = {
  buildCooperativePlan,
  buildContribution,
};
